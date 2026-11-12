# -*- coding: utf-8 -*-
"""Direct evdev reader for muOS handheld controls (works while MPV owns the screen)."""
from __future__ import annotations

import os
import struct
import subprocess

_EV_KEY = 1
_EV_ABS = 3
_EVENT_SIZE = struct.calcsize("llHHi")
KEYMAP_ANDROMEDA = {
    304: "A", 305: "B", 306: "Y", 307: "X",
    310: "L1", 311: "R1", 312: "L2", 313: "R2",
    314: "SELECT", 315: "START", 316: "MENU",
    114: "VOL-", 115: "VOL+",
}
KEYMAP_NON_ANDROMEDA = {
    304: "A", 305: "B", 307: "X", 308: "Y",
    310: "L1", 311: "R1", 312: "SELECT", 313: "L3",
    314: "R3", 315: "MENU", 316: "START",
    317: "L2", 318: "R2", 114: "VOL-", 115: "VOL+",
}

def detect_muos_release():
    value = os.environ.get("MUOS_VERSION", "")
    if not value:
        try:
            value = subprocess.run(
                ["sh", "-c", '. /opt/muos/script/var/func.sh 2>/dev/null; GET_VAR system version 2>/dev/null'],
                capture_output=True, text=True, timeout=2).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            value = ""
    if not value:
        try:
            with open("/opt/muos/config/system/version", encoding="utf-8") as stream:
                value = stream.readline().strip()
        except OSError:
            value = ""
    return "andromeda" if "andromeda" in value.lower() else "not_andromeda"

def resolve_profile(selection="auto"):
    selection = str(selection or "auto").lower()
    return detect_muos_release() if selection == "auto" else (
        "andromeda" if selection == "andromeda" else "not_andromeda")

def keymap_for(selection="auto"):
    return dict(KEYMAP_ANDROMEDA if resolve_profile(selection) == "andromeda"
                else KEYMAP_NON_ANDROMEDA)



class InputReader:
    def __init__(self, device_dir=None, profile="auto"):
        self.profile = profile
        self.resolved_profile = resolve_profile(profile)
        self.keymap = keymap_for(profile)
        self.device_dir = device_dir or os.environ.get("RINTROFLIX_INPUT_DIR", "/dev/input")
        self.fds = []
        self.hx = 0
        self.hy = 0

    def set_profile(self, profile):
        self.profile = profile
        self.resolved_profile = resolve_profile(profile)
        self.keymap = keymap_for(profile)

    def start(self):
        self.stop()
        try:
            names = sorted(n for n in os.listdir(self.device_dir) if n.startswith("event"))
        except OSError:
            names = []
        for name in names:
            try:
                self.fds.append(os.open(os.path.join(self.device_dir, name), os.O_RDONLY | os.O_NONBLOCK))
            except OSError:
                continue
        self.hx = self.hy = 0
        return bool(self.fds)

    def stop(self):
        for fd in self.fds:
            try:
                os.close(fd)
            except OSError:
                pass
        self.fds = []

    def active(self):
        return bool(self.fds)

    def hat(self):
        # Match SDL convention: +Y means up.
        return self.hx, -self.hy

    def poll(self):
        pressed = []
        for fd in tuple(self.fds):
            while True:
                try:
                    data = os.read(fd, _EVENT_SIZE * 32)
                except (BlockingIOError, InterruptedError):
                    break
                except OSError:
                    break
                if not data:
                    break
                usable = len(data) - (len(data) % _EVENT_SIZE)
                for offset in range(0, usable, _EVENT_SIZE):
                    _sec, _usec, etype, code, value = struct.unpack_from("llHHi", data, offset)
                    if etype == _EV_KEY and value == 1:
                        key = self.keymap.get(code)
                        if key:
                            pressed.append(key)
                    elif etype == _EV_ABS:
                        if code == 16:
                            self.hx = max(-1, min(1, value))
                        elif code == 17:
                            self.hy = max(-1, min(1, value))
        return pressed

    def close(self):
        self.stop()
