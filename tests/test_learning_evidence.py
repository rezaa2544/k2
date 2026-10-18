"""ذخیرهٔ شاهد یادگیری و ارتقای تسلط با فاصله/تأخیر/انتقال."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from k2.domain.enums import ContentType, MasteryLevel
from k2.domain.models import ExamProfile, LearningEvidence, ReviewItem, Subject, Topic
from k2.service import AdvisorService


def test_learning_evidence_persists_and_drives_operational_mastery(tmp_path: Path):
    db_path = tmp_path / "learning.db"
    service = AdvisorService(db_path)
    profile_id = service.create_exam_profile(ExamProfile(name="آزمون هدف", exam_year=1406))
    subject_id = service.create_subject(Subject(name="ریاضی", exam_profile_id=profile_id))
    topic_id = service.create_topic(Topic(
        subject_id=subject_id, subject_name="ریاضی", name="تابع",
        content_type=ContentType.CALCULATIONAL,
    ))
    for day, source, score in (
        (1, "diagnostic", 0.92),
        (6, "delayed", 0.88),
        (10, "transfer", 0.86),
    ):
        service.record_learning_evidence(LearningEvidence(
            topic_id=topic_id, observed_on=dt.date(2026, 10, day),
            source=source, score=score, item_count=10, confidence=3,
            duration_seconds=240,
        ))
    assessment = service.assess_topic(topic_id)
    assert assessment.level == MasteryLevel.L4
    assert assessment.distinct_sessions == 3
    assert assessment.delayed_confirmed and assessment.transfer_confirmed
    service.close()

    reopened = AdvisorService(db_path)
    try:
        evidence = reopened.list_learning_evidence(topic_id)
        assert [item.source for item in evidence] == ["diagnostic", "delayed", "transfer"]
        assert reopened.assess_topic(topic_id).level == MasteryLevel.L4
        topic = next(t for t in reopened.list_topics() if t.id == topic_id)
        assert topic.mastery == MasteryLevel.L4
    finally:
        reopened.close()


def test_review_result_is_recorded_as_topic_evidence_without_claiming_l4(tmp_path: Path):
    service = AdvisorService(tmp_path / "review-evidence.db")
    try:
        profile_id = service.create_exam_profile(ExamProfile(name="آزمون", exam_year=1406))
        subject_id = service.create_subject(Subject(name="زیست‌شناسی", exam_profile_id=profile_id))
        topic_id = service.create_topic(Topic(
            subject_id=subject_id, subject_name="زیست‌شناسی", name="سلول",
            content_type=ContentType.DIAGRAM,
        ))
        review_id = service.create_review_item(ReviewItem(
            topic_id=topic_id, subject_id=subject_id, label="اجزای سلول",
            due_date=dt.date(2026, 10, 17),
        ))
        service.record_review(review_id, correct=True, confidence=3, today=dt.date(2026, 10, 17))
        evidence = service.list_learning_evidence(topic_id)
        assert len(evidence) == 1
        assert evidence[0].source == "review"
        assert evidence[0].score == 1.0
        assert service.assess_topic(topic_id).level != MasteryLevel.L4
    finally:
        service.close()


def test_topic_recommendation_is_subject_specific_and_pathway_avoids_open_duplicates(tmp_path: Path):
    service = AdvisorService(tmp_path / "pathway.db")
    try:
        profile_id = service.create_exam_profile(ExamProfile(name="آزمون هنر", exam_year=1406, group_name="هنر"))
        subject_id = service.create_subject(Subject(name="خلاقیت تصویری و تجسمی", exam_profile_id=profile_id))
        topic_id = service.create_topic(Topic(
            subject_id=subject_id, subject_name="خلاقیت تصویری و تجسمی",
            name="ترکیب‌بندی پایه", content_type=ContentType.PRACTICAL,
        ))
        _assessment, prescription = service.recommend_topic(topic_id)
        assert any("خروجی قابل مشاهده" in method or "تمرین تولیدی" in method for method in prescription.methods)
        first = service.generate_topic_pathway(topic_id)
        second = service.generate_topic_pathway(topic_id)
        assert first
        assert second == []
        assert all(activity.topic_id == topic_id for activity in first)
    finally:
        service.close()
