import unittest
from unittest.mock import patch

from rintroflix.net import fetch_bytes


class FakeResponse:
    def __init__(self, final_url, payload=b"body"):
        self._final_url = final_url
        self._payload = payload
        self.headers = {"Content-Length": str(len(payload))}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def geturl(self):
        return self._final_url

    def read(self, size=-1):
        return self._payload[:size]


class HttpsRedirectTests(unittest.TestCase):
    @patch("rintroflix.net.urllib.request.urlopen")
    def test_rejects_https_repository_redirected_to_http(self, open_url):
        open_url.return_value = FakeResponse("http://mirror.example/addons.json")
        with self.assertRaisesRegex(ValueError, "redirect refused"):
            fetch_bytes("https://repo.example/addons.json", max_bytes=16, require_https=True)

    @patch("rintroflix.net.urllib.request.urlopen")
    def test_accepts_https_repository_redirect(self, open_url):
        open_url.return_value = FakeResponse("https://cdn.example/addons.json")
        self.assertEqual(
            fetch_bytes("https://repo.example/addons.json", max_bytes=16, require_https=True),
            b"body",
        )

    @patch("rintroflix.net.urllib.request.urlopen")
    def test_http_media_sources_remain_supported_by_default(self, open_url):
        open_url.return_value = FakeResponse("http://media.example/live.m3u", b"#EXTM3U")
        self.assertEqual(fetch_bytes("http://media.example/live.m3u"), b"#EXTM3U")

    def test_https_only_mode_rejects_initial_http_url(self):
        with self.assertRaisesRegex(ValueError, "HTTPS is required"):
            fetch_bytes("http://repo.example/addons.json", require_https=True)


if __name__ == "__main__":
    unittest.main()
