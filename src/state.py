"""Cassie state machine — IDLE / LISTENING / THINKING / SPEAKING."""
from __future__ import annotations

import asyncio
import logging
from enum import Enum, auto
from typing import Awaitable, Callable

log = logging.getLogger(__name__)

StateChangeCallback = Callable[["State", "State"], Awaitable[None]]


class State(Enum):
    IDLE = auto()
    LISTENING = auto()
    THINKING = auto()
    SPEAKING = auto()


class StateMachine:
    """Thread-safe async state machine with observer callbacks."""

    def __init__(self) -> None:
        self._state = State.IDLE
        self._lock = asyncio.Lock()
        self._callbacks: list[StateChangeCallback] = []

    @property
    def state(self) -> State:
        return self._state

    def add_callback(self, cb: StateChangeCallback) -> None:
        self._callbacks.append(cb)

    async def transition(self, new_state: State) -> bool:
        async with self._lock:
            if self._state is new_state:
                return False
            old_state = self._state
            self._state = new_state
            log.info("State: %s -> %s", old_state.name, new_state.name)

        for cb in self._callbacks:
            try:
                await cb(old_state, new_state)
            except Exception:
                log.exception("State callback raised an exception")

        return True

    async def set_idle(self) -> None:
        await self.transition(State.IDLE)

    async def set_listening(self) -> None:
        await self.transition(State.LISTENING)

    async def set_thinking(self) -> None:
        await self.transition(State.THINKING)

    async def set_speaking(self) -> None:
        await self.transition(State.SPEAKING)

    def is_idle(self) -> bool:
        return self._state is State.IDLE

    def is_listening(self) -> bool:
        return self._state is State.LISTENING

    def is_thinking(self) -> bool:
        return self._state is State.THINKING

    def is_speaking(self) -> bool:
        return self._state is State.SPEAKING
