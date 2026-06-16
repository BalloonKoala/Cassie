"""Cassie — starts automatically on boot via systemd. No manual commands."""
from __future__ import annotations
import asyncio
import logging
import signal
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from audio_manager import AudioManager
from http_server import HTTPServer
from llm import LLMEngine
from memory import MemoryManager
from net_wait import wait_for_internet
from stt import SpeechToText
from tts import TextToSpeech
from vad import VADProcessor
from wake_word import WakeWordDetector
from ws_server import WSServer

log = logging.getLogger(__name__)


def load_config() -> dict:
    p = ROOT / "config" / "config.yaml"
    if not p.is_file():
        raise FileNotFoundError(f"Missing {p} — add OpenRouter API key")
    with p.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def setup_logging(cfg: dict) -> None:
    lvl = getattr(logging, cfg.get("logging", {}).get("level", "INFO").upper(), logging.INFO)
    logging.basicConfig(
        level=lvl,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


class CassieApp:
    def __init__(self, config: dict) -> None:
        self._running = False
        self._busy = False
        self._config = config
        self._memory = MemoryManager(config)
        self._audio = AudioManager(config)
        self._vad = VADProcessor(
            int(config.get("audio", {}).get("sample_rate", 48000)),
            int(config.get("vad", {}).get("aggressiveness", 2)),
        )
        self._stt = SpeechToText(config)
        self._llm = LLMEngine(config)
        self._tts = TextToSpeech(config)
        ws = config.get("websocket", {})
        http = config.get("http", {})
        self._ws = WSServer(ws.get("host", "127.0.0.1"), int(ws.get("port", 8765)))
        self._http = HTTPServer(ROOT / "frontend", http.get("host", "127.0.0.1"), int(http.get("port", 8766)))
        self._wake = WakeWordDetector(self._audio, self._vad, self._stt, on_wake=self._on_wake)
        self._amp_task: asyncio.Task | None = None

    async def _broadcast_mic(self) -> None:
        while self._running:
            try:
                await self._ws.send_amplitude(self._audio.mic_level)
            except Exception:
                pass
            await asyncio.sleep(0.05)

    async def _on_wake(self, command: str) -> None:
        if self._busy:
            return
        self._busy = True
        self._wake.pause()
        try:
            await self._handle_command(command)
        finally:
            self._wake.resume()
            self._busy = False
            await self._ws.send_state("idle")

    async def _handle_command(self, command: str) -> None:
        await self._ws.send_state("listening")
        if not command.strip():
            pcm = await asyncio.to_thread(self._vad.collect_utterance, self._audio, 5.0)
            if pcm:
                command = await self._stt.transcribe(pcm)
            if not command.strip():
                return
        log.info("Command: %r", command)
        await self._ws.send_state("thinking")
        reply, facts = await self._llm.chat(command, self._memory.retrieve_relevant(command))
        if facts:
            self._memory.store_facts(facts)
        if not reply.strip():
            reply = "I'm not sure what to say."
        await self._ws.send_state("speaking")
        await self._tts.speak(
            reply,
            on_chunk=self._audio.play_chunk,
            on_amplitude=lambda lvl: asyncio.create_task(self._ws.send_amplitude(lvl)),
        )

    async def run(self) -> None:
        log.info("Cassie starting (auto-boot)...")
        self._running = True

        self._memory.open()
        await self._ws.start()
        await self._http.start()
        log.info("UI ready at http://127.0.0.1:8766/")

        if not await wait_for_internet(120.0):
            log.warning("No internet yet — STT/LLM will retry when needed")

        key = self._config.get("openrouter", {}).get("api_key", "")
        if not key or key == "YOUR_OPENROUTER_API_KEY":
            log.error("Set openrouter.api_key in /opt/cassie/config/config.yaml")

        try:
            self._audio.open()
            self._audio.play_beep()
            self._wake.start()
            self._amp_task = asyncio.create_task(self._broadcast_mic())
        except Exception:
            log.exception("Audio failed — orb UI still works; check mic/USB")

        log.info("Cassie ready. Listening for wake word...")
        await self._ws.send_state("idle")
        while self._running:
            await asyncio.sleep(0.5)

    async def shutdown(self) -> None:
        if not self._running:
            return
        log.info("Shutting down...")
        self._running = False
        self._wake.pause()
        if self._amp_task:
            self._amp_task.cancel()
            try:
                await self._amp_task
            except asyncio.CancelledError:
                pass
        await self._wake.stop()
        await self._ws.stop()
        await self._http.stop()
        self._audio.close()
        self._memory.close()
        log.info("Cassie stopped.")


async def main() -> None:
    config = load_config()
    setup_logging(config)
    app = CassieApp(config)
    loop = asyncio.get_running_loop()
    stop = asyncio.Event()

    def on_stop() -> None:
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, on_stop)
        except NotImplementedError:
            signal.signal(sig, lambda *_: on_stop())

    task = asyncio.create_task(app.run())
    await stop.wait()
    await app.shutdown()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        logging.basicConfig(level=logging.INFO)
        logging.exception("Cassie crashed")
        sys.exit(1)