"""نمای تثبیت: نردبان تثبیت، پیش‌بینی ماندگاری و توزیع سه‌مسیرهٔ بار.

این صفحه قلب «مشاور واقعی» است:
  * وضعیت هر مبحث روی نردبان تثبیت (S0 تا S5) با شواهد عملکردی.
  * پیش‌بینی ماندگاری تا روز آزمون بر پایهٔ مدل DSR.
  * توزیع ظرفیت امروز بین مطلب جدید / جبران / تثبیت.
  * امکان‌سنجی: آیا کارهای باقی‌مانده تا آزمون جا می‌شود؟
"""

from __future__ import annotations

import datetime as _dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ... import consolidation, streams
from ...jdate import format_jalali, format_minutes, format_number
from ...service import AdvisorService
from ..widgets import Card, info_box, notify

STATUS_LABELS = {
    "not_started": "ندیده",
    "on_track": "در مسیر",
    "at_risk": "در خطر",
    "behind": "عقب‌افتاده",
    "consolidated": "تثبیت‌شده",
}

STATUS_COLORS = {
    "not_started": "#8a9a94",
    "on_track": "#1d7a5f",
    "at_risk": "#b26a00",
    "behind": "#b3261e",
    "consolidated": "#0b6e4f",
}


class ConsolidationPage(QWidget):
    """داشبورد تثبیت حافظه و برنامهٔ سه‌مسیره."""

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
        title = QLabel("تثبیت حافظه و برنامهٔ سه‌مسیره")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        btn_seed = QPushButton("ساخت مباحث از کاتالوگ")
        btn_seed.setToolTip(
            "فهرست مبحثی هر درس را از کاتالوگ [H] می‌سازد؛ خودتان تأیید یا حذف کنید."
        )
        btn_seed.clicked.connect(self._seed_topics)
        header.addWidget(btn_seed)
        root.addLayout(header)

        # --- توزیع بار امروز ---
        streams_card = Card("توزیع ظرفیت امروز بین سه مسیر")
        self.streams_summary = QLabel("—")
        self.streams_summary.setObjectName("muted")
        streams_card.add(self.streams_summary)
        self.stream_bars: dict[str, QProgressBar] = {}
        for key, label in (
            ("new", "مطلب جدید"),
            ("catchup", "جبران عقب‌افتادگی"),
            ("consolidation", "تثبیت و مرور"),
            ("reserve", "حاشیهٔ آزاد"),
        ):
            line = QHBoxLayout()
            name = QLabel(label)
            name.setFixedWidth(140)
            bar = QProgressBar()
            bar.setFormat("%v دقیقه")
            bar.setTextVisible(True)
            line.addWidget(name)
            line.addWidget(bar, 1)
            streams_card.add_layout(line)
            self.stream_bars[key] = bar
        root.addWidget(streams_card)

        # --- امکان‌سنجی ---
        feasibility_card = Card("آیا کارهای باقی‌مانده تا آزمون جا می‌شود؟")
        self.feasibility_label = QLabel("—")
        self.feasibility_label.setWordWrap(True)
        feasibility_card.add(self.feasibility_label)
        self.feasibility_options = QLabel("")
        self.feasibility_options.setWordWrap(True)
        self.feasibility_options.setObjectName("muted")
        feasibility_card.add(self.feasibility_options)
        root.addWidget(feasibility_card)

        # --- صف جبران ---
        catchup_card = Card("صف جبران قدم‌به‌قدم")
        self.catchup_summary = QLabel("—")
        self.catchup_summary.setWordWrap(True)
        self.catchup_summary.setObjectName("muted")
        catchup_card.add(self.catchup_summary)
        root.addWidget(catchup_card)

        # --- جدول مبحث‌ها ---
        topics_card = Card("نردبان تثبیت مبحث‌ها")
        self.subject_filter = QComboBox()
        self.subject_filter.addItem("همهٔ درس‌ها", None)
        self.subject_filter.currentIndexChanged.connect(self._reload_table)
        topics_card.add(self.subject_filter)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            [
                "مبحث",
                "درس",
                "پلهٔ فعلی",
                "وضعیت",
                "پیش‌بینی ماندگاری تا آزمون",
                "موعد گام بعدی",
                "اقدام بعدی",
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        topics_card.add(self.table)
        root.addWidget(topics_card, 1)

        self.info = info_box()
        self.info.setText(
            "نردبان تثبیت: هر مبحث برای «تثبیت‌شده» اعلام شدن باید شواهد عملکردی "
            "هر پنج پله را بدهد — بازیابی اولیه (تا ۲۴ ساعت، پس از خواب)، فاصله‌دار، "
            "تأخیری، انتقالی و نگهداری. پیش‌بینی بر پایهٔ مدل DSR است و تضمین حافظه "
            "نیست. پله‌های عقب‌افتاده در صف جبران قرار می‌گیرند و حذف نمی‌شوند."
        )
        root.addWidget(self.info)

    # ---- به‌روزرسانی ----

    def refresh(self) -> None:
        today = _dt.date.today()
        try:
            overview = self.service.consolidation_overview(today)
        except Exception as exc:  # noqa: BLE001
            self.streams_summary.setText(f"خطا در محاسبهٔ تثبیت: {exc}")
            return

        self._refresh_subject_filter(overview)
        self._refresh_streams(overview)
        self._refresh_feasibility(overview)
        self._refresh_catchup(overview)
        self._reload_table(overview)

    def _refresh_subject_filter(self, overview: dict) -> None:
        current = self.subject_filter.currentData()
        names = []
        for item in overview["consolidations"]:
            if item.subject_name and item.subject_name not in names:
                names.append(item.subject_name)
        self.subject_filter.blockSignals(True)
        self.subject_filter.clear()
        self.subject_filter.addItem("همهٔ درس‌ها", None)
        for name in sorted(names):
            self.subject_filter.addItem(name, name)
        if current is not None:
            index = self.subject_filter.findData(current)
            if index >= 0:
                self.subject_filter.setCurrentIndex(index)
        self.subject_filter.blockSignals(False)

    def _refresh_streams(self, overview: dict) -> None:
        allocation: streams.StreamAllocation = overview["allocation"]
        capacity = max(1, allocation.capacity_minutes)
        self.streams_summary.setText(
            f"ظرفیت مؤثر امروز: {format_minutes(allocation.capacity_minutes)}"
            + (
                f" · {format_number(overview['days_to_exam'])} روز تا آزمون"
                if overview["days_to_exam"] is not None
                else ""
            )
            + (
                " · " + " · ".join(allocation.notes[:2])
                if allocation.notes
                else ""
            )
        )
        for key, bar in self.stream_bars.items():
            value = int(allocation.as_dict()[key])
            bar.setRange(0, capacity)
            bar.setValue(value)

    def _refresh_feasibility(self, overview: dict) -> None:
        verdict: streams.FeasibilityVerdict = overview["feasibility"]
        level_labels = {
            "ok": "قابل انجام",
            "tight": "فشرده ولی شدنی",
            "infeasible": "جا نمی‌شود",
            "unknown": "نامشخص",
        }
        tone = {
            "ok": "#1d7a5f",
            "tight": "#b26a00",
            "infeasible": "#b3261e",
            "unknown": "#8a9a94",
        }[verdict.level]
        self.feasibility_label.setStyleSheet(f"color: {tone}; font-weight: bold;")
        self.feasibility_label.setText(
            f"{level_labels[verdict.level]} — "
            + " ".join(verdict.notes)
        )
        if verdict.options:
            self.feasibility_options.setText(
                "گزینه‌های تصمیم (هیچ‌کدام خودکار اعمال نمی‌شود):\n"
                + "\n".join(f"• {option}" for option in verdict.options)
            )
        else:
            self.feasibility_options.setText("")

    def _refresh_catchup(self, overview: dict) -> None:
        """صف جبران: هر روز چه سهمی از کدام کار عقب‌افتاده پیش می‌رود."""
        backlog = overview.get("backlog")
        plan: list[streams.CatchupQuota] = overview.get("catchup") or []
        if backlog is None or not backlog.items:
            self.catchup_summary.setText("صف جبران خالی است؛ کار عقب‌افتاده‌ای ثبت نشده.")
            return
        total = backlog.debt_minutes
        planned = sum(quota.minutes for quota in plan)
        if planned >= total:
            tail = "کل بدهی در بازهٔ برنامه‌ریزی‌شده جبران می‌شود."
        else:
            tail = (
                f"{format_minutes(total - planned)} از بدهی در این بازه جا نمی‌شود؛ "
                "گزینه‌های امکان‌سنجی را بررسی کنید."
            )
        days = sorted({quota.date for quota in plan})
        preview = " · ".join(
            f"{format_jalali(day)}: {format_minutes(sum(q.minutes for q in plan if q.date == day))}"
            for day in days[:5]
        )
        self.catchup_summary.setText(
            f"بدهی: {format_minutes(total)} در {len(backlog.items)} کار · "
            f"جبران روزانهٔ برنامه‌ریزی‌شده: {format_minutes(overview['allocation'].catchup_minutes)}\n"
            f"{preview}"
            + (" …" if len(days) > 5 else "")
            + f"\n{tail}"
        )

    def _reload_table(self, overview: dict | None = None) -> None:
        today = _dt.date.today()
        if overview is None:
            try:
                overview = self.service.consolidation_overview(today)
            except Exception as exc:  # noqa: BLE001
                self.table.setRowCount(0)
                QMessageBox.warning(self, "خطا", str(exc))
                return
        subject_filter = self.subject_filter.currentData()
        rows = [
            item
            for item in overview["consolidations"]
            if subject_filter is None or item.subject_name == subject_filter
        ]
        # ترتیب: عقب‌افتاده → در خطر → در مسیر → تثبیت‌شده → ندیده
        order = {"behind": 0, "at_risk": 1, "on_track": 2, "consolidated": 3, "not_started": 4}
        rows.sort(key=lambda item: (order.get(item.status, 5), item.subject_name, item.topic_name))
        self.table.setRowCount(0)
        for item in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            topic_item = QTableWidgetItem(item.topic_name)
            topic_item.setData(Qt.UserRole, item.topic_id)
            self.table.setItem(row, 0, topic_item)
            self.table.setItem(row, 1, QTableWidgetItem(item.subject_name))
            self.table.setItem(row, 2, QTableWidgetItem(item.stage_label))
            status_item = QTableWidgetItem(STATUS_LABELS.get(item.status, item.status))
            status_item.setForeground(Qt.GlobalColor.white)
            from PySide6.QtGui import QColor

            status_item.setBackground(QColor(STATUS_COLORS.get(item.status, "#8a9a94")))
            self.table.setItem(row, 3, status_item)
            forecast = (
                format_number(item.forecast_retention * 100) + "٪"
                if item.forecast_retention
                else "—"
            )
            self.table.setItem(row, 4, QTableWidgetItem(forecast))
            self.table.setItem(
                row,
                5,
                QTableWidgetItem(format_jalali(item.next_due) if item.next_due else "—"),
            )
            advice = consolidation.consolidation_advice(item, self.service.settings)
            advice_item = QTableWidgetItem(advice[0])
            advice_item.setToolTip(advice[1])
            self.table.setItem(row, 6, advice_item)

    # ---- کنش‌ها ----

    def _seed_topics(self) -> None:
        from ..widgets import confirm

        subjects = self.service.selected_subjects()
        if not subjects:
            notify(self, "درسی ثبت نشده", "ابتدا در راه‌اندازی درس‌ها را انتخاب کنید.")
            return
        created_total = 0
        for subject in subjects:
            if subject.id is None:
                continue
            try:
                created = self.service.seed_topics_from_catalog(subject.id)
            except Exception as exc:  # noqa: BLE001
                QMessageBox.warning(self, "ساخت مباحث ناموفق", str(exc))
                return
            created_total += len(created)
        if created_total:
            notify(
                self,
                "مباحث ساخته شد",
                f"{created_total} مبحث از کاتالوگ ساخته شد. "
                "در صفحهٔ «مباحث و تسلط» آن‌ها را تأیید، حذف یا ویرایش کنید.",
            )
        else:
            notify(
                self,
                "مبحث تازه‌ای ساخته نشد",
                "همهٔ مباحث کاتالوگ از قبل ثبت شده‌اند.",
            )
        self.refresh()
