"""نمای «آزمون‌های جامع»: سنجش سراسری نزدیک به آزمون واقعی (بند ۱۷).

تفاوت با «تست و تحلیل»: آزمون جامع چند درسی و نزدیک به شرایط واقعی است
و خروجی‌اش «وضعیت کل» می‌دهد نه «اقدام اصلاحی یک تست».
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
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...domain.enums import ExamKind
from ...jdate import format_jalali, format_minutes, format_number
from ...service import AdvisorService
from ..widgets import Card, info_box, warn_box

#: نوع‌هایی که آزمون جامع شمرده می‌شوند.
COMPREHENSIVE_KINDS = {
    ExamKind.OFFICIAL.value,
    ExamKind.MOCK.value,
}


class ComprehensiveExamsPage(QWidget):
    """آزمون‌های جامع با روند درصد و تحلیل درسی."""

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
        title = QLabel("آزمون‌های جامع")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        btn_record = QPushButton("ثبت آزمون جامع")
        btn_record.setObjectName("primary")
        btn_record.clicked.connect(self._record)
        header.addWidget(btn_record)
        btn_bottleneck = QPushButton("تحلیل گلوگاه")
        btn_bottleneck.setToolTip(
            "از نتیجهٔ آزمون‌های جامع، گلوگاه آموزشی را پیدا کن"
        )
        btn_bottleneck.clicked.connect(self._bottleneck)
        header.addWidget(btn_bottleneck)
        root.addLayout(header)

        self.summary = QLabel("—")
        self.summary.setObjectName("muted")
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)

        self.alert = warn_box()
        self.alert.setVisible(False)
        root.addWidget(self.alert)

        splitter = QHBoxLayout()
        exams_card = Card("آزمون‌های ثبت‌شده", tone="exam")
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["نام", "نوع", "تاریخ", "درصد", "درست/کل", "مدت", "درس"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        exams_card.add(self.table)
        splitter.addWidget(exams_card, 3)

        trend_card = Card("روند درصد", tone="exam")
        self.trend_table = QTableWidget(0, 3)
        self.trend_table.setHorizontalHeaderLabels(
            ["آزمون", "درصد", "تغییر"]
        )
        self.trend_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.trend_table.verticalHeader().setVisible(False)
        self.trend_table.setEditTriggers(QTableWidget.NoEditTriggers)
        trend_card.add(self.trend_table)
        splitter.addWidget(trend_card, 2)
        root.addLayout(splitter, 1)

        self.info = info_box()
        self.info.setText(
            "آزمون جامع فقط وقتی معنا دارد که بعد از آن، برنامه عوض شود: "
            "گلوگاه پیدا می‌شود، اولویت‌ها بازبینی می‌شوند و مهلت‌ها بازمحاسبه "
            "می‌شوند. در بخش «مشکلات یادگیری» هم می‌توانی علت‌های تکرارشونده را "
            "ثبت و پیگیری کنی."
        )
        root.addWidget(self.info)

    def _attempts(self):
        attempts = self.service.list_attempts()
        return [
            a
            for a in attempts
            if (a.kind.value if hasattr(a.kind, "value") else str(a.kind))
            in COMPREHENSIVE_KINDS
        ]

    def refresh(self) -> None:
        exams = sorted(
            self._attempts(),
            key=lambda a: a.taken_at or _dt.datetime.min,
        )
        self.table.setRowCount(0)
        for attempt in exams:
            row = self.table.rowCount()
            self.table.insertRow(row)
            id_item = QTableWidgetItem(attempt.name or "آزمون جامع")
            id_item.setData(Qt.UserRole, attempt.id)
            self.table.setItem(row, 0, id_item)
            self.table.setItem(
                row, 1,
                QTableWidgetItem(
                    attempt.kind.label if hasattr(attempt.kind, "label") else str(attempt.kind)
                ),
            )
            self.table.setItem(
                row, 2,
                QTableWidgetItem(
                    format_jalali(attempt.taken_at.date(), with_weekday=False)
                    if attempt.taken_at else "—"
                ),
            )
            self.table.setItem(
                row, 3, QTableWidgetItem(f"{format_number(attempt.percentage)}٪")
            )
            self.table.setItem(
                row, 4, QTableWidgetItem(f"{attempt.correct} از {attempt.total}")
            )
            self.table.setItem(
                row, 5, QTableWidgetItem(format_minutes(attempt.duration_minutes))
            )
            self.table.setItem(row, 6, QTableWidgetItem(attempt.subject_name or "کل"))

        if exams:
            latest = exams[-1]
            previous = exams[-2] if len(exams) > 1 else None
            delta = (
                latest.percentage - previous.percentage if previous else None
            )
            self.summary.setText(
                f"{len(exams)} آزمون جامع ثبت شده — آخرین "
                f"{format_number(latest.percentage)}٪ ({latest.name})"
                + (
                    f" — تغییر {format_number(delta, digits=1)}٪ نسبت به قبلی"
                    if delta is not None else ""
                )
            )
            self.alert.setVisible(bool(delta is not None and delta < -5))
            if delta is not None and delta < -5:
                self.alert.setText(
                    "درصد آخرین آزمون جامع نسبت به قبلی افت کرده است. در "
                    "بازبینی شبانه علت را ثبت کن: حجم بیشتر بود؟ روش عوض نشده؟ "
                    "خستگی؟ بدون علت، برنامهٔ بعدی همان اشتباه را تکرار می‌کند."
                )
        else:
            self.summary.setText("هنوز آزمون جامعی ثبت نشده است.")
            self.alert.setVisible(False)

        self.trend_table.setRowCount(0)
        previous_percent = None
        for attempt in exams:
            row = self.trend_table.rowCount()
            self.trend_table.insertRow(row)
            self.trend_table.setItem(row, 0, QTableWidgetItem(attempt.name or "آزمون"))
            self.trend_table.setItem(
                row, 1, QTableWidgetItem(f"{format_number(attempt.percentage)}٪")
            )
            change = "—" if previous_percent is None else (
                f"{format_number(attempt.percentage - previous_percent, digits=1)}٪"
            )
            self.trend_table.setItem(row, 2, QTableWidgetItem(change))
            previous_percent = attempt.percentage

    def _record(self) -> None:
        from .exams import RecordAttemptDialog

        dialog = RecordAttemptDialog(self.service, self)
        if dialog.exec() != QDialog.Accepted:
            return
        if dialog.attachment_path and dialog.attempt_id:
            try:
                self.service.attach_file(
                    dialog.attachment_path,
                    owner="attempt",
                    owner_id=dialog.attempt_id,
                )
            except ValueError as exc:
                QMessageBox.warning(self, "پیوست نشد", str(exc))
        self.refresh()

    def _bottleneck(self) -> None:
        from ... import advisor_engine

        errors = self.service.repo.list_error_records()
        questions: list = []
        for attempt in self.service.list_attempts():
            questions.extend(self.service.repo.list_questions(attempt.id))
        subjects = self.service.selected_subjects()
        subject_name = subjects[0].name if subjects else "همهٔ درس‌ها"
        report = advisor_engine.detect_bottleneck(
            subject_name=subject_name,
            errors=errors,
            questions=questions,
            settings=self.service.settings,
        )
        lines = [f"گلوگاه فعلی: {report.bottleneck.label}", ""]
        lines.extend(report.evidence[:6])
        if not report.evidence:
            lines.append(
                "شواهد کافی برای تشخیص گلوگاه نیست؛ چند آزمون جامع با "
                "جزئیات سؤال ثبت کن."
            )
        QMessageBox.information(self, "گلوگاه آموزشی", "\n".join(lines))


__all__ = ["ComprehensiveExamsPage"]
