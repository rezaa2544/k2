"""نمای «تست و تحلیل»: تست‌های کوتاه، تحلیل خطا و اقدام اصلاحی (بند ۱۷).

این صفحه از «آزمون‌های جامع» جدا است: تست یک ابزار یادگیری است (تست
تدریس، تست زمان‌دار، تحلیل گزینه‌ها)، در حالی که آزمون جامع یک سنجش
سراسری نزدیک به آزمون واقعی است.
"""

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

from ...domain.enums import ErrorCode, ExamKind
from ...jdate import format_jalali, format_minutes, format_number
from ...service import AdvisorService
from ..widgets import Card, info_box, notify

#: نوع‌هایی که «تست و تحلیل» شمرده می‌شوند، نه آزمون جامع.
TEST_KINDS = {
    ExamKind.DIAGNOSTIC.value,
    ExamKind.INSTITUTE.value,
    ExamKind.MOCK.value,
}

ERROR_CODES = list(ErrorCode)


class QuestionDialog(QDialog):
    """ثبت جزئیات یک سؤال اشتباه."""

    def __init__(
        self, service: AdvisorService, attempt_id: int, parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.service = service
        self.attempt_id = attempt_id
        self.setWindowTitle("ثبت سؤال اشتباه")
        self.setLayoutDirection(Qt.RightToLeft)
        form = QFormLayout(self)

        self.number_spin = QSpinBox()
        self.number_spin.setRange(1, 500)
        form.addRow("شمارهٔ سؤال:", self.number_spin)

        self.status_combo = QComboBox()
        for value, label in (
            ("wrong", "غلط"), ("blank", "خالی"), ("correct", "درست"),
        ):
            self.status_combo.addItem(label, value)
        form.addRow("وضعیت:", self.status_combo)

        self.topic_combo = QComboBox()
        self.topic_combo.addItem("— بدون مبحث —", None)
        for topic in service.list_topics():
            self.topic_combo.addItem(
                f"{topic.subject_name} · {topic.name}", topic.id
            )
        form.addRow("مبحث:", self.topic_combo)

        self.error_combo = QComboBox()
        for code in ERROR_CODES:
            self.error_combo.addItem(code.label, code.value)
        form.addRow("علت خطا:", self.error_combo)

        self.seconds_spin = QSpinBox()
        self.seconds_spin.setRange(0, 3600)
        self.seconds_spin.setSuffix(" ثانیه")
        form.addRow("زمان صرف‌شده:", self.seconds_spin)

        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("یادداشت اختیاری")
        form.addRow("یادداشت:", self.note_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("ذخیره")
        buttons.button(QDialogButtonBox.Cancel).setText("انصراف")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _accept(self) -> None:
        if self.status_combo.currentData() == "correct" and self.error_combo.currentData():
            QMessageBox.warning(
                self, "ناسازگار", "سؤال درست علت خطا ندارد؛ وضعیت را «غلط» بگذار."
            )
            return
        self.accept()


class TestsPage(QWidget):
    """تست‌ها و تحلیل آن‌ها با ساخت اقدام اصلاحی."""

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
        title = QLabel("تست و تحلیل")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        btn_record = QPushButton("ثبت تست")
        btn_record.setObjectName("primary")
        btn_record.clicked.connect(self._record)
        header.addWidget(btn_record)
        btn_question = QPushButton("ثبت سؤال اشتباه")
        btn_question.clicked.connect(self._add_question)
        header.addWidget(btn_question)
        btn_remediate = QPushButton("ساخت اقدام اصلاحی")
        btn_remediate.setToolTip(
            "برای خطاهای ثبت‌شدهٔ تست انتخاب‌شده کار رفع اشکال می‌سازد"
        )
        btn_remediate.clicked.connect(self._remediate)
        header.addWidget(btn_remediate)
        root.addLayout(header)

        self.summary = QLabel("—")
        self.summary.setObjectName("muted")
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)

        self.analysis = info_box()
        self.analysis.setVisible(False)
        root.addWidget(self.analysis)

        splitter = QHBoxLayout()
        tests_card = Card("تست‌های ثبت‌شده", tone="exam")
        self.test_table = QTableWidget(0, 6)
        self.test_table.setHorizontalHeaderLabels(
            ["نام", "نوع", "تاریخ", "درصد", "مدت", "یادداشت"]
        )
        self.test_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.test_table.verticalHeader().setVisible(False)
        self.test_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.test_table.setSelectionBehavior(QTableWidget.SelectRows)
        tests_card.add(self.test_table)
        splitter.addWidget(tests_card, 3)

        errors_card = Card("خطاهای تست انتخاب‌شده", tone="problem")
        self.error_table = QTableWidget(0, 4)
        self.error_table.setHorizontalHeaderLabels(
            ["مبحث", "علت خطا", "وضعیت رفع", "اقدام"]
        )
        self.error_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.error_table.verticalHeader().setVisible(False)
        self.error_table.setEditTriggers(QTableWidget.NoEditTriggers)
        errors_card.add(self.error_table)
        splitter.addWidget(errors_card, 2)
        root.addLayout(splitter, 1)

        self.info = info_box()
        self.info.setText(
            "تست ابزار یادگیری است: بعد از هر تست، خطاها را با علت طبقه‌بندی "
            "کن و برای هر علت یک اقدام اصلاحی بساز. تحلیل بی‌اقدام، فقط "
            "نمره است؛ با اقدام، تغییر رفتار."
        )
        root.addWidget(self.info)

        self.test_table.itemSelectionChanged.connect(self._show_errors)

    def _attempts(self):
        attempts = self.service.list_attempts()
        return [
            a
            for a in attempts
            if (a.kind.value if hasattr(a.kind, "value") else str(a.kind))
            in TEST_KINDS
        ]

    def refresh(self) -> None:
        tests = self._attempts()
        self.test_table.setRowCount(0)
        for attempt in tests:
            row = self.test_table.rowCount()
            self.test_table.insertRow(row)
            id_item = QTableWidgetItem(attempt.name or "تست")
            id_item.setData(Qt.UserRole, attempt.id)
            self.test_table.setItem(row, 0, id_item)
            self.test_table.setItem(
                row, 1,
                QTableWidgetItem(
                    attempt.kind.label if hasattr(attempt.kind, "label") else str(attempt.kind)
                ),
            )
            self.test_table.setItem(
                row, 2,
                QTableWidgetItem(
                    format_jalali(attempt.taken_at.date(), with_weekday=False)
                    if attempt.taken_at else "—"
                ),
            )
            self.test_table.setItem(
                row, 3, QTableWidgetItem(f"{format_number(attempt.percentage)}٪")
            )
            self.test_table.setItem(
                row, 4, QTableWidgetItem(format_minutes(attempt.duration_minutes))
            )
            self.test_table.setItem(row, 5, QTableWidgetItem(attempt.note or "—"))
        if tests:
            best = max(tests, key=lambda a: a.percentage)
            worst = min(tests, key=lambda a: a.percentage)
            self.summary.setText(
                f"{len(tests)} تست ثبت شده — بهترین {format_number(best.percentage)}٪ "
                f"({best.name}) — ضعیف‌ترین {format_number(worst.percentage)}٪ ({worst.name})"
            )
        else:
            self.summary.setText("هنوز تستی ثبت نشده است.")
        self._show_errors()

    def _selected_attempt_id(self) -> int | None:
        row = self.test_table.currentRow()
        if row < 0:
            return None
        item = self.test_table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _show_errors(self) -> None:
        attempt_id = self._selected_attempt_id()
        self.error_table.setRowCount(0)
        if attempt_id is None:
            return
        errors = [
            e for e in self.service.repo.list_error_records()
            if e.attempt_id == attempt_id
        ]
        topics = {t.id: t for t in self.service.list_topics()}
        for error in errors:
            row = self.error_table.rowCount()
            self.error_table.insertRow(row)
            topic = topics.get(error.topic_id)
            self.error_table.setItem(
                row, 0,
                QTableWidgetItem(topic.name if topic else "—"),
            )
            self.error_table.setItem(row, 1, QTableWidgetItem(error.code.label))
            self.error_table.setItem(
                row, 2,
                QTableWidgetItem("رفع شد" if error.resolved_at else "باز"),
            )
            self.error_table.setItem(
                row, 3,
                QTableWidgetItem(
                    "اقدام ساخته شده" if error.resolution_activity_id else "—"
                ),
            )
        if errors:
            codes: dict[str, int] = {}
            for error in errors:
                key = error.code.label
                codes[key] = codes.get(key, 0) + 1
            summary = " — ".join(f"{k}: {v}" for k, v in sorted(codes.items(), key=lambda i: -i[1]))
            self.analysis.setVisible(True)
            self.analysis.setText(
                f"پرتکرارترین علت خطا: {summary}\n"
                "برای هر علت، یک اقدام اصلاحی بساز؛ تکرار یک علت یعنی روش "
                "قبلی کار نکرده است."
            )
        else:
            self.analysis.setVisible(False)

    def _record(self) -> None:
        from .exams import RecordAttemptDialog

        dialog = RecordAttemptDialog(self.service, self)
        if dialog.exec() != QDialog.Accepted:
            return
        # دیالوگ خودش آزمون را ثبت می‌کند؛ پیوست را بعد از داشتن شناسه
        # وصل می‌کنیم تا اعداد و منبعشان کنار هم بمانند.
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

    def _add_question(self) -> None:
        attempt_id = self._selected_attempt_id()
        if attempt_id is None:
            notify(self, "انتخاب نشده", "اول یک تست را انتخاب کن.")
            return
        dialog = QuestionDialog(self.service, attempt_id, self)
        if dialog.exec() != QDialog.Accepted:
            return
        from ...domain.models import ExamQuestion

        try:
            self.service.repo.create_question(
                ExamQuestion(
                    attempt_id=attempt_id,
                    topic_id=dialog.topic_combo.currentData(),
                    number=dialog.number_spin.value(),
                    status=dialog.status_combo.currentData(),
                    error_code=ErrorCode(dialog.error_combo.currentData()),
                    seconds=dialog.seconds_spin.value() or None,
                    note=dialog.note_edit.text().strip(),
                )
            )
            self.service.conn.commit()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "ذخیره نشد", str(exc))
            return
        self.refresh()

    def _remediate(self) -> None:
        attempt_id = self._selected_attempt_id()
        if attempt_id is None:
            notify(self, "انتخاب نشده", "اول یک تست را انتخاب کن.")
            return
        try:
            plan = self.service.build_remediation(attempt_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "ساخته نشد", str(exc))
            return
        for activity in plan.activities:
            self.service.create_activity(activity)
        notify(
            self,
            "اقدام اصلاحی ساخته شد",
            f"{len(plan.activities)} کار اصلاحی برای خطاهای این تست ساخته شد.\n"
            + "\n".join(plan.notes[:4]),
        )
        self.refresh()


__all__ = ["QuestionDialog", "TestsPage"]
