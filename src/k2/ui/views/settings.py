"""نمای تنظیمات: پنجرهٔ روز، انرژی، پروفایل آزمون و پشتیبان‌گیری."""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QScrollArea,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from ...domain.enums import DateStatus, FixedEventKind, RoutineKind, RoutineScope
from ...domain.models import ExamProfile, FixedEvent, Routine
from ...konkur_catalog import EXAM_WEIGHT_BY_GROUP
from ...jdate import format_jalali_long
from ...service import AdvisorService
from ..widgets import Card, confirm, info_box, notify


def _parse_clock(text: str) -> int | None:
    from ...jdate import normalize_digits

    normalized = normalize_digits(text).strip()
    if ":" not in normalized:
        return None
    hour, _, minute = normalized.partition(":")
    try:
        value = int(hour) * 60 + int(minute or 0)
    except ValueError:
        return None
    if not (0 <= value <= 24 * 60):
        return None
    return value


class SettingsPage(QWidget):
    """تنظیمات کاربر و داده."""

    def __init__(self, service: AdvisorService, parent: QWidget | None = None):
        super().__init__(parent)
        self.service = service
        self._build()
        self.refresh()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        root = QVBoxLayout(content)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        daily_card = Card("پنجرهٔ روز و انرژی")
        form = QFormLayout()
        self.wake_edit = QLineEdit()
        self.wake_edit.setPlaceholderText("۰۶:۰۰")
        form.addRow("ساعت بیداری:", self.wake_edit)
        self.sleep_edit = QLineEdit()
        self.sleep_edit.setPlaceholderText("۲۳:۰۰")
        form.addRow("ساعت خواب:", self.sleep_edit)
        self.energy_combo = QComboBox()
        self.energy_combo.addItem("انتخاب کنید", None)
        for value, label in ((1, "کم"), (2, "متوسط"), (3, "خوب")):
            self.energy_combo.addItem(label, value)
        form.addRow("انرژی امروز:", self.energy_combo)
        self.peak_edit = QLineEdit()
        self.peak_edit.setPlaceholderText("۱۶:۰۰-۱۸:۰۰, ۲۰:۰۰-۲۲:۰۰")
        form.addRow("ساعت‌های پربازده:", self.peak_edit)
        btn_save = QPushButton("ذخیرهٔ تنظیمات")
        btn_save.setObjectName("primary")
        btn_save.clicked.connect(self._save_daily)
        form.addRow(btn_save)
        daily_card.add_layout(form)
        root.addWidget(daily_card)

        mastery_card = Card("معیارهای تطبیقیِ تسلط · فرضیهٔ قابل تنظیم")
        mastery_form = QFormLayout()
        self.mastery_sessions_spin = QSpinBox()
        self.mastery_sessions_spin.setRange(2, 6)
        mastery_form.addRow("حداقل جلسهٔ جدا:", self.mastery_sessions_spin)
        self.mastery_spacing_spin = QSpinBox()
        self.mastery_spacing_spin.setRange(1, 30)
        self.mastery_spacing_spin.setSuffix(" روز")
        mastery_form.addRow("کمینهٔ فاصلهٔ جلسه‌ها:", self.mastery_spacing_spin)
        self.mastery_score_spin = QDoubleSpinBox()
        self.mastery_score_spin.setRange(0.50, 1.00)
        self.mastery_score_spin.setSingleStep(0.05)
        self.mastery_score_spin.setDecimals(2)
        self.mastery_score_spin.setSuffix(" (۰ تا ۱)")
        mastery_form.addRow("حداقل نمرهٔ تأخیری و انتقالی:", self.mastery_score_spin)
        mastery_note = QLabel(
            "این آستانه‌ها قاعدهٔ عملیاتیِ محصول‌اند، نه استاندارد علمی واحد؛ "
            "L4 هم عملکرد مشاهده‌شده است، نه تضمین تثبیت حافظه یا نمرهٔ آزمون."
        )
        mastery_note.setWordWrap(True)
        mastery_note.setObjectName("muted")
        mastery_form.addRow(mastery_note)
        save_mastery = QPushButton("ذخیرهٔ معیارهای تسلط")
        save_mastery.clicked.connect(self._save_mastery)
        mastery_form.addRow(save_mastery)
        mastery_card.add_layout(mastery_form)
        root.addWidget(mastery_card)

        exam_card = Card("پروفایل آزمون هدف (قابل ویرایش)")
        exam_form = QFormLayout()
        self.exam_name_edit = QLineEdit()
        exam_form.addRow("نام آزمون:", self.exam_name_edit)
        self.exam_group_edit = QLineEdit()
        exam_form.addRow("گروه/رشته:", self.exam_group_edit)
        self.exam_year_spin = QSpinBox()
        self.exam_year_spin.setRange(0, 1499)
        self.exam_year_spin.setSpecialValueText("نامشخص")
        exam_form.addRow("سال آزمون:", self.exam_year_spin)
        self.exam_date_edit = QLineEdit()
        self.exam_date_edit.setPlaceholderText("سال/ماه/روز")
        exam_form.addRow("تاریخ هدف (شمسی):", self.exam_date_edit)
        self.exam_status_combo = QComboBox()
        self.exam_status_combo.addItem("انتخاب وضعیت", None)
        for status in DateStatus:
            self.exam_status_combo.addItem(status.label, status.value)
        exam_form.addRow("وضعیت تاریخ:", self.exam_status_combo)
        self.exam_source_edit = QLineEdit()
        self.exam_source_edit.setPlaceholderText("عنوان و محل اطلاعیهٔ رسمی")
        exam_form.addRow("منبع:", self.exam_source_edit)
        self.contribution_notice = QLabel("")
        self.contribution_notice.setWordWrap(True)
        self.contribution_notice.setObjectName("muted")
        exam_form.addRow("سهم آزمون / سوابق:", self.contribution_notice)
        self.negative_spin = QDoubleSpinBox()
        self.negative_spin.setRange(0.0, 1.0)
        self.negative_spin.setSingleStep(0.05)
        self.negative_spin.setDecimals(2)
        exam_form.addRow("ضریب نمرهٔ منفی:", self.negative_spin)
        self.formula_combo = QComboBox()
        self.formula_combo.addItem("درصد خام", "raw")
        self.formula_combo.addItem("درصد با نمرهٔ منفی", "negative")
        exam_form.addRow("فرمول درصد:", self.formula_combo)
        self.auto_exam_priority = QCheckBox(
            "در اولویت خودکار، ضریب رسمی آزمون را لحاظ کن"
        )
        exam_form.addRow("اولویت‌بندی:", self.auto_exam_priority)
        priority_note = QLabel(
            "فقط برای اولویت فعالیت‌ها: ضریب رسمی به‌صورت تعدیل‌گر ۰٫۵ تا ۱٫۵ به کار می‌رود. "
            "وزن شخصی درس/مبحث تغییر نمی‌کند؛ ضرایب آزمون و سوابق تحصیلی جدا هستند."
        )
        priority_note.setWordWrap(True)
        priority_note.setObjectName("muted")
        exam_form.addRow(priority_note)
        btn_exam = QPushButton("ذخیرهٔ پروفایل آزمون")
        btn_exam.setObjectName("primary")
        btn_exam.clicked.connect(self._save_exam)
        exam_form.addRow(btn_exam)
        exam_card.add_layout(exam_form)
        root.addWidget(exam_card)

        schedule_card = Card("برنامهٔ کلاس‌ها و تعهدات هفتگی")
        self.schedule_text = QLabel("رویدادها و تعهدات ثبت‌شده")
        self.schedule_text.setObjectName("sectionTitle")
        schedule_card.add(self.schedule_text)
        self.event_list = QListWidget()
        self.event_list.setAccessibleName("رویدادهای هفتگی")
        self.event_list.setMaximumHeight(170)
        schedule_card.add(self.event_list)
        event_buttons = QHBoxLayout()
        self.btn_add_event = QPushButton("افزودن رویداد")
        self.btn_add_event.clicked.connect(self._add_event)
        event_buttons.addWidget(self.btn_add_event)
        self.btn_edit_event = QPushButton("ویرایش انتخاب")
        self.btn_edit_event.clicked.connect(self._edit_event)
        event_buttons.addWidget(self.btn_edit_event)
        self.btn_delete_event = QPushButton("حذف انتخاب")
        self.btn_delete_event.clicked.connect(self._delete_event)
        event_buttons.addWidget(self.btn_delete_event)
        schedule_card.add_layout(event_buttons)
        self.conflict_text = QLabel("")
        self.conflict_text.setWordWrap(True)
        self.conflict_text.setObjectName("warningBox")
        schedule_card.add(self.conflict_text)

        routine_label = QLabel("خواب، غذا، استراحت و فعالیت‌های ثابت")
        routine_label.setObjectName("sectionTitle")
        schedule_card.add(routine_label)
        self.routine_list = QListWidget()
        self.routine_list.setAccessibleName("بازه‌های ضروری و روال‌ها")
        self.routine_list.setMaximumHeight(140)
        schedule_card.add(self.routine_list)
        routine_buttons = QHBoxLayout()
        self.btn_add_routine = QPushButton("افزودن روال")
        self.btn_add_routine.clicked.connect(self._add_routine)
        routine_buttons.addWidget(self.btn_add_routine)
        self.btn_edit_routine = QPushButton("ویرایش روال")
        self.btn_edit_routine.clicked.connect(self._edit_routine)
        routine_buttons.addWidget(self.btn_edit_routine)
        self.btn_delete_routine = QPushButton("حذف روال")
        self.btn_delete_routine.clicked.connect(self._delete_routine)
        routine_buttons.addWidget(self.btn_delete_routine)
        schedule_card.add_layout(routine_buttons)
        root.addWidget(schedule_card)

        backup_card = Card("پشتیبان‌گیری و بازیابی")
        backup_buttons = QHBoxLayout()
        btn_backup = QPushButton("ساخت نسخهٔ پشتیبان")
        btn_backup.clicked.connect(self._backup)
        backup_buttons.addWidget(btn_backup)
        btn_restore = QPushButton("بازیابی از فایل پشتیبان")
        btn_restore.clicked.connect(self._restore)
        backup_buttons.addWidget(btn_restore)
        backup_card.add_layout(backup_buttons)
        self.backup_text = QLabel("—")
        self.backup_text.setWordWrap(True)
        backup_card.add(self.backup_text)
        root.addWidget(backup_card)

        self.info = info_box()
        self.info.setText(
            "همهٔ داده‌ها روی همین رایانه و در SQLite نگهداری می‌شوند. ضرایب آزمون ۱۴۰۶ "
            "از متن کامل بازنشرشدهٔ اطلاعیهٔ سنجش ثبت شده‌اند؛ نسخهٔ اولیهٔ سنجش و "
            "پیوستِ ضرایب تک‌درسِ سوابق در این محیط مستقیماً واکشی نشده‌اند. مواد آزمون، "
            "سوابق تحصیلی و وزن‌های شخصی از هم جدا نگه داشته می‌شوند."
        )
        root.addWidget(self.info)
        root.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll)

    # ---- بارگذاری ----

    def refresh(self) -> None:
        from ...jdate import minutes_to_clock

        wake_value = self.service.repo.get_setting("daily.wake_minute")
        sleep_value = self.service.repo.get_setting("daily.sleep_minute")
        self.wake_edit.setText(
            f"{minutes_to_clock(int(wake_value))[0]:02d}:"
            f"{minutes_to_clock(int(wake_value))[1]:02d}"
            if wake_value else ""
        )
        self.sleep_edit.setText(
            f"{minutes_to_clock(int(sleep_value))[0]:02d}:"
            f"{minutes_to_clock(int(sleep_value))[1]:02d}"
            if sleep_value else ""
        )
        energy_value = self.service.repo.get_setting("daily.energy_level")
        self.energy_combo.setCurrentIndex(
            self.energy_combo.findData(int(energy_value)) if energy_value else 0
        )
        advisor_settings = self.service.settings.advisor
        self.mastery_sessions_spin.setValue(advisor_settings.mastery_min_spaced_days)
        self.mastery_spacing_spin.setValue(advisor_settings.mastery_min_spacing_days)
        self.mastery_score_spin.setValue(advisor_settings.mastery_confirming_score)

        self.auto_exam_priority.setChecked(
            self.service.repo.get_setting("priority.use_exam_coefficients") != "0"
        )
        profile = self.service.active_exam_profile()
        if profile is not None:
            self.exam_name_edit.setText(profile.name)
            self.exam_group_edit.setText(profile.group_name)
            self.exam_year_spin.setValue(profile.exam_year or 0)
            self.exam_date_edit.setText(
                profile.target_date.strftime("%Y/%m/%d") if profile.target_date else ""
            )
            index = self.exam_status_combo.findData(profile.date_status.value)
            self.exam_status_combo.setCurrentIndex(max(0, index))
            self.exam_source_edit.setText(profile.source_note)
            self.negative_spin.setValue(profile.negative_marking_ratio)
            formula_index = self.formula_combo.findData(profile.percentage_formula)
            self.formula_combo.setCurrentIndex(max(0, formula_index))
        self._refresh_contribution_notice(profile)

        from ...onboarding import DAY_ORDER

        self.event_list.clear()
        events = self.service.repo.list_fixed_events()
        for event in events:
            recorded = " · ضبط‌شده/غیرهم‌زمان" if event.is_recorded else ""
            item = QListWidgetItem(
                f"{DAY_ORDER[event.weekday]} | {event.start_minute // 60:02d}:"
                f"{event.start_minute % 60:02d}–{event.end_minute // 60:02d}:"
                f"{event.end_minute % 60:02d} | {event.title}{recorded}"
            )
            item.setData(Qt.UserRole, event.id)
            self.event_list.addItem(item)
        if not events:
            self.event_list.addItem("هنوز رویدادی ثبت نشده است.")
        conflicts = self.service.schedule_conflicts()
        if conflicts:
            self.conflict_text.setText(
                "تعارض‌های باز؛ تا رفع آن‌ها برنامه می‌تواند غیرقطعی باشد:\n"
                + "\n".join(f"• {c.describe()} {c.question}" for c in conflicts)
            )
            self.conflict_text.setVisible(True)
        else:
            self.conflict_text.setText("تعارضی بین رویدادهای زندهٔ ثبت‌شده پیدا نشد.")
            self.conflict_text.setVisible(True)

        self.routine_list.clear()
        routines = self.service.repo.list_routines()
        for routine in routines:
            days = ", ".join(DAY_ORDER[d] for d in sorted(routine.weekdays))
            item = QListWidgetItem(
                f"{routine.title} | {routine.start_minute // 60:02d}:"
                f"{routine.start_minute % 60:02d}–{routine.end_minute // 60:02d}:"
                f"{routine.end_minute % 60:02d} | {days}"
            )
            item.setData(Qt.UserRole, routine.id)
            self.routine_list.addItem(item)
        if not routines:
            self.routine_list.addItem("هنوز روالی ثبت نشده است.")

    def _refresh_contribution_notice(self, profile: ExamProfile | None) -> None:
        group = profile.group_name if profile else self.exam_group_edit.text().strip()
        year = profile.exam_year if profile else self.exam_year_spin.value()
        share = EXAM_WEIGHT_BY_GROUP.get(group) if year == 1406 else None
        if share:
            exam_share, transcript_share = share
            self.contribution_notice.setText(
                f"۱۴۰۶ · سهم کل بازنشرشده: آزمون اختصاصی {exam_share}٪، سوابق تحصیلی "
                f"{transcript_share}٪. منبع ثانویه (بازنشر اطلاعیه)؛ نسخهٔ اولیهٔ سنجش "
                "در این محیط مستقیم cross-check نشده. ضرایب تک‌درس آزمون و سابقه، "
                "و وزن شخصی درس، جدا هستند."
            )
        else:
            self.contribution_notice.setText(
                "برای سال/گروه انتخابی سهم کل تأییدشده‌ای در کاتالوگ نیست؛ "
                "وزن ۱۴۰۶ به سال دیگر تعمیم داده نمی‌شود."
            )

    # ---- ذخیره ----

    def _save_daily(self) -> None:
        wake = _parse_clock(self.wake_edit.text())
        sleep = _parse_clock(self.sleep_edit.text())
        if wake is None or sleep is None:
            notify(self, "ساعت نامعتبر", "ساعت خواب و بیداری را به شکل ۰۶:۰۰ وارد کنید.")
            return
        self.service.wake_minute = wake
        self.service.sleep_minute = sleep
        if self.energy_combo.currentData() is not None:
            self.service.energy_level = int(self.energy_combo.currentData())

        peaks: list[tuple[int, int]] = []
        for chunk in self.peak_edit.text().split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            parts = chunk.replace("–", "-").split("-")
            if len(parts) != 2:
                continue
            start = _parse_clock(parts[0])
            end = _parse_clock(parts[1])
            if start is not None and end is not None:
                peaks.append((start, end))
        self.service.peak_hours = peaks
        notify(self, "ذخیره شد", "تنظیمات پنجرهٔ روز ذخیره شد.")

    def _save_mastery(self) -> None:
        advisor = self.service.settings.advisor
        advisor.mastery_min_spaced_days = self.mastery_sessions_spin.value()
        advisor.mastery_min_spacing_days = self.mastery_spacing_spin.value()
        advisor.mastery_confirming_score = self.mastery_score_spin.value()
        self.service.settings.save()
        notify(
            self,
            "ذخیره شد",
            "معیارهای L4 ذخیره شدند. این آستانه‌ها فرضیهٔ محصول هستند، نه تضمین یادگیری.",
        )

    def _save_exam(self) -> None:
        from ...jdate import parse_jalali_date

        target_date = None
        text = self.exam_date_edit.text().strip()
        if text:
            try:
                target_date = parse_jalali_date(text)
            except ValueError as exc:
                notify(self, "تاریخ نامعتبر", str(exc))
                return

        profile = self.service.active_exam_profile()
        entered_name = self.exam_name_edit.text().strip()
        if profile is None:
            if not entered_name:
                notify(self, "ورودی ناقص", "برای ساخت پروفایل، نام آزمون را وارد کنید.")
                return
            if self.exam_status_combo.currentData() is None:
                notify(self, "وضعیت تاریخ", "وضعیت تاریخ را انتخاب کنید؛ در صورت نامعلوم بودن، «نامشخص» را برگزینید.")
                return
            profile = ExamProfile(name=entered_name)
            self.service.create_exam_profile(profile)
        if entered_name:
            profile.name = entered_name
        profile.group_name = self.exam_group_edit.text()
        profile.exam_year = self.exam_year_spin.value() or None
        profile.target_date = target_date
        if self.exam_status_combo.currentData() is not None:
            profile.date_status = DateStatus(self.exam_status_combo.currentData())
        profile.source_note = self.exam_source_edit.text()
        profile.negative_marking_ratio = self.negative_spin.value()
        profile.percentage_formula = str(self.formula_combo.currentData())
        self.service.update_exam_profile(profile)
        self._refresh_contribution_notice(profile)
        self.service.repo.set_setting(
            "priority.use_exam_coefficients", "1" if self.auto_exam_priority.isChecked() else "0"
        )
        self.service.commit()
        notify(self, "ذخیره شد", "پروفایل آزمون و روش اولویت‌بندی به‌روزرسانی شد.")

    def _clear_events(self) -> None:
        if not confirm(
            self,
            "تأیید حذف",
            "همهٔ رویدادهای ثابت حذف می‌شوند. ادامه می‌دهید؟",
        ):
            return
        for event in self.service.repo.list_fixed_events():
            self.service.repo.delete_fixed_event(event.id)
        self.service.commit()
        self.refresh()

    def _selected_id(self, widget: QListWidget) -> int | None:
        item = widget.currentItem()
        value = item.data(Qt.UserRole) if item else None
        return int(value) if value is not None else None

    def _add_event(self) -> None:
        dialog = ScheduleEventDialog(self.service)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.service.create_fixed_event(dialog.value())
        except ValueError as exc:
            notify(self, "اطلاعات نامعتبر", str(exc))
            return
        self.refresh()

    def _edit_event(self) -> None:
        event_id = self._selected_id(self.event_list)
        event = next((e for e in self.service.repo.list_fixed_events() if e.id == event_id), None)
        if event is None:
            notify(self, "رویدادی انتخاب نشده", "ابتدا یک رویداد واقعی از فهرست انتخاب کنید.")
            return
        dialog = ScheduleEventDialog(self.service, event)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.service.update_fixed_event(dialog.value(event_id))
        except ValueError as exc:
            notify(self, "اطلاعات نامعتبر", str(exc))
            return
        self.refresh()

    def _delete_event(self) -> None:
        event_id = self._selected_id(self.event_list)
        if event_id is None:
            notify(self, "رویدادی انتخاب نشده", "ابتدا یک رویداد واقعی از فهرست انتخاب کنید.")
            return
        if confirm(self, "حذف رویداد", "این رویداد هفتگی حذف شود؟"):
            self.service.delete_fixed_event(event_id)
            self.refresh()

    def _add_routine(self) -> None:
        dialog = RoutineDialog()
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.service.create_routine(dialog.value())
        except ValueError as exc:
            notify(self, "اطلاعات نامعتبر", str(exc))
            return
        self.refresh()

    def _edit_routine(self) -> None:
        routine_id = self._selected_id(self.routine_list)
        routine = next((r for r in self.service.repo.list_routines() if r.id == routine_id), None)
        if routine is None:
            notify(self, "روالی انتخاب نشده", "ابتدا یک روال واقعی از فهرست انتخاب کنید.")
            return
        dialog = RoutineDialog(routine)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.service.update_routine(dialog.value(routine_id))
        except ValueError as exc:
            notify(self, "اطلاعات نامعتبر", str(exc))
            return
        self.refresh()

    def _delete_routine(self) -> None:
        routine_id = self._selected_id(self.routine_list)
        if routine_id is None:
            notify(self, "روالی انتخاب نشده", "ابتدا یک روال واقعی از فهرست انتخاب کنید.")
            return
        if confirm(self, "حذف روال", "این بازهٔ ضروری/روال از برنامه حذف شود؟"):
            self.service.delete_routine(routine_id)
            self.refresh()

    def _backup(self) -> None:
        info = self.service.backup()
        notify(
            self,
            "پشتیبان ساخته شد",
            f"مسیر: {info.path}\nنسخهٔ schema: {info.schema_version}",
        )
        self.backup_text.setText(
            f"آخرین پشتیبان: {format_jalali_long(info.created_at.date())}\n{info.path}"
        )

    def _restore(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "انتخاب فایل پشتیبان", "", "پشتیبان (*.k2backup)"
        )
        if not path:
            return
        if not confirm(
            self,
            "تأیید بازیابی",
            "داده‌های فعلی با محتوای فایل پشتیبان جایگزین می‌شوند. ادامه می‌دهید؟",
        ):
            return
        try:
            info = self.service.restore(path)
        except Exception as exc:  # noqa: BLE001 - پیام خطا به کاربر
            notify(self, "بازیابی ناموفق", str(exc))
            return
        notify(
            self,
            "بازیابی انجام شد",
            f"نسخهٔ schema: {info.schema_version}\n"
            f"تعداد رکوردها: {sum(info.counts.values())}",
        )
        self.refresh()


class ScheduleEventDialog(QDialog):
    """ثبت/ویرایش رویداد هفتگی با زمان‌های واقعی."""

    def __init__(self, service: AdvisorService, event: FixedEvent | None = None):
        super().__init__()
        from ...onboarding import DAY_ORDER

        self.service = service
        self.fixed_event = event
        self.setWindowTitle("ویرایش رویداد هفتگی" if event else "افزودن رویداد هفتگی")
        self.setLayoutDirection(Qt.RightToLeft)
        form = QFormLayout(self)
        self.title_edit = QLineEdit(event.title if event else "")
        form.addRow("عنوان:", self.title_edit)
        self.kind_combo = QComboBox()
        for kind in FixedEventKind:
            self.kind_combo.addItem(kind.label, kind.value)
        form.addRow("نوع:", self.kind_combo)
        self.weekday_combo = QComboBox()
        for index, day in enumerate(DAY_ORDER):
            self.weekday_combo.addItem(day, index)
        form.addRow("روز:", self.weekday_combo)
        self.start_edit = QTimeEdit()
        self.start_edit.setDisplayFormat("HH:mm")
        self.end_edit = QTimeEdit()
        self.end_edit.setDisplayFormat("HH:mm")
        form.addRow("از:", self.start_edit)
        form.addRow("تا:", self.end_edit)
        self.subject_combo = QComboBox()
        self.subject_combo.addItem("بدون پیوند به درس", None)
        for subject in service.repo.list_subjects(include_unselected=True):
            self.subject_combo.addItem(subject.name, subject.id)
        form.addRow("درس:", self.subject_combo)
        self.recorded_check = QCheckBox("ضبط‌شده/غیرهم‌زمان؛ این بازه زمان زنده را مسدود نکند")
        form.addRow("وضعیت:", self.recorded_check)
        self.notes_edit = QLineEdit(event.notes if event else "")
        form.addRow("یادداشت:", self.notes_edit)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        form.addRow(self.buttons)
        if event:
            self.title_edit.setText(event.title)
            self.kind_combo.setCurrentIndex(max(0, self.kind_combo.findData(event.kind.value)))
            self.weekday_combo.setCurrentIndex(max(0, self.weekday_combo.findData(event.weekday)))
            self.start_edit.setTime(self.start_edit.time().fromString(
                f"{event.start_minute // 60:02d}:{event.start_minute % 60:02d}", "HH:mm"))
            self.end_edit.setTime(self.end_edit.time().fromString(
                f"{event.end_minute // 60:02d}:{event.end_minute % 60:02d}", "HH:mm"))
            self.subject_combo.setCurrentIndex(max(0, self.subject_combo.findData(event.subject_id)))
            self.recorded_check.setChecked(event.is_recorded)

    def value(self, event_id: int | None = None) -> FixedEvent:
        start = self.start_edit.time()
        end = self.end_edit.time()
        return FixedEvent(
            id=event_id,
            title=self.title_edit.text().strip(),
            kind=FixedEventKind(self.kind_combo.currentData()),
            subject_id=self.subject_combo.currentData(),
            weekday=int(self.weekday_combo.currentData()),
            start_minute=start.hour() * 60 + start.minute(),
            end_minute=end.hour() * 60 + end.minute(),
            is_recorded=self.recorded_check.isChecked(),
            notes=self.notes_edit.text().strip(),
        )


class RoutineDialog(QDialog):
    """ثبت/ویرایش خواب، وعده، استراحت یا روال تکرارشونده."""

    def __init__(self, routine: Routine | None = None):
        super().__init__()
        from ...onboarding import DAY_ORDER

        self.routine = routine
        self.setWindowTitle("ویرایش روال" if routine else "افزودن روال")
        self.setLayoutDirection(Qt.RightToLeft)
        form = QFormLayout(self)
        self.title_edit = QLineEdit(routine.title if routine else "")
        form.addRow("عنوان:", self.title_edit)
        self.kind_combo = QComboBox()
        for kind in RoutineKind:
            self.kind_combo.addItem(kind.label, kind.value)
        form.addRow("دسته:", self.kind_combo)
        self.start_edit = QTimeEdit()
        self.start_edit.setDisplayFormat("HH:mm")
        self.end_edit = QTimeEdit()
        self.end_edit.setDisplayFormat("HH:mm")
        form.addRow("از:", self.start_edit)
        form.addRow("تا:", self.end_edit)
        self.scope_combo = QComboBox()
        for scope in RoutineScope:
            self.scope_combo.addItem(scope.label, scope.value)
        form.addRow("تکرار:", self.scope_combo)
        self.day_checks = []
        days_row = QHBoxLayout()
        for index, day in enumerate(DAY_ORDER):
            check = QCheckBox(day)
            check.setChecked(index in (routine.weekdays if routine else frozenset(range(7))))
            self.day_checks.append(check)
            days_row.addWidget(check)
        form.addRow("روزهای هفته:", days_row)
        self.study_check = QCheckBox("این بازه جزو مطالعه حساب شود")
        self.study_check.setChecked(routine.counts_as_study if routine else False)
        form.addRow("محاسبه:", self.study_check)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        form.addRow(self.buttons)
        if routine:
            self.kind_combo.setCurrentIndex(max(0, self.kind_combo.findData(routine.kind.value)))
            self.scope_combo.setCurrentIndex(max(0, self.scope_combo.findData(routine.scope.value)))
            self.start_edit.setTime(self.start_edit.time().fromString(
                f"{routine.start_minute // 60:02d}:{routine.start_minute % 60:02d}", "HH:mm"))
            self.end_edit.setTime(self.end_edit.time().fromString(
                f"{routine.end_minute // 60:02d}:{routine.end_minute % 60:02d}", "HH:mm"))

    def value(self, routine_id: int | None = None) -> Routine:
        start = self.start_edit.time()
        end = self.end_edit.time()
        return Routine(
            id=routine_id,
            title=self.title_edit.text().strip(),
            kind=RoutineKind(self.kind_combo.currentData()),
            start_minute=start.hour() * 60 + start.minute(),
            end_minute=end.hour() * 60 + end.minute(),
            weekdays=frozenset(i for i, item in enumerate(self.day_checks) if item.isChecked()),
            scope=RoutineScope(self.scope_combo.currentData()),
            counts_as_study=self.study_check.isChecked(),
        )
