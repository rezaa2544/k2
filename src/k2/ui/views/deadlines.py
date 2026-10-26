"""نمای «مهلت‌های من»: مهلت هر مبحث، بازمحاسبه و شاهد تکمیل (بند ۱۲)."""

from __future__ import annotations

import datetime as _dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
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

from ...deadline_planner import STAGE_LABELS, feasibility_message
from ...domain.enums import DeadlineKind, TrackKind
from ...domain.models import TopicDeadline
from ...jdate import format_jalali, format_number, parse_jalali_date
from ...service import AdvisorService
from ..widgets import Card, info_box, notify, warn_box

DEADLINE_KINDS = [
    (DeadlineKind.START, "مهلت شروع"),
    (DeadlineKind.INITIAL_LEARNING, "مهلت یادگیری اولیه"),
    (DeadlineKind.PRACTICE, "مهلت تمرین/تست"),
    (DeadlineKind.FINAL_CONSOLIDATION, "مهلت تثبیت نهایی"),
]

TRACKS = [(TrackKind.KONKUR, "کنکور (تستی)"), (TrackKind.FINAL, "نهایی/مدرک (تشریحی)")]


class DeadlineDialog(QDialog):
    """ثبت یا ویرایش یک مهلت."""

    def __init__(
        self,
        service: AdvisorService,
        deadline: TopicDeadline | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.service = service
        self.deadline = deadline
        self.setWindowTitle("ثبت مهلت مبحث" if deadline is None else "ویرایش مهلت")
        self.setLayoutDirection(Qt.RightToLeft)
        # حداقل پهنا برای اینکه برچسب‌های فارسی و فهرست‌های کشویی بریده نشوند.
        self.setMinimumWidth(520)
        form = QFormLayout(self)

        self.topic_combo = QComboBox()
        topics = service.list_topics()
        for topic in topics:
            self.topic_combo.addItem(f"{topic.subject_name} · {topic.name}", topic.id)
        form.addRow("مبحث:", self.topic_combo)
        if deadline is not None and deadline.topic_id is not None:
            index = self.topic_combo.findData(deadline.topic_id)
            if index >= 0:
                self.topic_combo.setCurrentIndex(index)

        self.kind_combo = QComboBox()
        for kind, label in DEADLINE_KINDS:
            self.kind_combo.addItem(label, kind.value)
        form.addRow("نوع مهلت:", self.kind_combo)
        if deadline is not None:
            index = self.kind_combo.findData(deadline.kind)
            if index >= 0:
                self.kind_combo.setCurrentIndex(index)

        self.date_edit = QLineEdit()
        self.date_edit.setPlaceholderText("تاریخ موعد را به شکل ۱۴۰۵/۰۷/۲۵ وارد کن")
        form.addRow("تاریخ مهلت (شمسی):", self.date_edit)
        if deadline is not None and deadline.target_date:
            self.date_edit.setText(format_jalali(deadline.target_date, with_weekday=False))

        self.track_combo = QComboBox()
        for track, label in TRACKS:
            self.track_combo.addItem(label, track.value)
        form.addRow("مسیر هدف:", self.track_combo)
        if deadline is not None:
            index = self.track_combo.findData(deadline.target_track)
            if index >= 0:
                self.track_combo.setCurrentIndex(index)

        self.percent_spin = QDoubleSpinBox()
        self.percent_spin.setRange(0, 100)
        self.percent_spin.setDecimals(0)
        self.percent_spin.setSuffix(" درصد")
        self.percent_spin.setSpecialValueText("بدون هدف درصدی")
        form.addRow("هدف درصد (اختیاری):", self.percent_spin)
        if deadline is not None and deadline.target_percent is not None:
            self.percent_spin.setValue(deadline.target_percent)

        self.level_spin = QSpinBox()
        self.level_spin.setRange(0, 4)
        self.level_spin.setSpecialValueText("بدون هدف سطح")
        self.level_spin.setSuffix(" (سطح تسلط)")
        form.addRow("هدف سطح تسلط (اختیاری):", self.level_spin)
        if deadline is not None and deadline.target_level:
            try:
                self.level_spin.setValue(int(str(deadline.target_level).lstrip("L")))
            except ValueError:
                self.level_spin.setValue(0)

        self.master_check = QComboBox()
        self.master_check.addItem("بله — از این مهلت به عقب محاسبه کن", True)
        self.master_check.addItem("خیر", False)
        form.addRow("مهلت مادرِ بازمحاسبه:", self.master_check)
        if deadline is not None:
            self.master_check.setCurrentIndex(0 if deadline.is_master else 1)

        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("یادداشت اختیاری")
        form.addRow("یادداشت:", self.note_edit)
        if deadline is not None:
            self.note_edit.setText(deadline.note)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("ذخیره")
        buttons.button(QDialogButtonBox.Cancel).setText("انصراف")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _accept(self) -> None:
        try:
            target = parse_jalali_date(self.date_edit.text())
        except ValueError as exc:
            QMessageBox.warning(self, "تاریخ نامعتبر", str(exc))
            return
        if target is None:
            QMessageBox.warning(self, "تاریخ لازم است", "تاریخ مهلت را وارد کن.")
            return
        level = self.level_spin.value()
        self.result_deadline = TopicDeadline(
            id=self.deadline.id if self.deadline else None,
            topic_id=int(self.topic_combo.currentData()),
            kind=DeadlineKind(self.kind_combo.currentData()),
            target_date=target,
            target_track=TrackKind(self.track_combo.currentData()),
            target_percent=(
                self.percent_spin.value() if self.percent_spin.value() > 0 else None
            ),
            target_level=f"L{level}" if level > 0 else None,
            is_master=bool(self.master_check.currentData()),
            note=self.note_edit.text().strip(),
        )
        self.accept()


class DeadlinesPage(QWidget):
    """مهلت‌های من با بازمحاسبه و امکان‌سنجی."""

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
        title = QLabel("مهلت‌های من")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        btn_add = QPushButton("ثبت مهلت تازه")
        btn_add.setObjectName("primary")
        btn_add.clicked.connect(self._add)
        header.addWidget(btn_add)
        btn_plan = QPushButton("بازمحاسبهٔ مبحث انتخاب‌شده")
        btn_plan.clicked.connect(self._show_plan)
        header.addWidget(btn_plan)
        root.addLayout(header)

        self.summary = QLabel("—")
        self.summary.setObjectName("muted")
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)

        self.alert = warn_box()
        self.alert.setVisible(False)
        root.addWidget(self.alert)

        card = Card("مهلت‌های ثبت‌شده", tone="deadline")
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["مبحث", "نوع مهلت", "تاریخ", "هدف", "مسیر", "مادر", "وضعیت"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        card.add(self.table)
        root.addWidget(card, 1)

        self.detail = Card("بازمحاسبه و امکان‌سنجی", tone="deadline")
        self.detail_text = QLabel("یک مبحث را انتخاب کن.")
        self.detail_text.setWordWrap(True)
        self.detail_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.detail.add(self.detail_text)
        root.addWidget(self.detail)

        self.info = info_box()
        self.info.setText(
            "مهلت «تثبیت نهایی» مهلت مادر است: برنامه از آن روز به عقب برمی‌گردد "
            "و تاریخ شروع، پایان یادگیری اولیه و پایان تمرین را می‌سازد. اگر جمع "
            "زمان لازم بیشتر از ظرفیت واقعی‌ات باشد، برنامه هشدار می‌دهد و چهار "
            "پیشنهاد می‌کند — تصمیم با خودت است."
        )
        root.addWidget(self.info)

        self.table.itemSelectionChanged.connect(self._show_plan)

    def refresh(self) -> None:
        deadlines = self.service.list_topic_deadlines()
        plans = {p.topic_id: p for p in self.service.all_deadline_plans()}
        self.table.setRowCount(0)
        for deadline in deadlines:
            row = self.table.rowCount()
            self.table.insertRow(row)
            label = f"{deadline.subject_name} · {deadline.topic_name}".strip(" ·")
            topic_item = QTableWidgetItem(label or "—")
            topic_item.setData(Qt.UserRole, deadline.topic_id)
            self.table.setItem(row, 0, topic_item)
            self.table.setItem(row, 1, QTableWidgetItem(deadline.kind.label))
            self.table.setItem(
                row, 2,
                QTableWidgetItem(
                    format_jalali(deadline.target_date, with_weekday=False)
                    if deadline.target_date else "—"
                ),
            )
            target = "—"
            if deadline.target_percent is not None:
                target = f"{format_number(deadline.target_percent)}٪"
            elif deadline.target_level:
                target = str(deadline.target_level)
            self.table.setItem(row, 3, QTableWidgetItem(target))
            self.table.setItem(row, 4, QTableWidgetItem(deadline.target_track.label))
            self.table.setItem(row, 5, QTableWidgetItem("بله" if deadline.is_master else "خیر"))
            plan = plans.get(deadline.topic_id)
            status = "شدنی" if plan and plan.feasible else "در خطر"
            status_item = QTableWidgetItem(status)
            if not (plan and plan.feasible):
                from PySide6.QtGui import QColor

                status_item.setForeground(QColor("#b3541e"))
            self.table.setItem(row, 6, status_item)

        if deadlines:
            risky = [
                d for d in deadlines
                if not (plans.get(d.topic_id) and plans[d.topic_id].feasible)
            ]
            self.summary.setText(
                f"{len(deadlines)} مهلت ثبت شده است"
                + (f" — {len(risky)} مهلت با ظرفیت فعلی در خطر است." if risky else " — همه شدنی‌اند.")
            )
            self.alert.setVisible(bool(risky))
            if risky:
                self.alert.setText(
                    "مهلت‌های در خطر: "
                    + "؛ ".join(
                        f"{d.topic_name} ({d.kind.label})" for d in risky[:6]
                    )
                    + "\nبرای هر مبحث، پیشنهادهای زمان بیشتر/حجم کمتر/اولویت/جابه‌جایی "
                    "مهلت در بخش بازمحاسبه نشان داده می‌شود."
                )
        else:
            self.summary.setText("هنوز مهلتی ثبت نشده است.")
            self.alert.setVisible(False)

    def _selected_topic_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _add(self) -> None:
        if not self.service.list_topics():
            notify(self, "اول مبحث اضافه کن", "برای ثبت مهلت، حداقل یک مبحث لازم است.")
            return
        dialog = DeadlineDialog(self.service, None, self)
        if dialog.exec() != QDialog.Accepted:
            return
        deadline = getattr(dialog, "result_deadline", None)
        if deadline is None:
            return
        try:
            self.service.save_topic_deadline(deadline)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "ذخیره نشد", str(exc))
            return
        self.refresh()

    def _show_plan(self) -> None:
        topic_id = self._selected_topic_id()
        if topic_id is None:
            self.detail_text.setText("یک مبحث را از جدول انتخاب کن.")
            return
        try:
            plan = self.service.topic_deadline_plan(topic_id)
        except ValueError as exc:
            self.detail_text.setText(str(exc))
            return
        lines = [f"<b>{plan.topic_name}</b> — {plan.subject_name}", ""]
        lines.append(
            f"جمع زمان لازم: {format_number(plan.total_minutes)} دقیقه — "
            f"ظرفیت روزانهٔ مؤثر: {format_number(plan.capacity_minutes_per_day)} دقیقه"
        )
        lines.append("")
        for milestone in plan.milestones:
            lines.append(
                f"• {milestone.label}: "
                + (
                    format_jalali(milestone.date, with_weekday=False)
                    if milestone.date else "—"
                )
                + f" ({format_number(milestone.minutes)} دقیقه)"
            )
        lines.append("")
        lines.append(feasibility_message(plan))
        if plan.suggestions:
            lines.append("")
            lines.append("<b>پیشنهادها:</b>")
            for suggestion in plan.suggestions:
                extra = (
                    f" (اثر: حدود {suggestion.shift_days} روز)"
                    if suggestion.shift_days
                    else ""
                )
                lines.append(f"• {suggestion.title}{extra} — {suggestion.detail}")
        evidence = self.service.deadline_evidence_status(topic_id)
        lines.append("")
        lines.append(
            "<b>اثبات تکمیل:</b> "
            + ("تأییدشده با شاهد" if evidence["proven"] else "تأییدنشده")
            + f" — {evidence['reason']}"
        )
        self.detail_text.setText("<br>".join(lines))


__all__ = ["DeadlineDialog", "DeadlinesPage"]
