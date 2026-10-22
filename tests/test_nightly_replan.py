"""تست‌های بازبینی شبانه و بازسازی برنامه (بند ۱۶)."""

from __future__ import annotations

import datetime as _dt

from k2.config import Settings
from k2.domain.enums import ActivityState, ActivityType, DeadlineType
from k2.domain.models import (
    Activity,
    DayPlan,
    LearningProblem,
    Placement,
    ProblemStatus,
    StudySession,
    TopicDeadlinePlan,
    DeadlineSuggestion,
)
from k2.domain.enums import FeasibilityAction
from k2.nightly_replan import (
    ReplanReport,
    assessment_minutes_of,
    classify_day,
    deadline_risk_notes,
    independent_minutes_of,
    replan_forward,
    summarize_review,
)

TODAY = _dt.date(2026, 10, 23)


def _activity(**kwargs) -> Activity:
    defaults = dict(
        id=1,
        title="کار آزمون",
        type=ActivityType.INDEPENDENT_PRACTICE,
        est_minutes=60,
        actual_minutes=0,
        remaining_minutes=0,
        max_chunk=90,
        min_chunk=20,
    )
    defaults.update(kwargs)
    return Activity(**defaults)


def _plan(**kwargs) -> DayPlan:
    defaults = dict(
        date=TODAY,
        placements=[],
        unplaced=[],
        capacity_minutes=180,
        raw_minutes=200,
        effective_minutes=180,
        planned_minutes=180,
        free_minutes=0,
        notes=[],
    )
    defaults.update(kwargs)
    return DayPlan(**defaults)


def _placement(activity_id: int, title: str, minutes: int = 60) -> Placement:
    return Placement(
        activity_id=activity_id,
        title=title,
        date=TODAY,
        start_minute=600,
        end_minute=600 + minutes,
        minutes=minutes,
    )


def test_classify_day_separates_class_from_independent_study():
    plan = _plan(
        placements=[_placement(1, "کلاس شیمی"), _placement(2, "تمرین ریاضی")],
        planned_minutes=180,
    )
    activities = [
        _activity(id=1, title="کلاس شیمی", type=ActivityType.LIVE_CLASS,
                  state=ActivityState.DONE, actual_minutes=90, est_minutes=90),
        _activity(id=2, title="تمرین ریاضی", state=ActivityState.DONE,
                  actual_minutes=60, est_minutes=90),
    ]
    sessions = [
        StudySession(kind=type("K", (), {"value": "live_class"})(), minutes=90,
                     started_at=_dt.datetime(2026, 10, 23, 9)),
        StudySession(kind=type("K", (), {"value": "study"})(), minutes=60,
                     started_at=_dt.datetime(2026, 10, 23, 11)),
    ]
    review = classify_day(plan, activities, sessions)
    assert review.class_minutes == 90
    assert review.independent_minutes == 60
    assert review.done_minutes == 150
    assert len(review.completed) == 2


def test_classify_day_lists_incomplete_work_with_reason():
    plan = _plan(placements=[_placement(1, "تمرین سخت")], planned_minutes=120)
    activities = [
        _activity(
            id=1,
            title="تمرین سخت",
            state=ActivityState.PARTIAL,
            state_reason="وقت کم آورد",
            actual_minutes=30,
            est_minutes=90,
            remaining_minutes=60,
        )
    ]
    review = classify_day(plan, activities, [])
    assert review.incomplete
    assert "وقت کم آورد" in review.incomplete[0]


def test_classify_day_flags_capacity_risk_when_plan_exceeds_capacity():
    plan = _plan(
        planned_minutes=260,
        capacity_minutes=180,
        unplaced=[],
    )
    assert plan.is_over_capacity is True
    review = classify_day(plan, [], [])
    assert review.capacity_risks


def test_classify_day_detects_better_and_worse_than_estimated():
    plan = _plan(placements=[_placement(1, "سریع"), _placement(2, "کند")])
    activities = [
        _activity(id=1, title="سریع", state=ActivityState.DONE,
                  est_minutes=90, actual_minutes=60),
        _activity(id=2, title="کند", state=ActivityState.DONE,
                  est_minutes=60, actual_minutes=95),
    ]
    review = classify_day(plan, activities, [])
    assert any("سریع‌تر" in item for item in review.better)
    assert any("کندتر" in item for item in review.worse)


def test_replan_forward_does_not_blindly_roll_over():
    """کار ناقص با سنجش اهمیت/فوریت توزیع می‌شود، نه کورکورانه به فردا."""
    activities = [
        _activity(id=1, title="مهم و فوری", state=ActivityState.PARTIAL,
                  remaining_minutes=60, actual_minutes=30),
        _activity(id=2, title="کم‌اهمیت", state=ActivityState.OVERDUE,
                  remaining_minutes=45, type=ActivityType.HOMEWORK),
    ]
    plans = [
        _plan(date=TODAY, capacity_minutes=180, planned_minutes=180, free_minutes=0),
        _plan(date=TODAY + _dt.timedelta(days=1), capacity_minutes=180,
              planned_minutes=60, free_minutes=120),
    ]
    report = replan_forward(
        activities=activities,
        day_plans=plans,
        today=TODAY,
        settings=Settings(),
        scores={1: 10.0, 2: 1.0},
    )
    assert report.decisions
    actions = {d.action for d in report.decisions}
    assert "rollover" in actions or "redistribute" in actions
    assert report.redistributed_minutes > 0
    assert all(d.reason for d in report.decisions)


def test_replan_forward_protects_hard_deadline_work():
    """کار با مهلت سخت اگر جا نشود، حذف بی‌صدای نمی‌شود."""
    activities = [
        _activity(id=1, title="مهلت سخت", state=ActivityState.PARTIAL,
                  deadline_type=DeadlineType.HARD, remaining_minutes=200,
                  max_chunk=90),
    ]
    plans = [_plan(date=TODAY + _dt.timedelta(days=i), capacity_minutes=60,
                   planned_minutes=60, free_minutes=0) for i in range(1, 4)]
    report = replan_forward(
        activities=activities, day_plans=plans, today=TODAY,
        settings=Settings(), scores={1: 5.0},
    )
    assert report.changes
    assert report.changes[0].severity in {"warning", "critical"}
    assert report.changes[0].deadline_impact


def test_replan_forward_keeps_fixed_classes_untouched():
    """کلاس‌های ثابت هرگز جابه‌جا نمی‌شوند."""
    plans = [
        _plan(date=TODAY + _dt.timedelta(days=i), capacity_minutes=180,
              planned_minutes=120, free_minutes=60, notes=["کلاس ثبت‌شده"])
        for i in range(1, 4)
    ]
    activities = [
        _activity(id=1, title="کلاس حضوری", type=ActivityType.LIVE_CLASS,
                  state=ActivityState.PARTIAL, remaining_minutes=90),
    ]
    report = replan_forward(
        activities=activities, day_plans=plans, today=TODAY, settings=Settings()
    )
    assert report.fixed_preserved == 3


def test_deadline_risk_notes_flags_infeasible_and_near_deadlines():
    infeasible = TopicDeadlinePlan(
        topic_id=1, topic_name="احتمال", feasible=False,
        total_minutes=600, capacity_minutes_per_day=180, available_days=2,
    )
    near = TopicDeadlinePlan(
        topic_id=2, topic_name="هندسه", feasible=True,
        total_minutes=500, capacity_minutes_per_day=180, available_days=2,
    )
    from k2.domain.enums import DeadlineKind
    from k2.domain.models import DeadlineMilestone

    near.milestones = [
        DeadlineMilestone(kind=DeadlineKind.FINAL_CONSOLIDATION,
                          label="تثبیت نهایی",
                          date=TODAY + _dt.timedelta(days=3))
    ]
    notes = deadline_risk_notes([infeasible, near], today=TODAY, warning_window_days=7)
    assert any("احتمال" in n for n in notes)
    assert any("هندسه" in n for n in notes)


def test_summarize_review_mentions_all_key_sections():
    plan = _plan(planned_minutes=180)
    activities = [_activity(id=1, title="کار", state=ActivityState.PARTIAL,
                            state_reason="خستگی", remaining_minutes=60)]
    review = classify_day(plan, activities, [])
    replan = ReplanReport()
    replan.changes = []
    text = summarize_review(
        review,
        replan,
        deadline_risks=["مهلت ریاضی در خطر است"],
        open_problems=[
            LearningProblem(id=1, title="بی‌دقتی", severity=4,
                            status=ProblemStatus.OPEN)
        ],
    )
    assert "دقیقه" in text
    assert "کلاس" in text
    assert "ریاضی" in text
    assert "بی‌دقتی" in text


def test_independent_and_assessment_minutes_exclude_classes():
    activities = [
        _activity(id=1, type=ActivityType.LIVE_CLASS, est_minutes=90),
        _activity(id=2, type=ActivityType.INDEPENDENT_PRACTICE, est_minutes=60),
        _activity(id=3, type=ActivityType.TIMED_TEST, est_minutes=45),
    ]
    assert independent_minutes_of(activities) == 60
    assert assessment_minutes_of(activities) == 45


def test_suggestion_objects_are_exported_for_the_ui():
    """پیشنهادها باید در رابط کاربری قابل نمایش باشند."""
    plan = TopicDeadlinePlan(topic_id=1, topic_name="شیمی", feasible=False)
    plan.suggestions = [
        DeadlineSuggestion(
            action=FeasibilityAction.MORE_TIME,
            title="مهلت را عقب بکش",
            detail="دو روز کم است",
            shift_days=2,
        )
    ]
    assert plan.suggestions[0].action.label
    assert plan.suggestions[0].shift_days == 2
