"""تست سناریوهای مرزی (سند اجرایی، بخش ۸)."""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

import pytest

from k2.backlog import build_backlog, build_minimal_day, build_triage, return_after_break
from k2.capacity import compute_capacity
from k2.config import Settings
from k2.domain.enums import (
    ActivityState,
    ActivityType,
    DeadlineType,
    EnergyNeed,
    ErrorCode,
    ReviewState,
)
from k2.scheduler import Scheduler, SchedulingContext
from k2.service import AdvisorService

from .conftest import make_activity, make_event

SATURDAY = _dt.date(2026, 10, 10)


# ---------------------------------------------------------------------------
# ظرفیت
# ---------------------------------------------------------------------------


def test_zero_capacity_day():
    breakdown = compute_capacity(
        SATURDAY, wake_minute=8 * 60, sleep_minute=8 * 60, settings=Settings()
    )
    assert breakdown.capacity_minutes == 0
    assert breakdown.notes


def test_capacity_with_full_day_of_classes():
    events = [
        make_event("کلاس", 0, "06:00", "23:00"),
    ]
    breakdown = compute_capacity(
        SATURDAY,
        wake_minute=6 * 60,
        sleep_minute=23 * 60,
        fixed_events=events,
        settings=Settings(),
    )
    assert breakdown.capacity_minutes == 0
    assert breakdown.raw_minutes == 0


def test_capacity_with_tiny_window():
    breakdown = compute_capacity(
        SATURDAY, wake_minute=12 * 60, sleep_minute=13 * 60, settings=Settings()
    )
    assert breakdown.awake_minutes == 60
    assert breakdown.capacity_minutes >= 0


# ---------------------------------------------------------------------------
# زمان‌بند
# ---------------------------------------------------------------------------


def test_multiple_simultaneous_deadlines():
    """چند مهلت هم‌زمان: همه باید در صف دیده شوند، نه فقط یکی."""
    scheduler = Scheduler(Settings())
    deadline = _dt.datetime(2026, 10, 12, 23, 59)
    activities = [
        make_activity(
            i,
            f"کار {i}",
            minutes=120,
            deadline=deadline,
            deadline_type=DeadlineType.HARD,
        )
        for i in range(1, 6)
    ]
    plan = scheduler.plan_day(SATURDAY, activities, SchedulingContext(settings=Settings()))
    placed_ids = {p.activity_id for p in plan.placements}
    unplaced_ids = {u.activity_id for u in plan.unplaced}
    assert placed_ids | unplaced_ids == {1, 2, 3, 4, 5}
    assert not (placed_ids & unplaced_ids)
    # با ظرفیت محدود، بخشی جا نمی‌شود و صریح گزارش می‌شود
    assert plan.unplaced
    for item in plan.unplaced:
        assert item.reason


def test_non_splittable_activity_bigger_than_block():
    scheduler = Scheduler(Settings())
    activity = make_activity(
        1,
        "شبیه‌سازی",
        minutes=150,
        activity_type=ActivityType.EXAM,
        splittable=False,
        max_chunk=90,
    )
    plan = scheduler.plan_day(SATURDAY, [activity], SchedulingContext(settings=Settings()))
    assert plan.unplaced
    assert "تقسیم‌ناپذیر" in plan.unplaced[0].reason


def test_overlapping_classes_are_detected_but_not_silently_dropped():
    scheduler = Scheduler(Settings())
    events = [make_event("شیمی", 0, "15:00", "19:00"), make_event("دینی", 0, "15:15", "20:45")]
    context = SchedulingContext(fixed_events=events, settings=Settings())
    plan = scheduler.plan_day(SATURDAY, [], context)
    assert any("تعارض" in note for note in plan.notes)


def test_exam_date_change_is_reflected_in_review_cap(service: AdvisorService):
    """تغییر تاریخ آزمون، سقف فاصلهٔ مرور را تغییر می‌دهد."""
    from k2.domain.models import ExamProfile

    profile = ExamProfile(name="آزمون", target_date=_dt.date(2026, 12, 1))
    service.create_exam_profile(profile)
    item = service.create_review_item(
        __import__("k2.review_engine", fromlist=["create_review_item"]).create_review_item(
            label="مفهوم", today=SATURDAY
        )
    )
    service.record_review(item, correct=True, confidence=3)
    first = service.repo.list_review_items()[0]

    profile.target_date = _dt.date(2026, 10, 20)
    service.update_exam_profile(profile)
    service.record_review(item, correct=True, confidence=3)
    second = service.repo.list_review_items()[0]
    assert second.interval_days <= first.interval_days + 0.001


# ---------------------------------------------------------------------------
# عقب‌افتادگی
# ---------------------------------------------------------------------------


def test_backlog_levels():
    settings = Settings()
    activities = []
    for index in range(1, 6):
        activity = make_activity(index, minutes=60)
        activity.deadline_at = _dt.datetime(2026, 10, 1, 23, 59)
        activity.state = ActivityState.OVERDUE
        activities.append(activity)
    summary = build_backlog(
        date=SATURDAY,
        activities=activities,
        daily_capacity_minutes=120,
        settings=settings,
    )
    assert summary.debt_minutes == 300
    assert summary.level.value in {"green", "yellow", "orange", "red"}
    assert summary.items


def test_backlog_with_zero_capacity_is_red():
    settings = Settings()
    activity = make_activity(1, minutes=60)
    activity.deadline_at = _dt.datetime(2026, 10, 1, 23, 59)
    summary = build_backlog(
        date=SATURDAY,
        activities=[activity],
        daily_capacity_minutes=0,
        settings=settings,
    )
    assert summary.level == "red" or summary.level.value == "red"
    assert summary.notes


def test_minimal_day_is_small_and_contains_no_heavy_new_work():
    settings = Settings()
    review = make_activity(1, "مرور", activity_type=ActivityType.REVIEW, minutes=20)
    heavy = make_activity(
        2,
        "بازآموزی سنگین",
        activity_type=ActivityType.REMEDIATION,
        minutes=180,
    )
    plan = build_minimal_day(
        date=SATURDAY,
        activities=[review, heavy],
        capacity_minutes=300,
        settings=settings,
    )
    assert plan.minutes <= int(300 * settings.backlog.minimal_day_ratio)
    assert all(a.type != ActivityType.REMEDIATION for a in plan.activities)
    assert plan.notes


def test_triage_splits_into_three_buckets():
    settings = Settings()
    must = make_activity(1, "سخت")
    must.deadline_type = DeadlineType.HARD
    must.deadline_at = _dt.datetime(2026, 10, 11, 23, 59)
    optional = make_activity(2, "اختیاری")
    optional.deadline_at = None
    triage = build_triage(
        activities=[must, optional],
        date=SATURDAY,
        capacity_minutes=300,
        settings=settings,
    )
    assert must in triage.must_do
    assert optional in triage.suggest_drop
    assert triage.notes


def test_return_after_break_reduces_load():
    settings = Settings()
    capacity, notes = return_after_break(
        date=SATURDAY,
        last_active_date=SATURDAY - _dt.timedelta(days=5),
        normal_capacity_minutes=600,
        settings=settings,
    )
    assert capacity < 600
    assert notes


def test_return_after_break_without_break_keeps_capacity():
    settings = Settings()
    capacity, notes = return_after_break(
        date=SATURDAY,
        last_active_date=SATURDAY - _dt.timedelta(days=1),
        normal_capacity_minutes=600,
        settings=settings,
    )
    assert capacity == 600
    assert notes == []


# ---------------------------------------------------------------------------
# داده و مسیر
# ---------------------------------------------------------------------------


def test_database_with_persian_path(tmp_path: Path):
    """مسیر دارای حروف فارسی باید کار کند."""
    target = tmp_path / "پوشهٔ فارسی" / "دادهٔ من"
    target.mkdir(parents=True)
    service = AdvisorService(target / "k2.db")
    try:
        service.wake_minute = 6 * 60
        plan = service.plan_day(SATURDAY)
        assert plan.capacity_minutes >= 0
    finally:
        service.close()


def test_reopen_database_keeps_data(tmp_path: Path):
    path = tmp_path / "k2.db"
    service = AdvisorService(path)
    service.create_exam_profile(
        __import__("k2.domain.models", fromlist=["ExamProfile"]).ExamProfile(name="آزمون")
    )
    service.close()

    service = AdvisorService(path)
    try:
        assert service.active_exam_profile() is not None
        assert service.active_exam_profile().name == "آزمون"
    finally:
        service.close()


def test_large_review_dataset_does_not_break(engineering=None):
    """دادهٔ مرور زیاد نباید باعث سرریز یا خطا شود."""
    from k2.review_engine import apply_review, create_review_item

    settings = Settings()
    item = create_review_item(label="مورد", today=SATURDAY)
    for _ in range(200):
        apply_review(item, 4, today=SATURDAY, settings=settings)
    assert item.interval_days <= settings.review.max_interval_days
    assert item.due_date is not None
