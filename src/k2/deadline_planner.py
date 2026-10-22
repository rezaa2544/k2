"""بازمحاسبهٔ مهلت‌های مبحث و امکان‌سنجی آن‌ها (بند ۱۲).

ایدهٔ مرکزی: کاربر «مهلت تثبیت نهایی» را می‌دهد و برنامه از آن روز به
عقب برمی‌گردد و می‌بیند هر پلهٔ مسیر چند روز وقت می‌خواهد. اگر جمع زمان
لازم بیشتر از ظرفیت واقعی باقی‌مانده باشد، برنامه **صادقانه** هشدار می‌دهد
و یکی از چهار پیشنهاد را می‌کند:

۱. مهلت را عقب بکش (زمان بیشتر)  ۲. حجم را کم کن
۳. اولویت‌ها را جابه‌جا کن      ۴. خود مهلت را جابه‌جا کن

هیچ‌کدام از این‌ها به‌جای کاربر تصمیم گرفته نمی‌شود؛ فقط تأثیرش روی تاریخ
نشان داده می‌شود. تکمیل یک مهلت بدون «شاهد» (نمره/سنجش) پذیرفته نیست.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Optional, Sequence

from .config import Settings
from .domain.enums import DeadlineKind, FeasibilityAction, TrackKind
from .domain.models import (
    DeadlineMilestone,
    DeadlineSuggestion,
    StudySession,
    TopicDeadline,
    TopicDeadlinePlan,
)

# ---------------------------------------------------------------------------
# برآورد زمان هر پله — فرضیهٔ محصول [H] و قابل تنظیم
# ---------------------------------------------------------------------------

#: دقیقهٔ تقریبی هر پله برای یک مبحث با حجم «متوسط» (بر حسب نوع محتوا).
DEFAULT_STAGE_MINUTES: dict[DeadlineKind, int] = {
    DeadlineKind.START: 30,
    DeadlineKind.INITIAL_LEARNING: 240,
    DeadlineKind.PRACTICE: 180,
    DeadlineKind.FINAL_CONSOLIDATION: 120,
}

#: ضریب برآورد برای هر مسیر؛ مسیر نهایی/مدرک سنگین‌تر است [H].
TRACK_MINUTE_FACTOR: dict[TrackKind, float] = {
    TrackKind.KONKUR: 1.0,
    TrackKind.FINAL: 1.25,
}

#: کمینهٔ روزهای لازم برای یک پله (جلوگیری از برنامهٔ غیرواقعی).
MIN_STAGE_DAYS: dict[DeadlineKind, int] = {
    DeadlineKind.START: 1,
    DeadlineKind.INITIAL_LEARNING: 2,
    DeadlineKind.PRACTICE: 2,
    DeadlineKind.FINAL_CONSOLIDATION: 2,
}

#: عنوان پله‌ها در نمایش.
STAGE_LABELS: dict[DeadlineKind, str] = {
    DeadlineKind.START: "شروع مطالعه",
    DeadlineKind.INITIAL_LEARNING: "پایان یادگیری اولیه",
    DeadlineKind.PRACTICE: "پایان تمرین و تست",
    DeadlineKind.FINAL_CONSOLIDATION: "تثبیت نهایی",
}

#: ترتیب بازمحاسبه: از آخرین مهلت به عقب.
BACKWARD_ORDER: tuple[DeadlineKind, ...] = (
    DeadlineKind.FINAL_CONSOLIDATION,
    DeadlineKind.PRACTICE,
    DeadlineKind.INITIAL_LEARNING,
    DeadlineKind.START,
)

#: فاصلهٔ کمینهٔ ایمن بین دو پله متوالی (روز) [H].
MIN_GAP_DAYS = 1


@dataclass
class DeadlineInput:
    """ورودی بازمحاسبه برای یک مبحث."""

    topic_id: int
    topic_name: str = ""
    subject_name: str = ""
    #: مهلت تثبیت نهایی (مرجع بازمحاسبه).
    consolidation_date: Optional[_dt.date] = None
    #: تاریخ آزمون هدف برای محاسبهٔ ظرفیت باقی‌مانده.
    exam_date: Optional[_dt.date] = None
    #: مسیری که این مهلت‌ها برای آن است.
    track: TrackKind = TrackKind.KONKUR
    #: برآورد زمان هر پله به دقیقه (اگر کاربر خودش وارد کرده باشد).
    stage_minutes: dict[DeadlineKind, int] = field(default_factory=dict)
    #: سطح تسلط فعلی؛ پله‌های گذشتهٔ تسلط را کوتاه می‌کند.
    mastery_level: int = 0
    #: ظرفیت مؤثر روزانهٔ کاربر (دقیقه).
    daily_capacity_minutes: int = 180
    #: تاریخ امروز (برای تست‌پذیری).
    today: Optional[_dt.date] = None
    #: درصد هدف و سطح هدف برای پیام امکان‌سنجی.
    target_percent: Optional[float] = None
    target_level: Optional[str] = None
    note: str = ""


def stage_minutes_for(
    kind: DeadlineKind,
    *,
    track: TrackKind = TrackKind.KONKUR,
    override: Optional[int] = None,
) -> int:
    """دقیقهٔ لازم یک پله با توجه به مسیر و مقدار دستی کاربر."""
    if override is not None and override > 0:
        return int(override)
    base = DEFAULT_STAGE_MINUTES[kind]
    factor = TRACK_MINUTE_FACTOR.get(track, 1.0)
    return int(round(base * factor))


def _resolve_today(today: Optional[_dt.date]) -> _dt.date:
    return today or _dt.date.today()


def back_calculate(inp: DeadlineInput) -> TopicDeadlinePlan:
    """از مهلت تثبیت نهایی به عقب برمی‌گردد و تاریخ هر پله را می‌سازد."""
    today = _resolve_today(inp.today)
    plan = TopicDeadlinePlan(
        topic_id=inp.topic_id,
        topic_name=inp.topic_name,
        subject_name=inp.subject_name,
        capacity_minutes_per_day=max(0, int(inp.daily_capacity_minutes)),
        available_days=0,
    )
    if inp.consolidation_date is None:
        plan.feasible = False
        plan.warnings.append("مهلت تثبیت نهایی ثبت نشده است؛ بازمحاسبه انجام نشد.")
        plan.suggestions.append(
            DeadlineSuggestion(
                action=FeasibilityAction.MOVE_DEADLINE,
                title="مهلت تثبیت نهایی را وارد کن",
                detail="بدون این مهلت نمی‌توان تاریخ شروع و تمرین را محاسبه کرد.",
            )
        )
        return plan

    if inp.consolidation_date < today:
        plan.feasible = False
        plan.warnings.append(
            "مهلت تثبیت نهایی در گذشته است؛ ابتدا آن را به یک تاریخ ممکن ببر."
        )
        return plan

    total_minutes = 0
    cursor = inp.consolidation_date
    for kind in BACKWARD_ORDER:
        minutes = stage_minutes_for(
            kind, track=inp.track, override=inp.stage_minutes.get(kind)
        )
        total_minutes += minutes
        days_needed = _days_for(minutes, inp.daily_capacity_minutes, kind)
        milestone_date = cursor
        if kind != DeadlineKind.FINAL_CONSOLIDATION:
            milestone_date = cursor - _dt.timedelta(days=days_needed + MIN_GAP_DAYS)
        plan.milestones.append(
            DeadlineMilestone(
                kind=kind,
                label=STAGE_LABELS[kind],
                date=milestone_date,
                minutes=minutes,
            )
        )
        if kind != DeadlineKind.FINAL_CONSOLIDATION:
            cursor = milestone_date

    plan.total_minutes = total_minutes
    start = plan.start_date
    if start is not None:
        # ظرفیت واقعی از **بعدترین** تاریخ ممکن محاسبه می‌شود: اگر بازمحاسبه
        # به تاریخی در گذشته رسیده، آن روزها دیگر وجود ندارند و باید به‌عنوان
        # کمبود ظرفیت دیده شوند.
        effective_start = max(today, start)
        plan.available_days = max(0, (inp.consolidation_date - effective_start).days)
        if start < today:
            plan.feasible = False
            late_days = (today - start).days
            plan.warnings.append(
                f"برای رسیدن به این مهلت باید {late_days} روز پیش‌تر شروع می‌شدی؛ "
                "آن روزها گذشته است و به‌عنوان کمبود ظرفیت حساب می‌شوند."
            )
    plan.required_days = round(total_minutes / max(1, inp.daily_capacity_minutes), 1)
    if inp.daily_capacity_minutes <= 0:
        # بدون ظرفیت، هیچ تاریخی «شدنی» نیست؛ برنامه نباید تاریخ جعلی بسازد.
        plan.feasible = False
        plan.warnings.append(
            "ظرفیت روزانهٔ مطالعه صفر ثبت شده است؛ ابتدا ساعت بیداری، خواب و "
            "بازهٔ آزادت را در تنظیمات وارد کن."
        )
    if not plan.feasible:
        plan.suggestions = build_suggestions(plan, inp)
    return plan


def _days_for(minutes: int, daily_capacity: int, kind: DeadlineKind) -> int:
    """چند روز برای این پله لازم است (کف روزهای هر پله رعایت می‌شود)."""
    floor = MIN_STAGE_DAYS[kind]
    if daily_capacity <= 0:
        return floor + 7  # بدون ظرفیت، برنامه هیجدست می‌سازد نه تاریخ جعلی
    days = max(1, -(-minutes // max(1, daily_capacity)))  # سقف‌گذاری صحیح
    return max(floor, int(days))


def build_suggestions(
    plan: TopicDeadlinePlan, inp: DeadlineInput
) -> list[DeadlineSuggestion]:
    """چهار پیشنهاد همیشه داده می‌شود تا کاربر خودش انتخاب کند."""
    suggestions: list[DeadlineSuggestion] = []
    overload = plan.overload_minutes
    capacity = max(1, inp.daily_capacity_minutes)
    if overload > 0:
        extra_days = -(-overload // capacity)
        suggestions.append(
            DeadlineSuggestion(
                action=FeasibilityAction.MORE_TIME,
                title="مهلت تثبیت نهایی را عقب بکش",
                detail=(
                    f"با ظرفیت روزانهٔ {_fa(inp.daily_capacity_minutes)} دقیقه، "
                    f"{extra_days} روز دیگر لازم است تا همهٔ پله‌ها جا شوند."
                ),
                shift_days=int(extra_days),
            )
        )
        suggestions.append(
            DeadlineSuggestion(
                action=FeasibilityAction.LESS_VOLUME,
                title="حجم مبحث را کم کن",
                detail=(
                    "اگر بخشی از این مبحث را به بعد از آزمون موکول کنی یا از "
                    "بودجهٔ رسمی خارجش کنی، مهلت ممکن می‌شود. فقط خودت تصمیم بگیر "
                    "کدام بخش حذف شود؛ برنامه حدس نمی‌زند."
                ),
                shift_days=0,
            )
        )
    suggestions.append(
        DeadlineSuggestion(
            action=FeasibilityAction.REPRIORITIZE,
            title="اولویت این مبحث را پایین ببر",
            detail=(
                "اگر این مبحث برای نمرهٔ کلیدی‌ات حائز اهمیت نیست، ظرفیت روزهای "
                "نزدیک را به مبحث‌های با سهم بیشتر بده. مبحث حذف نمی‌شود، فقط "
                "دیرتر تمام می‌شود."
            ),
            shift_days=0,
        )
    )
    suggestions.append(
        DeadlineSuggestion(
            action=FeasibilityAction.MOVE_DEADLINE,
            title="خود مهلت را جابه‌جا کن",
            detail=(
                "مهلت تثبیت نهایی را به تاریخی ببر که با ظرفیت واقعی‌ات بخواند؛ "
                "بازمحاسبهٔ تاریخ‌های شروع و تمرین خودش به‌روز می‌شود."
            ),
            shift_days=0,
        )
    )
    return suggestions


def deadline_progress_ratio(
    deadline: TopicDeadline,
    sessions: Sequence[StudySession],
    *,
    today: Optional[_dt.date] = None,
) -> float:
    """نسبت پیشرفت یک مهلت بر پایهٔ دقیقهٔ ثبت‌شدهٔ مرتبط.

    این نسبت **اطمینانِ تلاش** است، نه اثباتِ تسلط؛ اثبات فقط با شاهد
    (سنجش/تست) پذیرفته می‌شود.
    """
    if deadline.target_date is None:
        return 0.0
    today = _resolve_today(today)
    total = 0.0
    for session in sessions:
        if session.topic_id != deadline.topic_id:
            continue
        if session.started_at is None:
            continue
        if session.started_at.date() > deadline.target_date:
            continue
        total += max(0, session.minutes)
    return total


def feasibility_message(plan: TopicDeadlinePlan) -> str:
    """پیام فارسی و صادقانهٔ وضعیت مهلت."""
    if plan.feasible and not plan.warnings:
        return (
            f"مهلت شدنی است: {plan.total_minutes} دقیقهٔ کار در "
            f"{plan.available_days} روز با ظرفیت روزانهٔ "
            f"{_fa(plan.capacity_minutes_per_day)} دقیقه."
        )
    parts = list(plan.warnings)
    if plan.overload_minutes > 0:
        parts.append(
            f"{plan.overload_minutes} دقیقه بیش از ظرفیت باقی‌مانده است."
        )
    if plan.suggestions:
        parts.append("پیشنهادها: " + " | ".join(s.title for s in plan.suggestions[:4]))
    return " ".join(parts)


def _fa(value: float) -> str:
    """عدد فارسی با یک رقم اعشار."""
    text = f"{float(value):,.1f}".rstrip("0").rstrip(".")
    return text.replace(",", "،")


__all__ = [
    "BACKWARD_ORDER",
    "DEFAULT_STAGE_MINUTES",
    "DeadlineInput",
    "MIN_GAP_DAYS",
    "STAGE_LABELS",
    "back_calculate",
    "build_suggestions",
    "deadline_progress_ratio",
    "feasibility_message",
    "stage_minutes_for",
]
