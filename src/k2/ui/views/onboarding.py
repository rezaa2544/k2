"""جادوگر راه‌اندازی: مصاحبهٔ مرحله‌ای، قابل ذخیره و قابل ادامه."""

from __future__ import annotations

import datetime as _dt
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
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
from ...konkur_catalog import SUBJECTS_BY_GROUP, source_status_for_year
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
        self._selected_by_group: dict[str, set[str]] = {}
        self._loading_state = False
        self._displayed_subject_group = ""
        self._book_editing = False
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
            if step.key == "exam_group":
                widget.currentTextChanged.connect(self._refresh_subject_options)
            if step.key == "exam_year":
                widget.currentTextChanged.connect(self._update_source_notice)
                notice = QLabel("")
                notice.setObjectName("muted")
                notice.setWordWrap(True)
                notice.setObjectName("yearSourceNotice")
                card.add(notice)
        elif step.kind == "multiselect":
            widget = QWidget()
            widget.setObjectName(f"field_{step.key}")
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(0, 0, 0, 0)
            toolbar = QHBoxLayout()
            select_all = QPushButton("انتخاب همهٔ این رشته")
            select_all.clicked.connect(lambda: self._set_current_subjects(True))
            toolbar.addWidget(select_all)
            select_none = QPushButton("لغو انتخاب‌های این رشته")
            select_none.clicked.connect(lambda: self._set_current_subjects(False))
            toolbar.addWidget(select_none)
            layout.addLayout(toolbar)
            self.subject_list = QListWidget()
            self.subject_list.setObjectName("subjectChoices")
            self.subject_list.itemChanged.connect(self._subject_item_changed)
            layout.addWidget(self.subject_list)
            self.subject_selection_note = QLabel("")
            self.subject_selection_note.setWordWrap(True)
            self.subject_selection_note.setObjectName("muted")
            layout.addWidget(self.subject_selection_note)
            card.add(widget)
        elif step.kind == "books":
            widget = QWidget()
            widget.setObjectName(f"field_{step.key}")
            book_layout = QVBoxLayout(widget)
            book_layout.setContentsMargins(0, 0, 0, 0)
            book_form = QFormLayout()
            self.book_subject_combo = QComboBox()
            book_form.addRow("درس:", self.book_subject_combo)
            self.book_title_edit = QLineEdit()
            self.book_title_edit.setPlaceholderText("عنوان کتاب درسی یا منبع")
            book_form.addRow("عنوان:", self.book_title_edit)
            self.book_code_edit = QLineEdit()
            book_form.addRow("کد کتاب:", self.book_code_edit)
            self.book_grade_edit = QLineEdit()
            self.book_grade_edit.setPlaceholderText("مثلاً پایه یازدهم")
            book_form.addRow("پایه:", self.book_grade_edit)
            self.book_year_edit = QLineEdit()
            self.book_year_edit.setPlaceholderText("سال چاپ (اختیاری)")
            book_form.addRow("سال چاپ:", self.book_year_edit)
            self.book_source_edit = QLineEdit()
            self.book_source_edit.setPlaceholderText("پیوند صفحهٔ همان کتاب در منبع رسمی")
            book_form.addRow("منبع:", self.book_source_edit)
            book_layout.addLayout(book_form)
            add_book_button = QPushButton("افزودن کتاب به فهرست")
            add_book_button.clicked.connect(self._add_book)
            book_layout.addWidget(add_book_button)
            self.book_list = QListWidget()
            self.book_list.setAccessibleName("کتاب‌ها و منابع انتخاب‌شده")
            self.book_list.setMinimumHeight(110)
            self.book_list.itemChanged.connect(self._collect_book_selection)
            book_layout.addWidget(self.book_list)
            book_hint = QLabel(
                "کتاب‌ها تا بازبینی سند/پیوند در وضعیت «واردشده، تأییدنشده» هستند؛ "
                "ضرایب آزمون و سوابق تحصیلی از این فهرست نتیجه‌گیری نمی‌شوند."
            )
            book_hint.setObjectName("muted")
            book_hint.setWordWrap(True)
            book_layout.addWidget(book_hint)
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
        self._loading_state = True
        try:
            import json
            raw_selections = self.state.values.get("subject_selection_by_group", "{}")
            parsed = json.loads(raw_selections)
            self._selected_by_group = {
                str(group): set(map(str, names))
                for group, names in parsed.items()
                if isinstance(names, list)
            }
        except (ValueError, TypeError):
            self._selected_by_group = {}
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
            elif isinstance(widget, QPlainTextEdit):
                widget.setPlainText(value or "")
            elif isinstance(widget, QLabel):
                widget.setText(value or "—")
        self._loading_state = False
        self._refresh_subject_options()
        self._load_book_selections()
        self._update_source_notice()

    def _update_source_notice(self, *_args) -> None:
        step_index = next(i for i, step in enumerate(ONBOARDING_STEPS) if step.key == "exam_year")
        notice = self.stack.widget(step_index).findChild(QLabel, "yearSourceNotice")
        combo = self.stack.widget(step_index).findChild(QComboBox, "field_exam_year")
        if notice is None or combo is None:
            return
        from ...jdate import normalize_digits
        digits = normalize_digits(combo.currentText())
        year = int(digits) if digits.isdigit() else None
        status = source_status_for_year(year)
        if year == 1405:
            notice.setText(
                "۱۴۰۵: اطلاعیهٔ سنجش دربارهٔ فهرست دروس/کتاب‌ها پیدا شد، اما PDF اولیهٔ "
                "سنجش در این بررسی مستقیماً بازبینی نشد؛ ضرایب رسمی در برنامه وارد نشده‌اند."
            )
        elif year == 1406:
            notice.setText(
                "۱۴۰۶: دادهٔ رسمی سالانه در بستهٔ فعلی برنامه وارد/تأیید نشده است؛ "
                "هیچ ضریب یا تاریخ سال قبل به ۱۴۰۶ تعمیم داده نمی‌شود."
            )
        else:
            notice.setText("سال آزمون هنوز مشخص نیست؛ ضرایب رسمی خالی می‌مانند.")
        notice.setToolTip(status)

    def _current_group(self) -> str:
        group = self.stack.widget(
            next(i for i, step in enumerate(ONBOARDING_STEPS) if step.key == "exam_group")
        ).findChild(QComboBox, "field_exam_group")
        return group.currentText() if group else ""

    def _collect_subject_selection(self, group: str | None = None) -> None:
        if not hasattr(self, "subject_list"):
            return
        group = group or self._displayed_subject_group or self._current_group()
        if group not in SUBJECTS_BY_GROUP:
            return
        self._selected_by_group[group] = {
            self.subject_list.item(i).data(Qt.UserRole)
            for i in range(self.subject_list.count())
            if self.subject_list.item(i).checkState() == Qt.Checked
        }
        import json
        payload = {key: sorted(value) for key, value in self._selected_by_group.items()}
        self.state.set_value("subject_selection_by_group", json.dumps(payload, ensure_ascii=False))
        self.state.set_value("subjects", json.dumps(sorted(self._selected_by_group.get(group, set())), ensure_ascii=False))

    def _refresh_subject_options(self, *_args) -> None:
        if not hasattr(self, "subject_list") or self._loading_state:
            return
        if self._displayed_subject_group:
            self._collect_subject_selection(self._displayed_subject_group)
        group = self._current_group()
        options = SUBJECTS_BY_GROUP.get(group, ())
        selected = self._selected_by_group.get(group, set())
        self.subject_list.blockSignals(True)
        self.subject_list.clear()
        from PySide6.QtWidgets import QListWidgetItem
        for subject in options:
            item = QListWidgetItem(subject)
            item.setData(Qt.UserRole, subject)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if subject in selected else Qt.Unchecked)
            self.subject_list.addItem(item)
        self.subject_list.blockSignals(False)
        self._displayed_subject_group = group
        self._refresh_book_subject_options()
        retained = [g for g, names in self._selected_by_group.items() if g != group and names]
        if retained:
            self.subject_selection_note.setText(
                "انتخاب‌های رشته‌های قبلی حفظ شده‌اند و حذف نشده‌اند: " + "، ".join(retained)
                + "؛ برای ویرایش، رشتهٔ مربوط را انتخاب کنید."
            )
        else:
            self.subject_selection_note.setText(
                "در این پیش‌فهرست هیچ ضریب رسمی/تأییدشده‌ای ثبت نشده؛ "
                "انتخاب درس به‌تنهایی ضریب یا اولویت رسمی ایجاد نمی‌کند."
            )

    def _subject_item_changed(self, _item) -> None:
        if not self._loading_state:
            self._collect_subject_selection()

    def _set_current_subjects(self, selected: bool) -> None:
        self.subject_list.blockSignals(True)
        for index in range(self.subject_list.count()):
            self.subject_list.item(index).setCheckState(Qt.Checked if selected else Qt.Unchecked)
        self.subject_list.blockSignals(False)
        self._collect_subject_selection()

    def _refresh_book_subject_options(self) -> None:
        if not hasattr(self, "book_subject_combo"):
            return
        selected = sorted(self._selected_by_group.get(self._current_group(), set()))
        values = selected or list(SUBJECTS_BY_GROUP.get(self._current_group(), ()))
        current = self.book_subject_combo.currentText()
        self.book_subject_combo.blockSignals(True)
        self.book_subject_combo.clear()
        for value in values:
            self.book_subject_combo.addItem(value)
        index = self.book_subject_combo.findText(current)
        self.book_subject_combo.setCurrentIndex(max(0, index))
        self.book_subject_combo.blockSignals(False)

    def _load_book_selections(self) -> None:
        if not hasattr(self, "book_list"):
            return
        import json
        raw = self.state.values.get("books", "")
        entries = []
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    entries = [item for item in parsed if isinstance(item, dict)]
            except (ValueError, TypeError):
                entries = []
        elif (profile := self.service.active_exam_profile()) is not None:
            entries = [
                {
                    "subject": next((s.name for s in self.service.repo.list_subjects(profile.id) if s.id == b.subject_id), ""),
                    "title": b.title, "code": b.book_code, "grade": b.grade,
                    "year": b.edition_year or "", "source": b.source_url,
                    "status": b.source_status, "selected": b.is_selected,
                }
                for b in self.service.repo.list_textbooks(profile.id)
            ]
        self.book_list.blockSignals(True)
        self.book_list.clear()
        for entry in entries:
            self._append_book_item(entry)
        self.book_list.blockSignals(False)
        self._refresh_book_subject_options()

    def _append_book_item(self, entry: dict) -> None:
        title = str(entry.get("title", "")).strip()
        subject = str(entry.get("subject", "")).strip()
        if not title:
            return
        code = str(entry.get("code", "")).strip()
        grade = str(entry.get("grade", "")).strip()
        year = str(entry.get("year", "")).strip()
        label = f"{subject or 'بدون درس'} — {title}"
        if code:
            label += f" · کد {code}"
        if grade:
            label += f" · {grade}"
        if year:
            label += f" · چاپ {year}"
        label += " · واردشده/تأییدنشده"
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole, entry)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked if entry.get("selected", True) else Qt.Unchecked)
        self.book_list.addItem(item)

    def _add_book(self) -> None:
        title = self.book_title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "عنوان لازم است", "برای افزودن کتاب، عنوان آن را وارد کنید.")
            return
        entry = {
            "subject": self.book_subject_combo.currentText(),
            "title": title,
            "code": self.book_code_edit.text().strip(),
            "grade": self.book_grade_edit.text().strip(),
            "year": self.book_year_edit.text().strip(),
            "source": self.book_source_edit.text().strip(),
            "status": "user_entered_unverified",
            "selected": True,
        }
        self.book_list.blockSignals(True)
        self._append_book_item(entry)
        self.book_list.blockSignals(False)
        self.book_title_edit.clear()
        self.book_code_edit.clear()
        self._collect_book_selection()

    def _collect_book_selection(self, *_args) -> None:
        if not hasattr(self, "book_list") or self._book_editing:
            return
        self._book_editing = True
        import json
        entries = []
        for index in range(self.book_list.count()):
            item = self.book_list.item(index)
            entry = dict(item.data(Qt.UserRole) or {})
            entry["selected"] = item.checkState() == Qt.Checked
            entries.append(entry)
        self.state.set_value("books", json.dumps(entries, ensure_ascii=False))
        self._book_editing = False

    def _collect(self) -> None:
        self._collect_subject_selection()
        self._collect_book_selection()
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
            elif isinstance(widget, QPlainTextEdit):
                self.state.set_value(step.key, widget.toPlainText().strip())
            elif step.kind == "multiselect":
                self._collect_subject_selection()
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
        if step.key == "exam_date":
            try:
                from ...jdate import parse_jalali_date
                parse_jalali_date(self.state.values.get("exam_date", ""))
            except ValueError as exc:
                QMessageBox.warning(self, "تاریخ نامعتبر", str(exc))
                return
        if step.key == "weekly_schedule" and not self.service.repo.list_fixed_events():
            QMessageBox.warning(
                self, "برنامهٔ هفتگی لازم است",
                "ابتدا برنامهٔ نمونه را وارد کنید یا رویدادهای خود را در تنظیمات ثبت کنید.",
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
        self._apply_sunday_recorded_choice()
        conflicts = self.service.schedule_conflicts()
        if conflicts:
            QMessageBox.warning(
                self, "تعارض برنامه حل نشده است",
                "پیش از پایان راه‌اندازی، تعارض رویدادهای زنده را در تنظیمات "
                "ویرایش یا یکی را ضبط‌شده علامت بزنید:\n\n"
                + "\n".join(c.describe() for c in conflicts),
            )
            return
        if self.state.values.get("exam_date_status") == "رسمی (منبع ثبت‌شده)":
            source = self.state.values.get("exam_source", "").lower()
            official_domains = ("sanjesh.org", "sccr.ir", "medu.gov.ir", "chap.sch.ir")
            if not any(domain in source for domain in official_domains):
                QMessageBox.warning(
                    self, "منبع رسمی لازم است",
                    "برای انتخاب وضعیت رسمی، نشانی منبع از دامنهٔ رسمی سنجش، "
                    "شورای عالی انقلاب فرهنگی یا آموزش‌وپرورش را در مرحلهٔ منبع وارد کنید.",
                )
                return
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

    def _apply_sunday_recorded_choice(self) -> None:
        """تبدیل پاسخ یکشنبه به دادهٔ واقعی رویدادها؛ تعارض صرفاً متنی حل نمی‌شود."""
        choice = self.state.values.get("sunday_recorded", "")
        if choice not in {"شیمی", "دینی"}:
            return
        from ...domain.enums import FixedEventKind

        for event in self.service.repo.list_fixed_events():
            if event.weekday == 1 and choice in event.title:
                event.is_recorded = True
                event.kind = FixedEventKind.RECORDED_CLASS
                self.service.repo.update_fixed_event(event)
        self.service.commit()

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

        import json
        from ...domain.models import Textbook

        year_text = values.get("exam_year", "")
        digits = __import__("k2.jdate", fromlist=["normalize_digits"]).normalize_digits(year_text)
        profile.exam_year = int(digits) if digits.isdigit() else None
        profile.regulation_version = f"کنکور {profile.exam_year}" if profile.exam_year else ""
        self.service.update_exam_profile(profile)

        try:
            selection_map = json.loads(values.get("subject_selection_by_group", "{}"))
        except (ValueError, TypeError):
            selection_map = {}
        selected_names = set(selection_map.get(profile.group_name, []))
        existing = {
            subject.name: subject
            for subject in self.service.repo.list_subjects(profile.id, include_unselected=True)
        }
        for subject in existing.values():
            subject.is_selected = subject.name in selected_names
            self.service.repo.update_subject(subject)
        for name in selected_names:
            if name not in existing:
                self.service.repo.create_subject(
                    Subject(name=name, exam_profile_id=profile.id, is_selected=True)
                )

        # کتاب‌ها در این مرحله دادهٔ واردشدهٔ کاربرند، نه catalog رسمیِ تأییدشده.
        # ردیف قدیمی حذف نمی‌شود؛ نبودن آن در فرم فقط انتخابش را لغو می‌کند.
        existing_books = self.service.repo.list_textbooks(profile.id)
        for book in existing_books:
            self.service.repo.set_textbook_selected(book.id, False)
        subject_by_name = {
            subject.name: subject
            for subject in self.service.repo.list_subjects(profile.id, include_unselected=True)
        }
        try:
            book_entries = json.loads(values.get("books", "[]"))
        except (ValueError, TypeError):
            book_entries = []
        for entry in book_entries if isinstance(book_entries, list) else []:
            if not isinstance(entry, dict) or not str(entry.get("title", "")).strip():
                continue
            year_text = __import__("k2.jdate", fromlist=["normalize_digits"]).normalize_digits(str(entry.get("year", "")))
            book = Textbook(
                exam_profile_id=profile.id,
                subject_id=subject_by_name.get(str(entry.get("subject", ""))).id
                if str(entry.get("subject", "")) in subject_by_name else None,
                title=str(entry.get("title", "")).strip(),
                book_code=str(entry.get("code", "")).strip(),
                grade=str(entry.get("grade", "")).strip(),
                edition_year=int(year_text) if year_text.isdigit() else None,
                source_url=str(entry.get("source", "")).strip(),
                source_status="user_entered_unverified",
                is_selected=bool(entry.get("selected", True)),
            )
            self.service.repo.save_textbook_selection(book)
        self.service.conn.commit()

        sleep_pair = parse_clock_pair(values.get("sleep_time", ""))
        if sleep_pair:
            self.service.wake_minute = sleep_pair[0]
            self.service.sleep_minute = sleep_pair[1]

        sunday = values.get("sunday_recorded", "")
        if sunday and sunday not in {"—", ""}:
            self.service.repo.set_setting("onboarding.sunday_recorded", sunday)
            self.service.commit()
