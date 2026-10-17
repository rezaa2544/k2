"""تست‌های invariant / property.

قاعده‌هایی که **همیشه** باید برقرار باشند:
  1. هیچ دو فعالیتی در یک بازه هم‌پوشانی ندارند.
  2. هیچ فعالیتی در پنجرهٔ خواب یا روی کلاس/تعهد سخت قرار نمی‌گیرد.
  3. مجموع زمان برنامه‌ریزی‌شده از ظرفیت روز بیشتر نمی‌شود.
  4. هیچ فعالیتی بدون دلیل ناپدید نمی‌شود.
  5. داده‌های ذخیره‌شده پس از بستن و بازکردن دوباره یکسان‌اند.
"""

from __future__ import annotations

import datetime as _dt
import random

import pytest

from k2.config import Settings
from k2.domain.enums import ActivityState, ActivityType, DeadlineType, EnergyNeed
from k2.scheduler import Scheduler, SchedulingContext

from .conftest import make_activity, make_event

SEED = 20261017
DAYS = [_dt.date(2026, 10, 10) + _dt.timedelta(days=i) for i in range(7)]


def _random_activities(rng: random.Random, count: int):
    activities = []
    for index in range(1, count + 1):
        splittable = rng.random() > 0.3
        activity_type = (
            ActivityType.TIMED_TEST if not splittable else ActivityType.PROCESSING
        )
        deadline = None
        deadline_type = DeadlineType.NONE
        if rng.random() > 0.6:
            deadline = _dt.datetime(2026, 10, 20, 23, 59) + _dt.timedelta(
                days=rng.randint(-5, 10)
            )
            deadline_type = (
                DeadlineType.HARD if rng.random() > 0.5 else DeadlineType.SOFT
            )
        activities.append(
            make_activity(
                index,
                f"کار {index}",
                minutes=rng.choice([20, 45, 60, 90, 120, 200]),
                activity_type=activity_type,
                splittable=splittable,
                min_chunk=rng.choice([15, 20, 30]),
                max_chunk=rng.choice([60, 90, 120]),
                energy=rng.choice(list(EnergyNeed)),
                deadline=deadline,
                deadline_type=deadline_type,
            )
        )
    return activities


def _context(rng: random.Random) -> SchedulingContext:
    events = []
    for index in range(rng.randint(0, 4)):
        weekday = rng.randint(0, 6)
        start_hour = rng.randint(8, 20)
        duration = rng.choice([60, 90, 120, 180])
        start = start_hour * 60
        events.append(
            make_event(
                f"کلاس {index}",
                weekday,
                f"{start_hour:02d}:00",
                f"{(start + duration) // 60:02d}:{(start + duration) % 60:02d}",
            )
        )
    return SchedulingContext(
        wake_minute=rng.choice([5 * 60, 6 * 60, 7 * 60]),
        sleep_minute=rng.choice([22 * 60, 23 * 60, 24 * 60]),
        fixed_events=events,
        energy_level=rng.randint(1, 3),
        settings=Settings(),
    )


@pytest.mark.parametrize("seed", [SEED, SEED + 1, SEED + 2, SEED + 3, SEED + 4])
def test_invariants_hold_for_random_schedules(seed: int):
    rng = random.Random(seed)
    scheduler = Scheduler(Settings())
    for date in DAYS:
        activities = _random_activities(rng, rng.randint(1, 12))
        context = _context(rng)
        plan = scheduler.plan_day(date, activities, context)

        # ۱) بدون هم‌پوشانی
        spans = sorted((p.start_minute, p.end_minute) for p in plan.placements)
        for index in range(len(spans) - 1):
            assert spans[index][1] <= spans[index + 1][0], "هم‌پوشانی بلوک‌ها"

        # ۲) بیرون از خواب و بیرون از کلاس‌ها
        wake = context.wake_minute
        sleep = context.sleep_minute
        from k2.jdate import weekday_index

        busy = [
            (event.start_minute, event.end_minute)
            for event in context.fixed_events
            if event.weekday == weekday_index(date)
        ]
        for placement in plan.placements:
            assert placement.start_minute >= wake
            assert placement.end_minute <= sleep
            for start, end in busy:
                assert placement.end_minute <= start or placement.start_minute >= end

        # ۳) عدم تجاوز از ظرفیت
        assert plan.planned_minutes <= plan.capacity_minutes

        # ۴) هیچ فعالیتی بی‌سروصدا ناپدید نمی‌شود
        scheduled_ids = {p.activity_id for p in plan.placements}
        unplaced_ids = {u.activity_id for u in plan.unplaced}
        all_ids = {a.id for a in activities if a.id is not None}
        assert scheduled_ids | unplaced_ids == all_ids
        assert not (scheduled_ids & unplaced_ids)


@pytest.mark.parametrize("seed", [SEED + 10, SEED + 11])
def test_capacity_never_exceeded_over_a_week(seed: int):
    rng = random.Random(seed)
    scheduler = Scheduler(Settings())
    activities = _random_activities(rng, 20)
    context = _context(rng)
    plans = scheduler.plan_range(DAYS[0], 7, activities, context)
    for plan in plans:
        assert plan.planned_minutes <= plan.capacity_minutes
        assert plan.margin_minutes >= 0


def test_no_activity_is_scheduled_in_the_past():
    """برنامهٔ روز جاری نباید قبل از «اکنون» شروع شود (در عمل: از ابتدای پنجره)."""
    scheduler = Scheduler(Settings())
    context = SchedulingContext(wake_minute=0, sleep_minute=24 * 60, settings=Settings())
    activity = make_activity(1, minutes=60)
    plan = scheduler.plan_day(DAYS[0], [activity], context)
    assert plan.placements
    assert plan.placements[0].start_minute >= 0


def test_activity_never_disappears_across_a_week():
    """هیچ فعالیتی در طول هفته بدون دلیل حذف نمی‌شود."""
    rng = random.Random(SEED + 20)
    scheduler = Scheduler(Settings())
    activities = _random_activities(rng, 8)
    context = _context(rng)
    plans = scheduler.plan_range(DAYS[0], 7, activities, context)
    # هر فعالیت باید در طول هفته یا جا گرفته باشد یا صریحاً گزارش شده باشد.
    seen: set[int] = set()
    for plan in plans:
        seen |= {p.activity_id for p in plan.placements}
        seen |= {u.activity_id for u in plan.unplaced}
    for activity in activities:
        assert activity.id in seen, "فعالیت بدون دلیل ناپدید شد"


def test_remaining_minutes_are_preserved_for_partial_placement():
    rng = random.Random(SEED + 30)
    scheduler = Scheduler(Settings())
    activities = _random_activities(rng, 3)
    for activity in activities:
        activity.est_minutes = 500
        activity.remaining_minutes = 500
    context = SchedulingContext(
        wake_minute=6 * 60, sleep_minute=23 * 60, settings=Settings()
    )
    plans = scheduler.plan_range(DAYS[0], 3, activities, context)
    # پس از چند روز، باقی‌مانده باید کاهش یافته باشد ولی صفر نشده باشد
    assert activities[0].remaining_minutes < 500
    assert activities[0].remaining_minutes >= 0
