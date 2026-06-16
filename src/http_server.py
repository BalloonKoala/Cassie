"""Simple async HTTP server for the Cassie frontend."""
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
    ".svg": "image/svg+xml",
    ".json": "application/json; charset=utf-8",
}

TEXT_SUFFIXES = {".html", ".js", ".css", ".json", ".txt", ".svg"}


def _resolve_frontend_root(frontend_dir: Path) -> Path:
    """Resolve frontend directory path (works on Linux/Pi and Windows)."""
    try:
        return frontend_dir.expanduser().resolve(strict=False)
    except OSError as exc:
        log.warning("Could not resolve frontend dir %s: %s", frontend_dir, exc)
        return frontend_dir.expanduser().absolute()


def _is_safe_path(root: Path, candidate: Path) -> bool:
    """Return True if candidate is inside root (symlink-safe on Linux/Pi)."""
    try:
        root_resolved = root.resolve(strict=False)
        cand_resolved = candidate.resolve(strict=False)
        cand_resolved.relative_to(root_resolved)
        return True
    except ValueError:
        pass
    except OSError:
        pass
    try:
        common = os.path.commonpath(
            [str(root.resolve(strict=False)), str(candidate.resolve(strict=False))]
        )
        return common == str(root.resolve(strict=False))
    except (ValueError, OSError):
        return False


def _read_file_body(file_path: Path) -> bytes:
    """Read file bytes; normalize text files to UTF-8 (handles UTF-16 BOM/null bytes)."""
    raw = file_path.read_bytes()
    if not raw:
        return raw

    suffix = file_path.suffix.lower()
    if suffix not in TEXT_SUFFIXES:
        return raw

    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        try:
            text = raw.decode("utf-16")
        except UnicodeDecodeError:
            text = raw.decode("utf-16-le", errors="replace")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        if "\x00" in text:
            text = text.replace("\x00", "")
        return text.encode("utf-8")

    if b"\x00" in raw:
        text = raw.replace(b"\x00", b"").decode("utf-8", errors="replace")
        return text.encode("utf-8")

    return raw


class HTTPServer:
    def __init__(self, frontend_dir: Path, host: str = "127.0.0.1", port: int = 8766) -> None:
        self.frontend_dir = _resolve_frontend_root(Path(frontend_dir))
        self.host = host
        self.port = port
        self._runner: web.AppRunner | None = None

        if not self.frontend_dir.is_dir():
            log.warning("Frontend directory missing: %s", self.frontend_dir)
        else:
            log.info("Frontend root: %s", self.frontend_dir)

    async def start(self) -> None:
        app = web.Application()
        app.middlewares.append(self._error_middleware)
        app.router.add_get("/health", self._health)
        app.router.add_get("/", self._index)
        app.router.add_get("/{path:.*}", self._static)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.host, self.port)
        await site.start()
        log.info("HTTP server on http://%s:%d", self.host, self.port)

    @web.middleware
    async def _error_middleware(self, request: web.Request, handler):
        try:
            return await handler(request)
        except web.HTTPException:
            raise
        except Exception:
            log.exception("Unhandled error serving %s", request.path)
            return web.Response(
                status=500,
                text="Internal Server Error",
                content_type="text/plain; charset=utf-8",
            )

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
            self._runner = None

    async def _health(self, _request: web.Request) -> web.Response:
        index = self.frontend_dir / "index.html"
        return web.json_response(
            {
                "ok": self.frontend_dir.is_dir() and index.is_file(),
                "frontend_dir": str(self.frontend_dir),
                "frontend_exists": self.frontend_dir.is_dir(),
                "index_exists": index.is_file(),
            }
        )

    async def _index(self, _request: web.Request) -> web.Response:
        return await self._serve_file("index.html")

    async def _static(self, request: web.Request) -> web.Response:
        path = request.match_info["path"] or ""
        path = path.replace("\\", "/").lstrip("/")
        if ".." in path.split("/"):
            raise web.HTTPForbidden(reason="Path traversal denied")
        return await self._serve_file(path)

    async def _serve_file(self, rel_path: str) -> web.Response:
        rel_path = (rel_path or "index.html").replace("\\", "/").lstrip("/")
        if not rel_path:
            rel_path = "index.html"

        if not self.frontend_dir.is_dir():
            log.error("Frontend directory not found: %s", self.frontend_dir)
            raise web.HTTPNotFound(text="Frontend not installed")

        try:
            file_path = (self.frontend_dir / rel_path).resolve(strict=False)
        except OSError as exc:
            log.error("Path resolve failed for %r: %s", rel_path, exc)
            raise web.HTTPNotFound() from exc

        if not _is_safe_path(self.frontend_dir, file_path):
            log.warning("Forbidden path request: %s -> %s", rel_path, file_path)
            raise web.HTTPForbidden(reason="Outside frontend root")

        if not file_path.is_file():
            log.warning("File not found: %s (requested as %r)", file_path, rel_path)
            raise web.HTTPNotFound()

        try:
            body = _read_file_body(file_path)
        except PermissionError:
            log.exception("Permission denied reading %s", file_path)
            raise web.HTTPForbidden(reason="Cannot read file") from None
        except OSError:
            log.exception("Failed to read %s", file_path)
            raise web.HTTPInternalServerError(text="Failed to read file") from None

        suffix = file_path.suffix.lower()
        content_type = CONTENT_TYPES.get(suffix, "application/octet-stream")
        return web.Response(body=body, content_type=content_type)