import tempfile
import unittest
from pathlib import Path

from tools.build_muxapp import _safe_regular_file, collect_package_files


class PackageSourceSafetyTests(unittest.TestCase):
    def test_file_symlink_is_not_collected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "rintroflix"
            source.mkdir()
            safe = source / "safe.py"
            safe.write_text("VALUE = 1\n", encoding="utf-8")
            outside = root.parent / (root.name + "-outside.py")
            outside.write_text("SECRET = 'outside'\n", encoding="utf-8")
            link = source / "external.py"
            try:
                link.symlink_to(outside)
            except OSError:
                self.skipTest("symlinks are unavailable on this runner")
            files = collect_package_files(root)
            self.assertIn(safe, files)
            self.assertNotIn(link, files)
            self.assertFalse(_safe_regular_file(root, link))

    def test_symlinked_include_directory_is_not_traversed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            outside = root.parent / (root.name + "-external")
            outside.mkdir()
            secret = outside / "secret.py"
            secret.write_text("SHOULD_NOT_PACKAGE = True\n", encoding="utf-8")
            link = root / "resources"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("directory symlinks are unavailable on this runner")
            self.assertNotIn(secret, collect_package_files(root))

    def test_required_symlink_fails_regular_file_check(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            outside = root.parent / (root.name + "-required.py")
            outside.write_text("print('external')\n", encoding="utf-8")
            link = root / "mux_launch.sh"
            try:
                link.symlink_to(outside)
            except OSError:
                self.skipTest("symlinks are unavailable on this runner")
            self.assertFalse(_safe_regular_file(root, link))


if __name__ == "__main__":
    unittest.main()
