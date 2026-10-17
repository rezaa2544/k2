"""تست راه‌اندازی و دادهٔ نمونهٔ برنامه (ONB-01 تا ONB-05)."""

from __future__ import annotations

import datetime as _dt

import pytest

from k2.onboarding import (
    ONBOARDING_STEPS,
    OnboardingState,
    build_sample_fixed_events,
    build_sample_routines,
    detect_sample_conflicts,
    detect_event_conflicts,
    parse_clock_pair,
    parse_subjects,
    summarize,
)
from k2.service import AdvisorService
from k2.domain.models import FixedEvent


def test_sample_schedule_contains_all_week_days():
    events = build_sample_fixed_events()
    weekdays = {event.weekday for event in events}
    assert weekdays == {0, 1, 2, 3, 4, 5, 6}
    # شنبه: زیست و فیزیک
    saturday = [e for e in events if e.weekday == 0]
    assert {e.subject_name for e in saturday} == {"زیست", "فیزیک"}


def test_sample_schedule_contains_recorded_geology_class():
    events = build_sample_fixed_events()
    recorded = [e for e in events if e.is_recorded]
    assert recorded
    assert recorded[0].subject_name == "زمین‌شناسی"


def test_sunday_conflict_is_detected_and_not_hidden():
    conflicts = detect_sample_conflicts()
    assert conflicts
    conflict = conflicts[0]
    assert conflict.weekday == 1  # یکشنبه
    assert "شیمی" in conflict.first_title
    assert "دینی" in conflict.second_title
    assert conflict.question
    assert "تعارض" in conflict.describe()


def test_sample_routines_include_sleep_and_meals():
    routines = build_sample_routines()
    titles = {r.title for r in routines}
    assert any("خواب" in t for t in titles)
    assert any("غذا" in t or t in {"صبحانه", "ناهار", "شام"} for t in titles)


def test_state_is_resumable():
    state = OnboardingState()
    state.set_value("student_name", "رضا")
    state.complete_step("student_name")
    assert state.current_index == 1
    restored = OnboardingState.from_json(state.to_json())
    assert restored.values["student_name"] == "رضا"
    assert restored.current_index == 1


def test_blocking_question_blocks_completion():
    state = OnboardingState()
    questions = state.unresolved_blocking_questions()
    assert questions
    assert any("شیمی" in q for q in questions)
    state.complete_step("sunday_recorded")
    assert state.unresolved_blocking_questions() == []


def test_parse_clock_pair():
    assert parse_clock_pair("۲۳:۰۰ تا ۰۶:۰۰") == (23 * 60, 6 * 60)
    assert parse_clock_pair("23:00 - 06:00") == (23 * 60, 6 * 60)
    assert parse_clock_pair("نامعتبر") is None


def test_parse_subjects():
    result = parse_subjects("ریاضی:۳, فیزیک:۳, زیست:۲")
    assert result == [("ریاضی", 3.0), ("فیزیک", 3.0), ("زیست", 2.0)]
    assert parse_subjects("ریاضی") == [("ریاضی", 1.0)]


def test_summarize_contains_key_values():
    state = OnboardingState()
    state.set_value("student_name", "رضا")
    state.set_value("exam_name", "کنکور")
    lines = summarize(state)
    assert any("رضا" in line for line in lines)
    assert any("کنکور" in line for line in lines)


def test_service_imports_sample_schedule(service: AdvisorService):
    events, routines = service.import_sample_schedule()
    assert events > 0
    assert routines > 0
    assert len(service.repo.list_fixed_events()) == events
    assert len(service.repo.list_routines()) == routines


def test_imported_schedule_affects_capacity(service: AdvisorService):
    service.import_sample_schedule()
    service.wake_minute = 6 * 60
    service.sleep_minute = 23 * 60
    saturday = _dt.date(2026, 10, 10)
    breakdown = service.build_context(saturday).capacity_for(saturday)
    # کلاس‌ها و بازه‌های ضروری باید از ظرفیت کم شوند
    assert breakdown.fixed_minutes > 0
    assert breakdown.raw_minutes < breakdown.awake_minutes


def test_onboarding_steps_cover_required_areas():
    keys = {step.key for step in ONBOARDING_STEPS}
    for required in (
        "exam_group",
        "exam_date",
        "exam_date_status",
        "subjects",
        "sleep_time",
        "weekly_schedule",
        "sunday_recorded",
    ):
        assert required in keys


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
