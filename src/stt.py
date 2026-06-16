"""Speech-to-text via OpenRouter (Whisper)."""
from __future__ import annotations

import io
import logging
import wave
from typing import Optional

import httpx

log = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/audio/transcriptions"


class SpeechToText:
    def __init__(self, config: dict) -> None:
        or_cfg = config.get("openrouter", {})
        self.api_key: str = or_cfg.get("api_key", "")
        self.model: str = or_cfg.get("stt_model", "openai/whisper-large-v3-turbo")
        self.sample_rate: int = int(config.get("audio", {}).get("sample_rate", 48000))

    def _pcm_to_wav(self, pcm: bytes) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm)
        return buf.getvalue()

    async def transcribe(self, pcm: bytes) -> str:
        if not pcm:
            return ""
        if not self.api_key:
            log.error("OpenRouter API key not configured for STT")
            return ""

        wav_data = self._pcm_to_wav(pcm)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://cassie.local",
            "X-Title": "Cassie Assistant",
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    OPENROUTER_URL,
                    headers=headers,
                    files={"file": ("audio.wav", wav_data, "audio/wav")},
                    data={"model": self.model},
                )
                resp.raise_for_status()
                data = resp.json()
                text = data.get("text", "").strip()
                log.info("STT: %r", text)
                return text
        except Exception:
            log.exception("STT transcription failed")
            return ""

    async def transcribe_sync_pcm(self, pcm: bytes) -> str:
        """Alias for transcribe (async)."""
        return await self.transcribe(pcm)
