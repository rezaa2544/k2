"""ابزارک‌های مشترک با فاصله‌گذاری و خوانایی یکدست.

هر کارت می‌تواند «تُن» بگیرد: رنگ اختصاصیِ نوع کار (مطالعه، مرور، آزمون،
مهلت، ساعت، عقب‌افتادگی). تُن هم روی نوار رنگی ضخیم سمت راست کارت دیده
می‌شود و هم زمینهٔ کارت را tint می‌کند، تا کاربر با یک نگاه نوع کار را
بفهمد. انتخابگر ویژگی در QSS انجام می‌شود، پس رنگ‌ها یکجا در ``theme.py``
تعریف شده‌اند.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

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
