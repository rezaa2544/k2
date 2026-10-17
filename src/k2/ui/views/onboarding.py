"""جادوگر راه‌اندازی: مصاحبهٔ مرحله‌ای، قابل ذخیره و قابل ادامه."""

from __future__ import annotations

import datetime as _dt
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ...domain.enums import DateStatus
from ...domain.models import ExamProfile, Subject
from ...onboarding import (
    ONBOARDING_STEPS,
    OnboardingState,
    parse_clock_pair,
    parse_subjects,
    summarize,
)
from ...service import AdvisorService
from ..widgets import Card, info_box


class OnboardingWizard(QDialog):
    """راه‌اندازی گام‌به‌گام.

    وضعیت مصاحبه در جدول ``settings`` ذخیره می‌شود، بنابراین کاربر می‌تواند
    خارج شود و بعداً ادامه دهد (ONB-01).
    """

    def __init__(self, service: AdvisorService, parent: QWidget | None = None):
        super().__init__(parent)
        self.service = service
        self.state: OnboardingState = service.onboarding_state()
        self.setWindowTitle("راه‌اندازی — مشاور هوشمند کنکور")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(720, 560)
        self._build()
        self._load_state_into_widgets()
        self._goto(self.state.current_index)

    # ---- ساخت ----

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(10)

        self.header = QLabel()
        self.header.setObjectName("sectionTitle")
        root.addWidget(self.header)

        self.progress_label = QLabel()
        self.progress_label.setObjectName("muted")
        root.addWidget(self.progress_label)

        body = QHBoxLayout()
        body.setSpacing(12)

        self.step_list = QListWidget()
        self.step_list.setMaximumWidth(240)
        for index, step in enumerate(ONBOARDING_STEPS):
            item = QListWidgetItem(f"{index + 1}. {step.title}")
            self.step_list.addItem(item)
        self.step_list.currentRowChanged.connect(self._on_step_selected)
        body.addWidget(self.step_list)

        self.stack = QStackedWidget()
        for step in ONBOARDING_STEPS:
            self.stack.addWidget(self._build_step(step))
        body.addWidget(self.stack, 1)
        root.addLayout(body, 1)

        self.conflict_box = info_box()
        self.conflict_box.setVisible(False)
        root.addWidget(self.conflict_box)

        buttons = QHBoxLayout()
        self.btn_prev = QPushButton("مرحلهٔ قبل")
        self.btn_prev.clicked.connect(self._prev)
        self.btn_next = QPushButton("مرحلهٔ بعد")
        self.btn_next.setObjectName("primary")
        self.btn_next.clicked.connect(self._next)
        self.btn_finish = QPushButton("پایان راه‌اندازی")
        self.btn_finish.setObjectName("primary")
        self.btn_finish.clicked.connect(self._finish)
        self.btn_save = QPushButton("ذخیره و ادامه بعدی")
        self.btn_save.clicked.connect(self._save_and_close)
        buttons.addWidget(self.btn_prev)
        buttons.addWidget(self.btn_save)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_next)
        buttons.addWidget(self.btn_finish)
        root.addLayout(buttons)

        self._refresh_nav()

    def _build_step(self, step) -> QWidget:
        card = Card(step.title)
        description = QLabel(step.description)
        description.setObjectName("muted")
        description.setWordWrap(True)
        card.add(description)

        if step.kind == "choice":
            widget = QComboBox()
            for option in step.options:
                widget.addItem(option)
            widget.setObjectName(f"field_{step.key}")
            card.add(widget)
        elif step.kind == "number":
            widget = QComboBox()
            for option in step.options:
                widget.addItem(option)
            widget.setObjectName(f"field_{step.key}")
            card.add(widget)
        elif step.kind == "schedule":
            widget = QLabel("—")
            widget.setWordWrap(True)
            widget.setObjectName(f"field_{step.key}")
            card.add(widget)
            btn = QPushButton("ورود برنامهٔ نمونهٔ ثبت‌شده")
            btn.setObjectName(f"btn_{step.key}")
            btn.clicked.connect(self._import_sample)
            card.add(btn)
        elif step.kind == "confirm":
            widget = QLabel("—")
            widget.setWordWrap(True)
            widget.setObjectName(f"field_{step.key}")
            card.add(widget)
        else:
            widget = QLineEdit()
            widget.setObjectName(f"field_{step.key}")
            card.add(widget)

        return card

    # ---- بارگذاری/ذخیرهٔ وضعیت ----

    def _load_state_into_widgets(self) -> None:
        for step in ONBOARDING_STEPS:
            widget = self.stack.widget(ONBOARDING_STEPS.index(step)).findChild(
                QWidget, f"field_{step.key}"
            )
            if widget is None:
                continue
            value = self.state.values.get(step.key)
            if isinstance(widget, QComboBox):
                if value is not None:
                    index = widget.findText(value)
                    if index >= 0:
                        widget.setCurrentIndex(index)
            elif isinstance(widget, QLineEdit):
                widget.setText(value or "")
            elif isinstance(widget, QLabel):
                widget.setText(value or "—")

    def _collect(self) -> None:
        for step in ONBOARDING_STEPS:
            widget = self.stack.widget(ONBOARDING_STEPS.index(step)).findChild(
                QWidget, f"field_{step.key}"
            )
            if widget is None:
                continue
            if isinstance(widget, QComboBox):
                self.state.set_value(step.key, widget.currentText())
            elif isinstance(widget, QLineEdit):
                self.state.set_value(step.key, widget.text().strip())
            elif isinstance(widget, QLabel) and step.kind == "schedule":
                continue

    def _save_state(self) -> None:
        self.service.save_onboarding_state(self.state)

    # ---- ناوبری ----

    def _goto(self, index: int) -> None:
        index = max(0, min(len(ONBOARDING_STEPS) - 1, index))
        self.state.current_index = index
        step = ONBOARDING_STEPS[index]
        self.stack.setCurrentIndex(index)
        self.step_list.setCurrentRow(index)
        self.header.setText(step.title)
        self.progress_label.setText(
            f"مرحلهٔ {index + 1} از {len(ONBOARDING_STEPS)} — پیش‌نیاز: "
            + (ONBOARDING_STEPS[index - 1].title if index > 0 else "شروع")
        )
        self._refresh_nav()
        if step.kind == "confirm":
            self._collect()
            widget = self.stack.widget(index).findChild(QLabel, "field_confirm")
            if widget is not None:
                widget.setText("\n".join(summarize(self.state)))

    def _on_step_selected(self, row: int) -> None:
        if row >= 0:
            self._goto(row)

    def _next(self) -> None:
        self._collect()
        step = ONBOARDING_STEPS[self.state.current_index]
        if step.required and not self.state.values.get(step.key):
            QMessageBox.warning(
                self, "ورودی ناقص", f"«{step.title}» الزامی است."
            )
            return
        if step.blocking_question:
            self.state.complete_step(step.key)
        else:
            self.state.complete_step(step.key)
        self._save_state()
        if self.state.current_index < len(ONBOARDING_STEPS) - 1:
            self._goto(self.state.current_index + 1)
        else:
            self._finish()

    def _prev(self) -> None:
        self._collect()
        self._save_state()
        self._goto(self.state.current_index - 1)

    def _refresh_nav(self) -> None:
        last = len(ONBOARDING_STEPS) - 1
        self.btn_prev.setEnabled(self.state.current_index > 0)
        self.btn_next.setEnabled(self.state.current_index < last)
        self.btn_finish.setEnabled(self.state.current_index == last)

        unresolved = self.state.unresolved_blocking_questions()
        if unresolved:
            self.conflict_box.setVisible(True)
            self.conflict_box.setText(
                "پیش از ساخت برنامهٔ قطعی باید به این پرسش پاسخ داده شود:\n"
                + "\n".join(f"• {q}" for q in unresolved)
            )
        else:
            self.conflict_box.setVisible(False)

    # ---- کنش‌ها ----

    def _import_sample(self) -> None:
        events, routines = self.service.import_sample_schedule()
        conflicts = self.service.schedule_conflicts()
        text = f"{events} رویداد ثابت و {routines} بازهٔ ضروری وارد شد."
        if conflicts:
            text += "\n\nتعارض شناسایی‌شده:\n" + "\n".join(c.describe() for c in conflicts)
        widget = self.stack.widget(
            ONBOARDING_STEPS.index(
                next(s for s in ONBOARDING_STEPS if s.key == "weekly_schedule")
            )
        ).findChild(QLabel, "field_weekly_schedule")
        if widget is not None:
            widget.setText(text)
        self.state.set_value("weekly_schedule", text)
        self.state.complete_step("weekly_schedule")
        self._save_state()

    def _save_and_close(self) -> None:
        self._collect()
        self._save_state()
        self.accept()

    def _finish(self) -> None:
        self._collect()
        unresolved = self.state.unresolved_blocking_questions()
        if unresolved:
            QMessageBox.warning(
                self,
                "پرسش بی‌پاسخ",
                "تا زمانی که به پرسش‌های مسدودکننده پاسخ ندهید، برنامهٔ قطعی "
                "ساخته نمی‌شود:\n\n" + "\n".join(f"• {q}" for q in unresolved),
            )
            return

        self._apply_to_profile()
        self.state.complete_step("confirm")
        self._save_state()
        self.accept()

    def _apply_to_profile(self) -> None:
        """داده‌های مصاحبه را در پروفایل و تنظیمات ذخیره می‌کند."""
        values = self.state.values

        profile = self.service.active_exam_profile()
        if profile is None:
            profile = ExamProfile(name=values.get("exam_name", "آزمون هدف"))
            self.service.create_exam_profile(profile)
        profile.name = values.get("exam_name", profile.name)
        profile.group_name = values.get("exam_group", "")
        source_note = values.get("exam_source", "")
        profile.source_note = source_note

        date_text = values.get("exam_date", "")
        if date_text:
            from ...jdate import parse_jalali_date

            try:
                profile.target_date = parse_jalali_date(date_text)
            except ValueError:
                pass

        status_text = values.get("exam_date_status", "")
        mapping = {
            "رسمی (منبع ثبت‌شده)": DateStatus.OFFICIAL,
            "تخمینی": DateStatus.ESTIMATED,
            "نامشخص": DateStatus.UNKNOWN,
        }
        profile.date_status = mapping.get(status_text, DateStatus.UNKNOWN)
        self.service.update_exam_profile(profile)

        subjects = parse_subjects(values.get("subjects", ""))
        existing = {s.name: s for s in self.service.repo.list_subjects()}
        for name, coefficient in subjects:
            if name in existing:
                subject = existing[name]
                subject.coefficient = coefficient
                self.service.repo.conn.execute(
                    "UPDATE subject SET coefficient = ? WHERE id = ?",
                    (coefficient, subject.id),
                )
            else:
                self.service.create_subject(
                    Subject(
                        name=name,
                        coefficient=coefficient,
                        exam_profile_id=profile.id,
                    )
                )

        sleep_pair = parse_clock_pair(values.get("sleep_time", ""))
        if sleep_pair:
            self.service.wake_minute = sleep_pair[0]
            self.service.sleep_minute = sleep_pair[1]

        sunday = values.get("sunday_recorded", "")
        if sunday and sunday not in {"—", ""}:
            self.service.repo.set_setting("onboarding.sunday_recorded", sunday)
            self.service.commit()
