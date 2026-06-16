"""Voice activity detection using webrtcvad."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import webrtcvad

if TYPE_CHECKING:
    from audio_manager import AudioManager

log = logging.getLogger(__name__)

# webrtcvad frame sizes at 10/20/30 ms
FRAME_MS = 30


class VADProcessor:
    """Segments speech from the mic stream using WebRTC VAD."""

    def __init__(self, sample_rate: int = 48000, aggressiveness: int = 2) -> None:
        if sample_rate not in (8000, 16000, 32000, 48000):
            raise ValueError(f"webrtcvad requires 8/16/32/48 kHz, got {sample_rate}")
        self.sample_rate = sample_rate
        self.frame_bytes = int(sample_rate * FRAME_MS / 1000) * 2  # 16-bit mono
        self._vad = webrtcvad.Vad(aggressiveness)

    def is_speech(self, frame: bytes) -> bool:
        if len(frame) != self.frame_bytes:
            return False
        try:
            return self._vad.is_speech(frame, self.sample_rate)
        except Exception:
            return False

    def collect_utterance(
        self,
        audio_manager: AudioManager,
        max_silence_before_speech: float = 3.0,
        max_utterance_seconds: float = 10.0,
        trailing_silence: float = 0.8,
    ) -> bytes:
        """
        Block until speech is detected, then collect until trailing silence.
        Returns PCM16 mono bytes.
        """
        import time

        frames: list[bytes] = []
        speech_started = False
        silence_frames = 0
        trailing_frames = int(trailing_silence * 1000 / FRAME_MS)
        max_frames = int(max_utterance_seconds * 1000 / FRAME_MS)
        wait_frames = int(max_silence_before_speech * 1000 / FRAME_MS)
        waited = 0

        while waited < wait_frames or speech_started:
            frame = audio_manager.read_frame(self.frame_bytes, timeout=1.0)
            if not frame:
                waited += int(1000 / FRAME_MS)
                continue

            if self.is_speech(frame):
                speech_started = True
                silence_frames = 0
                frames.append(frame)
                waited = 0
            elif speech_started:
                silence_frames += 1
                frames.append(frame)
                if silence_frames >= trailing_frames:
                    break
            else:
                waited += 1

            if speech_started and len(frames) >= max_frames:
                break

        return b"".join(frames)
