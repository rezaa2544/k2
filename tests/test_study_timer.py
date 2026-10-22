"""تست‌های موتور تایمر مطالعه و جمع ساعت خالص (بند ۱۵)."""

from __future__ import annotations

import datetime as _dt

import pytest

from k2.domain.enums import SessionKind
from k2.domain.models import StudySession, StudySessionRevision
from k2.study_timer import (
    StudyTimer,
    daily_totals,
    net_minutes,
    planned_vs_actual,
    revise_session,
    totals_for,
    week_bounds,
    weekly_totals,
)


BASE = _dt.datetime(2026, 10, 23, 9, 0, 0)


class FakeClock:
    """ساعت مصنوعی برای تست قطعی تایمر."""

    def __init__(self, start: _dt.datetime):
        self.value = start

    def __call__(self) -> _dt.datetime:
        return self.value

    def advance(self, seconds: int) -> None:
        self.value += _dt.timedelta(seconds=seconds)


def _session(**kwargs) -> StudySession:
    defaults = dict(
        kind=SessionKind.STUDY,
        mode="timer",
        started_at=BASE,
        ended_at=BASE + _dt.timedelta(minutes=90),
        paused_seconds=0,
        minutes=90,
    )
    defaults.update(kwargs)
    return StudySession(**defaults)


def test_timer_start_pause_resume_stop_gives_net_minutes():
    clock = FakeClock(BASE)
    timer = StudyTimer(now=clock)
    timer.start(kind=SessionKind.STUDY, topic_id=3)
    clock.advance(50 * 60)
    timer.pause()
    clock.advance(10 * 60)  # استراحت — نباید شمرده شود
    timer.resume()
    clock.advance(40 * 60)
    session = timer.stop()
    assert session.ended_at == clock.value
    # ۵۰ دقیقه کار + ۱۰ دقیقه استراحت + ۴۰ دقیقه کار = ۱۰۰ دقیقهٔ گذشته
    # منهای ۱۰ دقیقهٔ استراحت = ۹۰ دقیقهٔ خالص.
    assert session.paused_seconds == 600
    assert session.minutes == 90
    assert net_minutes(session) == 90


def test_timer_snapshot_reports_running_and_paused():
    clock = FakeClock(BASE)
    timer = StudyTimer(now=clock)
    timer.start()
    clock.advance(600)
    snap = timer.snapshot()
    assert snap.running and not snap.paused
    assert snap.net_seconds == 600
    timer.pause()
    clock.advance(300)
    paused_snap = timer.snapshot()
    assert paused_snap.paused and not paused_snap.running
    assert paused_snap.net_seconds == 600  # زمان استراحت شمرده نشد


def test_timer_rejects_second_concurrent_session():
    timer = StudyTimer(now=FakeClock(BASE))
    timer.start()
    with pytest.raises(RuntimeError):
        timer.start()


def test_resuming_saved_session_does_not_count_closed_app_time():
    """جلسهٔ ناتمامِ ذخیره‌شده در حالت pause بازگشایی می‌شود.

    سناریوی واقعی: کاربر تایمر را زد، برنامه را بست (جلسه با
    ``paused_at`` ذخیره شد)، پنج ساعت بعد باز کرد. آن پنج ساعت نباید
    به‌عنوان مطالعه شمرده شود.
    """
    saved = StudySession(
        id=7,
        kind=SessionKind.STUDY,
        mode="timer",
        started_at=BASE,
        ended_at=None,
        paused_seconds=0,
        paused_at=BASE,
        minutes=0,
    )
    clock = FakeClock(BASE + _dt.timedelta(hours=5))
    timer = StudyTimer(saved, now=clock)
    snap = timer.snapshot()
    assert snap.paused and not snap.running
    assert snap.net_seconds == 0  # پنج ساعت بسته‌بودن شمرده نشد
    timer.resume()
    clock.advance(30 * 60)
    session = timer.stop()
    assert session.paused_seconds == 5 * 3600
    assert session.minutes == 30


def test_totals_separate_class_from_independent_study():
    sessions = [
        _session(kind=SessionKind.LIVE_CLASS, minutes=120),
        _session(kind=SessionKind.STUDY, minutes=90),
        _session(kind=SessionKind.RECORDED_CLASS, minutes=45),
        _session(kind=SessionKind.TEST, minutes=60),
        _session(kind=SessionKind.ANALYSIS, minutes=30),
        _session(kind=SessionKind.REVIEW, minutes=20),
        _session(kind=SessionKind.CONSOLIDATION, minutes=15),
    ]
    totals = totals_for(sessions)
    assert totals.total_minutes == 380
    assert totals.class_minutes == 165
    assert totals.independent_minutes == 90
    assert totals.test_minutes == 60
    assert totals.analysis_minutes == 30
    assert totals.review_minutes == 20
    assert totals.consolidation_minutes == 15
    assert totals.independent_share == pytest.approx(90 / 380)


def test_daily_and_weekly_totals_are_saturday_based():
    friday = _dt.datetime(2026, 10, 23, 8, 0)  # جمعه
    saturday = _dt.datetime(2026, 10, 24, 8, 0)  # شنبه — شروع هفتهٔ تازه
    sessions = [
        _session(started_at=friday, ended_at=friday + _dt.timedelta(hours=1), minutes=60),
        _session(started_at=saturday, ended_at=saturday + _dt.timedelta(hours=1), minutes=45),
    ]
    daily = daily_totals(sessions)
    assert set(daily) == {_dt.date(2026, 10, 23), _dt.date(2026, 10, 24)}
    start, end = week_bounds(_dt.date(2026, 10, 24))
    assert start == _dt.date(2026, 10, 24) and end == _dt.date(2026, 10, 30)
    assert weekly_totals(sessions, _dt.date(2026, 10, 24)).total_minutes == 45
    assert weekly_totals(sessions, _dt.date(2026, 10, 23)).total_minutes == 60


def test_planned_vs_actual_compares_net_minutes():
    sessions = [
        _session(kind=SessionKind.LIVE_CLASS, minutes=60),
        _session(kind=SessionKind.STUDY, minutes=90),
    ]
    result = planned_vs_actual(200, sessions)
    assert result["planned_minutes"] == 200
    assert result["actual_minutes"] == 150
    assert result["class_minutes"] == 60
    assert result["independent_minutes"] == 90
    assert result["ratio"] == pytest.approx(0.75)
    assert "نزدیک" in str(result["message"])


def test_revise_session_records_history_and_never_overwrites():
    session = _session(id=4, minutes=90)
    revision = revise_session(
        session, field_name="minutes", new_value=85, reason="اشتباه تایپی"
    )
    assert isinstance(revision, StudySessionRevision)
    assert revision.old_value == "90"
    assert revision.new_value == "85"
    assert revision.reason == "اشتباه تایپی"
    assert session.minutes == 85
    assert session.mode == "corrected"


def test_revise_session_rejects_unknown_field():
    session = _session(id=4)
    with pytest.raises(ValueError):
        revise_session(session, field_name="paused_seconds", new_value=5, reason="x")


def test_revise_session_changes_kind_and_topic():
    session = _session(id=4, topic_id=None)
    revise_session(session, field_name="kind", new_value="test", reason="کنکور")
    assert session.kind == SessionKind.TEST
    revise_session(session, field_name="topic_id", new_value=9, reason="مبحث اشتباه")
    assert session.topic_id == 9


def test_negative_minutes_are_rejected():
    with pytest.raises(ValueError):
        revise_session(_session(id=1), field_name="minutes", new_value=-5, reason="x")
