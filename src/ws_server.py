"""WebSocket server for frontend state and amplitude."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Set

import websockets

log = logging.getLogger(__name__)


class WSServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self._clients: Set[Any] = set()
        self._server = None
        self._current_state = "idle"
        self._amplitude = 0.0

    async def start(self) -> None:
        for attempt in range(5):
            try:
                self._server = await websockets.serve(
                    self._handler,
                    self.host,
                    self.port,
                    ping_interval=20,
                    ping_timeout=20,
                )
                log.info("WebSocket server on ws://%s:%d", self.host, self.port)
                return
            except OSError as e:
                if attempt >= 4:
                    raise
                log.warning("WS port busy, retry %d/5: %s", attempt + 1, e)
                await asyncio.sleep(2)

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        for ws in list(self._clients):
            await ws.close()
        self._clients.clear()

    async def _handler(self, ws) -> None:
        self._clients.add(ws)
        log.debug("WS client connected (%d total)", len(self._clients))
        try:
            await ws.send(
                json.dumps(
                    {
                        "type": "state",
                        "state": self._current_state,
                        "amplitude": self._amplitude,
                    }
                )
            )
            async for _message in ws:
                pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self._clients.discard(ws)

    async def _broadcast(self, payload: dict[str, Any]) -> None:
        if not self._clients:
            return
        msg = json.dumps(payload)
        dead: list = []
        for ws in self._clients:
            try:
                await ws.send(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._clients.discard(ws)

    async def send_state(self, state: str) -> None:
        self._current_state = state
        await self._broadcast({"type": "state", "state": state})

    async def send_amplitude(self, amplitude: float) -> None:
        self._amplitude = amplitude
        await self._broadcast({"type": "amplitude", "amplitude": amplitude})
