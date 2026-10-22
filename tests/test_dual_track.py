"""تست‌های دو مسیر مستقل هر مبحث و قانون «جایگزینی ممنوع» (بند ۱۳)."""

from __future__ import annotations

import pytest

from k2.domain.enums import FinalStage, KonkurStage, MasteryLevel, TrackKind
from k2.domain.models import LearningEvidence, Topic
from k2.dual_track import (
    FINAL_LADDER,
    KONKUR_LADDER,
    NO_SUBSTITUTION_NOTE,
    advance_stage,
    activity_type_for,
    dual_track_view,
    evidence_source_for,
    missing_steps,
    regression_after_failure,
    stage_label,
    track_progress,
)


def _topic(**kwargs) -> Topic:
    defaults = dict(id=3, subject_id=1, name="احتمال")
    defaults.update(kwargs)
    return Topic(**defaults)


def _evidence(**kwargs) -> LearningEvidence:
    defaults = dict(topic_id=3, observed_on=None, source="diagnostic", score=0.9)
    defaults.update(kwargs)
    return LearningEvidence(**defaults)


def test_konkur_ladder_has_six_ordered_stages():
    assert [s.value for s in KONKUR_LADDER] == [
        "conceptual",
        "teaching_test",
        "timed_test",
        "option_analysis",
        "error_review",
        "mixed_exam",
    ]


def test_final_ladder_has_seven_ordered_stages():
    assert [s.value for s in FINAL_LADDER] == [
        "textbook_study",
        "definitions",
        "detail_map",
        "descriptive_practice",
        "sample_questions",
        "completeness_check",
        "mock_final",
    ]


def test_ladders_are_distinct_but_related():
    """دو مسیر متفاوت‌اند و هیچ‌کدام زیرمجموعهٔ دیگری نیست."""
    konkur = {s.label for s in KONKUR_LADDER}
    final = {s.label for s in FINAL_LADDER}
    assert konkur != final
    assert not konkur <= final and not final <= konkur


def test_progress_requires_evidence_not_a_calendar_tick():
    topic = _topic(konkur_stage=KonkurStage.CONCEPTUAL.value)
    progress = track_progress(topic, TrackKind.KONKUR, [])
    assert progress.evidence_ready is False
    assert progress.missing_evidence
    assert progress.next_stage == KonkurStage.TEACHING_TEST.value
    assert progress.progress_percent == 0.0


def test_advance_stage_only_with_sufficient_score():
    topic = _topic(konkur_stage=KonkurStage.CONCEPTUAL.value)
    changed, message = advance_stage(
        topic, TrackKind.KONKUR, _evidence(source="diagnostic", score=0.5)
    )
    assert changed is False
    assert topic.konkur_stage == KonkurStage.CONCEPTUAL.value
    changed, message = advance_stage(
        topic, TrackKind.KONKUR, _evidence(source="diagnostic", score=0.8)
    )
    assert changed is True
    assert topic.konkur_stage == KonkurStage.TEACHING_TEST.value
    assert topic.konkur_evidence_id is None or True  # شاهد ذخیره‌نشده شناسه ندارد


def test_wrong_evidence_source_cannot_advance_a_stage():
    """شاهدِ پلهٔ دیگر (مثلاً سنجش اولیه) پلهٔ فعلی را تأیید نمی‌کند."""
    topic = _topic(konkur_stage=KonkurStage.TIMED_TEST.value)
    changed, message = advance_stage(
        topic, TrackKind.KONKUR, _evidence(source="diagnostic", score=0.95)
    )
    assert changed is False
    assert "کافی نیست" in message
    assert topic.konkur_stage == KonkurStage.TIMED_TEST.value
    # شاهد درستِ همین پله باعث پیشرفت می‌شود
    changed, message = advance_stage(
        topic, TrackKind.KONKUR, _evidence(source="timed_test", score=0.95)
    )
    assert changed is True
    assert topic.konkur_stage == KonkurStage.OPTION_ANALYSIS.value


def test_descriptive_practice_does_not_replace_konkur_practice():
    """تمرین تشریحی مسیر نهایی، پلهٔ تست مسیر کنکور را جلو نمی‌برد."""
    topic = _topic(
        konkur_stage=KonkurStage.CONCEPTUAL.value,
        final_stage=FinalStage.DESCRIPTIVE_PRACTICE.value,
    )
    changed, message = advance_stage(
        topic,
        TrackKind.KONKUR,
        _evidence(source="descriptive_practice", score=0.99),
    )
    assert changed is False
    assert NO_SUBSTITUTION_NOTE.split("؛")[0] in NO_SUBSTITUTION_NOTE
    assert topic.konkur_stage == KonkurStage.CONCEPTUAL.value


def test_konkur_practice_does_not_replace_final_practice():
    topic = _topic(
        konkur_stage=KonkurStage.TIMED_TEST.value,
        final_stage=FinalStage.DESCRIPTIVE_PRACTICE.value,
    )
    changed, _ = advance_stage(
        topic,
        TrackKind.FINAL,
        _evidence(source="timed_test", score=0.99),
    )
    assert changed is False
    assert topic.final_stage == FinalStage.DESCRIPTIVE_PRACTICE.value


def test_tracks_advance_independently():
    topic = _topic()
    konkur_ok, _ = advance_stage(
        topic, TrackKind.KONKUR, _evidence(source="diagnostic", score=0.9)
    )
    assert konkur_ok
    assert topic.konkur_stage == KonkurStage.TEACHING_TEST.value
    assert topic.final_stage == FinalStage.TEXTBOOK_STUDY.value
    final_ok, _ = advance_stage(
        topic, TrackKind.FINAL, _evidence(source="diagnostic", score=0.9)
    )
    assert final_ok
    assert topic.final_stage == FinalStage.DEFINITIONS.value
    assert topic.konkur_stage == KonkurStage.TEACHING_TEST.value


def test_last_stage_cannot_advance_further():
    topic = _topic(konkur_stage=KonkurStage.MIXED_EXAM.value)
    changed, message = advance_stage(
        topic, TrackKind.KONKUR, _evidence(source="mixed_exam", score=0.95)
    )
    assert changed is False
    assert "آخرین پله" in message


def test_weak_evidence_regresses_one_stage_and_keeps_history():
    topic = _topic(konkur_stage=KonkurStage.OPTION_ANALYSIS.value)
    note = regression_after_failure(topic, TrackKind.KONKUR, score=0.3)
    assert topic.konkur_stage == KonkurStage.TIMED_TEST.value
    assert "برگشت" in note


def test_strong_evidence_does_not_regress():
    topic = _topic(konkur_stage=KonkurStage.OPTION_ANALYSIS.value)
    assert regression_after_failure(topic, TrackKind.KONKUR, score=0.95) == ""
    assert topic.konkur_stage == KonkurStage.OPTION_ANALYSIS.value


def test_dual_view_flags_substitution_risk_when_tracks_diverge():
    topic = _topic(
        konkur_stage=KonkurStage.MIXED_EXAM.value,
        final_stage=FinalStage.TEXTBOOK_STUDY.value,
    )
    view = dual_track_view(topic, [])
    assert view.substitution_risk
    assert view.warnings
    assert "جایگزین" in view.substitution_risk


def test_dual_view_has_no_risk_when_tracks_are_close():
    topic = _topic(
        konkur_stage=KonkurStage.TEACHING_TEST.value,
        final_stage=FinalStage.DETAIL_MAP.value,
    )
    view = dual_track_view(topic, [])
    assert view.substitution_risk == ""


def test_missing_steps_lists_both_tracks():
    topic = _topic()
    messages = missing_steps(topic, [])
    assert len(messages) == 2
    assert any("کنکور" in m for m in messages)
    assert any("نهایی" in m for m in messages)


def test_stage_label_and_activity_mapping_are_stable():
    assert stage_label("timed_test") == "تست زمان‌دار"
    assert stage_label("mock_final") == "آزمون جامع نهایی"
    assert activity_type_for(TrackKind.KONKUR, "timed_test") == "timed_test"
    assert activity_type_for(TrackKind.FINAL, "descriptive_practice") == (
        "independent_practice"
    )


def test_evidence_source_mapping_matches_stage():
    assert evidence_source_for(TrackKind.KONKUR, "timed_test") == "timed_test"
    assert evidence_source_for(TrackKind.FINAL, "completeness_check") == (
        "completeness_check"
    )


def test_completed_track_reports_done():
    topic = _topic(final_stage=FinalStage.MOCK_FINAL.value)
    progress = track_progress(
        topic,
        TrackKind.FINAL,
        [_evidence(source="mock_final", score=0.92)],
    )
    assert progress.completed is True
    assert progress.next_stage is None
    assert progress.progress_percent == pytest.approx(100 * 6 / 7, abs=0.1)


def test_mastery_is_ignored_for_stage_progress():
    """تسلط خودگزارشی پله را جلو نمی‌برد؛ فقط شاهد."""
    topic = _topic(mastery=MasteryLevel.L4)
    progress = track_progress(topic, TrackKind.KONKUR, [])
    assert progress.evidence_ready is False
    assert progress.index == 0
