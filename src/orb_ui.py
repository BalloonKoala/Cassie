"""Pygame orb UI — no browser, no HTTP, no WebSocket."""
from __future__ import annotations

import math
import threading

import pygame

COLORS = {
    "idle": (55, 140, 255),
    "listening": (45, 200, 110),
    "thinking": (255, 170, 45),
    "speaking": (210, 90, 255),
}


class OrbUI:
    def __init__(self) -> None:
        pygame.init()
        pygame.mouse.set_visible(False)
        info = pygame.display.Info()
        self.w = max(info.current_w, 640)
        self.h = max(info.current_h, 480)
        self.screen = pygame.display.set_mode((self.w, self.h), pygame.FULLSCREEN)
        pygame.display.set_caption("Cassie")
        self.clock = pygame.time.Clock()
        self._lock = threading.Lock()
        self.state = "idle"
        self.amp = 0.0
        self.target_amp = 0.0
        self.t = 0.0

    def set_state(self, state: str) -> None:
        with self._lock:
            self.state = state or "idle"

    def set_amplitude(self, amp: float) -> None:
        with self._lock:
            self.target_amp = max(0.0, min(1.0, float(amp)))

    def run_forever(self) -> None:
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False

            with self._lock:
                state = self.state
                self.amp += (self.target_amp - self.amp) * 0.2

            self.t += 1.0
            self._draw(state)
            pygame.display.flip()
            self.clock.tick(30)
        pygame.quit()

    def _draw(self, state: str) -> None:
        w, h = self.w, self.h
        cx, cy = w // 2, h // 2
        rgb = COLORS.get(state, COLORS["idle"])
        pulse = 1.0 + self.amp * 0.35 + math.sin(self.t * 0.04) * 0.04
        if state == "thinking":
            pulse += math.sin(self.t * 0.08) * 0.06
        if state == "speaking":
            pulse += math.sin(self.t * 0.12) * 0.1
        r = int(min(w, h) * 0.11 * pulse)

        self.screen.fill((0, 0, 0))

        glow = pygame.Surface((w, h), pygame.SRCALPHA)
        for i in range(3, 0, -1):
            gr = r * (1.5 + i * 0.6)
            alpha = 25 + int(self.amp * 40) - i * 5
            pygame.draw.circle(glow, (*rgb, max(0, alpha)), (cx, cy), int(gr))
        self.screen.blit(glow, (0, 0))

        pygame.draw.circle(self.screen, rgb, (cx, cy), r)
        highlight = tuple(min(255, c + 80) for c in rgb)
        pygame.draw.circle(self.screen, highlight, (cx - r // 3, cy - r // 3), max(4, r // 5))

        border = 3 + int(self.amp * 12)
        gray = int(160 + self.amp * 80)
        pygame.draw.rect(self.screen, (gray, gray, gray), (border, border, w - border * 2, h - border * 2), border)
