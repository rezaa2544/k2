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


def test_past_master_deadline_still_offers_the_four_actions():
    """مهلت گذشته هم باید چهار راه بدهد، نه فقط یک هشدار.

    پیش‌تر مسیر «مهلت در گذشته» زودهنگام return می‌شد و هیچ پیشنهادی ساخته
    نمی‌شد؛ کاربر می‌دید که مهلت گذشته است ولی هیچ اقدامی برایش پیشنهاد
    نمی‌شد.
    """
    plan = back_calculate(_input(consolidation_date=TODAY - _dt.timedelta(days=3)))
    actions = {s.action for s in plan.suggestions}
    assert actions == {
        FeasibilityAction.MORE_TIME,
        FeasibilityAction.LESS_VOLUME,
        FeasibilityAction.REPRIORITIZE,
        FeasibilityAction.MOVE_DEADLINE,
    }
    assert plan.overload_minutes > 0
    assert any(s.shift_days > 0 for s in plan.suggestions)
    assert "گذشته" in plan.warnings[0]


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


# ---------------------------------------------------------------------------
# هدف فصل: «تا تاریخ فلانی فصل X تمام شود»
# ---------------------------------------------------------------------------


def _today() -> _dt.date:
    return _dt.date(2026, 10, 27)


def test_chapter_goal_counts_every_section_and_is_feasible_when_there_is_time():
    from k2.chapter_goal import ChapterGoalInput, plan_chapter_goal

    plan = plan_chapter_goal(ChapterGoalInput(
        subject="زیست‌شناسی", grade=11, chapter=1,
        deadline=_today() + _dt.timedelta(days=90),
        daily_capacity_minutes=120,
        section_count=7, open_section_count=7, today=_today(),
    ))
    assert plan.feasible
    assert plan.section_count == 7
    assert plan.open_section_count == 7
    assert plan.total_minutes == plan.minutes_per_section * 7
    assert plan.available_days >= plan.required_days
    assert plan.per_day, "تقسیم روزانه باید ساخته شود"
    assert sum(day.minutes for day in plan.per_day) == plan.total_minutes


def test_chapter_goal_is_honest_when_the_deadline_is_too_close():
    """مهلت نزدیک ⇒ تاریخ جعلی ساخته نمی‌شود، کمبود روز گفته می‌شود."""
    from k2.chapter_goal import ChapterGoalInput, plan_chapter_goal

    plan = plan_chapter_goal(ChapterGoalInput(
        subject="زیست‌شناسی", grade=11, chapter=1,
        deadline=_today() + _dt.timedelta(days=2),
        daily_capacity_minutes=60,
        section_count=7, open_section_count=7, today=_today(),
    ))
    assert not plan.feasible
    assert plan.missing_days > 0
    assert any("کم داری" in w for w in plan.warnings)
    assert not plan.per_day


def test_chapter_goal_can_count_only_open_needs():
    from k2.chapter_goal import ChapterGoalInput, plan_chapter_goal

    plan = plan_chapter_goal(ChapterGoalInput(
        subject="زیست‌شناسی", grade=11, chapter=1,
        deadline=_today() + _dt.timedelta(days=30),
        daily_capacity_minutes=120,
        only_open_needs=True,
        section_count=7, open_section_count=2, today=_today(),
    ))
    assert plan.open_section_count == 2
    assert plan.total_minutes == plan.minutes_per_section * 2


def test_chapter_goal_without_open_sections_says_so():
    from k2.chapter_goal import ChapterGoalInput, plan_chapter_goal

    plan = plan_chapter_goal(ChapterGoalInput(
        subject="زیست‌شناسی", grade=11, chapter=1,
        deadline=_today() + _dt.timedelta(days=30),
        daily_capacity_minutes=120,
        only_open_needs=True,
        section_count=7, open_section_count=0, today=_today(),
    ))
    assert not plan.feasible
    assert any("گفتارِ بازِ شمارش‌شدنی نیست" in w for w in plan.warnings)


def test_chapter_goal_without_a_deadline_does_not_invent_dates():
    from k2.chapter_goal import ChapterGoalInput, plan_chapter_goal

    plan = plan_chapter_goal(ChapterGoalInput(
        subject="زیست‌شناسی", grade=11, chapter=1,
        deadline=None, daily_capacity_minutes=120,
        section_count=7, open_section_count=7, today=_today(),
    ))
    assert not plan.feasible
    assert not plan.milestones
    assert not plan.per_day


def test_chapter_goal_back_calculates_from_the_chapter_volume():
    """تاریخ شروع باید از حجمِ *کل فصل* بیاید، نه از حجم یک گفتار."""
    from k2.chapter_goal import ChapterGoalInput, plan_chapter_goal

    deadline = _today() + _dt.timedelta(days=30)
    small = plan_chapter_goal(ChapterGoalInput(
        subject="زیست‌شناسی", grade=11, chapter=1,
        deadline=deadline, daily_capacity_minutes=120,
        section_count=7, open_section_count=1, today=_today(),
    ))
    large = plan_chapter_goal(ChapterGoalInput(
        subject="زیست‌شناسی", grade=11, chapter=1,
        deadline=deadline, daily_capacity_minutes=120,
        section_count=7, open_section_count=7, today=_today(),
    ))
    assert large.milestones[-1].date < small.milestones[-1].date


def test_chapter_goal_zero_capacity_is_refused():
    from k2.chapter_goal import ChapterGoalInput, plan_chapter_goal

    plan = plan_chapter_goal(ChapterGoalInput(
        subject="زیست‌شناسی", grade=11, chapter=1,
        deadline=_today() + _dt.timedelta(days=30),
        daily_capacity_minutes=0,
        section_count=7, open_section_count=7, today=_today(),
    ))
    assert not plan.feasible
    assert any("ظرفیت روزانه" in w for w in plan.warnings)
