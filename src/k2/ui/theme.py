"""هویت بصری K2: زنده، پرکنتراست و قابل خواندن در مطالعهٔ طولانی.

اصل طراحی: «وضوح». کاربر باید با یک نگاه بفهمد هر کادر نشان‌دهندهٔ چه نوع کاری
است (مطالعه / مرور / آزمون / مهلت / ساعت / عقب‌افتادگی). پس:

* هر نوع کار رنگ اختصاصی دارد و روی کارت به‌شکل نوار رنگی ضخیم دیده می‌شود.
* حاشیهٔ کارت‌ها ضخیم است تا از پس‌زمینهٔ خاکستری روشن جدا شوند (بدون سایه،
  چون Qt Style Sheets از ``box-shadow`` و ``gradient`` پشتیبانی نمی‌کند).
* سلسله‌مراتب تایپوگرافی با شش وزن فونت وزیرمتن ساخته می‌شود، نه فقط با
  اندازه — تیتر، متن، عدد و راهنما هر کدام وزن خودشان را دارند.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from ..jdate import persian_digits

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"

# ---------------------------------------------------------------------------
# پالت رنگ
# ---------------------------------------------------------------------------

COLORS = {
    # --- زمینه و سطح ---
    "bg": "#e9eff1",          # خاکستری-آبی روشن؛ کارت سفید را برجسته می‌کند
    "surface": "#ffffff",
    "surface_soft": "#f2f7f5",
    "surface_sunk": "#e3ebe9",
    "text": "#0b1a18",         # تیره‌تر برای کنتراست بالا
    "text_soft": "#2f4644",
    "muted": "#556967",       # خاکستری تیره‌تر تا راهنماها خوانا بمانند
    "border": "#c9d9d4",       # حاشیهٔ واضحِ کارت
    "border_strong": "#93b2ab",
    "white": "#ffffff",
    "black": "#000000",

    # --- لهجهٔ اصلی (سبزِ زنده) ---
    "accent": "#0a7a57",
    "accent_hover": "#06603f",
    "accent_pressed": "#054c33",
    "accent_soft": "#d3f1e3",
    "accent_line": "#63c8a5",
    "accent_deep": "#053326",

    # --- رنگ معناییِ هر نوع کار ---
    "study": "#0a7a57",        "study_soft": "#d3f1e3",
    "review": "#4639b8",       "review_soft": "#e2e0fb",
    "exam": "#bf5806",         "exam_soft": "#fce9d7",
    "deadline": "#bf2b26",     "deadline_soft": "#fbe2e0",
    "timer": "#0a6d8a",        "timer_soft": "#d6edf6",
    "backlog": "#a93260",      "backlog_soft": "#fbe0ea",
    "class": "#7442ae",        "class_soft": "#ece3fa",
    "problem": "#9c5610",      "problem_soft": "#fcedd9",

    # --- وضعیت ---
    "info": "#1259b8",         "info_soft": "#dbe9fb",
    "warn": "#8f5406",         "warn_soft": "#faecd3",
    "danger": "#ad231b",       "danger_soft": "#fbe1df",
    "ok": "#127a39",           "ok_soft": "#d9f2e0",

    # --- نوار کناری ---
    "sidebar": "#052e26",
    "sidebar_soft": "#0a4536",
    "sidebar_line": "#0f5645",
    "sidebar_text": "#e4f2ed",
    "sidebar_muted": "#8cb2a8",
}

#: نگاشت «تُن» به رنگ متن/زمینه/خط — برای کارت‌ها، کاشی‌ها و برچسب‌ها.
TONES: dict[str, tuple[str, str, str]] = {
    "study":    ("study", "study_soft", "study"),
    "review":   ("review", "review_soft", "review"),
    "exam":     ("exam", "exam_soft", "exam"),
    "deadline": ("deadline", "deadline_soft", "deadline"),
    "timer":    ("timer", "timer_soft", "timer"),
    "backlog":  ("backlog", "backlog_soft", "backlog"),
    "class":    ("class", "class_soft", "class"),
    "problem":  ("problem", "problem_soft", "problem"),
    "accent":   ("accent", "accent_soft", "accent"),
    "info":     ("info", "info_soft", "info"),
    "warn":     ("warn", "warn_soft", "warn"),
    "danger":   ("danger", "danger_soft", "danger"),
    "ok":       ("ok", "ok_soft", "ok"),
    "muted":    ("muted", "surface_sunk", "muted"),
}


def tone_colors(tone: str) -> tuple[str, str, str]:
    """(رنگ متن، رنگ زمینه، رنگ خط) یک تُن را به‌صورت مقدار hex برمی‌گرداند."""
    keys = TONES.get(tone, TONES["accent"])
    return tuple(COLORS[key] for key in keys)  # type: ignore[return-value]


_LOADED_FONT_FAMILY: Optional[str] = None
#: وزن‌های Fونت که در فایل‌های همراه موجود است (برای سلسله‌مراتب بصری).
FONT_WEIGHTS = (400, 500, 600, 700, 800, 900)


def load_fonts() -> str:
    """فونت فارسی همراه برنامه را بارگذاری می‌کند؛ بدون فونت نیز اجرا ادامه می‌یابد.

    هر شش وزن وزیرمتن به‌صورت فایل جداگانه است و همه زیر یک خانواده ثبت
    می‌شوند؛ بنابراین ``QFont(family)`` به‌همراه ``setWeight`` فایل درست را
    انتخاب می‌کند.
    """
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


def base_font(size: int = 10, weight: int = 400) -> QFont:
    """فونت متن پایه با وزن دلخواه (۴۰۰ Regular تا ۹۰۰ Black)."""
    font = QFont(load_fonts())
    font.setPointSize(size)
    font.setWeight(QFont.Weight(weight) if weight in FONT_WEIGHTS else QFont.Weight.Normal)
    return font


def stylesheet() -> str:
    """تم Qt با کنتراست بالا، حاشیهٔ واضح و رنگ معنایی برای هر نوع کار."""
    c = COLORS
    return f"""
    * {{ font-family: "{load_fonts()}"; }}
    QWidget {{
        background-color: transparent;
        color: {c['text']};
        font-size: 13px;
        outline: 0;
    }}
    QMainWindow, QDialog {{ background-color: {c['bg']}; }}
    QWidget#mainSurface, QWidget#pageHost, QWidget#dashboardPage {{ background-color: {c['bg']}; }}

    /* ---------- نوار کناری ---------- */
    QWidget#sidebar {{ background-color: {c['sidebar']}; }}
    QLabel#brandMark {{
        color: {c['white']}; background: {c['accent']}; border-radius: 13px;
        font-size: 20px; font-weight: 900; min-width: 44px; min-height: 44px;
        max-width: 44px; max-height: 44px;
    }}
    QLabel#brandName {{ color: {c['white']}; font-size: 16px; font-weight: 800; }}
    QLabel#brandCaption {{ color: {c['sidebar_muted']}; font-size: 11px; font-weight: 500; }}
    QLabel#sidebarCaption {{
        color: {c['sidebar_muted']}; font-size: 10px; font-weight: 700;
        padding: 14px 10px 6px; letter-spacing: 1px;
    }}
    QLabel#sidebarFooter {{
        color: {c['sidebar_text']}; background: {c['sidebar_soft']};
        border: 1px solid {c['sidebar_line']}; border-radius: 11px;
        padding: 11px; font-size: 11px; font-weight: 600;
    }}
    QListWidget#navigation {{
        background: transparent; border: none; outline: none; padding: 4px 0;
        color: {c['sidebar_text']};
    }}
    QListWidget#navigation::item {{
        min-height: 30px; padding: 11px 14px; margin: 3px 8px;
        border-radius: 10px; color: {c['sidebar_text']};
        font-size: 13px; font-weight: 600;
    }}
    QListWidget#navigation::item:hover {{ background: {c['sidebar_soft']}; color: {c['white']}; }}
    QListWidget#navigation::item:selected {{
        color: {c['white']}; background: {c['accent']}; font-weight: 800;
        border-right: 4px solid {c['accent_line']};
    }}

    /* ---------- نوار بالا و تیترها ---------- */
    QFrame#topBar {{
        background: {c['surface']}; border: 2px solid {c['border']}; border-radius: 15px;
    }}
    QLabel#topTitle {{ color: {c['text']}; font-size: 18px; font-weight: 800; }}
    QLabel#topSubtitle {{ color: {c['muted']}; font-size: 12px; font-weight: 500; }}
    QLabel#dateLabel {{ color: {c['text_soft']}; font-size: 12px; font-weight: 600; }}

    /* ---------- کارت‌ها: حاشیهٔ ضخیم، گوشهٔ گرد و نوار رنگی تُن ---------- */
    QFrame#card {{
        background-color: {c['surface']};
        border: 2px solid {c['border']};
        border-radius: 16px;
    }}
    QFrame#card[tone="study"] {{ background: {c['study_soft']}; border-color: {c['study']}; border-right: 6px solid {c['study']}; }}
    QFrame#card[tone="review"] {{ background: {c['review_soft']}; border-color: {c['review']}; border-right: 6px solid {c['review']}; }}
    QFrame#card[tone="exam"] {{ background: {c['exam_soft']}; border-color: {c['exam']}; border-right: 6px solid {c['exam']}; }}
    QFrame#card[tone="deadline"] {{ background: {c['deadline_soft']}; border-color: {c['deadline']}; border-right: 6px solid {c['deadline']}; }}
    QFrame#card[tone="timer"] {{ background: {c['timer_soft']}; border-color: {c['timer']}; border-right: 6px solid {c['timer']}; }}
    QFrame#card[tone="backlog"] {{ background: {c['backlog_soft']}; border-color: {c['backlog']}; border-right: 6px solid {c['backlog']}; }}
    QFrame#card[tone="class"] {{ background: {c['class_soft']}; border-color: {c['class']}; border-right: 6px solid {c['class']}; }}
    QFrame#card[tone="problem"] {{ background: {c['problem_soft']}; border-color: {c['problem']}; border-right: 6px solid {c['problem']}; }}
    QFrame#card[tone="info"] {{ background: {c['info_soft']}; border-color: {c['info']}; border-right: 6px solid {c['info']}; }}
    QFrame#card[tone="warn"] {{ background: {c['warn_soft']}; border-color: {c['warn']}; border-right: 6px solid {c['warn']}; }}
    QFrame#card[tone="danger"] {{ background: {c['danger_soft']}; border-color: {c['danger']}; border-right: 6px solid {c['danger']}; }}
    QFrame#card[tone="ok"] {{ background: {c['ok_soft']}; border-color: {c['ok']}; border-right: 6px solid {c['ok']}; }}

    /* ---------- کارت قهرمان (خلاصهٔ امروز) ---------- */
    QWidget#heroCard {{
        background-color: {c['accent_soft']};
        border: 2px solid {c['accent_line']};
        border-right: 6px solid {c['accent']};
        border-radius: 18px;
    }}
    QLabel#heroEyebrow {{ color: {c['accent']}; font-size: 11px; font-weight: 800; letter-spacing: 1px; }}
    QLabel#heroTitle {{ color: {c['text']}; font-size: 19px; font-weight: 900; }}
    QLabel#heroBody {{ color: {c['text_soft']}; font-size: 13px; font-weight: 500; }}

    /* ---------- تایپوگرافی ---------- */
    QLabel#cardTitle {{ font-size: 14px; font-weight: 800; color: {c['text']}; }}
    QLabel#muted {{ color: {c['muted']}; font-size: 12px; font-weight: 500; }}
    QLabel#hint {{ color: {c['muted']}; font-size: 11px; font-weight: 500; }}
    QLabel#bigNumber {{ font-size: 26px; font-weight: 900; color: {c['accent']}; }}
    QLabel#sectionTitle {{ font-size: 17px; font-weight: 900; color: {c['text']}; padding: 2px 0; }}
    QLabel#pageLead {{ color: {c['text_soft']}; font-size: 13px; font-weight: 500; }}
    QLabel#metricAccent {{ color: {c['accent']}; font-weight: 700; }}
    QLabel#metricInfo {{ color: {c['info']}; font-weight: 700; }}
    QLabel#metricWarn {{ color: {c['warn']}; font-weight: 700; }}
    QLabel#metricDanger {{ color: {c['danger']}; font-weight: 700; }}

    /* ---------- دکمه‌ها ---------- */
    QPushButton {{
        background: {c['surface']}; border: 2px solid {c['border']};
        border-radius: 10px; padding: 9px 16px; color: {c['text']};
        min-height: 20px; font-weight: 700; font-size: 13px;
    }}
    QPushButton:hover {{ background: {c['surface_soft']}; border-color: {c['border_strong']}; }}
    QPushButton:pressed {{ background: {c['accent_soft']}; border-color: {c['accent']}; }}
    QPushButton:disabled {{ color: #9aabaa; background: {c['surface_sunk']}; border-color: {c['border']}; }}
    QPushButton#primary {{
        background: {c['accent']}; border-color: {c['accent']}; color: {c['white']};
        font-weight: 800; padding: 10px 20px;
    }}
    QPushButton#primary:hover {{ background: {c['accent_hover']}; border-color: {c['accent_hover']}; }}
    QPushButton#primary:pressed {{ background: {c['accent_pressed']}; }}
    QPushButton#soft {{
        background: {c['accent_soft']}; border-color: {c['accent_line']}; color: {c['accent']};
        font-weight: 700;
    }}
    QPushButton#soft:hover {{ background: {c['accent']}; color: {c['white']}; }}
    QPushButton#danger {{
        background: {c['danger_soft']}; color: {c['danger']}; border-color: {c['danger']};
        font-weight: 700;
    }}
    QPushButton#danger:hover {{ background: {c['danger']}; color: {c['white']}; }}

    /* ---------- ورودی‌ها و فهرست‌ها ---------- */
    QListWidget, QTreeWidget, QTableWidget, QTextEdit, QPlainTextEdit,
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit {{
        background: {c['surface']}; border: 2px solid {c['border']};
        border-radius: 9px; padding: 8px 10px;
        selection-background-color: {c['accent_soft']}; selection-color: {c['text']};
    }}
    QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus,
    QDoubleSpinBox:focus {{ border: 2px solid {c['accent']}; }}

    /* ---------- کادر ساعت و تاریخ (ترکیبی، یک قالب واحد) ----------
       بخش‌های درونی باید کاملاً شفاف شوند، وگرنه قاعدهٔ عمومی QLineEdit
       و QSpinBox برایشان قاب و padding می‌گذارد و جای متن نمی‌ماند. */
    QFrame#timeBox {{
        background: {c['surface']}; border: 2px solid {c['border']};
        border-radius: 9px; padding: 1px 6px;
    }}
    QFrame#timeBox[active="true"] {{ border: 2px solid {c['accent']}; }}
    QFrame#timeBox QLineEdit {{
        background: transparent; border: none; padding: 0; selection-background-color: {c['accent_soft']};
    }}
    QSpinBox#timeHour {{
        font-size: 15px; font-weight: 700;
        background: transparent; border: none; padding: 0 1px;
    }}
    QSpinBox#timeMinute {{
        font-size: 13px; font-weight: 400;
        background: transparent; border: none; padding: 0 1px;
    }}
    QSpinBox#timeDate {{
        font-size: 13px; font-weight: 500;
        background: transparent; border: none; padding: 0 1px;
    }}
    QSpinBox#timeHour:focus, QSpinBox#timeMinute:focus, QSpinBox#timeDate:focus {{
        background: transparent; border: none;
    }}
    QLabel#timeColon {{ font-size: 14px; font-weight: 700; color: {c['muted']}; background: transparent; border: none; padding: 0; }}
    QLabel#dateSlash {{ font-size: 13px; font-weight: 500; color: {c['muted']}; background: transparent; border: none; padding: 0; }}
    /* قالب تودرتو: قالب بیرونی کادر را می‌سازد، این یکی فقط چیدمان است. */
    QFrame#timeBoxInner {{ background: transparent; border: none; padding: 0; }}
    QFrame#timeBoxInner QLineEdit {{ background: transparent; border: none; padding: 0; }}
    QFrame#timeBoxInner QSpinBox {{ background: transparent; border: none; }}
    QListWidget::item, QTreeWidget::item {{ padding: 6px 4px; border-radius: 6px; }}
    QListWidget::item:selected, QTreeWidget::item:selected {{
        background: {c['accent_soft']}; color: {c['text']};
        border-radius: 6px; font-weight: 700;
    }}
    QHeaderView::section {{
        background: {c['surface_sunk']}; border: none;
        border-bottom: 2px solid {c['border']}; padding: 10px;
        font-weight: 800; color: {c['text_soft']}; font-size: 12px;
    }}
    QTableWidget {{ gridline-color: {c['border']}; alternate-background-color: {c['surface_soft']}; }}
    QTableWidget::item {{ padding: 5px 8px; }}
    QTabWidget::pane {{ border: 2px solid {c['border']}; border-radius: 11px; background: {c['surface']}; top: -1px; }}
    QTabBar::tab {{
        background: {c['surface_sunk']}; border: 2px solid {c['border']};
        padding: 9px 18px; border-top-left-radius: 9px; border-top-right-radius: 9px;
        font-weight: 700; color: {c['text_soft']};
    }}
    QTabBar::tab:selected {{ background: {c['surface']}; color: {c['accent']}; font-weight: 800; }}
    QGroupBox {{
        border: 2px solid {c['border']}; border-radius: 12px;
        margin-top: 16px; padding: 14px 12px 12px; background: {c['surface']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin; right: 12px; padding: 0 6px;
        color: {c['text_soft']}; font-weight: 800;
    }}
    QScrollArea {{ background: transparent; border: none; }}
    QScrollBar:vertical {{ background: transparent; width: 12px; margin: 3px; }}
    QScrollBar::handle:vertical {{ background: {c['border_strong']}; border-radius: 6px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: {c['accent_line']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

    /* ---------- منوها ---------- */
    QMenuBar#appMenuBar {{
        background: {c['surface']}; color: {c['text']};
        border-bottom: 2px solid {c['border']}; padding: 5px 10px; spacing: 5px;
    }}
    QMenuBar#appMenuBar::item {{
        background: transparent; color: {c['text']}; padding: 8px 16px;
        margin: 2px 3px; border-radius: 9px; min-height: 22px; font-weight: 700;
    }}
    QMenuBar#appMenuBar::item:selected, QMenuBar#appMenuBar::item:pressed {{
        background: {c['accent_soft']}; color: {c['accent']};
    }}
    QMenu {{
        background-color: {c['surface']}; color: {c['text']};
        border: 2px solid {c['border']}; border-radius: 13px;
        padding: 8px; min-width: 250px;
    }}
    QMenu::item {{
        background: transparent; color: {c['text']}; padding: 11px 18px;
        margin: 2px 1px; min-height: 24px; border-radius: 8px; font-weight: 600;
    }}
    QMenu::item:selected {{ background: {c['accent_soft']}; color: {c['accent']}; font-weight: 800; }}
    QMenu::item:disabled {{ color: {c['muted']}; }}
    QMenu::separator {{ height: 2px; margin: 6px 10px; background: {c['border']}; }}

    /* ---------- نوار وضعیت و راهنما ---------- */
    QStatusBar {{ background: {c['surface']}; color: {c['muted']}; border-top: 2px solid {c['border']}; }}
    QToolTip {{
        background: {c['text']}; color: {c['white']}; border: none;
        padding: 8px 11px; border-radius: 6px; font-weight: 600;
    }}
    QMessageBox {{ background: {c['surface']}; }}
    QLabel#privacyDot {{ color: {c['ok']}; font-weight: 900; }}
    """


def apply_theme(app: QApplication, size: int = 10) -> None:
    app.setLayoutDirection(Qt.RightToLeft)
    app.setFont(base_font(size))
    app.setStyleSheet(stylesheet())


def digits(text: str, persian: bool = True) -> str:
    return persian_digits(text) if persian else text
