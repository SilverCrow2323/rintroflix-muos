# -*- coding: utf-8 -*-
"""MPV backend with navigable in-video OSD, real volume readback and zapping."""
from __future__ import annotations

import json
import os
import shlex
import shutil
import socket
import subprocess
import time
from datetime import datetime
from pathlib import Path

from . import config as C
from .input import InputReader

RESULT_BACK = "back"
RESULT_NEXT = "next"
RESULT_PREV = "prev"
RESULT_FAV = "fav"
RESULT_ERROR = "error"

MENU_ITEMS = [
    "Play / pause",
    "Previous channel",
    "Next channel",
    "Now playing / TV guide",
    "Add / remove favourite",
    "Change audio track",
    "Subtitles on / off",
    "Mute / unmute audio",
    "Start / stop recording",
    "Exit playback",
]


class Player:
    def __init__(self, cfg):
        self.cfg = cfg
        self.last_error = ""
        self.input = InputReader()
        self._recording = None
        self._menu_index = 0

    def backend(self):
        preferred = self.cfg.get("player_backend", "mpv")
        if preferred == "ffplay" and shutil.which("ffplay"):
            return "ffplay"
        if shutil.which("mpv"):
            return "mpv"
        if shutil.which("ffplay"):
            return "ffplay"
        return None

    @staticmethod
    def _request(sock_path, command, query=False, timeout=0.45):
        """Send one IPC command. Queries wait for their matching request_id."""
        if not sock_path or not os.path.exists(sock_path):
            return None
        request_id = int(time.monotonic() * 1000000) & 0x7fffffff
        payload = {"command": list(command), "request_id": request_id}
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
                conn.settimeout(timeout)
                conn.connect(sock_path)
                conn.sendall((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
                buffer = b""
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    chunk = conn.recv(8192)
                    if not chunk:
                        break
                    buffer += chunk
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        try:
                            answer = json.loads(line.decode("utf-8", "replace"))
                        except ValueError:
                            continue
                        if answer.get("request_id") == request_id:
                            if answer.get("error") != "success":
                                return None
                            return answer.get("data") if query else True
        except (OSError, ValueError, TimeoutError):
            return None
        return None

    def _cmd(self, sock_path, *args):
        return self._request(sock_path, args, query=False)

    def _get(self, sock_path, prop):
        return self._request(sock_path, ("get_property", prop), query=True)

    def _set(self, sock_path, prop, value):
        return self._cmd(sock_path, "set_property", prop, value)

    def _show(self, sock_path, message, duration=2200):
        self._cmd(sock_path, "show-text", str(message), int(duration))

    def _volume(self, sock_path, delta):
        actual = self._get(sock_path, "volume")
        if isinstance(actual, (int, float)):
            value = max(0, min(100, int(round(actual)) + delta))
            self._set(sock_path, "volume", value)
            # Read back after the command so the OSD reports MPV's real value.
            time.sleep(0.04)
            actual = self._get(sock_path, "volume")
        mute = self._get(sock_path, "mute")
        if isinstance(actual, (int, float)):
            percent = max(0, min(100, int(round(actual))))
            filled = max(0, min(10, round(percent / 10)))
            bar = "[" + ("#" * filled) + ("-" * (10 - filled)) + "]"
            msg = "AUDIO MUTED  |  %d%% %s" % (percent, bar) if mute else "VOLUME  %d%% %s" % (percent, bar)
        else:
            msg = "VOLUME UNAVAILABLE"
        self._show(sock_path, msg, 1800)

    def _toggle_mute(self, sock_path):
        current = self._get(sock_path, "mute")
        if not isinstance(current, bool):
            self._show(sock_path, "AUDIO STATUS UNAVAILABLE", 1800)
            return
        if not self._set(sock_path, "mute", not current):
            self._show(sock_path, "MUTE COMMAND FAILED", 1800)
            return
        actual = self._get(sock_path, "mute")
        if isinstance(actual, bool):
            self._show(sock_path, "AUDIO: MUTED" if actual else "AUDIO: ON", 1800)
        else:
            self._show(sock_path, "AUDIO UPDATED", 1800)

    def _overlay_text(self, sock_path, channel, epg):
        """Gamepad OSD menu; MPV owns the video plane so playback never loses focus."""
        # Five rows keep the menu legible on the RG35XX H's 640x480 panel.
        visible = 5
        first = max(0, min(self._menu_index - visible // 2, len(MENU_ITEMS) - visible))
        last = min(len(MENU_ITEMS), first + visible)
        labels = list(MENU_ITEMS)
        paused = self._get(sock_path, "pause")
        muted = self._get(sock_path, "mute")
        if isinstance(paused, bool):
            labels[0] = "Resume playback" if paused else "Pause playback"
        if isinstance(muted, bool):
            labels[7] = "Unmute audio" if muted else "Mute audio"
        lines = ["RINTROFLIX  /  PLAYER MENU"]
        for index in range(first, last):
            marker = ">" if index == self._menu_index else " "
            lines.append("%s  %s" % (marker, labels[index]))
        lines.append("UP/DOWN MOVE   A SELECT   B CLOSE")
        lines.append("CHANNEL  " + (channel.name or "Unknown channel")[:30])
        if epg:
            current, following = epg.now_next(channel)
            if current:
                lines.append("NOW  " + current.title[:32])
            if following:
                lines.append("NEXT " + following.title[:32])
        self._show(sock_path, "\n".join(lines), 600000)

    def _controls_text(self, sock_path, channel, epg, paused=False, duration=6200):
        """Transport strip with explicit controller hints and the live programme."""
        state = "PAUSED" if paused else "PLAYING"
        lines = [
            "RINTROFLIX  /  %s" % state,
            "LEFT  PREV CHANNEL   NEXT CHANNEL  RIGHT",
            "A  PLAY / PAUSE    SELECT  PLAYER MENU",
            "UP/DOWN  SEEK 30s    L1/R1  VOLUME",
            "START  HELP    B  EXIT PLAYER",
            "CHANNEL  " + (channel.name or "Unknown channel")[:30],
        ]
        if epg:
            current, following = epg.now_next(channel)
            if current:
                lines.append("NOW  " + current.title[:32])
            if following:
                lines.append("NEXT " + following.title[:32])
        self._show(sock_path, "\n".join(lines), duration)

    def _toggle_record(self, sock_path, channel):
        if self._recording:
            ok = self._set(sock_path, "stream-record", "")
            saved = os.path.basename(self._recording)
            self._recording = None
            self._show(sock_path, "RECORDING STOPPED: " + saved if ok else "RECORDING STOP NOT CONFIRMED")
            return
        target = Path(self.cfg.get("rec_dir", str(C.REC_DIR)))
        try:
            target.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._show(sock_path, "REC: recording folder unavailable - " + str(exc)[:40])
            return
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in channel.name)[:42] or "channel"
        filename = "%s_%s.ts" % (safe, datetime.now().strftime("%Y%m%d_%H%M%S"))
        path = str(target / filename)
        if self._set(sock_path, "stream-record", path):
            self._recording = path
            self._show(sock_path, "RECORDING: " + filename, 2400)
        else:
            self._show(sock_path, "RECORDING IS NOT SUPPORTED BY THIS MPV BUILD", 3000)

    def _select_menu(self, sock_path, channel, epg):
        choice = self._menu_index
        if choice == 0:
            paused = self._get(sock_path, "pause")
            self._set(sock_path, "pause", not bool(paused))
            state = self._get(sock_path, "pause")
            self._controls_text(sock_path, channel, epg, bool(state), 5200)
            self._menu_delay = 0.0
            return "continue"
        if choice == 1:
            self._cmd(sock_path, "quit", 21)
            return RESULT_PREV
        if choice == 2:
            self._cmd(sock_path, "quit", 20)
            return RESULT_NEXT
        if choice == 3:
            current, following = epg.now_next(channel) if epg else (None, None)
            msg = "NOW: %s\nNEXT: %s" % (
                current.title if current else "No guide data",
                following.title if following else "No upcoming programme")
            self._show(sock_path, msg, 6500)
            self._menu_delay = 6.6
            return "continue"
        if choice == 4:
            self._cmd(sock_path, "quit", 22)
            return RESULT_FAV
        if choice == 5:
            self._cmd(sock_path, "cycle", "audio")
            self._show(sock_path, "AUDIO TRACK CHANGED", 1800)
            self._menu_delay = 1.9
            return "continue"
        if choice == 6:
            self._cmd(sock_path, "cycle", "sub")
            self._show(sock_path, "SUBTITLE TRACK CHANGED", 1800)
            self._menu_delay = 1.9
            return "continue"
        if choice == 7:
            self._toggle_mute(sock_path)
            self._menu_delay = 1.9
            return "continue"
        if choice == 8:
            self._toggle_record(sock_path, channel)
            self._menu_delay = 2.5
            return "continue"
        if choice == 9:
            self._cmd(sock_path, "quit", 0)
            return RESULT_BACK
        return "continue"

    def play(self, channel, epg=None):
        backend = self.backend()
        if backend is None:
            self.last_error = "No media player found. Install MPV for the full RintrofliX experience."
            return RESULT_ERROR
        if backend != "mpv":
            return self._play_ffplay(channel)

        options = getattr(channel, "opts", None) or {}
        user_agent = options.get("user-agent") or self.cfg.get("user_agent", "")
        referrer = options.get("referrer", "")
        headers = dict(options.get("headers", {}))
        if options.get("origin"):
            headers.setdefault("Origin", options["origin"])
        cache_secs = max(0, min(30, int(self.cfg.get("player_cache_secs", 5))))
        sock_path = "/tmp/rintroflix-mpv-%d.sock" % os.getpid()
        try:
            os.unlink(sock_path)
        except OSError:
            pass
        scale = max(100, min(200, int(self.cfg.get("ui_scale", 125)))) / 100.0
        osd_size = max(25, min(34, round(28 * scale)))
        command = [
            "mpv", channel.url, "--no-config", "--fullscreen", "--keepaspect=yes",
            "--osd-level=1", "--osd-font-size=%d" % osd_size,
            "--osd-border-style=background-box", "--osd-border-size=2",
            "--osd-shadow-offset=2", "--osd-color=#FFF1F6FC",
            "--osd-back-color=#CC0D1724", "--osd-outline-color=#FF0A111D",
            "--osd-outline-size=1.2",
            "--osd-align-x=left", "--osd-align-y=top",
            "--osd-margin-x=22", "--osd-margin-y=18", "--osd-spacing=1",
            "--network-timeout=15", "--cache=yes", "--cache-secs=%d" % cache_secs,
            "--input-ipc-server=" + sock_path,
        ]
        if user_agent:
            command.append("--user-agent=" + user_agent)
        if referrer:
            command.append("--referrer=" + referrer)
        if headers:
            command.append("--http-header-fields=" + ",".join("%s: %s" % (k, v) for k, v in headers.items()))
        extra = os.environ.get("RINTROFLIX_MPV_EXTRA", "")
        if extra:
            command.extend(shlex.split(extra))
        env = dict(os.environ)
        env.pop("SDL_VIDEODRIVER", None)
        env.pop("RINTROFLIX_FB", None)
        log_path = str(C.DATA_DIR / "mpv.log")
        try:
            with open(log_path, "ab") as log_file:
                log_file.write(("\n=== %s ===\n" % channel.name).encode("utf-8", "replace"))
                proc = subprocess.Popen(command, stdout=log_file, stderr=log_file, env=env)
                result = self._control_loop(proc, sock_path, channel, epg)
                if proc.poll() is None:
                    try:
                        proc.wait(timeout=2.0)
                    except subprocess.TimeoutExpired:
                        proc.terminate()
                        try:
                            proc.wait(timeout=1.0)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            proc.wait()
        except OSError as exc:
            self.last_error = str(exc)
            return RESULT_ERROR
        finally:
            try:
                os.unlink(sock_path)
            except OSError:
                pass
        if result in (RESULT_NEXT, RESULT_PREV, RESULT_FAV):
            return result
        if proc.returncode not in (0, 4, None):
            self.last_error = "MPV exit %s: %s" % (proc.returncode, self._log_tail(log_path))
            return RESULT_ERROR
        return RESULT_BACK

    def _control_loop(self, proc, sock_path, channel, epg):
        started_here = False
        if not self.input.active():
            started_here = self.input.start()
        self._recording = None
        menu_open = False
        menu_last_activity = 0.0
        overlay_redraw_at = 0.0
        self._menu_delay = 0.0
        last_hat = (0, 0)
        last_hat_time = 0.0
        try:
            self._controls_text(sock_path, channel, epg, bool(self._get(sock_path, "pause")), 4600)
            while proc.poll() is None:
                now = time.monotonic()
                for button in self.input.poll():
                    if button == "MENU":
                        continue  # reserved by muOS
                    if menu_open:
                        menu_last_activity = time.monotonic()
                    if button in ("L1", "VOL-"):
                        self._volume(sock_path, -5)
                        if menu_open: overlay_redraw_at = time.monotonic() + 1.9
                    elif button in ("R1", "VOL+"):
                        self._volume(sock_path, 5)
                        if menu_open: overlay_redraw_at = time.monotonic() + 1.9
                    elif button == "X":
                        self._toggle_mute(sock_path)
                        if menu_open:
                            overlay_redraw_at = time.monotonic() + 1.9
                    elif button == "A":
                        if menu_open:
                            menu_last_activity = time.monotonic()
                            result = self._select_menu(sock_path, channel, epg)
                            if result in (RESULT_NEXT, RESULT_PREV, RESULT_FAV, RESULT_BACK):
                                return result
                            if getattr(self, "_menu_delay", 0.0) <= 0:
                                menu_open = False
                            else:
                                overlay_redraw_at = time.monotonic() + self._menu_delay
                        else:
                            paused = self._get(sock_path, "pause")
                            self._set(sock_path, "pause", not bool(paused))
                            actual = self._get(sock_path, "pause")
                            self._controls_text(sock_path, channel, epg, bool(actual), 5200)
                    elif button == "B":
                        if menu_open:
                            menu_open = False
                            self._cmd(sock_path, "show-text", "", 1)
                        else:
                            self._cmd(sock_path, "quit", 0)
                            return RESULT_BACK
                    elif button == "SELECT":
                        if menu_open:
                            menu_open = False
                            self._cmd(sock_path, "show-text", "", 1)
                        else:
                            menu_open = True
                            self._menu_index = 0
                            self._menu_delay = 0.0
                            menu_last_activity = time.monotonic()
                            self._overlay_text(sock_path, channel, epg)
                    elif button == "START":
                        self._controls_text(sock_path, channel, epg,
                                            bool(self._get(sock_path, "pause")), 6200)
                        if menu_open:
                            overlay_redraw_at = time.monotonic() + 6.3
                    elif button == "Y":
                        self._cmd(sock_path, "quit", 22)
                        return RESULT_FAV
                    elif button == "UP" and not menu_open:
                        self._cmd(sock_path, "seek", -30)
                        self._show(sock_path, "SEEK BACK 30s", 1100)
                    elif button == "DOWN" and not menu_open:
                        self._cmd(sock_path, "seek", 30)
                        self._show(sock_path, "SEEK FORWARD 30s", 1100)
                    elif button == "L2":
                        self._cmd(sock_path, "seek", -10)
                        self._show(sock_path, "SEEK BACK 10s", 900)
                        if menu_open:
                            overlay_redraw_at = time.monotonic() + 1.0
                    elif button == "R2":
                        self._cmd(sock_path, "seek", 10)
                        self._show(sock_path, "SEEK FORWARD 10s", 900)
                        if menu_open:
                            overlay_redraw_at = time.monotonic() + 1.0

                hx, hy = self.input.hat()
                hat = (hx, hy)
                now = time.monotonic()
                if hat != (0, 0) and (hat != last_hat or now - last_hat_time > 0.24):
                    last_hat_time = now
                    if hx < 0:
                        self._cmd(sock_path, "quit", 21)
                        return RESULT_PREV
                    elif hx > 0:
                        self._cmd(sock_path, "quit", 20)
                        return RESULT_NEXT
                    elif menu_open and hy > 0:
                        self._menu_index = (self._menu_index - 1) % len(MENU_ITEMS)
                        menu_last_activity = now
                        self._overlay_text(sock_path, channel, epg)
                    elif menu_open and hy < 0:
                        self._menu_index = (self._menu_index + 1) % len(MENU_ITEMS)
                        menu_last_activity = now
                        self._overlay_text(sock_path, channel, epg)
                    elif not menu_open and hy > 0:
                        self._cmd(sock_path, "seek", -30)
                        self._show(sock_path, "SEEK BACK 30s", 1000)
                    elif not menu_open and hy < 0:
                        self._cmd(sock_path, "seek", 30)
                        self._show(sock_path, "SEEK FORWARD 30s", 1000)
                last_hat = hat

                if menu_open and overlay_redraw_at and now >= overlay_redraw_at:
                    self._overlay_text(sock_path, channel, epg)
                    overlay_redraw_at = 0.0
                if menu_open and menu_last_activity and now - menu_last_activity >= 15.0:
                    menu_open = False
                    self._cmd(sock_path, "show-text", "", 1)
                time.sleep(0.045)
        finally:
            if started_here:
                self.input.stop()
        return RESULT_BACK

    def _play_ffplay(self, channel):
        command = ["ffplay", "-fs", "-autoexit", "-loglevel", "error", "-i", channel.url]
        try:
            subprocess.run(command, check=False)
            return RESULT_BACK
        except OSError as exc:
            self.last_error = str(exc)
            return RESULT_ERROR

    @staticmethod
    def _log_tail(path):
        try:
            lines = Path(path).read_text(encoding="utf-8", errors="replace")[-2400:].splitlines()
            return " | ".join(line.strip() for line in lines[-3:])
        except OSError:
            return "log unavailable"
