# -*- coding: utf-8 -*-
"""XMLTV multi-source EPG with gzip support, cache, id/name matching."""
from __future__ import annotations

import io
import re
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
    if len(bits) not in (1, 2) or not re.fullmatch(r"\d{14}", bits[0]):
        return None
    try:
        dt = datetime.strptime(bits[0], "%Y%m%d%H%M%S")
    except ValueError:
        return None

    offset = timedelta(0)
    if len(bits) == 2:
        zone = bits[1]
        if not re.fullmatch(r"[+-]\d{4}", zone):
            return None
        hours, minutes = int(zone[1:3]), int(zone[3:5])
        if hours > 14 or minutes > 59 or (hours == 14 and minutes != 0):
            return None
        offset = timedelta(hours=hours, minutes=minutes)
        if zone[0] == "-":
            offset = -offset
    return (dt - offset).replace(tzinfo=timezone.utc).timestamp()


def _local_name(element):
    return element.tag.rsplit("}", 1)[-1]


def _child_text(element, wanted):
    for child in element:
        if _local_name(child) == wanted:
            return (child.text or "").strip()
    return ""


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
        parsed = {}
        for _event, element in ET.iterparse(io.BytesIO(data), events=("end",)):
            tag = _local_name(element)
            if tag == "channel":
                channel_id = (element.get("id") or "").strip()
                names = [
                    (child.text or "").strip()
                    for child in element
                    if _local_name(child) == "display-name" and (child.text or "").strip()
                ]
                if channel_id:
                    channel_names[channel_id] = names
                element.clear()
            elif tag == "programme":
                channel_id = (element.get("channel") or "").strip()
                start = _parse_xmltv_time(element.get("start"))
                stop_value = element.get("stop")
                stop = _parse_xmltv_time(stop_value) if stop_value else None
                if stop_value and stop is None:
                    element.clear()
                    continue
                if channel_id and start is not None and (stop is None or stop > start):
                    item = Programme(
                        start,
                        stop if stop is not None else start + 1800,
                        _child_text(element, "title") or "Programme",
                        _child_text(element, "desc"),
                    )
                    keys = {_norm(channel_id)} | {_norm(x) for x in channel_names.get(channel_id, [])}
                    for key in keys:
                        if key:
                            parsed.setdefault(key, []).append(item)
                element.clear()

        # Commit this source only after the complete XML document parsed.
        # A truncated/malformed source must not leak partial programmes.
        for key, items in parsed.items():
            self.by_key.setdefault(key, []).extend(items)

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
