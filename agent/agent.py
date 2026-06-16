#!/usr/bin/env python3
"""Pi agent — mic in, speaker out, WebSocket to Cassie server."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import sys
from pathlib import Path

import websockets
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "agent"))

from audio_manager import AudioManager
from vad import VADProcessor
from apple_music import AppleMusicController

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def load_config() -> dict:
    p = ROOT / "config" / "config.yaml"
    if p.is_file():
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return {"audio": {"sample_rate": 48000, "channels": 1}}


class CassieAgent:
    def __init__(self) -> None:
        self.config = load_config()
        self.device_id = os.getenv("CASSIE_DEVICE", "pi-home")
        self.token = os.getenv("CASSIE_DEVICE_TOKEN", "change-me")
        server = os.getenv("CASSIE_SERVER", "http://127.0.0.1:8780").rstrip("/")
        server = server.replace("https://", "wss://").replace("http://", "ws://")
        self.ws_url = f"{server}/ws?device={self.device_id}&role=agent&token={self.token}"
        self.audio = AudioManager(self.config)
        self.vad = VADProcessor(int(self.config.get("audio", {}).get("sample_rate", 48000)))
        self.music = AppleMusicController()
        self._ws = None
        self._unlocked = False

    async def run(self) -> None:
        while True:
            try:
                async with websockets.connect(self.ws_url, ping_interval=20) as ws:
                    self._ws = ws
                    log.info("Connected to %s", self.ws_url)
                    await asyncio.gather(self._recv_loop(), self._amp_loop(), self._speech_loop())
            except Exception:
                log.exception("Connection lost, retry in 3s")
                await asyncio.sleep(3)

    async def _recv_loop(self) -> None:
        assert self._ws
        async for raw in self._ws:
            msg = json.loads(raw)
            t = msg.get("type")
            if t == "hello":
                self._unlocked = bool(msg.get("unlocked"))
            if t == "tts_pcm":
                self.audio.play_pcm(base64.b64decode(msg.get("data", "")))
            if t == "command":
                await self._handle_command(msg.get("cmd"), msg.get("payload") or {})

    async def _handle_command(self, cmd: str, payload: dict) -> None:
        if cmd == "apple_music":
            self.music.play_search(payload.get("query", ""))
        if cmd == "cassie_home":
            self.music.return_to_cassie()

    async def _amp_loop(self) -> None:
        try:
            self.audio.open()
        except Exception:
            log.exception("Audio open failed — orb will work but no mic/TTS")
        while self._ws:
            await self._send({"type": "amplitude", "level": self.audio.mic_level})
            await asyncio.sleep(0.05)

    async def _speech_loop(self) -> None:
        while self._ws:
            pcm = await asyncio.to_thread(self.vad.collect_utterance, self.audio, 10.0, 10.0, 0.9)
            if pcm:
                await self._send({"type": "utterance", "data": base64.b64encode(pcm).decode()})

    async def _send(self, msg: dict) -> None:
        if self._ws:
            await self._ws.send(json.dumps(msg))


def main() -> None:
    asyncio.run(CassieAgent().run())


if __name__ == "__main__":
    main()
