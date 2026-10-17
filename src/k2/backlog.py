"""مدیریت عقب‌افتادگی: بدهی، سطح‌بندی، سقف جبران و برنامهٔ حداقلی.

سند تحقیق ۲، بخش ۱۱ و ۱۲.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Optional, Sequence

from .config import Settings
from .domain.enums import ActivityState, ActivityType, DebtLevel
from .domain.models import Activity, DayPlan


@dataclass
class BacklogItem:
    """یک کار عقب‌افتاده."""

    activity_id: int
    title: str
    remaining_minutes: int
    age_days: float = 0.0
    deadline_at: Optional[_dt.datetime] = None
    deadline_type: str = "none"
    state: ActivityState = ActivityState.OVERDUE
    subject_name: str = ""
    reason: str = ""

    @property
    def age_score(self) -> float:
        return max(0.0, self.age_days)


@dataclass
class BacklogSummary:
    """خلاصهٔ صف عقب‌افتادگی (BL-01)."""

    date: _dt.date
    items: list[BacklogItem] = field(default_factory=list)
    debt_minutes: int = 0
    recoverable_minutes: int = 0
    debt_ratio: float = 0.0
    level: DebtLevel = DebtLevel.GREEN
    compensation_cap_minutes: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def is_critical(self) -> bool:
        return self.level == DebtLevel.RED


def build_backlog(
    *,
    date: _dt.date,
    activities: Sequence[Activity],
    daily_capacity_minutes: int,
    settings: Optional[Settings] = None,
    recoverable_days: Optional[int] = None,
) -> BacklogSummary:
    """صف عقب‌افتادگی و نسبت بدهی را محاسبه می‌کند."""
    settings = settings or Settings()
    b = settings.backlog
    days = recoverable_days or settings.capacity.recovery_window_days

    items: list[BacklogItem] = []
    for activity in activities:
        if activity.state in {
            ActivityState.DONE,
            ActivityState.EXPIRED,
            ActivityState.DROPPED,
        }:
            continue
        if activity.deadline_at is None:
            continue
        overdue_days = (date - activity.deadline_at.date()).days
        if overdue_days < 0:
            continue
        items.append(
            BacklogItem(
                activity_id=activity.id or -1,
                title=activity.title,
                remaining_minutes=activity.effective_minutes,
                age_days=float(overdue_days),
                deadline_at=activity.deadline_at,
                deadline_type=activity.deadline_type.value,
                state=ActivityState.OVERDUE,
                subject_name=activity.subject_name,
                reason=activity.state_reason,
            )
        )

    items.sort(key=lambda item: (-item.age_days, -item.remaining_minutes))
    debt = sum(item.remaining_minutes for item in items)
    recoverable = max(0, daily_capacity_minutes * days)
    ratio = (debt / recoverable) if recoverable else (1.0 if debt else 0.0)

    if ratio < b.green_max:
        level = DebtLevel.GREEN
    elif ratio < b.yellow_max:
        level = DebtLevel.YELLOW
    elif ratio < b.orange_max:
        level = DebtLevel.ORANGE
    else:
        level = DebtLevel.RED

    summary = BacklogSummary(
        date=date,
        items=items,
        debt_minutes=debt,
        recoverable_minutes=recoverable,
        debt_ratio=ratio,
        level=level,
        compensation_cap_minutes=int(daily_capacity_minutes * b.compensation_cap_ratio),
    )

    if level == DebtLevel.RED:
        summary.notes.append(
            "بدهی از ظرفیت قابل جبران هفتگی بیشتر است؛ فهرست سه‌بخشی «حتماً / اگر شد / "
            "پیشنهاد حذف» برای تصمیم شما ساخته شده است."
        )
    elif level == DebtLevel.ORANGE:
        summary.notes.append(
            "صف جبران فعال است؛ مرور سبک نگه داشته شود و حذف فعالیت‌های اختیاری "
            "فقط با تأیید شما انجام می‌شود."
        )
    elif level == DebtLevel.YELLOW:
        summary.notes.append("کاهش اختیاری حجم کار پیشنهاد می‌شود.")
    return summary


def compensation_budget(
    capacity_minutes: int, settings: Optional[Settings] = None
) -> int:
    """سقف کار جبرانی روزانه (سند ۲، بخش ۱۱.۳)."""
    settings = settings or Settings()
    return int(capacity_minutes * settings.backlog.compensation_cap_ratio)


@dataclass
class MinimalDayPlan:
    """برنامهٔ حداقلی روز دشوار (BEH-01، سند ۲، بخش ۱۲)."""

    date: _dt.date
    activities: list[Activity] = field(default_factory=list)
    minutes: int = 0
    notes: list[str] = field(default_factory=list)


def build_minimal_day(
    *,
    date: _dt.date,
    activities: Sequence[Activity],
    capacity_minutes: int,
    settings: Optional[Settings] = None,
) -> MinimalDayPlan:
    """برنامهٔ حداقلی: مرور حیاتی + یک کار کوتاه و آسان.

    بدون مطلب جدید سنگین و بدون جریمه در آمار.
    """
    settings = settings or Settings()
    budget = max(0, int(capacity_minutes * settings.backlog.minimal_day_ratio))
    plan = MinimalDayPlan(date=date)

    critical = [
        a
        for a in activities
        if a.type in {ActivityType.REVIEW, ActivityType.CONSOLIDATION}
        and a.state not in {ActivityState.DONE, ActivityState.DROPPED, ActivityState.EXPIRED}
    ]
    hard = [
        a
        for a in activities
        if a.deadline_type.value == "hard"
        and a.deadline_at is not None
        and 0 <= (a.deadline_at.date() - date).days <= 1
        and a.state not in {ActivityState.DONE, ActivityState.DROPPED, ActivityState.EXPIRED}
    ]

    chosen: list[Activity] = []
    for activity in hard + critical:
        if activity in chosen:
            continue
        if sum(a.effective_minutes for a in chosen) + activity.effective_minutes > budget:
            continue
        chosen.append(activity)
        if sum(a.effective_minutes for a in chosen) >= budget:
            break

    plan.activities = chosen
    plan.minutes = sum(a.effective_minutes for a in chosen)
    plan.notes.append(
        "برنامهٔ حداقلی روز دشوار: بدون جریمه، بدون مطلب جدید سنگین. "
        "این روز در آمار «روز حداقلی» ثبت می‌شود، نه «روز شکست»."
    )
    if not chosen:
        plan.notes.append("کار ضروری با مهلت نزدیک یافت نشد؛ برنامه خالی است.")
    return plan


@dataclass
class TriageList:
    """فهرست سه‌بخشی بحران بدهی (BL-03)."""

    must_do: list[Activity] = field(default_factory=list)
    if_possible: list[Activity] = field(default_factory=list)
    suggest_drop: list[Activity] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def build_triage(
    *,
    activities: Sequence[Activity],
    date: _dt.date,
    capacity_minutes: int,
    settings: Optional[Settings] = None,
) -> TriageList:
    """در وضعیت بحرانی: «حتماً / اگر شد / پیشنهاد حذف»."""
    settings = settings or Settings()
    triage = TriageList()

    pending = [
        a
        for a in activities
        if a.state not in {ActivityState.DONE, ActivityState.DROPPED, ActivityState.EXPIRED}
    ]

    def sort_key(activity: Activity) -> tuple:
        days = (
            (activity.deadline_at.date() - date).days if activity.deadline_at else 999
        )
        return (days, -activity.effective_minutes)

    pending.sort(key=sort_key)

    must_do: list[Activity] = []
    if_possible: list[Activity] = []
    suggest_drop: list[Activity] = []

    budget = max(0, int(capacity_minutes * settings.backlog.compensation_cap_ratio))
    used = 0

    for activity in pending:
        if activity.deadline_type.value == "hard":
            must_do.append(activity)
            used += activity.effective_minutes
        elif activity.deadline_at is not None and (activity.deadline_at.date() - date).days <= 2:
            must_do.append(activity)
            used += activity.effective_minutes
        elif activity.deadline_at is None:
            suggest_drop.append(activity)
        else:
            if_possible.append(activity)

    for activity in list(if_possible):
        if used + activity.effective_minutes <= budget:
            must_do.append(activity)
            used += activity.effective_minutes
            if_possible.remove(activity)

    triage.must_do = must_do
    triage.if_possible = if_possible
    triage.suggest_drop = suggest_drop
    triage.notes.append(
        "هیچ فعالیتی بدون تأیید شما حذف نمی‌شود؛ این فهرست فقط پیشنهاد است."
    )
    return triage


def return_after_break(
    *,
    date: _dt.date,
    last_active_date: Optional[_dt.date],
    normal_capacity_minutes: int,
    settings: Optional[Settings] = None,
) -> tuple[int, list[str]]:
    """بازگشت تدریجی پس از وقفهٔ چندروزه (BL-04، سند ۲، بخش ۱۱.۷).

    خروجی: (ظرفیت پیشنهادی امروز، یادداشت‌ها).
    """
    settings = settings or Settings()
    b = settings.backlog
    if last_active_date is None:
        return normal_capacity_minutes, []
    gap = (date - last_active_date).days
    if gap < b.break_threshold_days:
        return normal_capacity_minutes, []

    capacity = int(normal_capacity_minutes * b.return_load_ratio)
    notes = [
        f"{gap} روز وقفه ثبت شده است؛ بار امروز به {int(b.return_load_ratio * 100)}٪ "
        "ظرفیت معمول محدود شد.",
        "صف مرور به‌جای تخلیهٔ یک‌باره، طی چند روز پخش می‌شود و "
        "ابتدا یک آزمون نمونه‌ای ماندگاری پیشنهاد می‌شود.",
        "هیچ جریمه‌ای برای وقفه ثبت نمی‌شود؛ گزارش بدهی خنثی است.",
    ]
    return capacity, notes


def plan_summary(day_plan: DayPlan) -> str:
    """خلاصهٔ متنی برنامهٔ روز."""
    from .jdate import format_minutes

    return (
        f"ظرفیت {format_minutes(day_plan.capacity_minutes)} — "
        f"برنامه {format_minutes(day_plan.planned_minutes)} — "
        f"حاشیهٔ آزاد {format_minutes(day_plan.margin_minutes)}"
    )
