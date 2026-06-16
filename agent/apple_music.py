"""
Apple Music on Raspberry Pi — what actually works.

Apple does NOT let Python play Apple Music tracks directly (DRM).
On Pi/Linux there is no Apple Music app.

What we CAN do:
  1. Open https://music.apple.com in Chromium (logged-in profile) — agent or browser iframe
  2. Search URL: music.apple.com/us/search?term=...
  3. User taps play in the web UI (first time may need login)
  4. Future: MusicKit JS on cassie.web.app with Apple Developer MusicKit token

This module opens Apple Music in a dedicated Chromium profile so the main Cassie
kiosk tab can stay on the orb.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import urllib.parse

log = logging.getLogger(__name__)

DEFAULT_PROFILE = os.path.expanduser("~/.cassie-apple-music-profile")
CASSIE_URL = os.getenv("CASSIE_URL", "http://127.0.0.1:8780/?device=pi-home")


class AppleMusicController:
    def __init__(self, profile_dir: str = DEFAULT_PROFILE) -> None:
        self.profile_dir = profile_dir
        self._browser = shutil.which("chromium-browser") or shutil.which("chromium") or "chromium"

    def search_url(self, query: str) -> str:
        term = urllib.parse.quote(query.strip())
        return f"https://music.apple.com/us/search?term={term}"

    def play_search(self, query: str) -> None:
        if not query.strip():
            return
        url = self.search_url(query)
        log.info("Opening Apple Music: %s", url)
        subprocess.Popen(
            [
                self._browser,
                f"--user-data-dir={self.profile_dir}",
                "--no-first-run",
                "--start-maximized",
                url,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def return_to_cassie(self) -> None:
        """Close music browser windows and return focus to kiosk (best effort)."""
        subprocess.run(["pkill", "-f", self.profile_dir], check=False)
        subprocess.Popen(
            [
                self._browser,
                "--kiosk",
                "--no-first-run",
                CASSIE_URL,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
