#!/bin/sh
# Pi kiosk — opens Cassie website fullscreen (v3)
export DISPLAY=:0
xset s off
xset -dpms
xset s noblank

CASSIE_URL="${CASSIE_URL:-http://127.0.0.1:8780/?device=pi-home&token=change-me}"

# Start agent in background (mic + TTS + Apple Music commands)
/opt/cassie/venv/bin/python3 /opt/cassie/agent/agent.py >>/tmp/cassie-agent.log 2>&1 &

BROWSER=chromium-browser
command -v chromium-browser >/dev/null || BROWSER=chromium

exec "$BROWSER" --kiosk --start-maximized --no-first-run --disk-cache-size=1 "$CASSIE_URL"
