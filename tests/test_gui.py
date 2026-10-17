"""تست رابط کاربری: RTL، ورودی فارسی، اندازهٔ پنجره و مدیریت خطا."""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

import pytest

pytestmark = pytest.mark.gui

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QLineEdit

from k2.service import AdvisorService
from k2.ui.app import APP_TITLE, MainWindow
from k2.ui.theme import COLORS, load_fonts
from k2.ui.views.activities import AddActivityDialog
from k2.ui.views.onboarding import OnboardingWizard

SATURDAY = _dt.date(2026, 10, 10)


@pytest.fixture()
def window(qapp, tmp_path: Path) -> MainWindow:
    service = AdvisorService(tmp_path / "gui.db")
    win = MainWindow(service)
    yield win
    win.close()
    service.close()


def test_application_layout_is_rtl(qapp):
    assert qapp.layoutDirection() == Qt.RightToLeft


def test_persian_font_is_loaded(qapp):
    family = load_fonts()
    assert family
    # فونت باید واقعاً در پایگاه فونت Qt ثبت شده باشد
    from PySide6.QtGui import QFontDatabase

    assert family in QFontDatabase.families()


def test_main_window_has_all_navigation_pages(window: MainWindow):
    assert window.nav.count() == 7
    assert window.stack.count() == 7
    assert window.windowTitle() == APP_TITLE


def test_window_has_reasonable_default_size(window: MainWindow):
    width = window.width()
    height = window.height()
    assert width >= 900
    assert height >= 600


def test_navigation_and_dashboard_have_clear_visual_hierarchy(window: MainWindow):
    assert window.nav.objectName() == "navigation"
    assert window.nav.item(0).toolTip()
    assert window.nav.item(0).data(Qt.AccessibleTextRole) == "داشبورد؛ نمای کلی روز و ظرفیت"
    assert window.page_title.text() == "داشبورد"
    assert window.dashboard.hero.objectName() == "heroCard"
    assert window.dashboard.next_title.text()
    assert window.dashboard.btn_plan.objectName() == "primary"
    assert window.dashboard.btn_minimal.toolTip()
    assert window.menuBar().objectName() == "appMenuBar"
    assert window.menu_program.title() == "برنامه"
    assert window.menu_help.title() == "راهنما"
    assert all(action.isVisible() for action in window.menu_program.actions())
    assert window.action_refresh.shortcut().toString() == "F5"
    assert window.action_about.text() == "دربارهٔ K2"


def test_navigation_switches_pages(window: MainWindow):
    for index in range(window.stack.count()):
        window.nav.setCurrentRow(index)
        assert window.stack.currentIndex() == index


def test_persian_text_input_in_line_edit(qapp):
    edit = QLineEdit()
    edit.setText("پردازش اولیهٔ کلاس زیست")
    assert edit.text() == "پردازش اولیهٔ کلاس زیست"
    assert edit.text()[0] == "پ"


def test_persian_text_in_dashboard(window: MainWindow):
    window.refresh_all()
    text = window.dashboard.next_title.text()
    assert isinstance(text, str)


def test_pages_render_with_real_data(window: MainWindow):
    window.service.import_sample_schedule()
    window.service.create_exam_profile(
        __import__("k2.domain.models", fromlist=["ExamProfile"]).ExamProfile(
            name="آزمون", target_date=_dt.date(2027, 7, 1)
        )
    )
    window.refresh_all()
    for index in range(window.stack.count()):
        window.nav.setCurrentRow(index)
        page = window.stack.currentWidget()
        if hasattr(page, "refresh"):
            page.refresh()


def test_add_activity_dialog_rejects_invalid_date(qapp, tmp_path: Path, monkeypatch):
    """تاریخ نامعتبر باید پیش از ثبت رد شود (بدون بازکردن پنجرهٔ modal)."""
    service = AdvisorService(tmp_path / "d.db")
    shown: list[str] = []

    import k2.ui.views.activities as activities_module

    def fake_warning(parent, title, text, *args, **kwargs):
        shown.append(text)
        return None

    monkeypatch.setattr(
        activities_module.QMessageBox, "warning", staticmethod(fake_warning)
    )
    try:
        dialog = AddActivityDialog(service)
        dialog.title_edit.setText("کار")
        dialog.deadline_date.setText("نامعتبر")
        dialog._accept()
        assert shown, "باید هشدار تاریخ نامعتبر نشان داده می‌شد"
        assert not service.list_activities(), "فعالیت نباید ثبت می‌شد"
    finally:
        service.close()


def test_add_activity_dialog_creates_activity(qapp, tmp_path: Path):
    service = AdvisorService(tmp_path / "d2.db")
    try:
        dialog = AddActivityDialog(service)
        dialog.title_edit.setText("تحلیل آزمون")
        dialog.est_spin.setValue(30)
        dialog._accept()
        assert service.list_activities()
        assert service.list_activities()[0].title == "تحلیل آزمون"
    finally:
        service.close()


def test_onboarding_wizard_saves_state(qapp, tmp_path: Path):
    service = AdvisorService(tmp_path / "o.db")
    try:
        wizard = OnboardingWizard(service)
        wizard.state.set_value("student_name", "رضا")
        wizard.state.set_value("exam_name", "کنکور سراسری")
        wizard.state.set_value("exam_date", "۱۴۰۶/۰۴/۲۰")
        wizard.state.set_value("exam_date_status", "تخمینی")
        wizard.state.set_value("sunday_recorded", "شیمی")
        wizard.state.complete_step("sunday_recorded")
        wizard._save_state()

        reloaded = service.onboarding_state()
        assert reloaded.values["student_name"] == "رضا"
        assert "sunday_recorded" in reloaded.completed_steps
    finally:
        service.close()


def test_onboarding_blocking_question_is_reported(qapp, tmp_path: Path):
    service = AdvisorService(tmp_path / "o2.db")
    try:
        state = service.onboarding_state()
        assert any(
            "شیمی" in question
            for question in state.unresolved_blocking_questions()
        )
    finally:
        service.close()


def test_stylesheet_defines_rtl_and_theme_colors():
    from k2.ui.theme import stylesheet

    css = stylesheet()
    assert COLORS["accent"] in css
    assert "QPushButton" in css
    assert "QMenu {" in css
    assert "QMenu::item:selected" in css
    assert "QMenuBar#appMenuBar::item:selected" in css


def test_first_run_onboarding_is_scheduled_only_until_final_confirmation(qapp, tmp_path: Path):
    service = AdvisorService(tmp_path / "first-run.db")
    try:
        window = MainWindow(service)
        called = []
        window.run_onboarding = lambda: called.append("shown")  # type: ignore[method-assign]
        assert window._onboarding_auto_pending is True
        window.start_first_run_onboarding()
        from PySide6.QtTest import QTest

        QTest.qWait(20)
        assert called == ["shown"]

        state = service.onboarding_state()
        state.complete_step("confirm")
        service.save_onboarding_state(state)
        next_window = MainWindow(service)
        assert next_window._onboarding_auto_pending is False
        next_window.start_first_run_onboarding()
        QTest.qWait(20)
        assert called == ["shown"]
        window.close()
        next_window.close()
    finally:
        service.close()


def test_onboarding_subjects_and_user_books_are_persisted_without_official_weights(qapp, tmp_path: Path):
    from k2.ui.views.onboarding import OnboardingWizard

    service = AdvisorService(tmp_path / "profile-data.db")
    try:
        wizard = OnboardingWizard(service)
        wizard.state.values.update({
            "exam_name": "کنکور آزمایشی",
            "exam_group": "علوم تجربی",
            "exam_year": "۱۴۰۶",
            "exam_date_status": "نامشخص",
            "subject_selection_by_group": '{"علوم تجربی":["زیست‌شناسی"]}',
            "books": '[{"subject":"زیست‌شناسی","title":"کتاب زیست ۱",'
                     '"code":"110216","grade":"دهم","year":"1404",'
                     '"source":"https://chap.sch.ir/","selected":true}]',
        })
        wizard._apply_to_profile()
        profile = service.active_exam_profile()
        assert profile is not None
        assert profile.exam_year == 1406
        subjects = service.repo.list_subjects(profile.id, include_unselected=True)
        assert len(subjects) == 1 and subjects[0].name == "زیست‌شناسی"
        assert subjects[0].is_selected is True
        assert subjects[0].exam_coefficient is None
        assert subjects[0].academic_coefficient is None
        books = service.repo.list_textbooks(profile.id)
        assert len(books) == 1
        assert books[0].title == "کتاب زیست ۱"
        assert books[0].source_status == "user_entered_unverified"
        assert books[0].is_selected is True
    finally:
        service.close()


def test_calendar_dialog_values_roundtrip_and_validate(qapp, tmp_path: Path):
    from k2.domain.enums import FixedEventKind, RoutineKind
    from k2.ui.views.settings import RoutineDialog, ScheduleEventDialog

    service = AdvisorService(tmp_path / "dialogs.db")
    try:
        event_dialog = ScheduleEventDialog(service)
        event_dialog.title_edit.setText("کلاس زیست")
        event_dialog.kind_combo.setCurrentIndex(
            event_dialog.kind_combo.findData(FixedEventKind.LIVE_CLASS.value)
        )
        event_dialog.weekday_combo.setCurrentIndex(2)
        from PySide6.QtCore import QTime

        event_dialog.start_edit.setTime(QTime(15, 0))
        event_dialog.end_edit.setTime(QTime(17, 0))
        event = event_dialog.value()
        event_id = service.create_fixed_event(event)
        assert service.repo.list_fixed_events()[0].id == event_id
        assert service.repo.list_fixed_events()[0].start_minute == 900

        routine_dialog = RoutineDialog()
        routine_dialog.title_edit.setText("خواب")
        routine_dialog.kind_combo.setCurrentIndex(
            routine_dialog.kind_combo.findData(RoutineKind.SLEEP.value)
        )
        routine_dialog.start_edit.setTime(QTime(23, 0))
        routine_dialog.end_edit.setTime(QTime(6, 0))
        routine = routine_dialog.value()
        routine_id = service.create_routine(routine)
        assert service.repo.list_routines()[0].id == routine_id
        assert service.repo.list_routines()[0].start_minute > service.repo.list_routines()[0].end_minute
    finally:
        service.close()


def test_subject_picker_retains_each_track_and_book_checks(qapp, tmp_path: Path):
    import json
    from k2.ui.views.onboarding import OnboardingWizard

    service = AdvisorService(tmp_path / "picker.db")
    try:
        wizard = OnboardingWizard(service)
        group_combo = wizard.findChild(QComboBox, "field_exam_group")
        assert group_combo is not None
        group_combo.setCurrentText("علوم تجربی")
        wizard._set_current_subjects(True)
        group_combo.setCurrentText("علوم انسانی")
        wizard._set_current_subjects(False)
        group_combo.setCurrentText("علوم تجربی")
        assert all(
            wizard.subject_list.item(i).checkState() == Qt.Checked
            for i in range(wizard.subject_list.count())
        )
        selections = json.loads(wizard.state.values["subject_selection_by_group"])
        assert set(selections["علوم تجربی"]) == {"زیست‌شناسی", "شیمی", "فیزیک", "ریاضی", "زمین‌شناسی"}
        assert "علوم انسانی" in selections

        wizard.book_title_edit.setText("کتاب آزمایشی")
        wizard.book_code_edit.setText("X-1")
        wizard._add_book()
        item = wizard.book_list.item(0)
        item.setCheckState(Qt.Unchecked)
        books = json.loads(wizard.state.values["books"])
        assert books[0]["title"] == "کتاب آزمایشی"
        assert books[0]["selected"] is False
        assert "تأییدنشده" in item.text()
    finally:
        service.close()
