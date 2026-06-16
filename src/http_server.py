"""HTTP server for Cassie frontend — robust on Pi (no 500 from bad paths/perms)."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from aiohttp import web

log = logging.getLogger(__name__)

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".png": "image/png",
    ".ico": "image/x-icon",
}

TEXT_SUFFIXES = {".html", ".js", ".css", ".json", ".txt"}


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


FALLBACK_HTML = b"""<!DOCTYPE html><html><head><meta charset=utf-8><title>Cassie</title>
<style>*{margin:0}html,body{background:#000;height:100%}#canvas{position:fixed;inset:0;width:100%;height:100%;background:#000}</style>
</head><body><canvas id=canvas></canvas>
<script src=kiosk_boot.js></script><script src=mic_border.js></script><script src=sphere.js></script><script src=ws_client.js></script>
</body></html>"""


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
        log.info("Frontend dir: %s (exists=%s)", self.frontend_dir, self.frontend_dir.is_dir())

    async def start(self) -> None:
        app = web.Application(middlewares=[_errors])
        app.router.add_get("/health", self._health)
        app.router.add_get("/favicon.ico", self._favicon)
        app.router.add_get("/", self._index)
        app.router.add_get("/{name}", self._file)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        await web.TCPSite(self._runner, self.host, self.port).start()
        log.info("HTTP on http://%s:%d", self.host, self.port)

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
            self._runner = None

    async def _health(self, _req: web.Request) -> web.Response:
        idx = self.frontend_dir / "index.html"
        return web.json_response({
            "ok": idx.is_file(),
            "frontend": str(self.frontend_dir),
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
        if not self.frontend_dir.is_dir():
            log.error("No frontend dir: %s", self.frontend_dir)
            if name == "index.html":
                return web.Response(body=FALLBACK_HTML, content_type="text/html; charset=utf-8")
            raise web.HTTPNotFound()

        path = self.frontend_dir / name
        if not path.is_file():
            log.warning("Missing file: %s", path)
            if name == "index.html":
                return web.Response(body=FALLBACK_HTML, content_type="text/html; charset=utf-8")
            raise web.HTTPNotFound()

        try:
            body = _read_body(path)
        except PermissionError:
            log.exception("Permission denied: %s", path)
            if name == "index.html":
                return web.Response(body=FALLBACK_HTML, content_type="text/html; charset=utf-8")
            raise web.HTTPForbidden()
        except OSError:
            log.exception("Read failed: %s", path)
            raise web.HTTPInternalServerError()

        ct = CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")
        return web.Response(body=body, content_type=ct)
