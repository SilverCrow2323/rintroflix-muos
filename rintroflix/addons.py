# -*- coding: utf-8 -*-
"""Local RintrofliX add-on manager (manifest validation + explicit activation)."""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from . import config as C

API_VERSION = 2
SUPPORTED_API_VERSIONS = (1, 2)
MAX_ARCHIVE_BYTES = 12 * 1024 * 1024
MAX_EXPANDED_BYTES = 24 * 1024 * 1024
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,47}$")
VERSION_RE = re.compile(r"^\d+(?:\.\d+){0,2}(?:[-+][0-9A-Za-z.-]+)?$")
CONSTRAINT_RE = re.compile(r"^(>=|<=|==|>|<|~=)?\s*(\d+(?:\.\d+){0,2})$")


def _version_tuple(value):
    match = re.match(r"^(\d+(?:\.\d+){0,2})", str(value or ""))
    if not match:
        return (0, 0, 0)
    return tuple((list(map(int, match.group(1).split("."))) + [0, 0])[:3])


def _satisfies(version, constraint):
    match = CONSTRAINT_RE.fullmatch(str(constraint or ""))
    if not match:
        return False
    operator, wanted = match.groups()
    actual, expected = _version_tuple(version), _version_tuple(wanted)
    operator = operator or "=="
    if operator == ">=": return actual >= expected
    if operator == "<=": return actual <= expected
    if operator == ">": return actual > expected
    if operator == "<": return actual < expected
    if operator == "~=": return actual >= expected and actual[:2] == expected[:2]
    return actual == expected


class AddonError(ValueError):
    pass


class AddonAPI:
    """Versioned extension API. API v1 is actions-only; v2 adds sources/playback."""
    def __init__(self, app, addon_id, api_version=1):
        self.app = app
        self.addon_id = addon_id
        self.api_version = int(api_version)

    def toast(self, message, ok=True):
        self.app.toast("[%s] %s" % (self.addon_id, str(message)[:100]), ok=ok)

    def log(self, message):
        self.app.log_addon(self.addon_id, message)

    def get_setting(self, key, default=None):
        return self.app.cfg.get("addon:%s:%s" % (self.addon_id, key), default)

    def set_setting(self, key, value):
        self.app.cfg.set("addon:%s:%s" % (self.addon_id, key), value)

    def channels(self):
        """Read-only snapshot of channels from the core playlist."""
        return tuple(self.app.playlist.channels if self.app.playlist else ())

    def register_source(self, source_id, label, loader, play=None):
        """Register a source provider. Available only to API v2 add-ons.

        loader() must return an iterable of rintroflix.m3u.Channel instances.
        Optional play(channel) may handle playback itself and return True; False
        or None delegates to the core playback adapter.
        """
        if self.api_version < 2:
            raise AddonError("register_source requires add-on API v2")
        if not callable(loader):
            raise AddonError("Source loader must be callable")
        if play is not None and not callable(play):
            raise AddonError("Source play hook must be callable")
        self.app.addons.register_source(self.addon_id, source_id, label, loader, play)


class AddonManager:
    def __init__(self, app):
        self.app = app
        self.root = C.ADDON_DIR
        self.root.mkdir(parents=True, exist_ok=True)
        self.items = []
        self.actions = []
        self.sources = []
        self.errors = []
        self.discover(load_enabled=False)

    @staticmethod
    def _read_manifest(folder):
        path = folder / "addon.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise AddonError("Invalid addon.json: %s" % exc)
        if not isinstance(data, dict):
            raise AddonError("addon.json must contain an object")
        addon_id = str(data.get("id", ""))
        if not ID_RE.fullmatch(addon_id):
            raise AddonError("Invalid add-on ID")
        try:
            api_version = int(data.get("api_version", 0))
        except (TypeError, ValueError):
            raise AddonError("Invalid add-on API version")
        if api_version not in SUPPORTED_API_VERSIONS:
            raise AddonError("Unsupported add-on API version (supported: 1, 2)")
        entry = str(data.get("entrypoint", "addon.py"))
        p = PurePosixPath(entry)
        if p.is_absolute() or ".." in p.parts or not entry.endswith(".py"):
            raise AddonError("Invalid add-on entry point")
        if not (folder / Path(*p.parts)).is_file():
            raise AddonError("Add-on entry point is missing")
        data.setdefault("name", addon_id)
        data.setdefault("version", "0.0.0")
        data.setdefault("description", "No description provided")
        data.setdefault("capabilities", [])
        version = str(data.get("version", "0.0.0"))
        if not VERSION_RE.fullmatch(version):
            raise AddonError("Invalid add-on version")
        data["version"] = version
        requires = data.get("requires", {})
        if not isinstance(requires, dict):
            raise AddonError("requires must be an object")
        app_constraint = requires.get("rintroflix", "")
        if app_constraint and not CONSTRAINT_RE.fullmatch(str(app_constraint)):
            raise AddonError("Invalid RintrofliX version constraint")
        addon_requirements = requires.get("addons", {})
        if not isinstance(addon_requirements, dict):
            raise AddonError("requires.addons must be an object")
        for dependency_id, constraint in addon_requirements.items():
            if not ID_RE.fullmatch(str(dependency_id)) or not CONSTRAINT_RE.fullmatch(str(constraint)):
                raise AddonError("Invalid add-on dependency declaration")
        data["requires"] = {"rintroflix": app_constraint, "addons": addon_requirements}
        return data

    def discover(self, load_enabled=False):
        enabled = set(self.app.cfg.get("enabled_addons", []))
        self.items = []
        self.errors = []
        for folder in sorted(self.root.iterdir()) if self.root.exists() else []:
            if not folder.is_dir() or folder.name.startswith("."):
                continue
            try:
                manifest = self._read_manifest(folder)
                self.items.append({"folder": folder, "manifest": manifest,
                                   "enabled": manifest["id"] in enabled})
            except AddonError as exc:
                self.errors.append((folder.name, str(exc)))
        if load_enabled:
            self.load_enabled()
        return self.items

    def register_source(self, addon_id, source_id, label, loader, play=None):
        source_id = str(source_id or "").strip().lower()
        if not ID_RE.fullmatch(source_id):
            raise AddonError("Invalid source ID")
        if any(item["id"] == source_id for item in self.sources):
            raise AddonError("Duplicate source ID: " + source_id)
        self.sources.append({"id": source_id, "addon_id": addon_id,
                             "label": str(label or source_id)[:64],
                             "loader": loader, "play": play})

    def channels(self):
        """Load registered source channels; isolate provider failures."""
        from .m3u import Channel
        result = []
        for source in self.sources:
            try:
                provided = source["loader"]()
                if provided is None:
                    continue
                for channel in provided:
                    if not isinstance(channel, Channel):
                        raise AddonError("Source %s returned a non-Channel item" % source["id"])
                    channel._rfx_source_id = source["id"]
                    channel._rfx_source_label = source["label"]
                    result.append(channel)
            except Exception as exc:
                self.errors.append((source["addon_id"], "Source %s failed: %s" % (source["id"], str(exc)[:100])))
                self.app.log_addon(source["addon_id"], "Source %s failed: %s" % (source["id"], exc))
        return result

    def play_channel(self, channel):
        source_id = getattr(channel, "_rfx_source_id", None)
        if not source_id:
            return False
        source = next((item for item in self.sources if item["id"] == source_id), None)
        if not source or not source.get("play"):
            return False
        try:
            return source["play"](channel) is True
        except Exception as exc:
            self.app.log_addon(source["addon_id"], "Playback hook failed: %s" % exc)
            self.app.toast("Source playback failed", ok=False)
            return True

    def load_enabled(self):
        self.actions = []
        self.sources = []
        enabled = set(self.app.cfg.get("enabled_addons", []))
        for item in self.items:
            manifest = item["manifest"]
            addon_id = manifest["id"]
            if addon_id not in enabled:
                continue
            try:
                problems = self.compatibility_errors(manifest, enabled)
                if problems:
                    raise AddonError("; ".join(problems))
                entry = item["folder"] / manifest.get("entrypoint", "addon.py")
                spec = importlib.util.spec_from_file_location("rintroflix_addon_" + addon_id, str(entry))
                if spec is None or spec.loader is None:
                    raise AddonError("Cannot load entry point")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                register = getattr(module, "register", None)
                if not callable(register):
                    raise AddonError("Add-on must export register(api)")
                api_version = int(manifest.get("api_version", 1))
                registered = register(AddonAPI(self.app, addon_id, api_version)) or []
                if not isinstance(registered, (tuple, list)):
                    raise AddonError("register(api) must return a list")
                for action in registered:
                    if not isinstance(action, dict) or not callable(action.get("action")):
                        continue
                    label = str(action.get("label", "Add-on action"))[:64]
                    self.actions.append({"addon_id": addon_id, "label": label,
                                         "description": str(action.get("description", ""))[:100],
                                         "action": action["action"]})
            except Exception as exc:
                self.errors.append((addon_id, "Load failed: %s" % str(exc)[:120]))

    def compatibility_errors(self, manifest, enabled_ids=None):
        """Return unmet runtime/add-on requirements without executing code."""
        from .config import APP_VERSION
        errors = []
        requires = manifest.get("requires", {})
        app_constraint = requires.get("rintroflix", "")
        if app_constraint and not _satisfies(APP_VERSION, app_constraint):
            errors.append("Requires RintrofliX %s (current %s)" % (app_constraint, APP_VERSION))
        enabled = set(self.app.cfg.get("enabled_addons", []) if enabled_ids is None else enabled_ids)
        installed = {item["manifest"]["id"]: item["manifest"] for item in self.items}
        for dependency_id, constraint in requires.get("addons", {}).items():
            dependency = installed.get(dependency_id)
            if dependency_id not in enabled:
                errors.append("Dependency %s is not enabled" % dependency_id)
            elif dependency is None:
                errors.append("Dependency %s is not installed" % dependency_id)
            elif not _satisfies(dependency.get("version", "0.0.0"), constraint):
                errors.append("Dependency %s requires version %s" % (dependency_id, constraint))
        return errors

    def set_enabled(self, addon_id, enabled):
        ids = list(self.app.cfg.get("enabled_addons", []))
        ids = [item for item in ids if item != addon_id]
        if enabled:
            item = next((x for x in self.items if x["manifest"]["id"] == addon_id), None)
            if not item:
                raise AddonError("Add-on is not installed")
            errors = self.compatibility_errors(item["manifest"], ids)
            if errors:
                raise AddonError("; ".join(errors))
            ids.append(addon_id)
        else:
            dependents = []
            for item in self.items:
                other_id = item["manifest"]["id"]
                if other_id in ids and addon_id in item["manifest"].get("requires", {}).get("addons", {}):
                    dependents.append(other_id)
            if dependents:
                raise AddonError("Disable dependent add-ons first: " + ", ".join(dependents))
        self.app.cfg.set("enabled_addons", ids)
        self.discover(load_enabled=False)

    def remove(self, addon_id):
        item = next((x for x in self.items if x["manifest"]["id"] == addon_id), None)
        if not item:
            return False
        shutil.rmtree(item["folder"])
        self.set_enabled(addon_id, False)
        self.discover(load_enabled=False)
        return True

    def install_archive(self, archive_path):
        source = Path(archive_path)
        if not source.is_file() or source.stat().st_size > MAX_ARCHIVE_BYTES:
            raise AddonError("Archive missing or larger than 12 MB")
        if source.suffix.lower() not in (".zip", ".rfxaddon"):
            raise AddonError("Choose a .rfxaddon or .zip package")
        staging = Path(tempfile.mkdtemp(prefix=".addon-install-", dir=str(self.root)))
        try:
            with zipfile.ZipFile(source, "r") as archive:
                members = archive.infolist()
                expanded = sum(max(0, info.file_size) for info in members)
                if expanded > MAX_EXPANDED_BYTES:
                    raise AddonError("Expanded package exceeds 24 MB")
                manifest_member = next((i for i in members if PurePosixPath(i.filename).name == "addon.json"), None)
                if not manifest_member:
                    raise AddonError("Package does not contain addon.json")
                prefix = str(PurePosixPath(manifest_member.filename).parent)
                if prefix == ".":
                    prefix = ""
                for info in members:
                    parts = PurePosixPath(info.filename).parts
                    if PurePosixPath(info.filename).is_absolute() or ".." in parts:
                        raise AddonError("Unsafe path in add-on archive")
                    # Reject symlinks and special files.
                    mode = (info.external_attr >> 16) & 0o170000
                    if mode not in (0, 0o100000, 0o040000):
                        raise AddonError("Special files are not allowed")
                    rel = PurePosixPath(info.filename)
                    if prefix and str(rel).startswith(prefix + "/"):
                        rel = PurePosixPath(*rel.parts[len(PurePosixPath(prefix).parts):])
                    if not rel.parts:
                        continue
                    target = staging.joinpath(*rel.parts)
                    if info.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                        continue
                    # Keep package surface deliberately small and auditable.
                    if target.suffix.lower() not in (".py", ".json", ".md", ".txt", ".png", ".jpg", ".jpeg", ".svg"):
                        raise AddonError("Unsupported file type in add-on: " + target.suffix)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(info) as src, target.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
            manifest = self._read_manifest(staging)
            destination = self.root / manifest["id"]
            if destination.exists():
                raise AddonError("An add-on with this ID is already installed")
            staging.rename(destination)
            self.discover(load_enabled=False)
            return manifest
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        finally:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
