#!/usr/bin/env bash
# Remove all Cassie installs and kiosk leftovers, then reinstall from git.
# Run on Pi:  sudo bash scripts/fresh-pi.sh
# After wipe: git clone ... && sudo bash install.sh && sudo reboot
set -euo pipefail

CASSIE_USER="${CASSIE_USER:-cassie}"
HOME_DIR="/home/$CASSIE_USER"
INSTALL="/opt/cassie"
BACKUP="$HOME_DIR/cassie-config-backup.yaml"
GIT_DIR="$HOME_DIR/cassie-git"

[[ $EUID -eq 0 ]] || { echo "Run: sudo bash scripts/fresh-pi.sh"; exit 1; }

echo "=== Cassie fresh wipe (keeps Raspberry Pi OS, removes old Cassie) ==="

if [[ -f "$INSTALL/config/config.yaml" ]]; then
  cp "$INSTALL/config/config.yaml" "$BACKUP"
  echo "Saved API config -> $BACKUP"
elif [[ -f "$BACKUP" ]]; then
  echo "Keeping existing backup: $BACKUP"
fi

echo "=== Stop services ==="
systemctl stop cassie.service 2>/dev/null || true
systemctl disable cassie.service 2>/dev/null || true

echo "=== Kill kiosk / X ==="
pkill -u "$CASSIE_USER" -f chromium 2>/dev/null || true
pkill -u "$CASSIE_USER" -f startx 2>/dev/null || true
sleep 2

echo "=== Remove install dirs ==="
rm -rf "$INSTALL"
rm -rf "$GIT_DIR"
rm -rf "$HOME_DIR/cassie" "$HOME_DIR/cassie-usb" 2>/dev/null || true
rm -rf /media/"$CASSIE_USER"/cassie-usb /media/"$CASSIE_USER"/usb 2>/dev/null || true

echo "=== Clear Chromium cache (old broken UI) ==="
rm -rf "$HOME_DIR/.config/chromium" "$HOME_DIR/.cache/chromium" 2>/dev/null || true
rm -f /tmp/cassie-startx.log 2>/dev/null || true

echo "=== Remove old boot hooks (reinstall puts them back) ==="
rm -f /etc/systemd/system/getty@tty1.service.d/autologin.conf 2>/dev/null || true
rm -f /etc/systemd/system/cassie.service 2>/dev/null || true
systemctl daemon-reload

echo ""
echo "=== Wipe complete ==="
echo ""
echo "Next commands (as user cassie, not root):"
echo "  git clone https://github.com/BalloonKoala/Cassie.git $GIT_DIR"
echo "  cd $GIT_DIR"
echo "  sudo bash install.sh"
if [[ -f "$BACKUP" ]]; then
  echo "  sudo cp $BACKUP $INSTALL/config/config.yaml"
  echo "  sudo chown cassie:cassie $INSTALL/config/config.yaml"
fi
echo "  sudo bash scripts/fix-500.sh"
echo "  sudo reboot"
echo ""
