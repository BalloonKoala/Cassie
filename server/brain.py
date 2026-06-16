"""Voice AI + intent routing for Cassie v3."""
from __future__ import annotations

import base64
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from llm import LLMEngine
from stt import SpeechToText
from tts import TextToSpeech
from wake_utils import extract_command, is_wake_word

log = logging.getLogger(__name__)

MUSIC_PROMPT = (
    "If the user asks to play music on Apple Music, reply briefly AND append on its own line: "
    '{"action":"apple_music","query":"search terms"}'
)


def normalize_passphrase(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def greeting(name: str) -> str:
    h = datetime.now().hour
    if h < 12:
        part = "Good morning"
    elif h < 17:
        part = "Good afternoon"
    else:
        part = "Good evening"
    return f"{part}, {name}."


class Brain:
    def __init__(self, config: dict, owner: str, passphrase: str) -> None:
        self.owner = owner
        self.passphrase_norm = normalize_passphrase(passphrase)
        self.stt = SpeechToText(config)
        self.llm = LLMEngine(config)
        self.tts = TextToSpeech(config)
        self._memories: list[str] = []

    async def transcribe_pcm(self, pcm: bytes) -> str:
        return await self.stt.transcribe(pcm)

    def check_passphrase(self, text: str) -> bool:
        return self.passphrase_norm in normalize_passphrase(text) or normalize_passphrase(text) in self.passphrase_norm

    async def unlock_lines(self) -> str:
        return (
            f"{greeting(self.owner)} Please say the passphrase."
        )

    async def access_granted_line(self) -> str:
        return "Access granted. How can I help you?"

    def _parse_action(self, reply: str) -> tuple[str, dict | None]:
        m = re.search(r'\{"action"\s*:\s*"apple_music"[^}]+\}', reply)
        if not m:
            return reply, None
        try:
            action = json.loads(m.group(0))
            clean = reply[: m.start()].strip() or "Playing that on Apple Music."
            return clean, action
        except json.JSONDecodeError:
            return reply, None

    async def answer(self, user_text: str) -> tuple[str, dict | None]:
        if not user_text.strip():
            return "", None
        cmd = extract_command(user_text) if is_wake_word(user_text) else user_text
        if not cmd.strip():
            return "Yes?", None
        reply, facts = await self.llm.chat(cmd + "\n\n" + MUSIC_PROMPT, self._memories)
        if facts:
            self._memories.extend(facts)
        return self._parse_action(reply)

    async def stream_tts(
        self,
        text: str,
        on_pcm,
        on_amp,
    ) -> None:
        await self.tts.speak(text, on_chunk=on_pcm, on_amplitude=on_amp)

    @staticmethod
    def pcm_b64(pcm: bytes) -> str:
        return base64.b64encode(pcm).decode("ascii")
