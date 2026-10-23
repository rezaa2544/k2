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
    (metadata_root / "preview").mkdir()
    shutil.copyfile(ROOT / "preview" / "K2-preview.html", metadata_root / "preview" / "K2-preview.html")
    _packager.ROOT = metadata_root

    source_revision = "abcdef1234567890abcdef1234567890abcdef12"
    exe_hash, zip_hash = _packager.update_release_metadata(exe, archive, source_revision)
    readme = (metadata_root / "README.md").read_text(encoding="utf-8")
    release_doc = (metadata_root / "docs" / "RELEASE_AND_WINDOWS_PACKAGING.md").read_text(encoding="utf-8")

    assert exe_hash == hashlib.sha256(exe.read_bytes()).hexdigest()
    assert zip_hash == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert f"SHA-256: `{zip_hash}`" in readme
    assert f"{exe_hash}  K2.exe" in release_doc
    assert f"{zip_hash}  K2-windows-x64.zip" in release_doc
    assert f"{_packager.persian_grouped_number(exe.stat().st_size)} بایت" in release_doc
    assert f"{_packager.persian_grouped_number(archive.stat().st_size)} بایت" in release_doc
    preview = (metadata_root / "preview" / "K2-preview.html").read_text(encoding="utf-8")
    assert f'data-source-revision="{source_revision}"' in preview


def test_refresh_preview_download_bundle_keeps_zip_and_readme_in_sync(tmp_path: Path):
    """ZIP دانلود پیش‌نمایش باید با HTML جاری و هش README همیشه بخواند.

    چرا لازم است: مرحلهٔ «refresh bundle» در CI هش نسخه را داخل
    ``preview/K2-preview.html`` مهر می‌زند. اگر ZIP بازسازی نشود، ZIP و HTML
    از هم جدا می‌افتند و لینک دانلود README کهنه می‌شود.
    """
    import hashlib

    # ``normalize`` همان یکدست‌سازی پایان‌خط بسته است؛ تست کهنگی در
    # ``tests/test_preview.py`` هم از همین تابع استفاده می‌کند.
    sys.path.insert(0, str(ROOT / "preview"))
    try:
        from build_preview_zip import normalize
    finally:
        sys.path.pop(0)

    repo = tmp_path / "repo"
    (repo / "preview").mkdir(parents=True)
    (repo / "downloads").mkdir()
    shutil.copyfile(ROOT / "README.md", repo / "README.md")
    shutil.copyfile(ROOT / "preview" / "K2-preview.html", repo / "preview" / "K2-preview.html")
    shutil.copyfile(ROOT / "preview" / "build_preview_zip.py", repo / "preview" / "build_preview_zip.py")
    original_root = _packager.ROOT
    _packager.ROOT = repo

    preview = repo / "preview" / "K2-preview.html"
    # همان کاری که CI می‌کند: مهر کردن هش نسخهٔ سورس در پیش‌نمایش.
    # ``newline="\\n"`` مثل کد محصول لازم است، وگرنه روی ویندوز
    # ``write_text`` پایان‌خط را CRLF می‌کند و بسته با فایل نمی‌خواند.
    preview.write_text(
        preview.read_text(encoding="utf-8").replace(
            'data-source-revision="pending"', 'data-source-revision="abcdef1234567"'
        ),
        encoding="utf-8",
        newline="\n",
    )

    zip_path, digest = _packager.refresh_preview_download_bundle()

    assert zip_path == repo / "downloads" / "K2-preview-html.zip"
    assert digest == hashlib.sha256(zip_path.read_bytes()).hexdigest()
    assert f"SHA-256 فایل ZIP: `{digest}`" in (repo / "README.md").read_text(encoding="utf-8")
    try:
        with ZipFile(zip_path) as archive:
            assert archive.namelist() == ["K2-preview.html"]
            # بسته همیشه LF یکدست شده ذبابه می‌کند (normalize)؛ مقایسه با
            # بایت خام فایل روی ویندوز به‌خاطر CRLF شکست می‌خورد.
            assert archive.read("K2-preview.html") == normalize(preview.read_bytes())
    finally:
        _packager.ROOT = original_root


def test_html_preview_is_offline_and_contains_app_menus_and_navigation():
    preview = (ROOT / "preview" / "K2-preview.html").read_text(encoding="utf-8")

    for label in ("برنامه", "راهنما", "داشبورد", "برنامهٔ امروز", "فعالیت‌ها", "F5", "Ctrl+Q"):
        assert label in preview
    assert "https://" not in preview
    assert "http://" not in preview
    for old_seed in (
        "پردازش اولیهٔ کلاس زیست",
        "تعارض نمونهٔ یکشنبه",
        "شنبه ۲۵ مهر ۱۴۰۵",
        "۵ ساعت و ۴۰ دقیقه",
        "آزمون نمونه",
    ):
        assert old_seed not in preview
    assert "هیچ فعالیتی از پیش وارد نشده است" in preview
    assert 'checked>' not in preview
