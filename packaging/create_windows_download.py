"""ساخت ZIP بازتولیدپذیرِ بستهٔ Windows و همگام‌سازی checksum مستندات.

اجرا پس از build ویندوز:
    python packaging/create_windows_download.py \
        --source packaging/output/K2 \
        --destination downloads/K2-windows-x64.zip
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = "K2-windows-x64"
FIXED_TIMESTAMP = (2026, 1, 1, 0, 0, 0)
_PERSIAN_DIGITS = str.maketrans("0123456789,", "۰۱۲۳۴۵۶۷۸۹٬")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def persian_grouped_number(value: int) -> str:
    return f"{value:,}".translate(_PERSIAN_DIGITS)


def _zip_info(name: str, *, is_dir: bool) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=FIXED_TIMESTAMP)
    info.create_system = 3
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = ((0o40755 if is_dir else 0o100644) << 16)
    if is_dir:
        info.external_attr |= 0x10
    return info


def create_archive(source: Path, destination: Path) -> None:
    source = source.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    exe = source / "K2.exe"
    internal = source / "_internal"
    if not exe.is_file() or not internal.is_dir():
        raise FileNotFoundError("ورودی باید شامل K2.exe و پوشهٔ _internal باشد.")

    entries = sorted(source.rglob("*"), key=lambda path: path.relative_to(source).as_posix())
    with zipfile.ZipFile(
        destination,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        archive.writestr(_zip_info(f"{ARCHIVE_ROOT}/", is_dir=True), b"")
        for path in entries:
            relative = path.relative_to(source).as_posix()
            archive_name = f"{ARCHIVE_ROOT}/{relative}"
            if path.is_dir():
                archive.writestr(_zip_info(archive_name.rstrip("/") + "/", is_dir=True), b"")
            elif path.is_file():
                archive.writestr(
                    _zip_info(archive_name, is_dir=False),
                    path.read_bytes(),
                    compress_type=zipfile.ZIP_DEFLATED,
                    compresslevel=9,
                )

    with zipfile.ZipFile(destination) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise zipfile.BadZipFile(f"CRC نامعتبر برای {bad_member}")
        names = set(archive.namelist())
        if f"{ARCHIVE_ROOT}/K2.exe" not in names:
            raise zipfile.BadZipFile("K2.exe داخل بسته پیدا نشد.")
        if not any(name.startswith(f"{ARCHIVE_ROOT}/_internal/") for name in names):
            raise zipfile.BadZipFile("وابستگی‌های _internal داخل بسته پیدا نشدند.")


def _replace_once(text: str, pattern: str, replacement: str, *, path: Path) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"الگوی metadata دقیقاً یک بار در {path.relative_to(ROOT)} پیدا نشد: {pattern}")
    return updated


def update_release_metadata(
    exe_path: Path,
    archive_path: Path,
    source_revision: str | None = None,
) -> tuple[str, str]:
    if source_revision is not None and not re.fullmatch(r"[0-9a-f]{7,40}", source_revision):
        raise ValueError("source_revision باید SHA کوتاه یا کامل Git باشد.")
    exe_hash = sha256(exe_path)
    archive_hash = sha256(archive_path)
    exe_size = persian_grouped_number(exe_path.stat().st_size)
    archive_size = persian_grouped_number(archive_path.stat().st_size)

    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    readme = _replace_once(
        readme,
        r"^SHA-256: `[0-9a-f]{64}`$",
        f"SHA-256: `{archive_hash}`",
        path=readme_path,
    )
    readme_path.write_text(readme, encoding="utf-8", newline="\n")

    doc_path = ROOT / "docs" / "RELEASE_AND_WINDOWS_PACKAGING.md"
    doc = doc_path.read_text(encoding="utf-8")
    doc = _replace_once(
        doc,
        r"(`packaging/output/K2/K2\.exe` — )[0-9۰-۹٬,]+ بایت",
        rf"\g<1>{exe_size} بایت",
        path=doc_path,
    )
    doc = _replace_once(
        doc,
        r"(├── K2\.exe\s+)[0-9۰-۹٬,]+ بایت",
        rf"\g<1>{exe_size} بایت",
        path=doc_path,
    )
    doc = _replace_once(
        doc,
        r"^[0-9a-f]{64}(?=  K2\.exe$)",
        exe_hash,
        path=doc_path,
    )
    doc = _replace_once(
        doc,
        r"^[0-9a-f]{64}(?=  K2-windows-x64\.zip$)",
        archive_hash,
        path=doc_path,
    )
    doc = _replace_once(
        doc,
        r"(downloads/K2-windows-x64\.zip` نیز در مخزن ثبت شده است \()[0-9۰-۹٬,]+ بایت",
        rf"\g<1>{archive_size} بایت",
        path=doc_path,
    )
    doc_path.write_text(doc, encoding="utf-8", newline="\n")

    if source_revision is not None:
        preview_path = ROOT / "preview" / "K2-preview.html"
        preview = preview_path.read_text(encoding="utf-8")
        preview = _replace_once(
            preview,
            r'data-source-revision="(?:pending|[0-9a-f]{7,40})"',
            f'data-source-revision="{source_revision}"',
            path=preview_path,
        )
        preview = _replace_once(
            preview,
            r'(<b id="sourceRevision">)[^<]+(</b>)',
            rf"\g<1>{source_revision[:8]}\g<2>",
            path=preview_path,
        )
        preview_path.write_text(preview, encoding="utf-8", newline="\n")

    return exe_hash, archive_hash


def refresh_preview_download_bundle() -> tuple[Path, str]:
    """بستهٔ ZIP پیش‌نمایش HTML را با نسخهٔ جاری همگام و هش README را تازه می‌کند.

    چرا لازم است: ``update_release_metadata`` هش نسخهٔ سورس را داخل
    ``preview/K2-preview.html`` مهر می‌زند. اگر ZIP دانلود بازسازی نشود،
    ``downloads/K2-preview-html.zip`` و ``preview/K2-preview.html`` از هم
    جدا می‌افتند؛ لینک دانلود README کهنه می‌شود و
    ``test_preview_zip_bundle_is_current_and_reproducible`` شکست می‌خورد.
    """
    import importlib.util

    script = ROOT / "preview" / "build_preview_zip.py"
    spec = importlib.util.spec_from_file_location("k2_build_preview_zip", script)
    assert spec and spec.loader, "build_preview_zip.py پیدا نشد"
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    html = (ROOT / "preview" / "K2-preview.html").read_bytes()
    payload = module.build_zip(html)
    zip_path = ROOT / "downloads" / "K2-preview-html.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    zip_path.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()

    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    readme = _replace_once(
        readme,
        r"^SHA-256 فایل ZIP: `[0-9a-f]{64}`$",
        f"SHA-256 فایل ZIP: `{digest}`",
        path=readme_path,
    )
    readme_path.write_text(readme, encoding="utf-8", newline="\n")
    return zip_path, digest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="پوشهٔ PyInstaller شامل K2.exe و _internal")
    parser.add_argument("--destination", type=Path, required=True, help="مسیر ZIP قابل دانلود در مخزن")
    parser.add_argument("--no-metadata", action="store_true", help="ساخت بسته بدون تغییر README/سند release")
    parser.add_argument("--source-revision", help="SHA مبدأ برای ثبت در پیش‌نمایش HTML")
    args = parser.parse_args()
    create_archive(args.source, args.destination)
    exe_path = args.source / "K2.exe"
    if args.no_metadata:
        exe_hash, archive_hash = sha256(exe_path), sha256(args.destination)
    else:
        exe_hash, archive_hash = update_release_metadata(
            exe_path, args.destination, source_revision=args.source_revision
        )
        # پس از مهر کردن هش نسخه در پیش‌نمایش، بستهٔ ZIP دانلود را هم
        # همگام می‌کنیم؛ وگرنه ZIP و HTML از هم جدا می‌افتند.
        preview_zip, preview_sha = refresh_preview_download_bundle()
        print(f"PREVIEW_ZIP_SIZE={preview_zip.stat().st_size}")
        print(f"PREVIEW_ZIP_SHA256={preview_sha}")
    print(f"EXE_SIZE={exe_path.stat().st_size}")
    print(f"EXE_SHA256={exe_hash}")
    print(f"ZIP_SIZE={args.destination.stat().st_size}")
    print(f"ZIP_SHA256={archive_hash}")
    if args.source_revision:
        print(f"SOURCE_REVISION={args.source_revision}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
