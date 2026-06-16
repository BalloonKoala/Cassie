#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/cassie"
CASSIE_USER="${CASSIE_USER:-cassie}"
[[ $EUID -eq 0 ]] || { echo "Run: sudo bash install.sh"; exit 1; }

echo "Installing Cassie to $INSTALL_DIR..."
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip portaudio19-dev \
  libasound2-dev alsa-utils chromium unclutter curl rsync xinit x11-xserver-utils \
  matchbox-window-manager

id "$CASSIE_USER" &>/dev/null || useradd -m -s /bin/bash "$CASSIE_USER"
usermod -aG audio,video,input "$CASSIE_USER"

mkdir -p "$INSTALL_DIR"/{config,data,frontend,src,system,logs}
rsync -a "$SCRIPT_DIR/src/" "$INSTALL_DIR/src/"
rsync -a "$SCRIPT_DIR/frontend/" "$INSTALL_DIR/frontend/"
rsync -a "$SCRIPT_DIR/system/" "$INSTALL_DIR/system/"
cp "$SCRIPT_DIR/requirements.txt" "$SCRIPT_DIR/version.txt" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/patch_config.py" "$SCRIPT_DIR/fix.py" "$INSTALL_DIR/" 2>/dev/null || true

if [[ ! -f "$INSTALL_DIR/config/config.yaml" ]]; then
  cp "$SCRIPT_DIR/config.template.yaml" "$INSTALL_DIR/config/config.yaml"
  echo ">>> Edit $INSTALL_DIR/config/config.yaml and set openrouter.api_key <<<"
fi

python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

python3 "$INSTALL_DIR/patch_config.py" "$INSTALL_DIR/config/config.yaml" 2>/dev/null || true
python3 "$INSTALL_DIR/fix.py" --auto "$INSTALL_DIR" 2>/dev/null || true
chown -R "$CASSIE_USER:$CASSIE_USER" "$INSTALL_DIR"
chmod -R u+rX "$INSTALL_DIR/frontend" "$INSTALL_DIR/src"
bash "$SCRIPT_DIR/system/setup_boot.sh" "$INSTALL_DIR"

systemctl start cassie.service
echo "Install done. Set API key if needed, then: sudo reboot"