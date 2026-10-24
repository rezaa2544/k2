#!/usr/bin/env python3
"""بررسی اینکه آیکن واقعاً داخل EXE ویندوزی جا داده شده است.

چرا لازم است: ``k2.spec`` مسیر ``src/k2/ui/assets/k2.ico`` را به PyInstaller
می‌دهد، ولی «مسیر داده شده» به‌معنای «آیکن روی EXE نشسته» نیست. اگر فایل
 Gil باشد، مسیر اشتباه باشد یا PyInstaller آیکن را جا ندهد، کاربر آیکن
پیش‌فرض PyInstaller را می‌بیند و هیچ خطایی در build ظاهر نمی‌شود.

این اسکریپت بخش منابع (``.rsrc``) فایل PE را می‌خواند و فریم‌های
``RT_ICON`` و ``RT_GROUP_ICON`` را با فریم‌های فایل ``.ico`` مقایسه می‌کند.

PyInstaller (``PyInstaller/utils/win32/icon.py::CopyIcons_FromIco``) با
``UpdateResource`` کار می‌کند:

* ``RT_GROUP_ICON`` با شناسهٔ ۱ = ``ICONDIRHEADER`` + ``ICONDIRENTRY``ها که
  در آن‌ها ``dwImageOffset`` جای خود را به شناسهٔ عددی ``RT_ICON`` داده است.
* ``RT_ICON`` با شناسه‌های ۱..N و محتوای **بایت‌به‌بایت یکی** با فریم‌های
  فایل ``.ico``.

پس مقایسهٔ دقیق بایت‌ها ممکن است و همان کار را می‌کنیم؛ اگر روزی
PyInstaller بازکدوانی کرد، به مقایسهٔ تصویر رمزگشایی‌شده برمی‌گردیم.

استفاده::

    python packaging/verify_exe_icon.py packaging/output/K2/K2.exe src/k2/ui/assets/k2.ico
"""

from __future__ import annotations

import argparse
import os
import struct
import sys
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

RT_ICON = 3
RT_GROUP_ICON = 14

DOS_MAGIC = b"MZ"
PE_SIGNATURE = b"PE\x00\x00"
OPTIONAL_HEADER_MAGIC_PE32P = 0x20B
RESOURCE_DIRECTORY_INDEX = 2


class IconVerificationError(RuntimeError):
    """آیکن داخل EXE نیست یا با فایل ``.ico`` میانه ندارد."""


# --------------------------------------------------------------------------
# ICO
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class IcoFrame:
    width: int
    height: int
    bit_count: int
    size: int
    data: bytes

    @property
    def digest(self) -> str:
        return sha256(self.data).hexdigest()


def read_ico(path: Path) -> list[IcoFrame]:
    """فریم‌های یک فایل ``.ico`` را می‌خواند."""
    blob = path.read_bytes()
    if blob[:4] != b"\x00\x00\x01\x00":
        raise IconVerificationError(f"{path}: فایل ICO معتبر نیست (امضای ICONDIR ندارد)")
    reserved, icon_type, count = struct.unpack_from("<HHH", blob, 0)
    if reserved != 0 or icon_type != 1:
        raise IconVerificationError(f"{path}: سرآیند ICONDIR نامعتبر است")
    if count == 0:
        raise IconVerificationError(f"{path}: فایل ICO هیچ فریمی ندارد")

    frames: list[IcoFrame] = []
    for index in range(count):
        offset = 6 + index * 16
        if offset + 16 > len(blob):
            raise IconVerificationError(f"{path}: جدول ICONDIRENTRY ناقص است")
        width, height, _colors, _reserved, _planes, bit_count, size, image_offset = (
            struct.unpack_from("<BBBBHHII", blob, offset)
        )
        if image_offset + size > len(blob):
            raise IconVerificationError(f"{path}: فریم {index} از محدودهٔ فایل بیرون می‌زند")
        frames.append(
            IcoFrame(
                width=width or 256,
                height=height or 256,
                bit_count=bit_count,
                size=size,
                data=blob[image_offset : image_offset + size],
            )
        )
    return frames


# --------------------------------------------------------------------------
# PE
# --------------------------------------------------------------------------


@dataclass
class Section:
    name: str
    virtual_address: int
    virtual_size: int
    raw_pointer: int
    raw_size: int

    def rva_to_offset(self, rva: int) -> int:
        if self.virtual_size:
            span = self.virtual_size
        else:  # pragma: no cover - بخش‌های بدون اندازهٔ مجازی
            span = self.raw_size
        if not (self.virtual_address <= rva < self.virtual_address + max(span, self.raw_size)):
            raise IconVerificationError(
                f"RVA 0x{rva:x} در بخش {self.name!r} نیست"
            )
        return self.raw_pointer + (rva - self.virtual_address)


@dataclass
class ResourceEntry:
    """یک منبع خوانده‌شده از ``.rsrc``."""

    resource_type: int
    name: int
    language: int
    rva: int
    size: int
    data: bytes = field(repr=False, default=b"")


class PeFile:
    """حداقل چیزی که برای خواندن بخش منابع یک PE لازم است."""

    def __init__(self, blob: bytes) -> None:
        self.blob = blob
        if blob[:2] != DOS_MAGIC:
            raise IconVerificationError("فایل امضای MZ ندارد؛ PE ویندوزی نیست")
        (pe_offset,) = struct.unpack_from("<I", blob, 0x3C)
        if blob[pe_offset : pe_offset + 4] != PE_SIGNATURE:
            raise IconVerificationError("امضای PE پیدا نشد")

        (
            _machine,
            number_of_sections,
            _timestamp,
            _symbol_table,
            _symbols,
            size_of_optional_header,
            _characteristics,
        ) = struct.unpack_from("<HHIIIHH", blob, pe_offset + 4)
        optional_offset = pe_offset + 24
        (optional_magic,) = struct.unpack_from("<H", blob, optional_offset)
        if optional_magic != OPTIONAL_HEADER_MAGIC_PE32P:
            raise IconVerificationError(
                f"فقط PE32+ (magic 0x{OPTIONAL_HEADER_MAGIC_PE32P:x}) پشتیبانی می‌شود؛ "
                f"این فایل 0x{optional_magic:x} است"
            )

        data_directory = optional_offset + 112
        resource_rva, _resource_size = struct.unpack_from("<II", blob, data_directory + 8 * RESOURCE_DIRECTORY_INDEX)
        if resource_rva == 0:
            raise IconVerificationError("فایل PE بخش منابع (‎.rsrc‎) ندارد")

        sections_offset = optional_offset + size_of_optional_header
        self.sections: list[Section] = []
        for index in range(number_of_sections):
            base = sections_offset + index * 40
            raw_name = blob[base : base + 8]
            name = raw_name.rstrip(b"\x00").decode("latin-1")
            virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from(
                "<IIII", blob, base + 8
            )
            self.sections.append(
                Section(name, virtual_address, virtual_size, raw_pointer, raw_size)
            )
        self.resource_base = resource_rva

    # -- پایه‌ای‌ها ------------------------------------------------------

    def _rva_to_offset(self, rva: int) -> int:
        for section in self.sections:
            try:
                return section.rva_to_offset(rva)
            except IconVerificationError:
                continue
        raise IconVerificationError(f"هیچ بخشی RVA 0x{rva:x} را پوشش نمی‌دهد")

    def read_at_rva(self, rva: int, size: int) -> bytes:
        offset = self._rva_to_offset(rva)
        return self.blob[offset : offset + size]

    # -- پویش درخت منابع ------------------------------------------------

    def resources(self) -> list[ResourceEntry]:
        """همهٔ منابع ``RT_ICON`` و ``RT_GROUP_ICON`` را برمی‌گرداند."""
        root = self._rva_to_offset(self.resource_base)
        found: list[ResourceEntry] = []
        self._walk(root, root, 0, (0, 0, 0), found)
        return found

    def _walk(
        self,
        node_offset: int,
        root_offset: int,
        level: int,
        ids: tuple[int, int, int],
        found: list[ResourceEntry],
    ) -> None:
        (
            _characteristics,
            _timestamp,
            _major,
            _minor,
            named_entries,
            id_entries,
        ) = struct.unpack_from("<IIHHHH", self.blob, node_offset)
        total = named_entries + id_entries
        if total == 0:
            return

        for index in range(total):
            entry_offset = node_offset + 16 + index * 8
            name_field, offset_field = struct.unpack_from("<II", self.blob, entry_offset)
            if name_field & 0x80000000:
                # منبع نام‌دار؛ آیکن برنامه همیشه عددی است و اینجا رد می‌شود.
                continue
            name_id = name_field & 0x7FFFFFFF

            if level == 0:
                # سطح نوع منبع: فقط آیکن‌ها را دنبال می‌کنیم.
                if name_id not in (RT_ICON, RT_GROUP_ICON):
                    continue
                self._walk(
                    root_offset + (offset_field & 0x7FFFFFFF),
                    root_offset,
                    level + 1,
                    (name_id, 0, 0),
                    found,
                )
                continue

            if offset_field & 0x80000000:
                self._walk(
                    root_offset + (offset_field & 0x7FFFFFFF),
                    root_offset,
                    level + 1,
                    (ids[0], name_id, 0),
                    found,
                )
                continue

            # برگ داده: ``IMAGE_RESOURCE_DATA_ENTRY``
            data_entry = root_offset + offset_field
            rva, size, _code_page, _reserved = struct.unpack_from("<IIII", self.blob, data_entry)
            resource_type, resource_name, _ = ids
            found.append(
                ResourceEntry(
                    resource_type=resource_type,
                    name=resource_name,
                    language=name_id,
                    rva=rva,
                    size=size,
                    data=self.read_at_rva(rva, size),
                )
            )


# --------------------------------------------------------------------------
# مقایسه
# --------------------------------------------------------------------------


@dataclass
class IconReport:
    exe: Path
    ico: Path
    frames: int
    group_icons: int
    exact_matches: int
    decoded_matches: int
    mismatches: list[str]

    @property
    def ok(self) -> bool:
        return not self.mismatches and self.frames > 0 and self.group_icons > 0


def _wrap_as_ico(frame: bytes) -> bytes:
    """یک فریم خام ``RT_ICON`` را در ظرف تک‌فریمی ICO می‌گذارد."""
    width, height = 0, 0
    if frame[:8] == b"\x89PNG\r\n\x1a\n":
        from PIL import Image
        import io

        with Image.open(io.BytesIO(frame)) as image:
            width, height = image.size
    else:
        # BITMAPINFOHEADER: ارتفاع دو برابر است (XOR + AND mask).
        height = struct.unpack_from("<i", frame, 4)[0] // 2
        width = struct.unpack_from("<i", frame, 8)[0]
    header = struct.pack(
        "<HHBBHHII", 0, 1, 1, width % 256, height % 256, 0, 32, len(frame), 22
    )
    return header + frame


def _decode_fingerprint(frame: bytes) -> tuple[int, int, str] | None:
    """اثر انگشت تصویر رمزگشایی‌شده؛ مستقل از بازکدوانی."""
    try:
        import io

        from PIL import Image

        with Image.open(io.BytesIO(_wrap_as_ico(frame))) as image:
            rgba = image.convert("RGBA")
            return (rgba.width, rgba.height, sha256(rgba.tobytes()).hexdigest())
    except Exception:  # pragma: no cover - فریم غیرقابل رمزگشایی
        return None


def _parse_group_icon(data: bytes) -> set[tuple[int, int, int, int]]:
    """اندازه‌های اعلام‌شدهٔ ``RT_GROUP_ICON`` را به شکل
    ``(width, height, bit_count, declared_size)`` برمی‌گرداند.

    نکتهٔ مهم: قالبِ **داخل منبع** با قالبِ **داخل فایل ‎.ico‎** یکی نیست.

    * فایل ``.ico`` → ``ICONDIRENTRY`` با ``_format_ = "bbbbhhii"`` یعنی
      **۱۶ بایت**، چون فیلد آخر ``dwImageOffset`` یک ``DWORD`` است.
    * منبع ``RT_GROUP_ICON`` → ``GRPICONDIRENTRY`` با
      ``_format_ = "bbbbhhih"`` یعنی **۱۴ بایت**، چون آخرین فیلد
      ``nID`` یک ``WORD`` است.

    PyInstaller در ``PyInstaller/utils/win32/icon.py`` هم دقیقاً همین
    ``GRPICONDIRENTRY`` را می‌سازد. پس اگر گام ۱۶ بایت فرض شود، هر entry
    بعد از اول جابه‌جا خوانده می‌شود و اندازه‌ها خراب می‌شوند.

    پس گام را از روی طول خودِ منبع تشخیص می‌دهیم و هر دو قالب را
    می‌پذیریم: ``6 + n*14`` برای منبع ویندوزی و ``6 + n*16`` برای هر
    ابزاری که اشتباهاً قالب فایلی را بنویسد.
    """
    if len(data) < 6:
        return set()
    count = struct.unpack_from("<H", data, 4)[0]
    if count <= 0:
        return set()

    for stride in (14, 16):
        if 6 + count * stride > len(data):
            continue
        found = _read_group_entries(data, count, stride)
        if found and len(found) == count:
            return found
    return set()


def _read_group_entries(
    data: bytes, count: int, stride: int
) -> set[tuple[int, int, int, int]]:
    """``count`` تا entry را با گام ``stride`` می‌خواند و معتبر بودنشان را می‌سنجد."""
    found: set[tuple[int, int, int, int]] = set()
    for index in range(count):
        base = 6 + index * stride
        if base + stride > len(data):
            return set()
        width, height, _colors, _reserved, _planes, bits, size = struct.unpack_from(
            "<BBBBHHI", data, base
        )
        del _colors, _reserved, _planes
        # bWidth/bHeight صفر یعنی ۲۵۶ (ICO بزرگ‌تر از ۲۵۵ را صفر می‌گذارد).
        if not (0 <= width <= 256 and 0 <= height <= 256):
            return set()
        if not (0 < size <= 4 * 1024 * 1024):
            return set()
        found.add((width or 256, height or 256, bits, size))
    return found


def verify(exe: Path, ico: Path) -> IconReport:
    ico_frames = read_ico(ico)
    pe = PeFile(exe.read_bytes())
    entries = pe.resources()

    icon_frames = [e for e in entries if e.resource_type == RT_ICON]
    group_icons = [e for e in entries if e.resource_type == RT_GROUP_ICON]

    mismatches: list[str] = []
    if not icon_frames:
        mismatches.append("EXE هیچ منبع RT_ICON ندارد؛ آیکن جا داده نشده است")
    if not group_icons:
        mismatches.append("EXE هیچ منبع RT_GROUP_ICON ندارد؛ ویندوز نمی‌تواند آیکن را بخواند")

    # ۱) مقایسهٔ بایت‌به‌بایت (رفتار PyInstaller)
    exe_digests = {sha256(e.data).hexdigest() for e in icon_frames}
    exact = 0
    for frame in ico_frames:
        if frame.digest in exe_digests:
            exact += 1
        else:
            mismatches.append(
                f"فریم {frame.width}×{frame.height} ({frame.size} بایت) بایت‌به‌بایت در EXE نیست"
            )

    # ۲) اگر بازکدوانی شده باشد، تصویر رمزگشایی‌شده را مقایسه کن.
    decoded = 0
    if exact != len(ico_frames):
        ico_fingerprints = {
            fp for fp in (_decode_fingerprint(f.data) for f in ico_frames) if fp
        }
        for entry in icon_frames:
            fingerprint = _decode_fingerprint(entry.data)
            if fingerprint and fingerprint in ico_fingerprints:
                decoded += 1
        if decoded != len(ico_frames):
            mismatches.append(
                f"تصویر رمزگشایی‌شدهٔ منابع EXE با k2.ico نمی‌خواند "
                f"({decoded} از {len(ico_frames)} فریم)"
            )

    # ۳) اندازه‌های اعلام‌شده در RT_GROUP_ICON باید با فایل ICO بخواند.
    declared: set[tuple[int, int, int, int]] = set()
    for entry in group_icons:
        declared |= _parse_group_icon(entry.data)
    expected = {(f.width, f.height, f.bit_count, f.size) for f in ico_frames}
    missing = expected - declared
    if missing:
        mismatches.append(
            "RT_GROUP_ICON این فریم‌ها را اعلام نکرده است: "
            + ", ".join(f"{w}×{h}" for w, h, _b, _s in sorted(missing))
        )

    return IconReport(
        exe=exe,
        ico=ico,
        frames=len(icon_frames),
        group_icons=len(group_icons),
        exact_matches=exact,
        decoded_matches=decoded,
        mismatches=mismatches,
    )


def _force_utf8_output() -> None:
    """خروجی را UTF-8 کن.

    روی ویندوز، وقتی stdout یک **لوله** است (و نه کنسول)، پایتون از encoding
    محلی استفاده می‌کند که روی runner گیت‌هاب cp1252 است. متن فارسی آن‌وقت
    ``UnicodeEncodeError`` می‌دهد و اسکریپت با «exit code 1» می‌شکند، در حالی
    که هیچ ایراد منطقی وجود ندارد. PEP 528 فقط کنسول را پوشش می‌دهد.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover - پایتون قدیمی
            pass


def _annotate(level: str, message: str) -> None:
    """یک پیام را در UI Actions نشان می‌دهد (اگر در GitHub Actions باشیم).

    لاگ خام گردش‌کار خوانده نشدن است؛ این‌طور خطا مستقیم روی Pull Request
    دیده می‌شود.
    """
    if not os.environ.get("GITHUB_ACTIONS"):
        return
    # ::error:: / ::warning:: / ::notice:: — پیام باید تک‌خطی باشد.
    one_line = " ".join(str(message).split())
    print(f"::{level}::{one_line}")


def _diagnose(exe: Path, ico: Path) -> list[str]:
    """چند خط خلاصه برای تشخیص عیب در CI.

    Actions فقط ۱۰ annotation برای هر گام نشان می‌دهد، پس این تابع عمداً
    خلاصه است: جدول بخش‌ها، منابع پیدا‌شده، و نتیجهٔ مقایسه در چند خط.
    """
    lines: list[str] = []
    try:
        ico_frames = read_ico(ico)
    except Exception as error:  # noqa: BLE001
        ico_frames = []
        lines.append(f"ico read failed: {error!r}")
    try:
        blob = exe.read_bytes()
        pe = PeFile(blob)
        entries = pe.resources()
    except Exception as error:  # noqa: BLE001
        lines.append(f"pe read failed: {error!r}")
        return lines

    lines.append(f"size={len(blob)} sections={len(pe.sections)}")
    lines.append(
        "sections="
        + ",".join(
            f"{sec.name}:0x{sec.virtual_address:x}/0x{sec.virtual_size:x}"
            f"/0x{sec.raw_size:x}/0x{sec.raw_pointer:x}"
            for sec in pe.sections
        )
    )
    lines.append(f"resource_rva=0x{pe.resource_base:x}")
    icons = [e for e in entries if e.resource_type == RT_ICON]
    groups = [e for e in entries if e.resource_type == RT_GROUP_ICON]
    lines.append(f"entries={len(entries)} icons={len(icons)} groups={len(groups)}")
    lines.append(f"exe_icon_sizes={[e.size for e in icons]}")
    lines.append(f"ico_frames={len(ico_frames)} ico_sizes={[f.size for f in ico_frames]}")

    exe_digests = {sha256(e.data).hexdigest() for e in icons}
    matched = sum(1 for f in ico_frames if f.digest in exe_digests)
    lines.append(f"exact_byte_matches={matched}/{len(ico_frames)}")

    for group in groups:
        declared = sorted(_parse_group_icon(group.data))
        lines.append(f"group_len={len(group.data)} declared={declared}")
    expected = sorted({(f.width, f.height, f.bit_count, f.size) for f in ico_frames})
    lines.append(f"expected={expected}")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path, help="فایل EXE ساختهٔ PyInstaller")
    parser.add_argument("ico", type=Path, help="فایل آیکن برنامه")
    args = parser.parse_args(argv)
    _force_utf8_output()

    if not args.exe.is_file():
        print(f"EXE پیدا نشد: {args.exe}", file=sys.stderr)
        return 2
    if not args.ico.is_file():
        print(f"فایل آیکن پیدا نشد: {args.ico}", file=sys.stderr)
        return 2

    try:
        report = verify(args.exe, args.ico)
    except IconVerificationError as error:
        # خطاهای ساختاری (فایل PE نیست، بخش منابع نیست، …) هم باید در UI
        # Actions دیده شوند، نه فقط در لاگ خام.
        _annotate("error", str(error))
        print(f"خطا: {error}", file=sys.stderr)
        return 1
    except Exception as error:  # noqa: BLE001 - هر خطای غیرمنتظره را گزارش کن
        # بدون این، یک باگ در پارسر فقط «exit code 1» می‌داد و علتش را
        # نمی‌شد فهمید. حالا علت در UI Actions دیده می‌شود.
        import traceback

        _annotate("error", f"بررسی آیکن با خطای غیرمنتظره متوقف شد: {error!r}")
        for line in _diagnose(args.exe, args.ico):
            _annotate("error", line)
        print(traceback.format_exc(), file=sys.stderr)
        return 1

    if os.environ.get("GITHUB_ACTIONS"):
        # تشخیص عیب‌یابی: بدون این، «CI قرمز است» تنها اطلاعات ممکن بود.
        for line in _diagnose(args.exe, args.ico):
            _annotate("notice", line)

    print(f"EXE            : {report.exe}")
    print(f"ICO            : {report.ico}")
    print(f"RT_ICON        : {report.frames}")
    print(f"RT_GROUP_ICON  : {report.group_icons}")
    print(f"تطابق بایت‌به‌بایت: {report.exact_matches}")
    print(f"تطابق تصویری   : {report.decoded_matches}")
    for problem in report.mismatches:
        _annotate("error", problem)
        print(f"خطا: {problem}", file=sys.stderr)
    if not report.ok:
        return 1
    print("آیکن برنامه واقعاً داخل EXE نشسته است.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
