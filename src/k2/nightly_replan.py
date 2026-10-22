"""بازبینی شبانه و بازسازی برنامهٔ روزهای بعد (بند ۱۶).

هر شب (یا هر بار که کاربر بازبینی بگیرد) برنامه سؤال‌های زیر را می‌پرسد:

۱. چه کاری انجام شد و چه کاری ناقص ماند؟  ۲. چرا ناقص ماند؟
۳. کدام مباحث بهتر و کدام‌ها بدتر از برنامه پیش رفت؟
۴. مهلت‌ها هنوز شدنی‌اند؟  ۵. حجم آینده از ظرفیت واقعی بیشتر نیست؟

سپس برنامهٔ روزهای بعد **جلو به عقب** بازسازی می‌شود، با این قید که
کلاس‌های ثابت و تعهدهای ضروری کاربر دست‌نخورده می‌مانند. کار نیمه‌تمام
کورکورانه به فردا منتقل نمی‌شود؛ اول اهمیت و فوریتش سنجیده می‌شود و بعد
توزیع می‌شود.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Optional, Sequence

from .config import Settings
from .domain.enums import ActivityState, ActivityType
from .domain.models import (
    Activity,
    DayPlan,
    LearningProblem,
    NightlyChange,
    NightlyReview,
    StudySession,
    TopicDeadline,
    TopicDeadlinePlan,
)

#: فعالیت‌هایی که «مطالعهٔ مستقل» شمرده می‌شوند و با کلاس قاطی نمی‌شوند.
INDEPENDENT_TYPES = frozenset(
    {
        ActivityType.PROCESSING,
        ActivityType.GUIDED_EXAMPLE,
        ActivityType.INDEPENDENT_PRACTICE,
        ActivityType.MIXED_PRACTICE,
        ActivityType.HOMEWORK,
        ActivityType.REMEDIATION,
        ActivityType.REWORK,
        ActivityType.CONSOLIDATION,
        ActivityType.SUMMARY,
    }
)

#: فعالیت‌هایی که «تست/تحلیل» شمرده می‌شوند.
ASSESSMENT_TYPES = frozenset(
    {ActivityType.TIMED_TEST, ActivityType.TEST_ANALYSIS, ActivityType.EXAM}
)


@dataclass
class ReplanDecision:
    """یک تصمیم دربارهٔ یک فعالیت ناقص."""

    activity_id: int
    title: str
    #: rollover | redistribute | keep_today | defer | drop_candidate
    action: str
    reason: str
    target_date: Optional[_dt.date] = None


@dataclass
class ReplanReport:
    """خروجی بازسازی برنامهٔ چند روز بعد."""

    decisions: list[ReplanDecision] = field(default_factory=list)
    changes: list[NightlyChange] = field(default_factory=list)
    fixed_preserved: int = 0
    redistributed_minutes: int = 0

    @property
    def rolled_over(self) -> list[ReplanDecision]:
        return [d for d in self.decisions if d.action == "rollover"]

    @property
    def redistributed(self) -> list[ReplanDecision]:
        return [d for d in self.decisions if d.action == "redistribute"]


def classify_day(
    plan: DayPlan,
    activities: Sequence[Activity],
    sessions: Sequence[StudySession],
    *,
    date: Optional[_dt.date] = None,
) -> NightlyReview:
    """بازبینی یک روز: انجام‌شده، ناقص، بهتر/بدتر، ریسک مهلت و ظرفیت."""
    day = date or plan.date
    by_id = {a.id: a for a in activities if a.id is not None}
    review = NightlyReview(date=day, planned_minutes=plan.planned_minutes)

    for placement in plan.placements:
        activity = by_id.get(placement.activity_id)
        if activity is None:
            continue
        if activity.state == ActivityState.DONE:
            review.completed.append(activity.title)
        elif activity.state in {ActivityState.PARTIAL, ActivityState.IN_PROGRESS}:
            review.incomplete.append(
                f"{activity.title} — ناقص ({activity.state_reason or 'دلیل ثبت‌نشده'})"
            )
        elif activity.state == ActivityState.OVERDUE:
            review.incomplete.append(f"{activity.title} — عقب‌افتاده")
        elif activity.state == ActivityState.DROPPED:
            review.incomplete.append(f"{activity.title} — حذف‌شده")

    done_minutes = 0
    class_minutes = 0
    independent_minutes = 0
    for session in sessions:
        if session.started_at is None or session.started_at.date() != day:
            continue
        minutes = max(0, int(session.minutes))
        done_minutes += minutes
        if session.kind.value in {"live_class", "recorded_class"}:
            class_minutes += minutes
        else:
            independent_minutes += minutes
    # اگر جلسه‌ای ثبت نشده، از فعالیت‌های انجام‌شده استفاده می‌کنیم.
    if done_minutes == 0:
        done_minutes = sum(
            a.actual_minutes for a in by_id.values() if a.state == ActivityState.DONE
        )
    review.done_minutes = done_minutes
    review.class_minutes = class_minutes
    review.independent_minutes = independent_minutes

    for activity in activities:
        if activity.state == ActivityState.DONE and activity.est_minutes > 0:
            ratio = activity.actual_minutes / activity.est_minutes
            if ratio <= 0.85:
                review.better.append(
                    f"{activity.title}: سریع‌تر از برآورد ({activity.actual_minutes} از {activity.est_minutes} دقیقه)"
                )
            elif ratio >= 1.3:
                review.worse.append(
                    f"{activity.title}: کندتر از برآورد ({activity.actual_minutes} از {activity.est_minutes} دقیقه)"
                )

    if plan.unplaced:
        for item in plan.unplaced:
            review.capacity_risks.append(f"جا نشد: {item.title} — {item.reason}")
    if plan.is_over_capacity:
        review.capacity_risks.append(
            f"برنامهٔ روز {plan.planned_minutes - plan.capacity_minutes} دقیقه "
            "بیش از ظرفیت واقعی است."
        )
    if review.completion_ratio < 0.7 and review.planned_minutes > 0:
        review.capacity_risks.append(
            f"تنها {review.completion_ratio:.0%} برنامهٔ روز اجرا شد؛ "
            "احتمالاً حجم برنامه بیشتر از ظرفیت واقعی بوده است."
        )
    return review


def deadline_risk_notes(
    plans: Sequence[TopicDeadlinePlan],
    *,
    today: Optional[_dt.date] = None,
    warning_window_days: int = 7,
) -> list[str]:
    """مهلت‌هایی که دیگر شدنی نیستند یا در آستانهٔ خطرند."""
    today = today or _dt.date.today()
    notes: list[str] = []
    for plan in plans:
        consolidation = plan.consolidation_date
        if not plan.feasible:
            # حتی اگر تاریخ مهلت ثبت نشده باشد، «شدنی نیست» باید دیده شود.
            notes.append(
                f"{plan.topic_name or 'مبحث'}: مهلت با ظرفیت فعلی شدنی نیست "
                f"({plan.overload_minutes} دقیقه کمبود)."
            )
            continue
        if consolidation is None:
            continue
        days_left = (consolidation - today).days
        if days_left <= warning_window_days and plan.overload_minutes > 0:
            notes.append(
                f"{plan.topic_name}: {days_left} روز تا مهلت مانده و "
                f"{plan.overload_minutes} دقیقه کار جا نشده است."
            )
    return notes


def replan_forward(
    *,
    activities: Sequence[Activity],
    day_plans: Sequence[DayPlan],
    today: _dt.date,
    settings: Optional[Settings] = None,
    horizon_days: int = 7,
    scores: Optional[dict[int, float]] = None,
    protected_ids: Optional[set[int]] = None,
) -> ReplanReport:
    """برنامهٔ روزهای بعد را جلو به عقب بازسازی می‌کند.

    قواعد ثابت:

    * کلاس‌ها و رویدادهای سخت هرگز جابه‌جا نمی‌شوند (در ``day_plans``
      به‌عنوان ظرفیت رعایت شده‌اند؛ اینجا فقط کار مستقل توزیع می‌شود).
    * کار ناقص ابتدا با **اهمیت و فوریت** سنجیده می‌شود؛ اگر مهم و فوری
      بود به نزدیک‌ترین روز ظرفیت‌دار می‌رود، وگرنه بین روزهای باز توزیع
      می‌شود. هیچ کاری کورکورانه به فردا منتقل نمی‌شود.
    * هر تصمیم دلیل دارد و تأثیرش روی مهلت‌ها نوشته می‌شود.
    """
    settings = settings or Settings()
    scores = scores or {}
    protected = protected_ids or set()
    report = ReplanReport()
    horizon_end = today + _dt.timedelta(days=max(1, horizon_days))
    future = [p for p in day_plans if today <= p.date <= horizon_end]
    report.fixed_preserved = sum(
        1 for plan in future for note in plan.notes if "کلاس" in note
    )

    free_by_date = {
        plan.date: max(0, plan.margin_minutes) for plan in future
    }
    pending = [
        a
        for a in activities
        if a.state
        in {ActivityState.PARTIAL, ActivityState.IN_PROGRESS, ActivityState.OVERDUE}
        and a.type not in ASSESSMENT_TYPES
    ]
    pending.sort(key=lambda a: -scores.get(a.id or -1, 0.0))

    for activity in pending:
        minutes = activity.effective_minutes
        is_protected = (activity.topic_id or -1) in protected or activity.has_hard_deadline
        placed = False
        for plan in sorted(future, key=lambda p: p.date):
            if free_by_date.get(plan.date, 0) >= min(minutes, activity.max_chunk):
                target = plan.date
                free_by_date[target] -= minutes
                placed = True
                break
        if not placed and minutes > 0:
            if is_protected:
                # کار محافظت‌شده (مهلت سخت یا مبحث پیش‌نیاز) جا نشد: این
                # «ریسک مهلت» است و باید صریح گزارش شود، نه اینکه بی‌صدا
                # کنار گذاشته شود.
                report.decisions.append(
                    ReplanDecision(
                        activity_id=int(activity.id or 0),
                        title=activity.title,
                        action="keep_today",
                        reason=(
                            "ظرفیت خالی برای این کار پیدا نشد، ولی چون مهلت سخت "
                            "یا پیش‌نیاز بودنش محافظت دارد روی برنامه می‌ماند."
                        ),
                    )
                )
                report.changes.append(
                    NightlyChange(
                        title=f"ریسک مهلت برای «{activity.title}»",
                        reason=(
                            "در هفت روز پیش رو ظرفیت خالی برای این کار نماند و "
                            "به‌خاطر محافظت از حذف، روی همان روز می‌ماند."
                        ),
                        deadline_impact=(
                            "اگر مهلتش عقب برود، پله‌های بعدی این مبحث هم "
                            "جابه‌جا می‌شوند."
                        ),
                        severity="critical",
                    )
                )
                continue
            # جا نشد و محافظت هم ندارد: به‌عنوان کاندیدای تعویق ثبت می‌شود،
            # نه حذف بی‌صدا.
            report.decisions.append(
                ReplanDecision(
                    activity_id=int(activity.id or 0),
                    title=activity.title,
                    action="defer",
                    reason=(
                        "در بازهٔ هفت روز ظرفیت خالی برای این کار نماند؛ "
                        "برای تأیید یا جابه‌جایی دستی نیاز به تصمیم توست."
                    ),
                )
            )
            report.changes.append(
                NightlyChange(
                    title=f"تعویق «{activity.title}»",
                    reason="ظرفیت آزاد در هفت روز پیش رو کافی نبود.",
                    deadline_impact="اگر مهلت سخت داشته باشد، موعدش به خطر می‌افتد.",
                    severity="warning" if activity.has_hard_deadline else "info",
                )
            )
            continue

        if activity.state == ActivityState.OVERDUE and placed:
            action = "rollover"
            reason = (
                "کار عقب‌افتاده بود و فوریت/اهمیتش اجازهٔ دفع نشد؛ "
                "به نزدیک‌ترین روز با ظرفیت خالی رفت."
            )
        elif placed:
            action = "redistribute"
            reason = (
                "کار ناقص بین روزهای باز توزیع شد؛ مهم و فوری‌ترها جلوتر "
                "نشستند و کلاس‌های ثابت دست‌نخورده ماندند."
            )
        else:
            action = "keep_today"
            reason = "محافظت‌شده است (مهلت سخت یا مبحث پیش‌نیاز)؛ روی همین روز می‌ماند."
        report.decisions.append(
            ReplanDecision(
                activity_id=int(activity.id or 0),
                title=activity.title,
                action=action,
                reason=reason,
                target_date=None,
            )
        )
        report.redistributed_minutes += minutes
    return report


def summarize_review(
    review: NightlyReview,
    replan: ReplanReport,
    *,
    deadline_risks: Optional[Sequence[str]] = None,
    open_problems: Optional[Sequence[LearningProblem]] = None,
) -> str:
    """متن فارسی یک‌پاراگرافی برای نمایش در «برنامهٔ هفتگی» و «گزارش مشاور»."""
    parts: list[str] = []
    parts.append(
        f"امروز {review.done_minutes} دقیقه از {review.planned_minutes} دقیقهٔ "
        f"برنامه اجرا شد ({review.completion_ratio:.0%})."
    )
    parts.append(
        f"از این تعداد، {review.class_minutes} دقیقه کلاس و "
        f"{review.independent_minutes} دقیقه مطالعهٔ مستقل بود."
    )
    if review.incomplete:
        parts.append("ناقص مانده: " + "؛ ".join(review.incomplete[:4]) + ".")
    if review.worse:
        parts.append("کندتر از برآورد: " + "؛ ".join(review.worse[:3]) + ".")
    if review.better:
        parts.append("سریع‌تر از برآورد: " + "؛ ".join(review.better[:3]) + ".")
    for risk in list(deadline_risks or [])[:3]:
        parts.append("ریسک مهلت: " + risk)
    for problem in list(open_problems or [])[:3]:
        parts.append(f"مشکل باز: {problem.title} (شدت {problem.severity}).")
    if replan.changes:
        parts.append(
            "تغییرهای برنامه: " + "؛ ".join(c.title for c in replan.changes[:3]) + "."
        )
    return " ".join(parts)


def independent_minutes_of(activities: Sequence[Activity]) -> int:
    """دقیقهٔ مطالعهٔ مستقل در یک مجموعه فعالیت (کلاس‌ها شمرده نمی‌شوند)."""
    return sum(
        a.effective_minutes
        for a in activities
        if a.type in INDEPENDENT_TYPES
    )


def assessment_minutes_of(activities: Sequence[Activity]) -> int:
    return sum(a.effective_minutes for a in activities if a.type in ASSESSMENT_TYPES)


__all__ = [
    "ASSESSMENT_TYPES",
    "INDEPENDENT_TYPES",
    "ReplanDecision",
    "ReplanReport",
    "assessment_minutes_of",
    "classify_day",
    "deadline_risk_notes",
    "independent_minutes_of",
    "replan_forward",
    "summarize_review",
]
