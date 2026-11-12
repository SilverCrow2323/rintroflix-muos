# -*- coding: utf-8 -*-
"""M3U/M3U8 parser with per-channel HTTP headers and XMLTV source discovery."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

ATTR_RE = re.compile(r'''([A-Za-z0-9_-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s,]+))''')


def _attrs(line):
    return {m.group(1).lower(): next((g for g in m.groups()[1:] if g is not None), "")
            for m in ATTR_RE.finditer(line)}


@dataclass
class Channel:
    name: str
    url: str
    tvg_id: str = ""
    tvg_name: str = ""
    logo: str = ""
    group: str = "Ungrouped"
    index: int = 0
    opts: dict = field(default_factory=dict)

    def epg_keys(self):
        values = [self.tvg_id, self.tvg_name, self.name]
        return [str(x).strip().casefold() for x in values if x and str(x).strip()]


class Playlist:
    def __init__(self):
        self.channels = []
        self.epg_urls = []
        self.groups = []

    def build_groups(self):
        seen = set()
        self.groups = []
        for ch in self.channels:
            if ch.group not in seen:
                seen.add(ch.group)
                self.groups.append(ch.group)


def parse_m3u(content):
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig", "replace")
    content = str(content).lstrip("\ufeff")
    playlist = Playlist()
    pending = None
    for raw in content.splitlines():
        line = raw.strip().lstrip("\ufeff")
        if not line:
            continue
        upper = line.upper()
        if upper.startswith("#EXTM3U"):
            attrs = _attrs(line)
            for key in ("url-tvg", "x-tvg-url", "tvg-url"):
                for url in attrs.get(key, "").split(","):
                    url = url.strip()
                    if url and url not in playlist.epg_urls:
                        playlist.epg_urls.append(url)
            continue
        if upper.startswith("#EXTINF"):
            attrs = _attrs(line)
            name = line.split(",", 1)[1].strip() if "," in line else ""
            pending = {
                "name": name or attrs.get("tvg-name") or "Channel",
                "tvg_id": attrs.get("tvg-id", ""),
                "tvg_name": attrs.get("tvg-name", ""),
                "logo": attrs.get("tvg-logo", ""),
                "group": attrs.get("group-title", "Ungrouped"),
                "opts": {"headers": {}},
            }
            continue
        if pending is None:
            if line.startswith(("http://", "https://", "rtmp://", "rtsp://", "udp://")):
                label = urlparse(line).path.rsplit("/", 1)[-1] or "Channel %d" % (len(playlist.channels) + 1)
                playlist.channels.append(Channel(label, line, index=len(playlist.channels)))
            continue
        if upper.startswith("#EXTVLCOPT:"):
            value = line.split(":", 1)[1]
            if "=" in value:
                key, val = value.split("=", 1)
                key, val = key.strip().lower(), val.strip()
                if key == "http-user-agent":
                    pending["opts"]["user-agent"] = val
                elif key in ("http-referrer", "http-referer"):
                    pending["opts"]["referrer"] = val
                elif key == "http-origin":
                    pending["opts"]["origin"] = val
                elif key.startswith("http-header-"):
                    pending["opts"]["headers"][key[12:]] = val
            continue
        if upper.startswith("#EXTHTTP:"):
            try:
                headers = json.loads(line.split(":", 1)[1])
                if isinstance(headers, dict):
                    pending["opts"]["headers"].update({str(k): str(v) for k, v in headers.items()})
            except (ValueError, TypeError):
                pass
            continue
        if line.startswith("#"):
            continue
        if line.startswith(("http://", "https://", "rtmp://", "rtsp://", "udp://")):
            opts = pending.get("opts", {})
            if not opts.get("headers"):
                opts.pop("headers", None)
            playlist.channels.append(Channel(
                pending["name"], line, pending["tvg_id"], pending["tvg_name"],
                pending["logo"], pending["group"] or "Ungrouped",
                len(playlist.channels), opts))
            pending = None
    playlist.build_groups()
    return playlist


def load_playlist(entry, user_agent=None):
    if entry.get("type") == "url":
        from .net import fetch_text
        data = fetch_text(entry["source"], user_agent)
    else:
        path = Path(entry["source"])
        data = path.read_text(encoding="utf-8-sig", errors="replace")
    result = parse_m3u(data)
    if not result.channels:
        raise ValueError("The playlist does not contain any recognised channels.")
    return result
