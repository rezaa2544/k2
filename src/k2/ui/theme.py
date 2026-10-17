"""هویت بصری K2: آرام، خوانا و مناسب مطالعهٔ طولانی."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from ..jdate import persian_digits

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"

COLORS = {
    "bg": "#f3f6f8",
    "surface": "#ffffff",
    "surface_soft": "#f8fafb",
    "text": "#182b2a",
    "muted": "#687b7a",
    "border": "#e2e9e8",
    "accent": "#176b55",
    "accent_hover": "#105742",
    "accent_soft": "#e4f2ed",
    "sidebar": "#102d2a",
    "sidebar_soft": "#193c37",
    "sidebar_text": "#d9e8e4",
    "sidebar_muted": "#91aaa4",
    "info": "#385f88",
    "info_soft": "#eaf1f8",
    "warn": "#87641b",
    "warn_soft": "#fbf4e4",
    "danger": "#8a4848",
    "danger_soft": "#faeeee",
    "white": "#ffffff",
}

_LOADED_FONT_FAMILY: Optional[str] = None


def load_fonts() -> str:
    """فونت فارسی همراه برنامه را بارگذاری می‌کند؛ بدون فونت نیز اجرا ادامه می‌یابد."""
    global _LOADED_FONT_FAMILY
    if _LOADED_FONT_FAMILY:
        return _LOADED_FONT_FAMILY

    family = ""
    for path in sorted(FONTS_DIR.glob("*.ttf")):
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id >= 0 and not family:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                family = families[0]
    _LOADED_FONT_FAMILY = family or QFont().defaultFamily()
    return _LOADED_FONT_FAMILY


def base_font(size: int = 10) -> QFont:
    font = QFont(load_fonts())
    font.setPointSize(size)
    return font


def stylesheet() -> str:
    """تم Qt با سطوح روشن و کنتراست آرام؛ ویجت‌های داخلی شفاف می‌مانند."""
    c = COLORS
    return f"""
    QWidget {{
        background-color: transparent;
        color: {c['text']};
        font-size: 13px;
        outline: 0;
    }}
    QMainWindow, QDialog {{ background-color: {c['bg']}; }}
    QWidget#mainSurface, QWidget#pageHost, QWidget#dashboardPage {{ background-color: {c['bg']}; }}
    QWidget#sidebar {{ background-color: {c['sidebar']}; }}
    QLabel#brandMark {{
        color: {c['white']}; background: {c['accent']}; border-radius: 12px;
        font-size: 19px; font-weight: 800; min-width: 42px; min-height: 42px;
        max-width: 42px; max-height: 42px;
    }}
    QLabel#brandName {{ color: {c['white']}; font-size: 16px; font-weight: 700; }}
    QLabel#brandCaption {{ color: {c['sidebar_muted']}; font-size: 11px; }}
    QLabel#sidebarCaption {{ color: {c['sidebar_muted']}; font-size: 10px; font-weight: 700; padding: 12px 10px 5px; }}
    QLabel#sidebarFooter {{ color: {c['sidebar_text']}; background: {c['sidebar_soft']}; border-radius: 10px; padding: 10px; font-size: 11px; }}
    QListWidget#navigation {{
        background: transparent; border: none; outline: none; padding: 4px 0;
        color: {c['sidebar_text']};
    }}
    QListWidget#navigation::item {{
        min-height: 28px; padding: 10px 13px; margin: 3px 8px;
        border-radius: 9px; color: {c['sidebar_text']};
    }}
    QListWidget#navigation::item:hover {{ background: {c['sidebar_soft']}; }}
    QListWidget#navigation::item:selected {{
        color: {c['white']}; background: {c['accent']}; font-weight: 700;
        border-right: 3px solid #8dd5b9;
    }}
    QFrame#topBar {{
        background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 14px;
    }}
    QLabel#topTitle {{ color: {c['text']}; font-size: 17px; font-weight: 700; }}
    QLabel#topSubtitle {{ color: {c['muted']}; font-size: 11px; }}
    QFrame#card {{
        background-color: {c['surface']}; border: 1px solid {c['border']};
        border-radius: 14px;
    }}
    QWidget#heroCard {{
        background-color: #e8f3ef; border: 1px solid #d6e9e1; border-radius: 17px;
    }}
    QLabel#heroEyebrow {{ color: {c['accent']}; font-size: 11px; font-weight: 700; }}
    QLabel#heroTitle {{ color: {c['text']}; font-size: 18px; font-weight: 800; }}
    QLabel#heroBody {{ color: {c['muted']}; font-size: 12px; }}
    QLabel#cardTitle {{ font-size: 13px; font-weight: 700; color: {c['text']}; }}
    QLabel#muted {{ color: {c['muted']}; }}
    QLabel#bigNumber {{ font-size: 22px; font-weight: 800; color: {c['accent']}; }}
    QLabel#sectionTitle {{ font-size: 17px; font-weight: 800; color: {c['text']}; padding: 2px 0; }}
    QLabel#metricAccent {{ color: {c['accent']}; }}
    QLabel#metricInfo {{ color: {c['info']}; }}
    QLabel#metricWarn {{ color: {c['warn']}; }}
    QLabel#metricDanger {{ color: {c['danger']}; }}
    QPushButton {{
        background: {c['surface']}; border: 1px solid {c['border']};
        border-radius: 9px; padding: 8px 14px; color: {c['text']};
        min-height: 18px; font-weight: 600;
    }}
    QPushButton:hover {{ background: {c['surface_soft']}; border-color: #b9ceca; }}
    QPushButton:pressed {{ background: {c['accent_soft']}; }}
    QPushButton:disabled {{ color: #9aabaa; background: {c['bg']}; }}
    QPushButton#primary {{ background: {c['accent']}; border-color: {c['accent']}; color: {c['white']}; font-weight: 700; }}
    QPushButton#primary:hover {{ background: {c['accent_hover']}; border-color: {c['accent_hover']}; }}
    QPushButton#primary:pressed {{ background: #0d4b3b; }}
    QPushButton#danger {{ background: {c['danger_soft']}; color: {c['danger']}; border-color: #eedada; }}
    QListWidget, QTreeWidget, QTableWidget, QTextEdit, QPlainTextEdit,
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit {{
        background: {c['surface']}; border: 1px solid {c['border']};
        border-radius: 8px; padding: 7px 9px;
        selection-background-color: {c['accent_soft']}; selection-color: {c['text']};
    }}
    QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus,
    QDoubleSpinBox:focus {{ border: 1px solid {c['accent']}; }}
    QListWidget::item:selected, QTreeWidget::item:selected {{ background: {c['accent_soft']}; color: {c['text']}; border-radius: 5px; }}
    QHeaderView::section {{ background: {c['surface_soft']}; border: none; border-bottom: 1px solid {c['border']}; padding: 9px; font-weight: 700; color: {c['muted']}; }}
    QTableWidget {{ gridline-color: {c['border']}; alternate-background-color: {c['surface_soft']}; }}
    QTabWidget::pane {{ border: 1px solid {c['border']}; border-radius: 10px; background: {c['surface']}; top: -1px; }}
    QTabBar::tab {{ background: {c['surface_soft']}; border: 1px solid {c['border']}; padding: 8px 16px; border-top-left-radius: 8px; border-top-right-radius: 8px; }}
    QTabBar::tab:selected {{ background: {c['surface']}; color: {c['accent']}; font-weight: 700; }}
    QGroupBox {{ border: 1px solid {c['border']}; border-radius: 10px; margin-top: 14px; padding: 12px 10px 10px; }}
    QGroupBox::title {{ subcontrol-origin: margin; right: 12px; padding: 0 5px; color: {c['muted']}; font-weight: 700; }}
    QScrollArea {{ background: transparent; border: none; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 3px; }}
    QScrollBar::handle:vertical {{ background: #cbd8d5; border-radius: 5px; min-height: 28px; }}
    QScrollBar::handle:vertical:hover {{ background: #a9bfba; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QMenuBar#appMenuBar {{
        background: {c['surface']}; color: {c['text']};
        border-bottom: 1px solid {c['border']}; padding: 4px 10px; spacing: 4px;
    }}
    QMenuBar#appMenuBar::item {{
        background: transparent; color: {c['text']}; padding: 7px 15px;
        margin: 2px 3px; border-radius: 8px; min-height: 20px; font-weight: 600;
    }}
    QMenuBar#appMenuBar::item:selected, QMenuBar#appMenuBar::item:pressed {{
        background: {c['accent_soft']}; color: {c['accent']};
    }}
    QMenu {{
        background-color: {c['surface']}; color: {c['text']};
        border: 1px solid {c['border']}; border-radius: 12px;
        padding: 7px; min-width: 245px;
    }}
    QMenu::item {{
        background: transparent; color: {c['text']}; padding: 10px 18px;
        margin: 2px 1px; min-height: 22px; border-radius: 7px;
    }}
    QMenu::item:selected {{ background: {c['accent_soft']}; color: {c['accent']}; font-weight: 700; }}
    QMenu::item:disabled {{ color: {c['muted']}; }}
    QMenu::separator {{ height: 1px; margin: 5px 9px; background: {c['border']}; }}
    QStatusBar {{ background: {c['surface']}; color: {c['muted']}; border-top: 1px solid {c['border']}; }}
    QToolTip {{ background: {c['text']}; color: {c['white']}; border: none; padding: 6px 9px; border-radius: 5px; }}
    QMessageBox {{ background: {c['surface']}; }}
    """


def apply_theme(app: QApplication, size: int = 10) -> None:
    app.setLayoutDirection(Qt.RightToLeft)
    app.setFont(base_font(size))
    app.setStyleSheet(stylesheet())


def digits(text: str, persian: bool = True) -> str:
    return persian_digits(text) if persian else text
