"""تست راه‌اندازی خالی و دریافت دادهٔ واقعی کاربر."""

from __future__ import annotations

import datetime as _dt

from k2.domain.enums import FixedEventKind, RoutineKind, RoutineScope
from k2.domain.models import Activity, EventException, FixedEvent, Routine
from k2.onboarding import (
    ONBOARDING_STEPS,
    OnboardingState,
    detect_event_conflicts,
    parse_clock_pair,
    parse_subjects,
    summarize,
)
from k2.service import (
    LEGACY_IMPORTED_EVENT_SIGNATURES,
    LEGACY_IMPORTED_ROUTINE_SIGNATURES,
    AdvisorService,
)


def test_new_install_has_no_user_or_sample_data(service: AdvisorService):
    assert service.repo.list_fixed_events() == []
    assert service.repo.list_routines() == []
    assert service.list_activities() == []
    assert service.list_attempts() == []
    assert service.list_review_items() == []
    assert service.active_exam_profile() is None


def _seed_legacy_schedule(service: AdvisorService) -> None:
    for title, kind, subject_id, weekday, start, end, recorded, notes in LEGACY_IMPORTED_EVENT_SIGNATURES:
        service.repo.create_fixed_event(FixedEvent(
            title=title,
            kind=FixedEventKind(kind),
            subject_id=subject_id,
            weekday=weekday,
            start_minute=start,
            end_minute=end,
            is_recorded=recorded,
            notes=notes,
        ))
    for title, kind, start, end, weekdays, scope, counts_as_study in LEGACY_IMPORTED_ROUTINE_SIGNATURES:
        service.repo.create_routine(Routine(
            title=title,
            kind=RoutineKind(kind),
            start_minute=start,
            end_minute=end,
            weekdays=frozenset(weekdays),
            scope=RoutineScope(scope),
            counts_as_study=counts_as_study,
        ))
    service.repo.set_setting("schedule.sample_imported", "1")
    service.conn.commit()


def test_untouched_legacy_seed_is_removed_but_real_records_are_preserved(tmp_path):
    db = tmp_path / "legacy.db"
    old_service = AdvisorService(db)
    old_service.create_activity(Activity(title="فعالیت واقعی", est_minutes=30, remaining_minutes=30))
    _seed_legacy_schedule(old_service)
    old_service.close()

    upgraded = AdvisorService(db)
    try:
        assert upgraded.repo.list_fixed_events() == []
        assert upgraded.repo.list_routines() == []
        assert [item.title for item in upgraded.list_activities()] == ["فعالیت واقعی"]
        assert upgraded.repo.get_setting("schedule.sample_imported") == "legacy-cleaned"
    finally:
        upgraded.close()


def test_modified_legacy_schedule_is_not_deleted(tmp_path):
    db = tmp_path / "modified-legacy.db"
    old_service = AdvisorService(db)
    _seed_legacy_schedule(old_service)
    events = old_service.repo.list_fixed_events()
    events[0].title = "کلاس واقعی تغییرکرده"
    old_service.repo.update_fixed_event(events[0])
    old_service.conn.commit()
    old_service.close()

    upgraded = AdvisorService(db)
    try:
        assert len(upgraded.repo.list_fixed_events()) == len(LEGACY_IMPORTED_EVENT_SIGNATURES)
        assert len(upgraded.repo.list_routines()) == len(LEGACY_IMPORTED_ROUTINE_SIGNATURES)
        assert any(event.title == "کلاس واقعی تغییرکرده" for event in upgraded.repo.list_fixed_events())
    finally:
        upgraded.close()


def test_legacy_seed_with_an_extra_duplicate_is_preserved(tmp_path):
    db = tmp_path / "duplicated-legacy.db"
    old_service = AdvisorService(db)
    _seed_legacy_schedule(old_service)
    old_service.repo.create_fixed_event(old_service.repo.list_fixed_events()[0])
    old_service.conn.commit()
    old_service.close()

    upgraded = AdvisorService(db)
    try:
        assert len(upgraded.repo.list_fixed_events()) == len(LEGACY_IMPORTED_EVENT_SIGNATURES) + 1
        assert len(upgraded.repo.list_routines()) == len(LEGACY_IMPORTED_ROUTINE_SIGNATURES)
        assert upgraded.repo.get_setting("schedule.sample_imported") == "1"
    finally:
        upgraded.close()


def test_legacy_seed_with_user_exception_is_preserved(tmp_path):
    db = tmp_path / "exception-legacy.db"
    old_service = AdvisorService(db)
    _seed_legacy_schedule(old_service)
    event = old_service.repo.list_fixed_events()[0]
    old_service.repo.create_exception(EventException(
        event_id=event.id,
        date=_dt.date(2026, 10, 17),
        reason="تغییر واقعی کاربر",
    ))
    old_service.conn.commit()
    old_service.close()

    upgraded = AdvisorService(db)
    try:
        assert len(upgraded.repo.list_fixed_events()) == len(LEGACY_IMPORTED_EVENT_SIGNATURES)
        assert len(upgraded.repo.list_routines()) == len(LEGACY_IMPORTED_ROUTINE_SIGNATURES)
        assert upgraded.repo.list_exceptions(_dt.date(2026, 10, 17))[0].reason == "تغییر واقعی کاربر"
    finally:
        upgraded.close()


def test_weekly_schedule_is_optional_and_no_fake_sunday_step():


    steps = {step.key: step for step in ONBOARDING_STEPS}
    assert steps["weekly_schedule"].kind == "schedule"
    assert not steps["weekly_schedule"].required
    assert "sunday_recorded" not in steps
    assert "تعارض" not in steps["weekly_schedule"].description


def test_onboarding_state_is_resumable():
    state = OnboardingState()
    state.set_value("student_name", "رضا")
    state.complete_step("student_name")
    restored = OnboardingState.from_json(state.to_json())
    assert restored.values["student_name"] == "رضا"
    assert restored.current_index == 1
    assert restored.unresolved_blocking_questions() == []


def test_legacy_onboarding_sample_text_is_removed_without_touching_user_records():
    legacy = OnboardingState.from_json(
        '{"values":{"student_name":"کاربر","weekly_schedule":"14 رویداد ثابت وارد شد.",'
        '"sunday_recorded":"شیمی"},"completed_steps":["weekly_schedule","sunday_recorded"],'
        '"current_index":12}'
    )
    assert legacy.values == {"student_name": "کاربر"}
    assert legacy.completed_steps == set()
    assert legacy.current_index == 11


def test_parse_clock_pair():
    assert parse_clock_pair("۲۳:۰۰ تا ۰۶:۰۰") == (23 * 60, 6 * 60)
    assert parse_clock_pair("23:00 - 06:00") == (23 * 60, 6 * 60)
    assert parse_clock_pair("نامعتبر") is None


def test_parse_subjects():
    result = parse_subjects("ریاضی:۳, فیزیک:۳, زیست:۲")
    assert result == [("ریاضی", 3.0), ("فیزیک", 3.0), ("زیست", 2.0)]
    assert parse_subjects("ریاضی") == [("ریاضی", 1.0)]


def test_summarize_contains_user_values_without_sample_sunday():
    state = OnboardingState()
    state.set_value("student_name", "رضا")
    state.set_value("exam_name", "کنکور")
    lines = summarize(state)
    assert any("رضا" in line for line in lines)
    assert any("کنکور" in line for line in lines)
    assert not any("یکشنبه" in line for line in lines)


def test_real_event_conflicts_are_detected_without_preloaded_events(service: AdvisorService):
    assert service.schedule_conflicts() == []
    first = FixedEvent(title="کلاس الف", weekday=1, start_minute=900, end_minute=1140)
    second = FixedEvent(title="کلاس ب", weekday=1, start_minute=915, end_minute=1245)
    service.create_fixed_event(first)
    service.create_fixed_event(second)
    conflicts = service.schedule_conflicts()
    assert len(conflicts) == 1
    assert {conflicts[0].first_title, conflicts[0].second_title} == {"کلاس الف", "کلاس ب"}


def test_dynamic_conflict_detection_checks_nested_overlaps_and_ignores_recorded():
    events = [
        FixedEvent(title="بلند", weekday=2, start_minute=10 * 60, end_minute=14 * 60),
        FixedEvent(title="درونی", weekday=2, start_minute=11 * 60, end_minute=12 * 60),
        FixedEvent(title="ضبطی", weekday=2, start_minute=11 * 60, end_minute=13 * 60, is_recorded=True),
    ]
    conflicts = detect_event_conflicts(events)
    assert len(conflicts) == 1
    assert conflicts[0].weekday == 2
    assert {conflicts[0].first_title, conflicts[0].second_title} == {"بلند", "درونی"}


def test_user_schedule_affects_capacity(service: AdvisorService):
    service.wake_minute = 6 * 60
    service.sleep_minute = 23 * 60
    saturday = _dt.date(2026, 10, 10)
    assert service.build_context(saturday).capacity_for(saturday).fixed_minutes == 0
    service.create_fixed_event(
        FixedEvent(title="کلاس خودم", weekday=0, start_minute=15 * 60, end_minute=17 * 60)
    )
    breakdown = service.build_context(saturday).capacity_for(saturday)
    assert breakdown.fixed_minutes > 0
    assert breakdown.raw_minutes < breakdown.awake_minutes


def test_service_schedule_crud_is_persistent_and_detects_conflict(service: AdvisorService):
    first = FixedEvent(title="کلاس الف", weekday=0, start_minute=600, end_minute=720)
    second = FixedEvent(title="کلاس ب", weekday=0, start_minute=700, end_minute=800)
    service.create_fixed_event(first)
    service.create_fixed_event(second)
    assert service.schedule_conflicts()
    second.is_recorded = True
    service.update_fixed_event(second)
    assert not service.schedule_conflicts()
    service.delete_fixed_event(second.id)
    assert len(service.repo.list_fixed_events()) == 1
