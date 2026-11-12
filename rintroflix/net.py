# -*- coding: utf-8 -*-
"""Small HTTPS-safe downloader and bounded disk cache."""
from __future__ import annotations

import gzip
import hashlib
import io
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

MAX_DOWNLOAD = 64 * 1024 * 1024


def fetch_bytes(url, user_agent=None, timeout=18, max_bytes=MAX_DOWNLOAD):
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        raise ValueError("Only HTTP(S) URLs are supported.")
    headers = {"User-Agent": user_agent or "RintrofliX/1.0"}
    req = urllib.request.Request(url, headers=headers)
    # urllib uses the system CA store and verifies TLS certificates by default.
    with urllib.request.urlopen(req, timeout=timeout) as response:
        length = response.headers.get("Content-Length")
        if length and int(length) > max_bytes:
            raise ValueError("Resource too large (limit %d MB)." % (max_bytes // 1048576))
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("Resource exceeds the configured safety limit.")
    if data.startswith(b"\x1f\x8b"):
        # Read at most limit+1 bytes: a small gzip must not expand without bound.
        with gzip.GzipFile(fileobj=io.BytesIO(data), mode="rb") as compressed:
            data = compressed.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError("Decompressed archive exceeds the configured safety limit.")
    return data


def fetch_text(url, user_agent=None):
    return fetch_bytes(url, user_agent).decode("utf-8-sig", "replace")


def cached_fetch(url, cache_dir, max_age_hours=12, user_agent=None):
    root = Path(cache_dir)
    root.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    path = root / (key + ".xml")
    age = max(0, int(max_age_hours)) * 3600
    if path.is_file() and age and time.time() - path.stat().st_mtime < age:
        return path.read_bytes(), True
    data = fetch_bytes(url, user_agent, timeout=25)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    return data, False
