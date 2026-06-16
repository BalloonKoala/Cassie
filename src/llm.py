"""LLM via OpenRouter."""
from __future__ import annotations
import json, logging, re
from typing import Any
from openai import AsyncOpenAI
log = logging.getLogger(__name__)
SYSTEM = "You are Cassie, a friendly voice assistant. Keep replies concise (1-3 sentences) for speech. If the user shares personal facts, end with JSON: {\"remember\": [\"fact\"]}. Only when there are new facts."
class LLMEngine:
    def __init__(self, config):
        o = config.get("openrouter", {})
        self.api_key = o.get("api_key", "")
        self.model = o.get("llm_model", "google/gemma-4-26b-a4b-it")
        self.client = AsyncOpenAI(api_key=self.api_key, base_url="https://openrouter.ai/api/v1")
    async def chat(self, user_text, memories, history=None):
        if not user_text.strip(): return "", []
        if not self.api_key: return "I need an API key configured.", []
        msgs = [{"role":"system","content":SYSTEM}]
        if memories: msgs.append({"role":"system","content":"Known facts:\n"+"\n".join(f"- {m}" for m in memories)})
        if history: msgs.extend(history[-6:])
        msgs.append({"role":"user","content":user_text})
        try:
            r = await self.client.chat.completions.create(model=self.model, messages=msgs, temperature=0.7, max_tokens=300)
            raw = (r.choices[0].message.content or "").strip()
            reply, facts = self._parse(raw); log.info("LLM: %r", reply[:80]); return reply, facts
        except Exception:
            log.exception("LLM failed"); return "Sorry, I had trouble thinking of a response.", []
    @staticmethod
    def _parse(raw):
        facts = []; text = raw
        m = re.search(r'\{[^{}]*"remember"\s*:\s*\[[^\]]*\][^{}]*\}', raw, re.DOTALL)
        if m:
            try:
                d = json.loads(m.group(0)); remember = d.get("remember", [])
                if isinstance(remember, list): facts = [str(x).strip() for x in remember if str(x).strip()]
            except json.JSONDecodeError: pass
            text = raw[:m.start()].strip()
        return text or raw, facts