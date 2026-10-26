"""نمای «مشکلات یادگیری»: ثبت، پیگیری و رفع مشکل (بند ۱۷)."""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...domain.enums import ProblemKind, ProblemStatus
from ...domain.models import LearningProblem
from ...jdate import format_jalali, format_number
from ...service import AdvisorService
from ..widgets import Card, info_box, notify

PROBLEM_KINDS = list(ProblemKind)
STATUSES = list(ProblemStatus)

SEVERITY_LABELS = {
    1: "خیلی کم",
    2: "کم",
    3: "متوسط",
    4: "زیاد",
    5: "بسیار زیاد",
}


class ProblemDialog(QDialog):
    """ثبت یا ویرایش یک مشکل یادگیری."""

    def __init__(
        self,
        service: AdvisorService,
        problem: LearningProblem | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.service = service
        self.problem = problem
        self.setWindowTitle("ثبت مشکل یادگیری" if problem is None else "ویرایش مشکل")
        self.setLayoutDirection(Qt.RightToLeft)
        # حداقل پهنا برای اینکه برچسب‌های فارسی و فهرست‌های کشویی بریده نشوند.
        self.setMinimumWidth(540)
        self.attachment_path: str | None = None
        form = QFormLayout(self)

        self.kind_combo = QComboBox()
        for kind in PROBLEM_KINDS:
            self.kind_combo.addItem(kind.label, kind.value)
        form.addRow("نوع مشکل:", self.kind_combo)
        if problem is not None:
            index = self.kind_combo.findData(problem.kind)
            if index >= 0:
                self.kind_combo.setCurrentIndex(index)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("مثلاً در تست‌های زمان‌دار هندسه گیر می‌کنم")
        form.addRow("عنوان:", self.title_edit)
        if problem is not None:
            self.title_edit.setText(problem.title)

        self.subject_combo = QComboBox()
        self.subject_combo.addItem("— بدون درس —", None)
        for subject in service.repo.list_subjects(include_unselected=True):
            self.subject_combo.addItem(subject.name, subject.id)
        form.addRow("درس:", self.subject_combo)

        self.topic_combo = QComboBox()
        self.topic_combo.addItem("— بدون مبحث —", None)
        for topic in service.list_topics():
            self.topic_combo.addItem(
                f"{topic.subject_name} · {topic.name}", topic.id
            )
        form.addRow("مبحث:", self.topic_combo)

        self.severity_spin = QSpinBox()
        self.severity_spin.setRange(1, 5)
        form.addRow("شدت خودگزارشی:", self.severity_spin)
        if problem is not None:
            self.severity_spin.setValue(problem.severity)

        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText(
            "شرح مشکل: چه زمانی ظاهر می‌شود، در چه نوع سؤالی، چه کاری تا حالا کرده‌ای"
        )
        self.description_edit.setMaximumHeight(90)
        form.addRow("شرح:", self.description_edit)
        if problem is not None:
            self.description_edit.setPlainText(problem.description)

        self.status_combo = QComboBox()
        for status in STATUSES:
            self.status_combo.addItem(status.label, status.value)
        form.addRow("وضعیت:", self.status_combo)

        self.attachment_label = QLabel("پیوستی انتخاب نشده")
        self.attachment_label.setObjectName("fieldHint")
        btn_attach = QPushButton("انتخاب تصویر/فایل (اختیاری)")
        btn_attach.setToolTip(
            "عکس از دفتر یا تصویر سؤال را محلی نگه می‌دارد. برنامه تصویر را "
            "نمی‌خوانَد؛ توضیح را خودت وارد می‌کنی."
        )
        btn_attach.clicked.connect(self._pick_attachment)
        form.addRow("پیوست:", self.attachment_label)
        form.addRow("", btn_attach)
        if problem is not None:
            index = self.status_combo.findData(problem.status)
            if index >= 0:
                self.status_combo.setCurrentIndex(index)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("ذخیره")
        buttons.button(QDialogButtonBox.Cancel).setText("انصراف")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _pick_attachment(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "انتخاب تصویر یا فایل",
            "",
            "تصویر یا سند (*.png *.jpg *.jpeg *.webp *.pdf *.txt)",
        )
        if path:
            self.attachment_label.setText(Path(path).name)
            self.attachment_path = path

    def _accept(self) -> None:
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "عنوان لازم است", "عنوان مشکل را وارد کن.")
            return
        self.result_problem = LearningProblem(
            id=self.problem.id if self.problem else None,
            subject_id=self.subject_combo.currentData(),
            topic_id=self.topic_combo.currentData(),
            kind=ProblemKind(self.kind_combo.currentData()),
            title=title,
            description=self.description_edit.toPlainText().strip(),
            severity=self.severity_spin.value(),
            status=ProblemStatus(self.status_combo.currentData()),
            first_seen=self.problem.first_seen if self.problem else _dt.date.today(),
        )
        self.accept()


class LearningProblemsPage(QWidget):
    """مشکلات یادگیری با پیگیری و رویداد."""

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
        title = QLabel("مشکلات یادگیری")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        btn_add = QPushButton("ثبت مشکل")
        btn_add.setObjectName("primary")
        btn_add.clicked.connect(self._add)
        header.addWidget(btn_add)
        btn_resolve = QPushButton("ثبت رفع")
        btn_resolve.clicked.connect(self._resolve)
        header.addWidget(btn_resolve)
        btn_edit = QPushButton("ویرایش")
        btn_edit.clicked.connect(self._edit)
        header.addWidget(btn_edit)
        root.addLayout(header)

        self.summary = QLabel("—")
        self.summary.setObjectName("muted")
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)

        card = Card("مشکلات ثبت‌شده (به ترتیب شدت)", tone="problem")
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["عنوان", "نوع", "درس/مبحث", "شدت", "وضعیت", "اولین ظهور"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        card.add(self.table)
        root.addWidget(card, 1)

        self.detail = Card("پیگیری مشکل انتخاب‌شده", tone="problem")
        self.detail_text = QLabel("یک مشکل را انتخاب کن.")
        self.detail_text.setWordWrap(True)
        self.detail.add(self.detail_text)
        root.addWidget(self.detail)

        self.info = info_box()
        self.info.setText(
            "مشکل یادگیری چیزی است که خودت تشخیص می‌دهی: شکاف مفهومی، بی‌دقتی، "
            "کندی، فراموشی زودرس یا استرس آزمون. شدت خودگزارشی است و از نمرهٔ "
            "آزمون حساب نمی‌شود؛ ولی در اولویت‌دهی و بازبینی شبانه دیده می‌شود."
        )
        root.addWidget(self.info)

        self.table.itemSelectionChanged.connect(self._show_detail)

    def refresh(self) -> None:
        problems = self.service.list_learning_problems()
        open_problems = [p for p in problems if p.is_open]
        self.table.setRowCount(0)
        for problem in problems:
            row = self.table.rowCount()
            self.table.insertRow(row)
            id_item = QTableWidgetItem(problem.title)
            id_item.setData(Qt.UserRole, problem.id)
            self.table.setItem(row, 0, id_item)
            self.table.setItem(row, 1, QTableWidgetItem(problem.kind.label))
            label = problem.topic_name or problem.subject_name or "—"
            self.table.setItem(row, 2, QTableWidgetItem(label))
            self.table.setItem(
                row, 3,
                QTableWidgetItem(
                    f"{format_number(problem.severity)} ({SEVERITY_LABELS[problem.severity]})"
                ),
            )
            self.table.setItem(row, 4, QTableWidgetItem(problem.status.label))
            self.table.setItem(
                row, 5,
                QTableWidgetItem(
                    format_jalali(problem.first_seen, with_weekday=False)
                    if problem.first_seen else "—"
                ),
            )
        if problems:
            severe = [p for p in open_problems if p.severity >= 4]
            self.summary.setText(
                f"{len(open_problems)} مشکل باز از {len(problems)} مشکل ثبت‌شده"
                + (f" — {len(severe)} مشکل شدید." if severe else ".")
            )
        else:
            self.summary.setText("هنوز مشکلی ثبت نشده است.")

    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _show_detail(self) -> None:
        problem_id = self._selected_id()
        if problem_id is None:
            self.detail_text.setText("یک مشکل را از جدول انتخاب کن.")
            return
        problem = next(
            (p for p in self.service.list_learning_problems() if p.id == problem_id),
            None,
        )
        if problem is None:
            return
        events = self.service.problem_events(problem_id)
        lines = [f"<b>{problem.title}</b>", ""]
        lines.append(f"نوع: {problem.kind.label} — شدت: {problem.severity}")
        lines.append(f"وضعیت: {problem.status.label}")
        if problem.description:
            lines.append(f"شرح: {problem.description}")
        if problem.resolution_note:
            lines.append(f"راه‌حل: {problem.resolution_note}")
        if events:
            lines.append("")
            lines.append("<b>تاریخچهٔ پیگیری:</b>")
            for event in events:
                stamp = (
                    format_jalali(event.at.date(), with_weekday=False)
                    if event.at else "—"
                )
                lines.append(f"• {stamp} — {event.note}")
        self.detail_text.setText("<br>".join(lines))

    def _add(self) -> None:
        dialog = ProblemDialog(self.service, None, self)
        if dialog.exec() != QDialog.Accepted:
            return
        problem = getattr(dialog, "result_problem", None)
        if problem is None:
            return
        try:
            self.service.save_learning_problem(problem)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "ذخیره نشد", str(exc))
            return
        self.refresh()

    def _edit(self) -> None:
        problem_id = self._selected_id()
        if problem_id is None:
            notify(self, "انتخاب نشده", "اول یک مشکل را انتخاب کن.")
            return
        problem = next(
            (p for p in self.service.list_learning_problems() if p.id == problem_id),
            None,
        )
        if problem is None:
            return
        dialog = ProblemDialog(self.service, problem, self)
        if dialog.exec() != QDialog.Accepted:
            return
        updated = getattr(dialog, "result_problem", None)
        if updated is None:
            return
        try:
            self.service.save_learning_problem(updated)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "ذخیره نشد", str(exc))
            return
        if dialog.attachment_path and updated.id:
            try:
                self.service.attach_file(
                    dialog.attachment_path, owner="problem", owner_id=updated.id
                )
            except ValueError as exc:
                QMessageBox.warning(self, "پیوست نشد", str(exc))
        self.refresh()

    def _resolve(self) -> None:
        problem_id = self._selected_id()
        if problem_id is None:
            notify(self, "انتخاب نشده", "اول یک مشکل را انتخاب کن.")
            return
        dialog = ResolveDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.service.set_problem_status(
                problem_id, dialog.result_status, dialog.result_note
            )
        except ValueError as exc:
            QMessageBox.warning(self, "ثبت نشد", str(exc))
            return
        self.refresh()
        self._show_detail()


class ResolveDialog(QDialog):
    """ثبت رفع یا تغییر وضعیت یک مشکل با یادداشت."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("ثبت اقدام روی مشکل")
        self.setLayoutDirection(Qt.RightToLeft)
        # حداقل پهنا برای اینکه برچسب‌های فارسی و فهرست‌های کشویی بریده نشوند.
        self.setMinimumWidth(480)
        self.result_status = ProblemStatus.RESOLVED
        self.result_note = ""
        form = QFormLayout(self)
        self.status_combo = QComboBox()
        for status in STATUSES:
            self.status_combo.addItem(status.label, status.value)
        form.addRow("وضعیت تازه:", self.status_combo)
        self.note_edit = QTextEdit()
        self.note_edit.setPlaceholderText("چه کاری کردی و نتیجه چه بود")
        self.note_edit.setMaximumHeight(80)
        form.addRow("یادداشت:", self.note_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("ثبت")
        buttons.button(QDialogButtonBox.Cancel).setText("انصراف")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _accept(self) -> None:
        note = self.note_edit.toPlainText().strip()
        if not note:
            QMessageBox.warning(self, "یادداشت لازم است", "برای هر اقدام، یادداشت بگذار.")
            return
        self.result_status = ProblemStatus(self.status_combo.currentData())
        self.result_note = note
        self.accept()


__all__ = ["LearningProblemsPage", "ProblemDialog", "ResolveDialog"]
