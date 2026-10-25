"""سه تحقق باقی‌ماندهٔ انتشار ویندوز باید در CI واقعاً اجرا شوند.

کارponder صریحاً گفت همهٔ این موارد باید تکمیل باشند:

1. نصب‌کننده روی ویندوز **واقعاً** نصب، اجرا و حذف شود.
2. امضای دیجیتال به‌صورت یک خط لولهٔ کارا موجود باشد.
3. آیکنِ برنامه **واقعاً** داخل EXE نشسته باشد.

این تست‌ها همان قول را می‌بندند: گردش‌کار باید این گام‌ها را داشته باشد و
اگر پیکربندی نشده باشند، build باید شکست بخورد نه اینکه بی‌صدا رد شود.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "build-windows.yml"


def _workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _steps() -> list[str]:
    """نام همهٔ گام‌های گردش‌کار به ترتیب."""
    import yaml

    data = yaml.safe_load(_workflow())
    return [step.get("name", "") for step in data["jobs"]["test-and-build"]["steps"]]


# --------------------------------------------------------------------------
# ۱) نصب واقعی روی ویندوز
# --------------------------------------------------------------------------


def test_every_workflow_yaml_file_is_valid():
    """گردش‌کار خراب باید در تست شکست بخورد، نه در اجرای CI."""
    import yaml

    workflows = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    assert workflows, "هیچ گردش‌کاری پیدا نشد"
    for workflow in workflows:
        data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
        assert isinstance(data, dict), f"{workflow.name}: ساختار گردش‌کار درست نیست"
        assert "jobs" in data, f"{workflow.name}: بخش jobs نیست"


def test_every_windows_build_step_has_a_name_and_a_body():
    """گام بی‌نام یا بی‌بدن در UI Actions خوانا نیست."""
    import yaml

    data = yaml.safe_load(_workflow())
    steps = data["jobs"]["test-and-build"]["steps"]
    assert len(steps) >= 15, "گردش‌کار build-windows گام کافی ندارد"
    for step in steps:
        assert step.get("name"), f"گام بی‌نام: {step}"
        assert step.get("run") or step.get("uses"), f"گام بی‌بدن: {step.get('name')}"


def test_ci_installs_the_installer_on_a_real_windows_machine():
    steps = _steps()
    assert any("Install the built installer on Windows" in name for name in steps), (
        "گردش‌کار نصب‌کننده را روی ویندوز نصب نمی‌کند؛ فقط فایل را می‌سازد."
    )


def test_ci_verifies_the_install_registered_in_add_remove_programs():
    text = _workflow()
    for needle in (
        "CurrentVersion\\Uninstall\\$env:K2_APP_ID",
        "DisplayName",
        "UninstallString",
        "DisplayIcon",
    ):
        assert needle in text, f"بررسی رجیستری نصب ناقص است: {needle}"


def test_ci_verifies_the_shortcuts_are_created():
    """میان‌برها باید هم در Start-Menu و هم روی میزکار سنجیده شوند.

    نصب ممکن است ارتقا‌یافته یا غیرارتقا‌یافته اجرا شود، پس هر دو مسیر
    مشترک و هر دو مسیر خاص کاربر باید جست‌وجو شود — نه فقط
    ``ProgramData``.
    """
    text = _workflow()
    assert "CommonStartMenu" in text, "Start-Menu مشترک بررسی نمی‌شود"
    assert '"StartMenu"' in text, "Start-Menu کاربر بررسی نمی‌شود"
    assert "CommonDesktopDirectory" in text, "میزکار مشترک بررسی نمی‌شود"
    assert '"Desktop"' in text, "میزکار کاربر بررسی نمی‌شود"
    assert "Find-LinkToInstallDir" in text, "جست‌وجوی میان‌بر یک تابع مشترک نیست"
    assert "Test-LinkPointsAtInstallDir" in text, (
        "میان‌بر با محتوای فایل .lnk سنجیده نمی‌شود"
    )


def test_ci_runs_the_installed_executable_and_checks_the_database():
    text = _workflow()
    assert "--headless" in text, "برنامهٔ نصب‌شده اجرا نمی‌شود"
    assert "K2_DATA_DIR" in text, (
        "اجرای برنامهٔ نصب‌شده باید مسیر دادهٔ کاربر را جدا نگه دارد تا حفظ داده آزمون شود"
    )


def test_ci_verifies_a_second_install_is_an_upgrade_not_a_duplicate():
    text = _workflow()
    assert "نصب دوم" in text, "بررسی نصب دوم (ارتقا در برابر نصب تکراری) نیست"


def test_ci_uninstalls_and_verifies_the_user_data_survives():
    steps = _steps()
    assert any("Uninstall and verify the user's data survives" in name for name in steps), (
        "گردش‌کار نصب‌کننده را حذف نمی‌کند و حفظ دادهٔ کاربر را نمی‌آزماید."
    )
    text = _workflow()
    assert "پوشهٔ برنامه بعد از حذف نصب پاک نشد" in text
    assert "حذف نصب، پایگاه دادهٔ کاربر را هم پاک کرد" in text


def test_installer_script_only_deletes_the_app_folder_not_user_data():
    """حذف نصب باید فقط ``{app}`` را پاک کند."""
    iss = (ROOT / "packaging" / "k2_installer.iss").read_text(encoding="utf-8")
    uninstall_delete = iss[iss.index("[UninstallDelete]") :]
    uninstall_delete = uninstall_delete[: uninstall_delete.index("[Code]")]
    assert "{app}" in uninstall_delete, "[UninstallDelete] باید {app} را پاک کند"
    for forbidden in ("{userappdata}", "{localappdata}", "{commonappdata}", "{userdocs}"):
        assert forbidden not in uninstall_delete.lower(), (
            f"حذف نصب نباید {forbidden} را پاک کند"
        )


# --------------------------------------------------------------------------
# ۲) امضای دیجیتال
# --------------------------------------------------------------------------


def test_ci_has_a_signing_pipeline_that_is_actually_exercised():
    steps = _steps()
    assert any("Signing pipeline self-test" in name for name in steps), (
        "خط لولهٔ امضا هیچ‌وقت اجرا نمی‌شود؛ پس وقتی گواهی آمد، شکست می‌خورد."
    )


def _signing_selftest_step() -> str:
    text = _workflow()
    step = text[text.index("Signing pipeline self-test") :]
    return step[: step.index("\n      - name:")]


def _signing_selftest_script() -> str:
    script = ROOT / "packaging" / "signing_selftest.ps1"
    assert script.is_file(), "اسکریپت خودآزمایی امضا حذف شده است"
    return script.read_text(encoding="utf-8")


def test_signing_self_test_proves_sign_and_verify_both_work():
    script = _signing_selftest_script()
    assert "New-SelfSignedCertificate" in script, (
        "گواهی موقت برای آزمون خط لوله ساخته نمی‌شود"
    )
    assert "signtool sign" in script, "خط لوله امضا وجود ندارد"
    assert "signtool verify /pa" in script, "راستی‌آزمایی امضا وجود ندارد"
    assert "Get-AuthenticodeSignature" in script, "وضعیت امضا بررسی نمی‌شود"


def test_signing_self_test_runs_as_a_bounded_child_process():
    """New-SelfSignedCertificate روی runner آویزان می‌ماند و kill-pذیر نیست.

    پس باید در فرprocess جدا و با مهلت زمانی اجرا شود؛ وگرنه کل job را
    برای ۷۵ دقیقه می‌گیرد و هیچ گام بعدی اجرا نمی‌شود.
    """
    step = _signing_selftest_step()
    assert "signing_selftest.ps1" in step, "خودآزمایی باید اسکریپت جدا باشد"
    assert "Start-Process" in step, "خودآزمایی باید در فرprocess جدا اجرا شود"
    assert "AddSeconds(300)" in step, "برای خودآزمایی مهلت زمانی تعیین نشده"
    assert "HasExited" in step, "مهلت زمانی کنترل نمی‌شود"
    assert "$process.Kill()" in step, "فرprocess آویزان Kill نمی‌شود"
    assert "::warning::" in step, (
        "اگر خودآزمایی آویزان شد، باید هشدار بدهد و رد شود — نه اینکه job را بگیرد"
    )
    assert "exit 0" in step, "رد شدن خودآزمایی نباید build را قرمز کند"


def test_signing_self_test_never_publishes_the_self_signed_artifact():
    """گواهی خودامضا نباید به فایل منتشرشده برسد."""
    script = _signing_selftest_script()
    assert "Copy-Item" in script, "آزمون باید روی یک کپی کار کند"
    assert "$env:RUNNER_TEMP" in script, "کپی باید بیرون از خروجی انتشار باشد"
    assert "Remove-Item" in script, "کپی و گواهی موقت باید پاک شوند"
    assert "Cert:\\CurrentUser\\My" in script, "گواهی موقت در انبار کاربر است"
    assert "finally" in script, "پاک‌سازی حتی در صورت خطا هم باید اجرا شود"


def test_release_signing_fails_loudly_when_it_is_requested_but_not_configured():
    text = _workflow()
    assert "WINDOWS_SIGNING_ENABLED" in text, "کلید فعال‌سازی امضا نیست"
    assert "WINDOWS_CERTIFICATE_PFX_BASE64" in text, "سکرت گواهی نیست"
    assert "ولی گواهی داده نشده" in text, (
        "اگر امضا درخواست شود و گواهی نباشد، build باید شکست بخورد نه اینکه رد شود"
    )


def test_unsigned_release_is_reported_not_silently_skipped():
    text = _workflow()
    assert "::notice::امضای دیجیتال پیکربندی نشده است" in text, (
        "عدم امضا باید در لاگ CI اعلام شود"
    )


def test_the_installer_itself_is_signed_when_a_certificate_exists():
    steps = _steps()
    assert any(name.startswith("Sign the installer") for name in steps), (
        "نصب‌کننده امضا نمی‌شود؛ کاربر باز هم هشدار SmartScreen می‌گیرد."
    )
    text = _workflow()
    assert "K2-Setup-*.exe" in text


def test_the_icon_is_verified_inside_the_built_exe():
    steps = _steps()
    assert any("icon is embedded in the EXE" in name for name in steps), (
        "گردش‌کار آیکنِ داخل EXE را بررسی نمی‌کند."
    )
    text = _workflow()
    assert "verify_exe_icon.py" in text
    assert "src\\k2\\ui\\assets\\k2.ico" in text


# --------------------------------------------------------------------------
# ۳) آیکن
# --------------------------------------------------------------------------


def test_icon_verifier_script_exists_and_is_runnable():
    script = ROOT / "packaging" / "verify_exe_icon.py"
    assert script.is_file(), "اسکریپت بررسی آیکن وجود ندارد"
    text = script.read_text(encoding="utf-8")
    # باید پارسر واقعی PE باشد، نه جستجوی سادهٔ بایت‌ها.
    for needle in ("RT_ICON", "RT_GROUP_ICON", "IMAGE_RESOURCE_DATA_ENTRY", "rva_to_offset"):
        assert needle in text, f"پارسر PE ناقص است: {needle}"


def test_icon_verifier_fails_when_the_exe_has_no_icon(tmp_path: Path):
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "v_icon", ROOT / "packaging" / "verify_exe_icon.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    exe = tmp_path / "K2.exe"
    exe.write_bytes(b"MZ" + b"\x00" * 200)
    with pytest_raises_icon_error(module):
        module.verify(exe, ROOT / "src" / "k2" / "ui" / "assets" / "k2.ico")


def pytest_raises_icon_error(module):
    import pytest

    return pytest.raises(module.IconVerificationError)


def test_icon_file_exists_and_pyinstaller_spec_points_at_it():
    icon = ROOT / "src" / "k2" / "ui" / "assets" / "k2.ico"
    assert icon.is_file(), "فایل k2.ico وجود ندارد"
    assert "k2.ico" in (ROOT / "k2.spec").read_text(encoding="utf-8")


def test_build_script_builds_and_verifies_the_installer_too():
    """ساخت محلی هم باید نصب‌کننده و آیکن را پوشش دهد."""
    ps1 = (ROOT / "packaging" / "build_windows.ps1").read_text(encoding="utf-8")
    assert "iscc" in ps1, "ساخت محلی نصب‌کننده نمی‌سازد"
    assert "verify_exe_icon.py" in ps1, "ساخت محلی آیکن داخل EXE را بررسی نمی‌کند"


def test_the_app_id_used_by_ci_matches_the_installer_script():
    """گام نصب/حذف با ``$env:K2_APP_ID`` ورودی رجیستری را پیدا می‌کند.

    اگر این متغیر خالی باشد، مسیر رجیستری به ``...\\Uninstall\\_is1`` تبدیل
    می‌شود و گام با «نصب در رجیستری ثبت نشد» شکست می‌خورد — بی‌آنکه ایرادی
    به خودِ نصب‌کننده باشد.
    """
    import yaml

    data = yaml.safe_load(_workflow())
    env = data["jobs"]["test-and-build"]["env"]
    app_id = env.get("K2_APP_ID", "")
    assert app_id, "K2_APP_ID در محیط job تنظیم نشده است"
    assert app_id.startswith("{") and app_id.endswith("}"), app_id

    script = (ROOT / "packaging" / "k2_installer.iss").read_text(encoding="utf-8")
    assert app_id in script, (
        "K2_APP_ID گردش‌کار با AppId داخل k2_installer.iss یکی نیست"
    )


def test_the_install_step_captures_the_installer_log():
    """اگر نصب شکست خورد، علت باید خوانا باشد."""
    step = _workflow()
    step = step[step.index("Install the built installer on Windows") :]
    step = step[: step.index("\n      - name:")]
    assert "/LOG=" in step, "نصب‌کننده بدون لاگ اجرا می‌شود؛ شکست قابل تشخیص نیست"
    assert "::error::" in step, "لاگ نصب‌کننده در صورت شکست گزارش نمی‌شود"
    assert "::notice::" in step, "گام نصب نشانهٔ پیشرفت ندارد"


def test_shortcuts_are_found_by_target_not_by_name():
    """نام میان‌برها فارسی است، پس جست‌وجو با ``*K2*`` هیچ چیزی پیدا نمی‌کند.

    ``packaging/k2_installer.iss`` میان‌برها را ``{#MyAppName}`` می‌نامد که
    «مشاور هوشمند کنکور» است. پس گام نصب باید هدف (``TargetPath``) میان‌بر
    را بخواند و ببیند به ``K2.exe`` داخل پوشهٔ نصب اشاره می‌کند — نه اینکه
    نام فایل را با الگوی انگلیسی تطبیق دهد.
    """
    step = _workflow()
    step = step[step.index("Install the built installer on Windows") :]
    step = step[: step.index("\n      - name:")]

    assert "WScript.Shell" in step, "هدف میان‌بر خوانده نمی‌شود"
    assert "TargetPath" in step, "میان‌بر با هدفش سنجیده نمی‌شود"
    # هیچ خطی که میان‌بر ‎.lnk‎ را می‌شمارد نباید با نام انگلیسی تطبیق دهد.
    shortcut_lines = [ln for ln in step.splitlines() if ".lnk" in ln]
    assert shortcut_lines, "بخش میان‌بر پیدا نشد"
    for line in shortcut_lines:
        assert "-like" not in line or "*K2*" not in line, (
            f"جست‌وجوی میان‌بر با نام انگلیسی است و نام فارسی را پیدا نمی‌کند: {line}"
        )

    script = (ROOT / "packaging" / "k2_installer.iss").read_text(encoding="utf-8")
    assert "K2" not in script.split("[Icons]")[1].split("[Run]")[0], (
        "بخش [Icons] نباید به نام انگلیسی متکی باشد؛ نام میان‌برها فارسی است"
    )


# ---------------------------------------------------------------------------
# پایش ساختاری اسکریپت‌های PowerShell
#
# این گام روی ویندوز اجرا می‌شود و PowerShell روی این ماشین نیست، پس اشتبال
# نگارشیِ اسکریپت فقط در CI و فقط با «Process completed with exit code 1.»
# پیدا می‌شود — بدون هیچ خروجی. دو اشتبال واقعیِ همین جنس قبلاً یک اجرای کامل
# را آتش زد: یک آکولاد بستهٔ اضافه (کل اسکریپت در زمان parse می‌شکست و هیچ
# چیز اجرا نمی‌شد) و یک بک‌تیک گم‌شده در ``-ArgumentList`` که سوییچ
# ``/MERGETASKS`` را به یک رشتهٔ بی‌اثر تبدیل می‌کرد.
# ---------------------------------------------------------------------------


def _pwsh_run_blocks() -> list[tuple[str, str, int]]:
    """همهٔ بلوک‌های ``run: |`` را با نام گامشان از گردش‌کار بیرون می‌کشد."""
    text = (ROOT / ".github" / "workflows" / "build-windows.yml").read_text(encoding="utf-8")
    lines = text.splitlines()
    blocks: list[tuple[str, str, int]] = []
    index = 0
    run_start = re.compile(r"^(\s*)run: \|\s*$")
    while index < len(lines):
        match = run_start.match(lines[index])
        if not match:
            index += 1
            continue
        indent = len(match.group(1))
        cursor = index + 1
        body: list[str] = []
        while cursor < len(lines):
            line = lines[cursor]
            if line.strip() == "":
                body.append(line)
                cursor += 1
                continue
            if len(line) - len(line.lstrip()) <= indent:
                break
            body.append(line)
            cursor += 1
        name = ""
        for back in range(index, max(0, index - 12), -1):
            name_match = re.match(r"^\s*- name: (.*)$", lines[back])
            if name_match:
                name = name_match.group(1)
                break
        blocks.append((name, "\n".join(body), index + 1))
        index = cursor
    return blocks


def test_every_powershell_run_block_has_balanced_braces():
    """آکولاد باز و بستهٔ هر اسکریپت PowerShell باید برابر باشند.

    یک آکولاد اضافه باعث می‌شود کل بلوک در زمان parse شکست بخورد؛ چون اجرا
    هرگز شروع نمی‌شود، هیچ ``::notice::``‌ای هم چاپ نمی‌شود و تنها نشانهٔ
    خرابی یک «exit code 1» بی‌توضیح است.
    """
    blocks = _pwsh_run_blocks()
    assert len(blocks) >= 10, f"فقط {len(blocks)} بلوک run پیدا شد"
    unbalanced = []
    for name, body, line_number in blocks:
        # `` ` `` یک گریز است؛ `` `{ `` و `` `} `` آکولاد واقعی نیستند.
        cleaned = re.sub(r"`.", "", body)
        opened, closed = cleaned.count("{"), cleaned.count("}")
        if opened != closed:
            unbalanced.append(f"line {line_number} [{name}]: open={opened} close={closed}")
    assert not unbalanced, "آکولاد نامتوازن در اسکریپت PowerShell:\n" + "\n".join(unbalanced)


def test_no_argument_list_element_is_left_orphaned():
    """هیچ سوییچی از لیست آرگومان‌ها جا نماند.

    در ``-ArgumentList`` هر خط جز آخر باید با `` , `` یا `` ` `` ادامه پیدا
    کند. اگر بک‌تیک آخرین آرگومان گم شود، سوییچ بعدی یک دستور جدا می‌شود و
    هرگز به فرایند نمی‌رسد — بدون هیچ خطایی.
    """
    orphaned = []
    for name, body, line_number in _pwsh_run_blocks():
        lines = body.splitlines()
        for position, line in enumerate(lines):
            stripped = line.strip()
            # آرگومانی که با «/» شروع می‌شود (سوییچ نصب‌کننده/برنامه).
            if not re.match(r'^"/[A-Za-z\-]', stripped):
                continue
            previous = position - 1
            while previous >= 0 and not lines[previous].strip():
                previous -= 1
            if previous < 0:
                continue
            tail = lines[previous].rstrip()
            if tail.endswith("`") or tail.endswith(",") or tail.endswith("(") or tail.endswith("|"):
                continue
            orphaned.append(f"line {line_number + position} [{name}]: {stripped[:50]}")
    assert not orphaned, (
        "این سوییچ‌ها از لیست آرگومان جدا شده‌اند و به فرایند نمی‌رسند:\n"
        + "\n".join(orphaned)
    )


def test_install_step_actually_merges_the_desktop_icon_task():
    """``/MERGETASKS=desktopicon`` باید داخل همان ``-ArgumentList`` باشد.

    میان‌بر میزکار در ``k2_installer.iss`` به تسک ``desktopicon`` بسته شده.
    نصب خاموش بدون انتخاب صریح آن تسک، میان‌بر را نمی‌سازد و گام «میان‌بر
    میزکار ساخته نشد» قرمز می‌شود — علتش هم دقیقاً همین است.
    """
    blocks = {name: body for name, body, _ in _pwsh_run_blocks()}
    install = next(
        body
        for name, body in blocks.items()
        if name.startswith("Install the built installer")
    )
    start = install.index("function Install-Setup")
    end = install.index("return $p.ExitCode", start)
    function_body = install[start:end]

    assert "/MERGETASKS=desktopicon" in function_body, (
        "تابع Install-Setup تسک desktopicon را انتخاب نمی‌کند"
    )
    # باید روی خطی باشد که ادامهٔ لیست آرگومان است، نه دستور جدا.
    argument_lines = [
        line.strip()
        for line in function_body.splitlines()
        if line.strip().startswith('"/') or line.strip().startswith('-ArgumentList')
    ]
    assert any(line.startswith("-ArgumentList") for line in argument_lines), (
        "لیست آرگومان پیدا نشد"
    )
    merged = [line for line in argument_lines if "MERGETASKS" in line]
    assert merged, "/MERGETASKS در لیست آرگومان نیست"
    # خطی که MERGETASKS رویش است باید پیش از آن، خطی با `` ` `` یا ``,`` داشته باشد.
    flat = function_body.splitlines()
    for position, line in enumerate(flat):
        if "MERGETASKS" not in line:
            continue
        tail = flat[position - 1].rstrip()
        assert tail.endswith("`") or tail.endswith(","), (
            f"MERGETASKS به لیست آرگومان وصل نیست: {line.strip()}"
        )


def test_install_step_defines_each_variable_before_reading_it():
    """هر متغیر باید پیش از خواندنش تعریف شده باشد.

    یک بلوک تشخیصی، ``$startMenuDirs`` را پیش از تعریفش می‌خوانید. چون
    PowerShell بدنهٔ ``foreach`` را دیر ارزیابی می‌کند، آن بلوک همیشه خالی
    بود و فقط «۰ میان‌بر» گزارش می‌داد — گمراه‌کننده، نه مفید. تعریف‌شدنِ
    زودهنگام را به‌عنوان یک قاعده نگه می‌داریم.
    """
    blocks = {name: body for name, body, _ in _pwsh_run_blocks()}
    install = next(
        body
        for name, body in blocks.items()
        if name.startswith("Install the built installer")
    )
    lines = install.splitlines()
    for variable in ("$startMenuDirs", "$desktopDirs"):
        references = [
            position
            for position, line in enumerate(lines)
            if variable in line and not line.lstrip().startswith("#")
        ]
        assert references, f"{variable} در گام نصب استفاده نمی‌شود"
        first = lines[references[0]]
        assert re.match(rf"^\s*{re.escape(variable)}\s*=\s*@\(", first), (
            f"{variable} پیش از تعریفش خوانده می‌شود: {first.strip()}"
        )


def test_install_step_reports_the_setup_log_when_install_fails():
    """اگر نصب شکست خورد، لاگ نصب‌کننده باید بیرون بیاید.

    ``/LOG=`` به نصب‌کننده داده می‌شود تا علت شکست خوانا باشد؛ بدون بازخوانی
    آن لاگ، شکست فقط یک کد خروج بی‌معنی می‌ماند.
    """
    blocks = {name: body for name, body, _ in _pwsh_run_blocks()}
    install = next(
        body
        for name, body in blocks.items()
        if name.startswith("Install the built installer")
    )
    assert "/LOG=" in install, "لاگ نصب‌کننده گرفته نمی‌شود"
    assert "::error::" in install, "لاگ در صورت شکست به خطا تبدیل نمی‌شود"
    # هر دو فراخوانی Install-Setup باید لاگ را بخوانند.
    assert install.count("Get-Content $setupLog") >= 2, (
        "لاگ فقط در یکی از حالت‌های شکست خوانده می‌شود"
    )


def test_shortcut_check_does_not_depend_on_a_single_link_encoding():
    """جست‌وجوی میان‌بر نباید به یک رمزگشایی خاص تکیه کند.

    فایل ``.lnk`` می‌تواند مسیر را یونیکد (StringData) یا ANSI (LinkInfo)
    ذخیره کند. اگر تست فقط یکی را بخواند، نتیجه به شکل ذخیره‌سازیِ لینک
    وابسته می‌شود و روی ماشین دیگری بی‌دلیل قرمز می‌شود.
    """
    text = _workflow()
    install_step = text[text.index("Install the built installer on Windows") :]
    install_step = install_step[: install_step.index("\n      - name:")]

    assert "Test-LinkPointsAtInstallDir" in install_step, (
        "بررسی میان‌بر با محتوای فایل .lnk انجام نمی‌شود"
    )
    assert "Encoding]::Unicode" in install_step, "رمزگشایی یونیکد وجود ندارد"
    assert "Encoding]::Latin1" in install_step, "رمزگشایی Latin1 (ANSI) وجود ندارد"
    # OrdinalIgnoreCase لازم است؛ ویندوز مسیرها را بدون حساسیت به حرف مقایسه می‌کند.
    assert "OrdinalIgnoreCase" in install_step, "مقایسهٔ مسیر به حرف کوچک/بزرگ حساس است"


def test_shortcut_check_reports_the_setup_log():
    """لاگ نصب‌کننده باید خوانده و گزارش شود.

    Inno خودش می‌نویسد چه پوشه و میان‌بری ساخته شده. اگر جست‌وجوی فایل‌سیستم
    شکست بخورد، بدون این لاگ علت حدس می‌ماند.
    """
    text = _workflow()
    install_step = text[text.index("Install the built installer on Windows") :]
    install_step = install_step[: install_step.index("\n      - name:")]

    assert "/LOG=" in install_step, "لاگ نصب‌کننده گرفته نمی‌شود"
    assert "Select-String" in install_step, "لاگ نصب‌کننده خوانده نمی‌شود"
    assert "setup log:" in install_step, "لاگ به‌صورت notice گزارش نمی‌شود"


def test_shortcut_failure_reports_candidates_before_throwing():
    """قبل از شکست، میان‌برهای مشکوک و تازه‌ساخته‌شده گزارش شوند.

    یک throw بدون زمینه فقط می‌گوید «ساخته نشد». گزارش نام و هدفِ میان‌برهای
    موجود می‌گوید مشکل از نصب‌کننده است یا از جست‌وجوی ما.
    """
    text = _workflow()
    install_step = text[text.index("Install the built installer on Windows") :]
    install_step = install_step[: install_step.index("\n      - name:")]

    assert "recent shortcut" in install_step, "میان‌برهای تازه‌ساخته‌شده گزارش نمی‌شوند"
    assert "candidate" in install_step, "میان‌برهای نامشخص گزارش نمی‌شوند"
    # هر دو میان‌بر باید بررسی شوند و شکست فقط در پایان اعلام شود، نه با اولین
    # چیزی که پیدا نشد — وگرنه باز هم نصفه مطلب می‌مانیم.
    assert "problems" in install_step, "خطاها جمع نمی‌شوند"
    assert "$problems -join" in install_step, "شکست پیش از بررسی هر دو میان‌بر پرتاب می‌شود"
