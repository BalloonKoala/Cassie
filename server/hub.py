"""WebSocket hub — routes browser + agent for one device."""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class DeviceSession:
    device_id: str
    browser: Any | None = None
    agent: Any | None = None
    unlocked: bool = False


class Hub:
    def __init__(self) -> None:
        self._devices: dict[str, DeviceSession] = {}
        self._lock = asyncio.Lock()

    async def register(self, device_id: str, role: str, ws) -> DeviceSession:
        async with self._lock:
            sess = self._devices.setdefault(device_id, DeviceSession(device_id))
            if role == "browser":
                sess.browser = ws
            elif role == "agent":
                sess.agent = ws
            log.info("Registered %s for %s", role, device_id)
            return sess

    async def unregister(self, device_id: str, role: str, ws) -> None:
        async with self._lock:
            sess = self._devices.get(device_id)
            if not sess:
                return
            if role == "browser" and sess.browser is ws:
                sess.browser = None
            if role == "agent" and sess.agent is ws:
                sess.agent = None
            if not sess.browser and not sess.agent:
                del self._devices[device_id]

    async def send_browser(self, device_id: str, msg: dict) -> None:
        sess = self._devices.get(device_id)
        if sess and sess.browser:
            await sess.browser.send(json.dumps(msg))

    async def send_agent(self, device_id: str, msg: dict) -> None:
        sess = self._devices.get(device_id)
        if sess and sess.agent:
            await sess.agent.send(json.dumps(msg))

    async def broadcast(self, device_id: str, msg: dict) -> None:
        await self.send_browser(device_id, msg)
        await self.send_agent(device_id, msg)

    def session(self, device_id: str) -> DeviceSession | None:
        return self._devices.get(device_id)

    def set_unlocked(self, device_id: str, unlocked: bool) -> None:
        sess = self._devices.get(device_id)
        if sess:
            sess.unlocked = unlocked
