"""تست end-to-end: سناریوی کامل از کلاس تا آزمون تأخیری (QA-02).

سناریو:
    کلاس ضبط‌شدهٔ ناقص → ادامه → تکلیف → تست → آزمون → تحلیل خطا →
    رفع اشکال → مرور تأخیری.

این تست از لایهٔ سرویس (همان مسیری که رابط کاربری استفاده می‌کند) عبور
می‌کند و در پایان داده‌ها را در پایگاه داده بررسی می‌کند.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

import pytest

from k2.domain.enums import (
    ActivityState,
    ActivityType,
    DeadlineType,
    EnergyNeed,
    ErrorCode,
    ExamKind,
    ReviewState,
)
from k2.domain.models import (
    Activity,
    ExamProfile,
    ExamQuestion,
    Subject,
    Topic,
)
from k2.review_engine import create_review_item
from k2.service import AdvisorService

TODAY = _dt.date(2026, 10, 10)


@pytest.fixture()
def e2e_service(tmp_path: Path) -> AdvisorService:
    service = AdvisorService(tmp_path / "e2e.db")

    # ۱) پروفایل آزمون و دروس (قابل ویرایش، بدون دادهٔ رسمی ثابت)
    profile = ExamProfile(
        name="کنکور سراسری (پروفایل نمونه)",
        group_name="ریاضی",
        target_date=_dt.date(2027, 4, 1),
    )
    service.create_exam_profile(profile)

    subject = Subject(name="ریاضی", exam_profile_id=profile.id, coefficient=3.0)
    service.create_subject(subject)
    topic = Topic(subject_id=subject.id, name="تابع")
    service.create_topic(topic)

    service.wake_minute = 6 * 60
    service.sleep_minute = 23 * 60
    service.energy_level = 3
    return service


def test_full_learning_cycle(e2e_service: AdvisorService, tmp_path: Path):
    service = e2e_service

    # --- گام ۱: کلاس ضبط‌شدهٔ ناقص ---
    recorded = Activity(
        title="کلاس ضبط‌شدهٔ ریاضی — جلسهٔ ۱",
        type=ActivityType.RECORDED_CLASS,
        est_minutes=120,
        remaining_minutes=120,
        min_chunk=20,
        max_chunk=90,
        splittable=True,
        deadline_type=DeadlineType.SOFT,
        deadline_at=_dt.datetime(2026, 10, 12, 23, 59),
        energy_need=EnergyNeed.MEDIUM,
    )
    recorded_id = service.create_activity(recorded)

    # --- گام ۲: فعالیت وابسته (پردازش اولیه) که تا تکمیل کلاس مسدود است ---
    processing = Activity(
        title="پردازش اولیهٔ کلاس ریاضی",
        type=ActivityType.PROCESSING,
        est_minutes=30,
        remaining_minutes=30,
        depends_on=(recorded_id,),
        deadline_type=DeadlineType.SOFT,
        deadline_at=_dt.datetime(2026, 10, 12, 23, 59),
    )
    processing_id = service.create_activity(processing)

    # فعالیت وابسته باید Blocked باشد.
    activities = service.list_activities()
    dependent = next(a for a in activities if a.id == processing_id)
    assert dependent.state == ActivityState.BLOCKED

    # --- گام ۳: برنامه‌ریزی ---
    plan = service.plan_day(TODAY)
    assert plan.planned_minutes <= plan.capacity_minutes
    assert plan.placements

    # --- گام ۴: کلاس ضبط‌شده ناقص اجرا می‌شود ---
    service.start_activity(recorded_id)
    remaining = service.partial_activity(recorded_id, 45, resume_marker=2700)
    assert remaining > 0
    reloaded = service.repo.get_activity(recorded_id)
    assert reloaded is not None
    assert reloaded.state == ActivityState.PARTIAL
    assert reloaded.resume_marker == 2700
    assert reloaded.remaining_minutes == remaining

    # --- گام ۵: با تکمیل کلاس، فعالیت وابسته آزاد می‌شود ---
    service.complete_activity(recorded_id, 75)
    activities = service.list_activities()
    dependent = next(a for a in activities if a.id == processing_id)
    assert dependent.state in {ActivityState.READY, ActivityState.PLANNED}

    # --- گام ۶: اجرای پردازش، تکلیف و تست ---
    for activity_id, minutes in ((processing_id, 30),):
        service.start_activity(activity_id)
        service.complete_activity(activity_id, minutes)

    homework = Activity(
        title="تکلیف کلاس ریاضی",
        type=ActivityType.HOMEWORK,
        est_minutes=45,
        remaining_minutes=45,
        deadline_type=DeadlineType.SOFT,
        deadline_at=_dt.datetime(2026, 10, 12, 23, 59),
    )
    homework_id = service.create_activity(homework)
    service.start_activity(homework_id)
    service.complete_activity(homework_id, 50)

    test = Activity(
        title="تست زمان‌دار ریاضی",
        type=ActivityType.TIMED_TEST,
        est_minutes=30,
        remaining_minutes=30,
        splittable=False,
        deadline_type=DeadlineType.SOFT,
        deadline_at=_dt.datetime(2026, 10, 12, 23, 59),
    )
    test_id = service.create_activity(test)
    service.start_activity(test_id)
    service.complete_activity(test_id, 28)

    # --- گام ۷: ثبت آزمون با خطاها ---
    topic = service.repo.list_topics()[0]
    subject = service.repo.list_subjects()[0]
    questions = [
        ExamQuestion(number=1, status="correct", subject_id=subject.id, topic_id=topic.id),
        ExamQuestion(
            number=2,
            status="wrong",
            error_code=ErrorCode.E1,
            subject_id=subject.id,
            topic_id=topic.id,
        ),
        ExamQuestion(
            number=3,
            status="wrong",
            error_code=ErrorCode.E1,
            subject_id=subject.id,
            topic_id=topic.id,
        ),
        ExamQuestion(number=4, status="blank", subject_id=subject.id, topic_id=topic.id),
    ]
    attempt = service.record_attempt(
        name="آزمون جامع هفتگی",
        total=4,
        correct=1,
        wrong=2,
        blank=1,
        kind=ExamKind.MOCK,
        subject_id=subject.id,
        duration_minutes=60,
        questions=questions,
    )
    assert attempt.percentage == 25.0

    errors = service.repo.list_error_records(attempt.id)
    assert len(errors) == 2
    assert all(e.code == ErrorCode.E1 for e in errors)

    # --- گام ۸: تحلیل خطا ⇒ فعالیت اصلاحی با مهلت ---
    remediation = service.build_remediation(attempt.id)
    assert remediation.activities
    remedial = remediation.activities[0]
    assert remedial.deadline_at is not None
    assert "بازآموزی" in remedial.title

    # --- گام ۹: رفع اشکال (اجرای فعالیت اصلاحی) ---
    remedial_id = service.create_activity(remedial)
    service.start_activity(remedial_id)
    service.complete_activity(remedial_id, 45)

    # --- گام ۱۰: مرور تأخیری ---
    item = create_review_item(
        label="تابع — مشتق",
        subject_id=subject.id,
        topic_id=topic.id,
        item_type="formula",
        today=TODAY,
    )
    item_id = service.create_review_item(item)
    update = service.record_review(item_id, correct=True, confidence=3)
    assert update.new_interval > 0
    assert update.new_due is not None

    # --- گام ۱۱: گزارش و برنامهٔ نهایی ---
    weekly = service.weekly_report()
    assert weekly.total_activities > 0
    assert weekly.completed_activities > 0

    final_plan = service.plan_day(TODAY)
    assert final_plan.planned_minutes <= final_plan.capacity_minutes

    # --- گام ۱۲: پشتیبان‌گیری و بازیابی ---
    info = service.backup(tmp_path / "backups")
    assert info.path.exists()
    counts_before = service.repo.list_activities()
    service.restore(info.path)
    counts_after = service.repo.list_activities()
    assert len(counts_before) == len(counts_after)


def test_offline_operation_without_network(e2e_service: AdvisorService, monkeypatch):
    """هستهٔ برنامه نباید به شبکه نیاز داشته باشد."""
    import socket

    def blocked(*args, **kwargs):
        raise AssertionError("برنامه نباید به شبکه وصل شود")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)

    service = e2e_service
    plan = service.plan_day(TODAY)
    assert plan.capacity_minutes >= 0
    service.weekly_report(TODAY)
    service.backup()


def test_no_activity_is_silently_dropped(e2e_service: AdvisorService):
    """در طول چرخه، فعالیت‌ها بدون دلیل حذف نمی‌شوند."""
    service = e2e_service
    activity = Activity(
        title="کار بدون مهلت",
        type=ActivityType.PROCESSING,
        est_minutes=60,
        remaining_minutes=60,
    )
    activity_id = service.create_activity(activity)
    service.start_activity(activity_id)
    service.defer_activity(activity_id, "کم‌انرژی")
    reloaded = service.repo.get_activity(activity_id)
    assert reloaded is not None
    assert reloaded.state == ActivityState.DEFERRED
    assert reloaded.state_reason == "کم‌انرژی"
    events = service.repo.list_activity_events(activity_id)
    assert any(event.kind == "defer" for event in events)


def test_reopening_application_keeps_state(tmp_path: Path):
    """بستن و بازکردن دوبارهٔ برنامه نباید داده‌ای را از دست بدهد."""
    path = tmp_path / "reopen.db"
    service = AdvisorService(path)
    service.create_exam_profile(ExamProfile(name="آزمون ماندگار"))
    activity_id = service.create_activity(
        Activity(title="کار ماندگار", type=ActivityType.HOMEWORK)
    )
    service.close()

    service = AdvisorService(path)
    try:
        assert service.active_exam_profile().name == "آزمون ماندگار"
        assert service.list_activities()[0].title == "کار ماندگار"
    finally:
        service.close()
