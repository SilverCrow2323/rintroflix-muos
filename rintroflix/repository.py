# -*- coding: utf-8 -*-
"""HTTPS add-on repository client with bounded downloads and SHA-256 checks."""
from __future__ import annotations
import hashlib
import json
import re
import tempfile
from pathlib import Path
from urllib.parse import urljoin, urlparse
from .net import fetch_bytes

MAX_INDEX_BYTES = 1024 * 1024
MAX_PACKAGE_BYTES = 12 * 1024 * 1024
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

class RepositoryError(ValueError):
    pass

class RepositoryClient:
    def __init__(self, addon_manager, fetcher=None):
        self.manager = addon_manager
        self.fetcher = fetcher or fetch_bytes

    @staticmethod
    def _https(url):
        parsed = urlparse(str(url or ""))
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise RepositoryError("Repository and package URLs must use HTTPS")
        return url

    def load_index(self, index_url):
        index_url = self._https(index_url)
        try:
            raw = self.fetcher(index_url, max_bytes=MAX_INDEX_BYTES)
            data = json.loads(raw.decode("utf-8-sig"))
        except RepositoryError:
            raise
        except Exception as exc:
            raise RepositoryError("Cannot read repository index: %s" % str(exc)[:120])
        if not isinstance(data, dict) or data.get("format") != 1 or not isinstance(data.get("addons"), list):
            raise RepositoryError("Unsupported repository index format")
        entries, seen = [], set()
        for item in data["addons"]:
            if not isinstance(item, dict):
                continue
            addon_id = str(item.get("id", ""))
            version = str(item.get("version", ""))
            digest = str(item.get("sha256", "")).lower()
            package = urljoin(index_url, str(item.get("url", "")))
            self._https(package)
            if addon_id in seen or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,47}", addon_id):
                raise RepositoryError("Invalid or duplicate add-on ID in repository")
            if not re.fullmatch(r"\d+(?:\.\d+){0,2}(?:[-+][0-9A-Za-z.-]+)?", version) or not _SHA256.fullmatch(digest):
                raise RepositoryError("Invalid version or SHA-256 for " + addon_id)
            seen.add(addon_id)
            entries.append({"id": addon_id, "name": str(item.get("name", addon_id))[:80],
                            "version": version, "description": str(item.get("description", ""))[:180],
                            "sha256": digest, "url": package})
        return entries

    def install(self, entry):
        package_url = self._https(entry.get("url"))
        expected = str(entry.get("sha256", "")).lower()
        if not _SHA256.fullmatch(expected):
            raise RepositoryError("Missing or invalid package digest")
        try:
            payload = self.fetcher(package_url, max_bytes=MAX_PACKAGE_BYTES)
        except Exception as exc:
            raise RepositoryError("Package download failed: %s" % str(exc)[:100])
        actual = hashlib.sha256(payload).hexdigest()
        if actual != expected:
            raise RepositoryError("Package SHA-256 mismatch; installation refused")
        suffix = ".rfxaddon"
        with tempfile.NamedTemporaryFile(prefix="rfx-repo-", suffix=suffix, delete=False) as stream:
            path = Path(stream.name)
            stream.write(payload)
        try:
            manifest = self.manager.install_archive(path)
            if manifest.get("id") != entry.get("id") or manifest.get("version") != entry.get("version"):
                self.manager.remove(manifest.get("id", ""))
                raise RepositoryError("Package identity/version does not match repository index")
            return manifest
        finally:
            path.unlink(missing_ok=True)
