"""ابزارهای مشترک تست.

نکته: برای تست‌های رابط کاربری، محیط ``QT_QPA_PLATFORM=offscreen`` پیش از
واردکردن PySide6 تنظیم می‌شود تا نیازی به محیط گرافیکی نباشد.
"""

from __future__ import annotations

import datetime as _dt
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("K2_DATA_DIR", "/tmp/k2-tests")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from k2.config import Settings  # noqa: E402
from k2.domain.enums import (  # noqa: E402
    ActivityState,
    ActivityType,
    DeadlineType,
    EnergyNeed,
)
from k2.domain.models import Activity, FixedEvent, Routine  # noqa: E402
from k2.service import AdvisorService  # noqa: E402


@pytest.fixture()
def settings() -> Settings:
    return Settings()


@pytest.fixture()
def service(tmp_path: Path) -> AdvisorService:
    """سرویس با پایگاه دادهٔ موقت."""
    svc = AdvisorService(tmp_path / "k2-test.db")
    yield svc
    svc.close()


@pytest.fixture()
def service_with_schedule(service: AdvisorService) -> AdvisorService:
    """سرویس با برنامهٔ نمونهٔ کاربر."""
    service.import_sample_schedule()
    service.wake_minute = 6 * 60
    service.sleep_minute = 23 * 60
    return service


def make_activity(
    activity_id: int,
    title: str = "کار",
    *,
    minutes: int = 60,
    activity_type: ActivityType = ActivityType.PROCESSING,
    deadline: _dt.datetime | None = None,
    deadline_type: DeadlineType = DeadlineType.NONE,
    splittable: bool = True,
    min_chunk: int = 20,
    max_chunk: int = 90,
    energy: EnergyNeed = EnergyNeed.MEDIUM,
    depends_on: tuple[int, ...] = (),
    state: ActivityState = ActivityState.READY,
) -> Activity:
    """ساخت یک فعالیت تستی."""
    return Activity(
        id=activity_id,
        title=title,
        type=activity_type,
        est_minutes=minutes,
        remaining_minutes=minutes,
        min_chunk=min_chunk,
        max_chunk=max_chunk,
        splittable=splittable,
        deadline_type=deadline_type,
        deadline_at=deadline,
        energy_need=energy,
        depends_on=depends_on,
        state=state,
    )


def make_event(
    title: str,
    weekday: int,
    start: str,
    end: str,
    *,
    is_recorded: bool = False,
) -> FixedEvent:
    """ساخت رویداد ثابت تستی."""

    def minutes(clock: str) -> int:
        hour, _, minute = clock.partition(":")
        return int(hour) * 60 + int(minute)

    return FixedEvent(
        title=title,
        weekday=weekday,
        start_minute=minutes(start),
        end_minute=minutes(end),
        is_recorded=is_recorded,
    )


def make_routine(
    title: str, start: str, end: str, *, kind: str = "meal"
) -> Routine:
    """ساخت بازهٔ ضروری تستی."""
    from k2.domain.enums import RoutineKind

    def minutes(clock: str) -> int:
        hour, _, minute = clock.partition(":")
        return int(hour) * 60 + int(minute)

    return Routine(
        title=title,
        kind=RoutineKind(kind),
        start_minute=minutes(start),
        end_minute=minutes(end),
        weekdays=frozenset(range(7)),
    )


@pytest.fixture(scope="session")
def qapp():
    """نمونهٔ QApplication مشترک برای تست‌های رابط کاربری."""
    from PySide6.QtWidgets import QApplication

    from k2.ui.theme import apply_theme

    app = QApplication.instance() or QApplication([])
    apply_theme(app)
    return app
