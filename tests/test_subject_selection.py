"""تست اثر انتخاب درس در فرم‌ها و اولویت‌بندی فعالیت‌های قدیمی."""

from __future__ import annotations

import datetime as dt

from k2.domain.models import Activity, ExamProfile, Subject, Topic
from k2.service import AdvisorService


def test_selected_subjects_reflect_active_profile_selection(service: AdvisorService):
    profile_id = service.create_exam_profile(
        ExamProfile(name="آزمون ۱۴۰۶", group_name="علوم تجربی", exam_year=1406)
    )
    active_id = service.create_subject(
        Subject(name="زیست‌شناسی", exam_profile_id=profile_id, is_selected=True)
    )
    inactive_id = service.create_subject(
        Subject(name="زمین‌شناسی", exam_profile_id=profile_id, is_selected=False)
    )

    assert [subject.id for subject in service.selected_subjects()] == [active_id]
    all_subjects = service.repo.list_subjects(profile_id, include_unselected=True)
    assert {subject.id for subject in all_subjects} == {active_id, inactive_id}


def test_inactive_subject_reduces_old_topic_activity_weight_without_hiding_it(
    service: AdvisorService,
):
    profile_id = service.create_exam_profile(
        ExamProfile(name="آزمون ۱۴۰۶", group_name="علوم تجربی", exam_year=1406)
    )
    selected_id = service.create_subject(
        Subject(
            name="زیست‌شناسی", exam_profile_id=profile_id,
            coefficient=2.0, is_selected=True,
        )
    )
    inactive_id = service.create_subject(
        Subject(
            name="زمین‌شناسی", exam_profile_id=profile_id,
            coefficient=2.0, is_selected=False,
        )
    )
    selected_topic = service.create_topic(Topic(subject_id=selected_id, name="سلول"))
    inactive_topic = service.create_topic(Topic(subject_id=inactive_id, name="زمین"))
    selected_activity = service.create_activity(
        Activity(
            title="مرور زیست", subject_id=selected_id, topic_id=selected_topic,
            est_minutes=30,
        )
    )
    inactive_activity = service.create_activity(
        Activity(
            title="مرور زمین‌شناسی قدیمی", subject_id=inactive_id,
            topic_id=inactive_topic, est_minutes=30,
        )
    )
    service._topic_weakness = lambda: {selected_topic: 1.0, inactive_topic: 1.0}

    planned = service._schedulable_activities(dt.date(2026, 10, 17))
    by_id = {activity.id: activity for activity in planned}

    assert selected_activity in by_id
    assert inactive_activity in by_id  # تاریخچه/فعالیت قدیمی حذف یا پنهان نشود.
    assert by_id[selected_activity].topic_weight == 2.0
    assert by_id[inactive_activity].topic_weight == 0.5
    assert by_id[inactive_activity].topic_weakness == 1.0


def test_automatic_exam_coefficient_priority_is_separate_from_personal_weight(service: AdvisorService):
    profile_id = service.create_exam_profile(
        ExamProfile(name="آزمون ۱۴۰۶", group_name="علوم تجربی", exam_year=1406)
    )
    high = service.create_subject(Subject(
        name="زیست‌شناسی", exam_profile_id=profile_id, coefficient=2.0,
        exam_coefficient=12.0, exam_coefficient_status="official_notice_republished",
        exam_coefficient_source="https://www.yjc.ir/fa/news/9132127/", is_selected=True,
    ))
    low = service.create_subject(Subject(
        name="زمین‌شناسی", exam_profile_id=profile_id, coefficient=2.0,
        exam_coefficient=1.0, exam_coefficient_status="official_notice_republished",
        exam_coefficient_source="https://www.yjc.ir/fa/news/9132127/", is_selected=True,
    ))
    high_topic = service.create_topic(Topic(subject_id=high, name="سلول"))
    low_topic = service.create_topic(Topic(subject_id=low, name="سنگ"))
    high_activity = service.create_activity(Activity(
        title="زیست", subject_id=high, topic_id=high_topic, est_minutes=30,
    ))
    low_activity = service.create_activity(Activity(
        title="زمین", subject_id=low, topic_id=low_topic, est_minutes=30,
    ))
    service.repo.set_setting("priority.use_exam_coefficients", "1")
    service.commit()
    automatic = {a.id: a for a in service._schedulable_activities(dt.date(2026, 10, 17))}

    assert automatic[high_activity].topic_weight == 3.0
    assert automatic[low_activity].topic_weight == 2.0 * (0.5 + 1 / 12)
    # Neither the database's personal weight nor its official coefficient was rewritten.
    saved = {s.id: s for s in service.repo.list_subjects(profile_id)}
    assert saved[high].coefficient == 2.0 and saved[high].exam_coefficient == 12.0

    service.repo.set_setting("priority.use_exam_coefficients", "0")
    service.commit()
    personal_only = {a.id: a for a in service._schedulable_activities(dt.date(2026, 10, 17))}
    assert personal_only[high_activity].topic_weight == 2.0
    assert personal_only[low_activity].topic_weight == 2.0
