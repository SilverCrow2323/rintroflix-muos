#!/usr/bin/env python3
"""Build a muOS .muxapp with all application files inside RintrofliX/."""
from __future__ import annotations
import argparse
import stat
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = "RintrofliX"
INCLUDE_FILES = (
    "mux_launch.sh", "mux_lang.ini", "VERSION", "README.md",
    "ARCHITECTURE.md", "CHANGELOG.md", "ADDON_SDK.md",
)
INCLUDE_DIRS = ("rintroflix", "lib", "tools", "presets", "resources", "glyph", "data")

def _safe_regular_file(root: Path, path: Path) -> bool:
    """Return true only for regular files with no symlink in their path."""
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return False
    return current.is_file()


def collect_package_files(root: Path = ROOT) -> list[Path]:
    """Collect package inputs without following symlink files or directories."""
    root = root.resolve()
    files: list[Path] = []
    for name in INCLUDE_FILES:
        path = root / name
        if _safe_regular_file(root, path):
            files.append(path)
    for dirname in INCLUDE_DIRS:
        base = root / dirname
        if base.is_symlink() or not base.is_dir():
            continue
        for path in base.rglob("*"):
            if "__pycache__" in path.parts or path.suffix in (".pyc", ".pyo"):
                continue
            if _safe_regular_file(root, path):
                files.append(path)
    return sorted(set(files))

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="dist/RintrofliX-2.6.3.muxapp")
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    required = (
        "mux_launch.sh", "rintroflix/main.py", "rintroflix/ui.py",
        "rintroflix/player.py", "tools/bootstrap_runtime.py",
    )
    missing = [p for p in required if not _safe_regular_file(ROOT, ROOT / p)]
    if missing:
        raise SystemExit("Incomplete package; missing or symlinked: " + ", ".join(missing))

    files = collect_package_files(ROOT)

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(files):
            rel = path.relative_to(ROOT).as_posix()
            arcname = APP_DIR + "/" + rel
            info = zipfile.ZipInfo(arcname)
            permissions = 0o755 if rel == "mux_launch.sh" else stat.S_IMODE(path.stat().st_mode)
            info.external_attr = (stat.S_IFREG | permissions) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())

    with zipfile.ZipFile(output) as archive:
        bad = archive.testzip()
        if bad:
            raise SystemExit("ZIP CRC failure: " + bad)
        names = set(archive.namelist())
        for required_path in required:
            packaged = APP_DIR + "/" + required_path
            if packaged not in names:
                raise SystemExit("Archive is missing " + packaged)
        if "RintrofliX/mux_launch.sh" not in names:
            raise SystemExit("Archive is missing RintrofliX/mux_launch.sh")
        if any(not name.startswith("RintrofliX/") for name in names):
            raise SystemExit("Unexpected file outside RintrofliX/")
    print("Built %s (%d bytes, %d files)" % (output, output.stat().st_size, len(names)))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
