# -*- coding: utf-8 -*-
"""Asynchronous, bounded cache for channel logos advertised by M3U tvg-logo."""
from __future__ import annotations

import hashlib
import os
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

import pygame

from . import config as C

MAX_LOGO_BYTES = 512 * 1024
ALLOWED_SCHEMES = ("http", "https")


class LogoCache:
    def __init__(self, user_agent=None, workers=4):
        self.user_agent = user_agent or "RintrofliX/1.0"
        self.root = C.CACHE_DIR / "logos"
        self.root.mkdir(parents=True, exist_ok=True)
        self.executor = ThreadPoolExecutor(max_workers=max(1, min(6, workers)),
                                           thread_name_prefix="rintroflix-logo")
        self.lock = threading.Lock()
        self.pending = set()
        self.loaded = {}
        self.failed = set()
        self._surfaces = {}
        self.closed = False

    @staticmethod
    def _valid(url):
        try:
            parsed = urlparse(str(url))
            return parsed.scheme.lower() in ALLOWED_SCHEMES and bool(parsed.netloc)
        except ValueError:
            return False

    def _path(self, url):
        digest = hashlib.sha256(url.encode("utf-8", "replace")).hexdigest()
        return self.root / (digest + ".img")

    def _download(self, url, target):
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent,
                                                       "Accept": "image/*"})
        with urllib.request.urlopen(request, timeout=12) as response:
            content_type = response.headers.get("Content-Type", "").lower()
            if content_type and not (content_type.startswith("image/") or "octet-stream" in content_type):
                raise ValueError("not an image")
            length = response.headers.get("Content-Length")
            if length and int(length) > MAX_LOGO_BYTES:
                raise ValueError("logo too large")
            data = response.read(MAX_LOGO_BYTES + 1)
        if not data or len(data) > MAX_LOGO_BYTES:
            raise ValueError("logo size limit")
        # Only image signatures known to SDL_image / pygame are accepted.
        if not (data.startswith(b"\x89PNG\r\n\x1a\n") or data.startswith(b"\xff\xd8\xff") or
                data.startswith((b"GIF87a", b"GIF89a")) or data.startswith(b"RIFF") and b"WEBP" in data[:16]):
            raise ValueError("unsupported image format")
        temp = target.with_suffix(".tmp")
        temp.write_bytes(data)
        os.replace(temp, target)

    def request(self, url):
        if not url or not self._valid(url) or self.closed:
            return
        target = self._path(url)
        if target.is_file():
            return
        with self.lock:
            if url in self.pending or url in self.failed:
                return
            self.pending.add(url)
        def task():
            try:
                self._download(url, target)
            except Exception:
                with self.lock:
                    self.failed.add(url)
            finally:
                with self.lock:
                    self.pending.discard(url)
        try:
            self.executor.submit(task)
        except RuntimeError:
            with self.lock:
                self.pending.discard(url)

    def prefetch(self, channels, limit=96):
        count = 0
        for channel in channels:
            if channel.logo:
                self.request(channel.logo)
                count += 1
                if count >= limit:
                    break

    def get(self, url, size=48):
        if not url:
            return None
        key = (url, int(size))
        if key in self._surfaces:
            return self._surfaces[key]
        path = self._path(url) if self._valid(url) else None
        if path and path.is_file():
            try:
                image = pygame.image.load(str(path))
                if image.get_width() and image.get_height():
                    image = image.convert_alpha()
                    iw, ih = image.get_size()
                    ratio = min(float(size) / iw, float(size) / ih)
                    dims = (max(1, int(iw * ratio)), max(1, int(ih * ratio)))
                    image = pygame.transform.smoothscale(image, dims)
                    self._surfaces[key] = image
                    return image
            except (pygame.error, OSError, ValueError):
                try:
                    path.unlink()
                except OSError:
                    pass
        self.request(url)
        return None

    def close(self):
        self.closed = True
        self.executor.shutdown(wait=False, cancel_futures=True)
        self._surfaces.clear()
