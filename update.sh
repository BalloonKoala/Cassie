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
log "Updating $OLD -> $NEW (single-process mode)"

[[ -f "$SCRIPT_DIR/fix.py" ]] && python3 "$SCRIPT_DIR/fix.py" --auto "$SCRIPT_DIR" || true
systemctl stop cassie.service 2>/dev/null || true
pkill -u "$CASSIE_USER" -f "$INSTALL_DIR/src/run.py" 2>/dev/null || true
sleep 2

rsync -a --delete "$SCRIPT_DIR/src/" "$INSTALL_DIR/src/"
rsync -a "$SCRIPT_DIR/system/" "$INSTALL_DIR/system/"
cp "$SCRIPT_DIR/requirements.txt" "$SCRIPT_DIR/version.txt" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/patch_config.py" "$INSTALL_DIR/" 2>/dev/null || true
cp "$SCRIPT_DIR/fix.py" "$INSTALL_DIR/" 2>/dev/null || true

sudo -u "$CASSIE_USER" "$INSTALL_DIR/venv/bin/pip" install -q -r "$INSTALL_DIR/requirements.txt" || true
for f in "$INSTALL_DIR/src"/*.py; do "$INSTALL_DIR/venv/bin/python3" -m py_compile "$f"; done

python3 "$INSTALL_DIR/patch_config.py" "$INSTALL_DIR/config/config.yaml" 2>/dev/null || true
python3 "$INSTALL_DIR/fix.py" --auto "$INSTALL_DIR" 2>/dev/null || true
bash "$INSTALL_DIR/system/setup_boot.sh" "$INSTALL_DIR"
chown -R "$CASSIE_USER:$CASSIE_USER" "$INSTALL_DIR"

systemctl disable cassie.service 2>/dev/null || true
test -f "$INSTALL_DIR/src/run.py" || die "Missing run.py"

log "Updated to $NEW"
echo ""
echo "Reboot to apply:  sudo reboot"
echo "Cassie 2.0 = one Python app, no browser, no systemctl start."
