"""نصب‌کنندهٔ استاندارد ویندوز باید واقعاً یک installer باشد.

چرا لازم است: کاربر صریحاً خواست که فایل exe «کاملاً استاندارد» نصب شود و
«وقتی نصب را زدم فایل سی‌ام‌دی بیاورد». این تست‌ها همان قول را می‌بندند:
فایل ISS با کلیدهای استاندارد نصب، زبان فارسی راست‌چین، آیکن، و اتصال واقعی
نصب‌کننده به گردش‌کار CI و بستهٔ دانلود.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
ISS = ROOT / "packaging" / "k2_installer.iss"
FARSI_ISL = ROOT / "packaging" / "innosetup" / "Languages" / "Farsi.isl"
ICON = ROOT / "src" / "k2" / "ui" / "assets" / "k2.ico"
SPEC = ROOT / "k2.spec"
WORKFLOW = ROOT / ".github" / "workflows" / "build-windows.yml"
README = ROOT / "README.md"
PACKAGER = ROOT / "packaging" / "create_windows_download.py"

GUID = re.compile(r"^\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}$")


def _packager_module():
    spec = importlib.util.spec_from_file_location("k2_download_packager_iss", PACKAGER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_DEFINE = re.compile(r"^\s*#define\s+(\w+)\s+(.*?)\s*$")
_INLINE = re.compile(r"\{#(\w+)\}")
_PARAM_SECTIONS = {
    "Files",
    "Icons",
    "Tasks",
    "Run",
    "Languages",
    "UninstallDelete",
    "InstallDelete",
}


def _resolve_defines(text: str) -> str:
    """ISPP ``#define`` و ``{#Name}`` را حل می‌کند تا مقدار واقعی دیده شود."""
    defines: dict[str, str] = {}
    for raw in text.splitlines():
        m = _DEFINE.match(raw)
        if not m:
            continue
        name, value = m.group(1), m.group(2)
        defines[name] = value.strip('"')
    for _ in range(8):  # یک define می‌تواند به define دیگر اشاره کند
        expanded = _INLINE.sub(lambda m: defines.get(m.group(1), m.group(0)), text)
        if expanded == text:
            break
        text = expanded
    return text


def _iss_sections(text: str) -> dict[str, dict[str, str]]:
    """فایل ISS را به بخش/کلید تجزیه می‌کند (با حفظ ترتیب).

    ``[Setup]`` و ``[Messages]`` از شکل ``key=value`` استفاده می‌کنند؛
    ``[Files]``/``[Icons]``/``[Tasks]``/``[Run]`` از شکل پارامتری
    ``Name: value; Description: ...``. هر دو پشتیبانی می‌شود.
    """
    text = _resolve_defines(text)
    sections: dict[str, dict[str, str]] = {}
    current: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith((";", "#", "//")):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            sections.setdefault(current, {})
            continue
        if current is None:
            continue
        if current in _PARAM_SECTIONS:
            # چند پارامتر روی یک خط، با «;» جدا شده‌اند.
            parts = [part.strip() for part in line.split(";") if part.strip()]
            for index, part in enumerate(parts):
                if ":" in part:
                    key, value = part.split(":", 1)
                else:
                    key, value = f"line{index}", part
                key = key.strip().lower()
                if key in sections[current]:
                    suffix = 2
                    while f"{key}_{suffix}" in sections[current]:
                        suffix += 1
                    key = f"{key}_{suffix}"
                sections[current][key] = value.strip().strip('"')
        elif "=" in line:
            key, value = line.split("=", 1)
            sections[current][key.strip().lower()] = value.strip()
    return sections


def _app_id(text: str) -> str:
    """مقدار نهایی AppId پس از عبور از پیش‌پردازشگر Inno Setup.

    ``{#StringChange(MyAppId, '{', '{{')}`` همان GUID است، چون پیش‌پردازشگر
    خروجی خود را دوباره نمی‌خواند و «{{» در مرحلهٔ پارس به «{» تبدیل می‌شود.
    """
    defines: dict[str, str] = {}
    for raw in text.splitlines():
        m = _DEFINE.match(raw)
        if m:
            defines[m.group(1)] = m.group(2).strip().strip('"')
    line = next(
        (l for l in text.splitlines() if l.strip().lower().startswith("appid=")), ""
    )
    if "StringChange(" in line:
        m = re.search(r"StringChange\((\w+)", line)
        if m and m.group(1) in defines:
            return defines[m.group(1)]
    return _resolve_defines(line.split("=", 1)[1]).strip()


# --------------------------------------------------------------------------
# ۱) فایل نصب‌کننده: وجود و کلیدهای استاندارد
# --------------------------------------------------------------------------


def test_innosetup_script_exists_and_declares_a_standard_install():
    text = ISS.read_text(encoding="utf-8")
    sections = _iss_sections(text)

    assert "Setup" in sections, "فایل ISS بخش [Setup] ندارد"
    setup = sections["Setup"]

    # شناسهٔ ثابت: بدون آن هر نصب، «نصب تکراری» می‌شود و به‌روزرسانی کار نمی‌کند.
    app_id = _app_id(text)
    assert GUID.match(app_id), f"AppId ثابت و معتبر نیست: {app_id!r}"

    assert setup.get("appname", "").strip(), "AppName لازم است"
    assert setup.get("appversion", "").strip(), "AppVersion لازم است"

    # نصب استاندارد در Program Files با ارتقای سطح دسترسی.
    assert "{autopf}" in setup.get("defaultdirname", "").lower(), (
        "DefaultDirName باید به Program Files اشاره کند تا نصب «استاندارد» باشد"
    )
    assert setup.get("privilegesrequired", "").lower() == "admin", (
        "PrivilegesRequired=admin لازم است تا همهٔ کاربران ویندوز برنامه را ببینند"
    )

    # فقط ۶۴ بیتی: PyInstaller این پروژه x64 است.
    assert "x64compatible" in setup.get("architecturesallowed", "").lower()
    assert "x64compatible" in setup.get("architecturesinstallin64bitmode", "").lower()

    # فشرده‌سازی مدرن.
    assert "lzma2" in setup.get("compression", "").lower()
    assert setup.get("solidcompression", "").lower() == "yes"


def test_appid_reaches_the_compiler_with_a_usable_guid():
    """Inno Setup ``{`` را آغاز constant می‌بیند، پس GUID باید فرار داده شود.

    بدون این، ``AppId={7C4E...}`` به‌عنوان constant ناشناخته خطای کامپایل
    می‌دهد و کل نصب‌کننده ساخته نمی‌شود.
    """
    text = ISS.read_text(encoding="utf-8")
    defines: dict[str, str] = {}
    for raw in text.splitlines():
        m = _DEFINE.match(raw)
        if m:
            defines[m.group(1)] = m.group(2).strip().strip('"')

    assert "MyAppId" in defines, "GUID برنامه در #define تعریف نشده است"
    assert GUID.match(defines["MyAppId"]), f"GUID برنامه معتبر نیست: {defines['MyAppId']}"

    app_id_line = next(
        line for line in text.splitlines() if line.strip().lower().startswith("appid=")
    )
    assert "StringChange(MyAppId, '{', '{{')" in app_id_line, (
        "AppId باید شکل فرار‌داده‌شدهٔ {{GUID} را بگیرد؛ "
        "بیرون از این، کامپایلر GUID را constant می‌بیند."
    )


def test_innosetup_script_registers_add_remove_programs_entry():
    text = ISS.read_text(encoding="utf-8")
    sections = _iss_sections(text)

    # Inno Setup خودش ورودی «برنامه‌ها و قابلیت‌ها» را می‌سازد؛ این‌ها فقط
    # باید آیکن و نام راستین به آن ورودی بدهند.
    setup_keys = {k.lower() for k in sections.get("Setup", {})}
    assert "uninstalldisplayicon" in setup_keys, (
        "UninstallDisplayIcon لازم است تا نصب در فهرست برنامه‌ها آیکن داشته باشد"
    )
    assert "appmutex" in setup_keys, "AppMutex از نصب هم‌زمان جلوگیری می‌کند"


def test_innosetup_script_installs_the_whole_distribution_and_creates_shortcuts():
    text = ISS.read_text(encoding="utf-8")
    sections = _iss_sections(text)

    files = sections.get("Files", {})
    assert files, "بخش [Files] خالی است"
    # باید کل پوشهٔ PyInstaller (EXE + _internal) رفته باشد.
    joined = " ".join(files.values()).lower()
    assert "k2.exe" in joined or "{app}" in joined, "فایل اجرایی اصلی نصب نمی‌شود"
    assert "recursesubdirs" in joined, (
        "بدون recursesubdirs پوشهٔ _internal منتقل نمی‌شود و برنامه اجرا نمی‌شود"
    )

    icons = sections.get("Icons", {})
    icon_lines = list(icons.values())
    assert any("K2.exe" in line for line in icon_lines), "میان‌بر اجرای برنامه ساخته نمی‌شود"
    assert any("{uninstallexe}" in line for line in icon_lines), "میان‌بر حذف نصب ساخته نمی‌شود"
    # فهرست Start-Menu برای همهٔ کاربران.
    assert "{group}" in text, "میان‌بر فهرست شروع ساخته نمی‌شود"

    # میان‌بر میزکار باید از طریق [Tasks] قابل رد کردن باشد.
    tasks = sections.get("Tasks", {})
    assert tasks, "بخش [Tasks] خالی است؛ میان‌بر میزکار اجباری می‌شود"
    task_values = " ".join(tasks.values()).lower()
    assert "desktopicon" in task_values, "Task میان‌بر میزکار تعریف نشده"


def test_innosetup_script_preserves_user_data_on_uninstall():
    text = ISS.read_text(encoding="utf-8")
    sections = _iss_sections(text)

    uninstall_delete = " ".join(sections.get("UninstallDelete", {}).values())
    assert "{app}" in uninstall_delete, (
        "حذف نصب باید فقط پوشهٔ برنامه را پاک کند تا دادهٔ کاربر حفظ شود"
    )
    # هیچ‌جای فایل نباید پوشهٔ دادهٔ کاربر (AppData) پاک شود.
    for forbidden in ("{userappdata}", "{localappdata}", "{commonappdata}"):
        assert forbidden not in uninstall_delete.lower(), (
            f"حذف نصب نباید {forbidden} را پاک کند"
        )


def test_innosetup_script_handles_a_running_app_during_install():
    """اگر برنامه باز باشد، نصب نباید بی‌صدا خراب شود.

    Inno این کار را به‌صورت بومی انجام می‌دهد: ``AppMutex`` نام mutex مشترک
    را اعلام می‌کند و ``CloseApplications=yes`` فرایند قفل‌کنندهٔ فایل را
    می‌بندد. پیش‌تر یک ``CheckForMutexes`` روی GUID نوشته شده بود که هیچ
    فرایندی آن mutex را نمی‌ساخت، پس همیشه False بود و بی‌اثر — این تست
    همان چیزی را می‌سنجد که واقعاً کار می‌کند.
    """
    text = ISS.read_text(encoding="utf-8")
    assert "AppMutex=" in text, "AppMutex نیست؛ نصب‌کننده برنامهٔ در حال اجرا را نمی‌بیند"
    assert "CloseApplications=yes" in text, (
        "CloseApplications نیست؛ اگر برنامه باز باشد نصب روی فایل قفل‌شده می‌شکند"
    )
    # نام mutex اعلام‌شده باید همان چیزی باشد که برنامه واقعاً می‌سازد، وگرنه
    # دوباره کد مرده ساخته‌ایم. اپلیکیشن نام را در src/k2/app.py می‌سازد.
    app_py = (ROOT / "src" / "k2" / "app.py").read_text(encoding="utf-8")
    mutex_name = re.search(r"AppMutex=([^\r\n]+)", text).group(1).split(",")[0].strip()
    assert mutex_name in app_py, (
        f"AppMutex به '{mutex_name}' اشاره می‌کند ولی app.py آن را نمی‌سازد؛ "
        "پس دوباره بی‌اثر است"
    )


def test_innosetup_script_uses_the_persian_language_file():
    text = ISS.read_text(encoding="utf-8")
    assert "Farsi.isl" in text, "زبان فارسی به نصب‌کننده وصل نشده است"


def test_every_relative_path_in_the_iss_resolves_inside_the_repository():
    """Inno Setup مسیرهای نسبی را نسبت به پوشهٔ فایل ISS حل می‌کند.

    اگر کسی مسیر را نسبت به ریشهٔ مخزن بنویسد (مثلاً ``packaging\\output``)
    کامپایل روی CI با «file not found» شکست می‌خورد، چون ریشه واقعیِ مرجع
    ``packaging/`` است نه ریشهٔ مخزن.
    """
    sections = _iss_sections(ISS.read_text(encoding="utf-8"))
    base = ISS.parent
    setup = sections["Setup"]

    # ۱) فایل‌هایی که واقعاً در مخزن هستند باید حل شوند.
    for key in ("setupiconfile",):
        value = setup.get(key)
        assert value, f"{key} تعریف نشده است"
        assert not value.lower().startswith("packaging\\"), (
            f"{key} نباید پیشوند packaging\\ داشته باشد؛ ریشهٔ مرجع خودِ packaging است"
        )
        resolved = (base / value.replace("\\", "/")).resolve()
        assert resolved.is_file(), f"آیکن پیدا نشد: {value} -> {resolved}"

    farsi_messages = [
        v
        for k, v in sections.get("Languages", {}).items()
        if k == "messagesfile" and "farsi" in str(v).lower() or "farsi.isl" in str(v).lower()
    ]
    for value in farsi_messages:
        assert not value.lower().startswith("packaging\\"), (
            f"مسیر فایل زبان نباید پیشوند packaging\\ داشته باشد: {value}"
        )
        resolved = (base / value.replace("\\", "/")).resolve()
        assert resolved.is_file(), f"فایل زبان پیدا نشد: {value} -> {resolved}"

    # ۲) خروجی PyInstaller: باید «output\K2» باشد، نه «packaging\output\K2».
    files_source = " ".join(sections.get("Files", {}).values())
    assert "output\\K2" in files_source, (
        f"منبع [Files] باید خروجی PyInstaller در packaging/output/K2 باشد: {files_source}"
    )
    assert "packaging\\output" not in files_source, (
        "پیشوند packaging\\ در Source اشتباه است؛ ریشهٔ مرجع خودِ packaging است"
    )

    # ۳) پوشهٔ خروجی هم نباید پیشوند packaging\\ داشته باشد.
    output_dir = setup.get("outputdir", "")
    assert output_dir and not output_dir.lower().startswith("packaging\\"), (
        f"OutputDir باید نسبت به packaging باشد: {output_dir!r}"
    )
    assert (base / output_dir.replace("\\", "/")).resolve().parent.exists()


def test_innosetup_script_registers_the_persian_language_first():
    """فارسی زبان پیش‌فرض نصب‌کننده باشد، نه انگلیسی."""
    sections = _iss_sections(ISS.read_text(encoding="utf-8"))
    languages = sections.get("Languages", {})
    assert languages, "بخش [Languages] خالی است"
    messages = [v for k, v in languages.items() if k == "messagesfile"]
    assert messages, f"فایل زبان تعریف نشده: {languages}"
    assert "farsi.isl" in messages[0].lower(), f"زبان اول فارسی نیست: {messages[0]}"


def test_innosetup_output_is_a_single_standard_setup_executable():
    sections = _iss_sections(ISS.read_text(encoding="utf-8"))
    setup = sections["Setup"]
    assert setup.get("outputbasefilename", "").startswith("K2-Setup"), (
        "نام خروجی باید K2-Setup باشد تا کاربر بفهمد نصب‌کننده است"
    )
    assert setup.get("wizardstyle", "").lower() == "modern", "WizardStyle=modern رابط استاندارد می‌دهد"



# ۲) زبان فارسی
# --------------------------------------------------------------------------


def test_persian_innosetup_language_is_right_to_left():
    text = FARSI_ISL.read_text(encoding="utf-8")
    assert "RightToLeft=yes" in text.replace(" ", ""), "زبان فارسی باید راست‌چین باشد"
    assert "LanguageID=$0429" in text.replace(" ", ""), "LanguageID فارسی ($0429) ثبت نشده"
    # نام زبان باید برای کاربر فارسی‌زبان خوانا باشد.
    assert any(name in text for name in ("فارسی", "Persian")), "نام زبان خوانا نیست"


def test_persian_language_file_translates_the_core_wizard_steps():
    text = FARSI_ISL.read_text(encoding="utf-8")
    for key in ("ClickNext", "ClickInstall", "FinishedHeading", "WelcomeLabel", "UninstallAppTitle"):
        assert key in text, f"پیام {key} ترجمه نشده و کاربر انگلیسی می‌بیند"


# --------------------------------------------------------------------------
# ۳) آیکن
# --------------------------------------------------------------------------


def test_application_icon_exists_and_is_a_valid_multisize_ico():
    assert ICON.is_file(), "آیکن k2.ico ساخته نشده است"
    assert ICON.stat().st_size > 0

    from PIL import Image

    with Image.open(ICON) as image:
        assert image.format == "ICO"
        sizes = {size[0] for size in image.ico.sizes()}
    # بدون این اندازه‌ها ویندوز آیکن را تار نشان می‌دهد.
    assert {16, 32, 48, 256}.issubset(sizes), f"اندازه‌های آیکن ناقص است: {sorted(sizes)}"


def test_pyinstaller_spec_embeds_the_icon():
    text = SPEC.read_text(encoding="utf-8")
    assert "k2.ico" in text, "k2.spec باید آیکن برنامه را جاسازی کند"


# --------------------------------------------------------------------------
# ۴) اتصال نصب‌کننده به CI و بستهٔ دانلود
# --------------------------------------------------------------------------


def test_ci_workflow_builds_verifies_and_ships_the_installer():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "iscc" in text, "گردش‌کار نصب‌کننده را با iscc نمی‌سازد"
    assert "k2_installer.iss" in text, "گردش‌کار به فایل ISS اشاره نمی‌کند"
    assert "Build the standard Windows installer" in text, "گام ساخت نصب‌کننده در CI نیست"

    # بررسی واقعی فایل ساخته‌شده، نه فقط صدور دستور.
    assert "Verify the installer is a standard Windows package" in text, (
        "CI باید فایل نصب‌کننده را تأیید کند"
    )

    # artifact و release.
    assert "K2-windows-installer" in text, "نصب‌کننده به‌عنوان artifact آپلود نمی‌شود"
    assert "packaging/output/K2-Setup-*.exe" in text, "نصب‌کننده در release نیست"

    # بستهٔ دانلود مخزن.
    assert "git add downloads/K2-Setup-*.exe" in text, (
        "نصب‌کننده در بستهٔ دانلود ثبت‌شدهٔ مخزن commit نمی‌شود"
    )
    assert "--installer" in text, "ساخت بستهٔ دانلود باید نصب‌کننده را هم بگیرد"


def test_download_packager_can_record_the_installer():
    module = _packager_module()
    assert hasattr(module, "install_installer"), "create_windows_download تابع ثبت نصب‌کننده ندارد"
    assert "--installer" in PACKAGER.read_text(encoding="utf-8")


def test_download_packager_copies_the_installer_into_downloads(tmp_path: Path):
    module = _packager_module()
    source = tmp_path / "K2-Setup-1.0.0.exe"
    source.write_bytes(b"MZfake-installer")
    destination = tmp_path / "downloads" / "K2-Setup-1.0.0.exe"

    result = module.install_installer(source, destination)

    assert result == destination
    assert destination.read_bytes() == b"MZfake-installer"


def test_download_packager_refuses_a_missing_installer(tmp_path: Path):
    module = _packager_module()
    with pytest.raises(FileNotFoundError):
        module.install_installer(tmp_path / "does-not-exist.exe", tmp_path / "out.exe")


def test_release_metadata_accepts_an_installer_hash(tmp_path: Path):
    """README و سند انتشار باید هش نصب‌کننده را هم ثبت کنند."""
    import shutil

    module = _packager_module()

    source = tmp_path / "K2"
    (source / "_internal").mkdir(parents=True)
    (source / "K2.exe").write_bytes(b"sample executable")
    archive = tmp_path / "K2-windows-x64.zip"
    module.create_archive(source, archive)
    installer = tmp_path / "K2-Setup-1.0.0.exe"
    installer.write_bytes(b"sample installer")

    metadata_root = tmp_path / "repo"
    (metadata_root / "docs").mkdir(parents=True)
    (metadata_root / "preview").mkdir()
    shutil.copyfile(README, metadata_root / "README.md")
    shutil.copyfile(
        ROOT / "docs" / "RELEASE_AND_WINDOWS_PACKAGING.md",
        metadata_root / "docs" / "RELEASE_AND_WINDOWS_PACKAGING.md",
    )
    shutil.copyfile(ROOT / "preview" / "K2-preview.html", metadata_root / "preview" / "K2-preview.html")

    original_root = module.ROOT
    module.ROOT = metadata_root
    try:
        import hashlib

        module.update_release_metadata(
            source / "K2.exe", archive, source_revision="0" * 40, installer_path=installer
        )
        readme = (metadata_root / "README.md").read_text(encoding="utf-8")
        doc = (metadata_root / "docs" / "RELEASE_AND_WINDOWS_PACKAGING.md").read_text(encoding="utf-8")
        installer_hash = hashlib.sha256(b"sample installer").hexdigest()

        assert f"SHA-256 نصب‌کننده: `{installer_hash}`" in readme, (
            "هش نصب‌کننده در README ثبت نمی‌شود"
        )
        assert f"{installer_hash}  K2-Setup-1.0.0.exe" in doc, (
            "هش نصب‌کننده در سند انتشار ثبت نمی‌شود"
        )
    finally:
        module.ROOT = original_root


def test_readme_leads_with_the_standard_installer():
    text = README.read_text(encoding="utf-8")
    installer_position = text.find("downloads/K2-Setup-1.0.0.exe")
    zip_position = text.find("downloads/K2-windows-x64.zip")
    assert installer_position != -1, "README به نصب‌کنندهٔ استاندارد لینک نمی‌دهد"
    assert installer_position < zip_position, "نصب‌کنندهٔ استاندارد باید روش اصلی دانلود باشد"
    assert "Program Files" in text, "README نمی‌گوید نصب در Program Files انجام می‌شود"


def test_build_script_treats_the_installer_as_required():
    text = (ROOT / "packaging" / "build_windows.ps1").read_text(encoding="utf-8")
    assert "iscc" in text, "اسکریپت ساخت محلی نصب‌کننده نمی‌سازد"
    assert "k2_installer.iss" in text
    # گام باید اجباری باشد (throw در صورت شکست)، نه اختیاری.
    build_step = text[text.index("ساخت نصب‌کنندهٔ استاندارد") :]
    assert "throw" in build_step, "شکست ساخت نصب‌کننده باید build را ناموفق کند"


# --------------------------------------------------------------------------
# اعتبارسنجی خودکار اسکریپت نصب‌کننده
# --------------------------------------------------------------------------

# فلگ‌های معتبر بخش [Tasks] در Inno Setup 6. «checked» در این لیست نیست:
# تسک به‌صورت پیش‌فرض انتخاب شده است و فقط unchecked می‌تواند آن را خاموش کند.
_TASK_FLAGS = {
    "checkedonce",
    "dontinheritcheck",
    "exclusive",
    "restart",
    "unchecked",
}


def _iss_raw_lines(text: str) -> dict[str, list[str]]:
    """خطوط هر بخش از فایل ‎.iss‎ را برمی‌گرداند (بدون تجزیهٔ کلید/مقدار)."""
    sections: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped[1:-1].lower()
            sections.setdefault(current, [])
        elif current and stripped and not stripped.startswith(";"):
            sections[current].append(stripped)
    return sections


def test_every_task_flag_is_a_real_innosetup_flag():
    """فلگ نامعتبر در [Tasks] کامپایل را می‌شکند.

    ``Flags: checked`` معتبر نیست و خطای «Parameter "Flags" includes an
    unknown flag» می‌دهد. چون CI تنها جایی است که ‎.iss‎ واقعاً کامپایل
    می‌شود، این تست جلوی شکست دوبارهٔ CI را می‌گیرد.
    """
    sections = _iss_raw_lines(ISS.read_text(encoding="utf-8"))
    tasks = sections.get("tasks", [])
    assert tasks, "بخش [Tasks] در اسکریپت نصب‌کننده نیست"

    for line in tasks:
        if "Flags:" not in line:
            continue
        flags = line.split("Flags:")[1].split(";")[0].split()
        unknown = [flag for flag in flags if flag.lower() not in _TASK_FLAGS]
        assert not unknown, f"فلگ نامعتبر در [Tasks]: {unknown} — {line}"


def test_the_app_shortcut_sets_a_working_directory():
    """Inno به‌صورت پیش‌فرض «Start In» میان‌بر را نمی‌گذارد.

    مستندات Inno Setup: بدون WorkingDir، ویندوز خودش پوشه‌ای را حدس می‌زند
    که معمولاً پوشهٔ برنامه نیست.
    """
    sections = _iss_raw_lines(ISS.read_text(encoding="utf-8"))
    icons = sections.get("icons", [])
    assert icons, "بخش [Icons] در اسکریپت نصب‌کننده نیست"

    # اسکریپت از {#MyAppExeName} استفاده می‌کند، نه رشتهٔ ثابت K2.exe.
    app_shortcut = next(
        (
            line
            for line in icons
            if "{#MyAppExeName}" in line and "uninstallexe" not in line
        ),
        None,
    )
    assert app_shortcut is not None, "میان‌بر برنامه در [Icons] نیست"
    assert "WorkingDir:" in app_shortcut, (
        f"میان‌بر برنامه WorkingDir ندارد؛ ویندوز پوشهٔ کار را حدس می‌زند: {app_shortcut}"
    )


def test_start_menu_shortcuts_are_not_gated_by_a_task():
    """میان‌برهای Start Menu نباید مشروط به تسک باشند.

    اگر Tasks داشته باشند، در نصب خاموش ساخته نمی‌شوند مگر با /MERGETASKS.
    """
    sections = _iss_raw_lines(ISS.read_text(encoding="utf-8"))
    icons = sections.get("icons", [])

    start_menu = [line for line in icons if "{group}" in line]
    assert start_menu, "هیچ میان‌بر Start Menu در [Icons] نیست"
    for line in start_menu:
        assert "Tasks:" not in line, (
            f"میان‌بر Start Menu مشروط به تسک است و در نصب خاموش ساخته نمی‌شود: {line}"
        )


def test_the_ci_selects_the_desktop_task_when_installing_silently():
    """نصب خاموش باید تسک میزکار را صریحاً انتخاب کند."""
    import yaml

    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = data["jobs"]["test-and-build"]["steps"]
    install = next(
        (s for s in steps if s.get("name", "").startswith("Install the built installer")),
        None,
    )
    assert install is not None, "گام نصب خاموش نصب‌کننده نیست"
    assert "/MERGETASKS=desktopicon" in install["run"], (
        "نصب خاموش باید تسک desktopicon را با /MERGETASKS انتخاب کند"
    )


# ---------------------------------------------------------------------------
# پایش «کد مرده» در اسکریپت نصب‌کننده
#
# اسکریپت نصب‌کننده روی این ماشین (لینوکس) کامپایل نمی‌شود؛ فقط در CI و با
# iscc واقعی ساخته می‌شود. پس هر چیزی که در آن نوشته شود و کار نکند، تا
# اجرای CI پیدایش نمی‌شود. یک بلوک [Code] قبلاً CheckForMutexes روی GUID
# بود، در حالی که هیچ‌کس آن mutex را نمی‌ساخت — همیشه False و بی‌اثر.
# ---------------------------------------------------------------------------


def test_installer_code_has_no_mutex_check_on_a_name_nobody_creates():
    """هیچ ``CheckForMutexes`` نباید نامی را بسوزاند که کسی نسازد.

    «برنامهٔ در حال اجرا» را Inno به‌صورت بومی با ``AppMutex`` و
    ``CloseApplications=yes`` می‌گیرد (فایل قفل‌شدهٔ K2.exe). یک بررسی دستی
    روی نامی که هیچ فرایندی نمی‌سازد، شرطی است که همیشه False است و فقط
    ادعای کاری می‌کند که انجام نمی‌شود.
    """
    script = (ROOT / "packaging" / "k2_installer.iss").read_text(encoding="utf-8")
    # فقط دستورهای واقعی را بسنج، نه کامنت‌ها؛ کامنت می‌تواند نام را برای
    # توضیح بیاورد.
    directives = "\n".join(
        line for line in script.splitlines() if not line.strip().startswith(";")
    )

    assert "CheckForMutexes" not in directives, (
        "اسکریپت نصب‌کننده mutex دستی می‌سنجد؛ Inno این کار را خودش با "
        "AppMutex و CloseApplications می‌کند"
    )
    # ولی رفتار درست نباید حذف شده باشد.
    assert "AppMutex=" in script, "AppMutex حذف شده؛ برنامهٔ در حال اجرا تشخیص داده نمی‌شود"
    assert "CloseApplications=yes" in script, "CloseApplications حذف شده"


def test_installer_has_no_empty_section():
    """هیچ بخشی در اسکریپت نباید خالی یا فقط کامنت باشد.

    یک بخش خالی در Inno خطا نمی‌دهد ولی نشانهٔ کار نیمه‌تمام است.
    """
    sections = _iss_sections(ISS.read_text(encoding="utf-8"))
    empty = []
    for name, entries in sections.items():
        if name in {"Setup", "Languages", "Messages", "Code"}:
            continue
        if not entries:
            empty.append(name)
    assert not empty, f"این بخش‌ها خالی هستند: {empty}"


def test_uninstall_delete_only_removes_the_install_folder():
    """``[UninstallDelete]`` نباید پوشهٔ دادهٔ کاربر را هدف بگیرد.

    کاربر دادهٔ واقعی‌اش (پایهگاه داده) را در پوشهٔ دادهٔ سیستم دارد، نه در
    پوشهٔ برنامه. حذف نصب باید فقط فایل‌های نصب‌شده را پاک کند.
    """
    script = (ROOT / "packaging" / "k2_installer.iss").read_text(encoding="utf-8")
    section = script.split("[UninstallDelete]")[1]
    assert "{app}" in section, "حذف نصب پوشهٔ برنامه را هدف نگرفته"
    for forbidden in ("{localappdata}", "{userappdata}", "K2_DATA_DIR", "k2.db"):
        assert forbidden not in section, (
            f"حذف نصب دادهٔ کاربر را هدف گرفته: {forbidden}"
        )
