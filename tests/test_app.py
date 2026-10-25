from __future__ import annotations

import ctypes
import re
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

from k2 import app


def _plan():
    return SimpleNamespace(
        capacity_minutes=240,
        planned_minutes=180,
        placements=[object(), object()],
        notes=["یادداشت سلامت"],
    )


def test_headless_report_is_safe_without_console(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(app.sys, "stdout", None)

    app._print_headless_report(tmp_path / "k2.db", _plan())


def test_headless_report_remains_readable_when_console_exists(monkeypatch, tmp_path: Path):
    output = StringIO()
    monkeypatch.setattr(app.sys, "stdout", output)

    app._print_headless_report(tmp_path / "k2.db", _plan())

    text = output.getvalue()
    assert "پایگاه داده:" in text
    assert "ظرفیت امروز: 240 دقیقه" in text
    assert "برنامهٔ امروز: 180 دقیقه در 2 بلوک" in text
    assert "یادداشت سلامت" in text


# ---------------------------------------------------------------------------
# قفل نسخهٔ یگانه (single instance)
#
# نصب‌کنندهٔ استاندارد با ``AppMutex`` در packaging/k2_installer.iss می‌پرسد
# «برنامه باز است؟». آن mutex را باید خود برنامه بسازد؛ وگرنه اعلام نصب‌کننده
# بی‌اثر می‌ماند و نصب روی فایل قفل‌شدهٔ K2.exe می‌شکند.
# ---------------------------------------------------------------------------


class _CreateMutexW:
    """فراخوان‌پذیر که اجازهٔ تنظیم argtypes/restype را هم می‌دهد."""

    def __init__(self, owner: "_FakeKernel32"):
        self.owner = owner
        self.argtypes = None
        self.restype = None

    def __call__(self, attributes, initial_owner, name):
        return self.owner._create(attributes, initial_owner, name)


class _FakeKernel32:
    """جای‌گزین ``ctypes.WinDLL`` برای سنجش مسیر ویندوز روی لینوکس."""

    def __init__(self, already_exists: bool, raises: bool = False):
        self.already_exists = already_exists
        self.raises = raises
        self.calls: list[tuple] = []
        self.CreateMutexW = _CreateMutexW(self)

    def _create(self, attributes, initial_owner, name):
        self.calls.append((attributes, initial_owner, name))
        if self.raises:
            raise OSError("CreateMutexW failed")
        return 0x1234


def _patch_windows(monkeypatch, already_exists: bool, raises: bool = False) -> _FakeKernel32:
    """مسیر ویندوز را روی لینوکس شبیه‌سازی می‌کند.

    ``ctypes`` داخل تابع وارد می‌شود، پس ماژول واقعی را پینه می‌کنیم؛
    monkeypatch آن را پس از تست برمی‌گرداند. ``WinDLL`` و ``get_last_error``
    روی لینوکس وجود ندارند، پس ``raising=False`` لازم است.
    """
    fake = _FakeKernel32(already_exists, raises)
    monkeypatch.setattr(app.sys, "platform", "win32")
    monkeypatch.setattr(app, "_MUTEX_HANDLE", None, raising=False)
    monkeypatch.setattr(ctypes, "WinDLL", lambda *a, **k: fake, raising=False)
    monkeypatch.setattr(
        ctypes, "get_last_error", lambda: 183 if already_exists else 0, raising=False
    )
    return fake


def test_mutex_name_matches_the_installer_appmutex():
    """نام mutex برنامه باید با ``AppMutex`` نصب‌کننده یکی باشد.

    اگر یکی شوند و کسی یکی را عوض کند، نصب‌کننده دیگر برنامهٔ در حال اجرا را
    نمی‌بیند. این همان اشتبالی است که قبلاً رخ داده بود (``AppMutex`` بود
    ولی برنامه چیزی نمی‌ساخت).
    """
    iss = (Path(__file__).resolve().parents[1] / "packaging" / "k2_installer.iss").read_text(
        encoding="utf-8"
    )
    declared = re.search(r"AppMutex=([^\r\n]+)", iss).group(1).split(",")[0].strip()
    assert app.SINGLE_INSTANCE_MUTEX == declared, (
        f"برنامه '{app.SINGLE_INSTANCE_MUTEX}' می‌سازد ولی نصب‌کننده '{declared}' را می‌بیند"
    )


def test_mutex_is_created_on_windows(monkeypatch):
    fake = _patch_windows(monkeypatch, already_exists=False)

    assert app._acquire_single_instance_mutex() is True
    assert fake.calls == [(None, False, app.SINGLE_INSTANCE_MUTEX)]
    # handle باید نگه داشته شود تا mutex تا پایان عمر فرایند آزاد نشود.
    assert app._MUTEX_HANDLE == 0x1234


def test_second_instance_is_detected(monkeypatch):
    _patch_windows(monkeypatch, already_exists=True)

    assert app._acquire_single_instance_mutex() is False


def test_mutex_failure_never_blocks_the_app(monkeypatch):
    """شکست ساخت mutex نباید کاربر را از برنامه محروم کند."""
    _patch_windows(monkeypatch, already_exists=False, raises=True)

    assert app._acquire_single_instance_mutex() is True


def test_mutex_handle_is_not_created_off_windows(monkeypatch):
    monkeypatch.setattr(app.sys, "platform", "linux")
    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("WinDLL نباید روی غیر ویندوز صدا زده شود")
        ),
        raising=False,
    )

    assert app._acquire_single_instance_mutex() is True
