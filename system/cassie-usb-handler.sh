#!/usr/bin/env bash
# Cassie USB Deployment Handler
# Called by systemd when a USB block device is inserted.
# Usage: cassie-usb-handler.sh <device_name>  (e.g. sda1)

set -euo pipefail

DEVICE="${1:-}"
MOUNT_POINT="/mnt/cassie-usb"
INSTALL_DIR="/opt/cassie"
LOG_TAG="cassie-usb"

log() { logger -t "$LOG_TAG" "$*"; echo "[cassie-usb] $*"; }
die() { log "ERROR: $*"; exit 1; }

# ─── Validate device ─────────────────────────────────────────────────────────
[[ -z "$DEVICE" ]] && die "No device argument provided."
DEV_PATH="/dev/$DEVICE"
[[ -b "$DEV_PATH" ]] || die "Device $DEV_PATH is not a block device."

log "USB device detected: $DEV_PATH"

# ─── Wait briefly for the filesystem to settle ───────────────────────────────
sleep 2

# ─── Mount the USB drive ─────────────────────────────────────────────────────
mkdir -p "$MOUNT_POINT"

# Unmount if already mounted (previous run)
if mountpoint -q "$MOUNT_POINT"; then
    umount "$MOUNT_POINT" || true
fi

mount -o ro "$DEV_PATH" "$MOUNT_POINT" || die "Failed to mount $DEV_PATH at $MOUNT_POINT"
log "Mounted $DEV_PATH at $MOUNT_POINT"

# ─── Check for cassie folder ─────────────────────────────────────────────────
USB_CASSIE_DIR="$MOUNT_POINT/cassie"
if [[ ! -d "$USB_CASSIE_DIR" ]]; then
    log "No 'cassie' folder found on USB drive. Nothing to do."
    umount "$MOUNT_POINT" || true
    exit 0
fi

USB_VERSION_FILE="$USB_CASSIE_DIR/version.txt"
[[ -f "$USB_VERSION_FILE" ]] || die "No version.txt found in USB cassie folder."
USB_VERSION="$(tr -d '[:space:]' < "$USB_VERSION_FILE")"
log "USB cassie version: $USB_VERSION"

# ─── Decide: install or update ───────────────────────────────────────────────
if [[ ! -d "$INSTALL_DIR" ]]; then
    log "Cassie not installed. Running first-time installation..."
    bash "$USB_CASSIE_DIR/install.sh" "$USB_CASSIE_DIR" "$INSTALL_DIR"
else
    INSTALLED_VERSION_FILE="$INSTALL_DIR/version.txt"
    if [[ ! -f "$INSTALLED_VERSION_FILE" ]]; then
        log "Installed version unknown. Forcing update..."
        bash "$USB_CASSIE_DIR/update.sh" "$USB_CASSIE_DIR" "$INSTALL_DIR"
    else
        INSTALLED_VERSION="$(tr -d '[:space:]' < "$INSTALLED_VERSION_FILE")"
        log "Installed version: $INSTALLED_VERSION"

        # Compare semantic versions using sort -V
        NEWER="$(printf '%s\n%s\n' "$INSTALLED_VERSION" "$USB_VERSION" | sort -V | tail -1)"
        if [[ "$NEWER" == "$USB_VERSION" && "$USB_VERSION" != "$INSTALLED_VERSION" ]]; then
            log "USB version ($USB_VERSION) is newer than installed ($INSTALLED_VERSION). Updating..."
            bash "$USB_CASSIE_DIR/update.sh" "$USB_CASSIE_DIR" "$INSTALL_DIR"
        else
            log "Installed version ($INSTALLED_VERSION) is current or newer. No update needed."
        fi
    fi
fi

# ─── Cleanup ─────────────────────────────────────────────────────────────────
sync
umount "$MOUNT_POINT" || true
log "USB handler complete."
