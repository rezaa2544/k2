"""بررسی اینکه کدام نسخه‌های PySide6 ویندوزی فایل‌های ICU را همراه دارند.

روش: به‌جای دانلود کامل چرخاب (~۸۰ مگابایت)، فقط «دیرکتوری مرکزی» zip را
با درخواست بازه‌ای (HTTP Range) می‌خوانیم و نام فایل‌ها را استخراج می‌کنیم.
"""

from __future__ import annotations

import io
import json
import struct
import sys
import urllib.request


def _get(url: str, start: int | None = None, end: int | None = None) -> bytes:
    request = urllib.request.Request(url)
    if start is not None:
        request.add_header("Range", f"bytes={start}-{end if end is not None else ''}")
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def _central_directory_names(url: str) -> list[str]:
    size = int(_get(url, 0, 0) and 0)  # placeholder, replaced below
    head = _get(url, 0, 0)
    # طول واقعی فایل از هدر Content-Range
    request = urllib.request.Request(url)
    request.add_header("Range", "bytes=0-0")
    with urllib.request.urlopen(request, timeout=60) as response:
        content_range = response.headers.get("Content-Range", "")
        total = int(content_range.split("/")[-1])
    tail_size = min(total, 1 << 22)  # ۴ مگابایت کافی است
    tail = _get(url, total - tail_size, total - 1)
    # پیدا کردن End of Central Directory
    index = tail.rfind(b"PK\x05\x06")
    if index < 0:
        raise RuntimeError("EOCD not found")
    eocd = tail[index : index + 22]
    count = struct.unpack("<H", eocd[10:12])[0]
    cd_offset = struct.unpack("<I", eocd[16:20])[0]
    cd_size = struct.unpack("<I", eocd[12:16])[0]
    if cd_offset >= tail_size:
        # باید کل دایرکتوری مرکزی را بگیریم
        cd = _get(url, cd_offset, cd_offset + cd_size - 1)
    else:
        cd = tail[cd_offset - (total - tail_size) : cd_offset - (total - tail_size) + cd_size]
    names: list[str] = []
    pos = 0
    for _ in range(count):
        if cd[pos : pos + 4] != b"PK\x01\x02":
            break
        name_len = struct.unpack("<H", cd[pos + 28 : pos + 30])[0]
        extra_len = struct.unpack("<H", cd[pos + 30 : pos + 32])[0]
        comment_len = struct.unpack("<H", cd[pos + 32 : pos + 34])[0]
        name = cd[pos + 46 : pos + 46 + name_len].decode("utf-8", "replace")
        names.append(name)
        pos += 46 + name_len + extra_len + comment_len
    return names


def main() -> None:
    versions = sys.argv[1:] or ["6.12.0", "6.9.1", "6.8.3", "6.7.3", "6.6.1", "6.5.3"]
    index = json.loads(_get("https://pypi.org/pypi/pyside6-essentials/json").decode())
    for version in versions:
        files = index["releases"].get(version, [])
        wheel = next(
            (
                f
                for f in files
                if f["filename"].endswith("win_amd64.whl")
                and "abi3" in f["filename"]
            ),
            None,
        )
        if wheel is None:
            print(f"{version}: wheel ویندوز cp310-abi3 پیدا نشد")
            continue
        try:
            names = _central_directory_names(wheel["url"])
        except Exception as exc:  # pragma: no cover
            print(f"{version}: خطا در خواندن دایرکتوری: {exc}")
            continue
        icu = [n for n in names if "icu" in n.lower()]
        print(f"{version}: {len(names)} فایل | ICU: {icu if icu else '❌ وجود ندارد'}")


if __name__ == "__main__":
    main()
