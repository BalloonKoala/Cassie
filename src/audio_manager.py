"""PyAudio — Fifine USB mic in, Pi headphone jack out."""
from __future__ import annotations
import logging, math, struct, threading, time
from collections import deque
from typing import Callable, Optional
import pyaudio

log = logging.getLogger(__name__)
AmplitudeCallback = Callable[[float], None]
USB_MIC_KEYS = ("fifine", "usb", "microphone", "mic")
OUT_KEYS = ("bcm2835", "headphones", "analog", "built-in", "snd_rpi")


class AudioManager:
    def __init__(self, config: dict) -> None:
        a = config.get("audio", {})
        self.sample_rate = int(a.get("sample_rate", 48000))
        self.channels = int(a.get("channels", 1))
        self.chunk_size = int(a.get("chunk_size", 1024))
        ci, co = a.get("input_device_index"), a.get("output_device_index")
        self.input_device_index = int(ci) if ci is not None else None
        self.output_device_index = int(co) if co is not None else None
        self._pa = pyaudio.PyAudio()
        self._capture_stream = None
        self._playback_stream = None
        self._playback_channels = 2
        self._capture_buffer: deque[bytes] = deque(maxlen=500)
        self._capture_lock = threading.Lock()
        self._running = False
        self._mic_level = 0.0
        self._amp_callbacks: list[AmplitudeCallback] = []

    def add_amplitude_callback(self, cb: AmplitudeCallback) -> None:
        self._amp_callbacks.append(cb)

    def _log_devices(self) -> None:
        for i in range(self._pa.get_device_count()):
            d = self._pa.get_device_info_by_index(i)
            log.info("Audio device [%d] in=%s out=%s %s", i, int(d["maxInputChannels"]), int(d["maxOutputChannels"]), d["name"])

    def _find_usb_mic(self) -> Optional[int]:
        best = None
        for i in range(self._pa.get_device_count()):
            d = self._pa.get_device_info_by_index(i)
            if d.get("maxInputChannels", 0) <= 0:
                continue
            name = d["name"].lower()
            if any(k in name for k in USB_MIC_KEYS):
                log.info("Found USB mic [%d] %s", i, d["name"])
                if "fifine" in name:
                    return i
                best = i
        return best

    def _find_headphone_out(self) -> Optional[int]:
        for i in range(self._pa.get_device_count()):
            d = self._pa.get_device_info_by_index(i)
            if d.get("maxOutputChannels", 0) <= 0:
                continue
            name = d["name"].lower()
            if any(k in name for k in OUT_KEYS):
                log.info("Found headphone/analog out [%d] %s", i, d["name"])
                return i
        return None

    @staticmethod
    def _rms(data: bytes) -> float:
        n = len(data) // 2
        if n == 0:
            return 0.0
        s = struct.unpack(f"<{n}h", data[: n * 2])
        m = sum(x * x for x in s) / n
        return min(1.0, math.sqrt(m) / 32768.0 * 4.0)

    def _capture_callback(self, in_data, frame_count, time_info, status):
        self._mic_level = self._mic_level * 0.7 + self._rms(in_data) * 0.3
        with self._capture_lock:
            self._capture_buffer.append(bytes(in_data))
        for cb in self._amp_callbacks:
            try:
                cb(self._mic_level)
            except Exception:
                pass
        return (None, pyaudio.paContinue)

    def _open_capture(self) -> None:
        self._log_devices()
        idx = self.input_device_index
        if idx is not None:
            try:
                d = self._pa.get_device_info_by_index(idx)
                if d.get("maxInputChannels", 0) <= 0:
                    log.warning("Config input_device_index=%s has no inputs, auto-detecting", idx)
                    idx = None
            except Exception:
                idx = None
        if idx is None:
            idx = self._find_usb_mic()
        err = None
        for rate in (self.sample_rate, 48000, 44100):
            for ch in (self.channels, 1, 2):
                try:
                    kw = dict(format=pyaudio.paInt16, channels=ch, rate=rate, input=True,
                              frames_per_buffer=self.chunk_size, stream_callback=self._capture_callback)
                    if idx is not None:
                        kw["input_device_index"] = idx
                    self._capture_stream = self._pa.open(**kw)
                    self.sample_rate, self.channels, self.input_device_index = rate, ch, idx
                    self._capture_stream.start_stream()
                    log.info("Mic open: dev=%s rate=%d ch=%d", idx, rate, ch)
                    return
                except Exception as e:
                    err = e
                    self._capture_stream = None
        raise OSError(f"Cannot open Fifine USB mic (device={idx}): {err}")

    def _open_playback(self) -> None:
        out_candidates: list[Optional[int]] = []
        if self.output_device_index is not None:
            out_candidates.append(self.output_device_index)
        found = self._find_headphone_out()
        if found is not None and found not in out_candidates:
            out_candidates.append(found)
        out_candidates.append(None)
        err = None
        for out_idx in out_candidates:
            for ch in (2, 1):
                for rate in (self.sample_rate, 48000, 44100):
                    try:
                        kw = dict(format=pyaudio.paInt16, channels=ch, rate=rate, output=True, frames_per_buffer=self.chunk_size)
                        if out_idx is not None:
                            kw["output_device_index"] = out_idx
                        self._playback_stream = self._pa.open(**kw)
                        self._playback_channels = ch
                        self.sample_rate = rate
                        self.output_device_index = out_idx
                        log.info("Speakers open: dev=%s rate=%d ch=%d", out_idx, rate, ch)
                        return
                    except Exception as e:
                        err = e
                        self._playback_stream = None
        raise OSError(f"Cannot open headphone jack output: {err}")

    def open(self) -> None:
        if self._running:
            return
        self._open_capture()
        self._open_playback()
        self._running = True
        log.info("Audio ready")

    def close(self) -> None:
        self._running = False
        for s in (self._capture_stream, self._playback_stream):
            if s:
                try:
                    s.stop_stream()
                    s.close()
                except Exception:
                    pass
        self._capture_stream = self._playback_stream = None
        if self._pa:
            self._pa.terminate()
        log.info("Audio closed")

    @property
    def mic_level(self) -> float:
        return self._mic_level

    def read_frame(self, num_bytes: int, timeout: float = 1.0) -> bytes:
        end = time.time() + timeout
        parts: list[bytes] = []
        while sum(len(p) for p in parts) < num_bytes and time.time() < end:
            with self._capture_lock:
                if self._capture_buffer:
                    parts.append(self._capture_buffer.popleft())
            time.sleep(0.01)
        data = b"".join(parts)
        return data[:num_bytes]

    def _to_stereo(self, pcm: bytes) -> bytes:
        if self._playback_channels == 1 or not pcm:
            return pcm
        n = len(pcm) // 2
        s = struct.unpack(f"<{n}h", pcm[: n * 2])
        return struct.pack(f"<{n * 2}h", *[x for v in s for x in (v, v)])

    def play_pcm(self, pcm: bytes) -> None:
        if pcm and self._playback_stream:
            try:
                self._playback_stream.write(self._to_stereo(pcm))
            except Exception:
                log.exception("Playback failed")

    def play_chunk(self, chunk: bytes) -> None:
        self.play_pcm(chunk)

    def play_beep(self, frequency: float = 880.0, duration: float = 0.25, volume: float = 0.3) -> None:
        if not self._playback_stream:
            return
        n = int(self.sample_rate * duration)
        pcm = struct.pack(
            f"<{n}h",
            *[int(volume * 32767 * math.sin(2 * math.pi * frequency * i / self.sample_rate)) for i in range(n)],
        )
        self.play_pcm(pcm)
        log.info("Startup beep played")