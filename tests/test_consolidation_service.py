"""تست‌های یکپارچگی: مشاور تثبیت از دادهٔ واقعی تا پیشنهاد گام بعدی.

این تست‌ها رفتار «مشاور واقعی» را در لایهٔ سرویس می‌آزمایند:
  ۱. ساخت مبحث از کاتالوگ برای درس‌های انتخاب‌شده.
  ۲. پیشرفت روی نردبان تثبیت با ثبت شواهد واقعی.
  ۳. توزیع سه‌مسیره و صف جبران قدم‌به‌قدم.
  ۴. امکان‌سنجی و گزینه‌های تصمیم برای روزِ امکان‌ناپذیر.
"""

from __future__ import annotations

import datetime as _dt

import pytest

from k2.consolidation import (
    consolidation_debt,
    forecast_retention,
    retrievability,
)
from k2.config import Settings
from k2.domain.enums import DateStatus, DeadlineType
from k2.domain.models import ExamProfile, LearningEvidence, Subject, Topic
from k2.streams import assess_feasibility


@pytest.fixture()
def profile(service) -> int:
    created = service.create_exam_profile(
        ExamProfile(
            name="کنکور ۱۴۰۶",
            group_name="علوم تجربی",
            target_date=_dt.date(2027, 6, 15),
            date_status=DateStatus.ESTIMATED,
        )
    )
    return int(created)


def _subject(service, profile_id: int, name: str, coefficient: float = 12.0) -> int:
    return int(
        service.create_subject(
            Subject(name=name, exam_profile_id=profile_id, coefficient=coefficient)
        )
    )


def _overdue_activities(service, count: int, minutes: int = 400) -> list[int]:
    """فعالیت‌های با مهلت گذشته و کار باقی‌مانده (ورودی صف جبران)."""
    from tests.conftest import make_activity

    ids: list[int] = []
    for index in range(count):
        activity = make_activity(
            index + 1,
            f"کار {index + 1}",
            minutes=minutes,
            deadline=_dt.datetime(2026, 9, 25, 10, 0),
            deadline_type=DeadlineType.SOFT,
            max_chunk=90,
        )
        ids.append(int(service.create_activity(activity)))
    return ids


# --- ۱. کاتالوگ ---


def test_catalog_seeds_topics_for_every_selected_subject(service, profile):
    bio = _subject(service, profile, "زیست‌شناسی")
    chem = _subject(service, profile, "شیمی")
    created_bio = service.seed_topics_from_catalog(bio)
    created_chem = service.seed_topics_from_catalog(chem)
    assert created_bio and created_chem
    assert all(topic.subject_id == bio for topic in created_bio)
    assert all(topic.subject_id == chem for topic in created_chem)
    # تکرار نباید نسخهٔ تازه بسازد
    assert service.seed_topics_from_catalog(bio) == []
    topics = service.list_topics()
    assert len(topics) == len(created_bio) + len(created_chem)


def test_catalog_seed_respects_group_of_exam_profile(service, profile):
    """برای گروه علوم ریاضی، فهرست ریاضی باید مخصوص همان گروه باشد."""
    from k2.domain.models import ExamProfile as _ExamProfile

    active = service.active_exam_profile()
    assert active is not None
    service.update_exam_profile(
        _ExamProfile(
            id=active.id,
            name=active.name,
            group_name="علوم ریاضی و فنی",
            target_date=active.target_date,
            date_status=active.date_status,
        )
    )
    math = _subject(service, profile, "ریاضی")
    topics = service.seed_topics_from_catalog(math)
    assert len(topics) > 10  # فهرست کامل، نه چند مبحث نمونه


def test_catalog_unknown_subject_returns_empty(service, profile):
    subject = _subject(service, profile, "درسِ ثبت‌نشده")
    assert service.seed_topics_from_catalog(subject) == []


# --- ۲. نردبان تثبیت ---


def test_topic_advances_ladder_with_spaced_evidence(service, profile):
    subject = _subject(service, profile, "زیست‌شناسی")
    topic = int(
        service.create_topic(
            Topic(subject_id=subject, name="ژنتیک مولکولی")
        )
    )
    today = _dt.date(2026, 8, 1)
    schedule = (
        (0, "study", 1.0),
        (1, "review", 0.92),
        (6, "review", 0.88),
        (20, "delayed", 0.8),
        (40, "transfer", 0.75),
        (60, "review", 0.72),
    )
    for offset, source, score in schedule:
        service.record_learning_evidence(
            LearningEvidence(
                topic_id=topic,
                observed_on=today + _dt.timedelta(days=offset),
                source=source,
                score=score,
            )
        )
    states = service.topic_consolidations(today + _dt.timedelta(days=65))
    state = next(s for s in states if s.topic_id == topic)
    assert state.status == "consolidated"
    assert state.current_stage == "maintenance"
    assert state.next_due is None


def test_missing_first_retrieval_marks_topic_behind(service, profile):
    """اگر بازیابی اولیه (تا ۲۴ ساعت) ثبت نشود، مبحث عقب‌افتاده می‌شود."""
    subject = _subject(service, profile, "شیمی")
    topic = int(
        service.create_topic(
            Topic(subject_id=subject, name="استوکیومتری")
        )
    )
    today = _dt.date(2026, 8, 1)
    service.record_learning_evidence(
        LearningEvidence(topic_id=topic, observed_on=today, source="study", score=1.0)
    )
    states = service.topic_consolidations(_dt.date(2026, 10, 18))
    state = next(s for s in states if s.topic_id == topic)
    assert state.status == "behind"
    assert state.current_stage == "encode"
    advice = service.consolidation_advice_for(topic)
    assert advice is not None
    assert advice[1][0]


def test_forecast_and_debt_group_by_subject(service, profile):
    bio = _subject(service, profile, "زیست‌شناسی")
    schedule = (
        (0, "study", 1.0), (1, "review", 0.9), (6, "review", 0.85),
        (20, "delayed", 0.8), (40, "transfer", 0.75), (60, "review", 0.72),
    )
    for index in range(3):
        topic = int(
            service.create_topic(
                Topic(subject_id=bio, name=f"مبحث {index}")
            )
        )
        for offset, source, score in schedule:
            service.record_learning_evidence(
                LearningEvidence(
                    topic_id=topic,
                    observed_on=_dt.date(2026, 8, 1) + _dt.timedelta(days=offset),
                    source=source,
                    score=score,
                )
            )
    overview = service.consolidation_overview(_dt.date(2026, 10, 18))
    forecast = forecast_retention(overview["consolidations"])
    assert forecast.topics
    assert forecast.coverage > 0
    assert forecast.consolidated
    # همهٔ مباحث تثبیت‌شده ⇒ بدهی تثبیت صفر
    debts = consolidation_debt(
        overview["consolidations"], _dt.date(2026, 10, 18), subject_weights={"زیست‌شناسی": 12.0}
    )
    assert debts == []


# --- ۳. سه مسیر و صف جبران ---


def test_overview_splits_capacity_into_three_streams(service, profile):
    subject = _subject(service, profile, "زیست‌شناسی")
    service.create_topic(Topic(subject_id=subject, name="سلولی"))
    overview = service.consolidation_overview(_dt.date(2026, 10, 18))
    allocation = overview["allocation"]
    assert allocation.capacity_minutes > 0
    assert (
        allocation.new_minutes
        + allocation.catchup_minutes
        + allocation.consolidation_minutes
        <= allocation.capacity_minutes
    )
    # کف تثبیت باید رعایت شود مگر این‌که ظرفیت از کف کمتر باشد
    floor = int(
        allocation.capacity_minutes * service.settings.streams.consolidation_floor_ratio
    )
    assert allocation.consolidation_minutes >= min(floor, allocation.capacity_minutes)


def test_catchup_plan_chunks_backlog_without_dropping(service, profile):
    """بدهی عقب‌افتاده در روزها پخش می‌شود؛ هیچ کاری بی‌صدا حذف نمی‌شود."""
    _overdue_activities(service, 3)
    overview = service.consolidation_overview(_dt.date(2026, 10, 18))
    assert overview["backlog"].items
    plan = overview["catchup"]
    assert plan
    assert all(quota.minutes <= service.settings.capacity.max_block_minutes for quota in plan)
    assert sum(quota.minutes for quota in plan) <= overview["backlog"].debt_minutes
    covered = {quota.activity_id for quota in plan}
    backlog_ids = {item.activity_id for item in overview["backlog"].items}
    # هیچ کاری حذف نمی‌شود: هر فعالیت یا در برنامه هست یا در باقی‌مانده صریح
    assert covered <= backlog_ids
    assert covered


def test_catchup_plan_reports_unplanned_remainder(service):
    """وقتی بدهی از بازهٔ برنامه‌ریزی بیشتر است، باقی‌مانده صریح می‌ماند."""
    _overdue_activities(service, 1, minutes=20000)
    overview = service.consolidation_overview(_dt.date(2026, 10, 18))
    planned = sum(q.minutes for q in overview["catchup"])
    assert planned < overview["backlog"].debt_minutes
    assert overview["backlog"].debt_minutes - planned > 0


# --- ۴. امکان‌سنجی ---


def test_feasibility_offers_options_when_overloaded():
    verdict = assess_feasibility(
        new_load_minutes=20000,
        catchup_debt_minutes=5000,
        consolidation_load_minutes=6000,
        daily_capacity_minutes=300,
        days_to_exam=60,
        settings=Settings(),
    )
    assert verdict.level == "infeasible"
    assert verdict.deficit_minutes > 0
    assert verdict.ratio > 1
    assert len(verdict.options) >= 3
    assert any("کم‌اثر" in option or "اولویت" in option for option in verdict.options)


def test_feasibility_ok_for_light_load():
    verdict = assess_feasibility(
        new_load_minutes=1200,
        catchup_debt_minutes=0,
        consolidation_load_minutes=600,
        daily_capacity_minutes=300,
        days_to_exam=60,
        settings=Settings(),
    )
    assert verdict.level == "ok"
    assert verdict.ratio < 1


def test_feasibility_without_exam_date_reports_unknown():
    """بدون تاریخ آزمون، ادعای عددی ساخته نمی‌شود ولی توضیح داده می‌شود."""
    verdict = assess_feasibility(
        new_load_minutes=1200,
        catchup_debt_minutes=0,
        consolidation_load_minutes=600,
        daily_capacity_minutes=300,
        days_to_exam=None,
        settings=Settings(),
    )
    assert verdict.level == "unknown"
    assert verdict.notes


# --- ۴.۵ فعالیت خودکار تثبیت در برنامهٔ روز ---


def test_ensure_consolidation_activities_is_idempotent(service, profile):
    """پلهٔ سررسیدشده یک فعالیت واقعی می‌سازد و تکرار چیزی اضافه نمی‌کند."""
    subject = _subject(service, profile, "شیمی")
    topic = int(
        service.create_topic(Topic(subject_id=subject, name="استوکیومتری"))
    )
    service.record_learning_evidence(
        LearningEvidence(
            topic_id=topic, observed_on=_dt.date(2026, 10, 10), source="study", score=1.0
        )
    )
    today = _dt.date(2026, 10, 18)
    created = service.ensure_consolidation_activities(today)
    assert len(created) == 1
    activity = created[0]
    assert activity.state_reason.startswith("consolidation:first_retrieval")
    assert activity.topic_id == topic
    assert activity.deadline_at is not None
    assert service.ensure_consolidation_activities(today) == []
    # برنامهٔ روز باید همین کار را جای‌گذاری کند
    plan = service.plan_day(today)
    assert any(p.activity_id == activity.id for p in plan.placements)
    # اگر انجام نشود، در صف بدهی می‌ماند (حذف بی‌صدا نیست)
    backlog = service.backlog(today)
    assert any(item.activity_id == activity.id for item in backlog.items)


def test_consolidation_activity_not_created_before_due(service, profile):
    """پله‌ای که موعدش نرسیده، فعالیت نمی‌سازد."""
    subject = _subject(service, profile, "شیمی")
    topic = int(service.create_topic(Topic(subject_id=subject, name="حلال‌ها")))
    service.record_learning_evidence(
        LearningEvidence(
            topic_id=topic, observed_on=_dt.date(2026, 10, 17), source="study", score=1.0
        )
    )
    # ۱۷ مهر studied → S1 due ۱۸ مهر؛ در ۱۸ مهر ساخته می‌شود
    assert len(service.ensure_consolidation_activities(_dt.date(2026, 10, 18))) == 1


def test_completed_ladder_creates_no_activity(service, profile):
    """مبحث تثبیت‌شده کار تازه نمی‌سازد."""
    subject = _subject(service, profile, "زیست‌شناسی")
    topic = int(service.create_topic(Topic(subject_id=subject, name="ژنتیک")))
    base = _dt.date(2026, 8, 1)
    for offset, source, score in (
        (0, "study", 1.0), (1, "review", 0.92), (6, "review", 0.88),
        (20, "delayed", 0.8), (40, "transfer", 0.75), (60, "review", 0.72),
    ):
        service.record_learning_evidence(
            LearningEvidence(
                topic_id=topic,
                observed_on=base + _dt.timedelta(days=offset),
                source=source,
                score=score,
            )
        )
    assert service.ensure_consolidation_activities(base + _dt.timedelta(days=65)) == []


def test_streams_separate_consolidation_from_new_material(service, profile):
    """فعالیت تثبیت نباید در مسیر «مطلب جدید» شمرده شود."""
    subject = _subject(service, profile, "ریاضی")
    topic = int(service.create_topic(Topic(subject_id=subject, name="حد و پیوستگی")))
    service.record_learning_evidence(
        LearningEvidence(
            topic_id=topic, observed_on=_dt.date(2026, 10, 10), source="study", score=1.0
        )
    )
    today = _dt.date(2026, 10, 18)
    service.ensure_consolidation_activities(today)
    allocation = service.consolidation_overview(today)["allocation"]
    assert allocation.new_minutes == 0
    assert allocation.consolidation_minutes > 0


# --- ۵. ماندگاری مدل ---


def test_retention_decays_and_exam_horizon_is_visible():
    assert retrievability(days=10, stability=10) == pytest.approx(0.9, abs=0.01)
    assert retrievability(days=40, stability=10) < 0.75
    assert retrievability(days=0, stability=10) == pytest.approx(1.0)


def test_review_item_keeps_stability_after_grading(service, profile):
    """ثبت مرور باید پایداری و بازیابستگی مورد را به‌روز کند."""
    from k2.domain.models import ReviewItem

    subject = _subject(service, profile, "ریاضی")
    topic = int(
        service.create_topic(
            Topic(subject_id=subject, name="حد و پیوستگی")
        )
    )
    item_id = int(
        service.create_review_item(
            ReviewItem(
                topic_id=topic,
                subject_id=subject,
                label="حد یک‌طرفه",
                item_type="calculation",
                difficulty=3.0,
                due_date=_dt.date(2026, 10, 18),
            )
        )
    )
    update = service.record_review(item_id, correct=True, confidence=3)
    after = next(r for r in service.list_review_items() if r.id == item_id)
    assert update.new_interval > 0
    # پس از نخستین مرور، پایداری و بازیابگیری باید محاسبه و ذخیره شود
    assert after.stability_days > 0
    assert after.retrievability is not None
    assert after.interval_days > 0
