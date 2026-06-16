#!/usr/bin/env python3
"""Cassie v3 server — hosts web UI + WebSocket hub + voice AI."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import sys
from pathlib import Path

import yaml
from aiohttp import web
from dotenv import load_dotenv

from brain import Brain
from hub import Hub

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

load_dotenv(ROOT / "server" / ".env")
load_dotenv()

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DEVICE_TOKEN = os.getenv("CASSIE_DEVICE_TOKEN", "change-me")
WEB_ROOT = Path(os.getenv("WEB_ROOT", ROOT / "web")).resolve()
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8780"))

hub = Hub()


def load_config() -> dict:
    p = ROOT / "config" / "config.yaml"
    cfg: dict = {}
    if p.is_file():
        cfg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    key = os.getenv("OPENROUTER_API_KEY") or cfg.get("openrouter", {}).get("api_key", "")
    cfg.setdefault("openrouter", {})["api_key"] = key
    cfg.setdefault("audio", {})["sample_rate"] = int(cfg.get("audio", {}).get("sample_rate", 48000))
    return cfg


brain = Brain(
    load_config(),
    owner=os.getenv("OWNER_NAME", "Everett"),
    passphrase=os.getenv("PASSPHRASE", "146 easy street"),
)


async def set_state(device_id: str, state: str, amp: float | None = None) -> None:
    msg: dict = {"type": "state", "state": state}
    if amp is not None:
        msg["amplitude"] = amp
    await hub.send_browser(device_id, msg)


async def send_command(device_id: str, cmd: str, payload: dict) -> None:
    await hub.broadcast(device_id, {"type": "command", "cmd": cmd, "payload": payload})


async def ws_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse(heartbeat=20)
    await ws.prepare(request)

    device_id = request.query.get("device", "pi-home")
    role = request.query.get("role", "browser")
    token = request.query.get("token", "")

    if token != DEVICE_TOKEN:
        await ws.send_json({"type": "error", "message": "Invalid token"})
        await ws.close()
        return ws

    sess = await hub.register(device_id, role, ws)
    await ws.send_json({"type": "hello", "role": role, "unlocked": sess.unlocked})

    if role == "agent" and not sess.unlocked:
        await set_state(device_id, "speaking")
        line = await brain.unlock_lines()

        def play_pcm(pcm: bytes) -> None:
            asyncio.create_task(ws.send_json({"type": "tts_pcm", "data": brain.pcm_b64(pcm)}))

        def amp(a: float) -> None:
            asyncio.create_task(hub.send_browser(device_id, {"type": "amplitude", "amplitude": a}))

        await brain.stream_tts(line, play_pcm, amp)
        await set_state(device_id, "listening")

    try:
        async for msg in ws:
            if msg.type != web.WSMsgType.TEXT:
                continue
            data = json.loads(msg.data)
            await handle_message(device_id, role, ws, data)
    finally:
        await hub.unregister(device_id, role, ws)
    return ws


async def handle_message(device_id: str, role: str, ws, data: dict) -> None:
    mtype = data.get("type")

    if mtype == "amplitude" and role == "agent":
        await hub.send_browser(device_id, {"type": "amplitude", "amplitude": data.get("level", 0)})
        return

    if mtype == "utterance" and role == "agent":
        pcm = base64.b64decode(data.get("data", ""))
        text = await brain.transcribe_pcm(pcm)
        if not text:
            return

        sess = hub.session(device_id)
        if not sess or not sess.unlocked:
            if brain.check_passphrase(text):
                hub.set_unlocked(device_id, True)
                await hub.send_browser(device_id, {"type": "unlock"})
                await set_state(device_id, "speaking")
                granted = await brain.access_granted_line()

                def play_pcm(pcm: bytes) -> None:
                    asyncio.create_task(ws.send_json({"type": "tts_pcm", "data": brain.pcm_b64(pcm)}))

                await brain.stream_tts(granted, play_pcm, lambda a: None)
                await set_state(device_id, "idle")
            else:
                await set_state(device_id, "speaking")

                def play_pcm2(pcm: bytes) -> None:
                    asyncio.create_task(ws.send_json({"type": "tts_pcm", "data": brain.pcm_b64(pcm)}))

                await brain.stream_tts("Passphrase not recognized. Please try again.", play_pcm2, lambda a: None)
                await set_state(device_id, "listening")
            return

        if not is_wake_word(text):
            return

        await set_state(device_id, "thinking")
        reply, action = await brain.answer(text)
        if action and action.get("action") == "apple_music":
            q = action.get("query", "")
            await send_command(device_id, "apple_music", {"query": q})
        if reply:
            await set_state(device_id, "speaking")

            def play_pcm(pcm: bytes) -> None:
                asyncio.create_task(ws.send_json({"type": "tts_pcm", "data": brain.pcm_b64(pcm)}))

            def amp(a: float) -> None:
                asyncio.create_task(hub.send_browser(device_id, {"type": "amplitude", "amplitude": a}))

            await brain.stream_tts(reply, play_pcm, amp)
        await set_state(device_id, "idle")
        return

    if mtype == "text" and role == "browser":
        # Laptop testing without agent mic
        text = data.get("text", "")
        sess = hub.session(device_id)
        if not sess or not sess.unlocked:
            if brain.check_passphrase(text):
                hub.set_unlocked(device_id, True)
                await ws.send_json({"type": "unlock"})
            return
        if not is_wake_word(text):
            return
        await set_state(device_id, "thinking")
        reply, action = await brain.answer(text)
        if action and action.get("action") == "apple_music":
            await send_command(device_id, "apple_music", {"query": action.get("query", "")})
        await ws.send_json({"type": "reply", "text": reply})
        await set_state(device_id, "idle")


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/ws", ws_handler)
    app.router.add_static("/", WEB_ROOT, show_index=True)
    return app


def main() -> None:
    if not load_config().get("openrouter", {}).get("api_key"):
        log.error("Set OPENROUTER_API_KEY in server/.env or config/config.yaml")
        sys.exit(1)
    web.run_app(create_app(), host=HOST, port=PORT)


if __name__ == "__main__":
    main()
