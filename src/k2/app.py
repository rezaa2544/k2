"""نقطهٔ ورود برنامه."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Sequence

from .config import database_path


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="k2", description="مشاور هوشمند کنکور — نرم‌افزار دسکتاپ فارسی"
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="مسیر فایل پایگاه داده (پیش‌فرض: پوشهٔ دادهٔ کاربر)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="اجرای آفلاین بدون نمایش پنجره (برای بررسی سلامت برنامه)",
    )
    return parser.parse_args(argv)


def _force_utf8_output() -> None:
    """کنسول ویندوز به‌صورت پیش‌فرض cp1252 است و متن فارسی را نمی‌پذیرد.

    بدون این تنظیم، اجرای ``--headless`` روی ویندوز با ``UnicodeEncodeError``
    متوقف می‌شود. اگر خروجی قابل تنظیم نباشد (مثلاً build بدون کنسول)،
    بی‌صدا رد می‌شویم.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):  # pragma: no cover - وابسته به ترمینال
            pass


def main(argv: Optional[Sequence[str]] = None) -> int:
    """اجرای برنامه."""
    _force_utf8_output()
    args = _parse_args(argv)

    db_path = Path(args.db) if args.db else database_path()

    if args.headless:
        # اجرای آفلاین بدون رابط گرافیکی: هسته بررسی و برنامه ساخته می‌شود.
        from .service import AdvisorService

        service = AdvisorService(db_path)
        plan = service.plan_day()
        print(f"پایگاه داده: {db_path}")
        print(f"ظرفیت امروز: {plan.capacity_minutes} دقیقه")
        print(f"برنامهٔ امروز: {plan.planned_minutes} دقیقه در {len(plan.placements)} بلوک")
        for note in plan.notes:
            print(f"  یادداشت: {note}")
        service.close()
        return 0

    # واردکردن PySide6 پیش از ساخت QApplication لازم است.
    from PySide6.QtWidgets import QApplication

    from .service import AdvisorService
    from .ui.app import MainWindow
    from .ui.theme import apply_theme

    app = QApplication(sys.argv[:1])
    app.setApplicationName("K2 Konkur Advisor")
    app.setOrganizationName("K2")
    apply_theme(app)

    service = AdvisorService(db_path)
    window = MainWindow(service)
    window.show()
    exit_code = app.exec()
    service.close()
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
