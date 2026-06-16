"""Wait until the Pi can reach the internet (for OpenRouter)."""
from __future__ import annotations
import asyncio
import logging
import httpx
log = logging.getLogger(__name__)
URLS = ("https://openrouter.ai/api/v1/models", "https://www.google.com/generate_204")

async def wait_for_internet(timeout: float = 120.0, interval: float = 3.0) -> bool:
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    n = 0
    while loop.time() < deadline:
        n += 1
        for url in URLS:
            try:
                async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as c:
                    r = await c.get(url)
                    if r.status_code < 500:
                        log.info("Internet ready (%s)", url)
                        return True
            except Exception:
                pass
        log.info("Waiting for internet... (%d)", n)
        await asyncio.sleep(interval)
    log.error("No internet after %.0fs", timeout)
    return False