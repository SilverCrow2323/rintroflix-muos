# -*- coding: utf-8 -*-
"""Optional /dev/fb0 presenter for muOS devices without a usable SDL video driver."""
from __future__ import annotations

import fcntl
import mmap
import os
import struct

import pygame

_FBIOGET_VSCREENINFO = 0x4600
_FBIOPUT_VSCREENINFO = 0x4601
_FBIOGET_FSCREENINFO = 0x4602
_FBIOBLANK = 0x4611
_STATE = {"fb": None, "original_flip": None, "original_update": None, "error": ""}


def _probe(file_obj):
    try:
        variable = bytearray(160)
        fcntl.ioctl(file_obj, _FBIOGET_VSCREENINFO, variable)
        width, height, _xvirt, _yvirt, _xoff, _yoff, bpp, _gray = struct.unpack_from("8I", variable, 0)
        red_offset, red_len, _rmsb, green_offset, green_len, _gmsb, blue_offset, blue_len, _bmsb = struct.unpack_from("9I", variable, 32)
        fixed = bytearray(80)
        fcntl.ioctl(file_obj, _FBIOGET_FSCREENINFO, fixed)
        stride = struct.unpack_from("I", fixed, 48)[0]
        masks = (((1 << red_len) - 1) << red_offset,
                 ((1 << green_len) - 1) << green_offset,
                 ((1 << blue_len) - 1) << blue_offset, 0)
        if width and height and bpp in (16, 32) and stride:
            return width, height, bpp, stride, masks
    except Exception:
        pass
    return None


class _Framebuffer:
    def __init__(self):
        device = os.environ.get("RINTROFLIX_FB_DEV", "/dev/fb0")
        sysfs = os.environ.get("RINTROFLIX_FB_SYSFS", "/sys/class/graphics/fb0")
        self.ok = False
        self.error = ""
        try:
            self.file = open(device, "r+b")
            try:
                variable = bytearray(160)
                fcntl.ioctl(self.file, _FBIOGET_VSCREENINFO, variable)
                struct.pack_into("2I", variable, 16, 0, 0)
                fcntl.ioctl(self.file, _FBIOPUT_VSCREENINFO, bytes(variable))
                fcntl.ioctl(self.file, _FBIOBLANK, 0)
            except Exception:
                pass
            geometry = _probe(self.file)
            if geometry:
                self.width, self.height, self.bpp, self.stride, masks = geometry
            else:
                self.width, self.height = map(int, open(os.path.join(sysfs, "virtual_size")).read().strip().split(","))
                self.bpp = int(open(os.path.join(sysfs, "bits_per_pixel")).read())
                stride_path = os.path.join(sysfs, "stride")
                self.stride = int(open(stride_path).read()) if os.path.isfile(stride_path) else self.width * self.bpp // 8
                masks = (0xF800, 0x07E0, 0x001F, 0) if self.bpp == 16 else (0x00FF0000, 0x0000FF00, 0x000000FF, 0)
            self.memory = mmap.mmap(self.file.fileno(), self.stride * self.height)
            self.frame = pygame.Surface((self.width, self.height), 0, self.bpp, masks)
            self.frame.fill((0, 0, 0))
            self.pitch = self.frame.get_pitch()
            self._scaled = None
            self.ok = True
        except Exception as exc:
            self.error = "%s: %s" % (type(exc).__name__, str(exc) or repr(exc))
            self.close()

    def close(self):
        try:
            if getattr(self, "memory", None):
                self.memory.close()
            if getattr(self, "file", None):
                self.file.close()
        except Exception:
            pass
        self.ok = False

    def present(self, source):
        if not self.ok:
            return
        try:
            sw, sh = source.get_size()
            if (sw, sh) != (self.width, self.height):
                if self._scaled is None:
                    ratio = min(self.width / float(sw), self.height / float(sh))
                    dw, dh = int(sw * ratio), int(sh * ratio)
                    self._scaled = (dw, dh, (self.width - dw) // 2,
                                    (self.height - dh) // 2, pygame.Surface((dw, dh)))
                dw, dh, ox, oy, target = self._scaled
                self.frame.fill((0, 0, 0))
                pygame.transform.scale(source, (dw, dh), target)
                self.frame.blit(target, (ox, oy))
            else:
                self.frame.blit(source, (0, 0))
            raw = self.frame.get_buffer().raw
            if self.pitch == self.stride:
                self.memory[:len(raw)] = raw
            else:
                bytes_per_row = self.width * (self.bpp // 8)
                for row in range(self.height):
                    self.memory[row * self.stride:row * self.stride + bytes_per_row] = raw[row * self.pitch:row * self.pitch + bytes_per_row]
        except Exception:
            pass


def last_error():
    return _STATE.get("error", "")


def info():
    fb = _STATE.get("fb")
    if fb is None or not fb.ok:
        return "framebuffer non attivo"
    return "%dx%d %dbpp stride=%d" % (fb.width, fb.height, fb.bpp, fb.stride)


def attach(surface):
    old = _STATE.get("fb")
    if old:
        old.close()
    fb = _Framebuffer()
    if not fb.ok:
        _STATE["error"] = fb.error or "framebuffer initialization failed"
        return False
    _STATE["error"] = ""
    _STATE["fb"] = fb

    def _flip():
        fb.present(surface)

    if _STATE["original_flip"] is None:
        _STATE["original_flip"] = pygame.display.flip
        _STATE["original_update"] = pygame.display.update
    pygame.display.flip = _flip
    pygame.display.update = lambda *args, **kwargs: _flip()
    _flip()
    return True


def detach():
    fb = _STATE.get("fb")
    if fb:
        fb.close()
    _STATE["fb"] = None
    # Restore SDL entry points before pygame.display.quit()/reinitialisation.
    if _STATE.get("original_flip") is not None:
        try:
            pygame.display.flip = _STATE["original_flip"]
            pygame.display.update = _STATE["original_update"]
        except Exception:
            pass
