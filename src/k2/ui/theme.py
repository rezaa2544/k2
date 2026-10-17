"""تم، فونت فارسی و راست‌چین‌سازی رابط کاربری."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from ..jdate import persian_digits

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"

#: رنگ‌های تم. عمداً خنثی و کم‌تنش (بدون رنگ‌های «هشدار/اضطراب‌آور»).
COLORS = {
    "bg": "#f6f7f9",
    "surface": "#ffffff",
    "text": "#1f2933",
    "muted": "#5b6673",
    "border": "#dfe3e8",
    "accent": "#2f6f4e",
    "accent_soft": "#e8f2ec",
    "info": "#3b5b8c",
    "info_soft": "#e9eef6",
    "warn": "#8a6d1f",
    "warn_soft": "#fbf3df",
    "danger": "#8c3b3b",
    "danger_soft": "#f7eaea",
}

#: فونت بارگذاری‌شده (برای تست و گزارش).
_LOADED_FONT_FAMILY: Optional[str] = None


def load_fonts() -> str:
    """فونت فارسی را از پوشهٔ ``assets/fonts`` بارگذاری می‌کند.

    اگر فونت موجود نباشد (مثلاً در بستهٔ ناقص)، از فونت پیش‌فرض سیستم
    استفاده می‌شود و برنامه همچنان کار می‌کند.
    """
    global _LOADED_FONT_FAMILY
    if _LOADED_FONT_FAMILY:
        return _LOADED_FONT_FAMILY

    for path in sorted(FONTS_DIR.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(path))

    family = ""
    for path in sorted(FONTS_DIR.glob("*.ttf")):
        font_id = QFontDatabase.addApplicationFont(str(path))
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            family = families[0]
            break

    if not family:
        family = QFont().defaultFamily()

    _LOADED_FONT_FAMILY = family
    return family


def base_font(size: int = 11) -> QFont:
    """فونت پایهٔ برنامه."""
    font = QFont(load_fonts())
    font.setPointSize(size)
    return font


def stylesheet() -> str:
    """شیوه‌نامهٔ سراسری (RTL-پسند)."""
    return f"""
    QWidget {{
        background-color: {COLORS['bg']};
        color: {COLORS['text']};
        font-size: 13px;
    }}
    QMainWindow, QDialog {{ background-color: {COLORS['bg']}; }}
    QFrame#card {{
        background-color: {COLORS['surface']};
        border: 1px solid {COLORS['border']};
        border-radius: 10px;
    }}
    QLabel#cardTitle {{
        font-size: 15px;
        font-weight: bold;
        color: {COLORS['text']};
    }}
    QLabel#muted {{ color: {COLORS['muted']}; }}
    QLabel#bigNumber {{
        font-size: 22px;
        font-weight: bold;
        color: {COLORS['accent']};
    }}
    QLabel#sectionTitle {{
        font-size: 14px;
        font-weight: bold;
        padding: 4px 0;
    }}
    QPushButton {{
        background-color: {COLORS['surface']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 6px 14px;
        color: {COLORS['text']};
    }}
    QPushButton:hover {{ border-color: {COLORS['accent']}; }}
    QPushButton:disabled {{ color: {COLORS['muted']}; background-color: {COLORS['bg']}; }}
    QPushButton#primary {{
        background-color: {COLORS['accent']};
        color: #ffffff;
        border: 1px solid {COLORS['accent']};
        font-weight: bold;
    }}
    QPushButton#primary:hover {{ background-color: {COLORS['accent_soft']}; color: {COLORS['text']}; }}
    QPushButton#danger {{
        background-color: {COLORS['danger_soft']};
        color: {COLORS['danger']};
        border: 1px solid {COLORS['danger']};
    }}
    QListWidget, QTreeWidget, QTableWidget, QTextEdit, QPlainTextEdit, QComboBox,
    QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit {{
        background-color: {COLORS['surface']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 4px;
        selection-background-color: {COLORS['accent_soft']};
        selection-color: {COLORS['text']};
    }}
    QListWidget::item:selected, QTreeWidget::item:selected {{
        background-color: {COLORS['accent_soft']};
        color: {COLORS['text']};
    }}
    QHeaderView::section {{
        background-color: {COLORS['bg']};
        border: none;
        border-bottom: 1px solid {COLORS['border']};
        padding: 6px;
        font-weight: bold;
    }}
    QTabBar::tab {{
        background: {COLORS['surface']};
        border: 1px solid {COLORS['border']};
        border-bottom: none;
        padding: 6px 14px;
        border-top-right-radius: 6px;
        border-top-left-radius: 6px;
    }}
    QTabBar::tab:selected {{
        background: {COLORS['accent_soft']};
        color: {COLORS['accent']};
    }}
    QGroupBox {{
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        margin-top: 14px;
        padding-top: 8px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        right: 12px;
        padding: 0 4px;
        color: {COLORS['muted']};
    }}
    QScrollBar:vertical {{ background: {COLORS['bg']}; width: 10px; }}
    QScrollBar::handle:vertical {{
        background: {COLORS['border']}; border-radius: 5px; min-height: 24px;
    }}
    QStatusBar {{ background: {COLORS['surface']}; color: {COLORS['muted']}; }}
    QToolTip {{
        background-color: {COLORS['surface']};
        color: {COLORS['text']};
        border: 1px solid {COLORS['border']};
        padding: 4px;
    }}
    """


def apply_theme(app: QApplication, size: int = 11) -> None:
    """تم، فونت و راست‌چین‌سازی را اعمال می‌کند."""
    app.setLayoutDirection(Qt.RightToLeft)
    app.setFont(base_font(size))
    app.setStyleSheet(stylesheet())


def digits(text: str, persian: bool = True) -> str:
    """تبدیل ارقام برای نمایش."""
    return persian_digits(text) if persian else text
