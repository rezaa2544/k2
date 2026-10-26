"""نمای مرور: مرورهای سررسیدشده و ثبت نتیجهٔ بازیابی."""

from __future__ import annotations

import datetime as _dt

from PySide6.QtCore import Qt
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

from ...domain.enums import ReviewState
from ...domain.models import ReviewItem
from ...jdate import format_jalali, format_number
from ...service import AdvisorService
from ..widgets import Card, info_box, notify


class AddReviewDialog(QDialog):
    """افزودن مورد قابل بازیابی و اتصال اختیاری آن به مبحث سنجیده‌شونده."""

    def __init__(self, service: AdvisorService, parent: QWidget | None = None):
        super().__init__(parent)
        self.service = service
        self.item: ReviewItem | None = None
        self.setWindowTitle("افزودن مورد مرور فعال")
        self.setLayoutDirection(Qt.RightToLeft)
        # حداقل پهنا برای اینکه برچسب‌های بلند فارسی بریده نشوند.
        self.setMinimumWidth(540)
        form = QFormLayout(self)
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("سؤال، مفهوم یا مهارتی که باید از حافظه بازیابی شود")
        form.addRow("مورد مرور:", self.label_edit)
        self.topic_combo = QComboBox()
        self.topic_combo.addItem("بدون اتصال به مبحث", None)
        self.topics = service.list_topics()
        for topic in self.topics:
            self.topic_combo.addItem(f"{topic.subject_name} · {topic.name}", topic.id)
        form.addRow("مبحث مرتبط (اختیاری):", self.topic_combo)
        self.type_combo = QComboBox()
        for value, label in (
            ("concept", "مفهومی"), ("memorization", "حفظی"),
            ("calculation", "محاسباتی"), ("vocabulary", "واژگانی"),
            ("diagram", "تصویری/نموداری"),
        ):
            self.type_combo.addItem(label, value)
        form.addRow("نوع:", self.type_combo)
        self.due_edit = QLineEdit(format_jalali(_dt.date.today(), with_weekday=False))
        self.due_edit.setPlaceholderText("۱۴۰۵/۰۷/۲۵")
        form.addRow("موعد نخستین بازیابی (شمسی):", self.due_edit)
        self.difficulty_spin = QSpinBox()
        self.difficulty_spin.setRange(1, 5)
        self.difficulty_spin.setValue(3)
        form.addRow("دشواری تقریبی (۱–۵):", self.difficulty_spin)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("ذخیرهٔ مورد")
        buttons.button(QDialogButtonBox.Cancel).setText("انصراف")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _accept(self) -> None:
        from ...jdate import parse_jalali_date

        label = self.label_edit.text().strip()
        if not label:
            QMessageBox.warning(self, "عنوان لازم است", "مورد بازیابی را وارد کنید.")
            return
        try:
            due = parse_jalali_date(self.due_edit.text())
        except ValueError as exc:
            QMessageBox.warning(self, "تاریخ نامعتبر", str(exc))
            return
        topic_id = self.topic_combo.currentData()
        topic = next((t for t in self.topics if t.id == topic_id), None)
        self.item = ReviewItem(
            topic_id=int(topic.id) if topic else None,
            subject_id=int(topic.subject_id) if topic and topic.subject_id else None,
            label=label,
            item_type=str(self.type_combo.currentData()),
            difficulty=self.difficulty_spin.value(),
            due_date=due,
        )
        self.accept()


class ReviewPage(QWidget):
    """مرورهای سررسیدشده با ثبت سریع نتیجه."""

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
        title = QLabel("مرور تطبیقی")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        btn_add = QPushButton("افزودن مورد مرور")
        btn_add.clicked.connect(self._add_item)
        header.addWidget(btn_add)
        btn_correct = QPushButton("ثبت پاسخ درست")
        btn_correct.setObjectName("primary")
        btn_correct.clicked.connect(lambda: self._grade(True))
        header.addWidget(btn_correct)
        btn_wrong = QPushButton("ثبت پاسخ غلط")
        btn_wrong.clicked.connect(lambda: self._grade(False))
        header.addWidget(btn_wrong)
        root.addLayout(header)

        self.summary = QLabel("—")
        self.summary.setObjectName("muted")
        root.addWidget(self.summary)

        card = Card("مرورهای سررسیدشده", tone="review")
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["مورد", "نوع", "فاصله (روز)", "فراموشی", "سررسید", "وضعیت"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        card.add(self.table)
        root.addWidget(card, 1)

        self.info = info_box()
        self.info.setText(
            "مرور با «بازیابی فعال» شروع می‌شود، نه بازخوانی. فاصلهٔ بعدی از "
            "عملکرد، دشواری و فاصله تا آزمون محاسبه می‌شود؛ الگوی ثابت ۱-۳-۷-۱۴-۳۰ "
            "به‌عنوان قانون علمی استفاده نمی‌شود."
        )
        root.addWidget(self.info)

        # نردبان تثبیت حافظه زیرمجموعهٔ همین صفحه است تا کار تثبیتی از کار
        # مرور جدا نیفتد (بند ۱۷).
        from .consolidation import ConsolidationPage

        self.consolidation = ConsolidationPage(self.service, self)
        root.addWidget(self.consolidation, 1)

    def refresh(self) -> None:
        today = _dt.date.today()
        if hasattr(self, "consolidation"):
            self.consolidation.refresh()
        items = self.service.list_review_items()
        due = self.service.due_review_items(today)
        if items:
            self.summary.setText(
                f"{len(due)} مورد سررسیدشده از {len(items)} مورد ثبت‌شده — "
                f"سقف روزانهٔ مرور {format_number(self._cap(today))} درصد ظرفیت روز است."
            )
        else:
            self.summary.setText("هنوز موردی برای مرور ثبت نشده است.")

        self.table.setRowCount(0)
        for item in due:
            row = self.table.rowCount()
            self.table.insertRow(row)
            label_item = QTableWidgetItem(item.label)
            label_item.setData(Qt.UserRole, item.id)
            self.table.setItem(row, 0, label_item)
            self.table.setItem(row, 1, QTableWidgetItem(item.item_type))
            self.table.setItem(row, 2, QTableWidgetItem(str(item.interval_days)))
            self.table.setItem(row, 3, QTableWidgetItem(str(item.lapses)))
            self.table.setItem(
                row,
                4,
                QTableWidgetItem(format_jalali(item.due_date) if item.due_date else "—"),
            )
            self.table.setItem(row, 5, QTableWidgetItem(item.state.label))

    def _cap(self, today: _dt.date) -> int:
        from ...review_engine import review_budget_minutes

        breakdown = self.service.build_context(today).capacity_for(today)
        budget = review_budget_minutes(breakdown.capacity_minutes, self.service.settings)
        if breakdown.capacity_minutes <= 0:
            return 0
        return int(budget * 100 / breakdown.capacity_minutes)

    def _add_item(self) -> None:
        dialog = AddReviewDialog(self.service, self)
        if dialog.exec() != QDialog.Accepted or dialog.item is None:
            return
        try:
            self.service.create_review_item(dialog.item)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "ذخیره نشد", str(exc))
            return
        self.refresh()

    def _grade(self, correct: bool) -> None:
        row = self.table.currentRow()
        if row < 0:
            notify(self, "انتخاب نشده", "ابتدا یک مورد مرور را انتخاب کنید.")
            return
        item = self.table.item(row, 0)
        if item is None:
            return
        item_id = item.data(Qt.UserRole)
        if item_id is None:
            return
        update = self.service.record_review(
            int(item_id), correct=correct, confidence=2 if correct else 1
        )
        message = (
            f"فاصلهٔ بعدی: {update.new_interval:.1f} روز — "
            f"موعد بعدی: {format_jalali(update.new_due)}"
        )
        if update.notes:
            message += "\n" + "\n".join(update.notes)
        notify(self, "مرور ثبت شد", message)
        self.refresh()
