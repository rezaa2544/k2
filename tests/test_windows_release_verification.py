"""سه تحقق باقی‌ماندهٔ انتشار ویندوز باید در CI واقعاً اجرا شوند.

کارponder صریحاً گفت همهٔ این موارد باید تکمیل باشند:

1. نصب‌کننده روی ویندوز **واقعاً** نصب، اجرا و حذف شود.
2. امضای دیجیتال به‌صورت یک خط لولهٔ کارا موجود باشد.
3. آیکنِ برنامه **واقعاً** داخل EXE نشسته باشد.

این تست‌ها همان قول را می‌بندند: گردش‌کار باید این گام‌ها را داشته باشد و
اگر پیکربندی نشده باشند، build باید شکست بخورد نه اینکه بی‌صدا رد شود.
"""

from __future__ import annotations

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
    text = _workflow()
    assert "Start Menu" in text, "بررسی میان‌بر فهرست شروع نیست"
    assert "Desktop" in text, "بررسی میان‌بر میزکار نیست"


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


def test_signing_self_test_proves_sign_and_verify_both_work():
    text = _workflow()
    assert "New-SelfSignedCertificate" in text, "گواهی موقت برای آزمون خط لوله ساخته نمی‌شود"
    assert "signtool sign" in text, "خط لوله امضا وجود ندارد"
    assert "signtool verify /pa" in text, "راستی‌آزمایی امضا وجود ندارد"
    assert "Get-AuthenticodeSignature" in text, "وضعیت امضا بررسی نمی‌شود"


def test_signing_self_test_never_publishes_the_self_signed_artifact():
    """گواهی خودامضا نباید به فایل منتشرشده برسد."""
    text = _workflow()
    self_test = text[text.index("Signing pipeline self-test") :]
    self_test = self_test[: self_test.index("\n      - name:")]
    assert "Copy-Item" in self_test, "آزمون باید روی یک کپی کار کند"
    assert "$env:RUNNER_TEMP" in self_test, "کپی باید بیرون از خروجی انتشار باشد"
    assert "Remove-Item" in self_test, "کپی و گواهی موقت باید پاک شوند"


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
