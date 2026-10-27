"""ابزارک‌های مشترک با فاصله‌گذاری و خوانایی یکدست.

هر کارت می‌تواند «تُن» بگیرد: رنگ اختصاصیِ نوع کار (مطالعه، مرور، آزمون،
مهلت، ساعت، عقب‌افتادگی). تُن هم روی نوار رنگی ضخیم سمت راست کارت دیده
می‌شود و هم زمینهٔ کارت را tint می‌کند، تا کاربر با یک نگاه نوع کار را
بفهمد. انتخابگر ویژگی در QSS انجام می‌شود، پس رنگ‌ها یکجا در ``theme.py``
تعریف شده‌اند.
"""

from __future__ import annotations

import datetime as _dt
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from ..jdate import persian_digits
from .theme import COLORS, tone_colors


def _repolish(widget: QWidget) -> None:
    """انتخابگر ویژگیِ QSS را روی ویجت اعمال می‌کند."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class Card(QFrame):
    """کارت سفید با حاشیهٔ واضح، تیتر اختیاری و تُن رنگیِ نوع کار."""

    def __init__(
        self,
        title: str = "",
        parent: Optional[QWidget] = None,
        tone: str = "",
    ):
        super().__init__(parent)
        self.setObjectName("card")
        self._tone = ""
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 16, 18, 16)
        self._layout.setSpacing(11)
        if title:
            label = QLabel(title)
            label.setObjectName("cardTitle")
            self._layout.addWidget(label)
        if tone:
            self.set_tone(tone)

    def set_tone(self, tone: str) -> None:
        """رنگ معنایی کارت را تعیین می‌کند (نوار راست + زمینهٔ tint‌شده)."""
        self._tone = tone
        if not tone:
            self.setProperty("tone", None)
        else:
            self.setProperty("tone", tone)
        _repolish(self)

    def tone(self) -> str:
        return self._tone

    def body(self) -> QVBoxLayout:
        return self._layout

    def add(self, widget: QWidget) -> QWidget:
        self._layout.addWidget(widget)
        return widget

    def add_layout(self, layout) -> None:
        self._layout.addLayout(layout)


class StatTile(Card):
    """کاشی آماری با عدد درشت و نوار رنگیِ تُن."""

    def __init__(
        self,
        title: str,
        value: str = "—",
        hint: str = "",
        tone: str = "accent",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(title, parent, tone=tone)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("bigNumber")
        self.value_label.setStyleSheet(f"color: {tone_colors(tone)[0]};")
        self.value_label.setAccessibleName(title)
        self.add(self.value_label)
        self.hint_label = QLabel(hint)
        self.hint_label.setObjectName("hint")
        self.hint_label.setWordWrap(True)
        self.hint_label.setMinimumHeight(30)
        self.add(self.hint_label)

    def set_value(self, value: str, hint: str = "") -> None:
        self.value_label.setText(value)
        if hint:
            self.hint_label.setText(hint)


class Badge(QLabel):
    """برچسب رنگی کوچک با تُن."""

    def __init__(self, text: str = "", tone: str = "muted", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.set_tone(tone)
        self.setAlignment(Qt.AlignCenter)

    def set_tone(self, tone: str) -> None:
        fg, bg, _line = tone_colors(tone)
        self.setStyleSheet(
            f"background-color: {bg}; color: {fg};"
            "border-radius: 11px; padding: 5px 11px; font-size: 11px; font-weight: 800;"
        )


def section_title(text: str, parent: Optional[QWidget] = None) -> QLabel:
    """تیتر بخش با وزن سنگین."""
    label = QLabel(text, parent)
    label.setObjectName("sectionTitle")
    return label


def lead(text: str, parent: Optional[QWidget] = None) -> QLabel:
    """متن راهنمای صفحه."""
    label = QLabel(text, parent)
    label.setObjectName("pageLead")
    label.setWordWrap(True)
    return label


def _callout(tone: str, parent: Optional[QWidget] = None) -> QLabel:
    fg, bg, line = tone_colors(tone)
    label = QLabel(parent=parent)
    label.setWordWrap(True)
    label.setStyleSheet(
        f"background-color: {bg}; color: {fg};"
        f"border: 2px solid {line}; border-right: 5px solid {fg};"
        "border-radius: 12px; padding: 13px 15px; font-weight: 600;"
    )
    return label


def info_box(parent: Optional[QWidget] = None) -> QLabel:
    return _callout("info", parent)


def warn_box(parent: Optional[QWidget] = None) -> QLabel:
    return _callout("warn", parent)


def ok_box(parent: Optional[QWidget] = None) -> QLabel:
    return _callout("ok", parent)


def danger_box(parent: Optional[QWidget] = None) -> QLabel:
    return _callout("danger", parent)


def confirm(parent: Optional[QWidget], title: str, text: str) -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(QMessageBox.Question)
    box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    box.setDefaultButton(QMessageBox.No)
    return box.exec() == QMessageBox.Yes


def notify(parent: Optional[QWidget], title: str, text: str) -> None:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(QMessageBox.Information)
    box.exec()


def row(*widgets: QWidget, spacing: int = 10) -> QHBoxLayout:
    layout = QHBoxLayout()
    layout.setSpacing(spacing)
    for widget in widgets:
        layout.addWidget(widget)
    return layout


def format_clock(minutes: int) -> str:
    """دقیقه از نیمه‌شب را به قالب ``HH:mm`` فارسی تبدیل می‌کند.

    ورودی «دقیقه از نیمه‌شب» است، نه «ساعت». تفاوتش مهم است: نسخهٔ
    ``jdate.format_clock`` ساعت و دقیقه می‌گیرد و اگر دقیقه به آن داده
    شود «۹۰۰:۰۰» چاپ می‌شود — همان اشتبالی که در صفحهٔ کلاس‌ها رخ می‌داد.
    """
    minutes = int(minutes) % 1440
    return persian_digits(f"{minutes // 60:02d}:{minutes % 60:02d}")


def format_duration(minutes: int) -> str:
    """مدت را به فارسی خوانا می‌کند: «۲ ساعت و ۳۰ دقیقه»."""
    minutes = int(minutes)
    if minutes < 60:
        return f"{minutes} دقیقه"
    hours, rest = divmod(minutes, 60)
    if not rest:
        return f"{hours} ساعت"
    return f"{hours} ساعت و {rest} دقیقه"


class TimeRangeInput(QWidget):
    """ورودی بازهٔ ساعت با اعتبارسنجی زنده.

    ``QTimeEdit`` خالی هیچ چیزی دربارهٔ *ترتیب* شروع و پایان نمی‌گوید؛
    کاربر می‌توانست «۱۹:۰۰ تا ۱۵:۰۰» را بپذیرد و بعد در پایگاه داده یا
    در پنجرهٔ تعارض، بازه‌ای می‌دید که معنایی ندارد. این ویجت همان دو
    کادر را نگه می‌دارد اما سه چیز اضافه می‌کند:

    * مدتِ بازه هر لحظه کنار کادرها دیده می‌شود («۲ ساعت»)،
    * اگر پایان پیش از شروع باشد، خطای قرمز **جای همان کادر** می‌آید،
      نه یک پیام دهانی پس از ذخیره،
    * دکمهٔ ذخیره تا رفع خطا غیرفعال می‌شود.

    ``allow_cross_midnight=True`` برای بازه‌هایی مثل خواب (۲۳:۰۰ تا
    ۰۶:۰۰) است که از نیمه‌شب می‌گذرند و ``end < start`` برایشان درست است.
    """

    validityChanged = Signal(bool)

    def __init__(
        self,
        start: str | int = "07:00",
        end: str | int = "09:00",
        *,
        allow_cross_midnight: bool = False,
        start_label: str = "از ساعت",
        end_label: str = "تا ساعت",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.allow_cross_midnight = allow_cross_midnight
        self.setLayoutDirection(Qt.RightToLeft)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.start_label = QLabel(start_label)
        self.start_edit = QTimeEdit()
        self.sep_label = QLabel(end_label)
        self.end_edit = QTimeEdit()
        for edit in (self.start_edit, self.end_edit):
            edit.setDisplayFormat("HH:mm")
            # بدون پیچش: غلتیدن ۰۰:۰۰ به ۲۳:۵۹ باعث می‌شد کاربر ناخواسته
            # بازه‌ای بسازد که شب را می‌پیچد.
            edit.setWrapping(False)
            edit.setCurrentSection(QTimeEdit.HourSection)
            edit.setAlignment(Qt.AlignCenter)
            edit.setMinimumWidth(84)
            edit.setMaximumWidth(96)
            edit.setToolTip("قالب ۲۴ ساعته، مثلاً ۰۷:۳۰ یا ۱۹:۰۰")

        self.duration_label = QLabel()
        self.duration_label.setObjectName("muted")
        duration_font = QFont()
        duration_font.setPointSize(max(8, duration_font.pointSize() - 1))
        self.duration_label.setFont(duration_font)

        layout.addWidget(self.start_label)
        layout.addWidget(self.start_edit)
        layout.addWidget(self.sep_label)
        layout.addWidget(self.end_edit)
        layout.addWidget(self.duration_label)
        layout.addStretch(1)

        self.start_edit.timeChanged.connect(self._revalidate)
        self.end_edit.timeChanged.connect(self._revalidate)
        self.set_range(start, end)

    # ------------------------------------------------------------------
    # مقدار
    # ------------------------------------------------------------------

    def set_range(self, start: str | int, end: str | int) -> None:
        """مقدار اولیه/جدید را می‌گذارد (``HH:mm`` یا دقیقه از نیمه‌شب)."""
        self.start_edit.setTime(self._to_qtime(start))
        self.end_edit.setTime(self._to_qtime(end))

    @staticmethod
    def _to_qtime(value: str | int) -> _dt.time:
        if isinstance(value, str):
            hour, _, minute = value.partition(":")
            return _dt.time(int(hour), int(minute or 0))
        return _dt.time((int(value) % 1440) // 60, int(value) % 60)

    def start_minutes(self) -> int:
        value = self.start_edit.time()
        return value.hour() * 60 + value.minute()

    def end_minutes(self) -> int:
        value = self.end_edit.time()
        return value.hour() * 60 + value.minute()

    def set_start_minutes(self, minutes: int) -> None:
        self.start_edit.setTime(self._to_qtime(int(minutes)))

    def set_end_minutes(self, minutes: int) -> None:
        self.end_edit.setTime(self._to_qtime(int(minutes)))

    # ------------------------------------------------------------------
    # اعتبار
    # ------------------------------------------------------------------

    def is_valid(self) -> bool:
        start, end = self.start_minutes(), self.end_minutes()
        if self.allow_cross_midnight:
            return start != end
        return end > start

    def error_text(self) -> str:
        start, end = self.start_minutes(), self.end_minutes()
        if self.allow_cross_midnight:
            if start == end:
                return "شروع و پایان نمی‌توانند یکسان باشند."
            return ""
        if start == end:
            return "شروع و پایان یکسان است؛ بازهٔ صفر معنایی ندارد."
        if end < start:
            return (
                f"پایان ({format_clock(end)}) پیش از شروع ({format_clock(start)}) است. "
                "اگر این بازه از نیمه‌شب می‌گذرد، از حالت «بازهٔ شبانه» استفاده کن."
            )
        return ""

    def duration_minutes(self) -> int:
        start, end = self.start_minutes(), self.end_minutes()
        if self.allow_cross_midnight and end <= start:
            return (end - start) % 1440
        return max(0, end - start)

    def attach_button_box(self, box: QDialogButtonBox) -> None:
        """دکمهٔ تأیید را تا رفع خطا غیرفعال می‌کند."""
        self._button_box = box
        self._revalidate()

    def _revalidate(self) -> None:
        valid = self.is_valid()
        error = self.error_text()
        duration = self.duration_minutes()
        if valid and duration:
            self.duration_label.setText(f"مدت: {format_duration(duration)}")
        elif valid:
            self.duration_label.setText("")
        else:
            self.duration_label.setText(error)
        self.duration_label.setStyleSheet(
            "" if valid else f"color: {COLORS['danger']};"
        )
        box = getattr(self, "_button_box", None)
        if box is not None:
            ok = box.button(QDialogButtonBox.Ok)
            if ok is not None:
                ok.setEnabled(valid)
                if valid:
                    ok.setToolTip("")
                else:
                    ok.setToolTip(error)
        self.validityChanged.emit(valid)
