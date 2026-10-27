"""نمای «سرفصل درس‌ها»: فصل و گفتار رسمی، وضعیت مطالعه و اثر آن بر برنامه.

این صفحه جای «تایپ کردن دستی فصل‌ها» را می‌گیرد: فصل‌ها و گفتارها از
کاتالوگ کتاب درسی می‌آیند و کاربر فقط وضعیت هر گفتار را ثبت می‌کند.
هر گفتار یک شناسهٔ پایدار ``درس|پایه|فصل|گفتار`` دارد تا وضعیت، تست، مرور
و برنامه به همان گفتار بچسبد و با بازچینانی کتاب از بین نرود.
"""

from __future__ import annotations

import datetime as _dt
from typing import Optional

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

from ... import syllabus as syl
from ...chapter_goal import ChapterGoalInput, plan_chapter_goal
from ...domain.models import SyllabusChapterEdit, SyllabusSection
from ...jdate import (
    format_jalali,
    format_minutes,
    format_number,
    parse_jalali_date,
    persian_digits,
)
from ...service import AdvisorService
from ..widgets import Card, confirm, info_box, notify


class _SectionDialog(QDialog):
    """فرم هشت‌سؤالی وضعیت یک گفتار."""

    def __init__(
        self,
        service: AdvisorService,
        subject: str,
        grade: int,
        chapter,
        section,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.service = service
        self.subject = subject
        self.grade = grade
        self.chapter = chapter
        self.section = section
        self.setWindowTitle(f"وضعیت گفتار · {section.label}")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(560)
        root = QVBoxLayout(self)
        root.setSpacing(8)

        head = QLabel(
            f"<b>{subject}</b> · پایهٔ {grade} · فصل {chapter.no} "
            f"({chapter.title}) · گفتار {section.no}<br>"
            f"<span style='color:#6b7280'>نام رسمی: {section.official_title or 'ثبت نشده'}</span>"
        )
        head.setWordWrap(True)
        root.addWidget(head)

        note = info_box()
        note.setText(
            "این هشت سؤال وضعیت واقعی این گفتار را ثبت می‌کنند. پاسخ‌ها مستقیماً "
            "وارد برنامهٔ روزانه و هفتگی می‌شوند؛ گفتاری که نیاز باز دارد حذف "
            "نمی‌شود، جبران می‌شود."
        )
        root.addWidget(note)

        self.combos: dict[str, QComboBox] = {}
        record = section.record
        for question in syl.ASSESS_QUESTIONS:
            box = QHBoxLayout()
            label = QLabel(f"{question['title']}\n{question['hint']}")
            label.setWordWrap(True)
            label.setMinimumWidth(240)
            box.addWidget(label, 1)
            combo = QComboBox()
            combo.addItem("— انتخاب نشده —", None)
            for value, text in question["options"]:
                combo.addItem(text, value)
            current = getattr(record, question["key"], None) if record else None
            if current:
                index = combo.findData(current)
                if index >= 0:
                    combo.setCurrentIndex(index)
            box.addWidget(combo, 2)
            root.addLayout(box)
            self.combos[question["key"]] = combo

        mastery_row = QHBoxLayout()
        mastery_row.addWidget(QLabel("تسلط خوداظهاری (٪):"))
        self.mastery = QSpinBox()
        self.mastery.setRange(0, 100)
        self.mastery.setSuffix(" ٪")
        self.mastery.setSpecialValueText("نامشخص")
        if record and record.mastery is not None:
            self.mastery.setValue(int(record.mastery))
        else:
            self.mastery.setValue(0)
        mastery_row.addWidget(self.mastery)
        mastery_row.addStretch(1)
        root.addLayout(mastery_row)

        self.notes = QLineEdit(record.notes if record else "")
        self.notes.setPlaceholderText("یادداشت اختیاری؛ مثلاً «فصل ۳ پیش‌نیاز این گفتار است»")
        root.addWidget(self.notes)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("ذخیرهٔ وضعیت")
        buttons.button(QDialogButtonBox.Cancel).setText("انصراف")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _accept(self) -> None:
        answers = {key: combo.currentData() for key, combo in self.combos.items()}
        if not any(answers.values()):
            QMessageBox.warning(
                self,
                "پاسخی ثبت نشده",
                "حداقل به یکی از هشت سؤال پاسخ بده. اگر مطمئن نیستی "
                "«نمی‌دانم / نیاز به ارزیابی» را انتخاب کن.",
            )
            return
        self.answers = answers
        self.mastery_value = self.mastery.value() if self.mastery.value() else None
        self.notes_value = self.notes.text().strip()
        self.accept()

    # مقادیر پس از accept خوانده می‌شوند
    answers: dict = {}
    mastery_value: Optional[float] = None
    notes_value: str = ""

    def values(self) -> tuple[dict, Optional[float], str]:
        return self.answers, self.mastery_value, self.notes_value


class SyllabusPage(QWidget):
    """صفحهٔ سرفصل: فصل‌ها، گفتارها و وضعیت هر گفتار."""

    def __init__(self, service: AdvisorService, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.service = service
        self._build()
        self.refresh()

    # ------------------------------------------------------------------ UI

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("سرفصل درس‌ها: فصل و گفتار")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        self.btn_counts = QPushButton("ورود تعداد گفتارها")
        self.btn_counts.setToolTip(
            "تعداد گفتار فصل‌هایی که نام رسمی ندارند را از روی کتاب سال ۱۴۰۶ "
            "خودت وارد کن. خالی گذاشتن یعنی «نامشخص» — برنامه هیچ عددی حدس نمی‌زند."
        )
        self.btn_counts.clicked.connect(self._enter_counts)
        header.addWidget(self.btn_counts)
        self.btn_goal = QPushButton("هدف این فصل تا تاریخ…")
        self.btn_goal.setObjectName("primary")
        self.btn_goal.setToolTip(
            "بگو تا چه تاریخی می‌خواهی این فصل تمام شود؛ برنامه می‌گوید شدنی "
            "است یا نه و از چه روزی باید شروع کنی."
        )
        self.btn_goal.clicked.connect(self._chapter_goal)
        header.addWidget(self.btn_goal)
        self.btn_needs = QPushButton("نیازهای باز سرفصل")
        self.btn_needs.setToolTip("گفتارهایی که نیاز باز دارند؛ ورودی مستقیم برنامه‌ریزی")
        self.btn_needs.clicked.connect(self._show_needs)
        header.addWidget(self.btn_needs)
        root.addLayout(header)

        self.info = info_box()
        self.info.setText(
            "فصل‌ها و گفتارها از کتاب درسی می‌آیند و لازم نیست دستی تایپ شوند. "
            "هر گفتار شناسهٔ پایدار دارد، پس وضعیت، تست و مرور به همان گفتار "
            "می‌چسبد. نامی که در کتاب نیست ساخته نمی‌شود؛ آن گفتار «نام ثبت "
            "نشده» علامت می‌خورد و خودت تغییرش می‌دهی."
        )
        root.addWidget(self.info)

        picker = QHBoxLayout()
        picker.addWidget(QLabel("درس:"))
        self.subject_combo = QComboBox()
        self.subject_combo.currentIndexChanged.connect(self._subject_changed)
        picker.addWidget(self.subject_combo, 1)
        picker.addWidget(QLabel("پایه:"))
        self.grade_combo = QComboBox()
        self.grade_combo.currentIndexChanged.connect(self.refresh)
        picker.addWidget(self.grade_combo)
        picker.addStretch(1)
        self.coverage = QLabel("")
        self.coverage.setObjectName("muted")
        picker.addWidget(self.coverage)
        root.addLayout(picker)

        chapters_card = Card("فصل‌ها", tone="study")
        self.chapter_table = QTableWidget(0, 5)
        self.chapter_table.setHorizontalHeaderLabels(
            ["#", "عنوان فصل", "تعداد گفتار", "گفتار ارزیابی‌شده", "نیاز باز"]
        )
        self.chapter_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.chapter_table.verticalHeader().setVisible(False)
        self.chapter_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.chapter_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.chapter_table.itemSelectionChanged.connect(self._chapter_selected)
        chapters_card.add(self.chapter_table)
        root.addWidget(chapters_card, 1)

        sections_card = Card("گفتارهای فصل انتخاب‌شده", tone="study")
        self.section_table = QTableWidget(0, 6)
        self.section_table.setHorizontalHeaderLabels(
            ["#", "نام گفتار", "پاسخ‌ها", "تسلط", "وضعیت", "نیازهای باز"]
        )
        self.section_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.section_table.verticalHeader().setVisible(False)
        self.section_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.section_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.section_table.itemSelectionChanged.connect(self._section_selected)
        sections_card.add(self.section_table)
        root.addWidget(sections_card, 2)

        actions = QHBoxLayout()
        self.btn_assess = QPushButton("ثبت/ویرایش وضعیت گفتار")
        self.btn_assess.setObjectName("primary")
        self.btn_assess.clicked.connect(self._assess_section)
        self.btn_rename = QPushButton("تغییر نام گفتار")
        self.btn_rename.clicked.connect(self._rename_section)
        self.btn_delete = QPushButton("حذف گفتار")
        self.btn_delete.clicked.connect(self._delete_section)
        self.btn_rename_chapter = QPushButton("تغییر نام فصل")
        self.btn_rename_chapter.clicked.connect(self._rename_chapter)
        for button in (
            self.btn_assess,
            self.btn_rename,
            self.btn_delete,
            self.btn_rename_chapter,
        ):
            actions.addWidget(button)
        actions.addStretch(1)
        root.addLayout(actions)

    # -------------------------------------------------------------- helpers

    def _current_subject(self) -> str:
        return str(self.subject_combo.currentData() or "")

    def _current_grade(self) -> int:
        return int(self.grade_combo.currentData() or 0)

    def _selected_chapter(self):
        row = self.chapter_table.currentRow()
        if row < 0:
            return None
        item = self.chapter_table.item(row, 0)
        chapter_no = item.data(Qt.UserRole) if item else None
        return next(
            (c for c in self._chapters if c.no == chapter_no),
            None,
        )

    def _selected_section(self):
        row = self.section_table.currentRow()
        if row < 0:
            return None
        item = self.section_table.item(row, 0)
        section_no = item.data(Qt.UserRole) if item else None
        return next(
            (s for s in self._sections if s.no == section_no),
            None,
        )

    # ------------------------------------------------------------- refresh

    def refresh(self) -> None:
        current_subject = self._current_subject()
        current_grade = self._current_grade()
        self.subject_combo.blockSignals(True)
        self.subject_combo.clear()
        for name in self.service.syllabus_courses():
            self.subject_combo.addItem(name, name)
        if current_subject:
            index = self.subject_combo.findData(current_subject)
            if index >= 0:
                self.subject_combo.setCurrentIndex(index)
        self.subject_combo.blockSignals(False)

        self.grade_combo.blockSignals(True)
        self.grade_combo.clear()
        for grade in self.service.syllabus_grades(self._current_subject()):
            self.grade_combo.addItem(f"پایهٔ {grade}", grade)
        if current_grade:
            index = self.grade_combo.findData(current_grade)
            if index >= 0:
                self.grade_combo.setCurrentIndex(index)
        self.grade_combo.blockSignals(False)

        self._reload()

    def _subject_changed(self) -> None:
        self.grade_combo.blockSignals(True)
        self.grade_combo.clear()
        for grade in self.service.syllabus_grades(self._current_subject()):
            self.grade_combo.addItem(f"پایهٔ {grade}", grade)
        self.grade_combo.blockSignals(False)
        self._reload()

    def _reload(self) -> None:
        subject = self._current_subject()
        grade = self._current_grade()
        self._chapters = self.service.syllabus_chapter_views(subject, grade) if subject else []
        self._records = list(self.service.repo.list_syllabus_sections(subject, grade))
        self._sections = []

        self.chapter_table.setRowCount(0)
        for chapter in self._chapters:
            row = self.chapter_table.rowCount()
            self.chapter_table.insertRow(row)
            sections = (
                syl.sections(subject, grade, chapter, self._records) if chapter.sections else []
            )
            assessed = sum(1 for s in sections if s.is_assessed)
            needs = sum(len(s.needs) for s in sections)
            count_text = (
                "نامشخص" if chapter.sections is None else str(chapter.sections)
            )
            cells = [
                str(chapter.no),
                chapter.title,
                count_text,
                f"{assessed} از {chapter.sections or '—'}",
                str(needs) if needs else "—",
            ]
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if column == 0:
                    item.setData(Qt.UserRole, chapter.no)
                self.chapter_table.setItem(row, column, item)

        progress = self.service.syllabus_progress(subject, grade)
        if progress.sections:
            self.coverage.setText(
                f"{progress.chapters} فصل · {progress.sections} گفتار · "
                f"{progress.assessed} ارزیابی‌شده · {progress.open_needs} نیاز باز"
            )
        else:
            self.coverage.setText(
                f"{progress.chapters} فصل · {progress.unknown_chapters} فصل نامشخص"
            )

        self._load_sections(None)

    def _load_sections(self, chapter) -> None:
        self.section_table.setRowCount(0)
        self._sections = []
        if chapter is None:
            return
        subject = self._current_subject()
        grade = self._current_grade()
        if chapter.sections is None:
            row = self.section_table.rowCount()
            self.section_table.insertRow(row)
            item = QTableWidgetItem("تعداد گفتار این فصل نامشخص است.")
            item.setFlags(Qt.ItemIsEnabled)
            self.section_table.setItem(row, 0, item)
            self.section_table.setSpan(row, 0, 1, 6)
            return
        self._sections = syl.sections(subject, grade, chapter, self._records)
        for section in self._sections:
            row = self.section_table.rowCount()
            self.section_table.insertRow(row)
            badge, _tone = syl.section_badge(section.record)
            needs = section.needs
            mastery = section.mastery
            cells = [
                str(section.no),
                section.label,
                f"{section.answered}/۸" if section.is_assessed else "—",
                f"{mastery:.0f}٪" if mastery is not None else "نامشخص",
                badge,
                " · ".join(n["label"] for n in needs) if needs else "—",
            ]
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if column == 0:
                    item.setData(Qt.UserRole, section.no)
                self.section_table.setItem(row, column, item)

    def _chapter_selected(self) -> None:
        self._load_sections(self._selected_chapter())

    def _section_selected(self) -> None:
        section = self._selected_section()
        self.btn_assess.setEnabled(section is not None)
        self.btn_rename.setEnabled(section is not None)
        self.btn_delete.setEnabled(section is not None)

    # -------------------------------------------------------------- actions

    def _enter_counts(self) -> None:
        subject = self._current_subject()
        grade = self._current_grade()
        if not subject:
            notify(self, "درسی انتخاب نشده", "اول یک درس و پایه انتخاب کن.")
            return
        unknown = [c for c in self._chapters if c.sections is None]
        if not unknown:
            notify(
                self,
                "همهٔ فصل‌ها عدد دارند",
                "اگر کتاب ۱۴۰۶ را تطبیق داده‌ای و عددی فرق دارد، از دکمهٔ "
                "«تغییر نام فصل» کنار آن فصل استفاده کن.",
            )
            return
        dialog = _CountsDialog(self._chapters, self)
        if dialog.exec() == QDialog.Accepted and dialog.values:
            for chapter_no, value in dialog.values.items():
                self.service.syllabus_set_chapter_count(subject, grade, chapter_no, value)
            notify(self, "ثبت شد", "تعداد گفتارهای وارد‌شده ذخیره شد.")
            self._reload()

    def _assess_section(self) -> None:
        section = self._selected_section()
        if section is None:
            notify(self, "گفتاری انتخاب نشده", "اول یک گفتار از جدول انتخاب کن.")
            return
        chapter = self._selected_chapter()
        dialog = _SectionDialog(
            self.service,
            self._current_subject(),
            self._current_grade(),
            chapter,
            section,
            self,
        )
        if dialog.exec() == QDialog.Accepted:
            answers, mastery, notes = dialog.values()
            try:
                self.service.syllabus_save_section(
                    self._current_subject(),
                    self._current_grade(),
                    chapter.no,
                    section.no,
                    answers,
                    mastery,
                    notes,
                )
            except ValueError as exc:
                QMessageBox.warning(self, "ثبت نشد", str(exc))
                return
            notify(
                self,
                "وضعیت ثبت شد",
                "این گفتار با نیازهای بازش وارد برنامهٔ روزانه و هفتگی می‌شود.",
            )
            self._reload()

    def _rename_section(self) -> None:
        section = self._selected_section()
        if section is None:
            notify(self, "گفتاری انتخاب نشده", "اول یک گفتار از جدول انتخاب کن.")
            return
        dialog = _TextDialog(
            "تغییر نام گفتار",
            "نام تازهٔ گفتار (خالی = بازگشت به نام رسمی کتاب):",
            section.edited_title or "",
            f"نام رسمی کتاب: {section.official_title or 'ثبت نشده'}",
            self,
        )
        if dialog.exec() == QDialog.Accepted:
            self.service.syllabus_rename_section(
                self._current_subject(),
                self._current_grade(),
                self._selected_chapter().no,
                section.no,
                dialog.value,
            )
            self._reload()

    def _delete_section(self) -> None:
        section = self._selected_section()
        if section is None:
            notify(self, "گفتاری انتخاب نشده", "اول یک گفتار از جدول انتخاب کن.")
            return
        if not confirm(
            self,
            "حذف گفتار",
            f"وضعیت ثبت‌شدهٔ «{section.label}» پاک می‌شود. دادهٔ کتاب درسی "
            "حذف نمی‌شود و می‌توانی دوباره وضعیتش را ثبت کنی. مطمئنی؟",
        ):
            return
        self.service.syllabus_delete_section(
            self._current_subject(),
            self._current_grade(),
            self._selected_chapter().no,
            section.no,
        )
        self._reload()

    def _rename_chapter(self) -> None:
        chapter = self._selected_chapter()
        if chapter is None:
            notify(self, "فصلی انتخاب نشده", "اول یک فصل از جدول انتخاب کن.")
            return
        dialog = _TextDialog(
            "تغییر نام فصل",
            "نام تازهٔ فصل (خالی = بازگشت به نام رسمی کتاب):",
            chapter.title if chapter.title != chapter.base_title else "",
            f"نام رسمی کتاب: {chapter.base_title}",
            self,
        )
        if dialog.exec() == QDialog.Accepted:
            self.service.syllabus_rename_chapter(
                self._current_subject(), self._current_grade(), chapter.no, dialog.value
            )
            self._reload()

    def _chapter_goal(self) -> None:
        chapter = self._selected_chapter()
        if chapter is None:
            notify(
                self, "فصلی انتخاب نشده",
                "ابتدا یک فصل را از فهرست انتخاب کن.",
            )
            return
        dialog = ChapterGoalDialog(
            self.service, self._current_subject(), self._current_grade(), chapter, self
        )
        dialog.exec()

    def _show_needs(self) -> None:
        needs = self.service.syllabus_open_needs()
        if not needs:
            notify(
                self,
                "نیاز بازی ندارد",
                "هیچ گفتاری نیاز باز ندارد. گفتارهایی که ارزیابی نشده‌اند اینجا "
                "نیستند، چون هنوز هیچ نیازی برایشان ثبت نشده.",
            )
            return
        dialog = _NeedsDialog(needs, self)
        dialog.exec()


class _CountsDialog(QDialog):
    """ورود گروهی تعداد گفتار فصل‌های نامشخص."""

    def __init__(self, chapters, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("ورود تعداد گفتارها")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(520)
        self.values: dict[int, Optional[int]] = {}
        root = QVBoxLayout(self)
        info = info_box()
        info.setText(
            "تعداد را از روی کتاب سال ۱۴۰۶ خودت بخوان. خالی گذاشتن یعنی "
            "«نامشخص»؛ «نامشخص» صادقانه‌تر از یک عدد غلط است."
        )
        root.addWidget(info)
        self.spins: dict[int, QSpinBox] = {}
        for chapter in chapters:
            row = QHBoxLayout()
            label = QLabel(f"فصل {chapter.no} · {chapter.title}")
            label.setWordWrap(True)
            row.addWidget(label, 1)
            spin = QSpinBox()
            spin.setRange(0, 99)
            spin.setSpecialValueText("نامشخص")
            spin.setValue(chapter.sections if chapter.sections is not None else 0)
            row.addWidget(spin)
            root.addLayout(row)
            self.spins[chapter.no] = spin
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("ذخیرهٔ تعدادها")
        buttons.button(QDialogButtonBox.Cancel).setText("انصراف")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _accept(self) -> None:
        for chapter_no, spin in self.spins.items():
            self.values[chapter_no] = spin.value() if spin.value() else None
        self.accept()


class _TextDialog(QDialog):
    """گرفتن یک متن از کاربر."""

    def __init__(
        self,
        title: str,
        prompt: str,
        value: str,
        hint: str = "",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(460)
        self.value = value
        root = QVBoxLayout(self)
        root.addWidget(QLabel(prompt))
        self.edit = QLineEdit(value)
        root.addWidget(self.edit)
        if hint:
            note = info_box()
            note.setText(hint)
            root.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("ذخیره")
        buttons.button(QDialogButtonBox.Cancel).setText("انصراف")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _accept(self) -> None:
        self.value = self.edit.text().strip()
        self.accept()


class ChapterGoalDialog(QDialog):
    """«تا تاریخ فلانی فصل X از کتاب Y تمام شود.»

    کاربر گفت: «من یک بخش رو لازم دارم که برایم تعیین کند که تا تایم
    فلانی، مثلا بخش ۱ رو از کتاب فلانی تمام کنم.»

    فصل‌بندی از همان دادهٔ سرفصل کتاب درسی می‌آید و دستی تایپ نمی‌شود؛
    کاربر فقط مهلت و ظرفیت روزانه را می‌دهد و برنامه می‌گوید شدنی است یا
    نه و از چه روزی باید شروع کند.
    """

    def __init__(
        self,
        service: AdvisorService,
        subject: str,
        grade: int,
        chapter,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.service = service
        self.subject = subject
        self.grade = grade
        self.chapter = chapter
        self.setWindowTitle("هدف فصل: تا چه تاریخی تمام شود؟")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(620)
        root = QVBoxLayout(self)

        info = info_box()
        info.setText(
            f"{subject} · پایهٔ {format_number(grade)} · فصل "
            f"{format_number(chapter.no)} — {chapter.title or 'بدون نام رسمی'}. "
            "گفتارهای این فصل از کتاب درسی می‌آیند و لازم نیست دستی تایپ شوند."
        )
        root.addWidget(info)

        form = QFormLayout()
        self.date_edit = QLineEdit()
        self.date_edit.setPlaceholderText("مثلاً ۱۴۰۵/۰۸/۱۵")
        form.addRow("مهلت پایان این فصل (شمسی):", self.date_edit)

        self.capacity_spin = QSpinBox()
        self.capacity_spin.setRange(0, 720)
        self.capacity_spin.setSingleStep(15)
        self.capacity_spin.setSuffix(" دقیقه")
        self.capacity_spin.setValue(self._default_capacity())
        self.capacity_spin.setToolTip(
            "ظرفیت مؤثر روزانهٔ مطالعه؛ از ساعت بیداری، خواب، کلاس و "
            "بازه‌های ضروری‌ات حساب می‌شود."
        )
        form.addRow("ظرفیت روزانه:", self.capacity_spin)

        self.scope_combo = QComboBox()
        self.scope_combo.addItem("فقط گفتارهایی که نیاز باز دارند", True)
        self.scope_combo.addItem("همهٔ گفتارهای فصل", False)
        form.addRow("دامنهٔ کار:", self.scope_combo)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("محاسبهٔ برنامه")
        buttons.button(QDialogButtonBox.Cancel).setText("بستن")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.output = QLabel()
        self.output.setWordWrap(True)
        self.output.setTextInteractionFlags(Qt.TextSelectableByMouse)
        root.addWidget(self.output, 1)

    def _default_capacity(self) -> int:
        try:
            breakdown = self.service.build_context().capacity_for(_dt.date.today())
            return max(0, int(breakdown.effective_minutes))
        except Exception:  # pragma: no cover - ظرفیت نباید پنجره را بشکند
            return 180

    def _section_counts(self) -> tuple[int, int]:
        """(تعداد همهٔ گفتارها، تعداد گفتارهای نیازباز)."""
        total = self.chapter.sections or 0
        records = {
            (r.chapter, r.section): r
            for r in self.service.repo.list_syllabus_sections(
                self.subject, self.grade
            )
            if r.chapter == self.chapter.no
        }
        open_count = 0
        for section in range(1, total + 1):
            if syl.section_needs(records.get((self.chapter.no, section))):
                open_count += 1
        return total, open_count

    def _accept(self) -> None:
        try:
            deadline = parse_jalali_date(self.date_edit.text())
        except ValueError as exc:
            notify(self, "تاریخ نامعتبر", str(exc))
            return
        if deadline is None:
            notify(self, "مهلت لازم است", "تاریخ مهلت این فصل را وارد کن.")
            return

        total, open_count = self._section_counts()
        only_open = bool(self.scope_combo.currentData())
        if only_open and open_count == 0 and total > 0:
            # هنوز هیچ گفتاری ارزیابی نشده؛ «فقط نیازهای باز» یعنی صفر و
            # برنامه خالی می‌شود. در این حالت کل فصل حساب می‌شود و همین
            # در خروجی نوشته می‌شود — نه اینکه عددی ساخته شود.
            only_open = False
            index = self.scope_combo.findData(False)
            if index >= 0:
                self.scope_combo.setCurrentIndex(index)
        plan = plan_chapter_goal(
            ChapterGoalInput(
                subject=self.subject,
                grade=self.grade,
                chapter=self.chapter.no,
                deadline=deadline,
                daily_capacity_minutes=int(self.capacity_spin.value()),
                only_open_needs=only_open,
                section_count=total,
                open_section_count=open_count,
            )
        )
        self.output.setText(self._render(plan))
        if not plan.feasible:
            notify(
                self,
                "این مهلت با ظرفیت فعلی شدنی نیست",
                "\n".join(plan.warnings) or "جزئیات را در پایین ببین.",
            )

    @staticmethod
    def _date_text(value: _dt.date) -> str:
        """تاریخ با ارقام فارسی، هم‌خوان با بقیهٔ اعداد همین پنجره."""
        return persian_digits(format_jalali(value, with_weekday=False))

    @staticmethod
    def _render(plan) -> str:
        lines: list[str] = []
        lines.append(
            f"گفتارهای شمرده‌شده: {format_number(plan.open_section_count)} "
            f"از {format_number(plan.section_count)}"
        )
        lines.append(
            f"زمان هر گفتار: {format_minutes(plan.minutes_per_section)} — "
            f"جمع {format_minutes(plan.total_minutes)}"
        )
        lines.append(
            f"ظرفیت روزانه: {format_minutes(plan.capacity_minutes_per_day)} — "
            f"روزهای لازم: {format_number(plan.required_days, digits=1)}، "
            f"روزهای موجود: {format_number(plan.available_days)}"
        )
        if plan.milestones:
            lines.append("")
            lines.append("پله‌ها (از عقب به جلو):")
            for milestone in plan.milestones:
                lines.append(
                    f"  • {milestone.label}: {ChapterGoalDialog._date_text(milestone.date)}"
                    f" ({format_minutes(milestone.minutes)})"
                )
        if plan.per_day:
            lines.append("")
            lines.append(f"تقسیم روزانه ({format_number(len(plan.per_day))} روز):")
            for day in plan.per_day[:10]:
                lines.append(
                    f"  • {ChapterGoalDialog._date_text(day.date)}: "
                    f"{format_minutes(day.minutes)} "
                    f"({format_number(day.sections, digits=1)} گفتار)"
                )
            if len(plan.per_day) > 10:
                lines.append(f"  … و {format_number(len(plan.per_day) - 10)} روز دیگر")
        if plan.warnings:
            lines.append("")
            lines.append("هشدارها:")
            lines.extend(f"  • {w}" for w in plan.warnings)
        if plan.suggestions:
            lines.append("")
            lines.append("راه‌های جبران:")
            for suggestion in plan.suggestions:
                lines.append(f"  • {suggestion.title}: {suggestion.detail}")
        return "\n".join(lines)


class _NeedsDialog(QDialog):
    """فهرست گفتارهای نیازدار."""

    def __init__(self, needs: list[dict], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("نیازهای باز سرفصل")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(680)
        root = QVBoxLayout(self)
        info = info_box()
        info.setText(
            "این فهرست از وضعیت واقعی گفتارها ساخته شده و مستقیم ورودی "
            "برنامه‌ریزی است: هر ردیف یک نیاز بازِ قابل جبران است، نه یک "
            "توصیهٔ کلی."
        )
        root.addWidget(info)
        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["درس/پایه", "فصل", "گفتار", "نیازهای باز"])
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        for item in needs:
            row = table.rowCount()
            table.insertRow(row)
            cells = [
                f"{item['subject']} · پایهٔ {item['grade']}",
                f"{item['chapter']} · {item['chapter_title']}",
                f"{item['section']} · {item['label']}",
                " · ".join(n["label"] for n in item["needs"]),
            ]
            for column, text in enumerate(cells):
                table.setItem(row, column, QTableWidgetItem(text))
        root.addWidget(table, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Close).setText("بستن")
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
