"""تست‌های مهاجرت و ذخیره‌سازی داده‌های تازه (بندهای ۱۲، ۱۵، ۱۷)."""

from __future__ import annotations

import datetime as _dt

import pytest

from k2.storage.db import connect, current_version, initialize
from k2.storage.repositories import Repository
from k2.storage.schema import SCHEMA_VERSION
from k2.domain.models import (
    LearningProblem,
    LearningProblemEvent,
    StudySession,
    StudySessionRevision,
    Subject,
    Topic,
    TopicDeadline,
)


@pytest.fixture()
def repo(tmp_path):
    conn = initialize(tmp_path / "k2.db")
    repository = Repository(conn)
    repository.conn.commit()
    yield repository
    conn.close()


def _subject(repo: Repository) -> Subject:
    subject = Subject(name="ریاضی", coefficient=1.5)
    repo.create_subject(subject)
    return subject


def _topic(repo: Repository, subject: Subject) -> Topic:
    topic = Topic(subject_id=subject.id, name="احتمال")
    repo.create_topic(topic)
    return topic


def test_schema_version_is_six():
    assert SCHEMA_VERSION == 6


def test_fresh_database_reaches_current_version(tmp_path):
    conn = connect(tmp_path / "fresh.db")
    assert current_version(conn) == 0
    from k2.storage.db import apply_migrations

    apply_migrations(conn)
    assert current_version(conn) == SCHEMA_VERSION
    conn.close()


def test_migration_from_version_five_preserves_existing_rows(tmp_path):
    """پایگاه دادهٔ قدیمی (نسخهٔ ۵) بدون از دست دادن داده مهاجرت می‌کند."""
    conn = connect(tmp_path / "old.db")
    from k2.storage.schema import MIGRATIONS
    from k2.storage.db import apply_migrations

    for version, script in MIGRATIONS:
        if version > 5:
            continue
        conn.executescript(script)
        conn.execute(f"PRAGMA user_version = {version}")
        conn.commit()
    conn.execute(
        "INSERT INTO subject (id, name, coefficient) VALUES (1, 'شیمی', 1.0)"
    )
    conn.execute(
        "INSERT INTO topic (id, subject_id, name, mastery) VALUES (1, 1, 'دانسی', 'L2')"
    )
    conn.commit()

    apply_migrations(conn)
    assert current_version(conn) == 6
    repo = Repository(conn)
    topics = repo.list_topics()
    assert topics[0].name == "دانسی"
    assert topics[0].mastery.name == "L2"
    # مقادیر پیش‌فرض محافظه‌کارانه
    assert topics[0].konkur_stage == "conceptual"
    assert topics[0].final_stage == "textbook_study"
    assert topics[0].prerequisite_share == 0.0
    assert topics[0].estimated_minutes is None
    conn.close()


def test_topic_deadline_roundtrip(repo):
    subject = _subject(repo)
    topic = _topic(repo, subject)
    deadline = TopicDeadline(
        topic_id=topic.id,
        subject_id=subject.id,
        kind=None,
        target_date=_dt.date(2026, 12, 1),
        target_percent=72.5,
        target_level="L3",
        is_master=True,
        note="تثبیت نهایی احتمال",
    )
    from k2.domain.enums import DeadlineKind

    deadline.kind = DeadlineKind.FINAL_CONSOLIDATION
    repo.create_topic_deadline(deadline)
    repo.conn.commit()

    stored = repo.list_topic_deadlines(topic.id)
    assert len(stored) == 1
    assert stored[0].kind == DeadlineKind.FINAL_CONSOLIDATION
    assert stored[0].target_date == _dt.date(2026, 12, 1)
    assert stored[0].target_percent == 72.5
    assert stored[0].is_master is True
    assert stored[0].topic_name == "احتمال"
    assert stored[0].has_measurable_target is True

    stored[0].target_percent = 80
    repo.update_topic_deadline(stored[0])
    repo.conn.commit()
    assert repo.list_topic_deadlines(topic.id)[0].target_percent == 80

    repo.delete_topic_deadline(stored[0].id)
    repo.conn.commit()
    assert repo.list_topic_deadlines(topic.id) == []


def test_topic_deadline_rejects_bad_percent(repo):
    subject = _subject(repo)
    topic = _topic(repo, subject)
    from k2.domain.enums import DeadlineKind

    deadline = TopicDeadline(
        topic_id=topic.id, kind=DeadlineKind.PRACTICE,
        target_date=_dt.date(2026, 12, 1), target_percent=140,
    )
    with pytest.raises(ValueError):
        repo.create_topic_deadline(deadline)


def test_master_deadline_is_single_per_topic(repo):
    subject = _subject(repo)
    topic = _topic(repo, subject)
    from k2.domain.enums import DeadlineKind

    first = TopicDeadline(topic_id=topic.id, kind=DeadlineKind.START,
                          target_date=_dt.date(2026, 11, 1), is_master=True)
    second = TopicDeadline(topic_id=topic.id,
                           kind=DeadlineKind.FINAL_CONSOLIDATION,
                           target_date=_dt.date(2026, 12, 1), is_master=True)
    repo.create_topic_deadline(first)
    repo.create_topic_deadline(second)
    repo.set_master_deadline(topic.id, second.id)
    repo.conn.commit()
    masters = [d for d in repo.list_topic_deadlines(topic.id) if d.is_master]
    assert len(masters) == 1
    assert masters[0].kind == DeadlineKind.FINAL_CONSOLIDATION


def test_study_session_roundtrip_and_running_session(repo):
    subject = _subject(repo)
    topic = _topic(repo, subject)
    from k2.domain.enums import SessionKind

    session = StudySession(
        subject_id=subject.id,
        topic_id=topic.id,
        kind=SessionKind.STUDY,
        mode="timer",
        started_at=_dt.datetime(2026, 10, 23, 9, 0),
        ended_at=_dt.datetime(2026, 10, 23, 10, 30),
        paused_seconds=300,
        minutes=85,
        note="تمرین تستی",
    )
    repo.create_study_session(session)
    repo.conn.commit()
    assert repo.running_study_session() is None

    stored = repo.list_study_sessions()
    assert len(stored) == 1
    assert stored[0].minutes == 85
    assert stored[0].paused_seconds == 300
    assert stored[0].topic_name == "احتمال"
    assert stored[0].subject_name == "ریاضی"

    # بازهٔ تاریخی
    assert len(repo.list_study_sessions(start=_dt.date(2026, 10, 23))) == 1
    assert len(repo.list_study_sessions(start=_dt.date(2026, 10, 24))) == 0
    assert len(repo.list_study_sessions(topic_id=topic.id)) == 1


def test_unfinished_session_survives_a_restart(repo):
    subject = _subject(repo)
    from k2.domain.enums import SessionKind

    session = StudySession(
        subject_id=subject.id, kind=SessionKind.STUDY, mode="timer",
        started_at=_dt.datetime(2026, 10, 23, 9, 0), ended_at=None,
        paused_seconds=0, paused_at=_dt.datetime(2026, 10, 23, 9, 20),
    )
    repo.create_study_session(session)
    repo.conn.commit()
    running = repo.running_study_session()
    assert running is not None
    assert running.ended_at is None
    assert running.paused_at == _dt.datetime(2026, 10, 23, 9, 20)


def test_session_revision_history_is_kept(repo):
    subject = _subject(repo)
    from k2.domain.enums import SessionKind

    session = StudySession(
        subject_id=subject.id, kind=SessionKind.STUDY, mode="timer",
        started_at=_dt.datetime(2026, 10, 23, 9, 0),
        ended_at=_dt.datetime(2026, 10, 23, 10, 0), minutes=60,
    )
    repo.create_study_session(session)
    repo.add_session_revision(
        StudySessionRevision(
            session_id=session.id, field_name="minutes",
            old_value="60", new_value="55", reason="اشتباه تایپی",
        )
    )
    repo.conn.commit()
    revisions = repo.list_session_revisions(session.id)
    assert len(revisions) == 1
    assert revisions[0].old_value == "60"
    assert revisions[0].new_value == "55"
    assert revisions[0].reason == "اشتباه تایپی"


def test_session_rejects_negative_minutes(repo):
    from k2.domain.enums import SessionKind

    session = StudySession(
        kind=SessionKind.STUDY, mode="timer",
        started_at=_dt.datetime(2026, 10, 23, 9, 0), minutes=-5,
    )
    with pytest.raises(ValueError):
        repo.create_study_session(session)


def test_learning_problem_roundtrip_and_events(repo):
    subject = _subject(repo)
    topic = _topic(repo, subject)
    from k2.domain.enums import ProblemKind, ProblemStatus

    problem = LearningProblem(
        subject_id=subject.id, topic_id=topic.id,
        kind=ProblemKind.CONCEPTUAL_GAP, title="نمی‌فهمم نمودار چیست",
        description="در تست‌های زمان‌دار گیر می‌کنم", severity=4,
        first_seen=_dt.date(2026, 10, 1),
    )
    repo.create_learning_problem(problem)
    repo.conn.commit()
    assert problem.first_seen == _dt.date(2026, 10, 1)
    stored = repo.list_learning_problems()
    assert stored[0].kind == ProblemKind.CONCEPTUAL_GAP
    assert stored[0].severity == 4
    assert stored[0].topic_name == "احتمال"
    assert stored[0].is_open is True
    # رویداد «ثبت» خودکار ساخته می‌شود
    assert len(repo.list_problem_events(problem.id)) == 1

    stored[0].status = ProblemStatus.RESOLVED
    stored[0].resolution_note = "با مثال‌های هدایت‌شده حل شد"
    repo.update_learning_problem(stored[0])
    repo.conn.commit()
    resolved = repo.list_learning_problems(status=ProblemStatus.RESOLVED)
    assert len(resolved) == 1
    assert repo.list_learning_problems(status=ProblemStatus.OPEN) == []

    repo.add_problem_event(
        LearningProblemEvent(problem_id=problem.id, kind="resolved",
                             note="رفع شد")
    )
    repo.conn.commit()
    kinds = [e.kind for e in repo.list_problem_events(problem.id)]
    assert kinds == ["opened", "resolved"]

    repo.delete_learning_problem(problem.id)
    repo.conn.commit()
    assert repo.list_learning_problems() == []


def test_learning_problem_validates_severity_and_title(repo):
    from k2.domain.enums import ProblemKind

    with pytest.raises(ValueError):
        repo.create_learning_problem(
            LearningProblem(title="   ", kind=ProblemKind.SPEED, severity=3)
        )
    with pytest.raises(ValueError):
        repo.create_learning_problem(
            LearningProblem(title="کندم", kind=ProblemKind.SPEED, severity=9)
        )


def test_topic_update_persists_dual_track_fields(repo):
    subject = _subject(repo)
    topic = _topic(repo, subject)
    from k2.domain.enums import KonkurStage, FinalStage

    topic.konkur_stage = KonkurStage.TIMED_TEST.value
    topic.final_stage = FinalStage.DESCRIPTIVE_PRACTICE.value
    topic.prerequisite_share = 0.75
    topic.final_exam_share = 0.4
    topic.estimated_minutes = 210
    repo.update_topic(topic)
    repo.conn.commit()

    stored = repo.list_topics(subject.id)[0]
    assert stored.konkur_stage == "timed_test"
    assert stored.final_stage == "descriptive_practice"
    assert stored.prerequisite_share == 0.75
    assert stored.final_exam_share == 0.4
    assert stored.estimated_minutes == 210


def test_shares_are_clamped_to_zero_one(repo):
    subject = _subject(repo)
    topic = _topic(repo, subject)
    topic.prerequisite_share = 5.0
    topic.final_exam_share = -2.0
    repo.update_topic(topic)
    repo.conn.commit()
    stored = repo.list_topics(subject.id)[0]
    assert stored.prerequisite_share == 1.0
    assert stored.final_exam_share == 0.0
