"""ماشین حالت فعالیت و قواعد گذار (سند تحقیق ۲، بخش ۵).

گذارهای غیرمجاز **رد** می‌شوند و فعالیت هرگز بی‌صدا حذف نمی‌شود.
"""

from __future__ import annotations

from .enums import ActivityState

#: جدول گذارهای مجاز. هر کلید وضعیت مبدأ و هر مقدار مجموعهٔ وضعیت‌های مقصد.
ALLOWED_TRANSITIONS: dict[ActivityState, frozenset[ActivityState]] = {
    ActivityState.PLANNED: frozenset(
        {
            ActivityState.READY,
            ActivityState.BLOCKED,
            ActivityState.DEFERRED,
            ActivityState.EXPIRED,
            ActivityState.DROPPED,
            ActivityState.OVERDUE,
            # کاری که بیرون از برنامه انجام شده، بدون نیاز به «شروع» ثبت می‌شود.
            ActivityState.DONE,
        }
    ),
    ActivityState.READY: frozenset(
        {
            ActivityState.IN_PROGRESS,
            ActivityState.BLOCKED,
            ActivityState.DEFERRED,
            ActivityState.EXPIRED,
            ActivityState.DROPPED,
            ActivityState.OVERDUE,
            ActivityState.DONE,
        }
    ),
    ActivityState.BLOCKED: frozenset(
        {
            ActivityState.READY,
            ActivityState.DEFERRED,
            ActivityState.EXPIRED,
            ActivityState.DROPPED,
            ActivityState.OVERDUE,
        }
    ),
    ActivityState.IN_PROGRESS: frozenset(
        {
            ActivityState.DONE,
            ActivityState.PARTIAL,
            ActivityState.DEFERRED,
            ActivityState.OVERDUE,
        }
    ),
    ActivityState.PARTIAL: frozenset(
        {
            ActivityState.READY,
            ActivityState.IN_PROGRESS,
            # فعالیت نیمه‌تمام می‌تواند بعداً کامل شود (مثلاً ادامهٔ ویدئوی ضبط‌شده).
            ActivityState.DONE,
            ActivityState.DEFERRED,
            ActivityState.DROPPED,
            ActivityState.OVERDUE,
        }
    ),
    ActivityState.OVERDUE: frozenset(
        {
            ActivityState.READY,
            ActivityState.DEFERRED,
            ActivityState.EXPIRED,
            ActivityState.DROPPED,
        }
    ),
    ActivityState.DEFERRED: frozenset(
        {
            ActivityState.READY,
            ActivityState.PLANNED,
            ActivityState.EXPIRED,
            ActivityState.DROPPED,
        }
    ),
    ActivityState.DONE: frozenset(),
    ActivityState.EXPIRED: frozenset(),
    ActivityState.DROPPED: frozenset(),
}

#: وضعیت‌های پایانی.
TERMINAL_STATES: frozenset[ActivityState] = frozenset(
    {ActivityState.DONE, ActivityState.EXPIRED, ActivityState.DROPPED}
)

#: وضعیت‌هایی که فعالیت در آن‌ها «هنوز باید انجام شود».
ACTIVE_STATES: frozenset[ActivityState] = frozenset(
    {
        ActivityState.PLANNED,
        ActivityState.READY,
        ActivityState.BLOCKED,
        ActivityState.IN_PROGRESS,
        ActivityState.PARTIAL,
        ActivityState.OVERDUE,
        ActivityState.DEFERRED,
    }
)


class InvalidTransition(ValueError):
    """وقتی گذار درخواستی مجاز نیست."""

    def __init__(self, source: ActivityState, target: ActivityState):
        self.source = source
        self.target = target
        super().__init__(
            f"گذار از «{source.label}» به «{target.label}» مجاز نیست."
        )


def can_transition(source: ActivityState, target: ActivityState) -> bool:
    """آیا گذار ``source`` → ``target`` مجاز است؟"""
    if source == target:
        return True
    return target in ALLOWED_TRANSITIONS.get(source, frozenset())


def validate_transition(source: ActivityState, target: ActivityState) -> None:
    """گذار را بررسی می‌کند و در صورت نامعتبر بودن استثنا می‌دهد.

    Raises:
        InvalidTransition: اگر گذار مجاز نباشد.
    """
    if not can_transition(source, target):
        raise InvalidTransition(source, target)


def next_states(source: ActivityState) -> frozenset[ActivityState]:
    """گذارهای مجاز از یک وضعیت."""
    return ALLOWED_TRANSITIONS.get(source, frozenset())


def is_active(state: ActivityState) -> bool:
    """آیا فعالیت هنوز باید انجام شود؟"""
    return state in ACTIVE_STATES


def is_terminal(state: ActivityState) -> bool:
    return state in TERMINAL_STATES
