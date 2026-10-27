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

from PySide6.QtCore import QDate, QDateTime, QLocale, Qt, Signal, QTime
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..jdate import persian_digits
from .theme import COLORS, base_font, tone_colors


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


# ارقام فارسی و عربی که کاربر ممکن است تایپ کند، به لاتین برگردانده می‌شوند.
_LATIN_DIGITS = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)


class _LatinSpinBox(QSpinBox):
    """جعبهٔ چرخش که بی‌توجه به زبان سیستم همیشه اعداد لاتین می‌دهد.

    ``QSpinBox`` و ``QTimeEdit`` استاندارد مقدار را با ``QLocale::toString``
    رسم می‌کنند؛ روی فارسی «۰۷:۳۰» می‌شود و کاربری که به اعداد لاتین عادت
    دارد باید معنی شود. این زیرکلاس همان دو متبدل متن را می‌گیرد تا خروجی
    همیشه ``%02d`` لاتین باشد — هم برای نمایش و هم برای آنچه کاربر تایپ
    می‌کند (اگر ارقام فارسی بزند هم پذیرفته و لاتین می‌شود).
    """

    def __init__(self, low: int, high: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setRange(low, high)
        self.setDisplayIntegerBase(10)
        # بدون پیچش: غلتیدن ۲۳ به ۰ باعث می‌شد کاربر ناخواسته ساعت اشتباه بگذارد.
        self.setWrapping(False)
        self.setKeyboardTracking(False)
        self.setAccelerated(True)
        self.setAlignment(Qt.AlignCenter)

    def textFromValue(self, value: int) -> str:  # noqa: N802 - Qt naming
        return f"{value:02d}"

    def valueFromText(self, text: str) -> int:  # noqa: N802 - Qt naming
        cleaned = text.translate(_LATIN_DIGITS)
        digits = "".join(ch for ch in cleaned if ch.isdigit())
        try:
            value = int(digits)
        except ValueError:
            return self.minimum()
        return max(self.minimum(), min(self.maximum(), value))


class _TimeField(QWidget):
    """یک کادر ساعت: دو جعبهٔ چرخش (ساعت و دقیقه) با جداکنندهٔ دونقطه.

    چرا ``QTimeEdit`` کنار گذاشته شد:

    * اعداد را با locale سیستم می‌کشید؛ فارسی «۰۷:۳۰» می‌شد.
    * در ``QTimeEdit`` کل رشته یک قلم واحد دارد، پس نمی‌شد ساعت را از دقیقه
      پررنگ/بزرگ‌تر کرد تا در یک نگاه جدا شود.
    * دو جعبهٔ ۰–۲۳ و ۰–۵۹ قالب ۲۴ ساعته را ساختاراً تضمین می‌کنند، نه فقط
      با یک قالب نمایشی؛ امکان «۱۸:۰۰ بعدازظهر» بودن وجود ندارد.

    ساعت یک درجه بزرگ‌تر و پررنگ‌تر از دقیقه است.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        # اعداد همیشه چپ‌به‌راست می‌مانند حتی وقتی پنجرهٔ کل راست‌به‌چپ است.
        self.setLayoutDirection(Qt.LeftToRight)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        self.hour_spin = _LatinSpinBox(0, 23)
        self.minute_spin = _LatinSpinBox(0, 59)

        self.colon = QLabel(":")
        self.colon.setObjectName("timeColon")

        # قلم را با helper برنامه می‌سازیم تا خانوادهٔ Vazirmatn و فایل وزن
        # درست انتخاب شود، حتی اگر هنوز تم روی پنجره اعمال نشده باشد.
        base = base_font()
        size = base.pointSize() or 10
        hour_font = base_font(size + 2, 700)
        minute_font = base_font(size, 400)
        self.hour_spin.setFont(hour_font)
        self.colon.setFont(hour_font)
        self.minute_spin.setFont(minute_font)

        for spin in (self.hour_spin, self.minute_spin):
            spin.setFixedWidth(62)

        layout.addWidget(self.hour_spin)
        layout.addWidget(self.colon)
        layout.addWidget(self.minute_spin)

    def minutes(self) -> int:
        return self.hour_spin.value() * 60 + self.minute_spin.value()

    def set_minutes(self, minutes: int) -> None:
        total = int(minutes) % 1440
        self.hour_spin.setValue(total // 60)
        self.minute_spin.setValue(total % 60)

    def setToolTip(self, text: str) -> None:  # noqa: N802 - Qt naming
        for spin in (self.hour_spin, self.minute_spin):
            spin.setToolTip(text)


class LatinDateTimeField(QWidget):
    """کادر تاریخ‌وزمان: سال/ماه/روز و ساعت/دقیقه، همه با اعداد لاتین.

    چرا ترکیبی و نه ``QDateTimeEdit``: پنجرهٔ برنامه راست‌به‌چپ است و هر سه
    ویرایشگر تاریخ/ساعتِ Qt متن خودشان را راست‌به‌چپ رندر می‌کنند؛
    «2026-10-27 19:45» می‌شود «۴۵:۱۹ ۲۷-۱۰-۲۰۲۶». دادن locale لاتین فقط
    ارقام را درست می‌کند («45:19 27-10-2026»)، تراضی گروه‌ها نه.

    جعبه‌های جدا هر کدام فقط ارقام دارند و ارقام حتی در پاراگراف
    راست‌به‌چپ چپ‌به‌راست می‌مانند، پس ترتیب حفظ می‌شود. سال/ماه/روز
    میلادی است چون همان چیزی است که پایگاه داده ذخیره می‌کند؛ نمایشِ
    جلالی همان‌جایی که باید (با ``format_datetime``) انجام می‌شود.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setLayoutDirection(Qt.LeftToRight)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        self.year_spin = _LatinSpinBox(1900, 2200)
        self.month_spin = _LatinSpinBox(1, 12)
        self.day_spin = _LatinSpinBox(1, 31)
        self.time_field = _TimeField()

        for spin in (self.year_spin, self.month_spin, self.day_spin):
            spin.setFixedWidth(62)

        layout.addWidget(self.year_spin)
        layout.addWidget(QLabel("/"))
        layout.addWidget(self.month_spin)
        layout.addWidget(QLabel("/"))
        layout.addWidget(self.day_spin)
        layout.addSpacing(10)
        layout.addWidget(self.time_field)

        # اگر ماه یا سال عوض شد و روز از طول ماه بیشتر بود، پایین می‌آید؛
        # وگرنه کاربر «۳۱ فوریه» می‌ساخت و مقدار بی‌صدا جا می‌افتاد.
        self.month_spin.valueChanged.connect(self._clamp_day)
        self.year_spin.valueChanged.connect(self._clamp_day)

        self.setToolTip("تاریخ میلادی و ساعت ۲۴ ساعته، با اعداد لاتین")

    # ------------------------------------------------------------------

    def _clamp_day(self) -> None:
        days = QDate(self.year_spin.value(), self.month_spin.value(), 1).daysInMonth()
        if self.day_spin.value() > days:
            self.day_spin.setValue(days)

    def dateTime(self) -> QDateTime:
        year, month = self.year_spin.value(), self.month_spin.value()
        day = min(self.day_spin.value(), QDate(year, month, 1).daysInMonth())
        return QDateTime(
            QDate(year, month, day),
            QTime(self.time_field.hour_spin.value(), self.time_field.minute_spin.value()),
        )

    def setDateTime(self, value: "QDateTime | _dt.datetime") -> None:
        """``QDateTime`` یا ``datetime`` پایتون را می‌پذیرد.

        ``ManualSessionDialog`` مقدار اولیه را با ``datetime`` پایتون
        می‌گذارد و آزمون‌ها ``QDateTime`` پاس می‌دهند؛ هر دو باید کار کنند.
        ``datetime`` بی‌توجه به منطقهٔ زمانی یعنی زمان محلی، پس مستقیم
        استفاده می‌شود.
        """
        local = value.toLocalTime().toPython() if isinstance(value, QDateTime) else value
        self.year_spin.setValue(local.year)
        self.month_spin.setValue(local.month)
        self.day_spin.setValue(local.day)
        self.time_field.set_minutes(local.hour * 60 + local.minute)


class TimeRangeInput(QWidget):
    """ورودی بازهٔ ساعت با اعتبارسنجی زنده.

    کادرهای ساعت با دو جعبهٔ چرخش جدا (ساعت و دقیقه) ساخته شده‌اند تا
    اعداد همیشه لاتین بمانند و ساعت از دقیقه پررنگ/بزرگ‌تر و قابل تفکیک
    باشد؛ قالب ۲۴ ساعته هم با بازهٔ ۰–۲۳ ساختاری است، نه فقط نمایشی.

    جدا از آن، این ویجت سه چیز اضافه می‌کند:

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
        self.start_field = _TimeField()
        self.sep_label = QLabel(end_label)
        self.end_field = _TimeField()
        for field in (self.start_field, self.end_field):
            field.setToolTip("قالب ۲۴ ساعته با اعداد لاتین، مثلاً 07:30 یا 19:00")

        self.duration_label = QLabel()
        self.duration_label.setObjectName("muted")
        duration_font = QFont()
        duration_font.setPointSize(max(8, duration_font.pointSize() - 1))
        self.duration_label.setFont(duration_font)

        layout.addWidget(self.start_label)
        layout.addWidget(self.start_field)
        layout.addWidget(self.sep_label)
        layout.addWidget(self.end_field)
        layout.addWidget(self.duration_label)
        layout.addStretch(1)

        for spin in (
            self.start_field.hour_spin,
            self.start_field.minute_spin,
            self.end_field.hour_spin,
            self.end_field.minute_spin,
        ):
            spin.valueChanged.connect(self._revalidate)
        self.set_range(start, end)

    # ------------------------------------------------------------------
    # مقدار
    # ------------------------------------------------------------------

    def set_range(self, start: str | int, end: str | int) -> None:
        """مقدار اولیه/جدید را می‌گذارد (``HH:mm`` یا دقیقه از نیمه‌شب)."""
        self.start_field.set_minutes(self._to_minutes(start))
        self.end_field.set_minutes(self._to_minutes(end))

    @staticmethod
    def _to_minutes(value: str | int) -> int:
        if isinstance(value, str):
            hour, _, minute = value.partition(":")
            return int(hour) * 60 + int(minute or 0)
        return int(value) % 1440

    def start_minutes(self) -> int:
        return self.start_field.minutes()

    def end_minutes(self) -> int:
        return self.end_field.minutes()

    def set_start_minutes(self, minutes: int) -> None:
        self.start_field.set_minutes(int(minutes))

    def set_end_minutes(self, minutes: int) -> None:
        self.end_field.set_minutes(int(minutes))

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
