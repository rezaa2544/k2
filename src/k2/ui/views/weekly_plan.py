"""نمای «برنامه هفتگی»: بازهٔ هفت روز، بازبینی شبانه و بازسازی (بند ۱۶).

این صفحه جای «فعالیت‌ها»ی قدیمی را هم می‌گیرد: کارها را می‌بینید،
اضافه می‌کنید و با «بازبینی و بازسازی شبانه» برنامهٔ روزهای بعد را
بدون دست‌زدن به کلاس‌های ثابت از نو می‌سازد.
"""

from __future__ import annotations

import datetime as _dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...jdate import format_jalali, format_jalali_long, format_minutes, week_days
from ...service import AdvisorService
from ..widgets import Card, info_box, notify, warn_box

PERSIAN_WEEKDAYS = [
    "شنبه", "یک‌شنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه",
]


class WeeklyPlanPage(QWidget):
    """برنامهٔ هفت روز با دلیل هر تغییر."""

    def __init__(self, service: AdvisorService, parent: QWidget | None = None):
        super().__init__(parent)
        self.service = service
        self._build()
        self.refresh()

    # ---- ساخت رابط ----

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        header = QHBoxLayout()
        self.title = QLabel("برنامه هفتگی")
        self.title.setObjectName("sectionTitle")
        header.addWidget(self.title)
        header.addStretch(1)
        self.btn_review = QPushButton("بازبینی و بازسازی شبانه")
        self.btn_review.setObjectName("primary")
        self.btn_review.setToolTip(
            "کارهای انجام‌شده و ناقص امروز را می‌بیند، مهلت‌ها را می‌سنجد و "
            "برنامهٔ روزهای بعد را با حفظ کلاس‌های ثابت بازمی‌سازد."
        )
        self.btn_review.clicked.connect(self._nightly)
        header.addWidget(self.btn_review)
        self.btn_add = QPushButton("افزودن کار")
        self.btn_add.setToolTip("یک کار تازه برای برنامه اضافه کن")
        self.btn_add.clicked.connect(self._add_activity)
        header.addWidget(self.btn_add)
        root.addLayout(header)

        self.summary = QLabel("—")
        self.summary.setObjectName("muted")
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)

        self.review_box = warn_box()
        self.review_box.setVisible(False)
        root.addWidget(self.review_box)

        splitter = QSplitter(Qt.Vertical)

        week_card = Card("نمای هفت روز", tone="study")
        self.week_table = QTableWidget(0, 6)
        self.week_table.setHorizontalHeaderLabels(
            ["روز", "تاریخ", "ظرفیت", "برنامه‌ریزی", "اجراشده", "وضعیت"]
        )
        self.week_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.week_table.verticalHeader().setVisible(False)
        self.week_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.week_table.setSelectionBehavior(QTableWidget.SelectRows)
        week_card.add(self.week_table)
        splitter.addWidget(week_card)

        plan_card = Card("کارهای روز انتخاب‌شده", tone="study")
        self.plan_table = QTableWidget(0, 5)
        self.plan_table.setHorizontalHeaderLabels(
            ["ساعت", "مدت", "کار", "دلیل جای‌گذاری", "وضعیت"]
        )
        self.plan_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.plan_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.plan_table.verticalHeader().setVisible(False)
        self.plan_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.plan_table.setSelectionBehavior(QTableWidget.SelectRows)
        plan_card.add(self.plan_table)
        splitter.addWidget(plan_card)

        root.addWidget(splitter, 1)

        self.info = info_box()
        self.info.setText(
            "بازسازی شبانه کار نیمه‌تمام را کورکورانه به فردا نمی‌برد: اول "
            "اهمیت و فوریتش سنجیده می‌شود، بعد بین روزهای باز توزیع می‌شود. "
            "کلاس‌ها و تعهدهای ثابت شما هرگز جابه‌جا نمی‌شوند."
        )
        root.addWidget(self.info)

    # ---- به‌روزرسانی ----

    def refresh(self) -> None:
        today = _dt.date.today()
        start = week_start(today)
        days = week_days(start, 7)
        plans = self.service.plan_range(start, 7)
        sessions = self.service.list_study_sessions(days[0], days[-1])

        planned_total = sum(p.planned_minutes for p in plans)
        capacity_total = sum(p.capacity_minutes for p in plans)
        done_total = sum(
            s.minutes for s in sessions if s.started_at and days[0] <= s.started_at.date() <= days[-1]
        )
        self.title.setText(f"برنامه هفتگی — {format_jalali(days[0])} تا {format_jalali(days[-1])}")
        self.summary.setText(
            f"ظرفیت هفته {format_minutes(capacity_total)} — برنامه‌ریزی‌شده "
            f"{format_minutes(planned_total)} — اجراشده {format_minutes(done_total)}"
        )

        self.week_table.setRowCount(0)
        for index, plan in enumerate(plans):
            row = self.week_table.rowCount()
            self.week_table.insertRow(row)
            day_item = QTableWidgetItem(PERSIAN_WEEKDAYS[index])
            day_item.setData(Qt.UserRole, plan.date)
            self.week_table.setItem(row, 0, day_item)
            self.week_table.setItem(row, 1, QTableWidgetItem(format_jalali(plan.date, with_weekday=False)))
            self.week_table.setItem(row, 2, QTableWidgetItem(format_minutes(plan.capacity_minutes)))
            self.week_table.setItem(row, 3, QTableWidgetItem(format_minutes(plan.planned_minutes)))
            day_done = sum(
                s.minutes for s in sessions
                if s.started_at and s.started_at.date() == plan.date
            )
            self.week_table.setItem(row, 4, QTableWidgetItem(format_minutes(day_done)))
            status = "آزاد" if plan.planned_minutes < plan.capacity_minutes else "پُر"
            if plan.is_over_capacity:
                status = "بیش از ظرفیت"
            self.week_table.setItem(row, 5, QTableWidgetItem(status))
        if self.week_table.rowCount():
            self.week_table.setCurrentCell(0, 0)
        self._fill_selected_day()

    def _fill_selected_day(self) -> None:
        row = self.week_table.currentRow()
        if row < 0:
            self.plan_table.setRowCount(0)
            return
        item = self.week_table.item(row, 0)
        if item is None:
            return
        date = item.data(Qt.UserRole)
        plan = self.service.plan_day(date)
        self.plan_table.setRowCount(0)
        for placement in plan.placements:
            row_index = self.plan_table.rowCount()
            self.plan_table.insertRow(row_index)
            self.plan_table.setItem(
                row_index, 0,
                QTableWidgetItem(f"{placement.start_clock}–{placement.end_clock}"),
            )
            self.plan_table.setItem(
                row_index, 1, QTableWidgetItem(format_minutes(placement.minutes))
            )
            title = placement.title
            if placement.chunk_total > 1:
                title += f"  (قسمت {placement.chunk_index} از {placement.chunk_total})"
            self.plan_table.setItem(row_index, 2, QTableWidgetItem(title))
            self.plan_table.setItem(
                row_index, 3, QTableWidgetItem(" — ".join(placement.reasons))
            )
            self.plan_table.setItem(row_index, 4, QTableWidgetItem("برنامه‌ریزی‌شده"))
        for unplaced in plan.unplaced:
            row_index = self.plan_table.rowCount()
            self.plan_table.insertRow(row_index)
            self.plan_table.setItem(row_index, 0, QTableWidgetItem("—"))
            self.plan_table.setItem(row_index, 1, QTableWidgetItem(format_minutes(unplaced.minutes)))
            self.plan_table.setItem(row_index, 2, QTableWidgetItem(unplaced.title))
            self.plan_table.setItem(row_index, 3, QTableWidgetItem(f"جا نشد: {unplaced.reason}"))
            self.plan_table.setItem(row_index, 4, QTableWidgetItem("نیازمند تصمیم"))

    # ---- کنش‌ها ----

    def _add_activity(self) -> None:
        from .activities import AddActivityDialog

        dialog = AddActivityDialog(self.service, self)
        if dialog.exec() != dialog.Accepted or dialog.activity is None:
            return
        # دیالوگ خودش فعالیت را ذخیره می‌کند؛ اینجا فقط نما تازه می‌شود.
        self.refresh()

    def _nightly(self) -> None:
        today = _dt.date.today()
        review = self.service.nightly_review(today)
        replan = self.service.replan_forward(today=today)
        lines: list[str] = []
        lines.append(
            f"امروز {format_minutes(review.done_minutes)} از "
            f"{format_minutes(review.planned_minutes)} دقیقهٔ برنامه اجرا شد "
            f"({review.completion_ratio:.0%})."
        )
        lines.append(
            f"کلاس {format_minutes(review.class_minutes)} — "
            f"مطالعهٔ مستقل {format_minutes(review.independent_minutes)}."
        )
        if review.incomplete:
            lines.append("ناقص مانده: " + "؛ ".join(review.incomplete[:5]))
        if review.better:
            lines.append("بهتر از برآورد: " + "؛ ".join(review.better[:3]))
        if review.worse:
            lines.append("بدتر از برآورد: " + "؛ ".join(review.worse[:3]))
        for risk in review.deadline_risks[:4]:
            lines.append("ریسک مهلت: " + risk)
        for risk in review.capacity_risks[:3]:
            lines.append("ریسک ظرفیت: " + risk)
        for change in replan.changes[:5]:
            lines.append(
                f"تغییر: {change.title} — {change.reason}"
                + (f" (اثر بر مهلت: {change.deadline_impact})" if change.deadline_impact else "")
            )
        if replan.decisions:
            lines.append(
                "تصمیم‌ها: "
                + "؛ ".join(f"{d.title} → {d.action}" for d in replan.decisions[:5])
            )
        self.review_box.setVisible(True)
        self.review_box.setText("\n".join(lines))
        self.refresh()
        notify(self, "بازبینی شبانه انجام شد", "برنامهٔ روزهای بعد بازسازی شد.")


def week_start(day: _dt.date) -> _dt.date:
    """شنبهٔ هفتهٔ شامل روز مورد نظر."""
    return day - _dt.timedelta(days=(day.weekday() + 2) % 7)


__all__ = ["WeeklyPlanPage", "week_start"]
