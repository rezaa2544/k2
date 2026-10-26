"""جادوگر راه‌اندازی: مصاحبهٔ مرحله‌ای، قابل ذخیره و قابل ادامه."""

from __future__ import annotations

import datetime as _dt
from typing import Optional

from PySide6.QtCore import Qt, QTime
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
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from ...domain.enums import DateStatus, FixedEventKind, RoutineKind, RoutineScope
from ...domain.models import ExamProfile, FixedEvent, Routine, Subject
from ...konkur_catalog import (
    EXAM_WEIGHT_BY_GROUP,
    SUBJECTS_BY_GROUP,
    SOURCE_SANJESH_1406,
    catalog_books_for_selection,
    courses_for_group,
    is_official_exam_source_url,
    source_status_for_year,
    subject_metadata,
)
from ...onboarding import (
    DAY_ORDER,
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
        self._event_editors: dict[str, dict] = {}
        self._routine_editors: dict[str, dict] = {}
        self.setWindowTitle("راه‌اندازی — مشاور هوشمند کنکور")
        self.setLayoutDirection(Qt.RightToLeft)
        # اندازهٔ اولیهٔ کافی برای گام‌های کوتاه؛ گام‌های بلند داخل ناحیهٔ
        # اسکرول نمایش داده می‌شوند، پس هیچ ورودی‌ای بریده یا دست‌نیافتنی
        # نمی‌شود. حداقل اندازه باعث می‌شود کاربر بتواند پنجره را بزرگ‌تر کند.
        self.resize(760, 620)
        self.setMinimumSize(620, 460)
        self._build()
        self._load_state_into_widgets()
        self._goto(self.state.current_index)

    # ---- ساخت ----

    def _wrap_step(self, card: QWidget) -> QScrollArea:
        """گام راه‌اندازی را در ناحیهٔ اسکرول می‌گذارد.

        بدون این، گام‌های بلند (کتاب‌ها، کلاس‌ها، روال‌ها) از کادر پنجره
        بیرون می‌زدند و دکمه‌های پایین‌شان — از جمله «افزودن کتاب به فهرست» —
        بریده و دست‌نیافتنی می‌شدند. ``setWidgetResizable`` باعث می‌شود محتوا
        در عرض موجود بنشیند و فقط وقتی بلندتر است اسکرول شود.
        """
        scroll = QScrollArea()
        scroll.setObjectName("onboardingStepScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # کارت در ارتفاع کشش نمی‌خورد تا وقتی محتوا کوتاه است، فاصلهٔ خالی
        # اضافی در پایین کارت نماند.
        card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        scroll.setWidget(card)
        return scroll

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
            self.stack.addWidget(self._wrap_step(self._build_step(step)))
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
        # گام‌های اختیاری باید صریحاً قابل رد شدن باشند (تکمیل تدریجی).
        self.btn_skip = QPushButton("رد کردن این گام")
        self.btn_skip.clicked.connect(self._skip_step)
        buttons.addWidget(self.btn_prev)
        buttons.addWidget(self.btn_save)
        buttons.addWidget(self.btn_skip)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_next)
        buttons.addWidget(self.btn_finish)
        root.addLayout(buttons)

        self._refresh_nav()

    def _build_step(self, step) -> QWidget:
        card = Card(step.title, tone="accent")
        description = QLabel(step.description)
        description.setObjectName("muted")
        description.setWordWrap(True)
        card.add(description)

        if step.kind == "choice":
            widget = QComboBox()
            widget.addItem("انتخاب کنید", "")
            for option in step.options:
                widget.addItem(option, option)
            if step.key == "priority_mode":
                widget.setCurrentIndex(1)
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
            book_actions = QHBoxLayout()
            choose_all_books = QPushButton("انتخاب همهٔ کتاب‌های نمایش‌داده‌شده")
            choose_all_books.clicked.connect(lambda: self._set_books_selected(True))
            choose_none_books = QPushButton("لغو انتخاب کتاب‌ها")
            choose_none_books.clicked.connect(lambda: self._set_books_selected(False))
            remove_book = QPushButton("حذف ردیف دستی")
            remove_book.clicked.connect(self._remove_selected_book)
            book_actions.addWidget(choose_all_books)
            book_actions.addWidget(choose_none_books)
            book_actions.addWidget(remove_book)
            book_layout.addLayout(book_actions)
            book_hint = QLabel(
                "کتاب‌ها تا بازبینی سند/پیوند در وضعیت «واردشده، تأییدنشده» هستند؛ "
                "ضرایب آزمون و سوابق تحصیلی از این فهرست نتیجه‌گیری نمی‌شوند."
            )
            book_hint.setObjectName("muted")
            book_hint.setWordWrap(True)
            book_layout.addWidget(book_hint)
            card.add(widget)
        elif step.kind == "events":
            widget = self._build_event_editor(step.key)
            card.add(widget)
        elif step.kind == "routines":
            widget = self._build_routine_editor(step.key)
            card.add(widget)
        elif step.kind == "number":
            widget = QComboBox()
            widget.addItem("انتخاب کنید", "")
            for option in step.options:
                widget.addItem(option, option)
            widget.setObjectName(f"field_{step.key}")
            card.add(widget)
        elif step.kind == "schedule":
            widget = QLabel(step.description)
            widget.setWordWrap(True)
            widget.setObjectName(f"field_{step.key}")
            card.add(widget)
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

    def _build_event_editor(self, key: str) -> QWidget:
        root = QWidget()
        root.setObjectName(f"field_{key}")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 4, 0, 0)
        form = QFormLayout()
        title = QLineEdit()
        title.setPlaceholderText("عنوان جلسه یا تعهد")
        kind = QComboBox()
        choices = (
            (("کلاس حضوری", "live_class"), ("کلاس آنلاین زنده", "online_class"), ("کلاس ضبط‌شده", "recorded_class"))
            if key == "classes" else (("آزمون", "exam"), ("تعهد شخصی/رفت‌وآمد", "commitment"))
        )
        for label, value in choices:
            kind.addItem(label, value)
        subject = QComboBox()
        subject.addItem("بدون درس", "")
        weekday = QComboBox()
        for index, day in enumerate(DAY_ORDER):
            weekday.addItem(day, index)
        start = QTimeEdit()
        start.setDisplayFormat("HH:mm")
        start.setTime(QTime(15, 0))
        end = QTimeEdit()
        end.setDisplayFormat("HH:mm")
        end.setTime(QTime(16, 0))
        form.addRow("عنوان:", title)
        form.addRow("نوع:", kind)
        form.addRow("درس:", subject)
        form.addRow("روز هفته:", weekday)
        form.addRow("شروع:", start)
        form.addRow("پایان:", end)
        layout.addLayout(form)
        actions = QHBoxLayout()
        add = QPushButton("افزودن جلسه/تعهد")
        remove = QPushButton("حذف ردیف انتخاب‌شده از پیش‌نویس")
        actions.addWidget(add)
        actions.addWidget(remove)
        layout.addLayout(actions)
        rows = QListWidget()
        rows.setMinimumHeight(120)
        rows.setAccessibleName("رویدادهای هفتگی ثبت‌شده در این مرحله")
        layout.addWidget(rows)
        self._event_editors[key] = {
            "title": title, "kind": kind, "subject": subject,
            "weekday": weekday, "start": start, "end": end, "rows": rows,
        }
        add.clicked.connect(lambda: self._add_event_row(key))
        remove.clicked.connect(lambda: self._remove_event_row(key))
        self._refresh_event_subjects(key)
        return root

    def _build_routine_editor(self, key: str) -> QWidget:
        root = QWidget()
        root.setObjectName(f"field_{key}")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 4, 0, 0)
        form = QFormLayout()
        title = QLineEdit()
        title.setPlaceholderText("مثلاً ناهار، استراحت، رفت‌وآمد یا کار دلخواه")
        kind = QComboBox()
        for label, value in (("خواب", "sleep"), ("غذا", "meal"), ("استراحت", "rest"), ("بهداشت/حمام", "hygiene"), ("رفت‌وآمد", "commute"), ("سایر", "other")):
            kind.addItem(label, value)
        start = QTimeEdit()
        start.setDisplayFormat("HH:mm")
        start.setTime(QTime(12, 0))
        end = QTimeEdit()
        end.setDisplayFormat("HH:mm")
        end.setTime(QTime(12, 30))
        days = QListWidget()
        days.setMaximumHeight(105)
        for day in DAY_ORDER:
            item = QListWidgetItem(day)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            days.addItem(item)
        form.addRow("عنوان:", title)
        form.addRow("نوع بازه:", kind)
        form.addRow("شروع:", start)
        form.addRow("پایان:", end)
        form.addRow("روزهای تکرار (پیش‌فرض: هر روز):", days)
        layout.addLayout(form)
        actions = QHBoxLayout()
        add = QPushButton("افزودن بازهٔ ثابت")
        remove = QPushButton("حذف ردیف انتخاب‌شده از پیش‌نویس")
        actions.addWidget(add)
        actions.addWidget(remove)
        layout.addLayout(actions)
        rows = QListWidget()
        rows.setMinimumHeight(100)
        rows.setAccessibleName("روال‌های ثابت ثبت‌شده در این مرحله")
        layout.addWidget(rows)
        self._routine_editors[key] = {
            "title": title, "kind": kind, "start": start, "end": end,
            "days": days, "rows": rows,
        }
        add.clicked.connect(lambda: self._add_routine_row(key))
        remove.clicked.connect(lambda: self._remove_routine_row(key))
        return root

    def _refresh_event_subjects(self, key: str) -> None:
        editor = self._event_editors.get(key)
        if not editor:
            return
        combo = editor["subject"]
        current = combo.currentData()
        group = self._current_group()
        selected = sorted(self._selected_by_group.get(group, set()))
        values = selected or list(SUBJECTS_BY_GROUP.get(group, ()))
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("بدون درس", "")
        for name in values:
            combo.addItem(name, name)
        index = combo.findData(current)
        if index >= 0:
            combo.setCurrentIndex(index)
        combo.blockSignals(False)

    @staticmethod
    def _editor_time(widget: QTimeEdit) -> int:
        value = widget.time()
        return value.hour() * 60 + value.minute()

    @staticmethod
    def _clock_text(minutes: int) -> str:
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    def _add_event_row(self, key: str) -> None:
        editor = self._event_editors[key]
        start, end = self._editor_time(editor["start"]), self._editor_time(editor["end"])
        if end <= start:
            QMessageBox.warning(self, "زمان نامعتبر", "پایان جلسه باید بعد از شروع و در همان روز باشد.")
            return
        subject = str(editor["subject"].currentData() or "")
        title = editor["title"].text().strip() or subject
        if not title:
            QMessageBox.warning(self, "عنوان لازم است", "برای جلسه یا تعهد، عنوان وارد کنید.")
            return
        row = {
            "title": title,
            "kind": str(editor["kind"].currentData()),
            "subject": subject,
            "weekday": int(editor["weekday"].currentData()),
            "start": start,
            "end": end,
            "recorded": str(editor["kind"].currentData()) == "recorded_class",
        }
        self._append_event_row(key, row)
        editor["title"].clear()
        self._persist_event_rows(key)

    def _append_event_row(self, key: str, row: dict) -> None:
        editor = self._event_editors[key]
        day = DAY_ORDER[int(row.get("weekday", 0))]
        label = (f"{day} · {self._clock_text(int(row.get('start', 0)))}–"
                 f"{self._clock_text(int(row.get('end', 0)))} · {row.get('title', '')}")
        if row.get("subject"):
            label += f" · {row['subject']}"
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole, dict(row))
        editor["rows"].addItem(item)

    def _remove_event_row(self, key: str) -> None:
        editor = self._event_editors[key]
        row = editor["rows"].currentRow()
        if row >= 0:
            editor["rows"].takeItem(row)
            self._persist_event_rows(key)

    def _persist_event_rows(self, key: str) -> None:
        import json
        editor = self._event_editors[key]
        data = [editor["rows"].item(i).data(Qt.UserRole) for i in range(editor["rows"].count())]
        self.state.set_value(key, json.dumps(data, ensure_ascii=False))

    def _add_routine_row(self, key: str) -> None:
        editor = self._routine_editors[key]
        start, end = self._editor_time(editor["start"]), self._editor_time(editor["end"])
        if start == end:
            QMessageBox.warning(self, "زمان نامعتبر", "شروع و پایان بازه نمی‌توانند یکسان باشند.")
            return
        title = editor["title"].text().strip()
        if not title:
            QMessageBox.warning(self, "عنوان لازم است", "عنوان بازه را وارد کنید.")
            return
        weekdays = [i for i in range(7) if editor["days"].item(i).checkState() == Qt.Checked]
        if not weekdays:
            QMessageBox.warning(self, "روز تکرار لازم است", "حداقل یک روز هفته را انتخاب کنید.")
            return
        row = {
            "title": title, "kind": str(editor["kind"].currentData()),
            "start": start, "end": end, "weekdays": weekdays,
        }
        self._append_routine_row(key, row)
        editor["title"].clear()
        self._persist_routine_rows(key)

    def _append_routine_row(self, key: str, row: dict) -> None:
        editor = self._routine_editors[key]
        days = "، ".join(DAY_ORDER[int(day)] for day in row.get("weekdays", []))
        label = (f"{row.get('title', '')} · {self._clock_text(int(row.get('start', 0)))}–"
                 f"{self._clock_text(int(row.get('end', 0)))} · {days}")
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole, dict(row))
        editor["rows"].addItem(item)

    def _remove_routine_row(self, key: str) -> None:
        editor = self._routine_editors[key]
        row = editor["rows"].currentRow()
        if row >= 0:
            editor["rows"].takeItem(row)
            self._persist_routine_rows(key)

    def _persist_routine_rows(self, key: str) -> None:
        import json
        editor = self._routine_editors[key]
        data = [editor["rows"].item(i).data(Qt.UserRole) for i in range(editor["rows"].count())]
        self.state.set_value(key, json.dumps(data, ensure_ascii=False))

    def _load_structured_editors(self) -> None:
        import json
        for key, editor in self._event_editors.items():
            editor["rows"].clear()
            try:
                data = json.loads(self.state.values.get(key, "[]"))
            except (ValueError, TypeError):
                data = []
            for row in data if isinstance(data, list) else []:
                if isinstance(row, dict):
                    self._append_event_row(key, row)
            self._refresh_event_subjects(key)
        for key, editor in self._routine_editors.items():
            editor["rows"].clear()
            try:
                data = json.loads(self.state.values.get(key, "[]"))
            except (ValueError, TypeError):
                data = []
            for row in data if isinstance(data, list) else []:
                if isinstance(row, dict):
                    self._append_routine_row(key, row)

    def _set_books_selected(self, selected: bool) -> None:
        self.book_list.blockSignals(True)
        for index in range(self.book_list.count()):
            self.book_list.item(index).setCheckState(Qt.Checked if selected else Qt.Unchecked)
        self.book_list.blockSignals(False)
        self._collect_book_selection()

    def _remove_selected_book(self) -> None:
        row = self.book_list.currentRow()
        if row >= 0:
            item = self.book_list.item(row)
            entry = dict(item.data(Qt.UserRole) or {})
            if entry.get("is_catalog"):
                item.setCheckState(Qt.Unchecked)
            else:
                self.book_list.takeItem(row)
            self._collect_book_selection()

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
                # متون ذخیره‌شدهٔ نسخه‌های قدیمی (از جمله برنامهٔ نمایشی) را
                # در مرحلهٔ اختیاری برنامهٔ هفتگی دوباره نمایش نده.
                widget.setText(
                    step.description if step.kind == "schedule" else (value or "—")
                )
        self._loading_state = False
        self._refresh_subject_options()
        self._load_book_selections()
        self._sync_catalog_books()
        self._load_structured_editors()
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
        if year == 1406:
            notice.setText(
                "۱۴۰۶: متن کامل اطلاعیهٔ سازمان سنجش در باشگاه خبرنگاران جوان بازنشر شده؛ "
                "ضرایب مواد آزمون اختصاصی در کاتالوگ درج می‌شوند. نسخهٔ اولیهٔ سنجش و "
                "پیوست ضرایب عددیِ تک‌درسِ سوابق در این محیط مستقیماً واکشی نشده‌اند؛ "
                "سوابق تحصیلی از مواد آزمون تستی جداست."
            )
        elif year == 1405:
            notice.setText(
                "۱۴۰۵: ضرایب ۱۴۰۶ به این سال منتقل نمی‌شوند. برای ۱۴۰۵ در کاتالوگ "
                "دادهٔ کاملِ تأییدشده بارگذاری نشده است."
            )
        else:
            notice.setText("سال آزمون هنوز مشخص نیست؛ هیچ ضریب سال دیگری خودکار اعمال نمی‌شود.")
        notice.setToolTip(status)

    def _current_group(self) -> str:
        group = self.stack.widget(
            next(i for i, step in enumerate(ONBOARDING_STEPS) if step.key == "exam_group")
        ).findChild(QComboBox, "field_exam_group")
        return group.currentText() if group else ""

    def _current_year(self) -> Optional[int]:
        from ...jdate import normalize_digits
        step_index = next(i for i, step in enumerate(ONBOARDING_STEPS) if step.key == "exam_year")
        combo = self.stack.widget(step_index).findChild(QComboBox, "field_exam_year")
        digits = normalize_digits(combo.currentText()) if combo else ""
        return int(digits) if digits.isdigit() else None

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
            metadata = subject_metadata(group, subject)
            if metadata and metadata.exam_coefficient is not None:
                overlap = any(book.transcript_note for book in metadata.books)
                suffix = "؛ کتاب پایهٔ ۱۱ در سوابق هم هست" if overlap else ""
                label = f"{subject} — تخصصی آزمون اختصاصی · ضریب ۱۴۰۶: {metadata.exam_coefficient:g}{suffix}"
            elif metadata:
                label = f"{subject} — {metadata.course_type} · ضریب آزمون تستی ندارد؛ ضریب تک‌درس سوابق بارگذاری نشده"
            else:
                label = subject
            item = QListWidgetItem(label)
            item.setToolTip(metadata.note if metadata else "")
            item.setData(Qt.UserRole, subject)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if subject in selected else Qt.Unchecked)
            self.subject_list.addItem(item)
        self.subject_list.blockSignals(False)
        self._displayed_subject_group = group
        self._refresh_book_subject_options()
        for editor_key in self._event_editors:
            self._refresh_event_subjects(editor_key)
        self._sync_catalog_books()
        retained = [g for g, names in self._selected_by_group.items() if g != group and names]
        if retained:
            self.subject_selection_note.setText(
                "انتخاب‌های رشته‌های قبلی حفظ شده‌اند و حذف نشده‌اند: " + "، ".join(retained)
                + "؛ برای ویرایش، رشتهٔ مربوط را انتخاب کنید."
            )
        else:
            contribution = EXAM_WEIGHT_BY_GROUP.get(group) if self._current_year() == 1406 else None
            if contribution:
                exam_share, transcript_share = contribution
                share_text = (
                    f" سهم کل اعلام‌شده برای گروه {group}: آزمون اختصاصی {exam_share}٪، "
                    f"سوابق تحصیلی {transcript_share}٪ (اطلاعیهٔ بازنشرشده؛ منبع اولیهٔ "
                    "سنجش در این محیط مستقیم cross-check نشده)."
                )
            else:
                share_text = " سهم کل سال/گروه در این کاتالوگ رسمیِ تأییدشده نیست."
            self.subject_selection_note.setText(
                "مواد آزمون اختصاصی از متن بازنشرشدهٔ اطلاعیه ثبت شده‌اند؛ "
                "منبع و وضعیت بازبینی را در راهنما ببینید. ضریب تک‌درس آزمون، "
                "سهم کل کنکور/سوابق و وزن شخصی سه فیلد جدا هستند. " + share_text +
                " کتاب/فصل‌های تأییدنشده عمداً حدس زده نمی‌شوند."
            )

    def _subject_item_changed(self, _item) -> None:
        if not self._loading_state:
            self._collect_subject_selection()
            self._sync_catalog_books()
            for key in self._event_editors:
                self._refresh_event_subjects(key)

    def _set_current_subjects(self, selected: bool) -> None:
        self.subject_list.blockSignals(True)
        for index in range(self.subject_list.count()):
            self.subject_list.item(index).setCheckState(Qt.Checked if selected else Qt.Unchecked)
        self.subject_list.blockSignals(False)
        self._collect_subject_selection()
        self._sync_catalog_books()
        for key in self._event_editors:
            self._refresh_event_subjects(key)

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
                    "book_group": profile.group_name,
                }
                for b in self.service.repo.list_textbooks(profile.id)
            ]
        self.book_list.blockSignals(True)
        self.book_list.clear()
        for entry in entries:
            self._append_book_item(entry)
        self.book_list.blockSignals(False)
        self._refresh_book_subject_options()
        self._collect_book_selection()

    def _sync_catalog_books(self) -> None:
        if not hasattr(self, "book_list") or self._loading_state:
            return
        import json
        group = self._current_group()
        selected_names = set(self._selected_by_group.get(group, set()))
        try:
            entries = json.loads(self.state.values.get("books", "[]"))
            if not isinstance(entries, list):
                entries = []
        except (ValueError, TypeError):
            entries = []
        entries = [dict(item) for item in entries if isinstance(item, dict)]
        default_group = (
            self.service.active_exam_profile().group_name
            if self.service.active_exam_profile() else group
        )
        for entry in entries:
            if not entry.get("catalog_group") and not entry.get("book_group"):
                entry["book_group"] = default_group
        by_key = {item.get("catalog_key"): item for item in entries if item.get("catalog_key")}
        for entry in entries:
            if entry.get("is_catalog") and entry.get("catalog_group") == group:
                if entry.get("subject") not in selected_names:
                    entry["selected"] = False
        for book in catalog_books_for_selection(group, selected_names):
            key = f"{group}|{book.subject}|{book.code}|{book.title}"
            if key in by_key:
                continue
            entry = {
                "subject": book.subject,
                "title": book.title,
                "code": book.code,
                "grade": f"پایهٔ {book.grade}",
                "year": "۱۴۰۴–۱۴۰۵" if book.edition_year == 1405 else "",
                "edition_year": book.edition_year,
                "source": book.url,
                "status": book.status,
                "selected": True,
                "is_catalog": True,
                "catalog_group": group,
                "book_group": group,
                "catalog_key": key,
                "relation": book.relation,
                "transcript_note": book.transcript_note,
            }
            entries.append(entry)
            by_key[key] = entry
        self.state.set_value("books", json.dumps(entries, ensure_ascii=False))
        self.book_list.blockSignals(True)
        self.book_list.clear()
        visible_entries = [
            entry for entry in entries
            if entry.get("catalog_group", entry.get("book_group", group)) == group
        ]
        for entry in visible_entries:
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
        if entry.get("transcript_note"):
            label += " · سابقهٔ تحصیلی یازدهم"
        status = str(entry.get("status", "user_entered_unverified"))
        if status == "official_page_metadata_1404_1405":
            label += " · فرادادهٔ صفحهٔ رسمی، ۱۴۰۴–۱۴۰۵"
        elif status == "official_code_title_catalog_crosscheck_pending":
            label += " · پیوند به کاتالوگ رسمی؛ صفحه/ویرایش این ردیف نیازمند بازبینی"
        else:
            label += " · واردشده/تأییدنشده"
        item = QListWidgetItem(label)
        item.setToolTip(str(entry.get("relation", entry.get("source", ""))))
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
            "book_group": self._current_group(),
        }
        self.book_list.blockSignals(True)
        self._append_book_item(entry)
        self.book_list.blockSignals(False)
        self.book_title_edit.clear()
        self.book_code_edit.clear()
        self._collect_book_selection()

    @staticmethod
    def _book_entry_key(entry: dict) -> str:
        if entry.get("catalog_key"):
            return str(entry["catalog_key"])
        return "manual|" + "|".join(str(entry.get(key, "")) for key in (
            "book_group", "subject", "title", "code", "grade", "source"
        ))

    def _collect_book_selection(self, *_args) -> None:
        if not hasattr(self, "book_list") or self._book_editing:
            return
        self._book_editing = True
        import json
        try:
            stored = json.loads(self.state.values.get("books", "[]"))
            if not isinstance(stored, list):
                stored = []
        except (ValueError, TypeError):
            stored = []
        group = self._current_group()
        entries = [dict(row) for row in stored if isinstance(row, dict)]
        by_key = {self._book_entry_key(entry): entry for entry in entries}
        visible_rows: dict[str, dict] = {}
        for index in range(self.book_list.count()):
            item = self.book_list.item(index)
            entry = dict(item.data(Qt.UserRole) or {})
            entry["selected"] = item.checkState() == Qt.Checked
            entry.setdefault("book_group", group)
            visible_rows[self._book_entry_key(entry)] = entry
        # Keep historical selections for other tracks; a removed row in the
        # current draft is only deselected, never erased from stored records.
        for key, old in by_key.items():
            if old.get("catalog_group", old.get("book_group", group)) != group:
                continue
            if key not in visible_rows:
                old["selected"] = False
        for key, entry in visible_rows.items():
            if key in by_key:
                by_key[key].update(entry)
            else:
                entries.append(entry)
                by_key[key] = entry
        self.state.set_value("books", json.dumps(entries, ensure_ascii=False))
        self._book_editing = False

    def _collect(self) -> None:
        self._collect_subject_selection()
        self._collect_book_selection()
        for key in self._event_editors:
            self._persist_event_rows(key)
        for key in self._routine_editors:
            self._persist_routine_rows(key)
        for step in ONBOARDING_STEPS:
            widget = self.stack.widget(ONBOARDING_STEPS.index(step)).findChild(
                QWidget, f"field_{step.key}"
            )
            if widget is None:
                continue
            if isinstance(widget, QComboBox):
                self.state.set_value(step.key, str(widget.currentData() or ""))
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
        if ONBOARDING_STEPS[index].key == "classes" and self.state.values.get("class_attendance") == "خیر":
            index += 1
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
        if step.key == "sleep_time" and parse_clock_pair(self.state.values.get("sleep_time", "")) is None:
            QMessageBox.warning(self, "بازهٔ خواب نامعتبر", "ساعت خواب و بیداری را به قالب ۲۳:۰۰ تا ۰۶:۰۰ وارد کنید.")
            return
        if step.key == "exam_date" and self.state.values.get("exam_date", ""):
            try:
                from ...jdate import parse_jalali_date
                parse_jalali_date(self.state.values.get("exam_date", ""))
            except ValueError as exc:
                QMessageBox.warning(self, "تاریخ نامعتبر", str(exc))
                return
        if step.key == "subjects":
            selected = self._selected_by_group.get(self._current_group(), set())
            if not selected:
                QMessageBox.warning(self, "انتخاب درس لازم است", "حداقل یک درس یا دستهٔ سوابق را انتخاب کنید.")
                return
        if step.key == "classes" and self.state.values.get("class_attendance") == "بله":
            if not self._event_editors["classes"]["rows"].count():
                QMessageBox.warning(self, "ثبت کلاس لازم است", "گفتید کلاس مؤسسه دارید؛ دست‌کم یک جلسه را با روز و ساعت وارد کنید.")
                return
        self.state.complete_step(step.key)
        if step.key == "class_attendance" and self.state.values.get("class_attendance") == "خیر":
            self.state.current_index += 1
        self._save_state()
        if self.state.current_index < len(ONBOARDING_STEPS) - 1:
            # complete_step خودش current_index را به گام بعد می‌برد.
            self._goto(self.state.current_index)
        else:
            self._finish()

    def _prev(self) -> None:
        self._collect()
        self._save_state()
        self._goto(self.state.current_index - 1)

    def _skip_step(self) -> None:
        """گام اختیاری بدون پاسخ رد می‌شود؛ راه‌اندازی متوقف نمی‌شود."""
        step = ONBOARDING_STEPS[self.state.current_index]
        if step.required:
            QMessageBox.information(
                self, "گام الزامی", f"«{step.title}» الزامی است و نمی‌تواند رد شود."
            )
            return
        self.state.values.pop(step.key, None)
        self.state.completed_steps.discard(step.key)
        self.state.complete_step(step.key)
        self._save_state()
        if self.state.current_index < len(ONBOARDING_STEPS) - 1:
            self._goto(self.state.current_index)
        else:
            self._finish()

    def _refresh_nav(self) -> None:
        last = len(ONBOARDING_STEPS) - 1
        self.btn_prev.setEnabled(self.state.current_index > 0)
        self.btn_next.setEnabled(self.state.current_index < last)
        self.btn_finish.setEnabled(self.state.current_index == last)
        step = ONBOARDING_STEPS[self.state.current_index]
        self.btn_skip.setVisible(not step.required)

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

    def _save_and_close(self) -> None:
        self._collect()
        self._save_state()
        self.accept()

    def _pending_events(self) -> list[FixedEvent]:
        pending: list[FixedEvent] = []
        subject_ids = {
            subject.name: subject.id
            for subject in self.service.repo.list_subjects(
                self.service.active_exam_profile().id, include_unselected=True
            )
        } if self.service.active_exam_profile() else {}
        for key in ("classes", "weekly_schedule"):
            if key == "classes" and self.state.values.get("class_attendance") == "خیر":
                continue
            editor = self._event_editors.get(key)
            if not editor:
                continue
            for index in range(editor["rows"].count()):
                row = editor["rows"].item(index).data(Qt.UserRole) or {}
                try:
                    kind = FixedEventKind(str(row.get("kind", "commitment")))
                except ValueError:
                    kind = FixedEventKind.COMMITMENT
                pending.append(FixedEvent(
                    title=str(row.get("title", "")), kind=kind,
                    subject_id=subject_ids.get(str(row.get("subject", ""))),
                    weekday=int(row.get("weekday", 0)),
                    start_minute=int(row.get("start", 0)),
                    end_minute=int(row.get("end", 0)),
                    is_recorded=bool(row.get("recorded", False)),
                ))
        return pending

    def _finish(self) -> None:
        self._collect()
        required_keys = [step.key for step in ONBOARDING_STEPS if step.required and step.key != "confirm"]
        missing = [key for key in required_keys if not self.state.values.get(key)]
        if not self._selected_by_group.get(self._current_group(), set()):
            missing.append("subjects")
        if missing:
            labels = {step.key: step.title for step in ONBOARDING_STEPS}
            QMessageBox.warning(
                self, "راه‌اندازی ناقص است",
                "این موارد را کامل کنید: " + "، ".join(labels.get(key, key) for key in dict.fromkeys(missing)),
            )
            return
        if parse_clock_pair(self.state.values.get("sleep_time", "")) is None:
            QMessageBox.warning(self, "بازهٔ خواب نامعتبر", "ساعت خواب و بیداری را به قالب ۲۳:۰۰ تا ۰۶:۰۰ وارد کنید.")
            return
        if self.state.values.get("class_attendance") == "بله" and not self._event_editors["classes"]["rows"].count():
            QMessageBox.warning(self, "ثبت کلاس لازم است", "گفتید کلاس مؤسسه دارید؛ دست‌کم یک جلسه وارد کنید.")
            return
        existing_events = self.service.repo.list_fixed_events()
        pending_events = self._pending_events()
        conflicts = self.service.schedule_conflicts() + __import__(
            "k2.onboarding", fromlist=["detect_event_conflicts"]
        ).detect_event_conflicts(pending_events)
        if not conflicts:
            conflicts = __import__("k2.onboarding", fromlist=["detect_event_conflicts"]).detect_event_conflicts(
                existing_events + pending_events
            )
        if conflicts:
            QMessageBox.warning(
                self, "تعارض برنامه حل نشده است",
                "پیش از پایان راه‌اندازی، تعارض رویدادهای زنده را در تنظیمات "
                "ویرایش یا یکی را ضبط‌شده علامت بزنید:\n\n"
                + "\n".join(c.describe() for c in conflicts),
            )
            return
        if self.state.values.get("exam_date_status") == "رسمی (منبع ثبت‌شده)":
            source = self.state.values.get("exam_source", "")
            if not is_official_exam_source_url(source):
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
        # حداقل خواب مورد نظر: خواب قربانی جبران عقب‌افتادگی نمی‌شود.
        min_sleep_text = values.get("min_sleep", "")
        digits_min_sleep = __import__("k2.jdate", fromlist=["normalize_digits"]).normalize_digits(
            min_sleep_text
        )
        if digits_min_sleep.isdigit():
            self.service.repo.set_setting("daily.sleep_target_minutes", digits_min_sleep)

        # برآورد زمان هر نوع کار؛ فرضیهٔ محافظه‌کارانه و قابل کالیبراسیون.
        raw_durations = values.get("typical_durations", "")
        if raw_durations:
            parts = [x for x in raw_durations.replace("،", ",").split(",") if x.strip()]
            if len(parts) >= 4:
                normalized = [
                    __import__("k2.jdate", fromlist=["normalize_digits"]).normalize_digits(x).strip()
                    for x in parts[:4]
                ]
                if all(x.isdigit() for x in normalized):
                    self.service.repo.set_setting(
                        "estimate.defaults",
                        json.dumps({
                            "testing": int(normalized[0]),
                            "analysis": int(normalized[1]),
                            "consolidation": int(normalized[2]),
                            "homework": int(normalized[3]),
                        }),
                    )

        self.service.repo.set_setting(
            "priority.use_exam_coefficients",
            "1" if values.get("priority_mode") == "خودکار با توجه به ضریب آزمون" else "0",
        )

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
            metadata = subject_metadata(profile.group_name, subject.name)
            if metadata and profile.exam_year == 1406:
                subject.exam_coefficient = metadata.exam_coefficient
                subject.exam_coefficient_status = metadata.coefficient_status
                subject.exam_coefficient_source = metadata.coefficient_source
                subject.academic_coefficient = None
                subject.academic_coefficient_status = "numeric_transcript_coefficients_not_loaded"
                subject.academic_coefficient_source = SOURCE_SANJESH_1406.url
            elif subject.exam_coefficient_status == "official_notice_republished":
                # ضرایب آزمون ۱۴۰۶ را به سال دیگر منتقل نکن.
                subject.exam_coefficient = None
                subject.exam_coefficient_status = "year_dataset_not_loaded"
                subject.exam_coefficient_source = ""
            self.service.repo.update_subject(subject)
        for name in selected_names:
            if name not in existing:
                metadata = subject_metadata(profile.group_name, name)
                is_current_1406 = bool(metadata and profile.exam_year == 1406)
                self.service.repo.create_subject(Subject(
                    name=name,
                    exam_profile_id=profile.id,
                    is_selected=True,
                    exam_coefficient=metadata.exam_coefficient if is_current_1406 else None,
                    exam_coefficient_status=metadata.coefficient_status if is_current_1406 else "year_dataset_not_loaded",
                    exam_coefficient_source=metadata.coefficient_source if is_current_1406 else "",
                    academic_coefficient=None,
                    academic_coefficient_status=(
                        "numeric_transcript_coefficients_not_loaded" if metadata else "unknown"
                    ),
                    academic_coefficient_source=SOURCE_SANJESH_1406.url if metadata and profile.exam_year == 1406 else "",
                ))

        # ردیف کتاب‌های کاتالوگ/دستی هر دو با وضعیت منبع خود ذخیره می‌شوند.
        # هیچ رکوردی حذف نمی‌شود؛ انتخاب کاربر فقط پرچم is_selected را تغییر می‌دهد.
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
            year_digits = __import__("re").search(r"14\d{2}", year_text)
            edition_year = entry.get("edition_year")
            if not isinstance(edition_year, int):
                edition_year = int(year_digits.group(0)) if year_digits else None
            book = Textbook(
                exam_profile_id=profile.id,
                subject_id=subject_by_name.get(str(entry.get("subject", ""))).id
                if str(entry.get("subject", "")) in subject_by_name else None,
                title=str(entry.get("title", "")).strip(),
                book_code=str(entry.get("code", "")).strip(),
                grade=str(entry.get("grade", "")).strip(),
                edition_year=edition_year,
                source_url=str(entry.get("source", "")).strip(),
                source_status=str(entry.get("status", "user_entered_unverified")),
                is_selected=bool(entry.get("selected", True)),
            )
            self.service.repo.save_textbook_selection(book)
        # رویدادهای کلاس و تعهدهای کاربر؛ دادهٔ موجود حذف/جایگزین نمی‌شود.
        known_events = self.service.repo.list_fixed_events()
        event_signatures = {
            (e.title, e.kind.value, e.subject_id, e.weekday, e.start_minute, e.end_minute, e.is_recorded)
            for e in known_events
        }
        for key in ("classes", "weekly_schedule"):
            if key == "classes" and values.get("class_attendance") == "خیر":
                continue
            try:
                rows = json.loads(values.get(key, "[]"))
            except (ValueError, TypeError):
                rows = []
            for row in rows if isinstance(rows, list) else []:
                if not isinstance(row, dict):
                    continue
                try:
                    kind = FixedEventKind(str(row.get("kind", "commitment")))
                    weekday = int(row.get("weekday", 0))
                    start, end = int(row.get("start", 0)), int(row.get("end", 0))
                except (ValueError, TypeError):
                    continue
                subject_id = subject_by_name.get(str(row.get("subject", "")))
                signature = (str(row.get("title", "")).strip(), kind.value,
                             subject_id.id if subject_id else None, weekday, start, end,
                             bool(row.get("recorded", False)))
                if signature in event_signatures:
                    continue
                event = FixedEvent(
                    title=signature[0], kind=kind,
                    subject_id=signature[2], weekday=weekday,
                    start_minute=start, end_minute=end,
                    is_recorded=signature[6],
                )
                self.service.create_fixed_event(event)
                event_signatures.add(signature)

        # خوابِ واردشده، تنظیمِ بیداری/خواب و بازهٔ محافظت‌شده را هم‌راستا می‌کند.
        sleep_pair = parse_clock_pair(values.get("sleep_time", ""))
        if sleep_pair:
            sleep_start, wake_time = sleep_pair
            self.service.wake_minute = wake_time
            self.service.sleep_minute = sleep_start
            routine = Routine(
                title="خواب شب",
                kind=RoutineKind.SLEEP,
                start_minute=sleep_start,
                end_minute=wake_time,
                weekdays=frozenset(range(7)),
                scope=RoutineScope.DAILY,
            )
            managed_id = self.service.repo.get_setting("onboarding.sleep_routine_id")
            managed = next((r for r in self.service.repo.list_routines()
                            if managed_id and str(r.id) == managed_id), None)
            if managed is not None:
                routine.id = managed.id
                self.service.update_routine(routine)
            else:
                routine.id = self.service.create_routine(routine)
                self.service.repo.set_setting("onboarding.sleep_routine_id", str(routine.id))

        try:
            routine_rows = json.loads(values.get("routines", "[]"))
        except (ValueError, TypeError):
            routine_rows = []
        known_routines = self.service.repo.list_routines()
        routine_signatures = {
            (r.title, r.kind.value, r.start_minute, r.end_minute, tuple(sorted(r.weekdays)))
            for r in known_routines
        }
        for row in routine_rows if isinstance(routine_rows, list) else []:
            if not isinstance(row, dict):
                continue
            try:
                kind = RoutineKind(str(row.get("kind", "other")))
                start, end = int(row.get("start", 0)), int(row.get("end", 0))
                weekdays = frozenset(int(day) for day in row.get("weekdays", []))
            except (ValueError, TypeError):
                continue
            signature = (str(row.get("title", "")).strip(), kind.value, start, end, tuple(sorted(weekdays)))
            if not signature[0] or not weekdays or start == end or signature in routine_signatures:
                continue
            self.service.create_routine(Routine(
                title=signature[0], kind=kind, start_minute=start, end_minute=end,
                weekdays=weekdays, scope=RoutineScope.DAILY,
            ))
            routine_signatures.add(signature)
        self.service.conn.commit()
