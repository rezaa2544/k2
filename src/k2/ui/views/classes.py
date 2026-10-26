"""نمای «کلاس‌های من»: رویدادهای ثابت هفتگی و روال‌های ضروری (بند ۱۷)."""

from __future__ import annotations

import datetime as _dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from ...domain.enums import FixedEventKind, RoutineKind, RoutineScope
from ...domain.models import FixedEvent, Routine
from ...jdate import (
    WEEKDAY_NAMES,
    clock_to_minutes,
    format_clock,
    minutes_to_clock,
)
from ...service import AdvisorService
from ..widgets import Card, info_box, notify

WEEKDAYS = [
    (0, "شنبه"), (1, "یک‌شنبه"), (2, "دوشنبه"), (3, "سه‌شنبه"),
    (4, "چهارشنبه"), (5, "پنج‌شنبه"), (6, "جمعه"),
]

EVENT_KINDS = [
    (FixedEventKind.LIVE_CLASS, "کلاس حضوری"),
    (FixedEventKind.ONLINE_CLASS, "کلاس آنلاین زنده"),
    (FixedEventKind.RECORDED_CLASS, "کلاس ضبط‌شده"),
    (FixedEventKind.EXAM, "آزمون"),
    (FixedEventKind.COMMITMENT, "تعهد شخصی"),
]

ROUTINE_KINDS = [
    (RoutineKind.SLEEP, "خواب"),
    (RoutineKind.MEAL, "غذا"),
    (RoutineKind.REST, "استراحت"),
    (RoutineKind.HYGIENE, "بهداشت/حمام"),
    (RoutineKind.COMMUTE, "رفت‌وآمد"),
    (RoutineKind.OTHER, "سایر"),
]

ROUTINE_SCOPES = [
    (RoutineScope.DAILY, "روزانه"),
    (RoutineScope.ALTERNATE, "یک‌روزدرمیان"),
]


class FixedEventDialog(QDialog):
    """ثبت یا ویرایش یک رویداد ثابت هفتگی."""

    def __init__(
        self,
        service: AdvisorService,
        event_item: FixedEvent | None = None,
        parent: QWidget | None = None,
    ):
        # نکتهٔ فنی: نام ویژگی نباید ``event`` باشد؛ ``QObject.event`` یک متد
        # مجازی Qt است و بازنویسی آن باعث سقوط فرآیند می‌شود.
        super().__init__(parent)
        self.service = service
        self.event_item = event_item
        self.setWindowTitle(
            "ثبت کلاس" if event_item is None else "ویرایش کلاس"
        )
        self.setLayoutDirection(Qt.RightToLeft)
        # حداقل پهنا برای اینکه برچسب‌های فارسی و فهرست‌های کشویی بریده نشوند.
        self.setMinimumWidth(580)
        form = QFormLayout(self)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("عنوان کار یا روال شخصی")
        form.addRow("عنوان:", self.title_edit)

        self.kind_combo = QComboBox()
        for kind, label in EVENT_KINDS:
            self.kind_combo.addItem(label, kind.value)
        form.addRow("نوع:", self.kind_combo)

        self.subject_combo = QComboBox()
        self.subject_combo.addItem("— بدون درس —", None)
        for subject in service.repo.list_subjects(include_unselected=True):
            self.subject_combo.addItem(subject.name, subject.id)
        form.addRow("درس:", self.subject_combo)

        self.weekday_combo = QComboBox()
        for value, label in WEEKDAYS:
            self.weekday_combo.addItem(label, value)
        form.addRow("روز هفته:", self.weekday_combo)

        self.start_edit = QTimeEdit()
        self.start_edit.setDisplayFormat("HH:mm")
        self.end_edit = QTimeEdit()
        self.end_edit.setDisplayFormat("HH:mm")
        form.addRow("شروع:", self.start_edit)
        form.addRow("پایان:", self.end_edit)

        self.recorded_check = QCheckBox("کلاس ضبط‌شده است (قابل تقسیم با نقطهٔ توقف)")
        form.addRow("", self.recorded_check)

        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("یادداشت اختیاری")
        form.addRow("یادداشت:", self.notes_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("ذخیره")
        buttons.button(QDialogButtonBox.Cancel).setText("انصراف")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        if event_item is not None:
            self.title_edit.setText(event_item.title)
            index = self.kind_combo.findData(event_item.kind)
            if index >= 0:
                self.kind_combo.setCurrentIndex(index)
            index = self.subject_combo.findData(event_item.subject_id)
            if index >= 0:
                self.subject_combo.setCurrentIndex(index)
            index = self.weekday_combo.findData(event_item.weekday)
            if index >= 0:
                self.weekday_combo.setCurrentIndex(index)
            hour, minute = minutes_to_clock(event_item.start_minute)
            self.start_edit.setTime(_dt.time(hour, minute))
            hour, minute = minutes_to_clock(event_item.end_minute)
            self.end_edit.setTime(_dt.time(hour, minute))
            self.recorded_check.setChecked(event_item.is_recorded)
            self.notes_edit.setText(event_item.notes)

    def _accept(self) -> None:
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "عنوان لازم است", "عنوان رویداد را وارد کن.")
            return
        start = self.start_edit.time()
        end = self.end_edit.time()
        start_minute = clock_to_minutes(start.hour(), start.minute())
        end_minute = clock_to_minutes(end.hour(), end.minute())
        if end_minute <= start_minute:
            QMessageBox.warning(
                self, "بازهٔ نامعتبر", "زمان پایان باید بعد از شروع باشد."
            )
            return
        self.result_event = FixedEvent(
            id=self.event_item.id if self.event_item else None,
            title=title,
            kind=FixedEventKind(self.kind_combo.currentData()),
            subject_id=self.subject_combo.currentData(),
            weekday=int(self.weekday_combo.currentData()),
            start_minute=start_minute,
            end_minute=end_minute,
            is_recorded=self.recorded_check.isChecked(),
            notes=self.notes_edit.text().strip(),
        )
        self.accept()


class RoutineDialog(QDialog):
    """ثبت یا ویرایش یک بازهٔ ضروری روزانه."""

    def __init__(
        self, service: AdvisorService, routine: Routine | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.service = service
        self.routine = routine
        self.setWindowTitle("ثبت روال ضروری" if routine is None else "ویرایش روال")
        self.setLayoutDirection(Qt.RightToLeft)
        # حداقل پهنا برای اینکه برچسب‌های فارسی و فهرست‌های کشویی بریده نشوند.
        self.setMinimumWidth(560)
        form = QFormLayout(self)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("مثلاً ناهار، استراحت…")
        form.addRow("عنوان:", self.title_edit)

        self.kind_combo = QComboBox()
        for kind, label in ROUTINE_KINDS:
            self.kind_combo.addItem(label, kind.value)
        form.addRow("نوع:", self.kind_combo)

        self.scope_combo = QComboBox()
        for scope, label in ROUTINE_SCOPES:
            self.scope_combo.addItem(label, scope.value)
        form.addRow("تناوب:", self.scope_combo)

        self.start_edit = QTimeEdit()
        self.start_edit.setDisplayFormat("HH:mm")
        self.start_edit.setTime(_dt.time(7, 0))
        self.end_edit = QTimeEdit()
        self.end_edit.setDisplayFormat("HH:mm")
        self.end_edit.setTime(_dt.time(7, 30))
        form.addRow("شروع:", self.start_edit)
        form.addRow("پایان:", self.end_edit)

        self.weekday_combo = QComboBox()
        for value, label in WEEKDAYS:
            self.weekday_combo.addItem(label, value)
        form.addRow("از روز:", self.weekday_combo)

        self.study_check = QCheckBox("این بازه مطالعه حساب شود")
        form.addRow("", self.study_check)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("ذخیره")
        buttons.button(QDialogButtonBox.Cancel).setText("انصراف")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        if routine is not None:
            self.title_edit.setText(routine.title)
            index = self.kind_combo.findData(routine.kind)
            if index >= 0:
                self.kind_combo.setCurrentIndex(index)
            index = self.scope_combo.findData(routine.scope)
            if index >= 0:
                self.scope_combo.setCurrentIndex(index)
            hour, minute = minutes_to_clock(routine.start_minute)
            self.start_edit.setTime(_dt.time(hour, minute))
            hour, minute = minutes_to_clock(routine.end_minute)
            self.end_edit.setTime(_dt.time(hour, minute))
            days = sorted(routine.weekdays) or [0]
            index = self.weekday_combo.findData(days[0])
            if index >= 0:
                self.weekday_combo.setCurrentIndex(index)
            self.study_check.setChecked(routine.counts_as_study)

    def _accept(self) -> None:
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "عنوان لازم است", "عنوان روال را وارد کن.")
            return
        start = self.start_edit.time()
        end = self.end_edit.time()
        start_minute = clock_to_minutes(start.hour(), start.minute())
        end_minute = clock_to_minutes(end.hour(), end.minute())
        if end_minute <= start_minute:
            QMessageBox.warning(
                self, "بازهٔ نامعتبر", "زمان پایان باید بعد از شروع باشد."
            )
            return
        weekday = int(self.weekday_combo.currentData())
        scope = self.scope_combo.currentData()
        if scope == RoutineScope.ALTERNATE:
            weekdays = frozenset({weekday})
        else:
            weekdays = frozenset(range(7))
        self.result_routine = Routine(
            id=self.routine.id if self.routine else None,
            title=title,
            kind=RoutineKind(self.kind_combo.currentData()),
            start_minute=start_minute,
            end_minute=end_minute,
            weekdays=weekdays,
            scope=RoutineScope(scope),
            counts_as_study=self.study_check.isChecked(),
        )
        self.accept()


class ClassesPage(QWidget):
    """کلاس‌ها و روال‌های ثابت — ورودی ظرفیت واقعی برنامه."""

    def __init__(self, service: AdvisorService, parent: QWidget | None = None):
        super().__init__(parent)
        self.service = service
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("کلاس‌های من")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        btn_event = QPushButton("ثبت کلاس/تعهد")
        btn_event.setObjectName("primary")
        btn_event.clicked.connect(self._add_event)
        header.addWidget(btn_event)
        btn_routine = QPushButton("ثبت روال ضروری")
        btn_routine.clicked.connect(self._add_routine)
        header.addWidget(btn_routine)
        root.addLayout(header)

        self.summary = QLabel("—")
        self.summary.setObjectName("muted")
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)

        self.conflicts = info_box()
        self.conflicts.setVisible(False)
        root.addWidget(self.conflicts)

        splitter = QHBoxLayout()
        events_card = Card("رویدادهای ثابت هفتگی", tone="class")
        self.event_table = QTableWidget(0, 6)
        self.event_table.setHorizontalHeaderLabels(
            ["عنوان", "نوع", "روز", "ساعت", "ضبط‌شده", "درس"]
        )
        self.event_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.event_table.verticalHeader().setVisible(False)
        self.event_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.event_table.setSelectionBehavior(QTableWidget.SelectRows)
        events_card.add(self.event_table)
        splitter.addWidget(events_card, 3)

        routines_card = Card("روال‌های ضروری روزانه", tone="class")
        self.routine_table = QTableWidget(0, 4)
        self.routine_table.setHorizontalHeaderLabels(
            ["عنوان", "نوع", "ساعت", "تناوب"]
        )
        self.routine_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.routine_table.verticalHeader().setVisible(False)
        self.routine_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.routine_table.setSelectionBehavior(QTableWidget.SelectRows)
        routines_card.add(self.routine_table)
        splitter.addWidget(routines_card, 2)
        root.addLayout(splitter, 1)

        buttons = QHBoxLayout()
        self.btn_edit_event = QPushButton("ویرایش رویداد")
        self.btn_edit_event.clicked.connect(self._edit_event)
        buttons.addWidget(self.btn_edit_event)
        self.btn_delete_event = QPushButton("حذف رویداد")
        self.btn_delete_event.clicked.connect(self._delete_event)
        buttons.addWidget(self.btn_delete_event)
        self.btn_edit_routine = QPushButton("ویرایش روال")
        self.btn_edit_routine.clicked.connect(self._edit_routine)
        buttons.addWidget(self.btn_edit_routine)
        self.btn_delete_routine = QPushButton("حذف روال")
        self.btn_delete_routine.clicked.connect(self._delete_routine)
        buttons.addWidget(self.btn_delete_routine)
        buttons.addStretch(1)
        root.addLayout(buttons)

        self.info = info_box()
        self.info.setText(
            "کلاس‌ها و تعهدهای ثابت هرگز جابه‌جا نمی‌شوند؛ برنامه فقط فضای "
            "باقی‌مانده را پر می‌کند. زمان کلاس جدا از مطالعهٔ مستقل گزارش "
            "می‌شود تا ساعت درس، ساعت مطالعهٔ شخصی‌ات را پنهان نکند."
        )
        root.addWidget(self.info)

    def refresh(self) -> None:
        events = self.service.repo.list_fixed_events()
        routines = self.service.repo.list_routines()
        self.event_table.setRowCount(0)
        for event in events:
            row = self.event_table.rowCount()
            self.event_table.insertRow(row)
            id_item = QTableWidgetItem(event.title)
            id_item.setData(Qt.UserRole, event.id)
            self.event_table.setItem(row, 0, id_item)
            self.event_table.setItem(row, 1, QTableWidgetItem(event.kind.label))
            self.event_table.setItem(
                row, 2, QTableWidgetItem(
                    WEEKDAY_NAMES[event.weekday % 7]
                )
            )
            self.event_table.setItem(
                row, 3,
                QTableWidgetItem(
                    f"{format_clock(event.start_minute)}–{format_clock(event.end_minute)}"
                ),
            )
            self.event_table.setItem(
                row, 4, QTableWidgetItem("بله" if event.is_recorded else "خیر")
            )
            self.event_table.setItem(row, 5, QTableWidgetItem(event.subject_name or "—"))

        self.routine_table.setRowCount(0)
        for routine in routines:
            row = self.routine_table.rowCount()
            self.routine_table.insertRow(row)
            id_item = QTableWidgetItem(routine.title)
            id_item.setData(Qt.UserRole, routine.id)
            self.routine_table.setItem(row, 0, id_item)
            self.routine_table.setItem(row, 1, QTableWidgetItem(routine.kind.label))
            self.routine_table.setItem(
                row, 2,
                QTableWidgetItem(
                    f"{format_clock(routine.start_minute)}–{format_clock(routine.end_minute)}"
                ),
            )
            self.routine_table.setItem(row, 3, QTableWidgetItem(routine.scope.label))

        total_class = sum(
            e.end_minute - e.start_minute for e in events
        )
        total_routine = sum(
            r.end_minute - r.start_minute for r in routines
        )
        self.summary.setText(
            f"{len(events)} رویداد ثابت ({format_minutes_text(total_class)} در هفته) — "
            f"{len(routines)} روال ضروری ({format_minutes_text(total_routine)} در روز)"
        )
        conflicts = self.service.schedule_conflicts()
        self.conflicts.setVisible(bool(conflicts))
        if conflicts:
            self.conflicts.setText(
                "تعارض‌های زمان:\n"
                + "\n".join(item.describe() for item in conflicts[:5])
            )

    # ---- کنش‌ها ----

    def _selected_event_id(self) -> int | None:
        row = self.event_table.currentRow()
        if row < 0:
            return None
        item = self.event_table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _selected_routine_id(self) -> int | None:
        row = self.routine_table.currentRow()
        if row < 0:
            return None
        item = self.routine_table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _add_event(self) -> None:
        dialog = FixedEventDialog(self.service, None, self)
        if dialog.exec() != QDialog.Accepted:
            return
        event = getattr(dialog, "result_event", None)
        if event is None:
            return
        try:
            self.service.create_fixed_event(event)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "ذخیره نشد", str(exc))
            return
        self.refresh()

    def _edit_event(self) -> None:
        event_id = self._selected_event_id()
        if event_id is None:
            notify(self, "انتخاب نشده", "اول یک رویداد را انتخاب کن.")
            return
        event = next(
            (e for e in self.service.repo.list_fixed_events() if e.id == event_id),
            None,
        )
        if event is None:
            return
        dialog = FixedEventDialog(self.service, event, self)
        if dialog.exec() != QDialog.Accepted:
            return
        updated = getattr(dialog, "result_event", None)
        if updated is None:
            return
        try:
            self.service.update_fixed_event(updated)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "ذخیره نشد", str(exc))
            return
        self.refresh()

    def _delete_event(self) -> None:
        event_id = self._selected_event_id()
        if event_id is None:
            notify(self, "انتخاب نشده", "اول یک رویداد را انتخاب کن.")
            return
        try:
            self.service.delete_fixed_event(event_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "حذف نشد", str(exc))
            return
        self.refresh()

    def _add_routine(self) -> None:
        dialog = RoutineDialog(self.service, None, self)
        if dialog.exec() != QDialog.Accepted:
            return
        routine = getattr(dialog, "result_routine", None)
        if routine is None:
            return
        try:
            self.service.create_routine(routine)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "ذخیره نشد", str(exc))
            return
        self.refresh()

    def _edit_routine(self) -> None:
        routine_id = self._selected_routine_id()
        if routine_id is None:
            notify(self, "انتخاب نشده", "اول یک روال را انتخاب کن.")
            return
        routine = next(
            (r for r in self.service.repo.list_routines() if r.id == routine_id),
            None,
        )
        if routine is None:
            return
        dialog = RoutineDialog(self.service, routine, self)
        if dialog.exec() != QDialog.Accepted:
            return
        updated = getattr(dialog, "result_routine", None)
        if updated is None:
            return
        try:
            self.service.update_routine(updated)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "ذخیره نشد", str(exc))
            return
        self.refresh()

    def _delete_routine(self) -> None:
        routine_id = self._selected_routine_id()
        if routine_id is None:
            notify(self, "انتخاب نشده", "اول یک روال را انتخاب کن.")
            return
        try:
            self.service.delete_routine(routine_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "حذف نشد", str(exc))
            return
        self.refresh()


def format_minutes_text(total: int) -> str:
    hours, minutes = divmod(max(0, int(total)), 60)
    if hours and minutes:
        return f"{hours} ساعت و {minutes} دقیقه"
    if hours:
        return f"{hours} ساعت"
    return f"{minutes} دقیقه"


__all__ = ["ClassesPage", "FixedEventDialog", "RoutineDialog"]
