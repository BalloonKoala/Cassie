#!/usr/bin/env python3
"""
Cassie 2.0 — ONE process: pygame orb + voice AI.
Started from ~/.xinitrc on boot. No Chromium. No separate systemd backend.
"""
from __future__ import annotations

import asyncio
import logging
import sys
import threading
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from audio_manager import AudioManager
from llm import LLMEngine
from memory import MemoryManager
from net_wait import wait_for_internet
from orb_ui import OrbUI
from stt import SpeechToText
from tts import TextToSpeech
from vad import VADProcessor
from wake_word import WakeWordDetector

log = logging.getLogger(__name__)


def load_config() -> dict:
    p = ROOT / "config" / "config.yaml"
    if not p.is_file():
        raise FileNotFoundError(f"Missing {p} — set openrouter.api_key")
    with p.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def setup_logging(cfg: dict) -> None:
    lvl = getattr(logging, cfg.get("logging", {}).get("level", "INFO").upper(), logging.INFO)
    logging.basicConfig(
        level=lvl,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


class Cassie:
    def __init__(self, config: dict, ui: OrbUI) -> None:
        self._ui = ui
        self._config = config
        self._running = False
        self._busy = False
        self._memory = MemoryManager(config)
        self._audio = AudioManager(config)
        self._vad = VADProcessor(
            int(config.get("audio", {}).get("sample_rate", 48000)),
            int(config.get("vad", {}).get("aggressiveness", 2)),
        )
        self._stt = SpeechToText(config)
        self._llm = LLMEngine(config)
        self._tts = TextToSpeech(config)
        self._wake = WakeWordDetector(self._audio, self._vad, self._stt, on_wake=self._on_wake)
        self._amp_task: asyncio.Task | None = None

    def _set_state(self, state: str) -> None:
        self._ui.set_state(state)

    async def _broadcast_mic(self) -> None:
        while self._running:
            self._ui.set_amplitude(self._audio.mic_level)
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
            self._set_state("idle")

    async def _handle_command(self, command: str) -> None:
        self._set_state("listening")
        if not command.strip():
            pcm = await asyncio.to_thread(self._vad.collect_utterance, self._audio, 5.0)
            if pcm:
                command = await self._stt.transcribe(pcm)
            if not command.strip():
                return
        log.info("Command: %r", command)
        self._set_state("thinking")
        reply, facts = await self._llm.chat(command, self._memory.retrieve_relevant(command))
        if facts:
            self._memory.store_facts(facts)
        if not reply.strip():
            reply = "I'm not sure what to say."
        self._set_state("speaking")
        await self._tts.speak(
            reply,
            on_chunk=self._audio.play_chunk,
            on_amplitude=lambda lvl: self._ui.set_amplitude(lvl),
        )

    async def run(self) -> None:
        log.info("Cassie 2.0 starting...")
        self._running = True
        self._set_state("idle")
        self._memory.open()

        if not await wait_for_internet(60.0):
            log.warning("No internet yet — voice AI will retry when needed")

        key = self._config.get("openrouter", {}).get("api_key", "")
        if not key or key == "YOUR_OPENROUTER_API_KEY":
            log.error("Set openrouter.api_key in /opt/cassie/config/config.yaml")

        try:
            self._audio.open()
            self._audio.play_beep()
            self._wake.start()
            self._amp_task = asyncio.create_task(self._broadcast_mic())
        except Exception:
            log.exception("Audio failed — orb still shows; check USB mic")

        log.info("Ready. Say: Cassie, what time is it?")
        while self._running:
            await asyncio.sleep(0.5)


async def _backend(ui: OrbUI) -> None:
    config = load_config()
    setup_logging(config)
    app = Cassie(config, ui)
    await app.run()


def main() -> None:
    ui = OrbUI()
    loop = asyncio.new_event_loop()

    def backend_thread() -> None:
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_backend(ui))
        except Exception:
            logging.exception("Backend crashed")
        finally:
            loop.close()

    threading.Thread(target=backend_thread, daemon=True).start()
    ui.run_forever()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.basicConfig(level=logging.INFO)
        logging.exception("Cassie crashed")
        sys.exit(1)
