"""تست ثبت آزمون، درصد و تحلیل خطا (EX-01/EX-02/ERR-01/ERR-02/ERR-03)."""

from __future__ import annotations

import datetime as _dt

import pytest

from k2.domain.enums import ErrorCode, ExamKind
from k2.domain.models import ExamProfile, ExamQuestion
from k2.exam_analysis import (
    build_error_breakdown,
    build_remediation,
    build_topic_weakness,
    compute_attempt,
    exam_kind_label,
    repeated_errors,
)

NOW = _dt.datetime(2026, 10, 10, 9, 0)


def _profile(formula: str = "raw", negative: float = 0.0) -> ExamProfile:
    return ExamProfile(
        name="آزمون",
        percentage_formula=formula,
        negative_marking_ratio=negative,
    )


def test_raw_percentage():
    result = compute_attempt(total=40, correct=30, wrong=8, blank=2, profile=_profile())
    assert result.raw_score == 75.0
    assert result.percentage == 75.0
    assert result.formula_used == "raw"


def test_negative_marking_percentage():
    result = compute_attempt(
        total=40,
        correct=30,
        wrong=8,
        blank=2,
        profile=_profile("negative", 0.25),
    )
    expected = ((30 - 8 * 0.25) / 40) * 100
    assert result.percentage == pytest.approx(expected)
    assert result.formula_used == "negative(0.25)"


def test_negative_formula_without_ratio_falls_back_and_warns():
    result = compute_attempt(
        total=10, correct=5, wrong=5, blank=0, profile=_profile("negative", 0.0)
    )
    assert result.formula_used == "raw"
    assert any("خام" in note for note in result.notes)


def test_zero_total_is_handled():
    result = compute_attempt(total=0, correct=0, wrong=0, blank=0, profile=_profile())
    assert result.percentage == 0.0
    assert result.notes


def test_inconsistent_counts_are_flagged():
    result = compute_attempt(total=40, correct=10, wrong=5, blank=5, profile=_profile())
    assert any("برابر نیست" in note for note in result.notes)


def test_error_breakdown_counts_codes():
    questions = [
        ExamQuestion(number=1, status="wrong", error_code=ErrorCode.E1),
        ExamQuestion(number=2, status="wrong", error_code=ErrorCode.E1),
        ExamQuestion(number=3, status="wrong", error_code=ErrorCode.E4),
        ExamQuestion(number=4, status="correct"),
        ExamQuestion(number=5, status="blank"),
    ]
    breakdown = build_error_breakdown(questions)
    assert breakdown.counts[ErrorCode.E1] == 2
    assert breakdown.counts[ErrorCode.E4] == 1
    assert breakdown.total == 3
    assert breakdown.top()[0][0] == ErrorCode.E1
    assert breakdown.ratio(ErrorCode.E1) == pytest.approx(2 / 3)


def test_topic_weakness_uses_weight():
    questions = [
        ExamQuestion(topic_id=1, status="wrong"),
        ExamQuestion(topic_id=1, status="wrong"),
        ExamQuestion(topic_id=2, status="wrong"),
        ExamQuestion(topic_id=2, status="blank"),
    ]
    weakness = build_topic_weakness(
        questions,
        topic_names={1: ("ریاضی", "تابع"), 2: ("فیزیک", "حرکت")},
        weights={1: 3.0, 2: 1.0},
    )
    by_id = {item.topic_id: item for item in weakness}
    assert by_id[1].weakness == 6.0
    assert by_id[2].weakness == 1.0
    assert by_id[2].blank_penalty == 1.0
    assert by_id[1].subject_name == "ریاضی"


def test_remediation_creates_activities_with_deadlines():
    from k2.domain.models import ErrorRecord

    errors = [
        ErrorRecord(
            id=1,
            code=ErrorCode.E1,
            topic_id=10,
            subject_id=2,
            created_at=NOW,
        ),
        ErrorRecord(
            id=2,
            code=ErrorCode.E1,
            topic_id=10,
            subject_id=2,
            created_at=NOW,
        ),
    ]
    from k2.domain.models import ExamAttempt

    attempt = ExamAttempt(id=5, name="آزمون", taken_at=NOW)
    plan = build_remediation(
        errors=errors,
        attempt=attempt,
        topic_names={10: ("شیمی", "استوکیومتری")},
        now=NOW,
    )
    assert len(plan.activities) == 1  # دو خطای هم‌نوع ⇒ یک فعالیت
    activity = plan.activities[0]
    assert "استوکیومتری" in activity.title
    assert activity.deadline_at is not None
    assert activity.deadline_at > NOW
    assert plan.notes


def test_repeated_errors_are_detected():
    from k2.domain.models import ErrorRecord

    errors = [
        ErrorRecord(id=1, code=ErrorCode.E3, topic_id=1, created_at=NOW),
        ErrorRecord(id=2, code=ErrorCode.E3, topic_id=1, created_at=NOW),
        ErrorRecord(id=3, code=ErrorCode.E5, topic_id=2, created_at=NOW),
    ]
    stats = repeated_errors(errors, topic_names={1: ("ریاضی", "حد")})
    assert len(stats) == 1
    assert stats[0].occurrences == 2
    assert stats[0].is_repeated
    assert stats[0].code == ErrorCode.E3


def test_exam_kind_labels_are_distinct():
    labels = {kind: exam_kind_label(kind) for kind in ExamKind}
    assert len(set(labels.values())) == len(labels)
    assert labels[ExamKind.OFFICIAL] != labels[ExamKind.INSTITUTE]
