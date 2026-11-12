# -*- coding: utf-8 -*-
"""Direct evdev reader for muOS handheld controls (works while MPV owns the screen)."""
from __future__ import annotations

import os
import struct

_EV_KEY = 1
_EV_ABS = 3
_EVENT_SIZE = struct.calcsize("llHHi")
KEYMAP = {
    304: "A", 305: "B", 306: "Y", 307: "X",
    308: "L1", 309: "R1", 314: "L2", 315: "R2",
    310: "SELECT", 311: "START", 312: "MENU",
    114: "VOL-", 115: "VOL+",
}


class InputReader:
    def __init__(self, device_dir=None):
        self.device_dir = device_dir or os.environ.get("RINTROFLIX_INPUT_DIR", "/dev/input")
        self.fds = []
        self.hx = 0
        self.hy = 0

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
                        key = KEYMAP.get(code)
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
