"""HTTP server for Cassie frontend."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from aiohttp import web

log = logging.getLogger(__name__)

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}

TEXT_SUFFIXES = {".html", ".js", ".css", ".json", ".txt"}

# Same orb UI baked in — works even if frontend/ files missing
BUILTIN_INDEX = b"""<!DOCTYPE html><html><head><meta charset=UTF-8><title>Cassie</title>
<style>html,body{margin:0;background:#000;width:100%;height:100%}canvas{position:fixed;inset:0;width:100%;height:100%}</style>
</head><body><canvas id=c></canvas><script>
(function(){var c=document.getElementById('c'),x=c.getContext('2d'),s='idle',a=0,ta=0,t=0;
function R(){c.width=innerWidth||800;c.height=innerHeight||480}addEventListener('resize',R);R();
function D(){t++;a+=(ta-a)*0.2;var w=c.width,h=c.height,cx=w/2,cy=h/2,r=Math.min(w,h)*0.11*(1+a*0.3+Math.sin(t*0.04)*0.04);
x.fillStyle='#000';x.fillRect(0,0,w,h);var g=x.createRadialGradient(cx-r*0.2,cy-r*0.2,r*0.05,cx,cy,r);
g.addColorStop(0,'#fff');g.addColorStop(0.3,'#55aaff');g.addColorStop(1,'#002244');x.fillStyle=g;
x.beginPath();x.arc(cx,cy,r,0,6.28);x.fill();requestAnimationFrame(D)}D();
function W(){try{var w=new WebSocket('ws://127.0.0.1:8765');w.onmessage=function(e){try{var m=JSON.parse(e.data);
if(m.state)s=m.state;if(m.amplitude!=null)ta=m.amplitude;if(m.type==='amplitude')ta=m.amplitude;}catch(z){}};
w.onclose=function(){setTimeout(W,2000)};w.onerror=function(){w.close()}}catch(e){setTimeout(W,2000)}}W();})();
</script></body></html>"""


def _read_body(path: Path) -> bytes:
    raw = path.read_bytes()
    if not raw or path.suffix.lower() not in TEXT_SUFFIXES:
        return raw
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = raw[2:].decode("utf-16-le", errors="replace")
    elif b"\x00" in raw[:200]:
        text = raw.decode("utf-16-le", errors="replace")
    else:
        return raw
    return text.replace("\x00", "").replace("\r\n", "\n").encode("utf-8")


@web.middleware
async def _errors(request: web.Request, handler):
    try:
        return await handler(request)
    except web.HTTPException:
        raise
    except Exception:
        log.exception("HTTP error on %s", request.path)
        return web.Response(status=500, text="Server error", content_type="text/plain")


class HTTPServer:
    def __init__(self, frontend_dir: Path, host: str = "127.0.0.1", port: int = 8766) -> None:
        self.frontend_dir = Path(frontend_dir)
        self.host = host
        self.port = port
        self._runner: web.AppRunner | None = None

    async def start(self) -> None:
        app = web.Application(middlewares=[_errors])
        app.router.add_get("/health", self._health)
        app.router.add_get("/favicon.ico", self._favicon)
        app.router.add_get("/", self._index)
        app.router.add_get("/{name}", self._file)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        for attempt in range(5):
            try:
                await web.TCPSite(self._runner, self.host, self.port).start()
                log.info("HTTP on http://%s:%d", self.host, self.port)
                return
            except OSError as e:
                if attempt >= 4:
                    raise
                log.warning("HTTP port busy, retry %d/5: %s", attempt + 1, e)
                await asyncio.sleep(2)

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
            self._runner = None

    async def _health(self, _req: web.Request) -> web.Response:
        idx = self.frontend_dir / "index.html"
        return web.json_response({
            "ok": True,
            "version": "1.3.0",
            "index": idx.is_file(),
            "files": [p.name for p in self.frontend_dir.glob("*")] if self.frontend_dir.is_dir() else [],
        })

    async def _favicon(self, _req: web.Request) -> web.Response:
        return web.Response(status=204)

    async def _index(self, _req: web.Request) -> web.Response:
        return await self._serve("index.html")

    async def _file(self, req: web.Request) -> web.Response:
        name = req.match_info["name"]
        if not name or ".." in name or "/" in name:
            raise web.HTTPForbidden()
        return await self._serve(name)

    async def _serve(self, name: str) -> web.Response:
        if name == "index.html":
            path = self.frontend_dir / "index.html"
            if path.is_file():
                try:
                    body = _read_body(path)
                    if b"getContext('2d')" in body or b'getContext("2d")' in body:
                        return self._html(body)
                except OSError:
                    log.exception("Read failed: %s", path)
            log.warning("Serving built-in index.html")
            return self._html(BUILTIN_INDEX)

        path = self.frontend_dir / name
        if not path.is_file():
            raise web.HTTPNotFound()
        try:
            body = _read_body(path)
        except OSError:
            log.exception("Read failed: %s", path)
            raise web.HTTPInternalServerError()
        ct = CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")
        return web.Response(body=body, content_type=ct, headers={"Cache-Control": "no-store"})

    def _html(self, body: bytes) -> web.Response:
        return web.Response(
            body=body,
            content_type="text/html; charset=utf-8",
            headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
        )
