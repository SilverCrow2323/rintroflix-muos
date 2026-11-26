import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rintroflix.addons import AddonError, AddonManager


class MemoryConfig:
    def __init__(self, enabled):
        self.values = {"enabled_addons": list(enabled)}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


class FakeApp:
    def __init__(self, enabled):
        self.cfg = MemoryConfig(enabled)


class AddonRemovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def _write_addon(self, addon_id, requires=None):
        folder = self.root / addon_id
        folder.mkdir()
        (folder / "addon.py").write_text("def register(api):\n    return []\n", encoding="utf-8")
        manifest = {
            "id": addon_id,
            "version": "1.0.0",
            "api_version": 1,
            "entrypoint": "addon.py",
            "requires": requires or {},
        }
        (folder / "addon.json").write_text(json.dumps(manifest), encoding="utf-8")
        return folder

    def _manager(self, enabled):
        app = FakeApp(enabled)
        with patch("rintroflix.addons.C.ADDON_DIR", self.root):
            manager = AddonManager(app)
        return manager, app

    def test_dependency_guard_runs_before_any_package_is_deleted(self):
        base = self._write_addon("base-addon")
        self._write_addon("dependent-addon", {"addons": {"base-addon": ">=1.0.0"}})
        manager, app = self._manager(["base-addon", "dependent-addon"])

        with self.assertRaisesRegex(AddonError, "Disable dependent add-ons first: dependent-addon"):
            manager.remove("base-addon")

        self.assertTrue(base.is_dir())
        self.assertEqual(app.cfg.get("enabled_addons"), ["base-addon", "dependent-addon"])

    def test_successful_removal_disables_and_deletes_the_package(self):
        package = self._write_addon("sample-addon")
        self._write_addon("unrelated-addon")
        manager, app = self._manager(["sample-addon", "unrelated-addon"])

        self.assertTrue(manager.remove("sample-addon"))

        self.assertFalse(package.exists())
        self.assertEqual(app.cfg.get("enabled_addons"), ["unrelated-addon"])
        self.assertEqual([item["manifest"]["id"] for item in manager.items], ["unrelated-addon"])

    def test_filesystem_failure_leaves_package_installed_but_disabled(self):
        package = self._write_addon("sample-addon")
        manager, app = self._manager(["sample-addon"])

        with patch("rintroflix.addons.shutil.rmtree", side_effect=OSError("storage busy")):
            with self.assertRaisesRegex(OSError, "storage busy"):
                manager.remove("sample-addon")

        self.assertTrue(package.is_dir())
        self.assertEqual(app.cfg.get("enabled_addons"), [])
        self.assertEqual([item["manifest"]["id"] for item in manager.items], ["sample-addon"])

    def test_removing_an_unknown_addon_is_a_noop(self):
        manager, app = self._manager([])

        self.assertFalse(manager.remove("missing-addon"))
        self.assertEqual(app.cfg.get("enabled_addons"), [])


if __name__ == "__main__":
    unittest.main()
