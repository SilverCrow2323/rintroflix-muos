import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rintroflix.addons import AddonError, AddonManager
from rintroflix.m3u import parse_m3u
from rintroflix.repository import RepositoryClient, RepositoryError


class PlaylistTests(unittest.TestCase):
    def test_extended_m3u_metadata_and_headers(self):
        playlist = parse_m3u(
            '#EXTM3U url-tvg="https://guide.example/epg.xml"\n'
            '#EXTINF:-1 tvg-id="news.one" tvg-name="News One" group-title="News",News One HD\n'
            '#EXTVLCOPT:http-user-agent=RintroTest/1.0\n'
            '#EXTVLCOPT:http-referrer=https://example.test/\n'
            'https://stream.example/live.m3u8\n'
        )
        self.assertEqual(len(playlist.channels), 1)
        channel = playlist.channels[0]
        self.assertEqual(channel.name, "News One HD")
        self.assertEqual(channel.tvg_id, "news.one")
        self.assertEqual(channel.group, "News")
        self.assertEqual(channel.opts["user-agent"], "RintroTest/1.0")
        self.assertEqual(channel.opts["referrer"], "https://example.test/")
        self.assertEqual(playlist.epg_urls, ["https://guide.example/epg.xml"])


class AddonManifestTests(unittest.TestCase):
    def _folder(self, root, entry="addon.py"):
        folder = Path(root) / "sample-addon"
        folder.mkdir()
        (folder / "addon.py").write_text("# test addon\n", encoding="utf-8")
        manifest = {"id":"sample-addon","name":"Sample","version":"1.2.0","api_version":2,"entrypoint":entry}
        (folder / "addon.json").write_text(json.dumps(manifest), encoding="utf-8")
        return folder

    def test_valid_manifest(self):
        with tempfile.TemporaryDirectory() as root:
            data = AddonManager._read_manifest(self._folder(root))
        self.assertEqual(data["id"], "sample-addon")
        self.assertEqual(data["api_version"], 2)

    def test_entrypoint_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            folder = self._folder(root, "../outside.py")
            with self.assertRaises(AddonError):
                AddonManager._read_manifest(folder)


class RepositoryTests(unittest.TestCase):
    def test_http_and_url_credentials_are_rejected(self):
        for url in ("http://repo.example/index.json", "https://user:pass@repo.example/index.json"):
            with self.subTest(url=url), self.assertRaises(RepositoryError):
                RepositoryClient._https(url)

    def test_index_requires_unique_ids_and_valid_hash(self):
        client = RepositoryClient(object(), fetcher=lambda *_a, **_kw: json.dumps({
            "format": 1,
            "addons": [
                {"id":"sample-addon","version":"1.0.0","sha256":"0"*64,"url":"addon.rfxaddon"},
                {"id":"sample-addon","version":"1.0.1","sha256":"1"*64,"url":"addon2.rfxaddon"}
            ]
        }).encode())
        with self.assertRaises(RepositoryError):
            client.load_index("https://repo.example/index.json")

    def test_package_digest_mismatch_never_calls_installer(self):
        class Manager:
            called = False
            def install_archive(self, _path):
                self.called = True
                raise AssertionError("installer must not run on a digest mismatch")
        manager = Manager()
        payload = b"untrusted package bytes"
        client = RepositoryClient(manager, fetcher=lambda *_a, **_kw: payload)
        entry = {"url":"https://repo.example/addon.rfxaddon","sha256":hashlib.sha256(b"different").hexdigest()}
        with self.assertRaises(RepositoryError):
            client.install(entry)
        self.assertFalse(manager.called)


class PackageBuilderTests(unittest.TestCase):
    def test_builder_creates_single_root_muxapp_with_required_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "RintrofliX-test.muxapp"
            subprocess.run([sys.executable, str(ROOT / "tools/build_muxapp.py"),
                            "--output", str(output)], cwd=ROOT, check=True, capture_output=True, text=True)
            with zipfile.ZipFile(output) as archive:
                self.assertIsNone(archive.testzip())
                names = archive.namelist()
                self.assertTrue(names)
                self.assertTrue(all(name.startswith("RintrofliX/") for name in names))
                for required in ("mux_launch.sh","rintroflix/main.py","rintroflix/ui.py","rintroflix/player.py"):
                    self.assertIn("RintrofliX/" + required, names)
                info = archive.getinfo("RintrofliX/mux_launch.sh")
                self.assertEqual((info.external_attr >> 16) & 0o777, 0o755)

    def test_version_metadata_is_aligned(self):
        version = (ROOT / "VERSION").read_text(encoding="utf-8").split()[-1]
        init = (ROOT / "rintroflix/__init__.py").read_text(encoding="utf-8")
        self.assertIn('__version__ = "%s"' % version, init)


if __name__ == "__main__":
    unittest.main()
