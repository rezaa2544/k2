"""تست ماشین حالت فعالیت (ACT-02/ACT-03/ACT-04)."""

from __future__ import annotations

import datetime as _dt

import pytest

from k2.activity_lifecycle import (
    LifecycleError,
    complete_activity,
    count_blocked_dependents,
    defer_activity,
    drop_activity,
    expire_activity,
    mark_overdue,
    partial_activity,
    refresh_dependency_states,
    start_activity,
)
from k2.domain.enums import ActivityState
from k2.domain.state_machine import (
    ALLOWED_TRANSITIONS,
    TERMINAL_STATES,
    InvalidTransition,
    can_transition,
    is_active,
    is_terminal,
    next_states,
    validate_transition,
)

from .conftest import make_activity


def test_every_state_has_a_transition_entry():
    for state in ActivityState:
        assert state in ALLOWED_TRANSITIONS


def test_terminal_states_have_no_outgoing_transitions():
    for state in TERMINAL_STATES:
        assert ALLOWED_TRANSITIONS[state] == frozenset()
        assert is_terminal(state)
        assert not is_active(state)


def test_valid_transitions():
    assert can_transition(ActivityState.PLANNED, ActivityState.READY)
    assert can_transition(ActivityState.READY, ActivityState.IN_PROGRESS)
    assert can_transition(ActivityState.IN_PROGRESS, ActivityState.DONE)
    assert can_transition(ActivityState.IN_PROGRESS, ActivityState.PARTIAL)
    assert can_transition(ActivityState.PARTIAL, ActivityState.READY)
    assert can_transition(ActivityState.BLOCKED, ActivityState.READY)


def test_invalid_transition_raises():
    with pytest.raises(InvalidTransition):
        validate_transition(ActivityState.DONE, ActivityState.IN_PROGRESS)
    with pytest.raises(InvalidTransition):
        validate_transition(ActivityState.DONE, ActivityState.READY)


def test_next_states_helper():
    assert ActivityState.IN_PROGRESS in next_states(ActivityState.READY)
    assert next_states(ActivityState.DONE) == frozenset()


def test_start_and_complete_activity():
    activity = make_activity(1, minutes=60)
    start_activity(activity)
    assert activity.state == ActivityState.IN_PROGRESS
    outcome = complete_activity(activity, actual_minutes=55)
    assert outcome.to_state == ActivityState.DONE
    assert activity.actual_minutes == 55
    assert activity.remaining_minutes == 0


def test_partial_activity_keeps_remaining_and_marker():
    activity = make_activity(1, minutes=120)
    start_activity(activity)
    outcome = partial_activity(activity, actual_minutes=30, resume_marker=1234)
    assert outcome.to_state == ActivityState.PARTIAL
    assert outcome.remaining_minutes > 0
    assert activity.remaining_minutes == outcome.remaining_minutes
    assert activity.resume_marker == 1234
    assert activity.actual_minutes == 30


def test_defer_and_drop_require_reason():
    activity = make_activity(1)
    with pytest.raises(LifecycleError):
        defer_activity(activity, reason="")
    with pytest.raises(LifecycleError):
        drop_activity(activity, reason="")
    with pytest.raises(LifecycleError):
        expire_activity(activity, reason="")


def test_defer_records_reason():
    activity = make_activity(1)
    defer_activity(activity, reason="کم‌انرژی")
    assert activity.state == ActivityState.DEFERRED
    assert activity.state_reason == "کم‌انرژی"


def test_drop_from_done_is_rejected():
    activity = make_activity(1)
    complete_activity(activity, actual_minutes=10)
    with pytest.raises(InvalidTransition):
        drop_activity(activity, reason="نظرم عوض شد")


def test_dependency_blocks_until_prerequisite_done():
    first = make_activity(1, "کلاس", state=ActivityState.READY)
    second = make_activity(2, "پردازش", depends_on=(1,), state=ActivityState.READY)
    changed = refresh_dependency_states([first, second])
    assert second.state == ActivityState.BLOCKED
    assert any(a.id == 2 for a, _ in changed)

    first.state = ActivityState.DONE
    refresh_dependency_states([first, second])
    assert second.state == ActivityState.READY


def test_count_blocked_dependents():
    first = make_activity(1, state=ActivityState.READY)
    second = make_activity(2, depends_on=(1,), state=ActivityState.BLOCKED)
    third = make_activity(3, depends_on=(1,), state=ActivityState.BLOCKED)
    refresh_dependency_states([first, second, third])
    counts = count_blocked_dependents([first, second, third])
    assert counts.get(1) == 2


def test_mark_overdue_skips_terminal_and_future():
    past = make_activity(1)
    past.deadline_at = _dt.datetime(2026, 1, 1, 12, 0)
    future = make_activity(2)
    future.deadline_at = _dt.datetime(2027, 1, 1, 12, 0)
    done = make_activity(3, state=ActivityState.DONE)
    done.deadline_at = _dt.datetime(2026, 1, 1, 12, 0)
    overdue = mark_overdue([past, future, done], _dt.date(2026, 6, 1))
    assert [a.id for a in overdue] == [1]
    assert past.state == ActivityState.OVERDUE
    assert future.state == ActivityState.READY
    assert done.state == ActivityState.DONE
