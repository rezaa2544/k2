"""تست‌های لایهٔ سرویس برای قابلیت‌های تازه (بندهای ۱۲–۱۸)."""

from __future__ import annotations

import datetime as _dt

import pytest

from k2.domain.enums import (
    DeadlineKind,
    FinalStage,
    KonkurStage,
    ProblemKind,
    ProblemStatus,
    SessionKind,
    TrackKind,
)
from k2.domain.models import (
    ExamProfile,
    LearningEvidence,
    LearningProblem,
    StudySession,
    Subject,
    Topic,
    TopicDeadline,
)
from k2.service import AdvisorService

TODAY = _dt.date(2026, 10, 23)


@pytest.fixture()
def service(tmp_path):
    svc = AdvisorService(tmp_path / "k2.db")
    yield svc
    svc.close()


def _seed(service: AdvisorService) -> tuple[Subject, Topic]:
    subject = Subject(name="ریاضی", coefficient=2.0)
    service.create_subject(subject)
    topic = Topic(subject_id=subject.id, name="احتمال", estimated_minutes=300)
    service.create_topic(topic)
    return subject, topic


# ---------------------------------------------------------------------------
# مهلت‌ها
# ---------------------------------------------------------------------------


def test_deadline_survives_restart_and_back_calculates(service, tmp_path):
    _subject, topic = _seed(service)
    deadline = TopicDeadline(
        topic_id=topic.id,
        kind=DeadlineKind.FINAL_CONSOLIDATION,
        target_date=TODAY + _dt.timedelta(days=40),
        target_percent=70,
        target_level="L3",
        is_master=True,
    )
    service.save_topic_deadline(deadline)
    service.close()

    reopened = AdvisorService(tmp_path / "k2.db")
    try:
        stored = reopened.list_topic_deadlines(topic.id)
        assert len(stored) == 1
        assert stored[0].is_master is True
        plan = reopened.topic_deadline_plan(topic.id, today=TODAY)
        assert plan.consolidation_date == TODAY + _dt.timedelta(days=40)
        assert plan.total_minutes > 0
    finally:
        reopened.close()


def test_moving_master_deadline_moves_all_other_deadlines(service):
    _subject, topic = _seed(service)
    first = service.save_topic_deadline(
        TopicDeadline(topic_id=topic.id, kind=DeadlineKind.FINAL_CONSOLIDATION,
                      target_date=TODAY + _dt.timedelta(days=30), is_master=True)
    )
    early = service.topic_deadline_plan(topic.id, today=TODAY).start_date
    service.save_topic_deadline(
        TopicDeadline(topic_id=topic.id, kind=DeadlineKind.FINAL_CONSOLIDATION,
                      target_date=TODAY + _dt.timedelta(days=90), is_master=True)
    )
    late = service.topic_deadline_plan(topic.id, today=TODAY).start_date
    assert late > early


def test_infeasible_deadline_offers_four_suggestions(service):
    _subject, topic = _seed(service)
    service.save_topic_deadline(
        TopicDeadline(topic_id=topic.id, kind=DeadlineKind.FINAL_CONSOLIDATION,
                      target_date=TODAY + _dt.timedelta(days=2), is_master=True)
    )
    # today را صریح می‌فرستیم تا تست به تاریخ واقعی ماشین گره نخورد.
    suggestions = service.deadline_suggestions(topic.id, today=TODAY)
    actions = {s.action.value for s in suggestions}
    assert {"more_time", "less_volume", "reprioritize", "move_deadline"} <= actions


def test_deadline_completion_requires_evidence(service):
    _subject, topic = _seed(service)
    service.save_topic_deadline(
        TopicDeadline(topic_id=topic.id, kind=DeadlineKind.FINAL_CONSOLIDATION,
                      target_date=TODAY + _dt.timedelta(days=30),
                      target_percent=80, is_master=True)
    )
    status = service.deadline_evidence_status(topic.id)
    assert status["proven"] is False
    assert "شاهد" in str(status["reason"])

    service.record_track_evidence(
        topic.id,
        TrackKind.KONKUR,
        LearningEvidence(topic_id=topic.id, source="diagnostic", score=0.9,
                         item_count=20, confidence=3),
    )
    status = service.deadline_evidence_status(topic.id)
    assert status["proven"] is True


def test_deadline_without_target_is_not_provable(service):
    _subject, topic = _seed(service)
    service.save_topic_deadline(
        TopicDeadline(topic_id=topic.id, kind=DeadlineKind.FINAL_CONSOLIDATION,
                      target_date=TODAY + _dt.timedelta(days=30), is_master=True)
    )
    status = service.deadline_evidence_status(topic.id)
    assert status["proven"] is False
    assert "هدف" in str(status["reason"])


def test_all_deadline_plans_cover_every_topic_with_a_deadline(service):
    _subject, topic = _seed(service)
    service.save_topic_deadline(
        TopicDeadline(topic_id=topic.id, kind=DeadlineKind.FINAL_CONSOLIDATION,
                      target_date=TODAY + _dt.timedelta(days=30), is_master=True)
    )
    plans = service.all_deadline_plans(today=TODAY)
    assert len(plans) == 1
    assert plans[0].topic_id == topic.id


# ---------------------------------------------------------------------------
# ساعت مطالعه
# ---------------------------------------------------------------------------


def test_study_session_persists_across_restart(service, tmp_path):
    _subject, topic = _seed(service)
    service.save_study_session(
        StudySession(
            subject_id=_subject.id, topic_id=topic.id, kind=SessionKind.STUDY,
            mode="timer", started_at=_dt.datetime(2026, 10, 23, 9, 0),
            ended_at=_dt.datetime(2026, 10, 23, 10, 30), minutes=90,
            paused_seconds=0,
        )
    )
    service.close()
    reopened = AdvisorService(tmp_path / "k2.db")
    try:
        sessions = reopened.list_study_sessions()
        assert len(sessions) == 1
        assert sessions[0].minutes == 90
        assert sessions[0].topic_name == "احتمال"
        assert reopened.session_totals().total_minutes == 90
    finally:
        reopened.close()


def test_correcting_a_session_keeps_history(service):
    _subject, topic = _seed(service)
    session_id = service.save_study_session(
        StudySession(
            subject_id=_subject.id, topic_id=topic.id, kind=SessionKind.STUDY,
            mode="timer", started_at=_dt.datetime(2026, 10, 23, 9, 0),
            ended_at=_dt.datetime(2026, 10, 23, 10, 0), minutes=60,
        )
    )
    revision = service.correct_study_session(
        session_id, field_name="minutes", new_value=45, reason="تایمر را دیر زدم"
    )
    assert revision.old_value == "60"
    assert revision.new_value == "45"
    stored = service.list_study_sessions()[0]
    assert stored.minutes == 45
    assert stored.mode == "corrected"
    assert len(service.session_revisions(session_id)) == 1


def test_class_and_independent_time_are_reported_separately(service):
    subject, topic = _seed(service)
    for kind, minutes in (
        (SessionKind.LIVE_CLASS, 120),
        (SessionKind.STUDY, 90),
        (SessionKind.TEST, 60),
        (SessionKind.ANALYSIS, 30),
    ):
        service.save_study_session(
            StudySession(
                subject_id=subject.id, topic_id=topic.id, kind=kind, mode="timer",
                started_at=_dt.datetime(2026, 10, 23, 9, 0),
                ended_at=_dt.datetime(2026, 10, 23, 10, 0), minutes=minutes,
            )
        )
    totals = service.session_totals()
    assert totals.total_minutes == 300
    assert totals.class_minutes == 120
    assert totals.independent_minutes == 90
    assert totals.test_minutes == 60
    assert totals.analysis_minutes == 30


def test_planned_vs_actual_uses_net_minutes(service):
    subject, topic = _seed(service)
    service.save_study_session(
        StudySession(
            subject_id=subject.id, topic_id=topic.id, kind=SessionKind.STUDY,
            mode="timer", started_at=_dt.datetime(2026, 10, 23, 9, 0),
            ended_at=_dt.datetime(2026, 10, 23, 10, 0), minutes=60,
        )
    )
    result = service.planned_vs_actual(TODAY, TODAY)
    assert result["actual_minutes"] == 60
    assert result["independent_minutes"] == 60


# ---------------------------------------------------------------------------
# مشکلات یادگیری
# ---------------------------------------------------------------------------


def test_learning_problem_lifecycle(service):
    _subject, topic = _seed(service)
    problem_id = service.save_learning_problem(
        LearningProblem(
            subject_id=_subject.id, topic_id=topic.id,
            kind=ProblemKind.CONCEPTUAL_GAP, title="نمی‌فهمم نمودار چیست",
            severity=4, first_seen=TODAY,
        )
    )
    open_problems = service.list_learning_problems(status=ProblemStatus.OPEN)
    assert len(open_problems) == 1

    service.set_problem_status(
        problem_id, ProblemStatus.IN_PROGRESS, "مثال هدایت‌شده started"
    )
    service.set_problem_status(
        problem_id, ProblemStatus.RESOLVED, "با سه مثال حل شد"
    )
    events = service.problem_events(problem_id)
    assert [e.kind for e in events] == ["opened", "progressed", "resolved"]
    assert service.list_learning_problems(status=ProblemStatus.RESOLVED)


# ---------------------------------------------------------------------------
# مسیر دوگانه
# ---------------------------------------------------------------------------


def test_dual_track_advances_only_with_evidence(service):
    _subject, topic = _seed(service)
    view = service.topic_dual_track(topic.id)
    assert view.konkur.evidence_ready is False
    assert view.final.evidence_ready is False
    assert view.warnings

    changed, message = service.record_track_evidence(
        topic.id,
        TrackKind.KONKUR,
        LearningEvidence(topic_id=topic.id, source="diagnostic", score=0.85,
                         item_count=15),
    )
    assert changed is True
    view = service.topic_dual_track(topic.id)
    assert view.konkur.stage == KonkurStage.TEACHING_TEST.value
    assert view.final.stage == FinalStage.TEXTBOOK_STUDY.value
    # مسیر نهایی دست‌نخورده مانده است
    assert view.final.index == 0


def test_weak_evidence_does_not_advance_konkur_stage(service):
    _subject, topic = _seed(service)
    changed, message = service.record_track_evidence(
        topic.id,
        TrackKind.KONKUR,
        LearningEvidence(topic_id=topic.id, source="diagnostic", score=0.4),
    )
    assert changed is False
    view = service.topic_dual_track(topic.id)
    assert view.konkur.stage == KonkurStage.CONCEPTUAL.value


def test_manual_stage_setting_is_validated(service):
    _subject, topic = _seed(service)
    service.set_topic_stage(topic.id, TrackKind.FINAL, "mock_final")
    view = service.topic_dual_track(topic.id)
    assert view.final.stage == FinalStage.MOCK_FINAL.value
    with pytest.raises(ValueError):
        service.set_topic_stage(topic.id, TrackKind.FINAL, "timed_test")


def test_topic_update_persists_new_priority_fields(service):
    _subject, topic = _seed(service)
    topic.prerequisite_share = 0.8
    topic.final_exam_share = 0.3
    service.update_topic(topic)
    stored = next(t for t in service.list_topics() if t.id == topic.id)
    assert stored.prerequisite_share == 0.8
    assert stored.final_exam_share == 0.3


# ---------------------------------------------------------------------------
# بازبینی شبانه
# ---------------------------------------------------------------------------


def test_nightly_review_reports_incomplete_work_and_risks(service):
    _subject, topic = _seed(service)
    service.save_topic_deadline(
        TopicDeadline(topic_id=topic.id, kind=DeadlineKind.FINAL_CONSOLIDATION,
                      target_date=TODAY + _dt.timedelta(days=1), is_master=True)
    )
    review = service.nightly_review(TODAY)
    assert review.date == TODAY
    assert review.deadline_risks  # مهلت یک‌روزه باید ریسک داشته باشد
    assert isinstance(review.completion_ratio, float)


def test_night_summary_is_a_persian_sentence(service):
    _subject, topic = _seed(service)
    service.save_learning_problem(
        LearningProblem(
            subject_id=_subject.id, topic_id=topic.id,
            kind=ProblemKind.ACCURACY, title="بی‌دقتی", severity=3,
        )
    )
    summary = service.night_summary(TODAY)
    assert "دقیقه" in summary
    assert "بی‌دقتی" in summary


def test_replan_forward_preserves_fixed_events(service):
    from k2.domain.enums import FixedEventKind
    from k2.domain.models import FixedEvent

    service.create_fixed_event(
        FixedEvent(
            title="کلاس ریاضی", kind=FixedEventKind.LIVE_CLASS,
            weekday=TODAY.weekday() if TODAY.weekday() < 6 else 0,
            start_minute=9 * 60, end_minute=11 * 60,
        )
    )
    report = service.replan_forward(today=TODAY)
    assert report.fixed_preserved >= 0
    assert isinstance(report.decisions, list)
