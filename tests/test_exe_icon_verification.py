"""بررسی واقعی اینکه آیکن برنامه داخل EXE ویندوزی نشسته است.

چرا لازم است: ``k2.spec`` مسیر آیکن را به PyInstaller می‌دهد، ولی «مسیر
داده شده» به‌معنای «آیکن روی EXE نشسته» نیست. اگر فایل نبود یا PyInstaller
آیکن را جا نمی‌داد، کاربر آیکن پیش‌فرض را می‌دید و build هم خطا نمی‌داد.

این تست‌ها خودِ پارسر PE را با یک PE ساختگی که منابع واقعی دارد می‌آزمایند
(تا روی لینوکس هم بدون EXE ویندوزی قابل اجرا باشند)، و بعد پارسر را روی
فایل آیکن واقعی پروژه می‌سنجند.
"""

from __future__ import annotations

import importlib.util
import struct
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
EXE_ICON = ROOT / "src" / "k2" / "ui" / "assets" / "k2.ico"
SPEC = ROOT / "k2.spec"

_spec = importlib.util.spec_from_file_location(
    "k2_verify_exe_icon", ROOT / "packaging" / "verify_exe_icon.py"
)
assert _spec and _spec.loader
verifier = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = verifier
_spec.loader.exec_module(verifier)


# --------------------------------------------------------------------------
# ساخت یک PE ساختگی با بخش ‎.rsrc‎ حاوی منابع واقعی
# --------------------------------------------------------------------------

RT_ICON = 3
RT_GROUP_ICON = 14


def _align(value: int, alignment: int) -> int:
    return (value + alignment - 1) // alignment * alignment


def build_group_icon(
    frames: list[bytes],
    sizes: list[tuple[int, int, int, int]] | None = None,
    *,
    entry_stride: int = 14,
) -> bytes:
    """``RT_GROUP_ICON``: دقیقاً کاری که PyInstaller می‌کند.

    ``ICONDIRHEADER`` + ``GRPICONDIRENTRY``ها.

    اینجا دقت لازم است: قالبِ داخل منبع با قالبِ داخل فایل ‎.ico‎ یکی
    نیست. در فایل ``ICONDIRENTRY`` شونزده بایت است (``"bbbbhhii"``) چون
    فیلد آخر ``dwImageOffset`` یک DWORD است. ولی داخل منبع
    ``GRPICONDIRENTRY`` **چهارده** بایت است (``"bbbbhhih"``) چون آخرین
    فیلد ``nID`` یک WORD است — و PyInstaller دقیقاً همین را می‌نویسد
    (``PyInstaller/utils/win32/icon.py::GRPICONDIRENTRY``).

    ``entry_stride=16`` فقط برای آزمودن حالت دفاعی است که یک ابزار دیگر
    اشتباهاً قالب فایلی را داخل منبع گذاشته باشد.
    """
    entries = b""
    for index, frame in enumerate(frames):
        if sizes is not None:
            width, height, bits, declared_size = sizes[index]
        elif frame[:8] == b"\x89PNG\r\n\x1a\n":
            width, height, bits, declared_size = 16, 16, 32, len(frame)
        else:
            height = struct.unpack_from("<i", frame, 4)[0] // 2
            width = struct.unpack_from("<i", frame, 8)[0]
            bits, declared_size = 32, len(frame)
        if entry_stride == 16:
            # قالب فایلی (اشتباهی داخل منبع): dwImageOffset به جای nID.
            entries += struct.pack(
                "<BBBBHHII",
                width % 256,
                height % 256,
                0,
                0,
                1,
                bits,
                declared_size,
                index + 1,
            )
        else:
            assert entry_stride == 14, entry_stride
            # قالب واقعی منبع: GRPICONDIRENTRY با nID دو بایتی.
            entries += struct.pack(
                "<BBBBHHIH",
                width % 256,
                height % 256,
                0,
                0,
                1,
                bits,
                declared_size,
                index + 1,
            )
    return struct.pack("<HHH", 0, 1, len(frames)) + entries


def build_pe_with_icon(
    frames: list[bytes],
    *,
    include_group: bool = True,
    frame_sizes: list[tuple[int, int, int, int]] | None = None,
    entry_stride: int = 14,
) -> bytes:
    """یک PE حداقلی می‌سازد که منابع آیکن آن از ``frames`` ساخته شده است.

    ساختار درخت منابع همان چیزی است که ویندوز و PyInstaller می‌سازند:
    ``root -> نوع منبع -> نام -> زبان -> IMAGE_RESOURCE_DATA_ENTRY``.
    """
    file_alignment = 0x200
    section_alignment = 0x1000

    resources: list[tuple[int, int, bytes]] = [
        (RT_ICON, index + 1, frame) for index, frame in enumerate(frames)
    ]
    if include_group:
        resources.append(
            (RT_GROUP_ICON, 1, build_group_icon(frames, frame_sizes, entry_stride=entry_stride))
        )

    # --- بدنهٔ بخش ‎.rsrc‎ را از پایین به بالا می‌سازیم ---
    body = bytearray()
    rsrc_rva = section_alignment

    def append_directory(entry_count: int) -> int:
        """دایرکتوری منابع را با جایگاه رزروشده برای entryها می‌سازد."""
        offset = len(body)
        body.extend(struct.pack("<IIHHHH", 0, 0, 0, 0, 0, entry_count))
        body.extend(b"\x00" * (entry_count * 8))
        return offset

    def append_resource(name_id: int, blob: bytes) -> tuple[int, int]:
        """یک منبع کامل (دایرکتوری زبان + دادهٔ منبع) را اضافه می‌کند.

        جایگاه entry زبان را ``append_directory`` از قبل رزرو کرده است، پس
        باید همان‌جا پر شود — نه اینکه یک entry تازه بعد از دایرکتوری اضافه
        شود (وگرنه جایگاه رزروشده صفر می‌ماند و به RVA 0 اشاره می‌کند).
        """
        language_offset = append_directory(1)
        entry_slot = language_offset + 16
        body.extend(struct.pack("<II", 0x0409, 0))  # زبان، آفست داده (اصلاح می‌شود)
        data_entry_offset = len(body)
        body.extend(struct.pack("<IIII", 0, len(blob), 0, 0))
        blob_offset = len(body)
        body.extend(blob)
        # برگِ زبان به data entry اشاره می‌کند (بیت بالا صفر = برگ داده).
        struct.pack_into("<I", body, entry_slot + 4, data_entry_offset)
        # data entry به RVA واقعی بلاب اشاره می‌کند.
        struct.pack_into("<I", body, data_entry_offset, rsrc_rva + blob_offset)
        return language_offset, name_id

    by_type: dict[int, list[tuple[int, bytes]]] = {}
    for type_id, name_id, blob in resources:
        by_type.setdefault(type_id, []).append((name_id, blob))

    # دایرکتوری ریشه باید اولین چیز بخش ‎.rsrc‎ باشد، چون DataDirectory[2]
    # دقیقاً به همان RVA اشاره می‌کند. پس جایش را از قبل رزرو می‌کنیم و
    # entryهایش را در پایان می‌نویسیم.
    root_offset = append_directory(len(by_type))

    type_directories: list[tuple[int, int]] = []
    for type_id, items in by_type.items():
        names = [append_resource(name_id, blob) for name_id, blob in items]
        name_directory = append_directory(len(names))
        for slot, (language_offset, name_id) in enumerate(names):
            position = name_directory + 16 + slot * 8
            struct.pack_into("<II", body, position, name_id, 0x80000000 | language_offset)
        type_directories.append((type_id, name_directory))

    for slot, (type_id, name_directory) in enumerate(type_directories):
        position = root_offset + 16 + slot * 8
        struct.pack_into("<II", body, position, type_id, 0x80000000 | name_directory)

    # --- هدرهای PE ---
    size_of_optional_header = 240
    header_size = _align(0x200 + 4 + 20 + size_of_optional_header + 40, file_alignment)
    rsrc_size = _align(len(body), section_alignment)

    # سرآیند DOS دقیقاً ۰x۸۰ بایت است تا امضای PE همان‌جا بنشیند که
    # e_lfanew به آن اشاره می‌کند.
    pe = bytearray(0x80)
    pe[:2] = b"MZ"
    struct.pack_into("<I", pe, 0x3C, 0x80)

    pe.extend(b"PE\x00\x00")
    pe.extend(
        struct.pack("<HHIIIHH", 0x8664, 1, 0, 0, 0, size_of_optional_header, 0x0022)
    )
    optional = bytearray(size_of_optional_header)
    struct.pack_into("<H", optional, 0, 0x20B)  # PE32+
    # DataDirectory[2] = منبع (IMAGE_DIRECTORY_ENTRY_RESOURCE)
    struct.pack_into("<II", optional, 112 + 8 * 2, rsrc_rva, rsrc_size)
    pe.extend(optional)

    pe.extend(b".rsrc\x00\x00\x00")
    pe.extend(struct.pack("<IIII", len(body), rsrc_rva, rsrc_size, header_size))
    pe.extend(struct.pack("<II", 0, 0))
    pe.extend(struct.pack("<HH", 0, 0))
    pe.extend(struct.pack("<I", 0x40000040))
    # هدرها باید تا مرز تراز فایل پر شوند، وگرنه PointerToRawData دروغ می‌گوید.
    pe.extend(b"\x00" * (header_size - len(pe)))
    assert len(pe) == header_size, (len(pe), header_size)

    pe.extend(body)
    return bytes(pe)


# --------------------------------------------------------------------------
# تست‌ها
# --------------------------------------------------------------------------


def test_ico_file_is_a_real_multisize_icon():
    frames = verifier.read_ico(EXE_ICON)
    assert frames, "فایل k2.ico هیچ فریمی ندارد"
    sizes = {(f.width, f.height) for f in frames}
    # ویندوز برای نوار عنوان، Alt+Tab و Explorer به این اندازه‌ها نیاز دارد.
    assert {(16, 16), (32, 32), (48, 48), (256, 256)} <= sizes, sorted(sizes)


def test_ico_frames_are_nonempty_and_distinct():
    frames = verifier.read_ico(EXE_ICON)
    digests = [f.digest for f in frames]
    assert len(set(digests)) == len(digests), "دو فریم تکراری در آیکن هست"
    for frame in frames:
        assert frame.size > 0
        assert frame.data[:8] == b"\x89PNG\r\n\x1a\n" or frame.data[:2] == b"\x28\x00", (
            f"فریم {frame.width}×{frame.height} نه PNG است نه BMP"
        )


def test_verifier_reads_icons_out_of_a_real_pe():
    """پارسر PE باید منابعی که خودمان در PE ساختگی گذاشتیم پیدا کند."""
    ico_frames = verifier.read_ico(EXE_ICON)
    frames = [f.data for f in ico_frames]
    sizes = [(f.width, f.height, f.bit_count, f.size) for f in ico_frames]
    pe = build_pe_with_icon(frames, frame_sizes=sizes)

    parsed = verifier.PeFile(pe)
    entries = parsed.resources()
    icons = [e for e in entries if e.resource_type == RT_ICON]
    groups = [e for e in entries if e.resource_type == RT_GROUP_ICON]

    assert len(icons) == len(frames), (
        f"{len(icons)} منبع RT_ICON پیدا شد، {len(frames)} انتظار می‌رفت"
    )
    assert len(groups) == 1, "RT_GROUP_ICON پیدا نشد"
    # محتوای هر منبع باید بایت‌به‌بایت همان فریم فایل ICO باشد.
    assert {e.data for e in icons} == set(frames)


def test_verifier_accepts_an_exe_that_really_has_the_icon(tmp_path: Path):
    ico_frames = verifier.read_ico(EXE_ICON)
    frames = [f.data for f in ico_frames]
    sizes = [(f.width, f.height, f.bit_count, f.size) for f in ico_frames]
    exe = tmp_path / "K2.exe"
    exe.write_bytes(build_pe_with_icon(frames, frame_sizes=sizes))

    report = verifier.verify(exe, EXE_ICON)

    assert report.ok, report.mismatches
    assert report.frames == len(frames)
    assert report.exact_matches == len(frames)


def test_verifier_rejects_an_exe_with_no_icon_at_all(tmp_path: Path):
    exe = tmp_path / "K2.exe"
    exe.write_bytes(build_pe_with_icon([], include_group=False))

    report = verifier.verify(exe, EXE_ICON)

    assert not report.ok
    assert any("RT_ICON" in problem for problem in report.mismatches)


def test_verifier_rejects_an_exe_with_a_different_icon(tmp_path: Path):
    """آیکن اشتباه نباید قبول شود؛ همین‌طور آیکن ناقص."""
    frames = [f.data for f in verifier.read_ico(EXE_ICON)]
    exe = tmp_path / "K2.exe"
    exe.write_bytes(build_pe_with_icon(frames[:2]))

    report = verifier.verify(exe, EXE_ICON)

    assert not report.ok
    assert any("بایت‌به‌بایت در EXE نیست" in problem for problem in report.mismatches)


def test_verifier_rejects_an_exe_without_the_group_icon(tmp_path: Path):
    frames = [f.data for f in verifier.read_ico(EXE_ICON)]
    exe = tmp_path / "K2.exe"
    exe.write_bytes(build_pe_with_icon(frames, include_group=False))

    report = verifier.verify(exe, EXE_ICON)

    assert not report.ok
    assert any("RT_GROUP_ICON" in problem for problem in report.mismatches)


def test_verifier_rejects_a_non_pe_file(tmp_path: Path):
    bogus = tmp_path / "not-an-exe.exe"
    bogus.write_bytes(b"this is not a windows executable at all")

    with pytest.raises(verifier.IconVerificationError):
        verifier.verify(bogus, EXE_ICON)


def test_verifier_rejects_a_broken_ico(tmp_path: Path):
    broken = tmp_path / "broken.ico"
    broken.write_bytes(b"\x00\x00\x01\x00" + b"\x00" * 4)

    with pytest.raises(verifier.IconVerificationError):
        verifier.read_ico(broken)


def test_pyinstaller_spec_points_at_the_icon_that_gets_verified():
    """اسکریپت CI باید همان فایلی را بررسی کند که spec به آن اشاره می‌کند."""
    spec_text = SPEC.read_text(encoding="utf-8")
    assert "k2.ico" in spec_text, "k2.spec باید آیکن برنامه را جاسازی کند"
    assert "verify_exe_icon.py" in (
        ROOT / ".github" / "workflows" / "build-windows.yml"
    ).read_text(encoding="utf-8"), (
        "گردش‌کار CI باید آیکنِ داخل EXE را واقعاً بررسی کند"
    )
    assert EXE_ICON.is_file()


def test_resource_group_icon_entries_are_fourteen_bytes_not_sixteen():
    """قرارداد اصلی: ``GRPICONDIRENTRY`` چهارده بایت است، نه شونزده.

    ``ICONDIRENTRY`` داخل فایل ``.ico`` شونزده بایت است چون فیلد آخر
    ``dwImageOffset`` یک DWORD است. ولی ``GRPICONDIRENTRY`` داخل منبع
    ``RT_GROUP_ICON`` چهارده بایت است چون آخرین فیلد ``nID`` یک WORD است —
    و PyInstaller دقیقاً همین را می‌نویسد
    (``PyInstaller/utils/win32/icon.py::GRPICONDIRENTRY`` با
    ``_format_ = "bbbbhhih"``).

    اگر کسی دوباره گام را شونزده فرض کند، این تست می‌شکند.
    """
    frames = [f.data for f in verifier.read_ico(EXE_ICON)]
    group = build_group_icon(frames)

    count = struct.unpack_from("<H", group, 4)[0]
    assert count == len(frames)
    assert len(group) == 6 + count * 14, (
        "RT_GROUP_ICON باید ۶ + n×۱۴ بایت باشد (GRPICONDIRENTRY)، نه شونزده"
    )
    assert struct.calcsize("<BBBBHHIH") == 14
    assert struct.calcsize("<BBBBHHII") == 16


def test_verifier_reads_a_group_icon_written_in_the_file_entry_format(tmp_path: Path):
    """حالت دفاعی: ابزاری که اشتباهاً قالب فایلی را داخل منبع گذاشته.

    گام ۱۴ بایت است، ولی اگر کسی شونزده بایت بنویسد نباید نتیجهٔ گمراه‌کننده
    بدهیم؛ همان اندازه‌ها باید خوانده شوند.
    """
    ico_frames = verifier.read_ico(EXE_ICON)
    frames = [f.data for f in ico_frames]
    sizes = [(f.width, f.height, f.bit_count, f.size) for f in ico_frames]

    exe = tmp_path / "K2.exe"
    exe.write_bytes(
        build_pe_with_icon(frames, frame_sizes=sizes, entry_stride=16)
    )

    report = verifier.verify(exe, EXE_ICON)
    assert report.ok, report.mismatches
    assert report.frames == len(frames)


def test_verifier_reports_geometry_when_the_group_icon_declares_other_sizes(tmp_path: Path):
    """اگر group icon اندازه‌های دیگری اعلام کند، build باید شکست بخورد."""
    ico_frames = verifier.read_ico(EXE_ICON)
    frames = [f.data for f in ico_frames]
    wrong = [(16, 16, 32, 999) for _ in frames]

    exe = tmp_path / "K2.exe"
    exe.write_bytes(build_pe_with_icon(frames, frame_sizes=wrong))

    report = verifier.verify(exe, EXE_ICON)
    assert not report.ok
    assert any("RT_GROUP_ICON" in problem for problem in report.mismatches)


def test_a_two_hundred_fifty_six_frame_declares_zero_geometry():
    """ICO فریم ۲۵۶×۲۵۶ را با bWidth=0 اعلام می‌کند؛ صفر یعنی ۲۵۶."""
    biggest = max((f.data for f in verifier.read_ico(EXE_ICON)), key=len)

    group = build_group_icon([biggest], [(256, 256, 32, len(biggest))])
    declared = verifier._parse_group_icon(group)

    assert (256, 256, 32, len(biggest)) in declared, sorted(declared)
