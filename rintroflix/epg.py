# -*- coding: utf-8 -*-
"""XMLTV multi-source EPG with gzip support, cache, id/name matching."""
from __future__ import annotations

import io
import time
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from . import config as C
from . import net


def _norm(value):
    value = unicodedata.normalize("NFKD", str(value or "").casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return " ".join("".join(ch if ch.isalnum() else " " for ch in value).split())


def _parse_xmltv_time(value):
    if not value:
        return None
    bits = value.strip().split()
    raw = bits[0][:14].ljust(14, "0")
    try:
        dt = datetime.strptime(raw, "%Y%m%d%H%M%S")
    except ValueError:
        return None
    offset = timedelta(0)
    if len(bits) > 1 and len(bits[1]) == 5 and bits[1][0] in "+-":
        try:
            offset = timedelta(hours=int(bits[1][1:3]), minutes=int(bits[1][3:5]))
            if bits[1][0] == "-":
                offset = -offset
        except ValueError:
            pass
    return (dt - offset).replace(tzinfo=timezone.utc).timestamp()


@dataclass
class Programme:
    start: float
    stop: float
    title: str
    desc: str = ""


class EPG:
    def __init__(self):
        self.by_key = {}
        self.sources_ok = []
        self.sources_err = []
        self.loaded_at = 0

    def load(self, urls, user_agent=None, max_age_hours=12):
        self.by_key.clear()
        self.sources_ok, self.sources_err = [], []
        for url in urls:
            try:
                data, cached = net.cached_fetch(url, C.EPG_CACHE_DIR, max_age_hours, user_agent)
                self._parse(data)
                self.sources_ok.append(url + (" [cache]" if cached else ""))
            except Exception as exc:
                self.sources_err.append((url, str(exc)[:120]))
        for items in self.by_key.values():
            items.sort(key=lambda p: p.start)
        self.loaded_at = time.time()

    def _parse(self, data):
        channel_names = {}
        for _event, element in ET.iterparse(io.BytesIO(data), events=("end",)):
            tag = element.tag.rsplit("}", 1)[-1]
            if tag == "channel":
                channel_id = (element.get("id") or "").strip()
                names = [x.text.strip() for x in element.findall("display-name") if x.text]
                if channel_id:
                    channel_names[channel_id] = names
                element.clear()
            elif tag == "programme":
                channel_id = (element.get("channel") or "").strip()
                start = _parse_xmltv_time(element.get("start"))
                stop = _parse_xmltv_time(element.get("stop"))
                title_el = element.find("title")
                desc_el = element.find("desc")
                title = (title_el.text or "").strip() if title_el is not None else ""
                desc = (desc_el.text or "").strip() if desc_el is not None else ""
                if channel_id and start is not None:
                    item = Programme(start, stop or start + 1800, title or "Programme", desc)
                    keys = {_norm(channel_id)} | {_norm(x) for x in channel_names.get(channel_id, [])}
                    for key in keys:
                        if key:
                            self.by_key.setdefault(key, []).append(item)
                element.clear()

    def programmes_for(self, channel):
        for key in channel.epg_keys():
            found = self.by_key.get(_norm(key))
            if found:
                return found
        return []

    def now_next(self, channel, now=None):
        now = time.time() if now is None else now
        current = following = None
        for item in self.programmes_for(channel):
            if item.start <= now < item.stop:
                current = item
            elif item.start > now:
                following = item
                break
        return current, following

    def window(self, channel, start, stop):
        return [p for p in self.programmes_for(channel) if p.stop > start and p.start < stop]


def collect_epg_urls(cfg, playlist):
    urls = []
    if cfg.get("epg_use_playlist_sources", True) and playlist:
        urls.extend(playlist.epg_urls)
    urls.extend(cfg.get("epg_manual_urls", []))
    return list(dict.fromkeys(u.strip() for u in urls if u and u.strip()))
