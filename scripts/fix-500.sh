#!/usr/bin/env bash
# Fix Cassie 500 error on Pi — run: sudo bash scripts/fix-500.sh
set -euo pipefail
INSTALL=/opt/cassie
USER=cassie

echo "=== Fix permissions ==="
chown -R "$USER:$USER" "$INSTALL"
chmod -R u+rX "$INSTALL/frontend" "$INSTALL/src"

echo "=== Fix line endings in scripts ==="
find "$INSTALL" -name "*.sh" -exec sed -i 's/\r$//' {} + 2>/dev/null || true

echo "=== Fix UTF-16 files ==="
if [[ -f "$INSTALL/fix.py" ]]; then
  python3 "$INSTALL/fix.py" --auto "$INSTALL" || true
fi

echo "=== Verify frontend ==="
ls -la "$INSTALL/frontend/"
test -f "$INSTALL/frontend/index.html" || { echo "MISSING index.html!"; exit 1; }

echo "=== Compile check ==="
for f in "$INSTALL/src"/*.py; do
  "$INSTALL/venv/bin/python3" -m py_compile "$f"
done

echo "=== Restart ==="
systemctl restart cassie.service
sleep 4

echo "=== Test ==="
curl -s "http://127.0.0.1:8766/health" || true
echo ""
curl -s -o /dev/null -w "GET / -> HTTP %{http_code}\n" "http://127.0.0.1:8766/"
journalctl -u cassie -n 15 --no-pager
