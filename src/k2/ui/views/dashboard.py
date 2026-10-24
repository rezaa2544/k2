"""داشبورد آرام و کاربردی: ظرفیت، اقدام بعدی و هشدارهای شفاف."""

from __future__ import annotations

import datetime as _dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...advisor_engine import PHASE_LABELS
from ... import exam_calendar
from ...domain.enums import DebtLevel
from ...jdate import format_jalali_long, format_minutes, format_number
from ...service import AdvisorService
from ..theme import COLORS
from ..widgets import Card, StatTile, info_box, warn_box

DEBT_COLORS = {
    "accent": COLORS["accent"], "info": COLORS["info"],
    "warn": COLORS["warn"], "danger": COLORS["danger"],
    "muted": COLORS["muted"],
}


class DashboardPage(QWidget):
    """نمای اول برنامه؛ اطلاعات مهم در چند ثانیه قابل دریافت است."""

    def __init__(self, service: AdvisorService, parent: QWidget | None = None):
        super().__init__(parent)
        self.service = service
        self.setObjectName("dashboardPage")
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("dashboardContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(2, 2, 8, 14)
        layout.setSpacing(14)

        intro = QVBoxLayout()
        intro.setSpacing(4)
        self.header = QLabel()
        self.header.setObjectName("sectionTitle")
        intro.addWidget(self.header)
        self.intro_hint = QLabel("برنامهٔ خوب، با قدمی روشن و قابل انجام شروع می‌شود.")
        self.intro_hint.setObjectName("muted")
        intro.addWidget(self.intro_hint)
        layout.addLayout(intro)

        self.hero = QWidget()
        self.hero.setObjectName("heroCard")
        hero_layout = QHBoxLayout(self.hero)
        hero_layout.setContentsMargins(20, 17, 20, 17)
        hero_layout.setSpacing(18)
        hero_copy = QVBoxLayout()
        hero_copy.setSpacing(5)
        eyebrow = QLabel("پیشنهاد مشاور برای قدم بعدی")
        eyebrow.setObjectName("heroEyebrow")
        self.next_title = QLabel("—")
        self.next_title.setObjectName("heroTitle")
        self.next_title.setWordWrap(True)
        self.next_reason = QLabel("—")
        self.next_reason.setObjectName("heroBody")
        self.next_reason.setWordWrap(True)
        hero_copy.addWidget(eyebrow)
        hero_copy.addWidget(self.next_title)
        hero_copy.addWidget(self.next_reason)
        hero_layout.addLayout(hero_copy, 1)
        actions = QVBoxLayout()
        actions.setSpacing(8)
        self.btn_plan = QPushButton("ساخت برنامهٔ امروز")
        self.btn_plan.setObjectName("primary")
        self.btn_plan.clicked.connect(self._rebuild_plan)
        self.btn_minimal = QPushButton("روز حداقلی")
        self.btn_minimal.setToolTip("برای روزهای کم‌انرژی، بدون فداکردن خواب")
        self.btn_minimal.clicked.connect(self._minimal_day)
        actions.addWidget(self.btn_plan)
        actions.addWidget(self.btn_minimal)
        hero_layout.addLayout(actions)
        layout.addWidget(self.hero)

        tiles = QGridLayout()
        tiles.setSpacing(10)
        self.tile_capacity = StatTile("ظرفیت واقعی امروز", "—", "", "timer")
        self.tile_planned = StatTile("برنامهٔ ساخته‌شده", "—", "", "study")
        self.tile_margin = StatTile("زمان آزادِ محفوظ", "—", "", "ok")
        self.tile_debt = StatTile("کارهای عقب‌افتاده", "—", "", "backlog")
        self.tile_consolidation = StatTile("پوشش تثبیت", "—", "", "review")
        for tile in (
            self.tile_capacity, self.tile_planned, self.tile_margin,
            self.tile_debt, self.tile_consolidation,
        ):
            tile.setMinimumHeight(114)
        tiles.addWidget(self.tile_capacity, 0, 0)
        tiles.addWidget(self.tile_planned, 0, 1)
        tiles.addWidget(self.tile_margin, 0, 2)
        tiles.addWidget(self.tile_debt, 0, 3)
        tiles.addWidget(self.tile_consolidation, 0, 4)
        layout.addLayout(tiles)

        details = QGridLayout()
        details.setSpacing(10)
        self.capacity_card = Card("ظرفیت از کجا آمده؟", tone="timer")
        self.capacity_text = QLabel("—")
        self.capacity_text.setWordWrap(True)
        self.capacity_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.capacity_card.add(self.capacity_text)
        self.phase_card = Card("فاز زمانی و آزمون هدف", tone="exam")
        self.phase_label = QLabel("—")
        self.phase_label.setWordWrap(True)
        self.phase_card.add(self.phase_label)
        self.calendar_label = QLabel("—")
        self.calendar_label.setObjectName("muted")
        self.calendar_label.setWordWrap(True)
        self.phase_card.add(self.calendar_label)
        self.backlog_card = Card("صف عقب‌افتادگی", tone="backlog")
        self.backlog_label = QLabel("—")
        self.backlog_label.setWordWrap(True)
        self.backlog_card.add(self.backlog_label)
        self.advice_card = Card("یادآوری مشاور", tone="accent")
        self.advice_text = QLabel("—")
        self.advice_text.setWordWrap(True)
        self.advice_card.add(self.advice_text)
        details.addWidget(self.capacity_card, 0, 0, 2, 1)
        details.addWidget(self.phase_card, 0, 1)
        details.addWidget(self.backlog_card, 0, 2)
        details.addWidget(self.advice_card, 1, 1, 1, 2)
        details.setColumnStretch(0, 3)
        details.setColumnStretch(1, 2)
        details.setColumnStretch(2, 2)
        layout.addLayout(details)

        self.conflict_box = warn_box()
        self.conflict_box.setVisible(False)
        layout.addWidget(self.conflict_box)
        self.info = info_box()
        self.info.setText(
            "اصل برنامه‌ریزی: خواب و تعهدها محفوظ می‌مانند؛ کار جا‌نشده صریح گزارش می‌شود؛ "
            "هیچ فعالیتی بی‌خبر ناپدید نمی‌شود."
        )
        layout.addWidget(self.info)
        layout.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll)

    def refresh(self) -> None:
        today = _dt.date.today()
        self.header.setText(f"خلاصهٔ امروز  ·  {format_jalali_long(today)}")
        has_user_data = any((
            self.service.active_exam_profile(),
            self.service.list_activities(),
            self.service.list_attempts(),
            self.service.list_review_items(),
            self.service.repo.list_fixed_events(),
            self.service.repo.list_routines(),
            self.service.repo.get_setting("daily.wake_minute"),
            self.service.repo.get_setting("daily.sleep_minute"),
            self.service.repo.get_setting("daily.energy_level"),
            self.service.repo.get_setting("daily.peak_hours"),
        ))
        if not has_user_data:
            self.next_title.setText("هنوز اطلاعاتی ثبت نشده است")
            self.next_reason.setText("راه‌اندازی را کامل کنید یا اطلاعات واقعی خود را از بخش‌های مربوط اضافه کنید.")
            for tile in (
                self.tile_capacity, self.tile_planned, self.tile_margin,
                self.tile_debt, self.tile_consolidation,
            ):
                tile.set_value("—", "پس از ثبت اطلاعات نمایش داده می‌شود")
            self.capacity_text.setText("برای محاسبهٔ ظرفیت، ساعت خواب و بیداری یا تعهدهای خود را ثبت کنید.")
            self.phase_label.setText("هنوز آزمون هدفی ثبت نشده است.")
            calendar = exam_calendar.status()
            self.calendar_label.setText(
                calendar.summary() + "\n"
                + " · ".join(item["effect"] for item in calendar.announced)
            )
            self.calendar_label.setToolTip(
                "بررسی شده در " + format_jalali_long(calendar.checked_on)
                + "\n\nمنابع: " + "، ".join(src["title"] for src in calendar.sources)
            )
            self.backlog_label.setText("هنوز فعالیتی ثبت نشده است.")
            self.advice_text.setText("پس از ورود اطلاعات واقعی، پیشنهادهای شخصی در اینجا نمایش داده می‌شوند.")
            self.conflict_box.setVisible(False)
            self.btn_plan.setEnabled(False)
            self.btn_minimal.setEnabled(False)
            return

        self.btn_plan.setEnabled(True)
        self.btn_minimal.setEnabled(True)
        context = self.service.build_context(today)
        breakdown = context.capacity_for(today)
        self.tile_capacity.set_value(
            format_minutes(breakdown.capacity_minutes), "پس از تعهدها و حاشیهٔ اطمینان"
        )
        plan = self.service.plan_day(today)
        self.tile_planned.set_value(
            format_minutes(plan.planned_minutes), f"{len(plan.placements)} بازهٔ پیشنهادی"
        )
        self.tile_margin.set_value(
            format_minutes(plan.margin_minutes), "برای جابه‌جایی و وقفه‌های طبیعی"
        )

        backlog = self.service.backlog(today)
        tone = {
            DebtLevel.GREEN: "accent", DebtLevel.YELLOW: "warn",
            DebtLevel.ORANGE: "warn", DebtLevel.RED: "danger",
        }[backlog.level]
        self.tile_debt.set_value(
            format_minutes(backlog.debt_minutes),
            f"{len(backlog.items)} کار · سطح {backlog.level.label}"
        )
        self.tile_debt.value_label.setStyleSheet(f"color: {DEBT_COLORS[tone]};")

        self.capacity_text.setText(
            f"پنجرهٔ بیداری:  {format_minutes(breakdown.awake_minutes)}\n"
            f"کلاس‌ها و تعهدها:  {format_minutes(breakdown.fixed_minutes)}\n"
            f"زمان خام:  {format_minutes(breakdown.raw_minutes)}\n"
            f"تمرکز × انرژی:  {format_number(breakdown.focus_factor, digits=2)} × "
            f"{format_number(breakdown.energy_factor, digits=2)}\n"
            f"زمان مؤثر:  {format_minutes(breakdown.effective_minutes)}\n"
            f"حاشیهٔ اطمینان:  {format_number(breakdown.safety_margin * 100)}٪"
        )

        suggestion = self.service.next_action()
        self.next_title.setText(suggestion.title)
        self.next_reason.setText(suggestion.reason)

        profile = self.service.active_exam_profile()
        phase = self.service.study_phase()
        if profile is None:
            self.phase_label.setText("هنوز آزمون هدف ثبت نشده است.\nمی‌توانید تاریخ را از تنظیمات اضافه یا ویرایش کنید.")
        else:
            remaining = profile.days_remaining
            status = {
                "official": "رسمی · منبع ثبت‌شده",
                "estimated": "تخمینی · تاریخ رسمی تأیید نشده",
                "unknown": "نامشخص",
            }[profile.date_status.value]
            self.phase_label.setText(
                f"آزمون: {profile.name}\nتاریخ: {profile.target_date} · {status}\n"
                f"فاز: {PHASE_LABELS[phase]}"
                + (f" · {remaining} روز مانده" if remaining is not None else "")
            )
            hint = exam_calendar.planning_hint(profile)
            if hint:
                self.phase_label.setToolTip(hint)

        calendar = exam_calendar.status()
        self.calendar_label.setText(
            calendar.summary() + "\n"
            + " · ".join(item["effect"] for item in calendar.announced)
        )
        self.calendar_label.setToolTip(
            "بررسی شده در " + format_jalali_long(calendar.checked_on)
            + "\n\nمنابع: " + "، ".join(src["title"] for src in calendar.sources)
        )

        self.backlog_label.setText(
            f"کارهای عقب‌افتاده: {len(backlog.items)}\n"
            f"حجم باقی‌مانده: {format_minutes(backlog.debt_minutes)}\n"
            f"ظرفیت قابل جبران این هفته: {format_minutes(backlog.recoverable_minutes)}\n"
            f"سقف جبران روزانه: {format_minutes(backlog.compensation_cap_minutes)}"
        )

        conflicts = self.service.schedule_conflicts()
        if conflicts:
            self.conflict_box.setVisible(True)
            self.conflict_box.setText(
                "برای نهایی‌کردن برنامه این مورد نیاز به پاسخ شما دارد:\n\n" +
                "\n".join(f"• {c.describe()}  {c.question}" for c in conflicts)
            )
        else:
            self.conflict_box.setVisible(False)

        advice = []
        if plan.unplaced:
            advice.append(f"{len(plan.unplaced)} فعالیت در ظرفیت امروز جا نشد؛ از فهرست کارهای جا‌نشده بررسی‌اش کنید.")
        else:
            advice.append("برای امروز موردِ جا‌نشده‌ای ثبت نشده است.")
        if backlog.level in {DebtLevel.ORANGE, DebtLevel.RED}:
            advice.append("اگر فشار زیاد است، ترتیب «ضروری / در صورت توان / قابل تعویق» را بررسی کنید.")
        elif backlog.level == DebtLevel.GREEN:
            advice.append("فشار کاری در محدودهٔ عادی است؛ برای پرکردن زمان آزاد عجله نکنید.")
        self._refresh_consolidation_tile(advice)
        self.advice_text.setText("\n\n".join(advice))

    def _refresh_consolidation_tile(self, advice: list[str]) -> None:
        """کاشی پوشش تثبیت + یادآوری ماندگاری از موتور تثبیت."""
        try:
            overview = self.service.consolidation_overview()
        except Exception:  # noqa: BLE001 — داشبورد نباید با خطای تثبیت از کار بیفتد
            self.tile_consolidation.set_value("—", "محاسبهٔ تثبیت ممکن نشد")
            return
        forecast = overview["forecast"]
        if not forecast.topics:
            self.tile_consolidation.set_value(
                "—", "مبحثی ثبت نشده؛ از «مباحث و تسلط» یا کاتالوگ اضافه کنید"
            )
            return
        coverage = format_number(forecast.coverage * 100)
        self.tile_consolidation.set_value(
            f"{coverage}٪",
            f"{len(forecast.consolidated)} مبحث تثبیت‌شده از {len(forecast.topics)}",
        )
        at_risk = len(forecast.at_risk) + len(forecast.behind)
        if at_risk:
            advice.append(
                f"{at_risk} مبحث در خطر ماندگاری یا عقب‌افتادهٔ تثبیت است؛ "
                "در صفحهٔ «تثبیت حافظه» صف جبران را ببینید."
            )
        verdict = overview["feasibility"]
        if verdict.level in {"infeasible", "tight"}:
            advice.append(
                "کار باقی‌مانده تا آزمون با ظرفیت فعلی جا نمی‌شود؛ "
                "گزینه‌های تصمیم در صفحهٔ «تثبیت حافظه» آمده است."
            )

    def _rebuild_plan(self) -> None:
        self.service.plan_day(_dt.date.today())
        self.refresh()

    def _minimal_day(self) -> None:
        plan = self.service.minimal_day()
        text = "\n".join(
            f"• {a.title} ({format_minutes(a.effective_minutes)})" for a in plan.activities
        )
        from ..widgets import notify

        notify(
            self,
            "برنامهٔ حداقلی روز دشوار",
            (text or "کار ضروری با مهلت نزدیک یافت نشد.")
            + "\n\nاین روز بدون جریمه و بدون مطلب جدید سنگین ثبت می‌شود.",
        )
