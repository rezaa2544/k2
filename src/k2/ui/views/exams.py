"""نمای آزمون: ثبت نتیجه، تحلیل خطا و ساخت اقدام اصلاحی."""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

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
from ...jdate import format_minutes, format_number
from ...service import AdvisorService
from ..widgets import Card, info_box, notify


class RecordAttemptDialog(QDialog):
    """ثبت سریع نتیجهٔ یک نوبت آزمون."""

    def __init__(self, service: AdvisorService, parent: QWidget | None = None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("ثبت نوبت آزمون")
        self.setLayoutDirection(Qt.RightToLeft)
        self.attachment_path: str | None = None

        form = QFormLayout(self)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("نام آزمون")
        form.addRow("نام آزمون:", self.name_edit)

        self.kind_combo = QComboBox()
        for kind in ExamKind:
            self.kind_combo.addItem(kind.label, kind.value)
        form.addRow("نوع آزمون:", self.kind_combo)

        self.subject_combo = QComboBox()
        self.subject_combo.addItem("کل آزمون", None)
        for subject in service.selected_subjects():
            self.subject_combo.addItem(subject.name, subject.id)
        form.addRow("درس:", self.subject_combo)

        self.total_spin = QSpinBox()
        self.total_spin.setRange(0, 500)
        form.addRow("تعداد سؤال:", self.total_spin)

        self.correct_spin = QSpinBox()
        self.correct_spin.setRange(0, 500)
        form.addRow("درست:", self.correct_spin)

        self.wrong_spin = QSpinBox()
        self.wrong_spin.setRange(0, 500)
        form.addRow("غلط:", self.wrong_spin)

        self.blank_spin = QSpinBox()
        self.blank_spin.setRange(0, 500)
        form.addRow("نزده:", self.blank_spin)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(0, 600)
        form.addRow("مدت (دقیقه):", self.duration_spin)

        self.error_combo = QComboBox()
        self.error_combo.addItem("— بدون خطای ثبت‌شده —", None)
        for code in ErrorCode:
            self.error_combo.addItem(f"{code.value} — {code.label}", code.value)
        form.addRow("کد خطا (اختیاری):", self.error_combo)

        self.attachment_label = QLabel("پیوستی انتخاب نشده")
        self.attachment_label.setObjectName("fieldHint")
        btn_attach = QPushButton("انتخاب تصویر/فایل نتیجهٔ آزمون")
        btn_attach.setToolTip(
            "تصویر کارت پاسخ یا فایل نتیجه را به پوشهٔ محلی برنامه کپی می‌کند. "
            "برنامه تصویر را نمی‌خوانَد؛ اعداد را خودت وارد می‌کنی و پیوست فقط "
            "منبع اعداد را نگه می‌دارد."
        )
        btn_attach.clicked.connect(self._pick_attachment)
        form.addRow("پیوست (اختیاری):", self.attachment_label)
        form.addRow("", btn_attach)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("ثبت")
        buttons.button(QDialogButtonBox.Cancel).setText("انصراف")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _pick_attachment(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(
            self,
            "انتخاب تصویر یا فایل نتیجهٔ آزمون",
            "",
            "تصویر یا سند (*.png *.jpg *.jpeg *.webp *.pdf *.txt *.csv)",
        )
        if path:
            self.attachment_label.setText(Path(path).name)
            self.attachment_path = path

    def _accept(self) -> None:
        from ...domain.models import ExamQuestion

        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "ورودی ناقص", "نام آزمون را وارد کنید.")
            return

        total = self.total_spin.value()
        correct = self.correct_spin.value()
        wrong = self.wrong_spin.value()
        blank = self.blank_spin.value()
        if total <= 0:
            QMessageBox.warning(self, "ورودی ناقص", "تعداد سؤال را وارد کنید.")
            return
        if correct + wrong + blank > total:
            QMessageBox.warning(
                self, "ورودی ناسازگار", "مجموع درست/غلط/نزده از تعداد سؤال بیشتر است."
            )
            return

        questions = []
        error_code = self.error_combo.currentData()
        if error_code and wrong > 0:
            questions.append(
                ExamQuestion(
                    number=1,
                    status="wrong",
                    error_code=ErrorCode(error_code),
                    subject_id=self.subject_combo.currentData(),
                )
            )

        self.attempt_id = self.service.record_attempt(
            name=name,
            total=total,
            correct=correct,
            wrong=wrong,
            blank=blank,
            kind=ExamKind(self.kind_combo.currentData()),
            subject_id=self.subject_combo.currentData(),
            duration_minutes=self.duration_spin.value(),
            questions=questions,
        )
        self.accept()


class ExamsPage(QWidget):
    """فهرست آزمون‌ها و تحلیل."""

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
        title = QLabel("آزمون‌ها و تحلیل خطا")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        btn_add = QPushButton("ثبت آزمون")
        btn_add.setObjectName("primary")
        btn_add.clicked.connect(self._record)
        header.addWidget(btn_add)
        btn_remedy = QPushButton("ساخت اقدام اصلاحی از آخرین آزمون")
        btn_remedy.clicked.connect(self._remediate)
        header.addWidget(btn_remedy)
        root.addLayout(header)

        card = Card("نوبت‌های آزمون", tone="exam")
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["نام", "نوع", "تاریخ", "کل", "درست", "غلط", "نزده", "درصد"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        card.add(self.table)
        root.addWidget(card, 1)

        self.analysis = Card("تحلیل آخرین آزمون", tone="exam")
        self.analysis_text = QLabel("—")
        self.analysis_text.setWordWrap(True)
        self.analysis.add(self.analysis_text)
        root.addWidget(self.analysis)

        self.info = info_box()
        self.info.setText(
            "درصد بر پایهٔ پروفایل آزمون محاسبه می‌شود (درصد خام یا با نمرهٔ منفی)؛ "
            "آزمون مؤسسه با آزمون رسمی در یک نمودار مخلوط نمی‌شود."
        )
        root.addWidget(self.info)

    def refresh(self) -> None:
        attempts = self.service.list_attempts()
        self.table.setRowCount(0)
        for attempt in attempts:
            row = self.table.rowCount()
            self.table.insertRow(row)
            name_item = QTableWidgetItem(attempt.name)
            name_item.setData(Qt.UserRole, attempt.id)
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, QTableWidgetItem(attempt.kind.label))
            self.table.setItem(
                row,
                2,
                QTableWidgetItem(
                    attempt.taken_at.strftime("%Y-%m-%d") if attempt.taken_at else "—"
                ),
            )
            self.table.setItem(row, 3, QTableWidgetItem(str(attempt.total)))
            self.table.setItem(row, 4, QTableWidgetItem(str(attempt.correct)))
            self.table.setItem(row, 5, QTableWidgetItem(str(attempt.wrong)))
            self.table.setItem(row, 6, QTableWidgetItem(str(attempt.blank)))
            self.table.setItem(
                row, 7, QTableWidgetItem(format_number(attempt.percentage, digits=1) + "٪")
            )

        if not attempts:
            self.analysis_text.setText("هنوز آزمونی ثبت نشده است.")
            return

        latest = attempts[-1]
        errors = self.service.repo.list_error_records(latest.id)
        lines = [
            f"آخرین آزمون: «{latest.name}» ({latest.kind.label}) — "
            f"درصد {format_number(latest.percentage, digits=1)}"
        ]
        if latest.duration_minutes:
            lines.append(
                f"مدت: {format_minutes(latest.duration_minutes)} — "
                f"میانگین هر سؤال: {format_number(latest.duration_minutes / max(1, latest.total), digits=1)} دقیقه"
            )
        if errors:
            counts: dict[str, int] = {}
            for error in errors:
                counts[error.code.value] = counts.get(error.code.value, 0) + 1
            detail = "، ".join(
                f"{code} × {count}" for code, count in sorted(counts.items())
            )
            lines.append(f"کدهای خطا: {detail}")
            lines.append(
                "برای تبدیل خطاها به فعالیت اصلاحی، دکمهٔ «ساخت اقدام اصلاحی» را بزنید."
            )
        else:
            lines.append("برای این آزمون خطایی ثبت نشده است.")
        self.analysis_text.setText("\n".join(lines))

    def _record(self) -> None:
        dialog = RecordAttemptDialog(self.service, self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh()

    def _remediate(self) -> None:
        attempts = self.service.list_attempts()
        if not attempts:
            notify(self, "آزمونی ثبت نشده", "ابتدا یک نوبت آزمون ثبت کنید.")
            return
        plan = self.service.build_remediation(attempts[-1].id)
        if not plan.activities:
            notify(
                self,
                "خطایی ثبت نشده",
                "برای این آزمون خطایی با کد علت ثبت نشده است؛ "
                "در فرم ثبت آزمون، کد خطا را انتخاب کنید.",
            )
            return
        notify(
            self,
            "اقدام اصلاحی ساخته شد",
            "\n".join(plan.notes)
            + "\n\nاین فعالیت‌ها با مهلت مشخص به صف برنامه اضافه شدند.",
        )
        self.refresh()
