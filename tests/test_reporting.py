"""تست گزارش‌ها، خروجی CSV و نشانگر فشار (ADV-04/ADV-05/DATA-03)."""

from __future__ import annotations

import csv
import datetime as _dt
from pathlib import Path

import pytest

from k2.domain.enums import ActivityState, ErrorCode, ExamKind
from k2.domain.models import Activity, ExamAttempt, ErrorRecord
from k2.reporting import (
    build_daily_report,
    build_weekly_report,
    export_activities_csv,
    export_attempts_csv,
    accuracy_trend,
    pressure_signal,
    repeated_error_rate,
    weekly_report_to_text,
)

SATURDAY = _dt.date(2026, 10, 10)


def _activity(index: int, state: ActivityState, minutes: int = 60) -> Activity:
    return Activity(
        id=index,
        title=f"کار {index}",
        est_minutes=minutes,
        actual_minutes=minutes if state == ActivityState.DONE else 0,
        state=state,
        created_at=_dt.datetime(2026, 10, 12, 9, 0),
        state_reason="بیش از حد زیاد" if state == ActivityState.DROPPED else "",
    )


def test_daily_report_counts_states():
    activities = [
        _activity(1, ActivityState.DONE),
        _activity(2, ActivityState.PARTIAL),
        _activity(3, ActivityState.READY),
    ]
    report = build_daily_report(date=SATURDAY, activities=activities)
    assert report.completed == 1
    assert report.partial == 1
    assert report.missed == 1
    assert 0 < report.adherence <= 1
    assert "گزارش" in report.to_text()


def test_weekly_report_computes_adherence():
    activities = [
        _activity(1, ActivityState.DONE),
        _activity(2, ActivityState.DONE),
        _activity(3, ActivityState.DROPPED),
    ]
    report = build_weekly_report(
        start_date=SATURDAY,
        end_date=SATURDAY + _dt.timedelta(days=6),
        activities=activities,
    )
    assert report.total_activities == 3
    assert report.completed_activities == 2
    assert report.adherence == pytest.approx(2 / 3)
    assert report.blockers
    assert weekly_report_to_text(report)


def test_weekly_report_flags_underestimation():
    activities = []
    for index in range(1, 4):
        activity = _activity(index, ActivityState.DONE)
        activity.est_minutes = 30
        activity.actual_minutes = 60
        activities.append(activity)
    report = build_weekly_report(
        start_date=SATURDAY,
        end_date=SATURDAY + _dt.timedelta(days=6),
        activities=activities,
    )
    assert report.estimate_bias > 0
    assert any("تخمین" in change for change in report.next_week_changes)


def test_repeated_error_rate():
    errors = [
        ErrorRecord(id=1, code=ErrorCode.E1, topic_id=1),
        ErrorRecord(id=2, code=ErrorCode.E1, topic_id=1),
        ErrorRecord(id=3, code=ErrorCode.E4, topic_id=2),
    ]
    assert repeated_error_rate(errors) == pytest.approx(2 / 3)
    assert repeated_error_rate([]) == 0.0


def test_accuracy_trend_is_personal():
    attempts = [
        ExamAttempt(id=1, taken_at=_dt.datetime(2026, 10, 1, 9, 0), percentage=50.0),
        ExamAttempt(id=2, taken_at=_dt.datetime(2026, 10, 8, 9, 0), percentage=70.0),
    ]
    trend = accuracy_trend(attempts)
    assert trend.first == 0.5
    assert trend.last == 0.7
    assert trend.direction == "بهبود"
    assert "خود" in trend.note


def test_pressure_signal_is_inactive_without_patterns():
    signal = pressure_signal(energy_factors=[1.0, 1.0, 1.0], debt_ratio=0.1)
    assert not signal.active
    assert signal.message


def test_pressure_signal_activates_and_is_non_diagnostic():
    signal = pressure_signal(
        energy_factors=[0.6, 0.6, 0.6], debt_ratio=0.9, overload_reasons_last_week=4
    )
    assert signal.active
    assert signal.reasons
    assert "تشخیص" in signal.message
    assert "صحبت کردن" in signal.message


def test_export_activities_csv(tmp_path: Path):
    activities = [_activity(1, ActivityState.DONE), _activity(2, ActivityState.READY)]
    path = export_activities_csv(activities, tmp_path / "out.csv")
    assert path.exists()
    with path.open(encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    assert rows[0][0] == "شناسه"
    assert len(rows) == 3


def test_export_attempts_csv(tmp_path: Path):
    attempts = [
        ExamAttempt(
            id=1,
            name="آزمون",
            kind=ExamKind.MOCK,
            taken_at=_dt.datetime(2026, 10, 1, 9, 0),
            total=40,
            correct=30,
            wrong=8,
            blank=2,
            percentage=75.0,
        )
    ]
    path = export_attempts_csv(attempts, tmp_path / "attempts.csv")
    with path.open(encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    assert rows[0][0] == "شناسه"
    assert rows[1][1] == "آزمون"


def test_no_streak_or_ranking_language_in_reports():
    """هیچ واژهٔ استریک/رتبه‌بندی/شرمساری در گزارش‌ها نباشد."""
    activities = [_activity(1, ActivityState.DROPPED)]
    report = build_weekly_report(
        start_date=SATURDAY,
        end_date=SATURDAY + _dt.timedelta(days=6),
        activities=activities,
    )
    text = weekly_report_to_text(report)
    forbidden = ["استریک", "رتبه", "تنبل", "جریمه", "بازنده"]
    for word in forbidden:
        assert word not in text
