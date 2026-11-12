# -*- coding: utf-8 -*-
"""Persistent configuration, app paths and one-time VoidCast settings migration."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
ROOT_DIR = PKG_DIR.parent
DATA_DIR = ROOT_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
EPG_CACHE_DIR = CACHE_DIR / "epg"
PLAYLIST_DIR = DATA_DIR / "playlists"
REC_DIR = DATA_DIR / "recordings"
ADDON_DIR = DATA_DIR / "addons"
LIBRARY_CACHE_DIR = CACHE_DIR / "library"
CONFIG_PATH = DATA_DIR / "config.json"
LOG_PATH = DATA_DIR / "rintroflix.log"

for _directory in (DATA_DIR, CACHE_DIR, EPG_CACHE_DIR, PLAYLIST_DIR, REC_DIR, ADDON_DIR, LIBRARY_CACHE_DIR):
    _directory.mkdir(parents=True, exist_ok=True)

APP_NAME = "RintrofliX"
APP_VERSION = "2.6.0"
APP_TAGLINE = "IPTV · LIVE TV · YOUR SIGNAL, YOUR WAY"

PRESET_PLAYLISTS = [
    ("IPTV-Org · Italia", "https://iptv-org.github.io/iptv/countries/it.m3u"),
    ("IPTV-Org · Mondo", "https://iptv-org.github.io/iptv/index.m3u"),
    ("IPTV-Org · News", "https://iptv-org.github.io/iptv/categories/news.m3u"),
    ("IPTV-Org · Music", "https://iptv-org.github.io/iptv/categories/music.m3u"),
    ("IPTV-Org · Movies", "https://iptv-org.github.io/iptv/categories/movies.m3u"),
]

DEFAULTS = {
    "active_playlist": None,
    "playlists": [],
    "view_mode": "list",
    "epg_manual_urls": [],
    "epg_use_playlist_sources": True,
    "epg_max_age_hours": 12,
    "player_backend": "mpv",
    "player_cache_secs": 5,
    "user_agent": "RintrofliX/1.0 (muOS IPTV client)",
    "favorites": [],
    "last_group": "*",
    "show_logos": True,
    "library_sources": [],
    "enabled_addons": [],
    "addon_repositories": [],
    "boot_animation": True,
    "button_map": {
        "0": "A", "1": "B", "2": "X", "3": "Y",
        "4": "L1", "5": "R1", "6": "SELECT", "7": "START",
        "8": "L2", "9": "R2",
    },
    "theme_accent": "cyan",
    "ui_scale": 125,
    "rec_dir": str(REC_DIR),
}


def _first_existing(paths):
    for item in paths:
        p = Path(item)
        if p.is_file():
            return p
    return None


class Config:
    def __init__(self):
        self.data = json.loads(json.dumps(DEFAULTS))
        self.migrated = False
        self.load()

    def load(self):
        if CONFIG_PATH.is_file():
            try:
                stored = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                if isinstance(stored, dict):
                    self.data.update(stored)
                    return
            except (OSError, ValueError, TypeError):
                pass
        # Import only local settings. No source URL is shipped in this package.
        old = _first_existing([
            "/run/muos/storage/application/VoidCast/data/config.json",
            "/mnt/mmc/MUOS/application/VoidCast/data/config.json",
            "/mnt/sdcard/MUOS/application/VoidCast/data/config.json",
        ])
        if old:
            try:
                legacy = json.loads(old.read_text(encoding="utf-8"))
                if isinstance(legacy, dict):
                    for key in (
                        "active_playlist", "playlists", "view_mode",
                        "epg_manual_urls", "epg_use_playlist_sources",
                        "epg_max_age_hours", "player_backend",
                        "player_cache_secs", "user_agent", "favorites",
                        "last_group", "button_map", "theme_accent", "rec_dir",
                    ):
                        if key in legacy:
                            self.data[key] = legacy[key]
                    self._migrate_local_playlist_paths(old.parent.parent)
                    self.migrated = True
                    self.save()
            except (OSError, ValueError, TypeError):
                pass

    def _migrate_local_playlist_paths(self, legacy_root):
        """Keep relative file playlists usable after VoidCast is left behind."""
        migrated = []
        for item in self.data.get("playlists", []):
            if not isinstance(item, dict):
                migrated.append(item)
                continue
            entry = dict(item)
            if entry.get("type") == "file" and entry.get("source"):
                source = Path(str(entry["source"]))
                if not source.is_absolute():
                    source = Path(legacy_root) / source
                try:
                    source = source.resolve()
                except OSError:
                    source = Path(str(source))
                if source.is_file():
                    PLAYLIST_DIR.mkdir(parents=True, exist_ok=True)
                    target = PLAYLIST_DIR / ("voidcast_" + source.name)
                    if not target.exists():
                        try:
                            shutil.copy2(source, target)
                        except OSError:
                            target = source
                    entry["source"] = str(target if target.exists() else source)
                else:
                    # Preserve a truthful absolute path so the user can relink it.
                    entry["source"] = str(source)
            migrated.append(entry)
        self.data["playlists"] = migrated

    def save(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".config-", suffix=".tmp", dir=str(DATA_DIR))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(self.data, stream, indent=2, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp_name, CONFIG_PATH)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value, save=True):
        self.data[key] = value
        if save:
            self.save()

    def playlists(self):
        return list(self.data.get("playlists", []))

    def active_playlist(self):
        pid = self.get("active_playlist")
        return next((p for p in self.playlists() if p.get("id") == pid), None)

    def add_playlist(self, name, source, ptype):
        nums = []
        for item in self.playlists():
            try:
                nums.append(int(str(item.get("id", "")).split("_")[-1]))
            except ValueError:
                continue
        entry = {"id": "pl_%d" % (max(nums or [0]) + 1),
                 "name": name[:80], "source": source, "type": ptype}
        self.data.setdefault("playlists", []).append(entry)
        if not self.get("active_playlist"):
            self.data["active_playlist"] = entry["id"]
        self.save()
        return entry

    def remove_playlist(self, pid):
        self.data["playlists"] = [p for p in self.playlists() if p.get("id") != pid]
        if self.get("active_playlist") == pid:
            items = self.playlists()
            self.data["active_playlist"] = items[0]["id"] if items else None
        self.save()

    def toggle_favorite(self, url):
        items = self.data.setdefault("favorites", [])
        if url in items:
            items.remove(url)
            added = False
        else:
            items.append(url)
            added = True
        self.save()
        return added
