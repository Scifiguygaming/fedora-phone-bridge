#!/usr/bin/env python3
import sys
import time
import subprocess
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio
import notify2

SERVICE = "org.pipewire.Telephony"

class PhoneAppWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Phone")
        self.set_default_size(360, 620)
        self.set_resizable(False)

        self.call_start_time = None
        self.timer_source_id = None
        self.active_call_path = None
        self.ag_path = None
        self.in_call = False
        self.is_ringing = False

        try:
            notify2.init("PhoneBridge")
        except Exception:
            pass

        self._build_ui()
        self._detect_audio_gateway()
        self._init_session_dbus()

    def _build_ui(self):
        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(root_box)

        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="Phone Bridge", css_classes=["title-4"]))
        root_box.append(header)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(16)
        main_box.set_margin_start(16)
        main_box.set_margin_end(16)
        root_box.append(main_box)

        status_card = Adw.PreferencesGroup()
        main_box.append(status_card)

        self.status_banner = Adw.ActionRow()
        self.status_banner.set_title("Ready")
        self.status_banner.set_subtitle("Phone Connected • Native Audio Active")
        status_card.add(self.status_banner)

        self.number_entry = Gtk.Entry()
        self.number_entry.set_placeholder_text("Enter number to dial...")
        self.number_entry.set_alignment(0.5)
        self.number_entry.add_css_class("title-2")
        main_box.append(self.number_entry)

        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)
        grid.set_halign(Gtk.Align.CENTER)
        main_box.append(grid)

        buttons = [
            ("1", 0, 0), ("2", 1, 0), ("3", 2, 0),
            ("4", 0, 1), ("5", 1, 1), ("6", 2, 1),
            ("7", 0, 2), ("8", 1, 2), ("9", 2, 2),
            ("*", 0, 3), ("0", 1, 3), ("#", 2, 3)
        ]

        for text, col, row in buttons:
            btn = Gtk.Button(label=text)
            btn.set_size_request(80, 50)
            btn.add_css_class("title-3")
            btn.connect("clicked", self._on_digit_clicked, text)
            grid.attach(btn, col, row, 1, 1)

        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        action_box.set_halign(Gtk.Align.CENTER)
        action_box.set_margin_top(10)
        main_box.append(action_box)

        self.answer_btn = Gtk.Button(label="Answer")
        self.answer_btn.add_css_class("suggested-action")
        self.answer_btn.add_css_class("pill")
        self.answer_btn.set_size_request(110, 48)
        self.answer_btn.connect("clicked", self._on_answer_clicked)
        self.answer_btn.set_visible(False)
        action_box.append(self.answer_btn)

        self.dial_btn = Gtk.Button(label="Call")
        self.dial_btn.add_css_class("suggested-action")
        self.dial_btn.add_css_class("pill")
        self.dial_btn.set_size_request(110, 48)
        self.dial_btn.connect("clicked", self._on_dial_clicked)
        action_box.append(self.dial_btn)

        self.hangup_btn = Gtk.Button(label="Hang Up")
        self.hangup_btn.add_css_class("destructive-action")
        self.hangup_btn.add_css_class("pill")
        self.hangup_btn.set_size_request(110, 48)
        self.hangup_btn.connect("clicked", self._on_hangup_clicked)
        self.hangup_btn.set_sensitive(False)
        action_box.append(self.hangup_btn)

        del_btn = Gtk.Button(label="⌫ Delete")
        del_btn.add_css_class("flat")
        del_btn.connect("clicked", self._on_backspace_clicked)
        main_box.append(del_btn)

    def _detect_audio_gateway(self):
        try:
            res = subprocess.run(["busctl", "--user", "tree", SERVICE], capture_output=True, text=True)
            for line in res.stdout.splitlines():
                if "/org/pipewire/Telephony/ag" in line:
                    self.ag_path = line.strip().split()[-1]
                    break
        except Exception:
            pass

    def _init_session_dbus(self):
        try:
            self.session_conn = Gio.bus_get_sync(Gio.BusType.SESSION, None)

            self.session_conn.signal_subscribe(
                SERVICE,
                "org.ofono.VoiceCallManager",
                "CallAdded",
                None,
                None,
                Gio.DBusSignalFlags.NONE,
                self._on_call_added,
                None
            )

            self.session_conn.signal_subscribe(
                SERVICE,
                "org.ofono.VoiceCallManager",
                "CallRemoved",
                None,
                None,
                Gio.DBusSignalFlags.NONE,
                self._on_call_removed,
                None
            )
        except Exception as e:
            self.status_banner.set_subtitle(f"Telephony D-Bus error: {e}")

    def _on_call_added(self, connection, sender, path, iface, signal, params, user_data):
        call_obj, call_props = params.unpack()
        self.active_call_path = call_obj
        caller = call_props.get("LineIdentification", "Incoming Call")
        GLib.idle_add(self._trigger_incoming_alert, caller)

    def _on_call_removed(self, connection, sender, path, iface, signal, params, user_data):
        GLib.idle_add(self._reset_call_ui)

    def _trigger_incoming_alert(self, caller):
        self.is_ringing = True
        self.status_banner.set_title(f"Call: {caller}")
        self.status_banner.set_subtitle("Phone Ringing...")
        self.dial_btn.set_visible(False)
        self.answer_btn.set_visible(True)
        self.hangup_btn.set_sensitive(True)

        try:
            notif = notify2.Notification("Incoming Call", f"{caller}", "phone")
            notif.set_urgency(notify2.URGENCY_CRITICAL)
            notif.show()
        except Exception:
            pass
        return False

    def _on_digit_clicked(self, button, digit):
        self.number_entry.set_text(self.number_entry.get_text() + digit)

    def _on_backspace_clicked(self, button):
        text = self.number_entry.get_text()
        if text:
            self.number_entry.set_text(text[:-1])

    def _on_answer_clicked(self, button):
        if self.active_call_path:
            subprocess.run([
                "busctl", "--user", "call",
                SERVICE,
                self.active_call_path,
                "org.ofono.VoiceCall",
                "Answer"
            ], capture_output=True)

        if not self.ag_path:
            self._detect_audio_gateway()

        if self.ag_path:
            subprocess.run([
                "busctl", "--user", "call",
                SERVICE,
                self.ag_path,
                "org.pipewire.Telephony.AudioGateway1",
                "HoldAndAnswer"
            ], capture_output=True)

        self.in_call = True
        self.is_ringing = False
        self.answer_btn.set_visible(False)
        self.dial_btn.set_visible(False)
        self.hangup_btn.set_sensitive(True)
        self.call_start_time = time.time()
        self.status_banner.set_title("Call Active")
        self.status_banner.set_subtitle("Connected: 00:00")
        self.timer_source_id = GLib.timeout_add(1000, self._update_timer)

    def _on_hangup_clicked(self, button):
        if not self.ag_path:
            self._detect_audio_gateway()

        if self.ag_path:
            subprocess.run([
                "busctl", "--user", "call",
                SERVICE,
                self.ag_path,
                "org.pipewire.Telephony.AudioGateway1",
                "HangupAll"
            ], capture_output=True)
        self._reset_call_ui()

    def _on_dial_clicked(self, button):
        number = self.number_entry.get_text().strip()
        if not number:
            return

        if not self.ag_path:
            self._detect_audio_gateway()

        if self.ag_path:
            subprocess.run([
                "busctl", "--user", "call",
                SERVICE,
                self.ag_path,
                "org.pipewire.Telephony.AudioGateway1",
                "Dial", "s", number
            ], capture_output=True)

        self.in_call = True
        self.status_banner.set_title(f"Calling: {number}")
        self.status_banner.set_subtitle("Dialing via Bluetooth...")
        self.dial_btn.set_sensitive(False)
        self.hangup_btn.set_sensitive(True)
        self.call_start_time = time.time()
        self.timer_source_id = GLib.timeout_add(1000, self._update_timer)

    def _reset_call_ui(self):
        self.in_call = False
        self.is_ringing = False
        self.active_call_path = None
        self.status_banner.set_title("Ready")
        self.status_banner.set_subtitle("Phone Connected • Native Audio Active")
        if self.timer_source_id:
            GLib.source_remove(self.timer_source_id)
            self.timer_source_id = None
        self.answer_btn.set_visible(False)
        self.dial_btn.set_visible(True)
        self.dial_btn.set_sensitive(True)
        self.hangup_btn.set_sensitive(False)
        return False

    def _update_timer(self):
        if not self.call_start_time or not self.in_call:
            return False
        elapsed = int(time.time() - self.call_start_time)
        mins, secs = divmod(elapsed, 60)
        self.status_banner.set_subtitle(f"Call Duration: {mins:02d}:{secs:02d}")
        return True

class PhoneApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="io.github.phonebridge")

    def do_activate(self):
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.PREFER_DARK)

        win = self.props.active_window
        if not win:
            win = PhoneAppWindow(self)
        win.present()

if __name__ == "__main__":
    app = PhoneApp()
    app.run(sys.argv)
