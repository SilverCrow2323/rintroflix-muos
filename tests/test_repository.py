import hashlib
import json
import unittest
from unittest.mock import patch

from rintroflix.repository import RepositoryClient, RepositoryError


class FakeAddonManager:
    def __init__(self, manifest=None):
        self.manifest = manifest or {"id": "demo-addon", "version": "1.2.0"}
        self.installed = []
        self.removed = []

    def install_archive(self, path):
        self.installed.append(path.read_bytes())
        return dict(self.manifest)

    def remove(self, addon_id):
        self.removed.append(addon_id)
        return True


class RepositoryClientTests(unittest.TestCase):
    def setUp(self):
        self.package = b"verified package fixture"
        self.manager = FakeAddonManager()
        self.index = {
            "format": 1,
            "addons": [{
                "id": "demo-addon",
                "version": "1.2.0",
                "url": "packages/demo-addon.rfxaddon",
                "sha256": hashlib.sha256(self.package).hexdigest(),
            }],
        }

    def make_client(self, payload=None):
        body = json.dumps(self.index).encode("utf-8") if payload is None else payload
        def fetcher(url, max_bytes):
            self.assertLessEqual(len(body), max_bytes)
            return self.package if url.endswith(".rfxaddon") else body
        return RepositoryClient(self.manager, fetcher=fetcher)

    def test_rejects_non_https_repository_url_before_fetch(self):
        client = self.make_client()
        with self.assertRaisesRegex(RepositoryError, "HTTPS"):
            client.load_index("http://repo.example/index.json")

    def test_resolves_relative_package_url(self):
        entries = self.make_client().load_index("https://repo.example/catalog/index.json")
        self.assertEqual(entries[0]["url"], "https://repo.example/catalog/packages/demo-addon.rfxaddon")

    def test_rejects_duplicate_addon_ids(self):
        self.index["addons"].append(dict(self.index["addons"][0]))
        with self.assertRaisesRegex(RepositoryError, "duplicate"):
            self.make_client().load_index("https://repo.example/index.json")

    def test_rejects_bad_digest_before_download(self):
        self.index["addons"][0]["sha256"] = "not-a-digest"
        with self.assertRaisesRegex(RepositoryError, "SHA-256"):
            self.make_client().load_index("https://repo.example/index.json")

    def test_digest_mismatch_never_reaches_installer(self):
        client = self.make_client()
        entry = client.load_index("https://repo.example/index.json")[0]
        entry["sha256"] = "0" * 64
        with self.assertRaisesRegex(RepositoryError, "mismatch"):
            client.install(entry)
        self.assertEqual(self.manager.installed, [])

    def test_verified_package_is_installed(self):
        client = self.make_client()
        entry = client.load_index("https://repo.example/index.json")[0]
        self.assertEqual(client.install(entry), self.manager.manifest)
        self.assertEqual(self.manager.installed, [self.package])
        self.assertEqual(self.manager.removed, [])


    @patch("rintroflix.repository.fetch_bytes")
    def test_builtin_fetcher_enables_https_redirect_guard(self, fetch):
        fetch.return_value = b"index"
        client = RepositoryClient(self.manager)
        self.assertEqual(client._fetch("https://repo.example/index.json", 321), b"index")
        fetch.assert_called_once_with(
            "https://repo.example/index.json",
            max_bytes=321,
            require_https=True,
        )

    def test_index_identity_mismatch_is_removed(self):
        self.manager.manifest = {"id": "unexpected-addon", "version": "1.2.0"}
        client = self.make_client()
        entry = client.load_index("https://repo.example/index.json")[0]
        with self.assertRaisesRegex(RepositoryError, "identity/version"):
            client.install(entry)
        self.assertEqual(self.manager.removed, ["unexpected-addon"])


if __name__ == "__main__":
    unittest.main()
