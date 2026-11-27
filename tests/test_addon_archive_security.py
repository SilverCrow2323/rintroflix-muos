from __future__ import annotations
import io
import json
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

from rintroflix.addons import AddonError, AddonManager, MAX_EXPANDED_BYTES

class FakeConfig:
    def __init__(self): self.values = {}
    def get(self, key, default=None): return self.values.get(key, default)
    def set(self, key, value): self.values[key] = value

class FakeApp:
    def __init__(self):
        self.cfg = FakeConfig()
        self.logs = []
    def log_addon(self, addon_id, message): self.logs.append((addon_id, message))
    def toast(self, message, ok=True): pass

def manifest(addon_id="sample-source"):
    return {"id": addon_id, "name": "Sample Source", "version": "1.0.0",
            "api_version": 2, "entrypoint": "addon.py", "capabilities": ["source"]}

def write_package(path: Path, members: dict[str, bytes]):
    with zipfile.ZipFile(path, "w") as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    return path

class AddonArchiveSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "addons"
        self.root.mkdir()
        self.app = FakeApp()
        self.manager = AddonManager.__new__(AddonManager)
        self.manager.app = self.app
        self.manager.root = self.root
        self.manager.items = []
        self.manager.actions = []
        self.manager.sources = []
        self.manager.errors = []

    def tearDown(self):
        self.temp.cleanup()

    def package(self, members, name="sample.rfxaddon"):
        return write_package(Path(self.temp.name) / name, members)

    def valid_members(self):
        return {"sample/addon.json": json.dumps(manifest()).encode(),
                "sample/addon.py": b"def register(api):\n    return []\n",
                "sample/README.md": b"Sample source add-on\n"}

    def test_installs_valid_single_root_package(self):
        archive = self.package(self.valid_members())
        result = self.manager.install_archive(archive)
        self.assertEqual(result["id"], "sample-source")
        self.assertTrue((self.root / "sample-source" / "addon.py").is_file())
        self.assertEqual(len(self.manager.items), 1)

    def test_rejects_parent_traversal(self):
        members = self.valid_members()
        members["sample/../../escape.py"] = b"bad"
        with self.assertRaises(AddonError):
            self.manager.install_archive(self.package(members))

    def test_rejects_windows_path_separator(self):
        members = self.valid_members()
        members["sample\\escape.py"] = b"bad"
        with self.assertRaises(AddonError):
            self.manager.install_archive(self.package(members))

    def test_rejects_duplicate_archive_paths(self):
        archive = Path(self.temp.name) / "duplicate.zip"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("sample/addon.json", json.dumps(manifest()))
                z.writestr("sample/addon.json", json.dumps(manifest()))
                z.writestr("sample/addon.py", "def register(api): return []")
        with self.assertRaises(AddonError):
            self.manager.install_archive(archive)

    def test_rejects_multiple_manifests(self):
        members = self.valid_members()
        members["other/addon.json"] = json.dumps(manifest("other-source")).encode()
        with self.assertRaises(AddonError):
            self.manager.install_archive(self.package(members))

    def test_rejects_unsupported_file_types(self):
        members = self.valid_members()
        members["sample/payload.bin"] = b"not allowed"
        with self.assertRaises(AddonError):
            self.manager.install_archive(self.package(members))

    def test_rejects_oversized_member_count(self):
        members = self.valid_members()
        for index in range(520):
            members[f"sample/docs/{index}.txt"] = b"x"
        with self.assertRaises(AddonError):
            self.manager.install_archive(self.package(members))

    def test_failed_install_leaves_no_staging_directory(self):
        with self.assertRaises(AddonError):
            self.manager.install_archive(self.package({"sample/../escape.py": b"bad"}))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_rejects_actual_stream_larger_than_declared_zip_member_size(self):
        archive = self.package(self.valid_members())
        original_open = zipfile.ZipFile.open

        def dishonest_open(zip_file, name, mode="r", pwd=None, *, force_zip64=False):
            member_name = getattr(name, "filename", name)
            if member_name == "sample/addon.py":
                return io.BytesIO(b"x" * (MAX_EXPANDED_BYTES + 1))
            return original_open(zip_file, name, mode, pwd, force_zip64=force_zip64)

        with patch("rintroflix.addons.zipfile.ZipFile.open", new=dishonest_open):
            with self.assertRaises(AddonError):
                self.manager.install_archive(archive)
        self.assertEqual(list(self.root.iterdir()), [], "oversized streamed payload must not leave staged files")

    def test_discovery_rejects_symlinked_addon_directories(self):
        outside = Path(self.temp.name) / "outside-addon"
        outside.mkdir()
        (outside / "addon.json").write_text(json.dumps(manifest()), encoding="utf-8")
        (outside / "addon.py").write_text("def register(api): return []", encoding="utf-8")
        (self.root / "linked-addon").symlink_to(outside, target_is_directory=True)
        self.assertEqual(self.manager.discover(), [])
        self.assertTrue(any("symlink" in message.lower() for _, message in self.manager.errors))

    def test_manifest_rejects_symlinked_entrypoint_and_nested_files(self):
        folder = self.root / "sample"
        folder.mkdir()
        (folder / "addon.json").write_text(json.dumps(manifest()), encoding="utf-8")
        outside = Path(self.temp.name) / "outside.py"
        outside.write_text("def register(api): return []", encoding="utf-8")
        (folder / "addon.py").symlink_to(outside)
        with self.assertRaisesRegex(AddonError, "Symlinks are not allowed"):
            AddonManager._read_manifest(folder)
        (folder / "addon.py").unlink()
        (folder / "addon.py").write_text("def register(api): return []", encoding="utf-8")
        (folder / "data.json").symlink_to(outside)
        with self.assertRaisesRegex(AddonError, "Symlinks are not allowed"):
            AddonManager._read_manifest(folder)

    def test_install_rejects_symlinked_addon_root(self):
        outside = Path(self.temp.name) / "outside-root"
        outside.mkdir()
        link = Path(self.temp.name) / "addons-link"
        link.symlink_to(outside, target_is_directory=True)
        self.manager.root = link
        archive = self.package(self.valid_members())
        with self.assertRaisesRegex(AddonError, "real directory"):
            self.manager.install_archive(archive)
        self.assertEqual(list(outside.iterdir()), [])

if __name__ == "__main__":
    unittest.main()
