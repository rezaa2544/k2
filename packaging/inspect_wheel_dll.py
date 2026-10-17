"""خواندن یک DLL از داخل چرخاب PyPI بدون دانلود کل چرخاب.

از «دایرکتوری مرکزی» zip برای پیدا کردن offset و روش فشرده‌سازی استفاده
می‌شود، سپس فقط همان فایل با درخواست بازه‌ای دانلود و باز می‌شود.
"""

from __future__ import annotations

import json
import struct
import sys
import urllib.request
import zlib


def _get(url: str, start: int | None = None, end: int | None = None) -> bytes:
    request = urllib.request.Request(url)
    if start is not None:
        request.add_header("Range", f"bytes={start}-{end if end is not None else ''}")
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def _entries(url: str) -> dict[str, tuple[int, int, int, int]]:
    """نام → (offset محلی داده، اندازهٔ فشرده، اندازهٔ اصلی، روش فشرده‌سازی)"""
    request = urllib.request.Request(url)
    request.add_header("Range", "bytes=0-0")
    with urllib.request.urlopen(request, timeout=120) as response:
        total = int(response.headers.get("Content-Range", "").split("/")[-1])
    tail_size = min(total, 1 << 22)
    tail = _get(url, total - tail_size, total - 1)
    index = tail.rfind(b"PK\x05\x06")
    eocd = tail[index : index + 22]
    count = struct.unpack("<H", eocd[10:12])[0]
    cd_offset = struct.unpack("<I", eocd[16:20])[0]
    cd_size = struct.unpack("<I", eocd[12:16])[0]
    base = total - tail_size
    if cd_offset >= tail_size:
        cd = _get(url, cd_offset, cd_offset + cd_size - 1)
    else:
        cd = tail[cd_offset - base : cd_offset - base + cd_size]
    result: dict[str, tuple[int, int, int, int]] = {}
    pos = 0
    for _ in range(count):
        if cd[pos : pos + 4] != b"PK\x01\x02":
            break
        method = struct.unpack("<H", cd[pos + 10 : pos + 12])[0]
        comp_size = struct.unpack("<I", cd[pos + 20 : pos + 24])[0]
        uncomp_size = struct.unpack("<I", cd[pos + 24 : pos + 28])[0]
        name_len = struct.unpack("<H", cd[pos + 28 : pos + 30])[0]
        extra_len = struct.unpack("<H", cd[pos + 30 : pos + 32])[0]
        comment_len = struct.unpack("<H", cd[pos + 32 : pos + 34])[0]
        local_offset = struct.unpack("<I", cd[pos + 42 : pos + 46])[0]
        name = cd[pos + 46 : pos + 46 + name_len].decode("utf-8", "replace")
        result[name] = (local_offset, comp_size, uncomp_size, method)
        pos += 46 + name_len + extra_len + comment_len
    return result


def read_member(url: str, entries, name: str) -> bytes:
    local_offset, comp_size, uncomp_size, method = entries[name]
    header = _get(url, local_offset, local_offset + 30 - 1)
    name_len = struct.unpack("<H", header[26:28])[0]
    extra_len = struct.unpack("<H", header[28:30])[0]
    data_start = local_offset + 30 + name_len + extra_len
    raw = _get(url, data_start, data_start + comp_size - 1)
    if method == 0:
        return raw
    return zlib.decompress(raw, -zlib.MAX_WBITS)


def pe_imports(blob: bytes) -> list[str]:
    """نام DLLهای ایمپورت‌شده در یک فایل PE."""
    e_lfanew = struct.unpack("<I", blob[0x3C:0x40])[0]
    pe = e_lfanew
    assert blob[pe : pe + 4] == b"PE\x00\x00"
    coff = pe + 4
    num_sections = struct.unpack("<H", blob[coff + 2 : coff + 4])[0]
    opt_size = struct.unpack("<H", blob[coff + 16 : coff + 18])[0]
    opt = coff + 20
    magic = struct.unpack("<H", blob[opt : opt + 2])[0]
    if magic == 0x20B:  # PE32+
        dd_offset = opt + 112
    else:
        dd_offset = opt + 96
    import_rva, import_size = struct.unpack(
        "<II", blob[dd_offset + 8 : dd_offset + 16]
    )
    sections = []
    sec_start = opt + opt_size
    for i in range(num_sections):
        s = sec_start + i * 40
        name = blob[s : s + 8].rstrip(b"\x00").decode("ascii", "replace")
        vsize, vaddr, rawsize, rawptr = struct.unpack(
            "<IIII", blob[s + 8 : s + 24]
        )
        sections.append((name, vaddr, vsize, rawptr, rawsize))

    def rva_to_offset(rva: int) -> int:
        for name, vaddr, vsize, rawptr, rawsize in sections:
            if vaddr <= rva < vaddr + max(vsize, rawsize):
                return rawptr + (rva - vaddr)
        raise ValueError(f"rva {rva} not mapped")

    dlls: list[str] = []
    offset = rva_to_offset(import_rva)
    while True:
        entry = blob[offset : offset + 20]
        if len(entry) < 20 or entry == b"\x00" * 20:
            break
        name_rva = struct.unpack("<I", entry[12:16])[0]
        if name_rva == 0:
            break
        name_off = rva_to_offset(name_rva)
        end = blob.index(b"\x00", name_off)
        dlls.append(blob[name_off:end].decode("ascii", "replace"))
        offset += 20
    return dlls


def main() -> None:
    version = sys.argv[1]
    target = sys.argv[2] if len(sys.argv) > 2 else "PySide6/Qt6Core.dll"
    index = json.loads(_get("https://pypi.org/pypi/pyside6-essentials/json").decode())
    wheel = next(
        f
        for f in index["releases"][version]
        if f["filename"].endswith("win_amd64.whl") and "abi3" in f["filename"]
    )
    entries = _entries(wheel["url"])
    blob = read_member(wheel["url"], entries, target)
    print(f"=== {version} · {target} · {len(blob)} بایت ===")
    print("ICU-related imports:")
    for dll in pe_imports(blob):
        if "icu" in dll.lower():
            print("   ", dll)
    print("all imports:", ", ".join(pe_imports(blob)))


if __name__ == "__main__":
    main()
