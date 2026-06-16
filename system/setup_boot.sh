#!/usr/bin/env bash
# Enable Cassie auto-start on boot (backend + screen). Called by install/update.
set -euo pipefail
INSTALL_DIR="${1:-/opt/cassie}"
CASSIE_USER="${CASSIE_USER:-cassie}"
HOME_DIR="/home/$CASSIE_USER"

mkdir -p /etc/systemd/system/getty@tty1.service.d
cp "$INSTALL_DIR/system/getty-autologin.conf" /etc/systemd/system/getty@tty1.service.d/autologin.conf

cp "$INSTALL_DIR/system/xinitrc" "$HOME_DIR/.xinitrc"
chmod 755 "$HOME_DIR/.xinitrc"
chmod 755 "$INSTALL_DIR/system/keep-awake.sh" 2>/dev/null || true

# Disable Linux console screen blank (often ~5 min white/black)
if [[ -f /etc/kbd/config ]]; then
  sed -i 's/^BLANK_TIME=.*/BLANK_TIME=0/' /etc/kbd/config 2>/dev/null || true
  sed -i 's/^POWERDOWN_TIME=.*/POWERDOWN_TIME=0/' /etc/kbd/config 2>/dev/null || true
  grep -q '^BLANK_TIME=' /etc/kbd/config || echo 'BLANK_TIME=0' >> /etc/kbd/config
  grep -q '^POWERDOWN_TIME=' /etc/kbd/config || echo 'POWERDOWN_TIME=0' >> /etc/kbd/config
fi

cp "$INSTALL_DIR/system/bash_profile" "$HOME_DIR/.bash_profile"
chmod 644 "$HOME_DIR/.bash_profile"

if [[ -f "$INSTALL_DIR/config/config.yaml" ]]; then
  python3 "$INSTALL_DIR/patch_config.py" "$INSTALL_DIR/config/config.yaml" 2>/dev/null || \
    python3 "$(dirname "$INSTALL_DIR")/cassie/patch_config.py" "$INSTALL_DIR/config/config.yaml" 2>/dev/null || true
fi

cp "$INSTALL_DIR/system/cassie.service" /etc/systemd/system/cassie.service
systemctl daemon-reload
systemctl enable cassie.service
systemctl enable getty@tty1.service

chown -R "$CASSIE_USER:$CASSIE_USER" "$INSTALL_DIR"
chown "$CASSIE_USER:$CASSIE_USER" "$HOME_DIR/.xinitrc" "$HOME_DIR/.bash_profile"