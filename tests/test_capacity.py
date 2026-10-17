"""تست محاسبهٔ ظرفیت (CAP-01 تا CAP-03)."""

from __future__ import annotations

import datetime as _dt

import pytest

from k2.capacity import (
    Interval,
    awake_segments,
    compute_capacity,
    merge_intervals,
    subtract_intervals,
)
from k2.config import Settings
from k2.domain.enums import RoutineKind, RoutineScope

from .conftest import make_event, make_routine

SATURDAY = _dt.date(2026, 10, 10)


def test_awake_segments_normal_case():
    assert awake_segments(6 * 60, 23 * 60) == [(360, 1380)]


def test_awake_segments_after_midnight_sleep():
    # خواب ۰۱:۰۰ و بیداری ۰۷:۰۰ ⇒ دو قطعه
    segments = awake_segments(7 * 60, 60)
    assert segments == [(420, 1440), (0, 60)]
    assert sum(end - start for start, end in segments) == 1080


def test_merge_intervals_counts_once():
    merged = merge_intervals(
        [
            Interval(100, 200, "a"),
            Interval(150, 250, "b"),
            Interval(300, 350, "c"),
        ]
    )
    assert len(merged) == 2
    assert merged[0].start == 100 and merged[0].end == 250
    assert sum(iv.minutes for iv in merged) == 200


def test_subtract_intervals():
    free = subtract_intervals([(0, 600)], [Interval(100, 200), Interval(300, 400)])
    assert [(iv.start, iv.end) for iv in free] == [(0, 100), (200, 300), (400, 600)]


def test_capacity_baseline():
    breakdown = compute_capacity(
        SATURDAY, wake_minute=6 * 60, sleep_minute=23 * 60, settings=Settings()
    )
    # ۱۷ ساعت بیداری = ۱۰۲۰ دقیقه
    assert breakdown.awake_minutes == 1020
    assert breakdown.raw_minutes == 1020
    # ضریب تمرکز ۰٫۶ × انرژی ۰٫۸ = ۰٫۴۸
    assert breakdown.effective_minutes == int(round(1020 * 0.6 * 0.8))
    # با حاشیهٔ ۲۰٪
    assert breakdown.capacity_minutes == int(
        round(breakdown.effective_minutes * 0.8)
    )


def test_capacity_subtracts_classes_and_routines_once():
    event = make_event("زیست", 0, "15:00", "19:00")
    routine = make_routine("ناهار", "12:30", "13:00")
    breakdown = compute_capacity(
        SATURDAY,
        wake_minute=6 * 60,
        sleep_minute=23 * 60,
        fixed_events=[event],
        routines=[routine],
        settings=Settings(),
    )
    # ۲۴۰ دقیقه کلاس + ۳۰ دقیقه غذا
    assert breakdown.fixed_minutes == 270
    assert breakdown.raw_minutes == 1020 - 270
    assert breakdown.free_minutes == 1020 - 270


def test_overlapping_events_counted_once():
    """کلاس‌های هم‌پوشان نباید دوبار از ظرفیت کسر شوند."""
    first = make_event("شیمی", 0, "15:00", "19:00")
    second = make_event("دینی", 0, "15:15", "20:45")
    breakdown = compute_capacity(
        SATURDAY,
        wake_minute=6 * 60,
        sleep_minute=23 * 60,
        fixed_events=[first, second],
        settings=Settings(),
    )
    # بازهٔ یکتا ۱۵:۰۰ تا ۲۰:۴۵ = ۳۴۵ دقیقه
    assert breakdown.fixed_minutes == 345


def test_sleep_is_never_available():
    breakdown = compute_capacity(
        SATURDAY, wake_minute=6 * 60, sleep_minute=23 * 60, settings=Settings()
    )
    for interval in breakdown.free:
        assert not (interval.start < 6 * 60 and 6 * 60 < interval.end)
        assert interval.end <= 23 * 60


def test_zero_capacity_when_no_awake_window():
    breakdown = compute_capacity(
        SATURDAY, wake_minute=8 * 60, sleep_minute=8 * 60, settings=Settings()
    )
    assert breakdown.awake_minutes == 0
    assert breakdown.capacity_minutes == 0
    assert breakdown.notes


def test_capacity_never_negative_with_heavy_schedule():
    events = [
        make_event("کلاس ۱", 0, "06:00", "12:00"),
        make_event("کلاس ۲", 0, "12:00", "18:00"),
        make_event("کلاس ۳", 0, "18:00", "23:00"),
    ]
    breakdown = compute_capacity(
        SATURDAY,
        wake_minute=6 * 60,
        sleep_minute=23 * 60,
        fixed_events=events,
        settings=Settings(),
    )
    assert breakdown.raw_minutes == 0
    assert breakdown.capacity_minutes == 0


def test_energy_levels_change_capacity():
    settings = Settings()
    low = compute_capacity(
        SATURDAY, wake_minute=6 * 60, sleep_minute=23 * 60, energy_level=1, settings=settings
    )
    high = compute_capacity(
        SATURDAY, wake_minute=6 * 60, sleep_minute=23 * 60, energy_level=3, settings=settings
    )
    assert low.capacity_minutes < high.capacity_minutes


def test_alternate_routine_applies_every_other_day():
    routine = make_routine("حمام", "22:45", "23:00")
    routine.kind = RoutineKind.HYGIENE
    routine.scope = RoutineScope.ALTERNATE
    routine.weekdays = frozenset({0, 2, 4, 6})

    first = compute_capacity(
        _dt.date(2026, 10, 10),
        wake_minute=6 * 60,
        sleep_minute=23 * 60,
        routines=[routine],
        settings=Settings(),
    )
    second = compute_capacity(
        _dt.date(2026, 10, 11),
        wake_minute=6 * 60,
        sleep_minute=23 * 60,
        routines=[routine],
        settings=Settings(),
    )
    assert first.fixed_minutes == 15
    assert second.fixed_minutes == 0


def test_overnight_routine_blocks_both_sides_of_midnight():
    routine = make_routine("خواب", "23:00", "06:00")
    routine.kind = RoutineKind.SLEEP
    routine.weekdays = frozenset(range(7))
    # برای پنجره‌ای که از ۰۵:۰۰ آغاز می‌شود، نیمهٔ صبح هم باید مسدود باشد.
    breakdown = compute_capacity(
        SATURDAY, wake_minute=5 * 60, sleep_minute=23 * 60,
        routines=[routine], settings=Settings(),
    )
    assert breakdown.fixed_minutes == 60  # فقط 05:00–06:00 داخل پنجرهٔ بیداری است
    assert all(not (iv.start < 5 * 60 + 30 < iv.end) for iv in breakdown.free)
