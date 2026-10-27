"""هدفِ «تا تاریخ فلانی فصل X از کتاب Y تمام شود» (بند ۱۲ و سرفصل).

کاربر گفت: «من یک بخش رو لازم دارم که برایم تعیین کند که تا تایم فلانی،
مثلا بخش ۱ رو از کتاب فلانی تمام کنم.»

فصل‌بندی از همان دیتای سرفصل کتاب درسی می‌آید
(``konkur_catalog`` → ``syllabus``) و دستی تایپ نمی‌شود. کارِ این ماژول
فقط این است که حجم واقعی آن فصل را به روزهای موجود تا مهلت تقسیم کند و
**صادقانه** بگوید شدنی است یا نه — بدون اینکه تاریخ جعلی بسازد.

سه چیزی که اینجا تضمین می‌شود:

* گفتار «ارزیابی‌نشده» حذف نمی‌شود؛ اگر کاربر نخواسته فقط نیازهای باز را
  بشمارد، همهٔ گفتارهای فصل حساب می‌شوند.
* اگر مهلت گذشته یا ظرفیت کم باشد، برنامه تاریخ نمی‌سازد بلکه کمبود روز را
  می‌گوید و راه‌های جبران را نشان می‌دهد.
* تقسیم‌بندی روزانه از ظرفیت واقعی کاربر می‌آید، نه از یک عدد ثابت.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Optional

from .deadline_planner import (
    BACKWARD_ORDER,
    MIN_GAP_DAYS,
    MIN_STAGE_DAYS,
    STAGE_LABELS,
    DeadlineInput,
    build_suggestions,
    stage_minutes_for,
)
from .domain.models import DeadlineMilestone
from .domain.enums import DeadlineKind, TrackKind

#: کمینهٔ روزهای لازم برای تمام یک فصل، مستقل از حجم.
MIN_CHAPTER_DAYS = 3


@dataclass
class ChapterGoalInput:
    """ورودی هدف یک فصل."""

    subject: str
    grade: int
    chapter: int
    #: مهلت پایانِ کار روی این فصل.
    deadline: Optional[_dt.date] = None
    #: ظرفیت مؤثر روزانهٔ کاربر (دقیقه).
    daily_capacity_minutes: int = 180
    #: فقط گفتارهایی که نیاز باز دارند حساب شوند.
    only_open_needs: bool = True
    track: TrackKind = TrackKind.KONKUR
    #: تعداد گفتارها؛ اگر ``None`` باشد از سرفصل خوانده می‌شود.
    section_count: Optional[int] = None
    #: تعداد گفتارهای دارای نیاز باز (اگر ``only_open_needs``).
    open_section_count: Optional[int] = None
    #: برآورد دستی کاربر برای هر پله.
    stage_minutes: dict[DeadlineKind, int] = field(default_factory=dict)
    today: Optional[_dt.date] = None


@dataclass
class DayAllocation:
    """سهم یک روز از فصل."""

    date: _dt.date
    minutes: int
    #: چند گفتار در این روز پوشش داده می‌شود (کسری).
    sections: float


@dataclass
class ChapterGoalPlan:
    """نتیجهٔ محاسبهٔ هدف فصل."""

    subject: str = ""
    grade: int = 0
    chapter: int = 0
    chapter_title: str = ""
    section_count: int = 0
    open_section_count: int = 0
    minutes_per_section: int = 0
    total_minutes: int = 0
    capacity_minutes_per_day: int = 0
    required_days: float = 0.0
    available_days: int = 0
    missing_days: int = 0
    feasible: bool = True
    #: تاریخ‌های پله‌ها (شروع → یادگیری → تمرین → تثبیت).
    milestones: list = field(default_factory=list)
    #: تقسیم روزانه از تاریخ شروع تا مهلت.
    per_day: list[DayAllocation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list = field(default_factory=list)

    @property
    def minutes_per_day_text(self) -> str:
        from .jdate import format_minutes

        return format_minutes(self.capacity_minutes_per_day)


def minutes_per_section(
    inp: ChapterGoalInput,
) -> int:
    """زمان لازم برای یک گفتار: جمع چهار پلهٔ مسیر."""
    total = 0
    for kind in BACKWARD_ORDER:
        total += stage_minutes_for(
            kind, track=inp.track, override=inp.stage_minutes.get(kind)
        )
    return total


def _as_topic_plan(plan: "ChapterGoalPlan", deadline: Optional[_dt.date]):
    """نمای سازگار با ``build_suggestions`` تا پیشنهادهای مشترک استفاده شوند."""
    from .domain.models import TopicDeadlinePlan

    return TopicDeadlinePlan(
        topic_id=0,
        topic_name=f"فصل {plan.chapter}",
        subject_name=plan.subject,
        capacity_minutes_per_day=plan.capacity_minutes_per_day,
        available_days=plan.available_days,
        total_minutes=plan.total_minutes,
        required_days=plan.required_days,
        missing_days=plan.missing_days,
        feasible=plan.feasible,
        warnings=list(plan.warnings),
        milestones=list(plan.milestones),
    )


def plan_chapter_goal(inp: ChapterGoalInput):
    """هدف فصل را محاسبه می‌کند؛ اگر شدنی نبود صادقانه می‌گوید چرا."""
    today = inp.today or _dt.date.today()
    per_section = minutes_per_section(inp)

    if inp.section_count is not None:
        total_sections = int(inp.section_count)
    else:
        total_sections = 0
    if inp.only_open_needs and inp.open_section_count is not None:
        counted = max(0, int(inp.open_section_count))
    else:
        counted = total_sections

    plan = ChapterGoalPlan(
        subject=inp.subject,
        grade=inp.grade,
        chapter=inp.chapter,
        section_count=total_sections,
        open_section_count=counted,
        minutes_per_section=per_section,
        capacity_minutes_per_day=max(0, int(inp.daily_capacity_minutes)),
    )

    if counted <= 0:
        plan.feasible = False
        plan.warnings.append(
            "برای این فصل گفتارِ بازِ شمارش‌شدنی نیست. اگر همهٔ گفتارها را "
            "می‌خواهی بشماری، گزینهٔ «همهٔ گفتارهای فصل» را انتخاب کن."
        )
        return plan

    if inp.deadline is None:
        plan.feasible = False
        plan.warnings.append(
            "مهلت وارد نشده؛ بدون آن نمی‌توان گفت تا آن روز چند روز وقت داری."
        )
        return plan

    plan.total_minutes = per_section * counted
    capacity = max(1, inp.daily_capacity_minutes)

    # ---- بازمحاسبه از مهلت به عقب، با حجمِ *کل فصل* ----
    # حجم هر پله مقیاس‌شده با تعداد گفتارهاست، نه حجم یک مبحث تکی. اگر
    # فقط ``back_calculate`` را صدا می‌زدیم، تاریخ شروع از حجم یک گفتار
    # حساب می‌شد و برنامه کمبود روز را دست‌کم می‌گرفت.
    stage_minutes: dict[DeadlineKind, int] = {}
    for kind in BACKWARD_ORDER:
        stage_minutes[kind] = stage_minutes_for(
            kind, track=inp.track, override=inp.stage_minutes.get(kind)
        ) * counted

    def _days_for(minutes: int, kind: DeadlineKind) -> int:
        floor = MIN_STAGE_DAYS[kind]
        if inp.daily_capacity_minutes <= 0:
            return floor + 7
        return max(floor, -(-minutes // capacity))

    # ``milestone_date`` یعنی «تا این روز باید این پله تمام شده باشد».
    # پس از آن روز به عقب می‌رویم و روزهای کار همان پله را کنار می‌گذاریم.
    # نکتهٔ مهم: روزهای کار پلهٔ *تثبیت نهایی* هم باید از بازه کنار گذاشته
    # شود، وگرنه بازهٔ لازم از روزهای کار کمتر به نظر می‌رسد.
    cursor = inp.deadline
    for kind in BACKWARD_ORDER:
        minutes = stage_minutes[kind]
        days_needed = _days_for(minutes, kind)
        complete_by = cursor
        plan.milestones.append(
            DeadlineMilestone(
                kind=kind,
                label=STAGE_LABELS[kind],
                date=complete_by,
                minutes=minutes,
            )
        )
        cursor = complete_by - _dt.timedelta(days=days_needed)
        if kind != DeadlineKind.START:
            cursor -= _dt.timedelta(days=MIN_GAP_DAYS)

    start = cursor
    needed_days = max(
        -(-plan.total_minutes // capacity),
        max((MIN_STAGE_DAYS[k] for k in BACKWARD_ORDER), default=1),
    )
    plan.required_days = float(needed_days)
    effective_start = max(today, start)

    # بازهٔ تقویمی که این فصل می‌خواهد (شامل فاصلهٔ بین پله‌ها) در برابر
    # بازه‌ای که کاربر واقعاً دارد: از امروز تا مهلت. مقایسه با
    # ``effective_start`` circular است و همیشه کمبود می‌دهد.
    required_span = (inp.deadline - start).days
    plan.available_days = max(0, (inp.deadline - today).days)
    plan.missing_days = max(0, required_span - plan.available_days)

    if plan.missing_days > 0:
        plan.feasible = False
        plan.warnings.append(
            f"تا این مهلت {plan.missing_days} روز کم داری؛ این فصل با "
            f"ظرفیت روزانهٔ {plan.capacity_minutes_per_day} دقیقه "
            f"{needed_days} روز کار و {required_span} روز تقویم می‌خواهد."
        )
    if start < today:
        plan.feasible = False
        late = (today - start).days
        plan.warnings.append(
            f"برای رسیدن به این مهلت باید {late} روز پیش‌تر شروع می‌شدی؛ "
            "آن روزها گذشته است و به‌عنوان کمبود ظرفیت حساب می‌شوند."
        )
    if inp.daily_capacity_minutes <= 0:
        plan.feasible = False
        plan.warnings.append(
            "ظرفیت روزانهٔ مطالعه صفر ثبت شده است؛ ابتدا ساعت بیداری، خواب و "
            "بازهٔ آزادت را در تنظیمات وارد کن."
        )
    if not plan.feasible:
        plan.suggestions = build_suggestions(
            _as_topic_plan(plan, inp.deadline),
            DeadlineInput(
                topic_id=0,
                topic_name=f"فصل {inp.chapter}",
                subject_name=inp.subject,
                consolidation_date=inp.deadline,
                daily_capacity_minutes=inp.daily_capacity_minutes,
                today=today,
            ),
        )

    # ---- تقسیم روزانه از روزی که باید شروع شود تا مهلت ----
    if plan.feasible and inp.daily_capacity_minutes > 0:
        cursor = effective_start
        remaining = plan.total_minutes
        while cursor <= inp.deadline and remaining > 0:
            minutes = min(inp.daily_capacity_minutes, remaining)
            plan.per_day.append(
                DayAllocation(
                    date=cursor,
                    minutes=minutes,
                    sections=round(minutes / max(1, per_section), 2),
                )
            )
            remaining -= minutes
            cursor += _dt.timedelta(days=1)
        if remaining > 0:
            plan.warnings.append(
                "بازهٔ تا مهلت برای کل این فصل کافی نشد؛ سهم روزهای آخر را "
                "بازبینی کن."
            )
            plan.feasible = False

    return plan


__all__ = [
    "ChapterGoalInput",
    "ChapterGoalPlan",
    "DayAllocation",
    "minutes_per_section",
    "plan_chapter_goal",
]
