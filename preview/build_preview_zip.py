"""بستهٔ ZIP پیش‌نمایش HTML را از فایل ساخته‌شدهٔ preview می‌سازد.

چرا لازم است: لینک دانلود در README به ``downloads/K2-preview-html.zip`` اشاره
می‌کند. اگر ZIP دستی ساخته شود، با تغییرهای بعدی کهنه می‌شود. این اسکریپت بستهٔ
قطعی (deterministic) می‌سازد تا ``tests/test_preview.py`` بتواند کهنگی آن را
تشخیص دهد.

اجرا::

    python preview/build_preview_zip.py
"""

from __future__ import annotations

import hashlib
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HTML = ROOT / "K2-preview.html"
ZIP = ROOT.parent / "downloads" / "K2-preview-html.zip"
# نام ثابت داخل ZIP تا هش بسته بین سیستم‌ها تغییر نکند.
ENTRY = "K2-preview.html"
# زمان ثابت برای قاطع‌سازی بسته (mtime روی فایل influencing نمی‌شود).
TIMESTAMP = (2026, 10, 19, 0, 0, 0)


def normalize(html_bytes: bytes) -> bytes:
    """پایان‌خط‌ها را به LF یکدست می‌کند.

    چرا لازم است: روی ویندوز، ``git checkout`` و ``write_text`` پایان‌خط را به
    CRLF تبدیل می‌کنند؛ بدون این یکدست‌سازی هش بسته روی لینوکس و ویندوز تفاوت
    می‌کند و تست کهنگی بسته روی ویندوز شکست می‌خورد.
    """
    return html_bytes.replace(b"\r\n", b"\n")


def build_zip(html_bytes: bytes) -> bytes:
    """بایت‌های ZIP را برای محتوای داده‌شده به‌صورت قطعی می‌سازد."""
    import io

    html_bytes = normalize(html_bytes)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        info = zipfile.ZipInfo(ENTRY, date_time=TIMESTAMP)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(info, html_bytes)
    return buffer.getvalue()


def main() -> int:
    if not HTML.exists():
        print(f"فایل پیش‌نمایش یافت نشد: {HTML} — ابتدا build_preview.py را اجرا کنید.")
        return 1
    html_bytes = HTML.read_bytes()
    payload = build_zip(html_bytes)
    ZIP.parent.mkdir(parents=True, exist_ok=True)
    ZIP.write_bytes(payload)
    print(f"Built {ZIP} ({len(payload)} bytes)")
    print(f"SHA-256: {hashlib.sha256(payload).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
