"""محاسبهٔ ظرفیت واقعی روزانه (سند تحقیق ۲، بخش ۲).

قرارداد:
  * خواب **محدودیت سخت** است: هیچ فعالیتی در پنجرهٔ خواب قرار نمی‌گیرد.
  * بازه‌های هم‌پوشان فقط **یک‌بار** از ظرفیت کسر می‌شوند.
  * خروجی شامل تفکیک کامل است تا کاربر بتواند ببیند ظرفیت از کجا آمده (CAP-02).
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from .config import CapacitySettings, Settings
from .domain.enums import RoutineScope
from .domain.models import FixedEvent, Routine

DAY_MINUTES = 24 * 60


@dataclass(frozen=True)
class Interval:
    """بازهٔ زمانی در دقیقه از ابتدای شبانه‌روز."""

    start: int
    end: int
    label: str = ""
    kind: str = "fixed"
    hard: bool = True

    @property
    def minutes(self) -> int:
        return max(0, self.end - self.start)

    def overlaps(self, other: "Interval") -> bool:
        return self.start < other.end and other.start < self.end


@dataclass
class CapacityBreakdown:
    """تفکیک ظرفیت یک روز (CAP-02)."""

    date: _dt.date
    awake_minutes: int = 0
    fixed_minutes: int = 0
    essential_minutes: int = 0
    raw_minutes: int = 0
    effective_minutes: int = 0
    capacity_minutes: int = 0
    focus_factor: float = 1.0
    energy_factor: float = 1.0
    safety_margin: float = 0.0
    awake_segments: tuple[tuple[int, int], ...] = ()
    covered: tuple[Interval, ...] = ()
    free: tuple[Interval, ...] = ()
    notes: list[str] = field(default_factory=list)

    @property
    def margin_minutes(self) -> int:
        """حاشیهٔ آزاد باقی‌مانده (ظرفیت منهای برنامه)."""
        return max(0, self.capacity_minutes)

    @property
    def free_minutes(self) -> int:
        return sum(interval.minutes for interval in self.free)


# ---------------------------------------------------------------------------
# ابزارهای بازه
# ---------------------------------------------------------------------------


def merge_intervals(intervals: Iterable[Interval]) -> list[Interval]:
    """ادغام بازه‌های هم‌پوشان (بدون تغییر مجموع طول)."""
    ordered = sorted((iv for iv in intervals if iv.minutes > 0), key=lambda iv: (iv.start, iv.end))
    merged: list[Interval] = []
    for interval in ordered:
        if merged and interval.start <= merged[-1].end:
            last = merged[-1]
            if interval.end > last.end:
                merged[-1] = Interval(
                    start=last.start,
                    end=interval.end,
                    label=last.label,
                    kind=last.kind,
                    hard=last.hard,
                )
        else:
            merged.append(interval)
    return merged


def subtract_intervals(
    base: Sequence[tuple[int, int]], blocked: Sequence[Interval]
) -> list[Interval]:
    """بازه‌های آزاد = ``base`` منهای ``blocked``."""
    blocked_merged = merge_intervals(blocked)
    free: list[Interval] = []
    for start, end in base:
        cursor = start
        for block in blocked_merged:
            if block.end <= cursor or block.start >= end:
                continue
            if block.start > cursor:
                free.append(Interval(start=cursor, end=min(block.start, end), kind="free", hard=False))
            cursor = max(cursor, block.end)
            if cursor >= end:
                break
        if cursor < end:
            free.append(Interval(start=cursor, end=end, kind="free", hard=False))
    return [iv for iv in free if iv.minutes > 0]


def awake_segments(wake_minute: int, sleep_minute: int) -> list[tuple[int, int]]:
    """بازه‌های بیداری در یک شبانه‌روز.

    اگر ساعت خواب بعد از ساعت بیداری باشد (حالت معمول)، یک بازهٔ پیوسته
    به دست می‌آید. اگر خواب پیش از بیداری باشد (مثلاً خواب ۰۱:۰۰)، بازه
    به دو قطعه شکسته می‌شود.
    """
    wake = max(0, min(DAY_MINUTES - 1, wake_minute))
    sleep = max(0, min(DAY_MINUTES, sleep_minute))
    if sleep > wake:
        return [(wake, sleep)]
    if sleep == wake:
        return []
    return [(wake, DAY_MINUTES), (0, sleep)]


# ---------------------------------------------------------------------------
# جمع‌آوری رویدادهای یک روز
# ---------------------------------------------------------------------------


def _routine_applies_weekday(routine: Routine, weekday: int) -> bool:
    if routine.scope == RoutineScope.ALTERNATE:
        # یک‌روزدرمیان بر پایهٔ یکی از روزهای انتخاب‌شده به‌عنوان مبدأ.
        origin = routine.weekdays
        anchor = min(origin) if origin else 0
        distance = (weekday - anchor) % 7
        return distance % 2 == 0
    return weekday in routine.weekdays


def _routine_applies(routine: Routine, date: _dt.date) -> bool:
    from .jdate import weekday_index

    return _routine_applies_weekday(routine, weekday_index(date))


def collect_fixed_intervals(
    date: _dt.date,
    fixed_events: Sequence[FixedEvent],
    routines: Sequence[Routine],
    exceptions: Sequence=(),
) -> list[Interval]:
    """بازه‌های محافظت‌شدهٔ یک روز.

    شامل کلاس‌ها/آزمون‌ها/تعهدات (سخت) و کارهای ضروری مانند غذا و استراحت.
    """
    from .jdate import weekday_index

    weekday = weekday_index(date)
    exception_map = {exc.event_id: exc for exc in exceptions if exc.date == date}

    intervals: list[Interval] = []

    for event in fixed_events:
        if event.weekday != weekday or event.is_recorded:
            continue
        exc = exception_map.get(event.id)
        if exc is not None and exc.cancelled:
            continue
        start, end = event.start_minute, event.end_minute
        if exc is not None and exc.new_start_minute is not None and exc.new_end_minute is not None:
            start, end = exc.new_start_minute, exc.new_end_minute
        if end <= start:
            continue
        intervals.append(
            Interval(
                start=start,
                end=end,
                label=event.title,
                kind="fixed",
                hard=True,
            )
        )

    for routine in routines:
        if routine.end_minute == routine.start_minute:
            continue
        kind = "essential"
        if routine.end_minute > routine.start_minute:
            if _routine_applies(routine, date):
                intervals.append(
                    Interval(
                        start=routine.start_minute, end=routine.end_minute,
                        label=routine.title, kind=kind, hard=True,
                    )
                )
            continue

        # بازهٔ شبانه مثل خواب ۲۳:۰۰ تا ۰۶:۰۰ به دو نیمهٔ روز تقسیم می‌شود.
        # نیمهٔ پس از نیمه‌شب از روزِ قبلی به ارث می‌رسد.
        weekday = weekday_index(date)
        if _routine_applies_weekday(routine, weekday):
            intervals.append(
                Interval(
                    start=routine.start_minute, end=DAY_MINUTES,
                    label=routine.title, kind=kind, hard=True,
                )
            )
        if _routine_applies_weekday(routine, (weekday - 1) % 7) and routine.end_minute > 0:
            intervals.append(
                Interval(
                    start=0, end=routine.end_minute,
                    label=routine.title, kind=kind, hard=True,
                )
            )

    return intervals


# ---------------------------------------------------------------------------
# محاسبهٔ ظرفیت
# ---------------------------------------------------------------------------


def compute_capacity(
    date: _dt.date,
    *,
    wake_minute: int,
    sleep_minute: int,
    fixed_events: Sequence[FixedEvent] = (),
    routines: Sequence[Routine] = (),
    exceptions: Sequence = (),
    energy_level: int = 2,
    settings: Settings | None = None,
    focus_factor: float | None = None,
) -> CapacityBreakdown:
    """ظرفیت واقعی یک روز را محاسبه می‌کند.

    Args:
        date: روز موردنظر.
        wake_minute: ساعت بیداری (دقیقه از ابتدای شبانه‌روز).
        sleep_minute: ساعت خواب.
        fixed_events: رویدادهای ثابت هفتگی.
        routines: بازه‌های ضروری روزانه.
        exceptions: استثناهای رویداد (لغو/جابه‌جایی).
        energy_level: خودگزارشی انرژی ۱..۳.
        settings: تنظیمات برنامه.
        focus_factor: ضریب تمرکز؛ اگر داده نشود از تنظیمات/میانهٔ تاریخچه خوانده می‌شود.
    """
    settings = settings or Settings()
    cap_settings: CapacitySettings = settings.capacity

    segments = awake_segments(wake_minute, sleep_minute)
    awake_total = sum(end - start for start, end in segments)

    protected = collect_fixed_intervals(date, fixed_events, routines, exceptions)
    covered = merge_intervals(protected)
    covered_total = sum(
        _intersect_minutes(interval, segments) for interval in covered
    )

    raw = max(0, awake_total - covered_total)

    focus = cap_settings.focus_factor if focus_factor is None else focus_factor
    focus = max(0.05, min(1.5, float(focus)))
    energy = cap_settings.energy_factors.get(int(energy_level), 0.8)
    energy = max(0.05, min(1.5, float(energy)))

    effective = int(round(raw * focus * energy))
    margin = max(0.0, min(0.9, float(cap_settings.safety_margin)))
    capacity = int(round(effective * (1.0 - margin)))

    free = subtract_intervals(segments, covered)

    breakdown = CapacityBreakdown(
        date=date,
        awake_minutes=awake_total,
        fixed_minutes=covered_total,
        essential_minutes=0,
        raw_minutes=raw,
        effective_minutes=effective,
        capacity_minutes=capacity,
        focus_factor=focus,
        energy_factor=energy,
        safety_margin=margin,
        awake_segments=tuple(segments),
        covered=tuple(covered),
        free=tuple(free),
    )

    if awake_total == 0:
        breakdown.notes.append("پنجرهٔ بیداری تعریف نشده است؛ ظرفیت صفر است.")
    if raw < 0:
        breakdown.notes.append("تعارض در ساعت خواب و بیداری.")
    if capacity == 0 and raw > 0:
        breakdown.notes.append(
            "ظرفیت به صفر رسیده است؛ حاشیهٔ اطمینان یا ضرایب تمرکز/انرژی را بازبینی کنید."
        )
    return breakdown


def _intersect_minutes(interval: Interval, segments: Sequence[tuple[int, int]]) -> int:
    total = 0
    for start, end in segments:
        overlap = min(interval.end, end) - max(interval.start, start)
        if overlap > 0:
            total += overlap
    return total
