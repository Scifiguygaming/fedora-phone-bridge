# Fedora Phone Bridge

A native Linux GTK4/Libadwaita phone bridge for handling calls from an iPhone (or Android device) over Bluetooth.

Simultaneously routes regular desktop audio and incoming voice calls into wireless earbuds while feeding a desktop USB microphone into the call.

## Key Features
* **GTK4 / Libadwaita Interface:** Modern GNOME styling, dark-theme default, native titlebar drag support.
* **Native WirePlumber HFP Engine:** Uses WirePlumber native session-bus telephony backend (`org.pipewire.Telephony`), eliminating Bluetooth profile locking.
* **Full Call Controls:** Desktop notifications, live timer, Answer/Hangup controls, and outbound dialpad.
* **Hardware Independent:** Auto-detects connected phones and audio nodes dynamically.

## Installation

```bash
git clone [https://github.com/scifiguygaming/fedora-phone-bridge.git](https://github.com/scifiguygaming/fedora-phone-bridge.git)
cd fedora-phone-bridge
./install.sh
```

## Usage
1. Connect phone via GNOME Bluetooth.
2. Launch `phone-bridge` from the app grid or terminal.

