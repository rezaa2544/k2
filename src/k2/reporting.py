"""گزارش‌ها: روزانه، هفتگی، پیشرفت شخصی و خروجی CSV.

قواعد:
  * مقایسه فقط با **سابقهٔ خود کاربر** انجام می‌شود (نه با همسالان).
  * هیچ استریک، رتبه‌بندی یا پیام شرم‌آور تولید نمی‌شود (NFR-01).
  * نشانگر فشار فقط **توصیفی** است و تشخیص پزشکی/روان‌شناختی نمی‌دهد.
"""

from __future__ import annotations

import csv
import datetime as _dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional, Sequence

from .domain.enums import ActivityState, ExamKind
from .domain.models import (
    Activity,
    DayPlan,
    ErrorRecord,
    ExamAttempt,
    ReviewLog,
    WeeklyReport,
)
from .jdate import format_jalali_long, format_minutes, format_number, persian_digits


@dataclass
class DailyReport:
    """گزارش پایان روز."""

    date: _dt.date
    planned_minutes: int = 0
    done_minutes: int = 0
    completed: int = 0
    partial: int = 0
    missed: int = 0
    capacity_minutes: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def adherence(self) -> float:
        total = self.completed + self.partial + self.missed
        if total == 0:
            return 1.0
        return (self.completed + 0.5 * self.partial) / total

    def to_text(self) -> str:
        lines = [
            f"گزارش {format_jalali_long(self.date)}",
            (
                f"برنامه‌ریزی‌شده: {format_minutes(self.planned_minutes)} | "
                f"انجام‌شده: {format_minutes(self.done_minutes)} | "
                f"ظرفیت: {format_minutes(self.capacity_minutes)}"
            ),
            (
                f"تکمیل‌شده: {format_number(self.completed)} | ناقص: "
                f"{format_number(self.partial)} | انجام‌نشده: {format_number(self.missed)}"
            ),
        ]
        lines.extend(self.notes)
        return "\n".join(lines)


def build_daily_report(
    *,
    date: _dt.date,
    plan: Optional[DayPlan] = None,
    activities: Sequence[Activity] = (),
) -> DailyReport:
    """گزارش پایان روز از روی وضعیت فعالیت‌ها."""
    report = DailyReport(date=date)
    if plan is not None:
        report.planned_minutes = plan.planned_minutes
        report.capacity_minutes = plan.capacity_minutes

    for activity in activities:
        if activity.state == ActivityState.DONE:
            report.completed += 1
            report.done_minutes += activity.actual_minutes
        elif activity.state == ActivityState.PARTIAL:
            report.partial += 1
            report.done_minutes += activity.actual_minutes
        elif activity.state in {
            ActivityState.PLANNED,
            ActivityState.READY,
            ActivityState.IN_PROGRESS,
            ActivityState.OVERDUE,
            ActivityState.BLOCKED,
            ActivityState.DEFERRED,
        }:
            report.missed += 1
    return report


@dataclass
class ProgressTrend:
    """روند شخصی: مقایسه با سابقهٔ خود کاربر."""

    metric: str
    points: list[tuple[_dt.date, float]] = field(default_factory=list)
    note: str = ""

    @property
    def first(self) -> Optional[float]:
        return self.points[0][1] if self.points else None

    @property
    def last(self) -> Optional[float]:
        return self.points[-1][1] if self.points else None

    @property
    def delta(self) -> Optional[float]:
        if self.first is None or self.last is None:
            return None
        return self.last - self.first

    @property
    def direction(self) -> str:
        delta = self.delta
        if delta is None:
            return "نامشخص"
        if delta > 0.01:
            return "بهبود"
        if delta < -0.01:
            return "کاهش"
        return "ثابت"


def accuracy_trend(attempts: Sequence[ExamAttempt]) -> ProgressTrend:
    """روند دقت درصد آزمون‌ها (به تفکیک نوع آزمون قابل تفکیک است)."""
    points = [
        (attempt.taken_at.date(), attempt.percentage / 100.0)
        for attempt in attempts
        if attempt.taken_at is not None
    ]
    return ProgressTrend(
        metric="دقت آزمون",
        points=points,
        note="مقایسه با سابقهٔ خود شماست؛ مقایسه با دیگران انجام نمی‌شود.",
    )


def repeated_error_rate(errors: Sequence[ErrorRecord]) -> float:
    """نرخ خطای تکراری (سند ۱، بخش ۴.۴)."""
    if not errors:
        return 0.0
    buckets: dict[tuple[Optional[int], str], int] = {}
    for error in errors:
        key = (error.topic_id, error.code.value)
        buckets[key] = buckets.get(key, 0) + 1
    repeated = sum(count for count in buckets.values() if count >= 2)
    return repeated / len(errors)


def build_weekly_report(
    *,
    start_date: _dt.date,
    end_date: _dt.date,
    activities: Sequence[Activity],
    attempts: Sequence[ExamAttempt] = (),
    errors: Sequence[ErrorRecord] = (),
    review_logs: Sequence[ReviewLog] = (),
) -> WeeklyReport:
    """گزارش هفتگی (ADV-04): چه پیش رفت، چه مانع شد، چه تغییر می‌کند."""
    report = WeeklyReport(start_date=start_date, end_date=end_date)

    def _in_week(activity: Activity) -> bool:
        for stamp in (activity.created_at, activity.first_planned_at):
            if stamp is not None and start_date <= stamp.date() <= end_date:
                return True
        return False

    weekly = [a for a in activities if _in_week(a)]

    for activity in weekly:
        report.total_activities += 1
        report.planned_minutes += activity.est_minutes
        if activity.state == ActivityState.DONE:
            report.completed_activities += 1
            report.done_minutes += activity.actual_minutes
        elif activity.state == ActivityState.PARTIAL:
            report.partial_activities += 1
            report.done_minutes += activity.actual_minutes
        elif activity.state == ActivityState.DROPPED:
            report.dropped_activities += 1
            if activity.state_reason:
                report.blockers.append(activity.state_reason)

    if report.total_activities:
        report.adherence = report.completed_activities / report.total_activities

    weekly_attempts = [
        a for a in attempts if a.taken_at and start_date <= a.taken_at.date() <= end_date
    ]
    report.accuracy_trend = [
        a.percentage / 100.0 for a in sorted(weekly_attempts, key=lambda x: x.taken_at)
    ]

    weekly_errors = [
        e
        for e in errors
        if e.created_at and start_date <= e.created_at.date() <= end_date
    ]
    report.repeated_error_rate = repeated_error_rate(weekly_errors)

    # خطای تخمین: میانهٔ نسبت زمان واقعی به برآورد
    ratios = [
        a.actual_minutes / a.est_minutes
        for a in weekly
        if a.actual_minutes > 0 and a.est_minutes > 0
    ]
    if ratios:
        ratios.sort()
        report.estimate_bias = ratios[len(ratios) // 2] - 1.0

    if report.adherence >= 0.8:
        report.next_week_changes.append(
            "نرخ تحقق بالا است؛ می‌توان حجم کار را کمی بیشتر کرد."
        )
    elif report.adherence < 0.5:
        report.next_week_changes.append(
            "نرخ تحقق پایین است؛ بلوک‌های کوچک‌تر و برنامهٔ حداقلی پیشنهاد می‌شود."
        )

    if report.estimate_bias > 0.2:
        report.next_week_changes.append(
            f"برآوردها حدود {format_number(report.estimate_bias * 100)}٪ کمتر از واقعیت است؛ "
            "تخمین‌ها افزایش یابد."
        )
    elif report.estimate_bias < -0.2:
        report.next_week_changes.append(
            f"برآوردها حدود {format_number(abs(report.estimate_bias) * 100)}٪ بیشتر از واقعیت است؛ "
            "تخمین‌ها کاهش یابد."
        )

    if report.repeated_error_rate > 0.3:
        report.next_week_changes.append(
            "نرخ خطای تکراری بالاست؛ روش مطالعهٔ مباحث پرتکرار بازبینی شود."
        )

    if report.blockers:
        report.notes.append("موانع ثبت‌شده: " + "، ".join(sorted(set(report.blockers))))

    return report


@dataclass
class PressureSignal:
    """نشانگر فشار برنامه — توصیفی و غیرتشخیصی (ADV-05)."""

    active: bool
    reasons: list[str] = field(default_factory=list)
    message: str = ""
    can_dismiss: bool = True

    @property
    def label(self) -> str:
        return "نشانگر فشار فعال" if self.active else "بدون نشانگر فشار"


def pressure_signal(
    *,
    energy_factors: Sequence[float],
    debt_ratio: Optional[float] = None,
    overload_reasons_last_week: int = 0,
    settings: Optional = None,
) -> PressureSignal:
    """نشانگر فشار بر پایهٔ الگوهای ثبت‌شده.

    هیچ تشخیصی داده نمی‌شود؛ فقط الگوی داده توصیف و پیشنهاد داده می‌شود.
    """
    reasons: list[str] = []

    if len(energy_factors) >= 3 and sum(1 for f in energy_factors[-3:] if f <= 0.6) >= 3:
        reasons.append("ضریب انرژی در سه روز اخیر پایین گزارش شده است.")
    if debt_ratio is not None and debt_ratio >= 0.7:
        reasons.append(f"نسبت بدهی {format_number(debt_ratio * 100)}٪ است.")
    if overload_reasons_last_week >= 3:
        reasons.append(
            "دلیل «بیش از حد زیاد» دست‌کم سه بار در هفتهٔ اخیر ثبت شده است."
        )

    if not reasons:
        return PressureSignal(active=False, message="الگوی نگران‌کننده‌ای ثبت نشده است.")

    return PressureSignal(
        active=True,
        reasons=reasons,
        message=(
            "الگوی فشار در داده‌های ثبت‌شده دیده می‌شود. پیشنهاد می‌شود حجم کار "
            "کمی کم شود. این پیام تشخیص پزشکی یا روان‌شناختی نیست. اگر این وضعیت "
            "ادامه داشت، صحبت کردن با یک مشاور یا فرد مورد اعتماد کمک‌کننده است."
        ),
    )


# ---------------------------------------------------------------------------
# خروجی
# ---------------------------------------------------------------------------


def export_activities_csv(
    activities: Sequence[Activity], path: Path | str
) -> Path:
    """خروجی CSV فعالیت‌ها (DATA-03)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "شناسه",
                "عنوان",
                "نوع",
                "درس",
                "مبحث",
                "برآورد (دقیقه)",
                "واقعی (دقیقه)",
                "باقی‌مانده (دقیقه)",
                "مهلت",
                "نوع مهلت",
                "وضعیت",
                "دلیل وضعیت",
            ]
        )
        for activity in activities:
            writer.writerow(
                [
                    activity.id,
                    activity.title,
                    activity.type.label,
                    activity.subject_name,
                    activity.topic_name,
                    activity.est_minutes,
                    activity.actual_minutes,
                    activity.remaining_minutes,
                    activity.deadline_at.isoformat() if activity.deadline_at else "",
                    activity.deadline_type.label,
                    activity.state.label,
                    activity.state_reason,
                ]
            )
    return target


def export_attempts_csv(attempts: Sequence[ExamAttempt], path: Path | str) -> Path:
    """خروجی CSV نتایج آزمون‌ها."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "شناسه",
                "نام آزمون",
                "نوع آزمون",
                "تاریخ",
                "درس",
                "کل",
                "درست",
                "غلط",
                "نزده",
                "درصد",
                "مدت (دقیقه)",
            ]
        )
        for attempt in attempts:
            writer.writerow(
                [
                    attempt.id,
                    attempt.name,
                    attempt.kind.label,
                    attempt.taken_at.isoformat() if attempt.taken_at else "",
                    attempt.subject_name,
                    attempt.total,
                    attempt.correct,
                    attempt.wrong,
                    attempt.blank,
                    f"{attempt.percentage:.2f}",
                    attempt.duration_minutes,
                ]
            )
    return target


def weekly_report_to_text(report: WeeklyReport) -> str:
    """متن گزارش هفتگی برای نمایش."""
    lines = [
        f"گزارش هفتگی {format_jalali_long(report.start_date)} تا {format_jalali_long(report.end_date)}",
        (
            f"انجام‌شده: {report.completed_activities} از {report.total_activities} "
            f"({format_number(report.adherence * 100)}٪) — "
            f"زمان ثبت‌شده: {format_minutes(report.done_minutes)}"
        ),
    ]
    if report.accuracy_trend:
        trend = ", ".join(
            format_number(value * 100) + "٪" for value in report.accuracy_trend
        )
        lines.append(f"دقت آزمون‌ها: {trend}")
    lines.append(
        f"نرخ خطای تکراری: {format_number(report.repeated_error_rate * 100)}٪"
    )
    if report.blockers:
        lines.append("موانع: " + "، ".join(sorted(set(report.blockers))))
    if report.next_week_changes:
        lines.append("تغییرات پیشنهادی هفتهٔ بعد:")
        lines.extend(f"  • {item}" for item in report.next_week_changes)
    return "\n".join(lines)
