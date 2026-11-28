import json
import zipfile
from pathlib import Path

import pytest

from rintroflix.addons import AddonError, AddonManager


def manager_at(root: Path) -> AddonManager:
    manager = AddonManager.__new__(AddonManager)
    manager.root = root
    manager.items = []
    manager.actions = []
    manager.sources = []
    manager.errors = []
    return manager


def write_manifest(folder: Path, entrypoint="addon.py"):
    (folder / "addon.json").write_text(
        json.dumps({
            "id": "safe-addon",
            "api_version": 1,
            "version": "1.0.0",
            "entrypoint": entrypoint,
        }),
        encoding="utf-8",
    )


def test_manifest_entrypoint_cannot_escape_through_a_symlink(tmp_path):
    addon = tmp_path / "addon"
    addon.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("def register(api): return []", encoding="utf-8")
    (addon / "addon.py").symlink_to(outside)
    write_manifest(addon)

    with pytest.raises(AddonError, match="symbolic links"):
        AddonManager._read_manifest(addon)


def test_archive_rejects_duplicate_casefolded_target_paths(tmp_path):
    root = tmp_path / "installed"
    root.mkdir()
    archive_path = tmp_path / "duplicate.zip"
    manifest = json.dumps({
        "id": "safe-addon",
        "api_version": 1,
        "version": "1.0.0",
        "entrypoint": "addon.py",
    })
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("addon.json", manifest)
        archive.writestr("addon.py", "def register(api): return []")
        archive.writestr("ADDON.PY", "def register(api): return []")

    with pytest.raises(AddonError, match="Duplicate or case-colliding"):
        manager_at(root).install_archive(archive_path)

    assert list(root.iterdir()) == []


def test_archive_rejects_backslash_paths(tmp_path):
    root = tmp_path / "installed"
    root.mkdir()
    archive_path = tmp_path / "backslash.zip"
    manifest = json.dumps({
        "id": "safe-addon",
        "api_version": 1,
        "version": "1.0.0",
        "entrypoint": "addon.py",
    })
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("addon.json", manifest)
        archive.writestr("addon.py", "def register(api): return []")
        archive.writestr(r"nested\\escape.py", "bad")

    with pytest.raises(AddonError, match="Unsafe path"):
        manager_at(root).install_archive(archive_path)

    assert list(root.iterdir()) == []


def _valid_manifest():
    return json.dumps({
        "id": "safe-addon",
        "api_version": 1,
        "version": "1.0.0",
        "entrypoint": "addon.py",
    })


def test_archive_rejects_excessive_member_count_before_install(tmp_path):
    root = tmp_path / "installed"
    root.mkdir()
    archive_path = tmp_path / "many-files.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("addon.json", _valid_manifest())
        archive.writestr("addon.py", "def register(api): return []")
        for index in range(511):
            archive.writestr("data/%04d.txt" % index, "x")

    with pytest.raises(AddonError, match="too many archive entries"):
        manager_at(root).install_archive(archive_path)

    assert list(root.iterdir()) == []


def test_archive_rejects_single_file_over_eight_mib(tmp_path):
    root = tmp_path / "installed"
    root.mkdir()
    archive_path = tmp_path / "oversized-file.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("addon.json", _valid_manifest())
        archive.writestr("addon.py", "x" * (8 * 1024 * 1024 + 1))

    with pytest.raises(AddonError, match="per-file limit"):
        manager_at(root).install_archive(archive_path)

    assert list(root.iterdir()) == []


def test_archive_rejects_extreme_compression_ratio(tmp_path):
    root = tmp_path / "installed"
    root.mkdir()
    archive_path = tmp_path / "compressed-bomb.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("addon.json", _valid_manifest())
        archive.writestr("addon.py", "A" * (128 * 1024))

    with pytest.raises(AddonError, match="compression ratio"):
        manager_at(root).install_archive(archive_path)

    assert list(root.iterdir()) == []


def test_archive_requires_exactly_one_manifest_even_with_case_variants(tmp_path):
    root = tmp_path / "installed"
    root.mkdir()
    archive_path = tmp_path / "two-manifests.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("addon.json", _valid_manifest())
        archive.writestr("addon.py", "def register(api): return []")
        archive.writestr("nested/ADDON.JSON", _valid_manifest())

    with pytest.raises(AddonError, match="exactly one addon.json"):
        manager_at(root).install_archive(archive_path)

    assert list(root.iterdir()) == []
