"""نمای مباحث: سنجش عملکردی، روش پیشنهادی و ساخت مسیر مطالعه."""

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

from ...advisor_engine import PHASE_LABELS
from ...domain.enums import ContentType, MasteryLevel
from ...domain.models import LearningEvidence, Topic
from ...jdate import format_jalali
from ...service import AdvisorService
from ..widgets import Card, info_box, notify

EVIDENCE_TYPES = (
    ("diagnostic", "آزمون تشخیصی"),
    ("delayed", "بازیابی تأخیری"),
    ("transfer", "سؤال تازه/انتقال"),
    ("mixed_exam", "آزمون ترکیبی"),
    ("review", "مرور فعال"),
)


class AddTopicDialog(QDialog):
    """افزودن هدف یادگیری واقعی؛ برنامه کتاب/مبحث را از کاربر می‌گیرد."""

    def __init__(self, service: AdvisorService, parent: QWidget | None = None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("افزودن مبحث یا مهارت")
        self.setLayoutDirection(Qt.RightToLeft)
        self.topic: Topic | None = None
        form = QFormLayout(self)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("عنوان مبحث/خروجی قابل سنجش؛ مثلاً حل معادلهٔ درجه‌دو")
        form.addRow("مبحث:", self.name_edit)
        self.subject_combo = QComboBox()
        subjects = service.selected_subjects()
        for subject in subjects:
            self.subject_combo.addItem(subject.name, subject.id)
        form.addRow("درس:", self.subject_combo)
        self.content_combo = QComboBox()
        for content_type in ContentType:
            self.content_combo.addItem(content_type.label, content_type.value)
        form.addRow("نوع محتوای مبحث:", self.content_combo)
        self.self_combo = QComboBox()
        self.self_combo.addItem("هنوز خودسنجی نشده", None)
        for value in range(5):
            self.self_combo.addItem(f"{value} از ۴", value)
        form.addRow("خودسنجی (شاهد ضعیف):", self.self_combo)
        self.notes = QLineEdit()
        self.notes.setPlaceholderText("پیش‌نیاز/منبع/یادداشت اختیاری؛ فصل رسمی را حدس نزنید")
        form.addRow("یادداشت:", self.notes)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText("ذخیرهٔ مبحث")
        self.buttons.button(QDialogButtonBox.Cancel).setText("انصراف")
        self.buttons.accepted.connect(self._accept)
        self.buttons.rejected.connect(self.reject)
        form.addRow(self.buttons)

    def _accept(self) -> None:
        name = self.name_edit.text().strip()
        subject_id = self.subject_combo.currentData()
        if not name:
            QMessageBox.warning(self, "عنوان لازم است", "نام مبحث یا مهارت را وارد کنید.")
            return
        if subject_id is None:
            QMessageBox.warning(self, "درس لازم است", "ابتدا در راه‌اندازی یک درس واقعی انتخاب کنید.")
            return
        self.topic = Topic(
            subject_id=int(subject_id),
            subject_name=self.subject_combo.currentText(),
            name=name,
            content_type=ContentType(self.content_combo.currentData()),
            self_assessed=self.self_combo.currentData(),
            notes=self.notes.text().strip(),
        )
        self.accept()


class AddEvidenceDialog(QDialog):
    """ثبت یک مشاهدهٔ قابل ردیابی برای مبحث؛ خودگزارش اطمینان از نمره جداست."""

    def __init__(self, topic: Topic, parent: QWidget | None = None):
        super().__init__(parent)
        self.topic = topic
        self.evidence: LearningEvidence | None = None
        self.setWindowTitle(f"ثبت سنجش — {topic.name}")
        self.setLayoutDirection(Qt.RightToLeft)
        form = QFormLayout(self)
        self.source_combo = QComboBox()
        for value, label in EVIDENCE_TYPES:
            self.source_combo.addItem(label, value)
        form.addRow("نوع سنجش:", self.source_combo)
        self.score = QDoubleSpinBox()
        self.score.setRange(0, 100)
        self.score.setDecimals(1)
        self.score.setSuffix("٪")
        self.score.setValue(0)
        form.addRow("درصد پاسخ درست:", self.score)
        self.count = QSpinBox()
        self.count.setRange(0, 500)
        self.count.setSpecialValueText("ثبت نشده")
        form.addRow("تعداد سؤال/آیتم:", self.count)
        self.confidence = QComboBox()
        for value, label in ((1, "۱ — حدس/اطمینان خیلی کم"), (2, "۲ — کم"), (3, "۳ — متوسط"), (4, "۴ — زیاد")):
            self.confidence.addItem(label, value)
        form.addRow("اطمینان پیش از بازخورد:", self.confidence)
        self.duration = QSpinBox()
        self.duration.setRange(0, 24 * 60 * 60)
        self.duration.setSpecialValueText("ثبت نشده")
        self.duration.setSuffix(" ثانیه")
        form.addRow("زمان پاسخ‌گویی:", self.duration)
        self.date_edit = QLineEdit(format_jalali(_dt.date.today(), with_weekday=False))
        self.date_edit.setPlaceholderText("۱۴۰۵/۰۷/۲۵")
        form.addRow("تاریخ سنجش (شمسی):", self.date_edit)
        self.note = QLineEdit()
        self.note.setPlaceholderText("منبع آزمون/توضیح اختیاری")
        form.addRow("یادداشت:", self.note)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText("ثبت شاهد")
        self.buttons.button(QDialogButtonBox.Cancel).setText("انصراف")
        self.buttons.accepted.connect(self._accept)
        self.buttons.rejected.connect(self.reject)
        form.addRow(self.buttons)

    def _accept(self) -> None:
        from ...jdate import parse_jalali_date

        try:
            observed_on = parse_jalali_date(self.date_edit.text())
        except ValueError as exc:
            QMessageBox.warning(self, "تاریخ نامعتبر", str(exc))
            return
        self.evidence = LearningEvidence(
            topic_id=self.topic.id,
            observed_on=observed_on,
            source=str(self.source_combo.currentData()),
            score=self.score.value() / 100.0,
            item_count=self.count.value(),
            confidence=int(self.confidence.currentData()),
            duration_seconds=self.duration.value() or None,
            note=self.note.text().strip(),
        )
        self.accept()


class TopicsPage(QWidget):
    """مدیریت مباحث/مهارت‌ها و چرخهٔ سنجش و توصیه."""

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
        title = QLabel("مباحث، تسلط و روش یادگیری")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        self.btn_add = QPushButton("افزودن مبحث")
        self.btn_add.setObjectName("primary")
        self.btn_add.clicked.connect(self._add_topic)
        header.addWidget(self.btn_add)
        self.btn_seed = QPushButton("ساخت از کاتالوگ")
        self.btn_seed.setToolTip(
            "مباحث همهٔ درس‌های انتخاب‌شده را از کاتالوگ [H] می‌سازد؛ "
            "این فهرست ادعای دامنهٔ رسمی آزمون نیست و باید تأیید کنید."
        )
        self.btn_seed.clicked.connect(self._seed_from_catalog)
        header.addWidget(self.btn_seed)
        root.addLayout(header)

        self.info = info_box()
        self.info.setText(
            "مبحث را به‌صورت خروجی قابل سنجش ثبت کنید. دکمهٔ «ساخت از کاتالوگ» "
            "فهرست مبحثی فرضیه‌محور [H] هر درس را می‌سازد؛ آن را تأیید، حذف یا "
            "ویرایش کنید. L4 عملیاتی است و حافظه یا نتیجهٔ آزمون را تضمین نمی‌کند."
        )
        root.addWidget(self.info)

        card = Card("نقشهٔ یادگیری شخصی", tone="study")
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["مبحث/مهارت", "درس", "نوع محتوا", "وضعیت عملکردی", "جلسه‌های جدا", "آخرین شاهد"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        card.add(self.table)
        root.addWidget(card, 1)

        actions = QHBoxLayout()
        self.btn_evidence = QPushButton("ثبت آزمون/بازیابی")
        self.btn_evidence.clicked.connect(self._add_evidence)
        self.btn_pathway = QPushButton("ساخت مسیر پیشنهادی")
        self.btn_pathway.setObjectName("primary")
        self.btn_pathway.clicked.connect(self._generate_pathway)
        self.btn_explain = QPushButton("چرا این روش؟")
        self.btn_explain.clicked.connect(self._explain)
        for button in (self.btn_evidence, self.btn_pathway, self.btn_explain):
            actions.addWidget(button)
        actions.addStretch(1)
        root.addLayout(actions)
        self.method_card = Card("روش‌های پیشنهادی برای مبحث انتخاب‌شده", tone="study")
        self.method_label = QLabel("یک مبحث را انتخاب کنید تا شواهد و روش‌ها دیده شود.")
        self.method_label.setWordWrap(True)
        self.method_card.add(self.method_label)
        root.addWidget(self.method_card)

    def _selected_topic(self) -> Topic | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        topic_id = item.data(Qt.UserRole) if item else None
        return next((t for t in self.service.list_topics() if t.id == topic_id), None)

    def _seed_from_catalog(self) -> None:
        """ساخت مبحث برای همهٔ درس‌های انتخاب‌شده از کاتالوگ فرضیه‌محور."""
        from ..widgets import notify

        subjects = self.service.selected_subjects()
        if not subjects:
            notify(self, "درسی ثبت نشده", "ابتدا در راه‌اندازی درس‌ها را انتخاب کنید.")
            return
        created_total = 0
        missing: list[str] = []
        for subject in subjects:
            if subject.id is None:
                continue
            try:
                created = self.service.seed_topics_from_catalog(subject.id)
            except Exception as exc:  # noqa: BLE001
                notify(self, "ساخت مباحث ناموفق", str(exc))
                return
            created_total += len(created)
            if not created:
                missing.append(subject.name)
        message = f"{created_total} مبحث از کاتالوگ ساخته شد."
        if missing:
            message += (
                "\n\nبرای این درس‌ها مبحثی در کاتالوگ نبود یا همه از قبل ثبت شده‌اند: "
                + "، ".join(missing)
                + "."
            )
        notify(self, "ساخت از کاتالوگ", message)
        self.refresh()

    def refresh(self) -> None:
        topics = self.service.list_topics()
        self.table.setRowCount(0)
        for topic in topics:
            assessment = self.service.assess_topic(int(topic.id))
            evidence = self.service.list_learning_evidence(topic.id)
            row = self.table.rowCount()
            self.table.insertRow(row)
            name = QTableWidgetItem(topic.name)
            name.setData(Qt.UserRole, topic.id)
            self.table.setItem(row, 0, name)
            self.table.setItem(row, 1, QTableWidgetItem(topic.subject_name or "—"))
            self.table.setItem(row, 2, QTableWidgetItem(topic.content_type.label))
            self.table.setItem(row, 3, QTableWidgetItem(assessment.label))
            self.table.setItem(row, 4, QTableWidgetItem(str(assessment.distinct_sessions)))
            last = evidence[-1].observed_on if evidence else None
            self.table.setItem(
                row, 5,
                QTableWidgetItem(format_jalali(last, with_weekday=False) if last else "شاهدی ثبت نشده"),
            )
        selected = self._selected_topic()
        self.btn_evidence.setEnabled(bool(selected))
        self.btn_pathway.setEnabled(bool(selected))
        self.btn_explain.setEnabled(bool(selected))
        if selected:
            self._show_methods(selected)
        elif not topics:
            self.method_label.setText("هنوز مبحثی ثبت نشده است؛ با یک مبحث واقعی شروع کنید.")

    def _add_topic(self) -> None:
        dialog = AddTopicDialog(self.service, self)
        if dialog.exec() == QDialog.Accepted and dialog.topic:
            try:
                self.service.create_topic(dialog.topic)
            except Exception as exc:  # noqa: BLE001
                QMessageBox.warning(self, "ذخیره نشد", str(exc))
                return
            self.refresh()

    def _add_evidence(self) -> None:
        topic = self._selected_topic()
        if topic is None:
            notify(self, "انتخاب مبحث", "ابتدا یک مبحث را انتخاب کنید.")
            return
        dialog = AddEvidenceDialog(topic, self)
        if dialog.exec() != QDialog.Accepted or not dialog.evidence:
            return
        try:
            assessment = self.service.record_learning_evidence(dialog.evidence)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "ثبت نشد", str(exc))
            return
        notify(
            self,
            "سنجش ذخیره شد",
            f"وضعیت فعلی: {assessment.label} · این معیار عملکردی است، نه تضمین تثبیت.",
        )
        self.refresh()

    def _show_methods(self, topic: Topic) -> None:
        assessment, prescription = self.service.recommend_topic(int(topic.id))
        lines = [
            f"وضعیت عملکردی: {assessment.label} (اطمینان الگوریتمی {assessment.confidence:.0%})",
            *[f"• {reason}" for reason in assessment.reasons],
            f"فاز زمانی: {PHASE_LABELS[prescription.phase]} · نوع محتوا: {topic.content_type.label}",
            "روش‌های آغازین (با عملکرد بعدی اصلاح شوند):",
            *[f"• {method}" for method in prescription.methods],
        ]
        self.method_label.setText("\n".join(lines))

    def _selection_changed(self) -> None:
        topic = self._selected_topic()
        if topic:
            self._show_methods(topic)
        self.btn_evidence.setEnabled(bool(topic))
        self.btn_pathway.setEnabled(bool(topic))
        self.btn_explain.setEnabled(bool(topic))

    def _explain(self) -> None:
        topic = self._selected_topic()
        if topic:
            self._show_methods(topic)

    def _generate_pathway(self) -> None:
        topic = self._selected_topic()
        if topic is None:
            return
        try:
            created = self.service.generate_topic_pathway(int(topic.id))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "مسیر ساخته نشد", str(exc))
            return
        if created:
            notify(self, "مسیر آماده شد", f"{len(created)} فعالیت به صف زمان‌بندی اضافه شد.")
        else:
            notify(self, "فعالیت تکراری ساخته نشد", "برای این مرحله فعالیت باز/تکمیل‌شده وجود دارد.")
