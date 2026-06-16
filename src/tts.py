"""Text-to-speech via OpenRouter (gpt-audio-mini)."""
from __future__ import annotations

import base64
import logging
from typing import AsyncIterator, Callable, Optional

from openai import AsyncOpenAI

log = logging.getLogger(__name__)

AmplitudeCallback = Callable[[float], None]


class TextToSpeech:
    def __init__(self, config: dict) -> None:
        or_cfg = config.get("openrouter", {})
        self.api_key: str = or_cfg.get("api_key", "")
        self.model: str = or_cfg.get("tts_model", "openai/gpt-audio-mini")
        self.voice: str = or_cfg.get("tts_voice", "alloy")
        self.sample_rate: int = int(config.get("audio", {}).get("sample_rate", 48000))
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1",
        )

    async def speak(
        self,
        text: str,
        on_chunk: Optional[Callable[[bytes], None]] = None,
        on_amplitude: Optional[AmplitudeCallback] = None,
    ) -> None:
        """Stream TTS audio and invoke on_chunk for each PCM chunk."""
        if not text or not self.api_key:
            return

        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                modalities=["text", "audio"],
                audio={"voice": self.voice, "format": "pcm16"},
                messages=[{"role": "user", "content": text}],
                stream=True,
            )

            async for event in stream:
                if not event.choices:
                    continue
                delta = event.choices[0].delta
                if hasattr(delta, "audio") and delta.audio:
                    audio_data = delta.audio
                    if isinstance(audio_data, dict):
                        b64 = audio_data.get("data", "")
                    else:
                        b64 = getattr(audio_data, "data", "") or ""
                    if b64:
                        pcm = base64.b64decode(b64)
                        if on_chunk:
                            on_chunk(pcm)
                        if on_amplitude and pcm:
                            import struct
                            import math

                            count = len(pcm) // 2
                            if count:
                                samples = struct.unpack(f"<{count}h", pcm[: count * 2])
                                rms = math.sqrt(sum(s * s for s in samples) / count) / 32768.0
                                on_amplitude(min(1.0, rms * 3.0))

        except Exception:
            log.exception("TTS failed for text: %r", text[:80])

    async def synthesize(self, text: str) -> bytes:
        """Return full PCM audio bytes (non-streaming fallback)."""
        chunks: list[bytes] = []

        def collect(chunk: bytes) -> None:
            chunks.append(chunk)

        await self.speak(text, on_chunk=collect)
        return b"".join(chunks)
