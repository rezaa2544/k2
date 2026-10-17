"""پنجرهٔ اصلی K2 با ناوبری روشن، ساده و راست‌چین."""

from __future__ import annotations

import datetime as _dt
from typing import Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..jdate import format_jalali_long
from ..service import AdvisorService
from .views import (
    ActivitiesPage,
    DashboardPage,
    ExamsPage,
    OnboardingWizard,
    ReportsPage,
    ReviewPage,
    SettingsPage,
    TodayPlanPage,
)

APP_TITLE = "مشاور هوشمند کنکور"
NAV_ITEMS = [
    ("⌂   داشبورد", "داشبورد", "نمای کلی روز و ظرفیت"),
    ("◷   برنامهٔ امروز", "برنامهٔ امروز", "کارهای امروز و زمان‌بندی"),
    ("▦   فعالیت‌ها", "فعالیت‌ها", "ثبت و پیگیری مطالعه"),
    ("◎   آزمون و تحلیل", "آزمون و تحلیل", "نتیجه و تحلیل سؤال‌ها"),
    ("↻   مرور تطبیقی", "مرور تطبیقی", "مرور بر اساس یادگیری"),
    ("▤   گزارش‌ها", "گزارش‌ها", "گزارش روزانه و هفتگی"),
    ("⚙   تنظیمات", "تنظیمات", "ترجیحات و پشتیبان‌گیری"),
]


class MainWindow(QMainWindow):
    """پنجرهٔ اصلی برنامه."""

    def __init__(self, service: AdvisorService, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.service = service
        self.setObjectName("mainWindow")
        self.setWindowTitle(APP_TITLE)
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(1260, 820)
        self.setMinimumSize(980, 650)

        self._build()
        self._build_menu()
        self.refresh_all()
        self._onboarding_auto_pending = not self.service.onboarding_completed()

    def _build(self) -> None:
        central = QWidget()
        central.setObjectName("mainSurface")
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._build_sidebar(root)
        self._build_content(root)
        self.setCentralWidget(central)

        status = QStatusBar()
        status.setSizeGripEnabled(False)
        self.status_label = QLabel("آمادهٔ شروع یک روز متعادل")
        status.addWidget(self.status_label, 1)
        status.addPermanentWidget(QLabel("●  داده‌ها فقط روی این دستگاه ذخیره می‌شوند"))
        self.setStatusBar(status)

    def _build_sidebar(self, root: QHBoxLayout) -> None:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(246)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(14, 20, 14, 16)
        side.setSpacing(5)

        brand = QHBoxLayout()
        brand.setSpacing(11)
        mark = QLabel("K2")
        mark.setObjectName("brandMark")
        mark.setAlignment(Qt.AlignCenter)
        brand.addWidget(mark)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(2)
        name = QLabel("مشاور هوشمند")
        name.setObjectName("brandName")
        caption = QLabel("کنکور · برنامه‌ریزی واقع‌بینانه")
        caption.setObjectName("brandCaption")
        brand_text.addWidget(name)
        brand_text.addWidget(caption)
        brand.addLayout(brand_text, 1)
        side.addLayout(brand)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background:#294541; border:none; margin-top:16px; margin-bottom:8px;")
        side.addWidget(divider)
        section = QLabel("فضای مطالعه")
        section.setObjectName("sidebarCaption")
        side.addWidget(section)

        self.nav = QListWidget()
        self.nav.setObjectName("navigation")
        self.nav.setAccessibleName("بخش‌های برنامه")
        self.nav.setSpacing(1)
        self.nav.setSelectionMode(QListWidget.SingleSelection)
        self._nav_items = []
        for label, title, hint in NAV_ITEMS:
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, len(self._nav_items))
            item.setToolTip(hint)
            item.setData(Qt.AccessibleTextRole, f"{title}؛ {hint}")
            self.nav.addItem(item)
            self._nav_items.append(item)
        self.nav.currentRowChanged.connect(self._on_nav)
        side.addWidget(self.nav, 1)

        footer = QLabel("●   آفلاین و خصوصی\n\nبرنامه‌ریزی با توجه به ظرفیت واقعی شما")
        footer.setObjectName("sidebarFooter")
        footer.setWordWrap(True)
        side.addWidget(footer)
        root.addWidget(sidebar)

    def _build_content(self, root: QHBoxLayout) -> None:
        host = QWidget()
        host.setObjectName("pageHost")
        content = QVBoxLayout(host)
        content.setContentsMargins(20, 16, 20, 12)
        content.setSpacing(14)

        topbar = QFrame()
        topbar.setObjectName("topBar")
        topbar.setFixedHeight(70)
        top = QHBoxLayout(topbar)
        top.setContentsMargins(17, 10, 17, 10)
        top.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.page_title = QLabel("داشبورد")
        self.page_title.setObjectName("topTitle")
        self.page_hint = QLabel("یک نگاه کوتاه؛ بعد فقط قدم بعدی")
        self.page_hint.setObjectName("topSubtitle")
        title_box.addWidget(self.page_title)
        title_box.addWidget(self.page_hint)
        top.addLayout(title_box, 1)

        self.date_label = QLabel(format_jalali_long(_dt.date.today()))
        self.date_label.setObjectName("muted")
        top.addWidget(self.date_label)
        self.refresh_button = QPushButton("↻  تازه‌سازی")
        self.refresh_button.setToolTip("به‌روزرسانی همهٔ نماها")
        self.refresh_button.clicked.connect(self.refresh_all)
        top.addWidget(self.refresh_button)
        content.addWidget(topbar)

        self.stack = QStackedWidget()
        self.stack.setObjectName("pageStack")
        self.dashboard = DashboardPage(self.service)
        self.today = TodayPlanPage(self.service)
        self.activities = ActivitiesPage(self.service)
        self.exams = ExamsPage(self.service)
        self.review = ReviewPage(self.service)
        self.reports = ReportsPage(self.service)
        self.settings = SettingsPage(self.service)
        for page in (
            self.dashboard, self.today, self.activities, self.exams,
            self.review, self.reports, self.settings,
        ):
            self.stack.addWidget(page)
        content.addWidget(self.stack, 1)
        root.addWidget(host, 1)
        self.nav.setCurrentRow(0)

    def _build_menu(self) -> None:
        # استفاده از نوار منوی Qt به‌جای منوی بومی سیستم‌عامل، برای نمایش
        # یکنواخت و خوانای آیتم‌ها در Windows و Linux.
        self.menuBar().setNativeMenuBar(False)
        self.menuBar().setObjectName("appMenuBar")
        self.menu_program = self.menuBar().addMenu("برنامه")
        self.menu_program.setObjectName("programMenu")
        self.menu_program.setToolTipsVisible(True)

        self.action_setup = QAction("راه‌اندازی / ادامهٔ مصاحبه", self)
        self.action_setup.setStatusTip("ادامه یا آغاز راه‌اندازی مرحله‌ای برنامه")
        self.action_setup.setToolTip(self.action_setup.statusTip())
        self.action_setup.triggered.connect(self.run_onboarding)
        self.menu_program.addAction(self.action_setup)

        self.action_refresh = QAction("تازه‌سازی همهٔ نماها", self)
        self.action_refresh.setShortcut("F5")
        self.action_refresh.setStatusTip("به‌روزرسانی اطلاعات صفحه‌های برنامه")
        self.action_refresh.setToolTip("F5 — " + self.action_refresh.statusTip())
        self.action_refresh.triggered.connect(self.refresh_all)
        self.menu_program.addAction(self.action_refresh)

        self.menu_program.addSeparator()
        self.action_quit = QAction("خروج از برنامه", self)
        self.action_quit.setShortcut("Ctrl+Q")
        self.action_quit.setStatusTip("بستن مشاور هوشمند کنکور")
        self.action_quit.triggered.connect(self.close)
        self.menu_program.addAction(self.action_quit)

        self.menu_help = self.menuBar().addMenu("راهنما")
        self.menu_help.setObjectName("helpMenu")
        self.menu_help.setToolTipsVisible(True)
        self.action_about = QAction("دربارهٔ K2", self)
        self.action_about.setStatusTip("نسخه و توضیحات برنامه")
        self.action_about.triggered.connect(self.show_about)
        self.menu_help.addAction(self.action_about)

    def _on_nav(self, row: int) -> None:
        if row < 0 or not hasattr(self, "stack"):
            return
        self.stack.setCurrentIndex(row)
        _, title, hint = NAV_ITEMS[row]
        self.page_title.setText(title)
        self.page_hint.setText(hint)
        self.date_label.setText(format_jalali_long(_dt.date.today()))
        page = self.stack.currentWidget()
        if hasattr(page, "refresh"):
            page.refresh()

    def refresh_all(self) -> None:
        for index in range(self.stack.count()):
            page = self.stack.widget(index)
            if hasattr(page, "refresh"):
                try:
                    page.refresh()
                except Exception as exc:  # noqa: BLE001
                    self.status_label.setText(f"خطا در به‌روزرسانی نما: {exc}")
                    return
        self.date_label.setText(format_jalali_long(_dt.date.today()))
        self.status_label.setText(
            f"اطلاعات محلی ذخیره شد · {self.service.db_path}"
        )

    def start_first_run_onboarding(self) -> None:
        """پس از نمایش پنجره، راه‌اندازی ناقص را خودکار آغاز/ادامه می‌کند."""
        if self._onboarding_auto_pending:
            QTimer.singleShot(0, self._run_first_onboarding)

    def _run_first_onboarding(self) -> None:
        if not self._onboarding_auto_pending or self.service.onboarding_completed():
            return
        self._onboarding_auto_pending = False
        self.run_onboarding()

    def run_onboarding(self) -> None:
        wizard = OnboardingWizard(self.service, self)
        wizard.exec()
        self.refresh_all()

    def show_about(self) -> None:
        from .. import __version__

        QMessageBox.about(
            self,
            "دربارهٔ برنامه",
            f"<b>{APP_TITLE}</b> نسخهٔ {__version__}<br><br>"
            "نرم‌افزار دسکتاپ فارسی، راست‌چین و آفلاین‌محور برای برنامه‌ریزی "
            "واقع‌بینانهٔ مطالعه، مدیریت عقب‌افتادگی، مرور تطبیقی، تحلیل آزمون "
            "و مشاورهٔ آموزشی.<br><br>"
            "این برنامه تشخیص پزشکی یا روان‌شناختی ارائه نمی‌دهد و هیچ داده‌ای "
            "به اینترنت ارسال نمی‌کند.",
        )
