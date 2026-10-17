from __future__ import annotations

import hashlib
import importlib.util
import shutil
import sys
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "k2_windows_download_packager", ROOT / "packaging" / "create_windows_download.py"
)
assert _spec and _spec.loader
_packager = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _packager
_spec.loader.exec_module(_packager)


def _sample_distribution(path: Path) -> Path:
    source = path / "K2"
    (source / "_internal" / "nested").mkdir(parents=True)
    (source / "K2.exe").write_bytes(b"sample executable")
    (source / "_internal" / "nested" / "dependency.dll").write_bytes(b"sample dependency")
    return source


def test_windows_download_zip_is_complete_and_reproducible(tmp_path: Path):
    source = _sample_distribution(tmp_path)
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"

    _packager.create_archive(source, first)
    _packager.create_archive(source, second)

    assert first.read_bytes() == second.read_bytes()
    with ZipFile(first) as archive:
        assert archive.testzip() is None
        assert archive.read("K2-windows-x64/K2.exe") == b"sample executable"
        assert archive.read("K2-windows-x64/_internal/nested/dependency.dll") == b"sample dependency"
        assert all(item.date_time == _packager.FIXED_TIMESTAMP for item in archive.infolist())


def test_release_metadata_tracks_exe_and_zip_hashes_and_sizes(tmp_path: Path):
    source = _sample_distribution(tmp_path)
    exe = source / "K2.exe"
    archive = tmp_path / "K2-windows-x64.zip"
    _packager.create_archive(source, archive)

    metadata_root = tmp_path / "repo"
    (metadata_root / "docs").mkdir(parents=True)
    shutil.copyfile(ROOT / "README.md", metadata_root / "README.md")
    shutil.copyfile(
        ROOT / "docs" / "RELEASE_AND_WINDOWS_PACKAGING.md",
        metadata_root / "docs" / "RELEASE_AND_WINDOWS_PACKAGING.md",
    )
    _packager.ROOT = metadata_root

    exe_hash, zip_hash = _packager.update_release_metadata(exe, archive)
    readme = (metadata_root / "README.md").read_text(encoding="utf-8")
    release_doc = (metadata_root / "docs" / "RELEASE_AND_WINDOWS_PACKAGING.md").read_text(encoding="utf-8")

    assert exe_hash == hashlib.sha256(exe.read_bytes()).hexdigest()
    assert zip_hash == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert f"SHA-256: `{zip_hash}`" in readme
    assert f"{exe_hash}  K2.exe" in release_doc
    assert f"{zip_hash}  K2-windows-x64.zip" in release_doc
    assert f"{_packager.persian_grouped_number(exe.stat().st_size)} بایت" in release_doc
    assert f"{_packager.persian_grouped_number(archive.stat().st_size)} بایت" in release_doc
