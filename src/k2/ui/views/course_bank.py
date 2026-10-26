"""نمای «بانک دروس»: درس‌ها، مباحث، مسیر دوگانه و فاکتورهای اولویت (بند ۱۷).

این صفحه جای «مباحث و تسلط»ی قدیمی را می‌گیرد و علاوه بر سنجش تسلط،
پلهٔ هر مبحث در هر دو مسیر (کنکور/نهایی) و فاکتورهای اولویتی را نشان
می‌دهد: پیش‌نیاز بودن، سهم آزمون نهایی، ضعف ثبت‌شده و مهلت اختصاصی.
"""

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

from ...domain.enums import (
    ContentType,
    FinalStage,
    KonkurStage,
    MasteryLevel,
    TrackKind,
)
from ...domain.models import LearningEvidence, Topic
from ...jdate import format_jalali, format_number
from ...service import AdvisorService
from ..widgets import Card, info_box, notify

EVIDENCE_TYPES = (
    ("diagnostic", "آزمون تشخیصی"),
    ("delayed", "بازیابی تأخیری"),
    ("transfer", "سؤال تازه/انتقال"),
    ("mixed_exam", "آزمون ترکیبی"),
    ("review", "مرور فعال"),
    ("teaching_test", "تست تدریس"),
    ("timed_test", "تست زمان‌دار"),
    ("option_analysis", "تحلیل گزینه‌ها"),
    ("error_review", "مرور خطاها"),
    ("descriptive_practice", "تمرین تشریحی"),
    ("sample_questions", "سؤال نمونهٔ معتبر"),
    ("completeness_check", "بررسی کامل‌بودن"),
    ("mock_final", "آزمون جامع نهایی"),
)

KONKUR_STAGES = [
    (KonkurStage.CONCEPTUAL, "مطالعهٔ مفهومی"),
    (KonkurStage.TEACHING_TEST, "تست تدریس"),
    (KonkurStage.TIMED_TEST, "تست زمان‌دار"),
    (KonkurStage.OPTION_ANALYSIS, "تحلیل گزینه‌ها"),
    (KonkurStage.ERROR_REVIEW, "مرور خطاها"),
    (KonkurStage.MIXED_EXAM, "آزمون ترکیبی"),
]

FINAL_STAGES = [
    (FinalStage.TEXTBOOK_STUDY, "مطالعهٔ دقیق کتاب"),
    (FinalStage.DEFINITIONS, "تعریف‌ها و روابط"),
    (FinalStage.DETAIL_MAP, "جزئیات و نقشهٔ محتوا"),
    (FinalStage.DESCRIPTIVE_PRACTICE, "تمرین تشریحی"),
    (FinalStage.SAMPLE_QUESTIONS, "سؤال‌های نمونهٔ معتبر"),
    (FinalStage.COMPLETENESS_CHECK, "بررسی کامل‌بودن و نشانه‌گذاری"),
    (FinalStage.MOCK_FINAL, "آزمون جامع نهایی"),
]


class AddTopicDialog(QDialog):
    """افزودن مبحث با فاکتورهای اولویتی."""

    def __init__(self, service: AdvisorService, parent: QWidget | None = None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("افزودن مبحث")
        self.setLayoutDirection(Qt.RightToLeft)
        # حداقل پهنا برای اینکه برچسب‌های فارسی و فهرست‌های کشویی بریده نشوند.
        self.setMinimumWidth(520)
        self.topic: Topic | None = None
        form = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("عنوان مبحث یا خروجی قابل سنجش")
        form.addRow("مبحث:", self.name_edit)

        self.subject_combo = QComboBox()
        for subject in service.selected_subjects():
            self.subject_combo.addItem(subject.name, subject.id)
        form.addRow("درس:", self.subject_combo)

        self.content_combo = QComboBox()
        for content in ContentType:
            self.content_combo.addItem(content.label, content.value)
        form.addRow("نوع محتوا:", self.content_combo)

        self.prereq_spin = QDoubleSpinBox()
        self.prereq_spin.setRange(0, 1)
        self.prereq_spin.setSingleStep(0.1)
        self.prereq_spin.setValue(0.0)
        self.prereq_spin.setToolTip("این مبحث پیش‌نیاز چند مبحث دیگر است؟")
        form.addRow("پیش‌نیاز بودن (۰..۱):", self.prereq_spin)

        self.final_share_spin = QDoubleSpinBox()
        self.final_share_spin.setRange(0, 1)
        self.final_share_spin.setSingleStep(0.1)
        self.final_share_spin.setValue(0.0)
        self.final_share_spin.setToolTip("سهم لازم در سؤال‌های تشریحی نهایی")
        form.addRow("سهم آزمون نهایی (۰..۱):", self.final_share_spin)

        self.estimate_spin = QSpinBox()
        self.estimate_spin.setRange(0, 5000)
        self.estimate_spin.setSingleStep(15)
        self.estimate_spin.setSuffix(" دقیقه")
        self.estimate_spin.setToolTip("برآورد زمان تکمیل هر دو مسیر")
        form.addRow("برآورد زمان:", self.estimate_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("ذخیرهٔ مبحث")
        buttons.button(QDialogButtonBox.Cancel).setText("انصراف")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "عنوان لازم است", "عنوان مبحث را وارد کن.")
            return
        self.topic = Topic(
            subject_id=self.subject_combo.currentData(),
            name=name,
            content_type=ContentType(self.content_combo.currentData()),
            prerequisite_share=self.prereq_spin.value(),
            final_exam_share=self.final_share_spin.value(),
            estimated_minutes=self.estimate_spin.value() or None,
        )
        self.accept()


class CourseBankPage(QWidget):
    """بانک دروس: درس‌ها، مباحث، مسیر دوگانه و فاکتورهای اولویت."""

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
        title = QLabel("بانک دروس")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        btn_add = QPushButton("افزودن مبحث")
        btn_add.setObjectName("primary")
        btn_add.clicked.connect(self._add_topic)
        header.addWidget(btn_add)
        btn_seed = QPushButton("ساخت از کاتالوگ")
        btn_seed.setToolTip(
            "فهرست مبحثی هر درس را از کاتالوگ [H] می‌سازد؛ خودت تأیید یا حذف کن."
        )
        btn_seed.clicked.connect(self._seed)
        header.addWidget(btn_seed)
        btn_evidence = QPushButton("ثبت شاهد عملکرد")
        btn_evidence.setToolTip(
            "شاهد (سنجش/تست/تمرین) ثبت کن تا پلهٔ مسیرها جلو برود"
        )
        btn_evidence.clicked.connect(self._add_evidence)
        header.addWidget(btn_evidence)
        root.addLayout(header)

        self.summary = QLabel("—")
        self.summary.setObjectName("muted")
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)

        self.alert = info_box()
        self.alert.setVisible(False)
        root.addWidget(self.alert)

        card = Card("مباحث ثبت‌شده", tone="study")
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            [
                "مبحث", "تسلط", "مسیر کنکور", "مسیر نهایی",
                "پیش‌نیاز", "سهم نهایی", "برآورد", "مهلت",
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        card.add(self.table)
        root.addWidget(card, 1)

        self.detail = Card("جزئیات مبحث انتخاب‌شده", tone="study")
        self.detail_text = QLabel("یک مبحث را انتخاب کن.")
        self.detail_text.setWordWrap(True)
        self.detail_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.detail.add(self.detail_text)
        root.addWidget(self.detail)

        self.info = info_box()
        self.info.setText(
            "هر مبحث دو مسیر مستقل دارد: کنکور (مفهومی → تست تدریس → تست "
            "زمان‌دار → تحلیل گزینه‌ها → مرور خطاها → آزمون ترکیبی) و نهایی "
            "(مطالعهٔ دقیق کتاب → تعریف‌ها → جزئیات → تمرین تشریحی → سؤال "
            "نمونهٔ معتبر → بررسی کامل‌بودن → آزمون جامع). هیچ‌کدام جای دیگری "
            "را نمی‌گیرد و هر پیشرفت نیازمند شاهد است."
        )
        root.addWidget(self.info)

        self.table.itemSelectionChanged.connect(self._show_detail)

    def refresh(self) -> None:
        topics = self.service.list_topics()
        evidences = self.service.repo.list_learning_evidence()
        deadlines = self.service.list_topic_deadlines()
        deadline_by_topic: dict[int, object] = {}
        for deadline in deadlines:
            if deadline.is_master and deadline.target_date:
                deadline_by_topic[deadline.topic_id] = deadline

        self.table.setRowCount(0)
        for topic in topics:
            row = self.table.rowCount()
            self.table.insertRow(row)
            id_item = QTableWidgetItem(f"{topic.subject_name} · {topic.name}")
            id_item.setData(Qt.UserRole, topic.id)
            self.table.setItem(row, 0, id_item)
            self.table.setItem(row, 1, QTableWidgetItem(topic.mastery.label))
            view = self.service.topic_dual_track(topic.id)
            self.table.setItem(row, 2, QTableWidgetItem(view.konkur.stage_label))
            self.table.setItem(row, 3, QTableWidgetItem(view.final.stage_label))
            self.table.setItem(
                row, 4, QTableWidgetItem(format_number(topic.prerequisite_share, digits=1))
            )
            self.table.setItem(
                row, 5, QTableWidgetItem(format_number(topic.final_exam_share, digits=1))
            )
            self.table.setItem(
                row, 6,
                QTableWidgetItem(
                    f"{format_number(topic.estimated_minutes)} دقیقه"
                    if topic.estimated_minutes else "—"
                ),
            )
            deadline = deadline_by_topic.get(topic.id)
            self.table.setItem(
                row, 7,
                QTableWidgetItem(
                    format_jalali(deadline.target_date, with_weekday=False)
                    if deadline is not None else "—"
                ),
            )

        if topics:
            missing = [
                t for t in topics
                if not self.service.topic_dual_track(t.id).konkur.evidence_ready
            ]
            self.summary.setText(
                f"{len(topics)} مبحث ثبت شده — {len(missing)} مبحث شاهد تأیید "
                "پلهٔ فعلی مسیر کنکور را ندارد."
            )
        else:
            self.summary.setText("هنوز مبحثی ثبت نشده است.")

        self._show_detail()

    def _selected_topic_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _show_detail(self) -> None:
        topic_id = self._selected_topic_id()
        if topic_id is None:
            self.detail_text.setText("یک مبحث را از جدول انتخاب کن.")
            return
        topic = next(
            (t for t in self.service.list_topics() if t.id == topic_id), None
        )
        if topic is None:
            return
        view = self.service.topic_dual_track(topic_id)
        lines = [f"<b>{topic.subject_name} · {topic.name}</b>", ""]
        lines.append(f"تسلط: {topic.mastery.label} — نوع محتوا: {topic.content_type.label}")
        lines.append(
            f"پیش‌نیاز بودن: {format_number(topic.prerequisite_share, digits=1)} — "
            f"سهم آزمون نهایی: {format_number(topic.final_exam_share, digits=1)}"
        )
        if topic.estimated_minutes:
            lines.append(f"برآورد زمان: {format_number(topic.estimated_minutes)} دقیقه")
        for progress in (view.konkur, view.final):
            lines.append("")
            lines.append(
                f"<b>{progress.track.label}</b>: {progress.stage_label} "
                f"({progress.ladder_text}) — پیشرفت {format_number(progress.progress_percent, digits=1)}٪"
            )
            if progress.next_stage_label:
                lines.append(f"پلهٔ بعدی: {progress.next_stage_label}")
            if progress.missing_evidence:
                lines.append(f"نیازمند: {progress.missing_evidence}")
            if progress.evidence_count:
                lines.append(f"شواهد تأییدکننده: {progress.evidence_count}")
        for warning in view.warnings:
            lines.append("")
            lines.append(f"هشدار: {warning}")
        self.detail_text.setText("<br>".join(lines))

    def _add_topic(self) -> None:
        if not self.service.selected_subjects():
            notify(self, "اول درس اضافه کن", "برای ثبت مبحث، حداقل یک درس لازم است.")
            return
        dialog = AddTopicDialog(self.service, self)
        if dialog.exec() != QDialog.Accepted or dialog.topic is None:
            return
        try:
            self.service.create_topic(dialog.topic)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "ذخیره نشد", str(exc))
            return
        self.refresh()

    def _seed(self) -> None:
        subjects = self.service.selected_subjects()
        if not subjects:
            notify(self, "اول درس اضافه کن", "برای ساخت از کاتالوگ، درس لازم است.")
            return
        created = 0
        for subject in subjects:
            try:
                created += len(self.service.seed_topics_from_catalog(subject.id))
            except Exception:  # noqa: BLE001
                continue
        notify(
            self,
            "کاتالوگ",
            f"{created} مبحث از کاتالوگ ساخته شد؛ موارد بی‌ربط را حذف کن.",
        )
        self.refresh()

    def _add_evidence(self) -> None:
        topic_id = self._selected_topic_id()
        if topic_id is None:
            notify(self, "انتخاب نشده", "اول یک مبحث را انتخاب کن.")
            return
        dialog = EvidenceDialog(self.service, topic_id, self)
        if dialog.exec() != QDialog.Accepted:
            return
        track = dialog.result_track
        evidence = dialog.result_evidence
        if track is None or evidence is None:
            return
        try:
            changed, message = self.service.record_track_evidence(
                topic_id, track, evidence
            )
        except ValueError as exc:
            QMessageBox.warning(self, "ثبت نشد", str(exc))
            return
        notify(
            self,
            "شاهد ثبت شد",
            message + ("\nپلهٔ مسیر جلو رفت." if changed else ""),
        )
        self.refresh()


class EvidenceDialog(QDialog):
    """ثبت یک شاهد عملکردی برای یک مبحث."""

    def __init__(
        self, service: AdvisorService, topic_id: int, parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.service = service
        self.topic_id = topic_id
        self.setWindowTitle("ثبت شاهد عملکرد")
        self.setLayoutDirection(Qt.RightToLeft)
        # حداقل پهنا برای اینکه برچسب‌های فارسی و فهرست‌های کشویی بریده نشوند.
        self.setMinimumWidth(520)
        self.result_track: TrackKind | None = None
        self.result_evidence: LearningEvidence | None = None
        form = QFormLayout(self)

        self.track_combo = QComboBox()
        self.track_combo.addItem("مسیر کنکور", TrackKind.KONKUR.value)
        self.track_combo.addItem("مسیر نهایی/مدرک", TrackKind.FINAL.value)
        form.addRow("مسیر:", self.track_combo)
        self.track_combo.currentIndexChanged.connect(self._on_track)

        self.source_combo = QComboBox()
        form.addRow("نوع شاهد:", self.source_combo)

        self.score_spin = QDoubleSpinBox()
        self.score_spin.setRange(0, 1)
        self.score_spin.setSingleStep(0.05)
        self.score_spin.setValue(0.8)
        form.addRow("نمره (۰..۱):", self.score_spin)

        self.items_spin = QSpinBox()
        self.items_spin.setRange(0, 500)
        form.addRow("تعداد سؤال/مورد:", self.items_spin)

        self.confidence_spin = QSpinBox()
        self.confidence_spin.setRange(1, 4)
        form.addRow("اطمینان خودگزارشی (۱–۴):", self.confidence_spin)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(0, 600)
        self.duration_spin.setSuffix(" دقیقه")
        form.addRow("مدت:", self.duration_spin)

        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("یادداشت اختیاری")
        form.addRow("یادداشت:", self.note_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("ذخیره")
        buttons.button(QDialogButtonBox.Cancel).setText("انصراف")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        self._on_track()

    def _on_track(self) -> None:
        track = self.track_combo.currentData()
        stages = KONKUR_STAGES if track == TrackKind.KONKUR else FINAL_STAGES
        self.source_combo.clear()
        if track == TrackKind.KONKUR:
            self.source_combo.addItem("آزمون تشخیصی/سنجش اولیه", "diagnostic")
        else:
            self.source_combo.addItem("سنجش اولیه مطالعهٔ کتاب", "diagnostic")
        for stage, label in stages:
            self.source_combo.addItem(label, stage.value)
        for value, label in EVIDENCE_TYPES:
            if value != "diagnostic":
                self.source_combo.addItem(f"سایر: {label}", value)

    def _accept(self) -> None:
        self.result_track = TrackKind(self.track_combo.currentData())
        self.result_evidence = LearningEvidence(
            topic_id=self.topic_id,
            observed_on=_dt.date.today(),
            source=str(self.source_combo.currentData()),
            score=self.score_spin.value(),
            item_count=self.items_spin.value(),
            confidence=self.confidence_spin.value(),
            duration_seconds=self.duration_spin.value() * 60 or None,
            note=self.note_edit.text().strip(),
        )
        self.accept()


__all__ = ["AddTopicDialog", "CourseBankPage", "EvidenceDialog"]
