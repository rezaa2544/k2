"""نمای مرور: مرورهای سررسیدشده و ثبت نتیجهٔ بازیابی."""

from __future__ import annotations

import datetime as _dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...domain.enums import ReviewState
from ...jdate import format_jalali, format_number
from ...service import AdvisorService
from ..widgets import Card, info_box, notify


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

        card = Card("مرورهای سررسیدشده")
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

    def refresh(self) -> None:
        today = _dt.date.today()
        items = self.service.list_review_items()
        due = self.service.due_review_items(today)
        self.summary.setText(
            f"{len(due)} مورد سررسیدشده از {len(items)} مورد ثبت‌شده — "
            f"سقف روزانهٔ مرور {format_number(self._cap(today))} درصد ظرفیت روز است."
        )

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
