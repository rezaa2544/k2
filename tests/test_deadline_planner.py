"""تست‌های بازمحاسبهٔ مهلت و امکان‌سنجی (بند ۱۲)."""

from __future__ import annotations

import datetime as _dt

import pytest

from k2.deadline_planner import (
    DeadlineInput,
    back_calculate,
    build_suggestions,
    deadline_progress_ratio,
    feasibility_message,
    stage_minutes_for,
)
from k2.domain.enums import DeadlineKind, FeasibilityAction, TrackKind
from k2.domain.models import StudySession, TopicDeadline

TODAY = _dt.date(2026, 10, 23)


def _input(**kwargs) -> DeadlineInput:
    defaults = dict(
        topic_id=1,
        topic_name="احتمال",
        subject_name="ریاضی",
        consolidation_date=_dt.date(2026, 12, 1),
        daily_capacity_minutes=180,
        today=TODAY,
    )
    defaults.update(kwargs)
    return DeadlineInput(**defaults)


def test_back_calculation_orders_milestones_from_consolidation_backwards():
    plan = back_calculate(_input())
    kinds = [m.kind for m in plan.milestones]
    assert kinds == [
        DeadlineKind.FINAL_CONSOLIDATION,
        DeadlineKind.PRACTICE,
        DeadlineKind.INITIAL_LEARNING,
        DeadlineKind.START,
    ]
    dates = [m.date for m in plan.milestones]
    assert dates == sorted(dates, reverse=True)
    assert plan.consolidation_date == _dt.date(2026, 12, 1)
    assert plan.total_minutes == sum(m.minutes for m in plan.milestones)
    assert plan.feasible is True


def test_master_deadline_anchors_every_other_deadline():
    """تغییر مهلت تثبیت نهایی، تاریخ شروع و تمرین را جابه‌جا می‌کند."""
    first = back_calculate(_input(consolidation_date=_dt.date(2026, 12, 1)))
    later = back_calculate(_input(consolidation_date=_dt.date(2027, 1, 15)))
    assert later.start_date > first.start_date
    assert later.consolidation_date == _dt.date(2027, 1, 15)


def test_tight_deadline_is_infeasible_and_reports_overload():
    plan = back_calculate(
        _input(consolidation_date=TODAY + _dt.timedelta(days=2))
    )
    assert plan.feasible is False
    assert plan.overload_minutes > 0
    assert plan.warnings
    assert "عقب" in plan.warnings[0] or "گذشته" in plan.warnings[0]


def test_four_suggestion_types_are_offered():
    plan = back_calculate(_input(consolidation_date=TODAY + _dt.timedelta(days=2)))
    actions = {s.action for s in plan.suggestions}
    assert actions == {
        FeasibilityAction.MORE_TIME,
        FeasibilityAction.LESS_VOLUME,
        FeasibilityAction.REPRIORITIZE,
        FeasibilityAction.MOVE_DEADLINE,
    }
    assert any(s.shift_days > 0 for s in plan.suggestions)


def test_build_suggestions_always_offers_reprioritize_and_move():
    plan = back_calculate(_input())
    plan.feasible = False
    suggestions = build_suggestions(plan, _input())
    actions = {s.action for s in suggestions}
    assert FeasibilityAction.REPRIORITIZE in actions
    assert FeasibilityAction.MOVE_DEADLINE in actions


def test_missing_master_deadline_is_reported_not_guessed():
    plan = back_calculate(_input(consolidation_date=None))
    assert plan.feasible is False
    assert not plan.milestones
    assert plan.warnings
    assert plan.suggestions


def test_past_master_deadline_is_rejected():
    plan = back_calculate(_input(consolidation_date=TODAY - _dt.timedelta(days=3)))
    assert plan.feasible is False
    assert plan.warnings


def test_final_track_requires_more_time_than_konkur_track():
    konkur = stage_minutes_for(DeadlineKind.PRACTICE, track=TrackKind.KONKUR)
    final = stage_minutes_for(DeadlineKind.PRACTICE, track=TrackKind.FINAL)
    assert final > konkur


def test_manual_stage_minutes_override_the_default():
    minutes = stage_minutes_for(
        DeadlineKind.INITIAL_LEARNING, track=TrackKind.KONKUR, override=90
    )
    assert minutes == 90


def test_progress_ratio_counts_only_sessions_before_the_deadline():
    deadline = TopicDeadline(
        id=1,
        topic_id=5,
        kind=DeadlineKind.FINAL_CONSOLIDATION,
        target_date=_dt.date(2026, 11, 1),
    )
    sessions = [
        StudySession(topic_id=5, minutes=30, started_at=_dt.datetime(2026, 10, 20, 9)),
        StudySession(topic_id=5, minutes=45, started_at=_dt.datetime(2026, 10, 25, 9)),
        StudySession(topic_id=5, minutes=60, started_at=_dt.datetime(2026, 11, 5, 9)),
        StudySession(topic_id=7, minutes=99, started_at=_dt.datetime(2026, 10, 25, 9)),
    ]
    assert deadline_progress_ratio(deadline, sessions) == 75


def test_feasibility_message_is_honest_when_overloaded():
    plan = back_calculate(_input(consolidation_date=TODAY + _dt.timedelta(days=2)))
    message = feasibility_message(plan)
    assert "دقیقه" in message
    assert "پیشنهاد" in message


def test_feasibility_message_reports_success():
    message = feasibility_message(back_calculate(_input()))
    assert "شدنی است" in message


def test_zero_capacity_does_not_produce_a_fake_plan():
    plan = back_calculate(_input(daily_capacity_minutes=0))
    assert plan.feasible is False
    assert plan.warnings
    # تاریخ‌ها ساخته می‌شوند ولی هشدار صریح است
    assert plan.overload_minutes > 0


@pytest.mark.parametrize(
    "consolidation,expected_feasible",
    [
        (_dt.date(2026, 12, 20), True),
        (_dt.date(2026, 10, 24), False),
        (_dt.date(2026, 10, 23), False),
    ],
)
def test_feasibility_depends_on_capacity(consolidation, expected_feasible):
    plan = back_calculate(_input(consolidation_date=consolidation))
    assert plan.feasible is expected_feasible
