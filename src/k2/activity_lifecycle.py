"""چرخهٔ حیات فعالیت: شروع، اتمام ناقص، تعویق، انقضا و عقب‌افتادگی.

قواعد (سند تحقیق ۲، بخش ۵ و ۱۱):
  * گذارهای غیرمجاز **رد** می‌شوند.
  * فعالیت ناقص، **زمان باقی‌مانده** و **نقطهٔ توقف** را حفظ می‌کند.
  * حذف/تعویق/انقضا بدون ثبت دلیل انجام نمی‌شود.
  * فعالیت وابسته تا تکمیل پیش‌نیاز `Blocked` می‌ماند.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from .config import Settings
from .domain.enums import ActivityState
from .domain.models import Activity
from .domain.state_machine import validate_transition

#: حداقل زمان باقی‌مانده برای یک فعالیت ناقص (دقیقه) [H].
MIN_REMAINING = 10


class LifecycleError(RuntimeError):
    """خطا در چرخهٔ حیات فعالیت."""


@dataclass
class CompletionOutcome:
    """نتیجهٔ ثبت اتمام یا اتمام ناقص."""

    activity: Activity
    from_state: ActivityState
    to_state: ActivityState
    remaining_minutes: int
    message: str = ""


def start_activity(activity: Activity) -> ActivityState:
    """شروع فعالیت.

    فعالیتی که هنوز «برنامه‌ریزی‌شده» است، ابتدا به «آماده» و سپس به
    «در حال انجام» می‌رود. فعالیتِ مسدود (پیش‌نیازِ انجام‌نشده) اجازهٔ شروع
    ندارد.
    """
    if activity.state == ActivityState.PLANNED:
        validate_transition(activity.state, ActivityState.READY)
        activity.state = ActivityState.READY
    validate_transition(activity.state, ActivityState.IN_PROGRESS)
    activity.state = ActivityState.IN_PROGRESS
    activity.state_reason = "در حال انجام"
    return activity.state


def complete_activity(
    activity: Activity,
    *,
    actual_minutes: int,
    settings: Optional[Settings] = None,
) -> CompletionOutcome:
    """اتمام کامل فعالیت."""
    settings = settings or Settings()
    source = activity.state
    validate_transition(source, ActivityState.DONE)
    activity.actual_minutes += max(0, actual_minutes)
    activity.remaining_minutes = 0
    activity.state = ActivityState.DONE
    activity.state_reason = "انجام‌شده"
    return CompletionOutcome(
        activity=activity,
        from_state=source,
        to_state=ActivityState.DONE,
        remaining_minutes=0,
        message="فعالیت انجام شد.",
    )


def partial_activity(
    activity: Activity,
    *,
    actual_minutes: int,
    resume_marker: Optional[int] = None,
    settings: Optional[Settings] = None,
) -> CompletionOutcome:
    """ثبت اتمام ناقص؛ باقی‌مانده حفظ می‌شود.

    باقی‌مانده = max(برآورد × ضریب کالیبراسیون − زمان واقعی، حداقل ۱۰ دقیقه).
    """
    settings = settings or Settings()
    source = activity.state
    validate_transition(source, ActivityState.PARTIAL)

    added = max(0, actual_minutes)
    activity.actual_minutes += added
    if resume_marker is not None:
        activity.resume_marker = resume_marker

    ratio = settings.advisor.calibration_default_ratio
    expected = activity.est_minutes * ratio
    remaining = max(MIN_REMAINING, int(round(expected - activity.actual_minutes)))
    if activity.remaining_minutes > 0:
        # اگر قبلاً باقی‌مانده‌ای ثبت شده بود، کمتر از آن نگه می‌داریم.
        remaining = min(remaining, activity.remaining_minutes) if activity.actual_minutes else remaining

    activity.remaining_minutes = remaining
    activity.state = ActivityState.PARTIAL
    activity.state_reason = "ناقص"
    return CompletionOutcome(
        activity=activity,
        from_state=source,
        to_state=ActivityState.PARTIAL,
        remaining_minutes=remaining,
        message=(
            f"فعالیت ناقص ثبت شد؛ {remaining} دقیقهٔ دیگر باقی مانده است و "
            "در برنامهٔ بعدی ادامه می‌یابد."
        ),
    )


def defer_activity(activity: Activity, *, reason: str) -> ActivityState:
    """تعویق آگاهانه با ثبت دلیل."""
    if not reason:
        raise LifecycleError("برای تعویق فعالیت باید دلیل ثبت شود.")
    validate_transition(activity.state, ActivityState.DEFERRED)
    activity.state = ActivityState.DEFERRED
    activity.state_reason = reason
    return activity.state


def drop_activity(activity: Activity, *, reason: str) -> ActivityState:
    """حذف آگاهانه با ثبت دلیل."""
    if not reason:
        raise LifecycleError("برای حذف فعالیت باید دلیل ثبت شود.")
    validate_transition(activity.state, ActivityState.DROPPED)
    activity.state = ActivityState.DROPPED
    activity.state_reason = reason
    return activity.state


def expire_activity(activity: Activity, *, reason: str) -> ActivityState:
    """انقضا با ثبت دلیل (پیشنهاد می‌شود، خودکار اعمال نمی‌شود)."""
    if not reason:
        raise LifecycleError("برای انقضای فعالیت باید دلیل ثبت شود.")
    validate_transition(activity.state, ActivityState.EXPIRED)
    activity.state = ActivityState.EXPIRED
    activity.state_reason = reason
    return activity.state


def refresh_dependency_states(activities: Sequence[Activity]) -> list[tuple[Activity, ActivityState]]:
    """وضعیت `Blocked`/`Ready` را بر اساس پیش‌نیازها بازمحاسبه می‌کند.

    فعالیت وابسته تا وقتی همهٔ پیش‌نیازها `Done` نشده‌اند، `Blocked` می‌ماند.
    """
    by_id = {a.id: a for a in activities if a.id is not None}
    changed: list[tuple[Activity, ActivityState]] = []

    for activity in activities:
        if activity.state in {
            ActivityState.DONE,
            ActivityState.DROPPED,
            ActivityState.EXPIRED,
            ActivityState.IN_PROGRESS,
        }:
            continue
        if not activity.depends_on:
            continue

        pending = [
            by_id[dep]
            for dep in activity.depends_on
            if dep in by_id and by_id[dep].state != ActivityState.DONE
        ]
        blocked_dependents = len(pending)

        if pending and activity.state != ActivityState.BLOCKED:
            try:
                validate_transition(activity.state, ActivityState.BLOCKED)
            except ValueError:
                continue
            activity.state = ActivityState.BLOCKED
            activity.state_reason = (
                "منتظر تکمیل پیش‌نیاز: " + "، ".join(p.title for p in pending)
            )
            changed.append((activity, ActivityState.BLOCKED))
        elif not pending and activity.state == ActivityState.BLOCKED:
            try:
                validate_transition(activity.state, ActivityState.READY)
            except ValueError:
                continue
            activity.state = ActivityState.READY
            activity.state_reason = "همهٔ پیش‌نیازها تکمیل شد"
            changed.append((activity, ActivityState.READY))

        activity.blocked_dependents = blocked_dependents

    return changed


def mark_overdue(activities: Sequence[Activity], today: _dt.date) -> list[Activity]:
    """فعالیت‌های گذشته از مهلت را `Overdue` می‌کند."""
    overdue: list[Activity] = []
    for activity in activities:
        if activity.deadline_at is None:
            continue
        if activity.state in {
            ActivityState.DONE,
            ActivityState.DROPPED,
            ActivityState.EXPIRED,
            ActivityState.DEFERRED,
        }:
            continue
        if activity.deadline_at.date() < today:
            try:
                validate_transition(activity.state, ActivityState.OVERDUE)
            except ValueError:
                continue
            activity.state = ActivityState.OVERDUE
            activity.state_reason = "مهلت این فعالیت گذشته است."
            overdue.append(activity)
    return overdue


def count_blocked_dependents(activities: Sequence[Activity]) -> dict[int, int]:
    """تعداد فعالیت‌های مسدودشده‌ای که به هر فعالیت وابسته‌اند."""
    counts: dict[int, int] = {}
    for activity in activities:
        if activity.state != ActivityState.BLOCKED:
            continue
        for dependency in activity.depends_on:
            counts[dependency] = counts.get(dependency, 0) + 1
    return counts
