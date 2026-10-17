"""نمای «برنامهٔ امروز»: بلوک‌ها، دلیل جای‌گذاری و کارهای جا‌نشده."""

from __future__ import annotations

import datetime as _dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...jdate import format_jalali_long, format_minutes
from ...service import AdvisorService
from ..widgets import Card, info_box, warn_box


class TodayPlanPage(QWidget):
    """برنامهٔ روز با دلیل هر انتخاب."""

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
        self.title = QLabel("برنامهٔ امروز")
        self.title.setObjectName("sectionTitle")
        header.addWidget(self.title)
        header.addStretch(1)
        self.btn_refresh = QPushButton("بازسازی برنامه")
        self.btn_refresh.setObjectName("primary")
        self.btn_refresh.clicked.connect(self.refresh)
        header.addWidget(self.btn_refresh)
        root.addLayout(header)

        self.summary = QLabel("—")
        self.summary.setObjectName("muted")
        root.addWidget(self.summary)

        self.conflicts = warn_box()
        self.conflicts.setVisible(False)
        root.addWidget(self.conflicts)

        splitter = QSplitter(Qt.Vertical)

        plan_card = Card("بلوک‌های برنامه")
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["ساعت", "مدت", "کار", "دلیل جای‌گذاری", "وضعیت"]
        )
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        plan_card.add(self.table)
        splitter.addWidget(plan_card)

        unplaced_card = Card("کارهایی که امروز جا نشدند (پنهان نشده‌اند)")
        self.unplaced_table = QTableWidget(0, 4)
        self.unplaced_table.setHorizontalHeaderLabels(
            ["کار", "مدت لازم", "دلیل", "جزئیات"]
        )
        self.unplaced_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.unplaced_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.unplaced_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.unplaced_table.verticalHeader().setVisible(False)
        self.unplaced_table.setEditTriggers(QTableWidget.NoEditTriggers)
        unplaced_card.add(self.unplaced_table)
        splitter.addWidget(unplaced_card)

        root.addWidget(splitter, 1)

        self.info = info_box()
        self.info.setText(
            "زمان‌بند قاعده‌محور است: محدودیت‌های سخت (خواب، کلاس، آزمون) هرگز "
            "نقض نمی‌شوند و برنامه از ظرفیت روز بیشتر نمی‌شود."
        )
        root.addWidget(self.info)

    def refresh(self) -> None:
        today = _dt.date.today()
        plan = self.service.plan_day(today)

        self.title.setText(f"برنامهٔ {format_jalali_long(today)}")
        self.summary.setText(
            f"ظرفیت {format_minutes(plan.capacity_minutes)} — "
            f"زمان خام {format_minutes(plan.raw_minutes)} — "
            f"زمان مؤثر {format_minutes(plan.effective_minutes)} — "
            f"برنامه {format_minutes(plan.planned_minutes)} — "
            f"حاشیهٔ آزاد {format_minutes(plan.margin_minutes)}"
        )

        self.table.setRowCount(0)
        for placement in plan.placements:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(f"{placement.start_clock}–{placement.end_clock}"))
            self.table.setItem(row, 1, QTableWidgetItem(format_minutes(placement.minutes)))
            title = placement.title
            if placement.chunk_total > 1:
                title += f"  (قسمت {placement.chunk_index} از {placement.chunk_total})"
            self.table.setItem(row, 2, QTableWidgetItem(title))
            self.table.setItem(row, 3, QTableWidgetItem(" — ".join(placement.reasons)))
            self.table.setItem(row, 4, QTableWidgetItem("برنامه‌ریزی‌شده"))

        self.unplaced_table.setRowCount(0)
        for item in plan.unplaced:
            row = self.unplaced_table.rowCount()
            self.unplaced_table.insertRow(row)
            self.unplaced_table.setItem(row, 0, QTableWidgetItem(item.title))
            self.unplaced_table.setItem(row, 1, QTableWidgetItem(format_minutes(item.minutes)))
            self.unplaced_table.setItem(row, 2, QTableWidgetItem(item.reason))
            self.unplaced_table.setItem(row, 3, QTableWidgetItem(" — ".join(item.details)))

        notes = [n for n in plan.notes]
        if notes:
            self.conflicts.setVisible(True)
            self.conflicts.setText("\n".join(notes))
        else:
            self.conflicts.setVisible(False)
