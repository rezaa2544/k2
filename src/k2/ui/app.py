"""پنجرهٔ اصلی برنامه."""

from __future__ import annotations

import datetime as _dt
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..service import AdvisorService
from .theme import apply_theme
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


class MainWindow(QMainWindow):
    """پنجرهٔ اصلی با ناوبری راست‌چین."""

    def __init__(self, service: AdvisorService, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle(APP_TITLE)
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(1180, 760)

        self._build()
        self._build_menu()
        self.refresh_all()

    # ---- ساخت ----

    def _build(self) -> None:
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.nav = QListWidget()
        self.nav.setFixedWidth(210)
        self.nav.setStyleSheet(
            "QListWidget { border-left: none; border-top: none; border-bottom: none;"
            "border-right: 1px solid #dfe3e8; }"
        )
        self._nav_items = [
            ("داشبورد", 0),
            ("برنامهٔ امروز", 1),
            ("فعالیت‌ها", 2),
            ("آزمون و تحلیل", 3),
            ("مرور تطبیقی", 4),
            ("گزارش‌ها", 5),
            ("تنظیمات", 6),
        ]
        for title, index in self._nav_items:
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, index)
            self.nav.addItem(item)
        self.nav.currentRowChanged.connect(self._on_nav)
        self.nav.setCurrentRow(0)
        layout.addWidget(self.nav)

        self.stack = QStackedWidget()
        self.dashboard = DashboardPage(self.service)
        self.today = TodayPlanPage(self.service)
        self.activities = ActivitiesPage(self.service)
        self.exams = ExamsPage(self.service)
        self.review = ReviewPage(self.service)
        self.reports = ReportsPage(self.service)
        self.settings = SettingsPage(self.service)
        for page in (
            self.dashboard,
            self.today,
            self.activities,
            self.exams,
            self.review,
            self.reports,
            self.settings,
        ):
            self.stack.addWidget(page)
        layout.addWidget(self.stack, 1)

        self.setCentralWidget(central)

        status = QStatusBar()
        self.status_label = QLabel("آماده")
        status.addWidget(self.status_label)
        self.setStatusBar(status)

    def _build_menu(self) -> None:
        menu = self.menuBar().addMenu("برنامه")
        action_setup = QAction("راه‌اندازی / مصاحبهٔ دوباره", self)
        action_setup.triggered.connect(self.run_onboarding)
        menu.addAction(action_setup)

        action_refresh = QAction("بازسازی همهٔ نماها", self)
        action_refresh.triggered.connect(self.refresh_all)
        menu.addAction(action_refresh)

        action_quit = QAction("خروج", self)
        action_quit.triggered.connect(self.close)
        menu.addAction(action_quit)

        help_menu = self.menuBar().addMenu("راهنما")
        action_about = QAction("دربارهٔ برنامه", self)
        action_about.triggered.connect(self.show_about)
        help_menu.addAction(action_about)

    # ---- ناوبری ----

    def _on_nav(self, row: int) -> None:
        if row < 0 or not hasattr(self, "stack"):
            return
        self.stack.setCurrentIndex(row)
        page = self.stack.currentWidget()
        if hasattr(page, "refresh"):
            page.refresh()

    def refresh_all(self) -> None:
        for index in range(self.stack.count()):
            page = self.stack.widget(index)
            if hasattr(page, "refresh"):
                try:
                    page.refresh()
                except Exception as exc:  # noqa: BLE001 - نمای خراب نباید کل برنامه را بخواباند
                    self.status_label.setText(f"خطا در به‌روزرسانی نما: {exc}")
                    return
        today = _dt.date.today()
        self.status_label.setText(
            f"{APP_TITLE} — داده‌ها به‌صورت محلی در {self.service.db_path} ذخیره می‌شود."
        )

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
