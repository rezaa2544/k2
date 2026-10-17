"""داشبورد: خلاصهٔ وضعیت امروز، ظرفیت، گلوگاه و کار بعدی."""

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
from ...domain.enums import DebtLevel
from ...jdate import format_jalali_long, format_minutes, format_number
from ...service import AdvisorService
from ..widgets import Badge, Card, StatTile, info_box, warn_box

#: رنگ نمایش سطح بدهی.
DEBT_COLORS = {
    "accent": "#2f6f4e",
    "info": "#3b5b8c",
    "warn": "#8a6d1f",
    "danger": "#8c3b3b",
    "muted": "#5b6673",
}


class DashboardPage(QWidget):
    """نمای کلی وضعیت."""

    def __init__(self, service: AdvisorService, parent: QWidget | None = None):
        super().__init__(parent)
        self.service = service
        self._build()
        self.refresh()

    # ---- ساخت ----

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        self.header = QLabel()
        self.header.setObjectName("sectionTitle")
        outer.addWidget(self.header)

        tiles = QGridLayout()
        tiles.setSpacing(12)
        self.tile_capacity = StatTile("ظرفیت امروز", "—", "", "accent")
        self.tile_planned = StatTile("برنامهٔ امروز", "—", "", "info")
        self.tile_margin = StatTile("حاشیهٔ آزاد", "—", "", "muted")
        self.tile_debt = StatTile("بدهی عقب‌افتادگی", "—", "", "warn")
        tiles.addWidget(self.tile_capacity, 0, 0)
        tiles.addWidget(self.tile_planned, 0, 1)
        tiles.addWidget(self.tile_margin, 0, 2)
        tiles.addWidget(self.tile_debt, 0, 3)
        outer.addLayout(tiles)

        body = QHBoxLayout()
        body.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(12)

        self.next_card = Card("کار بعدی")
        self.next_title = QLabel("—")
        self.next_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.next_title.setWordWrap(True)
        self.next_card.add(self.next_title)
        self.next_reason = QLabel("—")
        self.next_reason.setObjectName("muted")
        self.next_reason.setWordWrap(True)
        self.next_card.add(self.next_reason)
        buttons = QHBoxLayout()
        self.btn_plan = QPushButton("ساخت برنامهٔ امروز")
        self.btn_plan.setObjectName("primary")
        self.btn_plan.clicked.connect(self._rebuild_plan)
        self.btn_minimal = QPushButton("روز حداقلی")
        self.btn_minimal.clicked.connect(self._minimal_day)
        buttons.addWidget(self.btn_plan)
        buttons.addWidget(self.btn_minimal)
        self.next_card.add_layout(buttons)
        left.addWidget(self.next_card)

        self.phase_card = Card("فاز زمانی و آزمون هدف")
        self.phase_label = QLabel("—")
        self.phase_label.setWordWrap(True)
        self.phase_card.add(self.phase_label)
        left.addWidget(self.phase_card)

        self.backlog_card = Card("صف عقب‌افتادگی")
        self.backlog_label = QLabel("—")
        self.backlog_label.setWordWrap(True)
        self.backlog_card.add(self.backlog_label)
        left.addWidget(self.backlog_card)

        body.addLayout(left, 2)

        right = QVBoxLayout()
        right.setSpacing(12)
        self.capacity_card = Card("تفکیک ظرفیت")
        self.capacity_text = QLabel("—")
        self.capacity_text.setWordWrap(True)
        self.capacity_card.add(self.capacity_text)
        right.addWidget(self.capacity_card)

        self.advice_card = Card("توصیهٔ امروز")
        self.advice_text = QLabel("—")
        self.advice_text.setWordWrap(True)
        self.advice_card.add(self.advice_text)
        right.addWidget(self.advice_card)

        self.conflict_box = warn_box()
        self.conflict_box.setVisible(False)
        right.addWidget(self.conflict_box)

        self.info = info_box()
        self.info.setText(
            "ساعت مطالعه هدف، خروجی ظرفیت واقعی است. برنامه هرگز از ظرفیت "
            "بیشتر نمی‌شود و فعالیت جا‌نشده پنهان نمی‌ماند."
        )
        right.addWidget(self.info)

        body.addLayout(right, 1)
        outer.addLayout(body)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        container = QWidget()
        container.setLayout(outer)
        scroll.setWidget(container)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    # ---- به‌روزرسانی ----

    def refresh(self) -> None:
        today = _dt.date.today()
        self.header.setText(f"داشبورد — {format_jalali_long(today)}")

        context = self.service.build_context(today)
        breakdown = context.capacity_for(today)

        self.tile_capacity.set_value(
            format_minutes(breakdown.capacity_minutes),
            "ظرفیت نهایی پس از حاشیهٔ اطمینان",
        )
        plan = self.service.plan_day(today)
        self.tile_planned.set_value(
            format_minutes(plan.planned_minutes),
            f"{len(plan.placements)} بلوک برنامه‌ریزی‌شده",
        )
        self.tile_margin.set_value(
            format_minutes(plan.margin_minutes), "بدون اضافه‌کاری پنهان"
        )

        backlog = self.service.backlog(today)
        tone = {
            DebtLevel.GREEN: "accent",
            DebtLevel.YELLOW: "warn",
            DebtLevel.ORANGE: "warn",
            DebtLevel.RED: "danger",
        }[backlog.level]
        self.tile_debt.set_value(
            format_minutes(backlog.debt_minutes),
            f"سطح: {backlog.level.label} — نسبت بدهی {format_number(backlog.debt_ratio * 100)}٪",
        )
        self.tile_debt.value_label.setStyleSheet(f"color: {DEBT_COLORS[tone]};")

        self.capacity_text.setText(
            f"پنجرهٔ بیداری: {format_minutes(breakdown.awake_minutes)}\n"
            f"کلاس‌ها و تعهدات: {format_minutes(breakdown.fixed_minutes)}\n"
            f"زمان خام: {format_minutes(breakdown.raw_minutes)}\n"
            f"ضریب تمرکز: {format_number(breakdown.focus_factor, digits=2)} "
            f"× ضریب انرژی: {format_number(breakdown.energy_factor, digits=2)}\n"
            f"زمان مؤثر: {format_minutes(breakdown.effective_minutes)}\n"
            f"حاشیهٔ اطمینان: {format_number(breakdown.safety_margin * 100)}٪"
        )

        suggestion = self.service.next_action()
        self.next_title.setText(suggestion.title)
        self.next_reason.setText(suggestion.reason)

        profile = self.service.active_exam_profile()
        phase = self.service.study_phase()
        if profile is None:
            self.phase_label.setText("پروفایل آزمون هنوز ثبت نشده است.")
        else:
            remaining = profile.days_remaining
            status = {
                "official": "رسمی (منبع ثبت‌شده)",
                "estimated": "تخمینی — تاریخ رسمی اعلام نشده",
                "unknown": "نامشخص",
            }[profile.date_status.value]
            self.phase_label.setText(
                f"آزمون: {profile.name}\n"
                f"تاریخ: {profile.target_date} — {status}\n"
                f"فاز فعلی: «{PHASE_LABELS[phase]}»"
                + (f"\nروزهای باقی‌مانده: {remaining}" if remaining is not None else "")
            )

        self.backlog_label.setText(
            f"تعداد کارهای عقب‌افتاده: {len(backlog.items)}\n"
            f"بدهی: {format_minutes(backlog.debt_minutes)}\n"
            f"ظرفیت قابل جبران ۷ روز آینده: {format_minutes(backlog.recoverable_minutes)}\n"
            f"نسبت بدهی: {format_number(backlog.debt_ratio * 100)}٪ "
            f"(سطح {backlog.level.label})\n"
            f"سقف کار جبرانی روزانه: {format_minutes(backlog.compensation_cap_minutes)}"
        )

        conflicts = self.service.schedule_conflicts()
        if conflicts:
            self.conflict_box.setVisible(True)
            self.conflict_box.setText(
                "\n".join(
                    f"{conflict.describe()} {conflict.question}" for conflict in conflicts
                )
            )
        else:
            self.conflict_box.setVisible(False)

        advice_lines = []
        if plan.unplaced:
            advice_lines.append(
                f"{len(plan.unplaced)} کار امروز جا نشد و صریح گزارش شده است."
            )
        else:
            advice_lines.append("همهٔ کارهای کاندید امروز در برنامه جا گرفتند.")
        if backlog.level in {DebtLevel.ORANGE, DebtLevel.RED}:
            advice_lines.append(
                "برای کاهش بدهی، فهرست «حتماً / اگر شد / پیشنهاد حذف» آماده شده است."
            )
        if backlog.level == DebtLevel.GREEN:
            advice_lines.append("فشار کاری در محدودهٔ عادی است.")
        self.advice_text.setText("\n".join(advice_lines))

    # ---- کنش‌ها ----

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
