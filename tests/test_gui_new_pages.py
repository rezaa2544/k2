"""تست‌های رابط کاربری برای صفحه‌های تازه (بندهای ۱۲–۱۸)."""

from __future__ import annotations

import datetime as _dt

import pytest
from PySide6.QtWidgets import QMessageBox

from k2.domain.enums import (
    DeadlineKind,
    RoutineKind,
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
from k2.ui.app import MainWindow

TODAY = _dt.date.today()


@pytest.fixture(autouse=True)
def _no_modal_blocking(monkeypatch):
    """دیالوگ‌های اطلاعاتی نباید تست را متوقف کنند."""
    import sys

    for name, module in list(sys.modules.items()):
        if not name.startswith("k2.ui.views"):
            continue
        if hasattr(module, "notify"):
            monkeypatch.setattr(module, "notify", lambda *a, **k: None)
        if hasattr(module, "confirm"):
            monkeypatch.setattr(module, "confirm", lambda *a, **k: False)
    monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)
    monkeypatch.setattr(QMessageBox, "exec_", lambda self: 0)
    for static_name in ("warning", "information", "critical", "question"):
        monkeypatch.setattr(
            QMessageBox, static_name, staticmethod(lambda *a, **k: 0)
        )


@pytest.fixture()
def window(qapp, tmp_path):
    service = AdvisorService(tmp_path / "gui.db")
    win = MainWindow(service)
    yield win
    win.close()
    service.close()


def _seed(service: AdvisorService) -> Topic:
    subject = Subject(name="ریاضی", coefficient=2.0)
    service.create_subject(subject)
    topic = Topic(subject_id=subject.id, name="احتمال", estimated_minutes=240)
    service.create_topic(topic)
    return topic


# ---------------------------------------------------------------------------
# مهلت‌های من
# ---------------------------------------------------------------------------


def test_deadlines_page_shows_back_calculation_and_evidence(window):
    topic = _seed(window.service)
    window.service.save_topic_deadline(
        TopicDeadline(
            topic_id=topic.id,
            kind=DeadlineKind.FINAL_CONSOLIDATION,
            target_date=TODAY + _dt.timedelta(days=40),
            target_percent=70,
            is_master=True,
        )
    )
    window.deadlines.refresh()
    assert window.deadlines.table.rowCount() == 1
    window.deadlines.table.setCurrentCell(0, 0)
    window.deadlines._show_plan()
    text = window.deadlines.detail_text.text()
    assert "شروع مطالعه" in text
    assert "تثبیت نهایی" in text
    assert "اثبات تکمیل" in text
    assert "پیشنهاد" in text or "شدنی" in text


def test_deadline_dialog_parses_jalali_date(window):
    topic = _seed(window.service)
    from k2.ui.views import DeadlineDialog

    dialog = DeadlineDialog(window.service, None)
    dialog.topic_combo.setCurrentIndex(dialog.topic_combo.findData(topic.id))
    dialog.date_edit.setText("۱۴۰۵/۱۰/۰۱")
    dialog._accept()
    deadline = getattr(dialog, "result_deadline", None)
    assert deadline is not None
    assert deadline.target_date is not None


def test_deadline_dialog_rejects_invalid_date(window, monkeypatch):
    topic = _seed(window.service)
    from k2.ui.views import DeadlineDialog

    shown: list[str] = []
    real_warning = QMessageBox.warning
    monkeypatch.setattr(
        QMessageBox, "warning", staticmethod(lambda *a, **k: shown.append(a))
    )
    try:
        dialog = DeadlineDialog(window.service, None)
        dialog.topic_combo.setCurrentIndex(dialog.topic_combo.findData(topic.id))
        dialog.date_edit.setText("نامعتبر")
        dialog._accept()
    finally:
        monkeypatch.setattr(QMessageBox, "warning", real_warning)
    assert shown
    assert not hasattr(dialog, "result_deadline")


# ---------------------------------------------------------------------------
# ساعت مطالعه
# ---------------------------------------------------------------------------


def test_study_timer_page_renders_totals(window):
    topic = _seed(window.service)
    for kind, minutes in (
        (SessionKind.LIVE_CLASS, 60),
        (SessionKind.STUDY, 90),
        (SessionKind.TEST, 30),
    ):
        window.service.save_study_session(
            StudySession(
                subject_id=topic.subject_id, topic_id=topic.id, kind=kind,
                mode="manual", started_at=_dt.datetime.now() - _dt.timedelta(hours=2),
                ended_at=_dt.datetime.now() - _dt.timedelta(hours=1), minutes=minutes,
            )
        )
    window.timer.refresh()
    assert window.timer.table.rowCount() == 3
    assert window.timer.day_value.text()
    assert "کلاس" in window.timer.day_detail.text()
    assert "مطالعهٔ مستقل" in window.timer.day_detail.text()


def test_study_timer_start_pause_stop_flow(window):
    topic = _seed(window.service)
    index = window.timer.topic_combo.findData(topic.id)
    window.timer.topic_combo.setCurrentIndex(index)
    window.timer._start()
    running = window.service.running_session()
    assert running is not None
    assert running.ended_at is None
    window.timer._pause()
    paused = window.service.running_session()
    assert paused.paused_at is not None
    window.timer._pause()  # ادامه
    window.timer._stop()
    assert window.service.running_session() is None
    sessions = window.service.list_study_sessions()
    assert sessions and sessions[0].ended_at is not None
    assert sessions[0].minutes >= 0


def test_manual_session_dialog_computes_net_minutes(window):
    topic = _seed(window.service)
    from k2.ui.views import ManualSessionDialog

    dialog = ManualSessionDialog(window.service)
    dialog.kind_combo.setCurrentIndex(
        dialog.kind_combo.findData(SessionKind.STUDY)
    )
    dialog.topic_combo.setCurrentIndex(dialog.topic_combo.findData(topic.id))
    start = _dt.datetime.now().replace(second=0, microsecond=0) - _dt.timedelta(
        hours=1, minutes=10
    )
    from PySide6.QtCore import QDateTime

    dialog.start_edit.setDateTime(QDateTime(start))
    dialog.end_edit.setDateTime(QDateTime(start + _dt.timedelta(hours=1, minutes=10)))
    dialog.break_spin.setValue(10)
    dialog._accept()
    session = getattr(dialog, "result_session", None)
    assert session is not None
    assert session.minutes == 60  # ۷۰ دقیقهٔ گذشته منهای ۱۰ دقیقهٔ استراحت
    assert session.mode == "manual"


def test_correction_dialog_requires_a_reason(window):
    topic = _seed(window.service)
    session_id = window.service.save_study_session(
        StudySession(
            subject_id=topic.subject_id, topic_id=topic.id, kind=SessionKind.STUDY,
            mode="timer", started_at=_dt.datetime.now() - _dt.timedelta(hours=1),
            ended_at=_dt.datetime.now(), minutes=60,
        )
    )
    from k2.ui.views import CorrectSessionDialog

    session = window.service.list_study_sessions()[0]
    dialog = CorrectSessionDialog(window.service, session)
    dialog.minutes_spin.setValue(45)
    dialog._accept()  # بدون دلیل ⇒ نباید پذیرفته شود
    assert not hasattr(dialog, "revision")
    dialog.reason_edit.setText("اشتباه تایپی")
    dialog._accept()
    assert dialog.revision.old_value == "60"
    assert dialog.revision.new_value == "45"
    assert window.service.list_study_sessions()[0].minutes == 45
    assert len(window.service.session_revisions(session_id)) == 1


# ---------------------------------------------------------------------------
# مشکلات یادگیری
# ---------------------------------------------------------------------------


def test_problems_page_lists_and_tracks(window):
    topic = _seed(window.service)
    window.service.save_learning_problem(
        LearningProblem(
            subject_id=topic.subject_id, topic_id=topic.id,
            title="در تست زمان‌دار گیر می‌کنم", severity=4,
        )
    )
    window.problems.refresh()
    assert window.problems.table.rowCount() == 1
    window.problems.table.setCurrentCell(0, 0)
    window.problems._show_detail()
    assert "گیر می‌کنم" in window.problems.detail_text.text()


def test_problem_status_change_logs_an_event(window):
    topic = _seed(window.service)
    problem_id = window.service.save_learning_problem(
        LearningProblem(
            subject_id=topic.subject_id, topic_id=topic.id,
            title="بی‌دقتی", severity=3,
        )
    )
    from k2.ui.views import ResolveDialog

    dialog = ResolveDialog()
    dialog.status_combo.setCurrentIndex(
        dialog.status_combo.findData(
            __import__("k2.domain.enums", fromlist=["ProblemStatus"]).ProblemStatus.RESOLVED
        )
    )
    dialog.note_edit.setPlainText("با چک‌لیست حل شد")
    dialog._accept()
    window.service.set_problem_status(
        problem_id, dialog.result_status, dialog.result_note
    )
    events = window.service.problem_events(problem_id)
    assert [e.kind for e in events] == ["opened", "resolved"]


# ---------------------------------------------------------------------------
# بانک دروس
# ---------------------------------------------------------------------------


def test_course_bank_shows_both_tracks(window):
    topic = _seed(window.service)
    window.courses.refresh()
    assert window.courses.table.rowCount() == 1
    window.courses.table.setCurrentCell(0, 0)
    window.courses._show_detail()
    text = window.courses.detail_text.text()
    assert "مسیر کنکور" in text
    assert "مسیر نهایی" in text
    assert "جایگزین" in text or "هشدار" in text


def test_course_bank_evidence_advances_konkur_stage(window):
    topic = _seed(window.service)
    from k2.ui.views import EvidenceDialog

    dialog = EvidenceDialog(window.service, topic.id)
    dialog.source_combo.setCurrentIndex(
        dialog.source_combo.findData("diagnostic")
    )
    dialog.score_spin.setValue(0.9)
    dialog._accept()
    changed, message = window.service.record_track_evidence(
        topic.id, dialog.result_track, dialog.result_evidence
    )
    assert changed is True
    view = window.service.topic_dual_track(topic.id)
    assert view.konkur.index == 1
    assert view.final.index == 0


def test_add_topic_dialog_collects_priority_factors(window):
    from k2.ui.views import AddTopicDialog

    dialog = AddTopicDialog(window.service)
    dialog.name_edit.setText("حد و تابع")
    dialog.prereq_spin.setValue(0.6)
    dialog.final_share_spin.setValue(0.3)
    dialog.estimate_spin.setValue(180)
    dialog._accept()
    topic = dialog.topic
    assert topic.name
    assert topic.prerequisite_share == 0.6
    assert topic.final_exam_share == 0.3
    assert topic.estimated_minutes == 180


# ---------------------------------------------------------------------------
# کلاس‌های من
# ---------------------------------------------------------------------------


def test_classes_page_lists_events_and_routines(window):
    from k2.domain.enums import FixedEventKind
    from k2.domain.models import FixedEvent, Routine

    window.service.create_fixed_event(
        FixedEvent(
            title="کلاس ریاضی", kind=FixedEventKind.LIVE_CLASS, weekday=0,
            start_minute=600, end_minute=720,
        )
    )
    window.service.create_routine(
        Routine(
            title="خواب", kind=RoutineKind.SLEEP,
            start_minute=1380, end_minute=360,
        )
    )
    window.classes.refresh()
    assert window.classes.event_table.rowCount() == 1
    assert window.classes.routine_table.rowCount() == 1
    assert "کلاس ریاضی" in window.classes.event_table.item(0, 0).text()


def test_fixed_event_dialog_validates_range(window, monkeypatch):
    from k2.ui.views import FixedEventDialog

    dialog = FixedEventDialog(window.service)
    dialog.title_edit.setText("کلاس")
    dialog.start_edit.setTime(_dt.time(18, 0))
    dialog.end_edit.setTime(_dt.time(17, 0))
    dialog._accept()
    assert not hasattr(dialog, "result_event")


# ---------------------------------------------------------------------------
# برنامه هفتگی
# ---------------------------------------------------------------------------


def test_weekly_plan_page_renders_seven_days(window):
    window.weekly.refresh()
    assert window.weekly.week_table.rowCount() == 7
    assert window.weekly.summary.text()
    window.weekly._fill_selected_day()


def test_weekly_plan_nightly_review_reports_changes(window):
    topic = _seed(window.service)
    window.service.save_topic_deadline(
        TopicDeadline(
            topic_id=topic.id, kind=DeadlineKind.FINAL_CONSOLIDATION,
            target_date=TODAY + _dt.timedelta(days=1), is_master=True,
        )
    )
    window.weekly._nightly()
    # پنجره در تست نمایش داده نمی‌شود؛ به‌جای isVisible، محتوا را می‌سنجیم.
    assert window.weekly.review_box.text()
    assert "دقیقه" in window.weekly.review_box.text()
    assert "ریسک مهلت" in window.weekly.review_box.text()


# ---------------------------------------------------------------------------
# عقب‌فتادگی‌ها و آزمون جامع
# ---------------------------------------------------------------------------


def test_backlogs_page_renders_triage_groups(window):
    topic = _seed(window.service)
    from k2.domain.enums import ActivityState, ActivityType
    from k2.domain.models import Activity

    window.service.create_activity(
        Activity(
            title="کار عقب‌افتاده", type=ActivityType.INDEPENDENT_PRACTICE,
            est_minutes=45, remaining_minutes=45,
            state=ActivityState.OVERDUE,
        )
    )
    window.backlogs.refresh()
    assert window.backlogs.summary.text()
    assert window.backlogs.backlog_table.rowCount() >= 1


def test_comprehensive_exams_page_shows_trend(window):
    window.service.create_exam_profile(
        ExamProfile(name="کنکور", target_date=TODAY + _dt.timedelta(days=300))
    )
    window.service.record_attempt(
        name="آزمون جامع ۱", total=100, correct=60, wrong=30, blank=10,
        duration_minutes=120,
    )
    window.service.record_attempt(
        name="آزمون جامع ۲", total=100, correct=70, wrong=20, blank=10,
        duration_minutes=120,
    )
    window.comprehensive.refresh()
    assert window.comprehensive.table.rowCount() == 2
    assert window.comprehensive.trend_table.rowCount() == 2
    assert "تغییر" in window.comprehensive.summary.text()


def test_tests_page_lists_tests_and_errors(window):
    window.service.record_attempt(
        name="تست تدریس", total=20, correct=15, wrong=5, blank=0,
        duration_minutes=20,
    )
    window.tests.refresh()
    assert window.tests.test_table.rowCount() == 1
    assert "تست" in window.tests.summary.text()
