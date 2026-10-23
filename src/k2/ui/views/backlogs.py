"""نمای «عقب‌افتادگی‌ها»: بدهی مطالعه، تریاژ و روز حداقلی (سند تحقیق ۲)."""

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

from ...jdate import format_jalali, format_minutes, format_number
from ...service import AdvisorService
from ..widgets import Card, info_box, warn_box

LEVEL_LABELS = {
    "green": "سبز",
    "yellow": "زرد",
    "orange": "نارنجی",
    "red": "قرمز",
}


class BacklogsPage(QWidget):
    """عقب‌افتادگی‌ها با تریاژ صریح و بدون پنهان‌کردن کارها."""

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
        title = QLabel("عقب‌افتادگی‌ها")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        self.btn_minimal = QPushButton("روز حداقلی")
        self.btn_minimal.setToolTip(
            "اگر امروز ظرفیت چندانی نداری، کمینهٔ کار لازم را نشان بده"
        )
        self.btn_minimal.clicked.connect(self._show_minimal)
        header.addWidget(self.btn_minimal)
        root.addLayout(header)

        self.summary = QLabel("—")
        self.summary.setObjectName("muted")
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)

        self.alert = warn_box()
        self.alert.setVisible(False)
        root.addWidget(self.alert)

        splitter = QHBoxLayout()

        triage_card = Card("تریاژ امروز", tone="backlog")
        self.triage_table = QTableWidget(0, 4)
        self.triage_table.setHorizontalHeaderLabels(
            ["کار", "مدت", "اولویت", "دلیل"]
        )
        self.triage_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.triage_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.triage_table.verticalHeader().setVisible(False)
        self.triage_table.setEditTriggers(QTableWidget.NoEditTriggers)
        triage_card.add(self.triage_table)
        splitter.addWidget(triage_card, 2)

        backlog_card = Card("بدهی ثبت‌شده", tone="backlog")
        self.backlog_table = QTableWidget(0, 3)
        self.backlog_table.setHorizontalHeaderLabels(["کار", "مهلت", "وضعیت"])
        self.backlog_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.backlog_table.verticalHeader().setVisible(False)
        self.backlog_table.setEditTriggers(QTableWidget.NoEditTriggers)
        backlog_card.add(self.backlog_table)
        splitter.addWidget(backlog_card, 1)

        root.addLayout(splitter, 1)

        self.minimal_text = QLabel("")
        self.minimal_text.setWordWrap(True)
        self.minimal_text.setVisible(False)
        root.addWidget(self.minimal_text)

        self.info = info_box()
        self.info.setText(
            "عقب‌افتادگی حذف نمی‌شود؛ یا جبران می‌شود یا با دلیل روشن تعویق "
            "می‌خورد. سقف کار جبرانی روزانه از تنظیمات خوانده می‌شود تا "
            "«تزریق شوک» رخ ندهد."
        )
        root.addWidget(self.info)

    def refresh(self) -> None:
        today = _dt.date.today()
        summary = self.service.backlog(today)
        triage = self.service.triage(today)
        self.summary.setText(
            f"بدهی: {format_minutes(summary.debt_minutes)} از "
            f"{format_minutes(summary.recoverable_minutes)} قابل جبران — "
            f"سطح {LEVEL_LABELS.get(getattr(summary.level, 'value', ''), '—')} — "
            f"سقف جبران روزانه: {format_minutes(summary.compensation_cap_minutes)}"
        )
        for note in summary.notes[:3]:
            self.summary.setText(self.summary.text() + "\n" + note)
        overdue = [
            a for a in self.service.list_activities()
            if getattr(a, "deadline_at", None) and a.deadline_at.date() < today
        ]
        self.alert.setVisible(bool(overdue))
        if overdue:
            self.alert.setText(
                f"{len(overdue)} کار از موعدش گذشته است. در بازبینی شبانه، "
                "اهمیت و فوریت هر کدام سنجیده می‌شود؛ کاری کورکورانه به فردا "
                "نمی‌رود."
            )

        self.triage_table.setRowCount(0)
        groups = (
            ("باید انجام شود", triage.must_do),
            ("اگر وقت شد", triage.if_possible),
            ("کاندیدای تعویق", triage.suggest_drop),
        )
        for group_label, activities in groups:
            for activity in activities:
                row = self.triage_table.rowCount()
                self.triage_table.insertRow(row)
                self.triage_table.setItem(
                    row, 0, QTableWidgetItem(f"{activity.title}  ({group_label})")
                )
                self.triage_table.setItem(
                    row, 1, QTableWidgetItem(format_minutes(activity.effective_minutes))
                )
                self.triage_table.setItem(row, 2, QTableWidgetItem(group_label))
                reason = activity.state_reason or "—"
                if activity.times_rescheduled:
                    reason += f" — {activity.times_rescheduled} بار بازچینی شده"
                self.triage_table.setItem(row, 3, QTableWidgetItem(reason))
        for note in triage.notes[:3]:
            self.summary.setText(self.summary.text() + "\n" + note)

        self.backlog_table.setRowCount(0)
        for activity in self.service.list_activities():
            if activity.state.value not in {"overdue", "partial", "deferred", "expired"}:
                continue
            row = self.backlog_table.rowCount()
            self.backlog_table.insertRow(row)
            self.backlog_table.setItem(row, 0, QTableWidgetItem(activity.title))
            self.backlog_table.setItem(
                row, 1,
                QTableWidgetItem(
                    format_jalali(activity.deadline_at.date(), with_weekday=False)
                    if activity.deadline_at else "—"
                ),
            )
            self.backlog_table.setItem(row, 2, QTableWidgetItem(activity.state.label))

    def _show_minimal(self) -> None:
        today = _dt.date.today()
        plan = self.service.minimal_day(today)
        lines = [
            f"روز حداقلی {format_jalali(today)}:",
            f"زمان لازم: {format_minutes(plan.minutes)}",
        ]
        for activity in plan.activities:
            lines.append(f"• {activity.title} — {format_minutes(activity.effective_minutes)}")
        lines.extend(plan.notes)
        self.minimal_text.setText("\n".join(lines))
        self.minimal_text.setVisible(True)


__all__ = ["BacklogsPage"]
