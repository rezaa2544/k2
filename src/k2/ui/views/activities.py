"""نمای فعالیت‌ها: ثبت، شروع، اتمام، تعویق و حذف با ثبت دلیل."""

from __future__ import annotations

import datetime as _dt

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
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
    QVBoxLayout,
    QWidget,
)

from ...domain.enums import (
    ActivityType,
    DeadlineType,
    EnergyNeed,
)
from ...domain.models import Activity
from ...jdate import format_minutes
from ...service import AdvisorService
from ..widgets import Card, confirm, info_box, notify


class AddActivityDialog(QDialog):
    """افزودن فعالیت تازه."""

    def __init__(self, service: AdvisorService, parent: QWidget | None = None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("افزودن فعالیت")
        self.setLayoutDirection(Qt.RightToLeft)

        form = QFormLayout(self)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("مثلاً پردازش اولیهٔ کلاس زیست")
        form.addRow("عنوان:", self.title_edit)

        self.type_combo = QComboBox()
        for activity_type in ActivityType:
            self.type_combo.addItem(activity_type.label, activity_type.value)
        form.addRow("نوع:", self.type_combo)

        self.subject_combo = QComboBox()
        for subject in service.repo.list_subjects():
            self.subject_combo.addItem(subject.name, subject.id)
        form.addRow("درس:", self.subject_combo)

        self.est_spin = QSpinBox()
        self.est_spin.setRange(5, 600)
        self.est_spin.setValue(45)
        self.est_spin.setSuffix(" دقیقه")
        form.addRow("زمان برآوردی:", self.est_spin)

        self.deadline_combo = QComboBox()
        for deadline_type in DeadlineType:
            self.deadline_combo.addItem(deadline_type.label, deadline_type.value)
        form.addRow("نوع مهلت:", self.deadline_combo)

        self.deadline_date = QLineEdit()
        self.deadline_date.setPlaceholderText("۱۴۰۵/۰۷/۲۴ (اختیاری)")
        form.addRow("تاریخ مهلت:", self.deadline_date)

        self.energy_combo = QComboBox()
        for energy in EnergyNeed:
            self.energy_combo.addItem(energy.label, energy.value)
        form.addRow("انرژی لازم:", self.energy_combo)

        self.splittable_check = QPushButton("تقسیم‌پذیر: بله")
        self.splittable_check.setCheckable(True)
        self.splittable_check.setChecked(True)
        form.addRow("تقسیم‌پذیری:", self.splittable_check)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal
        )
        buttons.button(QDialogButtonBox.Ok).setText("افزودن")
        buttons.button(QDialogButtonBox.Cancel).setText("انصراف")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _accept(self) -> None:
        from ...jdate import parse_jalali_date

        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "ورودی ناقص", "عنوان فعالیت را وارد کنید.")
            return

        deadline_at = None
        deadline_text = self.deadline_date.text().strip()
        if deadline_text:
            try:
                deadline_date = parse_jalali_date(deadline_text)
            except ValueError as exc:
                QMessageBox.warning(self, "تاریخ نامعتبر", str(exc))
                return
            deadline_at = _dt.datetime.combine(deadline_date, _dt.time(23, 59))

        subject_id = self.subject_combo.currentData()
        subjects = {s.id: s.name for s in self.service.repo.list_subjects()}
        activity = Activity(
            title=title,
            type=ActivityType(self.type_combo.currentData()),
            subject_id=subject_id,
            subject_name=subjects.get(subject_id, ""),
            est_minutes=self.est_spin.value(),
            remaining_minutes=self.est_spin.value(),
            min_chunk=20,
            max_chunk=90,
            splittable=self.splittable_check.isChecked(),
            deadline_type=DeadlineType(self.deadline_combo.currentData()),
            deadline_at=deadline_at,
            energy_need=EnergyNeed(self.energy_combo.currentData()),
        )
        self.service.create_activity(activity)
        self.accept()


class ActivitiesPage(QWidget):
    """فهرست فعالیت‌ها با چرخهٔ حیات کامل."""

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
        title = QLabel("فعالیت‌ها و صف عقب‌افتادگی")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        btn_add = QPushButton("افزودن فعالیت")
        btn_add.setObjectName("primary")
        btn_add.clicked.connect(self._add)
        header.addWidget(btn_add)
        root.addLayout(header)

        card = Card("همهٔ فعالیت‌ها")
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["عنوان", "نوع", "درس", "برآورد", "باقی‌مانده", "مهلت", "وضعیت"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        card.add(self.table)
        root.addWidget(card, 1)

        actions = QHBoxLayout()
        self.btn_start = QPushButton("شروع")
        self.btn_start.clicked.connect(self._start)
        self.btn_complete = QPushButton("ثبت اتمام")
        self.btn_complete.clicked.connect(self._complete)
        self.btn_partial = QPushButton("ثبت اتمام ناقص")
        self.btn_partial.clicked.connect(self._partial)
        self.btn_defer = QPushButton("تعویق")
        self.btn_defer.clicked.connect(self._defer)
        self.btn_drop = QPushButton("حذف (با تأیید)")
        self.btn_drop.setObjectName("danger")
        self.btn_drop.clicked.connect(self._drop)
        for button in (
            self.btn_start,
            self.btn_complete,
            self.btn_partial,
            self.btn_defer,
            self.btn_drop,
        ):
            actions.addWidget(button)
        actions.addStretch(1)
        root.addLayout(actions)

        self.info = info_box()
        self.info.setText(
            "هیچ فعالیتی بدون ثبت دلیل حذف یا منقضی نمی‌شود؛ فعالیت ناقص "
            "باقی‌مانده و نقطهٔ توقفش را حفظ می‌کند."
        )
        root.addWidget(self.info)

    # ---- کمک‌کننده ----

    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            notify(self, "انتخاب نشده", "ابتدا یک فعالیت را از فهرست انتخاب کنید.")
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        activity_id = item.data(Qt.UserRole)
        return int(activity_id) if activity_id is not None else None

    # ---- کنش‌ها ----

    def refresh(self) -> None:
        activities = self.service.list_activities()
        self.table.setRowCount(0)
        for activity in activities:
            row = self.table.rowCount()
            self.table.insertRow(row)
            title_item = QTableWidgetItem(activity.title)
            title_item.setData(Qt.UserRole, activity.id)
            self.table.setItem(row, 0, title_item)
            self.table.setItem(row, 1, QTableWidgetItem(activity.type.label))
            self.table.setItem(row, 2, QTableWidgetItem(activity.subject_name or "—"))
            self.table.setItem(row, 3, QTableWidgetItem(format_minutes(activity.est_minutes)))
            self.table.setItem(
                row, 4, QTableWidgetItem(format_minutes(activity.remaining_minutes))
            )
            deadline = (
                activity.deadline_at.strftime("%Y-%m-%d %H:%M")
                if activity.deadline_at
                else "—"
            )
            self.table.setItem(row, 5, QTableWidgetItem(deadline))
            state_text = activity.state.label
            if activity.state_reason:
                state_text += f" — {activity.state_reason}"
            self.table.setItem(row, 6, QTableWidgetItem(state_text))

    def _add(self) -> None:
        dialog = AddActivityDialog(self.service, self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh()

    def _start(self) -> None:
        activity_id = self._selected_id()
        if activity_id is None:
            return
        try:
            self.service.start_activity(activity_id)
        except ValueError as exc:
            notify(self, "گذار نامعتبر", str(exc))
            return
        self.refresh()

    def _complete(self) -> None:
        activity_id = self._selected_id()
        if activity_id is None:
            return
        minutes, ok = _ask_minutes(self, "ثبت اتمام", "زمان صرف‌شده (دقیقه):")
        if not ok:
            return
        try:
            self.service.complete_activity(activity_id, minutes)
        except ValueError as exc:
            notify(self, "گذار نامعتبر", str(exc))
            return
        self.refresh()

    def _partial(self) -> None:
        activity_id = self._selected_id()
        if activity_id is None:
            return
        minutes, ok = _ask_minutes(self, "ثبت اتمام ناقص", "زمان صرف‌شده (دقیقه):")
        if not ok:
            return
        remaining = self.service.partial_activity(activity_id, minutes)
        notify(
            self,
            "ثبت شد",
            f"فعالیت ناقص ثبت شد. {remaining} دقیقهٔ دیگر باقی مانده و در "
            "برنامهٔ بعدی ادامه می‌یابد.",
        )
        self.refresh()

    def _defer(self) -> None:
        activity_id = self._selected_id()
        if activity_id is None:
            return
        reason, ok = _ask_text(
            self, "تعویق فعالیت", "دلیل تعویق (کم‌انرژی، بیش از حد زیاد، سؤال، …):"
        )
        if not ok or not reason:
            return
        try:
            self.service.defer_activity(activity_id, reason)
        except ValueError as exc:
            notify(self, "گذار نامعتبر", str(exc))
            return
        self.refresh()

    def _drop(self) -> None:
        activity_id = self._selected_id()
        if activity_id is None:
            return
        reason, ok = _ask_text(self, "حذف فعالیت", "دلیل حذف (ثبت می‌شود):")
        if not ok or not reason:
            return
        if not confirm(
            self,
            "تأیید حذف",
            "این فعالیت حذف می‌شود و دلیل آن در تاریخچه ثبت می‌گردد. ادامه می‌دهید؟",
        ):
            return
        try:
            self.service.drop_activity(activity_id, reason)
        except ValueError as exc:
            notify(self, "گذار نامعتبر", str(exc))
            return
        self.refresh()


def _ask_minutes(parent: QWidget, title: str, label: str) -> tuple[int, bool]:
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setLayoutDirection(Qt.RightToLeft)
    form = QFormLayout(dialog)
    spin = QSpinBox()
    spin.setRange(0, 1440)
    spin.setValue(30)
    form.addRow(label, spin)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.button(QDialogButtonBox.Ok).setText("ثبت")
    buttons.button(QDialogButtonBox.Cancel).setText("انصراف")
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    form.addRow(buttons)
    if dialog.exec() == QDialog.Accepted:
        return spin.value(), True
    return 0, False


def _ask_text(parent: QWidget, title: str, label: str) -> tuple[str, bool]:
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setLayoutDirection(Qt.RightToLeft)
    form = QFormLayout(dialog)
    edit = QLineEdit()
    form.addRow(label, edit)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.button(QDialogButtonBox.Ok).setText("ثبت")
    buttons.button(QDialogButtonBox.Cancel).setText("انصراف")
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    form.addRow(buttons)
    if dialog.exec() == QDialog.Accepted:
        return edit.text().strip(), True
    return "", False
