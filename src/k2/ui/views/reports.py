"""نمای گزارش‌ها: گزارش روزانه/هفتگی، پیشرفت شخصی و خروجی CSV."""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ... import reporting
from ...jdate import format_jalali_long, format_number
from ...service import AdvisorService
from ..widgets import Card, info_box, notify


class ReportsPage(QWidget):
    """گزارش‌های شخصی (بدون مقایسه با دیگران)."""

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
        title = QLabel("گزارش‌ها")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        btn_csv = QPushButton("خروجی CSV فعالیت‌ها")
        btn_csv.clicked.connect(self._export_csv)
        header.addWidget(btn_csv)
        btn_refresh = QPushButton("به‌روزرسانی")
        btn_refresh.setObjectName("primary")
        btn_refresh.clicked.connect(self.refresh)
        header.addWidget(btn_refresh)
        root.addLayout(header)

        self.daily_card = Card("گزارش روز")
        self.daily_text = QLabel("—")
        self.daily_text.setWordWrap(True)
        self.daily_card.add(self.daily_text)
        root.addWidget(self.daily_card)

        self.weekly_card = Card("گزارش هفتگی")
        self.weekly_text = QTextEdit()
        self.weekly_text.setReadOnly(True)
        self.weekly_text.setMinimumHeight(220)
        self.weekly_card.add(self.weekly_text)
        root.addWidget(self.weekly_card)

        self.trend_card = Card("روند شخصی")
        self.trend_text = QLabel("—")
        self.trend_text.setWordWrap(True)
        self.trend_card.add(self.trend_text)
        root.addWidget(self.trend_card)

        self.pressure_card = Card("نشانگر فشار برنامه (توصیفی)")
        self.pressure_text = QLabel("—")
        self.pressure_text.setWordWrap(True)
        self.pressure_card.add(self.pressure_text)
        root.addWidget(self.pressure_card)

        self.info = info_box()
        self.info.setText(
            "همهٔ مقایسه‌ها با سابقهٔ خود شماست. هیچ رتبه‌بندی، استریک یا "
            "مقایسه با همسالان وجود ندارد و هیچ تشخیص پزشکی ارائه نمی‌شود."
        )
        root.addWidget(self.info)
        root.addStretch(1)

    def refresh(self) -> None:
        today = _dt.date.today()
        if not self.service.list_activities() and not self.service.list_attempts():
            self.daily_text.setText("هنوز فعالیت یا آزمونی ثبت نشده است.")
            self.weekly_text.setPlainText("پس از ثبت داده‌های واقعی، گزارش هفتگی در اینجا نمایش داده می‌شود.")
            self.trend_text.setText("برای نمایش روند، ابتدا نتایج آزمون خود را ثبت کنید.")
            self.pressure_text.setText("تا زمان ثبت اطلاعات، نشانگر فشار محاسبه نمی‌شود.")
            return

        daily = self.service.daily_report(today)
        self.daily_text.setText(daily.to_text())

        weekly = self.service.weekly_report(today)
        self.weekly_text.setPlainText(reporting.weekly_report_to_text(weekly))

        trend = reporting.accuracy_trend(self.service.list_attempts())
        if trend.points:
            self.trend_text.setText(
                f"دقت آزمون‌ها: {format_number((trend.first or 0) * 100, digits=1)}٪ → "
                f"{format_number((trend.last or 0) * 100, digits=1)}٪ "
                f"(روند: {trend.direction}).\n{trend.note}"
            )
        else:
            self.trend_text.setText("هنوز آزمونی ثبت نشده است.")

        backlog = self.service.backlog(today)
        signal = reporting.pressure_signal(
            energy_factors=[self.service.energy_level / 3.0],
            debt_ratio=backlog.debt_ratio,
        )
        if signal.active:
            self.pressure_text.setText(signal.message + "\n\n" + "\n".join(signal.reasons))
        else:
            self.pressure_text.setText(signal.message)

    def _export_csv(self) -> None:
        target, _ = QFileDialog.getSaveFileName(
            self, "ذخیرهٔ خروجی CSV", "k2-activities.csv", "CSV (*.csv)"
        )
        if not target:
            return
        path = reporting.export_activities_csv(self.service.list_activities(), target)
        notify(self, "خروجی گرفته شد", f"فایل ذخیره شد:\n{path}")
