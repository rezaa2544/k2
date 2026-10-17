"""نمای تنظیمات: پنجرهٔ روز، انرژی، پروفایل آزمون و پشتیبان‌گیری."""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...domain.enums import DateStatus
from ...domain.models import ExamProfile
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
        root = QVBoxLayout(self)
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

        exam_card = Card("پروفایل آزمون هدف (قابل ویرایش)")
        exam_form = QFormLayout()
        self.exam_name_edit = QLineEdit()
        exam_form.addRow("نام آزمون:", self.exam_name_edit)
        self.exam_group_edit = QLineEdit()
        exam_form.addRow("گروه/رشته:", self.exam_group_edit)
        self.exam_date_edit = QLineEdit()
        self.exam_date_edit.setPlaceholderText("۱۴۰۵/۰۷/۲۴")
        exam_form.addRow("تاریخ هدف (شمسی):", self.exam_date_edit)
        self.exam_status_combo = QComboBox()
        for status in DateStatus:
            self.exam_status_combo.addItem(status.label, status.value)
        exam_form.addRow("وضعیت تاریخ:", self.exam_status_combo)
        self.exam_source_edit = QLineEdit()
        self.exam_source_edit.setPlaceholderText("عنوان و محل اطلاعیهٔ رسمی")
        exam_form.addRow("منبع:", self.exam_source_edit)
        self.negative_spin = QDoubleSpinBox()
        self.negative_spin.setRange(0.0, 1.0)
        self.negative_spin.setSingleStep(0.05)
        self.negative_spin.setDecimals(2)
        exam_form.addRow("ضریب نمرهٔ منفی:", self.negative_spin)
        self.formula_combo = QComboBox()
        self.formula_combo.addItem("درصد خام", "raw")
        self.formula_combo.addItem("درصد با نمرهٔ منفی", "negative")
        exam_form.addRow("فرمول درصد:", self.formula_combo)
        btn_exam = QPushButton("ذخیرهٔ پروفایل آزمون")
        btn_exam.setObjectName("primary")
        btn_exam.clicked.connect(self._save_exam)
        exam_form.addRow(btn_exam)
        exam_card.add_layout(exam_form)
        root.addWidget(exam_card)

        schedule_card = Card("برنامهٔ کلاس‌ها و تعهدات")
        self.schedule_text = QLabel("—")
        self.schedule_text.setWordWrap(True)
        schedule_card.add(self.schedule_text)
        buttons = QHBoxLayout()
        btn_import = QPushButton("ورود برنامهٔ نمونهٔ ثبت‌شده")
        btn_import.clicked.connect(self._import_sample)
        buttons.addWidget(btn_import)
        btn_clear = QPushButton("پاک‌کردن رویدادهای ثابت")
        btn_clear.clicked.connect(self._clear_events)
        buttons.addWidget(btn_clear)
        schedule_card.add_layout(buttons)
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
            "همهٔ داده‌ها روی همین رایانه و در SQLite نگهداری می‌شوند. هستهٔ "
            "برنامه به اینترنت نیازی ندارد. هیچ تاریخ یا ضریب رسمی کنکور در کد "
            "ثابت نشده است."
        )
        root.addWidget(self.info)
        root.addStretch(1)

    # ---- بارگذاری ----

    def refresh(self) -> None:
        from ...jdate import minutes_to_clock

        self.wake_edit.setText(
            f"{minutes_to_clock(self.service.wake_minute)[0]:02d}:"
            f"{minutes_to_clock(self.service.wake_minute)[1]:02d}"
        )
        self.sleep_edit.setText(
            f"{minutes_to_clock(self.service.sleep_minute)[0]:02d}:"
            f"{minutes_to_clock(self.service.sleep_minute)[1]:02d}"
        )
        self.energy_combo.setCurrentIndex(max(0, self.service.energy_level - 1))

        profile = self.service.active_exam_profile()
        if profile is not None:
            self.exam_name_edit.setText(profile.name)
            self.exam_group_edit.setText(profile.group_name)
            self.exam_date_edit.setText(
                profile.target_date.strftime("%Y/%m/%d") if profile.target_date else ""
            )
            index = self.exam_status_combo.findData(profile.date_status.value)
            self.exam_status_combo.setCurrentIndex(max(0, index))
            self.exam_source_edit.setText(profile.source_note)
            self.negative_spin.setValue(profile.negative_marking_ratio)
            formula_index = self.formula_combo.findData(profile.percentage_formula)
            self.formula_combo.setCurrentIndex(max(0, formula_index))

        events = self.service.repo.list_fixed_events()
        if events:
            from ...domain.models import FixedEvent
            from ...jdate import WEEKDAY_NAMES

            lines = []
            for event in events:
                lines.append(
                    f"• {WEEKDAY_NAMES[event.weekday]} — {event.title} "
                    f"({event.start_minute // 60:02d}:{event.start_minute % 60:02d}–"
                    f"{event.end_minute // 60:02d}:{event.end_minute % 60:02d})"
                )
            self.schedule_text.setText("\n".join(lines))
        else:
            self.schedule_text.setText("هنوز رویداد ثابتی ثبت نشده است.")

    # ---- ذخیره ----

    def _save_daily(self) -> None:
        wake = _parse_clock(self.wake_edit.text())
        sleep = _parse_clock(self.sleep_edit.text())
        if wake is None or sleep is None:
            notify(self, "ساعت نامعتبر", "ساعت خواب و بیداری را به شکل ۰۶:۰۰ وارد کنید.")
            return
        self.service.wake_minute = wake
        self.service.sleep_minute = sleep
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
        if profile is None:
            profile = ExamProfile(name=self.exam_name_edit.text() or "آزمون هدف")
            self.service.create_exam_profile(profile)
        profile.name = self.exam_name_edit.text() or profile.name
        profile.group_name = self.exam_group_edit.text()
        profile.target_date = target_date
        profile.date_status = DateStatus(self.exam_status_combo.currentData())
        profile.source_note = self.exam_source_edit.text()
        profile.negative_marking_ratio = self.negative_spin.value()
        profile.percentage_formula = str(self.formula_combo.currentData())
        self.service.update_exam_profile(profile)
        notify(self, "ذخیره شد", "پروفایل آزمون به‌روزرسانی شد.")

    def _import_sample(self) -> None:
        event_count, routine_count = self.service.import_sample_schedule()
        notify(
            self,
            "برنامهٔ نمونه وارد شد",
            f"{event_count} رویداد ثابت و {routine_count} بازهٔ ضروری ثبت شد.\n"
            "تعارض یکشنبه (شیمی/دینی) همچنان باز است و باید تعیین شود.",
        )
        self.refresh()

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
