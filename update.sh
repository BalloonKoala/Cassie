#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/cassie"
CASSIE_USER="${CASSIE_USER:-cassie}"
log(){ echo "[cassie-update] $*"; }
die(){ echo "[cassie-update] ERROR: $*" >&2; exit 1; }
[[ $EUID -eq 0 ]] || die "Run: sudo bash update.sh"

OLD="$(tr -d '\r\n' < "$INSTALL_DIR/version.txt" 2>/dev/null || echo 0)"
NEW="$(tr -d '\r\n' < "$SCRIPT_DIR/version.txt" 2>/dev/null || echo 0)"
log "Updating $OLD -> $NEW"

[[ -f "$SCRIPT_DIR/fix.py" ]] && python3 "$SCRIPT_DIR/fix.py" --auto "$SCRIPT_DIR" || true
systemctl stop cassie.service 2>/dev/null || true
sleep 2

rsync -a --delete "$SCRIPT_DIR/src/" "$INSTALL_DIR/src/"
rsync -a --delete "$SCRIPT_DIR/frontend/" "$INSTALL_DIR/frontend/"
rsync -a "$SCRIPT_DIR/system/" "$INSTALL_DIR/system/"
cp "$SCRIPT_DIR/requirements.txt" "$SCRIPT_DIR/version.txt" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/patch_config.py" "$INSTALL_DIR/"

if [[ ! -f "$INSTALL_DIR/config/config.yaml" ]]; then
  mkdir -p "$INSTALL_DIR/config"
  cp "$SCRIPT_DIR/config.template.yaml" "$INSTALL_DIR/config/config.yaml"
fi

sudo -u "$CASSIE_USER" "$INSTALL_DIR/venv/bin/pip" install -q -r "$INSTALL_DIR/requirements.txt" || true
for f in "$INSTALL_DIR/src"/*.py; do "$INSTALL_DIR/venv/bin/python3" -m py_compile "$f"; done

python3 "$INSTALL_DIR/patch_config.py" "$INSTALL_DIR/config/config.yaml"
bash "$INSTALL_DIR/system/setup_boot.sh" "$INSTALL_DIR"

# Fix permissions + encoding on Pi (common cause of HTTP 500)
python3 "$INSTALL_DIR/fix.py" --auto "$INSTALL_DIR" 2>/dev/null || true
find "$INSTALL_DIR" -name "*.sh" -exec sed -i 's/\r$//' {} + 2>/dev/null || true
chown -R "$CASSIE_USER:$CASSIE_USER" "$INSTALL_DIR"
chmod -R u+rX "$INSTALL_DIR/frontend" "$INSTALL_DIR/src"

systemctl restart cassie.service
sleep 4
systemctl is-active --quiet cassie.service && log "Backend running ($NEW)" || die "journalctl -u cassie -n 30"

echo ""
echo "Done. Reboot once:  sudo reboot"
echo "After that Cassie starts by itself every boot — no manual start/restart."