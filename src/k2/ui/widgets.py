"""ابزارک‌های مشترک با فاصله‌گذاری و خوانایی یکدست."""

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

from .theme import COLORS


class Card(QFrame):
    """کارت سفید با تیتر اختیاری و فضای تنفس مناسب."""

    def __init__(self, title: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(17, 15, 17, 15)
        self._layout.setSpacing(10)
        if title:
            label = QLabel(title)
            label.setObjectName("cardTitle")
            self._layout.addWidget(label)

    def body(self) -> QVBoxLayout:
        return self._layout

    def add(self, widget: QWidget) -> QWidget:
        self._layout.addWidget(widget)
        return widget

    def add_layout(self, layout) -> None:
        self._layout.addLayout(layout)


class StatTile(Card):
    """کاشی آماری با یک نکتهٔ کوتاه و نشانهٔ رنگیِ کم‌تنش."""

    def __init__(
        self,
        title: str,
        value: str = "—",
        hint: str = "",
        tone: str = "accent",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(title, parent)
        color = {
            "accent": COLORS["accent"], "info": COLORS["info"],
            "warn": COLORS["warn"], "danger": COLORS["danger"],
            "muted": COLORS["muted"],
        }.get(tone, COLORS["accent"])
        self.setStyleSheet(f"QFrame#card {{ border-right: 3px solid {color}; }}")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("bigNumber")
        self.value_label.setStyleSheet(f"color: {color};")
        self.value_label.setAccessibleName(title)
        self.add(self.value_label)
        self.hint_label = QLabel(hint)
        self.hint_label.setObjectName("muted")
        self.hint_label.setWordWrap(True)
        self.hint_label.setMinimumHeight(30)
        self.add(self.hint_label)

    def set_value(self, value: str, hint: str = "") -> None:
        self.value_label.setText(value)
        if hint:
            self.hint_label.setText(hint)


class Badge(QLabel):
    """برچسب رنگی کوچک."""

    TONES = {
        "accent": ("accent_soft", "accent"),
        "info": ("info_soft", "info"),
        "warn": ("warn_soft", "warn"),
        "danger": ("danger_soft", "danger"),
        "muted": ("bg", "muted"),
    }

    def __init__(self, text: str = "", tone: str = "muted", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.set_tone(tone)
        self.setAlignment(Qt.AlignCenter)

    def set_tone(self, tone: str) -> None:
        bg, fg = self.TONES.get(tone, self.TONES["muted"])
        self.setStyleSheet(
            f"background-color: {COLORS[bg]}; color: {COLORS[fg]};"
            "border-radius: 10px; padding: 4px 10px; font-size: 11px; font-weight: 700;"
        )


def info_box(parent: Optional[QWidget] = None) -> QLabel:
    label = QLabel(parent=parent)
    label.setWordWrap(True)
    label.setStyleSheet(
        f"background-color: {COLORS['info_soft']}; color: {COLORS['info']};"
        f"border: 1px solid #dce7f0; border-radius: 10px; padding: 12px 14px;"
    )
    return label


def warn_box(parent: Optional[QWidget] = None) -> QLabel:
    label = QLabel(parent=parent)
    label.setWordWrap(True)
    label.setStyleSheet(
        f"background-color: {COLORS['warn_soft']}; color: {COLORS['warn']};"
        f"border: 1px solid #f0e5c8; border-radius: 10px; padding: 12px 14px;"
    )
    return label


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


def row(*widgets: QWidget, spacing: int = 8) -> QHBoxLayout:
    layout = QHBoxLayout()
    layout.setSpacing(spacing)
    for widget in widgets:
        layout.addWidget(widget)
    return layout
