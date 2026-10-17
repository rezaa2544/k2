"""تست زمان‌بند قاعده‌محور (SCH-01 تا SCH-05)."""

from __future__ import annotations

import datetime as _dt

import pytest

from k2.config import Settings
from k2.domain.enums import ActivityType, DeadlineType, EnergyNeed
from k2.scheduler import Scheduler, SchedulingContext, detect_fixed_conflicts

from .conftest import make_activity, make_event

SATURDAY = _dt.date(2026, 10, 10)  # شنبه


def _context(**kwargs) -> SchedulingContext:
    base = dict(
        wake_minute=6 * 60,
        sleep_minute=23 * 60,
        settings=Settings(),
    )
    base.update(kwargs)
    return SchedulingContext(**base)


def test_no_overlap_between_placements():
    scheduler = Scheduler(Settings())
    activities = [make_activity(i, f"کار {i}", minutes=90) for i in range(1, 6)]
    plan = scheduler.plan_day(SATURDAY, activities, _context())
    spans = sorted((p.start_minute, p.end_minute) for p in plan.placements)
    for index in range(len(spans) - 1):
        assert spans[index][1] <= spans[index + 1][0]


def test_planned_minutes_never_exceed_capacity():
    scheduler = Scheduler(Settings())
    activities = [make_activity(i, f"کار {i}", minutes=120) for i in range(1, 21)]
    plan = scheduler.plan_day(SATURDAY, activities, _context())
    assert plan.planned_minutes <= plan.capacity_minutes
    assert not plan.is_over_capacity


def test_nothing_is_scheduled_during_sleep():
    scheduler = Scheduler(Settings())
    activities = [make_activity(i, f"کار {i}", minutes=90) for i in range(1, 8)]
    context = _context(wake_minute=7 * 60, sleep_minute=22 * 60)
    plan = scheduler.plan_day(SATURDAY, activities, context)
    for placement in plan.placements:
        assert placement.end_minute <= 22 * 60
        assert placement.start_minute >= 7 * 60


def test_nothing_is_scheduled_on_top_of_a_class():
    scheduler = Scheduler(Settings())
    event = make_event("زیست", 0, "15:00", "19:00")
    context = _context(fixed_events=[event])
    activities = [make_activity(i, f"کار {i}", minutes=90) for i in range(1, 10)]
    plan = scheduler.plan_day(SATURDAY, activities, context)
    class_start = 15 * 60
    class_end = 19 * 60
    for placement in plan.placements:
        assert placement.end_minute <= class_start or placement.start_minute >= class_end


def test_unplaced_activities_are_reported_with_reason():
    scheduler = Scheduler(Settings())
    activities = [make_activity(i, f"کار {i}", minutes=200) for i in range(1, 8)]
    plan = scheduler.plan_day(SATURDAY, activities, _context())
    assert plan.unplaced, "باید فعالیت‌های جا‌نشده صریح گزارش شوند."
    for item in plan.unplaced:
        assert item.reason
        assert item.minutes > 0


def test_placement_carries_reason():
    scheduler = Scheduler(Settings())
    deadline = _dt.datetime(2026, 10, 12, 23, 59)
    activity = make_activity(
        1, "مهم", minutes=60, deadline=deadline, deadline_type=DeadlineType.HARD
    )
    plan = scheduler.plan_day(SATURDAY, [activity], _context())
    assert plan.placements
    reasons = " ".join(plan.placements[0].reasons)
    assert "مهلت سخت" in reasons


def test_hard_deadline_activity_is_scheduled_first():
    scheduler = Scheduler(Settings())
    hard = make_activity(
        1,
        "سخت",
        minutes=60,
        deadline=_dt.datetime(2026, 10, 20, 23, 59),
        deadline_type=DeadlineType.HARD,
    )
    soft = make_activity(
        2,
        "نرم",
        minutes=60,
        deadline=_dt.datetime(2026, 10, 11, 23, 59),
        deadline_type=DeadlineType.SOFT,
    )
    plan = scheduler.plan_day(SATURDAY, [soft, hard], _context())
    assert plan.placements
    assert plan.placements[0].activity_id == 1


def test_past_hard_deadline_is_reported_not_hidden():
    scheduler = Scheduler(Settings())
    activity = make_activity(
        1,
        "گذشته",
        minutes=60,
        deadline=_dt.datetime(2026, 10, 1, 23, 59),
        deadline_type=DeadlineType.HARD,
    )
    plan = scheduler.plan_day(SATURDAY, [activity], _context())
    assert not plan.placements
    assert len(plan.unplaced) == 1
    assert "گذشته" in plan.unplaced[0].reason


def test_splittable_activity_is_split_across_blocks():
    settings = Settings()
    # ضرایب را روی ۱ می‌گذاریم تا ظرفیت برای بررسی تقسیم کافی باشد.
    settings.capacity.focus_factor = 1.0
    settings.capacity.energy_factors = {1: 1.0, 2: 1.0, 3: 1.0}
    settings.capacity.safety_margin = 0.0
    scheduler = Scheduler(settings)
    # کلاس ۱۲:۰۰ تا ۱۶:۰۰ ⇒ دو بازهٔ آزاد: ۶:۰۰–۱۲:۰۰ و ۱۶:۰۰–۲۳:۰۰
    event = make_event("کلاس", 0, "12:00", "16:00")
    activity = make_activity(1, "ویدئوی بلند", minutes=300, splittable=True)
    plan = scheduler.plan_day(
        SATURDAY, [activity], _context(fixed_events=[event], settings=settings)
    )
    assert len(plan.placements) >= 2
    assert plan.placements[0].chunk_total >= 2
    assert sum(p.minutes for p in plan.placements) == 300


def test_non_splittable_activity_needs_contiguous_block():
    scheduler = Scheduler(Settings())
    # یک کلاس طولانی وسط روز ⇒ هیچ بلوک ۹۰ دقیقه‌ای پیوسته باقی نمی‌ماند
    event = make_event("کلاس", 0, "08:00", "22:00")
    activity = make_activity(
        1,
        "آزمون زمان‌دار",
        minutes=90,
        activity_type=ActivityType.TIMED_TEST,
        splittable=False,
    )
    plan = scheduler.plan_day(SATURDAY, [activity], _context(fixed_events=[event]))
    assert not plan.placements
    assert plan.unplaced
    assert "تقسیم‌ناپذیر" in plan.unplaced[0].reason


def test_non_splittable_larger_than_max_block_is_rejected():
    scheduler = Scheduler(Settings())
    activity = make_activity(
        1,
        "بزرگ",
        minutes=200,
        activity_type=ActivityType.TIMED_TEST,
        splittable=False,
        max_chunk=90,
    )
    plan = scheduler.plan_day(SATURDAY, [activity], _context())
    assert not plan.placements
    assert "بزرگ‌تر" in plan.unplaced[0].reason


def test_peak_hours_preferred_for_high_energy_tasks():
    scheduler = Scheduler(Settings())
    context = _context(peak_hours=[(18 * 60, 20 * 60)])
    activity = make_activity(
        1, "سنگین", minutes=60, energy=EnergyNeed.HIGH
    )
    plan = scheduler.plan_day(SATURDAY, [activity], context)
    assert plan.placements
    placement = plan.placements[0]
    # بلوک انتخاب‌شده باید با ساعت پربازده هم‌پوشانی داشته باشد.
    assert placement.start_minute < 20 * 60 and placement.end_minute > 18 * 60


def test_conflict_detection_reports_overlapping_classes():
    first = make_event("شیمی", 1, "15:00", "19:00")
    second = make_event("دینی", 1, "15:15", "20:45")
    context = _context(fixed_events=[first, second])
    messages = detect_fixed_conflicts(_dt.date(2026, 10, 11), context)
    assert messages
    assert "شیمی" in messages[0] and "دینی" in messages[0]


def test_plan_range_carries_unplaced_activities_forward():
    scheduler = Scheduler(Settings())
    activities = [make_activity(1, "بزرگ", minutes=600, splittable=True)]
    plans = scheduler.plan_range(SATURDAY, 3, activities, _context())
    assert len(plans) == 3
    # فعالیت باید در روزهای بعد هم دیده شود (نه حذف پنهان)
    assert any(plan.unplaced or plan.placements for plan in plans[1:])


def test_done_activities_are_not_scheduled():
    from k2.domain.enums import ActivityState

    scheduler = Scheduler(Settings())
    activity = make_activity(
        1, "انجام‌شده", minutes=60, state=ActivityState.DONE
    )
    plan = scheduler.plan_day(SATURDAY, [activity], _context())
    assert not plan.placements
    assert not plan.unplaced
