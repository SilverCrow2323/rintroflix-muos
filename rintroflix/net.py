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
from urllib.parse import urlparse

MAX_DOWNLOAD = 64 * 1024 * 1024


def _is_https_url(url):
    """Return whether a URL is HTTPS with a real host and no embedded credentials."""
    parsed = urlparse(str(url or ""))
    return (
        parsed.scheme.lower() == "https"
        and bool(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
    )


class _HTTPSOnlyRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject insecure or credential-bearing redirect targets before following them."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _is_https_url(newurl):
            raise ValueError("HTTPS redirect refused; repository downloads must remain on HTTPS.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_bytes(url, user_agent=None, timeout=18, max_bytes=MAX_DOWNLOAD,
                require_https=False):
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        raise ValueError("Only HTTP(S) URLs are supported.")
    if require_https and not _is_https_url(url):
        raise ValueError("HTTPS is required for this download.")

    headers = {"User-Agent": user_agent or "RintrofliX/1.0"}
    req = urllib.request.Request(url, headers=headers)
    # urllib uses the system CA store and verifies TLS certificates by default.
    # In strict mode, reject every redirect hop before following it, then verify
    # the final response URL as a second boundary check.
    opener = urllib.request.build_opener(_HTTPSOnlyRedirectHandler()) if require_https else None
    response_context = opener.open(req, timeout=timeout) if opener else urllib.request.urlopen(req, timeout=timeout)
    with response_context as response:
        # urllib follows redirects automatically. Check the final URL before
        # accepting bytes, otherwise an HTTPS repository can silently downgrade
        # its index or package request to plain HTTP.
        if require_https and not _is_https_url(response.geturl()):
            raise ValueError("HTTPS redirect refused; repository downloads must remain on HTTPS.")
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
