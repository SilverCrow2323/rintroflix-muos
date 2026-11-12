#!/usr/bin/env python3
"""Build a clean muOS .muxapp archive from the RintrofliX source tree."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
INCLUDE_FILES = (
    "mux_launch.sh", "mux_lang.ini", "VERSION", "README.md",
    "ARCHITECTURE.md", "CHANGELOG.md", "ADDON_SDK.md",
)
INCLUDE_DIRS = ("rintroflix", "lib", "tools", "presets", "resources", "glyph")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="dist/RintrofliX-2.6.1.muxapp")
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    required = ("rintroflix/main.py", "rintroflix/ui.py", "rintroflix/player.py",
                "tools/bootstrap_runtime.py", "mux_launch.sh")
    missing = [p for p in required if not (ROOT / p).is_file()]
    if missing:
        raise SystemExit("Incomplete package; missing: " + ", ".join(missing))

    files = []
    for name in INCLUDE_FILES:
        path = ROOT / name
        if path.is_file():
            files.append(path)
    for dirname in INCLUDE_DIRS:
        base = ROOT / dirname
        if base.is_dir():
            for path in base.rglob("*"):
                if path.is_file() and "__pycache__" not in path.parts and path.suffix not in (".pyc", ".pyo"):
                    files.append(path)
    data_keep = ROOT / "data" / ".keep"
    if data_keep.is_file():
        files.append(data_keep)

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        seen = set()
        for path in sorted(files):
            rel = path.relative_to(ROOT).as_posix()
            if rel in seen:
                continue
            seen.add(rel)
            info = zipfile.ZipInfo(rel)
            mode = path.stat().st_mode
            info.external_attr = (stat.S_IMODE(mode) | (stat.S_IFREG << 16)) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    with zipfile.ZipFile(output) as archive:
        bad = archive.testzip()
        if bad:
            raise SystemExit("ZIP CRC failure: " + bad)
        names = set(archive.namelist())
        for required_path in required:
            if required_path not in names:
                raise SystemExit("Archive is missing " + required_path)
    print("Built %s (%d bytes, %d files)" % (output, output.stat().st_size, len(files)))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
