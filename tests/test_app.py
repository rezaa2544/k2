from __future__ import annotations

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
