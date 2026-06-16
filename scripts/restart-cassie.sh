#!/usr/bin/env bash
# Clean restart after manual stop — frees ports and stale Python processes.
set -euo pipefail
INSTALL=/opt/cassie
USER=cassie

echo "Stopping cassie..."
systemctl stop cassie.service 2>/dev/null || true
sleep 2

echo "Killing stale Cassie processes..."
pkill -u "$USER" -f "$INSTALL/venv/bin/python3" 2>/dev/null || true
pkill -u "$USER" -f "$INSTALL/src/main.py" 2>/dev/null || true
sleep 1

echo "Freeing ports 8765 and 8766..."
fuser -k 8765/tcp 2>/dev/null || true
fuser -k 8766/tcp 2>/dev/null || true
sleep 1

systemctl daemon-reload
systemctl start cassie.service
sleep 5

if systemctl is-active --quiet cassie.service; then
  echo "OK: cassie.service is running"
  curl -sf http://127.0.0.1:8766/health && echo ""
else
  echo "FAILED — last log lines:"
  journalctl -u cassie -n 25 --no-pager
  exit 1
fi
