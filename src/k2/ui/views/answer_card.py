"""پنجرهٔ خواندن کارت پاسخ — آفلاین، بدون هیچ سرویس بیرونی.

جریان کار: کاربر تصویر کارت را می‌دهد → برنامه شبکهٔ دایره‌ها را پیدا و
میزان سیاهی هر خانه را می‌سنجد → جدول نتیجه را نشان می‌دهد → کاربر هر
خانهٔ اشتباه را اصلاح می‌کند → فقط بعد از تأیید، اعداد وارد فرم آزمون
می‌شوند.

هیچ عددی (تعداد سؤال، درست، غلط، خالی) از خودِ تصویر به‌عنوان واقعیت ثبت
نمی‌شود؛ کاربر همه را می‌بیند و تأیید می‌کند.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ... import answer_card
from ..widgets import Card, info_box, notify


class AnswerCardDialog(QDialog):
    """خواندن کارت پاسخ و اصلاح دستی نتیجه قبل از ثبت."""

    def __init__(self, service, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("خواندن کارت پاسخ")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumSize(760, 620)
        self.reading: Optional[answer_card.CardReading] = None
        self.key_reading: Optional[answer_card.CardReading] = None
        self.result: Optional[dict] = None

        root = QVBoxLayout(self)
        root.setSpacing(10)

        self.info = info_box()
        self.info.setText(
            "تصویر کارت پاسخ را بده؛ برنامه شبکهٔ دایره‌ها را پیدا می‌کند و "
            "گزینهٔ پر‌شدهٔ هر سؤال را نشان می‌دهد. هیچ سؤالی حدس زده نمی‌شود: "
            "اگر خالی باشد یا بیش از یک گزینه پر شده باشد، «نامشخص» ثبت می‌شود "
            "و خودت در جدول اصلاحش می‌کنی. خواندن کامل آفلاین است و تصویر "
            "هیچ‌جا فرستاده نمی‌شود."
        )
        root.addWidget(self.info)

        setup = QHBoxLayout()
        setup.addWidget(QLabel("تعداد سؤال کارت:"))
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 400)
        self.rows_spin.setValue(100)
        setup.addWidget(self.rows_spin)
        setup.addWidget(QLabel("تعداد گزینه:"))
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(2, 6)
        self.cols_spin.setValue(4)
        setup.addWidget(self.cols_spin)
        setup.addWidget(QLabel("آستانهٔ پر‌شدن:"))
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(5, 95)
        self.threshold_spin.setValue(int(answer_card.DEFAULT_FILL_THRESHOLD * 100))
        self.threshold_spin.setSuffix(" ٪")
        setup.addWidget(self.threshold_spin)
        setup.addStretch(1)
        root.addLayout(setup)

        actions = QHBoxLayout()
        self.btn_read = QPushButton("انتخاب تصویر کارت پاسخ")
        self.btn_read.setObjectName("primary")
        self.btn_read.clicked.connect(self._read_card)
        actions.addWidget(self.btn_read)
        self.btn_key = QPushButton("انتخاب تصویر کلید پاسخ")
        self.btn_key.setToolTip(
            "اگر کارت کلید را هم بدهی، درست و غلط و نزده حساب می‌شود."
        )
        self.btn_key.clicked.connect(self._read_key)
        actions.addWidget(self.btn_key)
        actions.addStretch(1)
        self.summary_label = QLabel("هنوز تصویری خوانده نشده.")
        self.summary_label.setObjectName("muted")
        self.summary_label.setWordWrap(True)
        actions.addWidget(self.summary_label, 1)
        root.addLayout(actions)

        card = Card("نتیجهٔ خواندن — هر خانه را می‌توانی اصلاح کنی")
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["شمارهٔ سؤال", "گزینهٔ خوانده‌شده", "وضعیت", "اصلاح دستی"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        card.add(self.table)
        root.addWidget(card, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("ثبت اعداد در فرم آزمون")
        buttons.button(QDialogButtonBox.Cancel).setText("انصراف")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ------------------------------------------------------------------

    def _read_card(self) -> None:
        self._read_into("card")

    def _read_key(self) -> None:
        self._read_into("key")

    def _read_into(self, which: str) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "انتخاب تصویر کارت پاسخ",
            "",
            "تصویر (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not path:
            return
        try:
            reading = answer_card.read_card(
                path,
                expected_rows=self.rows_spin.value(),
                columns=self.cols_spin.value(),
                fill_threshold=self.threshold_spin.value() / 100.0,
            )
        except answer_card.AnswerCardError as exc:
            QMessageBox.warning(self, "کارت خوانده نشد", str(exc))
            return
        if which == "card":
            self.reading = reading
        else:
            self.key_reading = reading
        self._rebuild_table()

    def _rebuild_table(self) -> None:
        self.table.setRowCount(0)
        if self.reading is None:
            self.summary_label.setText("هنوز تصویری خوانده نشده.")
            return
        for question in self.reading.questions:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(question.number)))
            self.table.setItem(row, 1, QTableWidgetItem(self._option_text(question)))
            self.table.setItem(row, 2, QTableWidgetItem(self._status_text(question)))
            combo = QComboBox()
            combo.addItem("— نامشخص —", None)
            for index in range(self.reading.columns):
                combo.addItem(answer_card.OPTION_LABELS[index], index)
            if question.selected is not None:
                combo.setCurrentIndex(combo.findData(question.selected))
            self.table.setCellWidget(row, 3, combo)
        self._refresh_summary()

    @staticmethod
    def _option_text(question) -> str:
        if question.selected is None:
            return "—"
        index = question.selected
        return answer_card.OPTION_LABELS[index] if index < len(
            answer_card.OPTION_LABELS
        ) else str(index + 1)

    @staticmethod
    def _status_text(question) -> str:
        return {
            "marked": "پر‌شده",
            "blank": "خالی",
            "ambiguous": "ابهام‌دار — نیاز به تأیید",
        }[question.status]

    def _refresh_summary(self) -> None:
        if self.reading is None:
            return
        text = answer_card.summarise(self.reading)
        if self.reading.warnings:
            text += "\n" + " · ".join(self.reading.warnings)
        if self.key_reading is not None:
            result = answer_card.compare_with_key(
                self.reading, self.key_reading.selected_list()
            )
            text += (
                f"\nنسبت به کلید: {result['correct']} درست، {result['wrong']} غلط، "
                f"{result['blank']} نزده، {result['unknown']} نامشخص."
            )
        self.summary_label.setText(text)

    # ------------------------------------------------------------------

    def _accept(self) -> None:
        if self.reading is None:
            QMessageBox.warning(self, "تصویری خوانده نشده", "اول تصویر کارت را بده.")
            return
        # مقادیر اصلاح‌شدهٔ دستی کاربر از جدول خوانده می‌شود
        for row in range(self.table.rowCount()):
            question = self.reading.questions[row]
            combo = self.table.cellWidget(row, 3)
            if combo is None:
                continue
            value = combo.currentData()
            if value is None:
                question.selected = None
                question.status = "ambiguous"
                question.note = "کاربر تأیید نکرد"
            else:
                question.selected = int(value)
                question.status = "marked"
                question.note = "اصلاح دستی کاربر"
        if self.key_reading is not None:
            self.result = answer_card.compare_with_key(
                self.reading, self.key_reading.selected_list()
            )
        else:
            self.result = {
                "total": len(self.reading.questions),
                "clean": self.reading.clean_count,
                "blank": self.reading.blank_count,
                "ambiguous": self.reading.ambiguous_count,
            }
        self.accept()
