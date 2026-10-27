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
    assert steps["weekly_schedule"].kind == "events"
    assert not steps["weekly_schedule"].required
    assert steps["class_attendance"].options == ("بله", "خیر")
    assert steps["classes"].kind == "events"
    assert steps["routines"].kind == "routines"
    assert "sunday_recorded" not in steps
    assert "تعارض" not in steps["weekly_schedule"].description


def test_all_essential_interview_questions_are_covered():
    """هر هفت پرسش ضروری سند onboarding در مصاحبه پرسیده می‌شود.

    مرجع: docs/USER_SCHEDULE_AND_ONBOARDING.md بخش ۳.
    """
    keys = {step.key: step for step in ONBOARDING_STEPS}
    # ۱) رشته/گروه و آزمون هدف و وضعیت تاریخ
    assert keys["exam_group"].required and keys["exam_name"].required
    assert keys["exam_date_status"].required
    assert set(keys["exam_date_status"].options) == {
        "رسمی (منبع ثبت‌شده)", "تخمینی", "نامشخص"
    }
    # ۲) خواب/بیداری و حداقل خواب مورد نظر
    assert keys["sleep_time"].required
    assert "min_sleep" in keys, "حداقل خواب مورد نظر پرسیده نشده است"
    assert keys["min_sleep"].kind == "choice"
    # ۳) منابع/کتاب
    assert keys["books"].kind == "books"
    # ۴) کلاس‌ها و تعهدات
    assert keys["classes"].kind == "events"
    assert keys["weekly_schedule"].kind == "events"
    # ۵) آزمون جامع: تکرار و سال تاریخ
    assert "comprehensive_exam_cycle" in keys, "چرخهٔ آزمون جامع پرسیده نشده است"
    assert "comprehensive_exam_date" in keys, "سال تاریخ ۳۰ مهر پرسیده نشده است"
    # ۶) طول معمول تست/تحلیل/تثبیت/تکلیف (کالیبراسیون)
    assert "typical_durations" in keys, "برآورد زمان هر نوع کار پرسیده نشده است"
    # ۷) سطح مبحثی (ONB-04)
    assert "topic_levels" in keys, "سطح اولیهٔ مبحث پرسیده نشده است"


def test_optional_steps_can_be_skipped_without_blocking():
    """گام‌های اختیاری قابل رد شدن‌اند؛ الزامی‌ها نه (تکمیل تدریجی)."""
    optional = [s.key for s in ONBOARDING_STEPS if not s.required]
    for key in ("min_sleep", "comprehensive_exam_cycle", "comprehensive_exam_date",
                "typical_durations", "topic_levels", "previous_results",
                "books", "classes", "weekly_schedule", "routines"):
        assert key in optional, f"گام {key} باید اختیاری باشد"
    # گام‌های اختیاری نباید پرسش مسدودکننده بسازند
    state = OnboardingState()
    for key in optional:
        state.complete_step(key)
    assert state.unresolved_blocking_questions() == []
    # گام سطح مبحثی عمداً به صفحهٔ مباحث ارجاع می‌دهد، نه برچسب کلی
    levels = {s.key: s for s in ONBOARDING_STEPS}["topic_levels"]
    assert "مبحث" in levels.description
    assert "اختیاری" in levels.description


def test_min_sleep_and_typical_durations_are_stored(service: AdvisorService, qapp, tmp_path):
    """حداقل خواب و برآورد زمان هر نوع کار در تنظیمات ذخیره می‌شوند."""
    from k2.ui.views.onboarding import OnboardingWizard

    wizard = OnboardingWizard(service)
    wizard.state.set_value("min_sleep", "۴۵۰")
    wizard.state.set_value("typical_durations", "۵۰، ۳۵، ۲۵، ۴۰")
    wizard._apply_to_profile()
    assert service.repo.get_setting("daily.sleep_target_minutes") == "450"
    import json

    defaults = json.loads(service.repo.get_setting("estimate.defaults") or "{}")
    assert defaults == {
        "testing": 50, "analysis": 35, "consolidation": 25, "homework": 40
    }


def test_min_sleep_rejects_non_numeric(service: AdvisorService, qapp, tmp_path):
    """مقدار نامعتبر حداقل خواب ذخیره نمی‌شود."""
    from k2.ui.views.onboarding import OnboardingWizard

    wizard = OnboardingWizard(service)
    wizard.state.set_value("min_sleep", "نامشخص")
    wizard._apply_to_profile()
    assert service.repo.get_setting("daily.sleep_target_minutes") is None


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
    assert legacy.current_index == next(i for i, step in enumerate(ONBOARDING_STEPS) if step.key == "energy_level")


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


def _seed_legacy_schedule_without_marker(service: AdvisorService) -> None:
    """همان bundle نمونه، ولی بدون marker ``schedule.sample_imported``.

    marker فقط در نسخه‌هایی گذاشته شده بود که خودشان داده را import کرده‌اند.
    پایگاه‌داده‌هایی که از مسیر دیگری (مثلاً کپی فایل یا نسخهٔ میانی) این
    داده را دارند marker ندارند، و پاک‌سازی آن‌ها را انجام نمی‌داد.
    """
    for title, kind, subject_id, weekday, start, end, recorded, notes in LEGACY_IMPORTED_EVENT_SIGNATURES:
        service.repo.create_fixed_event(FixedEvent(
            title=title, kind=FixedEventKind(kind), subject_id=subject_id,
            weekday=weekday, start_minute=start, end_minute=end,
            is_recorded=recorded, notes=notes,
        ))
    for title, kind, start, end, weekdays, scope, counts_as_study in LEGACY_IMPORTED_ROUTINE_SIGNATURES:
        service.repo.create_routine(Routine(
            title=title, kind=RoutineKind(kind), start_minute=start,
            end_minute=end, weekdays=frozenset(weekdays),
            scope=RoutineScope(scope), counts_as_study=counts_as_study,
        ))
    service.conn.commit()


def test_legacy_sample_schedule_is_removed_even_without_the_marker(tmp_path):
    """bundle نمونه باید حذف شود حتی اگر markerش نباشد.

    کاربر گفت: «دیتاهای اولیه (فقط زمانبندی‌ها) در برنامه هست که باید اونو
    حذف و برنامه به صورت خام باشه.» بدون این تست، پایگاه‌داده‌ای که marker
    ندارد برای همیشه دادهٔ نمونه را نگه می‌دارد و همان ساعت‌های ساختگی در
    صفحهٔ کلاس‌ها و در پنجرهٔ تعارض راه‌اندازی دیده می‌شوند.
    """
    db = tmp_path / "legacy-no-marker.db"
    old_service = AdvisorService(db)
    _seed_legacy_schedule_without_marker(old_service)
    old_service.close()

    upgraded = AdvisorService(db)
    try:
        assert upgraded.repo.list_fixed_events() == []
        assert upgraded.repo.list_routines() == []
        assert upgraded.repo.get_setting("schedule.sample_imported") == "legacy-cleaned"
    finally:
        upgraded.close()


def test_a_real_user_schedule_is_never_touched_by_legacy_cleanup(tmp_path):
    """پاک‌سازی نباید هیچ برنامهٔ واقعی کاربر را دست بزند."""
    db = tmp_path / "real.db"
    service = AdvisorService(db)
    try:
        service.create_fixed_event(FixedEvent(
            title="کلاس شیمی", kind=FixedEventKind.LIVE_CLASS,
            weekday=1, start_minute=900, end_minute=1140,
        ))
        service.create_routine(Routine(
            title="خواب شب", kind=RoutineKind.SLEEP,
            start_minute=1380, end_minute=360, weekdays=frozenset(range(7)),
            scope=RoutineScope.DAILY,
        ))
    finally:
        service.close()

    reopened = AdvisorService(db)
    try:
        assert [e.title for e in reopened.repo.list_fixed_events()] == ["کلاس شیمی"]
        assert [r.title for r in reopened.repo.list_routines()] == ["خواب شب"]
        assert reopened.repo.get_setting("schedule.sample_imported") is None
    finally:
        reopened.close()


def test_exam_cycle_step_lets_the_user_define_the_times(tmp_path):
    """مرحلهٔ چرخهٔ آزمون جامع دیگر گزینهٔ از پیش چاپ‌شده نیست.

    کاربر گفت: «در راه اندازی اولیه، بخش چرخه آزمون جامع، طوری باشد که
    خودمان تایم ها رو براش تعریف کنیم. مثلا هر دو هفته یک بار در ساعت
    ..:..»
    """
    from k2.onboarding import ONBOARDING_STEPS

    step = next(s for s in ONBOARDING_STEPS if s.key == "comprehensive_exam_cycle")
    assert step.kind == "exam_cycle", "مرحله باید ورودی ساختگیِ کاربر بگیرد، نه choice"
    assert not step.options, "هیچ گزینهٔ از پیش تعیین‌شده‌ای نمانده باشد"


def test_exam_cycle_editor_roundtrips_user_values(qapp):
    from k2.ui.views.onboarding import ExamCycleEditor

    editor = ExamCycleEditor()
    editor.weekday_combo.setCurrentIndex(editor.weekday_combo.findData(4))
    editor.time_range.set_start_minutes(8 * 60)
    editor.time_range.set_end_minutes(12 * 60)
    editor.every_spin.setValue(2)
    editor.name_edit.setText("آزمون جامع تجربی")

    restored = ExamCycleEditor()
    restored.set_json(editor.to_json())
    assert restored.weekday_combo.currentData() == 4
    assert restored.time_range.start_minutes() == 8 * 60
    assert restored.time_range.end_minutes() == 12 * 60
    assert restored.every_spin.value() == 2
    assert restored.name_edit.text() == "آزمون جامع تجربی"


def test_exam_cycle_editor_rejects_an_inverted_range(qapp):
    from k2.ui.views.onboarding import ExamCycleEditor

    editor = ExamCycleEditor()
    editor.time_range.set_start_minutes(19 * 60)
    editor.time_range.set_end_minutes(15 * 60)
    assert not editor.is_valid()

    editor.time_range.set_start_minutes(8 * 60)
    editor.time_range.set_end_minutes(12 * 60)
    assert editor.is_valid()

    # «هنوز مشخص نیست» باید بدون خطا از مرحله رد شود.
    editor.enabled_combo.setCurrentIndex(1)
    assert editor.is_valid()


def test_exam_cycle_becomes_a_real_recurring_event(tmp_path):
    """چرخهٔ تعریف‌شده باید رویداد واقعی با تناوبِ خودش شود."""
    import json

    service = AdvisorService(tmp_path / "cycle.db")
    try:
        service.create_fixed_event(FixedEvent(
            title="آزمون جامع", kind=FixedEventKind.EXAM, weekday=4,
            start_minute=480, end_minute=720,
            every_weeks=2,
        ))
        events = service.repo.list_fixed_events()
        assert len(events) == 1
        assert events[0].every_weeks == 2
        assert events[0].kind == FixedEventKind.EXAM
    finally:
        service.close()
