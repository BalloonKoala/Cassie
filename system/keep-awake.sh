#!/bin/sh
# Keep Pi display awake — run in background from .xinitrc
export DISPLAY=:0
while true; do
  xset s off 2>/dev/null
  xset -dpms 2>/dev/null
  xset s noblank 2>/dev/null
  xsetroot -solid '#000000' 2>/dev/null
  sleep 30
done
