#!/usr/bin/env bash
set -e

echo "=== Installing Fedora Phone Bridge ==="

# 1. System dependencies
sudo dnf install -y python3-gobject libadwaita gtk4 python3-notify2 pipewire wireplumber bluez

# 2. Mask ofono to prevent profile locking
if systemctl list-unit-files | grep -q ofono; then
    echo "[+] Masking oFono..."
    sudo systemctl stop ofono || true
    sudo systemctl mask ofono || true
fi

# 3. Configure WirePlumber native backend
echo "[+] Configuring WirePlumber native HFP backend..."
mkdir -p ~/.config/wireplumber/wireplumber.conf.d/
cp wireplumber-bluez-native.conf ~/.config/wireplumber/wireplumber.conf.d/50-bluez-hf.conf

echo "[+] Restarting audio stack..."
systemctl --user restart wireplumber pipewire pipewire-pulse

# 4. Install Application Executable
sudo mkdir -p /usr/local/bin
sudo cp src/phone_gui.py /usr/local/bin/phone-bridge
sudo chmod +x /usr/local/bin/phone-bridge

# 5. Install Desktop Launcher
mkdir -p ~/.local/share/applications
cat << 'DESKTOP_EOF' > ~/.local/share/applications/io.github.phonebridge.desktop
[Desktop Entry]
Name=Phone Bridge
Comment=Native Bluetooth Phone Call Bridge
Exec=env GSK_RENDERER=ngl /usr/local/bin/phone-bridge
Icon=call-start
Terminal=false
Type=Application
Categories=Utility;Telephony;AudioVideo;
StartupNotify=true
DESKTOP_EOF

update-desktop-database ~/.local/share/applications

echo "=== Installation Complete ==="
echo "Launch 'Phone Bridge' from your application menu or run 'phone-bridge'."
