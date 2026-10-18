"""تست موتور مشاور: فاز زمانی، تسلط، گلوگاه و تجویز (ADV-01 تا ADV-04)."""

from __future__ import annotations

import datetime as _dt

import pytest

from k2.advisor_engine import (
    PHASE_LABELS,
    MasteryEvidence,
    assess_mastery,
    determine_phase,
    detect_bottleneck,
    next_action,
    prescribe_for_topic,
)
from k2.config import Settings
from k2.domain.enums import (
    ActivityType,
    Bottleneck,
    ContentType,
    ErrorCode,
    MasteryLevel,
    StudyPhase,
)
from k2.domain.models import ErrorRecord, ExamQuestion, Topic


def test_phase_boundaries():
    settings = Settings()
    assert determine_phase(400, settings) == StudyPhase.FOUNDATION
    assert determine_phase(150, settings) == StudyPhase.CONSOLIDATION
    assert determine_phase(60, settings) == StudyPhase.INTENSIFICATION
    assert determine_phase(20, settings) == StudyPhase.SUMMARIZATION
    assert determine_phase(5, settings) == StudyPhase.FINAL_DAYS
    assert determine_phase(0, settings) == StudyPhase.FINAL_DAYS
    assert determine_phase(None, settings) == StudyPhase.UNKNOWN


def test_phase_boundaries_are_configurable():
    settings = Settings()
    settings.advisor.phase_intensification_days = 200
    assert determine_phase(150, settings) == StudyPhase.INTENSIFICATION
    settings.advisor.phase_final_days = 20
    assert determine_phase(10, settings) == StudyPhase.FINAL_DAYS


def test_single_diagnostic_does_not_claim_mastery():
    assessment = assess_mastery(
        topic_id=1,
        topic_name="تابع",
        evidence=[
            MasteryEvidence(at=_dt.date(2026, 10, 1), source="diagnostic", score=0.9)
        ],
        settings=Settings(),
    )
    assert assessment.level == MasteryLevel.L3
    assert assessment.confidence < 0.5
    assert any("تشخیصی" in reason for reason in assessment.reasons)
    assert any("تأخیری" in reason for reason in assessment.reasons)


def test_l4_requires_spaced_delayed_and_transfer_evidence():
    assessment = assess_mastery(
        topic_id=1,
        topic_name="تابع",
        evidence=[
            MasteryEvidence(at=_dt.date(2026, 10, 1), source="diagnostic", score=0.92),
            MasteryEvidence(at=_dt.date(2026, 10, 6), source="delayed", score=0.88),
            MasteryEvidence(at=_dt.date(2026, 10, 10), source="transfer", score=0.86),
        ],
        settings=Settings(),
    )
    assert assessment.level == MasteryLevel.L4
    assert assessment.distinct_sessions == 3
    assert assessment.delayed_confirmed and assessment.transfer_confirmed
    assert any("تضمین" in reason for reason in assessment.reasons)


def test_mastery_low_score_is_l1():
    assessment = assess_mastery(
        topic_id=1,
        topic_name="تابع",
        evidence=[
            MasteryEvidence(at=_dt.date(2026, 10, 1), source="exam", score=0.2)
        ],
        settings=Settings(),
    )
    assert assessment.level == MasteryLevel.L1


def test_mastery_without_evidence_is_l0_with_low_confidence():
    assessment = assess_mastery(
        topic_id=1, topic_name="تابع", evidence=[], settings=Settings()
    )
    assert assessment.level == MasteryLevel.L0
    assert assessment.confidence < 0.3


def test_self_report_alone_has_low_confidence():
    assessment = assess_mastery(
        topic_id=1,
        topic_name="تابع",
        evidence=[],
        self_assessed=4,
        settings=Settings(),
    )
    assert assessment.confidence <= 0.3
    assert any("خودسنجی" in reason for reason in assessment.reasons)


def test_transfer_evidence_is_noted():
    assessment = assess_mastery(
        topic_id=1,
        topic_name="تابع",
        evidence=[
            MasteryEvidence(at=_dt.date(2026, 10, 1), source="diagnostic", score=0.75),
            MasteryEvidence(at=_dt.date(2026, 10, 5), source="transfer", score=0.8),
        ],
        settings=Settings(),
    )
    assert any("انتقال" in reason for reason in assessment.reasons)


def test_bottleneck_knowledge():
    errors = [
        ErrorRecord(code=ErrorCode.E1),
        ErrorRecord(code=ErrorCode.E2),
        ErrorRecord(code=ErrorCode.E4),
    ]
    result = detect_bottleneck(
        subject_name="زیست", errors=errors, settings=Settings()
    )
    assert result.bottleneck == Bottleneck.KNOWLEDGE
    assert result.evidence


def test_bottleneck_method():
    errors = [
        ErrorRecord(code=ErrorCode.E3),
        ErrorRecord(code=ErrorCode.E9),
        ErrorRecord(code=ErrorCode.E3),
    ]
    result = detect_bottleneck(
        subject_name="ریاضی", errors=errors, settings=Settings()
    )
    assert result.bottleneck == Bottleneck.METHOD


def test_bottleneck_speed_from_blanks():
    questions = [
        ExamQuestion(status="blank"),
        ExamQuestion(status="blank"),
        ExamQuestion(status="correct"),
    ]
    result = detect_bottleneck(
        subject_name="ریاضی", errors=[], questions=questions, settings=Settings()
    )
    assert result.bottleneck == Bottleneck.SPEED


def test_bottleneck_execution_from_low_adherence():
    result = detect_bottleneck(
        subject_name="ریاضی", errors=[], adherence=0.3, settings=Settings()
    )
    assert result.bottleneck == Bottleneck.EXECUTION


def test_bottleneck_none_without_data():
    result = detect_bottleneck(
        subject_name="ریاضی", errors=[], settings=Settings()
    )
    assert result.bottleneck == Bottleneck.NONE


def test_prescription_matrix_has_all_phase_level_cells():
    from k2.domain.learning import PRESCRIPTION_MATRIX

    for phase in (
        StudyPhase.FOUNDATION,
        StudyPhase.CONSOLIDATION,
        StudyPhase.INTENSIFICATION,
        StudyPhase.SUMMARIZATION,
        StudyPhase.FINAL_DAYS,
    ):
        for level in (
            MasteryLevel.L0,
            MasteryLevel.L1,
            MasteryLevel.L2,
            MasteryLevel.L3,
            MasteryLevel.L4,
        ):
            assert (phase, level) in PRESCRIPTION_MATRIX


def test_prescription_creates_activities_with_criteria():
    topic = Topic(id=1, subject_id=2, name="تابع", content_type=ContentType.CALCULATIONAL)
    prescription = prescribe_for_topic(
        topic=topic,
        subject_name="ریاضی",
        phase=StudyPhase.FOUNDATION,
        level=MasteryLevel.L1,
        settings=Settings(),
    )
    assert prescription.activities
    for activity in prescription.activities:
        assert activity.topic_id == 1
        assert activity.est_minutes > 0
        assert "تابع" in activity.title
    assert prescription.methods
    assert any("مثال حل‌شده" in method for method in prescription.methods)


def test_subject_specific_methods_cover_art_and_foreign_language():
    from k2.domain.learning import recommended_methods, subject_default_content_type

    art_type = subject_default_content_type("خلاقیت تصویری و تجسمی")
    assert art_type == ContentType.PRACTICAL
    art_methods = recommended_methods(art_type, "خلاقیت تصویری و تجسمی")
    assert any("خروجی قابل مشاهده" in method for method in art_methods)
    language_methods = recommended_methods(
        subject_default_content_type("زبان تخصصی (زبان انتخابی داوطلب)"),
        "زبان تخصصی (زبان انتخابی داوطلب)",
    )
    assert any("متن تازه" in method for method in language_methods)


def test_next_action_has_a_reason():
    suggestion = next_action(
        topic_name="تابع",
        level=MasteryLevel.L2,
        phase=StudyPhase.INTENSIFICATION,
        bottleneck=Bottleneck.SPEED,
    )
    assert suggestion.title
    assert suggestion.reason
    assert len(suggestion.reason) > 10


def test_phase_labels_cover_all_phases():
    for phase in StudyPhase:
        assert PHASE_LABELS[phase]
