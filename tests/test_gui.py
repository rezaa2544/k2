"""تست رابط کاربری: RTL، ورودی فارسی، اندازهٔ پنجره و مدیریت خطا."""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

import pytest

pytestmark = pytest.mark.gui

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QLabel, QLineEdit, QWidget

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
    """صفحه‌های ناوبری کامل‌اند و صفحهٔ سرفصل هم اضافه شده است (بند ۱۷)."""
    from k2.ui.app import NAV_ITEMS

    assert len(NAV_ITEMS) == 14
    assert window.nav.count() == 14
    assert window.stack.count() == 15  # ۱۴ صفحهٔ ناوبری + «برنامهٔ امروز» فرعی
    assert window.windowTitle() == APP_TITLE
    titles = [title for _, title, _ in NAV_ITEMS]
    for expected in (
        "داشبورد امروز", "برنامه هفتگی", "بانک دروس", "سرفصل درس‌ها",
        "عقب‌افتادگی‌ها", "کلاس‌های من", "مشکلات یادگیری", "تست و تحلیل",
        "مرورهای من", "آزمون‌های جامع", "مهلت‌های من", "ساعت مطالعه",
        "گزارش مشاور", "تنظیمات",
    ):
        assert expected in titles
    # هیچ عنوان تکراری نباشد؛ وگرنه ناوبری دو معنا می‌شود
    assert len(set(titles)) == len(titles)


def test_window_has_reasonable_default_size(window: MainWindow):
    width = window.width()
    height = window.height()
    assert width >= 900
    assert height >= 600


def test_navigation_and_dashboard_have_clear_visual_hierarchy(window: MainWindow):
    assert window.nav.objectName() == "navigation"
    assert window.nav.item(0).toolTip()
    assert window.nav.item(0).data(Qt.AccessibleTextRole) == (
        "داشبورد امروز؛ نمای کلی روز، ظرفیت و قدم بعدی"
    )
    assert window.page_title.text() == "داشبورد امروز"
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
    for index in range(window.nav.count()):
        window.nav.setCurrentRow(index)
        assert window.stack.currentIndex() == index
        assert window.page_title.text()


def test_subpage_today_is_reachable_from_dashboard(window: MainWindow):
    window.open_page("today")
    assert window.page_title.text() == "برنامهٔ امروز"
    assert window.stack.currentIndex() == window._extra_pages["today"]


def test_persian_text_input_in_line_edit(qapp):
    edit = QLineEdit()
    edit.setText("پردازش اولیهٔ کلاس زیست")
    assert edit.text() == "پردازش اولیهٔ کلاس زیست"
    assert edit.text()[0] == "پ"


def test_persian_text_in_dashboard(window: MainWindow):
    window.refresh_all()
    assert window.dashboard.next_title.text() == "هنوز اطلاعاتی ثبت نشده است"
    assert window.dashboard.tile_capacity.value_label.text() == "—"
    assert not window.dashboard.btn_plan.isEnabled()
    assert window.today.summary.text().startswith("هنوز فعالیت")
    assert not window.today.btn_refresh.isEnabled()
    assert window.reports.daily_text.text() == "هنوز فعالیت یا آزمونی ثبت نشده است."


def test_new_install_settings_have_no_prefilled_personal_values(window: MainWindow):
    assert window.settings.wake_edit.text() == ""
    assert window.settings.sleep_edit.text() == ""
    assert window.settings.exam_name_edit.text() == ""
    assert window.settings.exam_date_edit.text() == ""
    assert window.settings.exam_status_combo.currentData() is None
    assert window.settings.mastery_sessions_spin.value() == 2
    assert window.settings.mastery_spacing_spin.value() == 3
    assert window.settings.mastery_score_spin.value() == 0.8
    assert window.review
    assert window.service.repo.list_fixed_events() == []
    assert window.service.repo.list_routines() == []


def test_settings_page_exposes_and_saves_consolidation_thresholds(
    qapp, tmp_path: Path, monkeypatch
):
    """آستانه‌های نردبان تثبیت و سه مسیر باید در تنظیمات قابل تغییر و ذخیره باشند."""
    import k2.ui.views.settings as settings_module

    monkeypatch.setattr(settings_module, "notify", lambda *a, **k: None)
    # ذخیرهٔ تنظیمات در فایل مشترک /tmp/k2-tests، تست‌های دیگر را آلوده می‌کند؛
    # پس پوشهٔ داده برای این تست موقت می‌شود.
    monkeypatch.setenv("K2_DATA_DIR", str(tmp_path / "data"))
    service = AdvisorService(tmp_path / "settings.db")
    window = MainWindow(service)
    page = window.settings
    page.target_retention_spin.setValue(0.85)
    page.spacing_ratio_spin.setValue(0.20)
    page.first_retrieval_spin.setValue(12)
    page.stage_score_spin.setValue(0.75)
    page.stage_spacing_spin.setValue(2.0)
    page.consolidation_floor_spin.setValue(0.25)
    page.catchup_cap_spin.setValue(0.35)
    page._save_consolidation()
    settings = service.settings
    assert settings.consolidation.target_retention == 0.85
    assert settings.consolidation.spacing_ratio == 0.20
    assert settings.consolidation.first_retrieval_hours == 12
    assert settings.consolidation.stage_evidence_score == 0.75
    assert settings.consolidation.stage_min_spacing_days == 2.0
    assert settings.streams.consolidation_floor_ratio == 0.25
    assert settings.streams.catchup_cap_ratio == 0.35
    # بازخوانی از تنظیمات ذخیره‌شده باید همان مقادیر را نشان دهد
    page.refresh()
    assert page.target_retention_spin.value() == 0.85
    assert page.consolidation_floor_spin.value() == 0.25
    window.close()
    service.close()


def test_consolidation_page_renders_three_streams_and_ladder(qapp, tmp_path: Path):
    """صفحهٔ تثبیت باید مسیرها، امکان‌سنجی و نردبان را از دادهٔ واقعی بسازد."""
    from k2.domain.models import ExamProfile, LearningEvidence, Subject, Topic

    service = AdvisorService(tmp_path / "cons.db")
    service.create_exam_profile(
        ExamProfile(
            name="کنکور",
            group_name="علوم تجربی",
            target_date=_dt.date(2027, 7, 1),
        )
    )
    subject_id = service.create_subject(
        Subject(name="زیست‌شناسی", exam_profile_id=1, coefficient=12.0)
    )
    topic_id = service.create_topic(Topic(subject_id=subject_id, name="ژنتیک"))
    for offset, source, score in ((0, "study", 1.0), (1, "review", 0.9)):
        service.record_learning_evidence(
            LearningEvidence(
                topic_id=topic_id,
                observed_on=_dt.date(2026, 10, 10) + _dt.timedelta(days=offset),
                source=source,
                score=score,
            )
        )
    window = MainWindow(service)
    window.refresh_all()
    page = window.review.consolidation
    page.refresh()
    assert page.table.rowCount() >= 1
    assert page.streams_summary.text().startswith("ظرفیت")
    assert page.feasibility_label.text()
    assert page.stream_bars["consolidation"].maximum() > 0
    advice_item = page.table.item(0, 6)
    assert advice_item is not None and advice_item.text()
    window.close()
    service.close()


def test_pages_render_with_real_data(window: MainWindow):
    from k2.domain.models import FixedEvent
    window.service.create_fixed_event(FixedEvent(
        title="کلاس واقعی", weekday=0, start_minute=600, end_minute=660
    ))
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
        wizard._save_state()

        reloaded = service.onboarding_state()
        assert reloaded.values["student_name"] == "رضا"
    finally:
        service.close()


def test_onboarding_has_no_synthetic_blocking_question(qapp, tmp_path: Path):
    service = AdvisorService(tmp_path / "o2.db")
    try:
        state = service.onboarding_state()
        assert state.unresolved_blocking_questions() == []
        wizard = OnboardingWizard(service)
        assert not wizard.conflict_box.isVisible()
        steps = __import__("k2.onboarding", fromlist=["ONBOARDING_STEPS"]).ONBOARDING_STEPS
        weekly_step = next(i for i, step in enumerate(steps) if step.key == "weekly_schedule")
        group_step = next(i for i, step in enumerate(steps) if step.key == "exam_group")
        assert wizard.stack.widget(weekly_step).findChild(
            QWidget, "field_weekly_schedule"
        ) is not None
        assert wizard._event_editors["weekly_schedule"]["rows"].count() == 0
        group_combo = wizard.stack.widget(group_step).findChild(QComboBox, "field_exam_group")
        assert group_combo.currentData() == ""
        wizard._collect()
        assert wizard.state.values.get("exam_group", "") == ""
        wizard._goto(weekly_step)
        wizard._next()
        assert wizard.state.current_index == weekly_step + 1
        assert service.repo.list_fixed_events() == []
        assert service.repo.list_routines() == []
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
        assert subjects[0].exam_coefficient == 12
        assert subjects[0].exam_coefficient_status == "official_notice_republished"
        assert subjects[0].academic_coefficient is None
        books = service.repo.list_textbooks(profile.id)
        assert len(books) == 1
        assert books[0].title == "کتاب زیست ۱"
        assert books[0].source_status == "user_entered_unverified"
        assert books[0].is_selected is True
    finally:
        service.close()


def test_onboarding_persists_classes_commitments_sleep_and_custom_routines(qapp, tmp_path: Path):
    from PySide6.QtCore import QTime
    from k2.domain.enums import FixedEventKind, RoutineKind

    service = AdvisorService(tmp_path / "onboarding-calendar.db")
    try:
        wizard = OnboardingWizard(service)
        wizard.state.values.update({
            "exam_name": "کنکور هدف", "exam_group": "علوم تجربی",
            "exam_year": "۱۴۰۶", "exam_date_status": "نامشخص",
            "class_attendance": "بله", "sleep_time": "۲۳:۰۰ تا ۰۶:۳۰",
            "subject_selection_by_group": '{"علوم تجربی":["زیست‌شناسی"]}',
        })
        class_editor = wizard._event_editors["classes"]
        class_editor["title"].setText("کلاس زیست مؤسسه")
        class_editor["subject"].setCurrentText("زیست‌شناسی")
        class_editor["weekday"].setCurrentIndex(1)
        class_editor["start"].setTime(QTime(15, 0))
        class_editor["end"].setTime(QTime(17, 0))
        wizard._add_event_row("classes")

        event_editor = wizard._event_editors["weekly_schedule"]
        event_editor["title"].setText("آزمون آزمایشی")
        event_editor["kind"].setCurrentIndex(event_editor["kind"].findData(FixedEventKind.EXAM.value))
        event_editor["weekday"].setCurrentIndex(5)
        event_editor["start"].setTime(QTime(8, 0))
        event_editor["end"].setTime(QTime(12, 0))
        wizard._add_event_row("weekly_schedule")

        routine_editor = wizard._routine_editors["routines"]
        routine_editor["title"].setText("استراحت بعدازظهر")
        routine_editor["kind"].setCurrentIndex(routine_editor["kind"].findData(RoutineKind.REST.value))
        routine_editor["start"].setTime(QTime(16, 0))
        routine_editor["end"].setTime(QTime(16, 30))
        wizard._add_routine_row("routines")
        wizard._apply_to_profile()

        events = service.repo.list_fixed_events()
        assert {(e.title, e.kind.value, e.weekday) for e in events} == {
            ("کلاس زیست مؤسسه", "live_class", 1), ("آزمون آزمایشی", "exam", 5)
        }
        routines = service.repo.list_routines()
        sleep = next(r for r in routines if r.title == "خواب شب")
        assert sleep.start_minute == 23 * 60 and sleep.end_minute == 6 * 60 + 30
        assert (service.wake_minute, service.sleep_minute) == (390, 1380)
        assert any(r.title == "استراحت بعدازظهر" and r.kind == RoutineKind.REST for r in routines)
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
        from k2.konkur_catalog import SUBJECTS_BY_GROUP
        assert set(selections["علوم تجربی"]) == set(SUBJECTS_BY_GROUP["علوم تجربی"])
        assert "علوم انسانی" in selections

        wizard.book_title_edit.setText("کتاب آزمایشی")
        wizard.book_code_edit.setText("X-1")
        wizard._add_book()
        item = next(
            wizard.book_list.item(i) for i in range(wizard.book_list.count())
            if "— کتاب آزمایشی" in wizard.book_list.item(i).text()
        )
        item.setCheckState(Qt.Unchecked)
        books = json.loads(wizard.state.values["books"])
        manual = next(row for row in books if row["title"] == "کتاب آزمایشی")
        assert manual["selected"] is False
        assert "واردشده/تأییدنشده" in item.text()
    finally:
        service.close()


def test_every_onboarding_step_is_reachable_inside_a_scroll_area(
    qapp, tmp_path: Path
):
    """هیچ گامی از راه‌اندازی نباید بریده یا دست‌نیافتنی باشد.

    پیش از این اصلاح، پنجرهٔ جادوگر اندازهٔ ثابت ۷۶۰×۶۲۰ داشت و گام‌های
    بلند (کتاب‌ها، کلاس‌ها، روال‌ها) از کادر بیرون می‌زدند؛ دکمه‌های پایین
    آن گام‌ها — از جمله «افزودن کتاب به فهرست» — بریده و غیرقابل‌کلیک
    می‌شدند. حالا هر گام داخل ``QScrollArea`` است و پنجره حداقل اندازه دارد.
    """
    from PySide6.QtWidgets import QScrollArea, QSizePolicy

    from k2.onboarding import ONBOARDING_STEPS

    service = AdvisorService(tmp_path / "scroll.db")
    try:
        wizard = OnboardingWizard(service)
        assert wizard.stack.count() == len(ONBOARDING_STEPS)
        # پنجره باید قابل بزرگ‌شدن باشد، نه اندازهٔ ثابت.
        assert wizard.minimumSize().width() > 0
        assert wizard.minimumSize().height() > 0
        for index, step in enumerate(ONBOARDING_STEPS):
            page = wizard.stack.widget(index)
            assert isinstance(page, QScrollArea), (
                f"گام «{step.title}» داخل ناحیهٔ اسکرول نیست"
            )
            assert page.widgetResizable()
            # نوار اسکرول فقط وقتی لازم باشد دیده شود؛ محتوا همیشه قابل رسیدن.
            assert page.verticalScrollBarPolicy() == Qt.ScrollBarAsNeeded
            card = page.widget()
            assert card is not None
            assert card.sizePolicy().verticalPolicy() == QSizePolicy.Maximum
            # ورودی‌های هر گام باید هنوز با findChild پیدا شوند تا جمع‌آوری
            # مقدارها از کار نیفتد.
            field = page.findChild(QWidget, f"field_{step.key}")
            assert field is not None, f"ورودی گام «{step.title}» پیدا نشد"
        wizard.close()
    finally:
        service.close()


def test_tall_onboarding_step_scrolls_instead_of_clipping(qapp, tmp_path: Path):
    """گام کتاب‌ها در پنجرهٔ کوچک اسکرول می‌شود، نه اینکه بریده شود.

    پیش از این اصلاح، گام کتاب‌ها از کادر پنجره بیرون می‌زد و دکمهٔ
    «افزودن کتاب به فهرست» در پایین کارت اصلاً قابل کلیک نبود.
    """
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QPushButton, QScrollArea

    from k2.onboarding import ONBOARDING_STEPS

    service = AdvisorService(tmp_path / "tall.db")
    try:
        wizard = OnboardingWizard(service)
        books_step = next(
            i for i, step in enumerate(ONBOARDING_STEPS) if step.kind == "books"
        )
        page = wizard.stack.widget(books_step)
        assert isinstance(page, QScrollArea)
        # پنجره را عمداً خیلی کوتاه می‌کنیم (کران حداقل اندازه را برای آزمون
        # برمی‌داریم) تا گام بلند جا نشود و نوار اسکرول حتماً فعال شود.
        wizard.setMinimumSize(0, 0)
        wizard.resize(760, 240)
        wizard.show()
        qapp.processEvents()
        bar = page.verticalScrollBar()
        assert bar.maximum() > 0, "گام کتاب‌ها باید در پنجرهٔ کوتاه اسکرول شود"
        card = page.widget()
        assert card is not None
        add_buttons = [
            b for b in card.findChildren(QPushButton)
            if b.text() == "افزودن کتاب به فهرست"
        ]
        assert len(add_buttons) == 1
        button = add_buttons[0]
        # محتوای کارت از ناحیهٔ دیدنی بلندتر است و دکمهٔ پایین کارت داخل
        # همان محتوای اسکرول‌شدنی قرار دارد؛ یعنی با اسکرول کامل قابل رسیدن
        # است، نه بریده.
        assert card.height() > page.viewport().height()
        pos_in_card = button.mapTo(card, QPoint(0, 0))
        assert 0 <= pos_in_card.y() < card.height(), (
            "دکمهٔ افزودن کتاب باید داخل محتوای اسکرول‌شدنی کارت باشد"
        )
        assert button.height() > 0
        wizard.close()
    finally:
        service.close()


# ---------------------------------------------------------------------------
# پیمایش صفحه‌های اصلی و اندازهٔ دیالوگ‌ها
# ---------------------------------------------------------------------------

def test_every_main_page_is_scrollable_instead_of_clipped(
    qapp, window: MainWindow
):
    """هیچ صفحهٔ اصلی نباید محتوایش از دید بیرون بزند.

    پیش از این اصلاح، صفحهٔ «مرورهای من» (ReviewPage) محتوایی بلندتر از
    فضای دیدنی می‌ساخت و چون هیچ ناحیهٔ پیمایشی نداشت، برچسب‌های پایینی
    کاملاً فرو می‌ریختند (ارتفاع صفر) و متن چندخطی بریده می‌شد؛ کاربر
    راهی برای دیدن آن‌ها نداشت.
    """
    from PySide6.QtWidgets import QScrollArea

    stack = window.stack
    assert isinstance(window.page_scroll, QScrollArea)
    assert window.page_scroll.widget() is stack
    assert window.page_scroll.widgetResizable() is True
    window.show()
    qapp.processEvents()
    for index in range(stack.count()):
        stack.setCurrentIndex(index)
        qapp.processEvents()
        page = stack.widget(index)
        # محتوای صفحه هرگز از ناحیهٔ دیدنی کوچک‌تر نیست: یا جا می‌شود، یا
        # ناحیهٔ پیمایش بیرونی به‌اندازهٔ محتوا بالا می‌کشد.
        assert page.height() >= window.page_scroll.viewport().height() - 1, (
            f"صفحهٔ {page.__class__.__name__} از ناحیهٔ دیدنی کوچک‌تر شد"
        )
        # و هیچ برچسبی به ارتفاع صفر نمی‌ریزد (یعنی محتوای نامرئی نمی‌شود).
        for label in page.findChildren(QLabel):
            if not label.isVisible() or not label.text().strip():
                continue
            assert label.height() > 0 or label.parent() is None, (
                f"برچسب «{label.text()[:24]}» در "
                f"{page.__class__.__name__} ارتفاع صفر گرفت"
            )


def test_page_scroll_range_follows_current_page(qapp, window: MainWindow):
    """نوار پیمایش بیرونی باید فقط به صفحهٔ جاری گوش بدهد.

    ``QStackedWidget`` به‌صورت پیش‌فرض بزرگ‌ترین حداقلِ همهٔ صفحه‌ها را
    گزارش می‌کند؛ بدون اصلاح، پس از دیدن صفحهٔ بلند، صفحه‌های کوچک هم
    نوار پیمایش بی‌مورد می‌گرفتند و کاربر به فضای خالی می‌لغزید.
    """
    stack = window.stack
    window.show()
    qapp.processEvents()
    # داشبورد کوتاه است: نباید هیچ اسکرول بی‌موردی داشته باشد.
    stack.setCurrentIndex(0)
    qapp.processEvents()
    small_range = window.page_scroll.verticalScrollBar().maximum()
    # صفحهٔ «مرورهای من» بلند است: باید اسکرول بگیرد.
    review_index = next(
        i for i in range(stack.count())
        if stack.widget(i).__class__.__name__ == "ReviewPage"
    )
    stack.setCurrentIndex(review_index)
    qapp.processEvents()
    tall_range = window.page_scroll.verticalScrollBar().maximum()
    assert tall_range > 0, "صفحهٔ بلند باید اسکرول‌شدنی باشد"
    # بازگشت به صفحهٔ کوتاه، نوار را باید آزاد کند.
    stack.setCurrentIndex(0)
    qapp.processEvents()
    assert window.page_scroll.verticalScrollBar().maximum() <= small_range


def test_form_dialogs_are_wide_enough_for_persian_labels(
    qapp, tmp_path: Path
):
    """هیچ دیالوگ فرمی نباید باریک شود.

    برچسب‌های فارسی مثل «موعد نخستین بازیابی (شمسی):» و فهرست‌های کشویی
    بلندند؛ با اندازهٔ پیش‌فرض چیدمان، سیزده دیالوگ بین ۲۳۱ و ۳۵۱ پیکسل عرض
    می‌گرفتند و محتوایشان بریده می‌شد. این تست همهٔ دیالوگ‌های فرم را پوشش
    می‌دهد تا دیالوگ تازه دوباره باریک نشود.
    """
    from k2.domain.models import StudySession, Subject, Topic

    from k2.ui.views.classes import FixedEventDialog, RoutineDialog
    from k2.ui.views.course_bank import AddTopicDialog, EvidenceDialog
    from k2.ui.views.deadlines import DeadlineDialog
    from k2.ui.views.exams import RecordAttemptDialog
    from k2.ui.views.problems import ProblemDialog, ResolveDialog
    from k2.ui.views.review import AddReviewDialog
    from k2.ui.views.settings import ScheduleEventDialog
    from k2.ui.views.study_timer_page import (
        CorrectSessionDialog,
        ManualSessionDialog,
    )
    from k2.ui.views.tests_page import QuestionDialog
    from k2.ui.views.topics import AddEvidenceDialog

    service = AdvisorService(tmp_path / "dlg.db")
    try:
        subject = Subject(name="ریاضی", coefficient=2.0)
        service.create_subject(subject)
        topic = Topic(subject_id=subject.id, name="احتمال", estimated_minutes=300)
        service.create_topic(topic)
        session = StudySession(kind="study", minutes=45, note="")

        dialogs = [
            AddActivityDialog(service),
            AddTopicDialog(service),
            RecordAttemptDialog(service),
            AddReviewDialog(service),
            FixedEventDialog(service),
            RoutineDialog(service),
            ManualSessionDialog(service),
            EvidenceDialog(service, topic.id),
            DeadlineDialog(service),
            ProblemDialog(service),
            ResolveDialog(),
            ScheduleEventDialog(service),
            CorrectSessionDialog(service, session),
            QuestionDialog(service, 1),
            AddEvidenceDialog(topic),
        ]
        assert len(dialogs) == 15
        for dialog in dialogs:
            dialog.show()
            qapp.processEvents()
            assert dialog.minimumWidth() >= 460, (
                f"{dialog.__class__.__name__} عرض حداقل "
                f"{dialog.minimumWidth()} پیکسل دارد"
            )
            # برچسب‌های فرم باید ارتفاع واقعی داشته باشند (فرو نریزند).
            for label in dialog.findChildren(QLabel):
                if not label.isVisible() or not label.text().strip():
                    continue
                assert label.height() > 0, (
                    f"برچسب «{label.text()[:24]}» در "
                    f"{dialog.__class__.__name__} ارتفاع صفر گرفت"
                )
            dialog.close()
    finally:
        service.close()
