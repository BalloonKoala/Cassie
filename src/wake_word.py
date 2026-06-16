"""Wake word detection via VAD + STT keyword check (no openwakeword)."""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Optional

from wake_utils import extract_command, is_wake_word

log = logging.getLogger(__name__)

WakeCallback = Callable[[str], Awaitable[None]]


class WakeWordDetector:
    """
    Listens continuously: VAD collects short utterances, STT transcribes,
    fuzzy-matches wake word, then invokes callback with trailing command.
    """

    def __init__(
        self,
        audio_manager,
        vad_processor,
        stt,
        on_wake: WakeCallback,
    ) -> None:
        self._audio = audio_manager
        self._vad = vad_processor
        self._stt = stt
        self._on_wake = on_wake
        self._task: Optional[asyncio.Task] = None
        self._paused = False
        self._running = False

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._running = True
        self._task = asyncio.create_task(self._listen_loop(), name="wake-listener")
        log.info("Wake listener started (VAD+STT)")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    async def _listen_loop(self) -> None:
        while self._running:
            if self._paused:
                await asyncio.sleep(0.2)
                continue

            try:
                pcm = await asyncio.to_thread(
                    self._vad.collect_utterance,
                    self._audio,
                    3.0,
                )
                if not pcm or self._paused:
                    continue

                text = await self._stt.transcribe(pcm)
                if not text:
                    continue

                log.info("Heard: %r", text)

                if is_wake_word(text):
                    command = extract_command(text)
                    log.info("Wake detected, command=%r", command)
                    await self._on_wake(command)
                else:
                    log.debug("No wake word in: %r", text)

            except asyncio.CancelledError:
                break
            except Exception:
                log.exception("Wake loop error")
                await asyncio.sleep(0.5)
