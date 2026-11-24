import unittest
from unittest.mock import patch
import urllib.request

from rintroflix.net import _HTTPSOnlyRedirectHandler, fetch_bytes


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


class FakeOpener:
    def __init__(self, response):
        self.response = response

    def open(self, request, timeout=18):
        return self.response


class HttpsRedirectTests(unittest.TestCase):
    @patch("rintroflix.net.urllib.request.build_opener")
    def test_rejects_https_repository_redirected_to_http(self, build_opener):
        build_opener.return_value = FakeOpener(FakeResponse("http://mirror.example/addons.json"))
        with self.assertRaisesRegex(ValueError, "redirect refused"):
            fetch_bytes("https://repo.example/addons.json", max_bytes=16, require_https=True)

    @patch("rintroflix.net.urllib.request.build_opener")
    def test_accepts_https_repository_redirect(self, build_opener):
        build_opener.return_value = FakeOpener(FakeResponse("https://cdn.example/addons.json"))
        self.assertEqual(
            fetch_bytes("https://repo.example/addons.json", max_bytes=16, require_https=True),
            b"body",
        )

    @patch("rintroflix.net.urllib.request.build_opener")
    def test_rejects_final_https_url_with_embedded_credentials(self, build_opener):
        build_opener.return_value = FakeOpener(FakeResponse("https://user:secret@cdn.example/addons.json"))
        with self.assertRaisesRegex(ValueError, "redirect refused"):
            fetch_bytes("https://repo.example/addons.json", max_bytes=16, require_https=True)

    @patch("rintroflix.net.urllib.request.urlopen")
    def test_http_media_sources_remain_supported_by_default(self, open_url):
        open_url.return_value = FakeResponse("http://media.example/live.m3u", b"#EXTM3U")
        self.assertEqual(fetch_bytes("http://media.example/live.m3u"), b"#EXTM3U")

    def test_redirect_handler_rejects_intermediate_http_hop(self):
        handler = _HTTPSOnlyRedirectHandler()
        request = urllib.request.Request("https://repo.example/addons.json")
        with self.assertRaisesRegex(ValueError, "redirect refused"):
            handler.redirect_request(request, None, 302, "Found", {}, "http://relay.example/next")

    def test_redirect_handler_allows_credential_free_https_hop(self):
        handler = _HTTPSOnlyRedirectHandler()
        request = urllib.request.Request("https://repo.example/addons.json")
        redirected = handler.redirect_request(
            request, None, 302, "Found", {}, "https://cdn.example/addons.json"
        )
        self.assertEqual(redirected.full_url, "https://cdn.example/addons.json")

    def test_https_only_mode_rejects_initial_http_url(self):
        with self.assertRaisesRegex(ValueError, "HTTPS is required"):
            fetch_bytes("http://repo.example/addons.json", require_https=True)

    def test_https_only_mode_rejects_initial_url_with_credentials(self):
        with self.assertRaisesRegex(ValueError, "HTTPS is required"):
            fetch_bytes("https://user:secret@repo.example/addons.json", require_https=True)

    def test_https_only_mode_rejects_missing_host(self):
        with self.assertRaisesRegex(ValueError, "HTTPS is required"):
            fetch_bytes("https:///addons.json", require_https=True)


if __name__ == "__main__":
    unittest.main()
