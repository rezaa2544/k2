"""زمان‌بند قاعده‌محور و توضیح‌پذیر (سند تحقیق ۲، بخش ۹ و ۱۱).

ویژگی‌های کلیدی:
  * **بدون هم‌پوشانی**: هر بازهٔ آزاد فقط یک‌بار مصرف می‌شود.
  * **بدون نقض خواب**: خواب و رویدادهای سخت در بازهٔ آزاد قرار ندارند.
  * **بدون اضافه‌کاری پنهان**: مجموع زمان برنامه‌ریزی‌شده ≤ ظرفیت روز.
  * **توضیح‌پذیر**: هر جای‌گذاری دلیل دارد و هر فعالیت جا‌نشده صریح گزارش می‌شود.

این نسخه عمداً **قاعده‌محور + امتیازدهی** است. CP-SAT/OR-Tools فقط در صورتی
اضافه می‌شود که بنچمارک نشان دهد روش ساده نیاز را برآورده نمی‌کند (SCH-06).
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Optional, Sequence

from .capacity import CapacityBreakdown, Interval, compute_capacity
from .config import Settings
from .domain.enums import ActivityState, DeadlineType, EnergyNeed
from .domain.models import Activity, DayPlan, FixedEvent, Placement, Routine, UnplacedActivity
from .jdate import weekday_index, weekday_name

# ---------------------------------------------------------------------------
# زمینهٔ زمان‌بندی
# ---------------------------------------------------------------------------


@dataclass
class SchedulingContext:
    """همهٔ ورودی‌های لازم برای برنامه‌ریزی یک بازهٔ روز."""

    wake_minute: int = 6 * 60
    sleep_minute: int = 23 * 60
    fixed_events: Sequence[FixedEvent] = field(default_factory=list)
    routines: Sequence[Routine] = field(default_factory=list)
    exceptions: Sequence = field(default_factory=list)
    energy_level: int = 2
    #: بازه‌های پربازده (دقیقه از ابتدای شبانه‌روز) — خودگزارشی یا آموخته‌شده.
    peak_hours: Sequence[tuple[int, int]] = field(default_factory=list)
    focus_factor: Optional[float] = None
    settings: Settings = field(default_factory=Settings)

    def capacity_for(self, date: _dt.date) -> CapacityBreakdown:
        return compute_capacity(
            date,
            wake_minute=self.wake_minute,
            sleep_minute=self.sleep_minute,
            fixed_events=self.fixed_events,
            routines=self.routines,
            exceptions=self.exceptions,
            energy_level=self.energy_level,
            settings=self.settings,
            focus_factor=self.focus_factor,
        )


@dataclass
class PriorityScore:
    """امتیاز اولویت به‌همراه اجزای آن (قابل نمایش به کاربر)."""

    total: float = 0.0
    components: tuple[tuple[str, float], ...] = ()

    def component(self, name: str) -> float:
        for label, value in self.components:
            if label == name:
                return value
        return 0.0


@dataclass
class TopicFactors:
    """فاکتورهای مبحثیِ اولویت که از فعالیت به‌تنهایی خوانده نمی‌شوند (بند ۱۴).

    همهٔ مقادیر اختیاری‌اند تا با دادهٔ ناقص هم اولویت‌دهی کار کند؛ فاکتورِ
    ناشناخته صفر شمرده می‌شود و در رابط کاربری به‌صورت «نامشخص» نشان داده
    می‌شود، نه اینکه برنامه خطا بدهد.
    """

    #: این مبحث پیش‌نیاز چند مبحث دیگر است (۰..۱).
    prerequisite_share: float = 0.0
    #: سهم لازم در سؤال‌های تشریحی/نهایی (۰..۱).
    final_exam_share: float = 0.0
    #: سرعت فراموشی (۰..۱) — از مدل حافظه.
    forgetting_rate: float = 0.0
    #: فاصلهٔ روز تا مهلت اختصاصی خود مبحث (None = مهلتی ثبت نشده).
    topic_deadline_days: Optional[float] = None
    #: کار باقی‌ماندهٔ مبحث (دقیقه).
    remaining_minutes: float = 0.0
    #: ظرفیت باقی‌مانده تا آن مهلت (دقیقه).
    available_minutes: float = 0.0
    #: وزن اهمیت مبحث در آزمون هدف (برای محافظت از حذف).
    importance: float = 1.0
    #: ضعف ثبت‌شده در آزمون (۰..۱).
    exam_weakness: float = 0.0


# ---------------------------------------------------------------------------
# کمک‌کننده‌ها
# ---------------------------------------------------------------------------


def _split_blocks(free: Sequence[Interval], max_block: int) -> list[Interval]:
    """بلوک‌های آزاد را به بلوک‌های مطالعهٔ قابل استفاده تقسیم می‌کند.

    تقسیم «متوازن» است تا قطعهٔ بسیار کوتاه در انتها باقی نماند.
    """
    blocks: list[Interval] = []
    for interval in free:
        length = interval.minutes
        if length <= 0:
            continue
        count = max(1, -(-length // max_block))
        base = length // count
        remainder = length % count
        cursor = interval.start
        for index in range(count):
            size = base + (1 if index < remainder else 0)
            blocks.append(Interval(start=cursor, end=cursor + size, kind="free", hard=False))
            cursor += size
    return blocks


def _is_peak(start: int, end: int, peak_hours: Sequence[tuple[int, int]]) -> bool:
    if not peak_hours:
        return False
    for peak_start, peak_end in peak_hours:
        if start < peak_end and peak_start < end:
            return True
    return False


def _days_until(deadline: Optional[_dt.datetime], today: _dt.date) -> Optional[float]:
    if deadline is None:
        return None
    delta = deadline.date() - today
    return delta.days


def progress_probability(
    remaining_minutes: float, available_minutes: float
) -> float:
    """احتمال پیشرفت معنادار در زمان باقی‌مانده (بند ۱۴، فاکتور نهم).

    نسبت کار باقی‌مانده به ظرفیت باقی‌مانده؛ اگر کار بیشتر از ظرفیت باشد
    احتمال پایین می‌آید و آن مبحث در برنامهٔ روز اولویت کمتری می‌گیرد —
    اما **حذف نمی‌شود** (به ``protect_reason`` نگاه کن).
    """
    if remaining_minutes <= 0:
        return 1.0
    if available_minutes <= 0:
        return 0.0
    ratio = available_minutes / remaining_minutes
    return max(0.0, min(1.0, ratio))


def compute_priority(
    activity: Activity,
    *,
    today: _dt.date,
    settings: Settings,
    debt_age_days: float = 0.0,
    topic_factors: Optional[TopicFactors] = None,
) -> PriorityScore:
    """امتیاز اولویت یک فعالیت (سند تحقیق ۲، بخش ۷).

    همهٔ وزن‌ها فرضیهٔ محصول [H] و از تنظیمات خوانده می‌شوند.

    یازده فاکتور: مهلت فعالیت، فعالیت‌های مسدود، ضعف مبحث × اهمیت، مرور
    سررسید، سن بدهی، هزینهٔ زمان، پیش‌نیاز بودن، سهم آزمون نهایی، سرعت
    فراموشی، نزدیکی مهلت اختصاصی مبحث و احتمال پیشرفت در زمان موجود.
    """
    w = settings.scheduler
    components: list[tuple[str, float]] = []

    # 1) فوریت مهلت
    days_to = _days_until(activity.deadline_at, today)
    if days_to is None:
        urgency = 0.0
    else:
        urgency = 1.0 / max(0.5, float(days_to))
        if activity.deadline_type == DeadlineType.HARD:
            urgency *= w.hard_deadline_multiplier
    components.append(("فوریت مهلت", urgency * w.w_deadline))

    # 2) تعداد فعالیت‌های مسدودشده‌ای که به این فعالیت وابسته‌اند
    blocked = float(activity.blocked_dependents)
    components.append(("فعالیت‌های مسدود", blocked * w.w_blocked_dependents))

    # 3) ضعف مبحث × وزن اهمیت
    weakness_term = float(activity.topic_weakness) * float(activity.topic_weight)
    components.append(("ضعف مبحث × اهمیت", weakness_term * w.w_topic_weakness))

    # 4) مرور سررسیدشده
    overdue_term = min(30.0, max(0.0, float(activity.review_overdue_days)))
    components.append(("مرور سررسید", overdue_term * w.w_review_overdue))

    # 5) سن بدهی
    age = max(0.0, float(debt_age_days))
    components.append(("سن عقب‌افتادگی", age * w.w_debt_age))

    # 6) هزینهٔ زمان (با جریمه)
    cost = float(activity.effective_minutes) / 60.0
    components.append(("هزینهٔ زمان", -cost * w.w_time_cost))

    factors = topic_factors or TopicFactors()

    # 7) پیش‌نیاز بودن برای مباحث دیگر
    components.append(
        ("پیش‌نیاز بودن", float(factors.prerequisite_share) * w.w_prerequisite)
    )

    # 8) سهم لازم در سؤال‌های نهایی/تشریحی
    components.append(
        ("سهم آزمون نهایی", float(factors.final_exam_share) * w.w_final_exam_share)
    )

    # 9) سرعت فراموشی — مبحث‌های زودفراموش‌شونده جلوتر می‌آیند
    components.append(
        ("سرعت فراموشی", float(factors.forgetting_rate) * w.w_forgetting_rate)
    )

    # 10) نزدیکی مهلت اختصاصی خود مبحث
    if factors.topic_deadline_days is None:
        components.append(("مهلت مبحث", 0.0))
    else:
        closeness = 1.0 / max(0.5, float(factors.topic_deadline_days))
        components.append(("مهلت مبحث", closeness * w.w_topic_deadline))

    # 11) احتمال پیشرفت معنادار در زمان باقی‌مانده
    probability = progress_probability(
        factors.remaining_minutes, factors.available_minutes
    )
    components.append(
        ("احتمال پیشرفت", probability * w.w_progress_probability)
    )

    total = sum(value for _, value in components)
    return PriorityScore(total=total, components=tuple(components))


# ---------------------------------------------------------------------------
# محافظ حذف‌نشدن (بند ۱۴)
# ---------------------------------------------------------------------------


def protect_reason(
    activity: Activity,
    topic_factors: Optional[TopicFactors] = None,
    *,
    settings: Optional[Settings] = None,
) -> str:
    """چرا این فعالیت **نباید** فقط به‌خاطر سخت‌بودن کنار گذاشته شود.

    خروجی رشتهٔ خالی یعنی استثنایی در کار ندارد؛ رشتهٔ پرشده یعنی این
    فعالیت در برنامهٔ روز «محافظ‌شده» است و اگر جا نشود باید دلیلش در
    بازبینی شبانه ثبت شود، نه اینکه بی‌صدا حذف شود.
    """
    factors = topic_factors or TopicFactors()
    w = (settings or Settings()).scheduler
    reasons: list[str] = []
    if factors.prerequisite_share > 0:
        reasons.append("پیش‌نیاز مباحث دیگر است")
    if factors.final_exam_share > 0:
        reasons.append("سهم مشخصی در سؤال‌های نهایی دارد")
    if float(factors.importance) >= 1.0 and float(factors.exam_weakness) > 0.4:
        reasons.append("در آزمون ضعف ثبت‌شده دارد ولی مهم است")
    if activity.deadline_type == DeadlineType.HARD:
        reasons.append("مهلت سخت دارد")
    if not reasons:
        return ""
    return "؛ ".join(reasons) + (
        f" (کف محافظت: {w.hard_topic_floor_ratio:.0%} ظرفیت روز)"
    )


def protected_minutes(
    activities: Sequence[Activity],
    topic_factors_by_id: dict[int, TopicFactors],
    capacity_minutes: int,
    *,
    settings: Optional[Settings] = None,
) -> int:
    """حداقل دقیقه‌ای که باید به مباحث سخت/مهم اختصاص یابد.

    این تابع برنامهٔ روز را وادار نمی‌کند ظرفیت را پرکند؛ فقط **کف** را
    مشخص می‌کند تا اگر تصمیمی به حذف گرفته شد، حداقل این مقدار به این
    دسته اختصاص یابد.
    """
    ratio = (settings or Settings()).scheduler.hard_topic_floor_ratio
    if capacity_minutes <= 0 or not activities:
        return 0
    guarded = [
        a
        for a in activities
        if protect_reason(a, topic_factors_by_id.get(a.topic_id or -1), settings=settings)
    ]
    if not guarded:
        return 0
    floor = int(capacity_minutes * ratio)
    needed = sum(a.effective_minutes for a in guarded)
    return max(0, min(needed, floor))


def drop_order(
    activities: Sequence[Activity],
    scores: dict[int, PriorityScore],
) -> list[Activity]:
    """ترتیب اولویت **کنارگذاشتن** کارها وقتی ظرفیت کم است.

    قاعده: کار کم‌اهمیت و کم‌فوریت اول کنار می‌رود؛ سختی یا ضعف مبحث هرگز
    دلیل کنارگذاشتن نیست.
    """
    return sorted(
        activities,
        key=lambda a: (
            scores.get(a.id or -1, PriorityScore()).total,
            a.effective_minutes,
        ),
    )


# ---------------------------------------------------------------------------
# زمان‌بند
# ---------------------------------------------------------------------------


class Scheduler:
    """زمان‌بند روزانهٔ قاعده‌محور."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()

    # ---- API عمومی ----

    def plan_day(
        self,
        date: _dt.date,
        activities: Sequence[Activity],
        context: SchedulingContext,
        *,
        carried_debt_ages: Optional[dict[int, float]] = None,
    ) -> DayPlan:
        """برنامهٔ یک روز را می‌سازد."""
        capacity = context.capacity_for(date)
        plan = DayPlan(
            date=date,
            capacity_minutes=capacity.capacity_minutes,
            raw_minutes=capacity.raw_minutes,
            effective_minutes=capacity.effective_minutes,
            free_minutes=capacity.free_minutes,
        )
        plan.notes.extend(capacity.notes)
        plan.notes.extend(detect_fixed_conflicts(date, context))

        blocks = _split_blocks(capacity.free, self.settings.capacity.max_block_minutes)
        remaining: list[int] = [b.minutes for b in blocks]
        occupancy: list[list[tuple[int, int]]] = [[] for _ in blocks]

        debt_ages = carried_debt_ages or {}
        today = date

        # 1) مرتب‌سازی: مهلت سخت ابتدا (نزدیک‌ترین مهلت)، سپس بقیه بر اساس امتیاز
        scored: list[tuple[Activity, PriorityScore, tuple[int, int]]] = []
        for activity in activities:
            score = compute_priority(
                activity,
                today=today,
                settings=self.settings,
                debt_age_days=debt_ages.get(activity.id if activity.id is not None else -1, 0.0),
            )
            hard_class = 0 if activity.deadline_type == DeadlineType.HARD else 1
            deadline_key = (
                activity.deadline_at.date().toordinal()
                if activity.deadline_at is not None
                else 10**9
            )
            scored.append((activity, score, (hard_class, deadline_key)))

        scored.sort(key=lambda item: (item[2][0], item[2][1], -item[1].total))

        budget = capacity.capacity_minutes
        placed_minutes = 0

        for activity, score, _key in scored:
            if activity.id is None:
                continue
            if activity.state in {
                ActivityState.DONE,
                ActivityState.EXPIRED,
                ActivityState.DROPPED,
            }:
                continue

            if (
                activity.deadline_type == DeadlineType.HARD
                and activity.deadline_at is not None
                and activity.deadline_at.date() < date
            ):
                plan.unplaced.append(
                    UnplacedActivity(
                        activity_id=activity.id,
                        title=activity.title,
                        minutes=activity.effective_minutes,
                        reason="مهلت سخت این فعالیت گذشته است.",
                        details=(
                            "برای جلوگیری از پنهان‌سازی، فعالیت حذف نشده و در صف تصمیم می‌ماند.",
                        ),
                    )
                )
                continue

            placements, complete = self._place(
                activity,
                score,
                blocks,
                remaining,
                occupancy,
                budget=budget,
                date=date,
                context=context,
            )

            if not placements:
                plan.unplaced.append(
                    UnplacedActivity(
                        activity_id=activity.id,
                        title=activity.title,
                        minutes=activity.effective_minutes,
                        reason=self._unplaced_reason(activity, budget, capacity),
                        details=(
                            f"ظرفیت امروز: {capacity.capacity_minutes} دقیقه",
                            f"زمان لازم این کار: {activity.effective_minutes} دقیقه",
                        ),
                    )
                )
                continue

            for placement in placements:
                plan.placements.append(placement)
                placed_minutes += placement.minutes
                budget -= placement.minutes

            if not complete:
                plan.notes.append(
                    f"«{activity.title}» به‌طور ناقص در برنامهٔ امروز جا گرفت؛ "
                    "باقی‌ماندهٔ آن به روز بعد منتقل می‌شود."
                )

        plan.placements.sort(key=lambda p: (p.start_minute, p.end_minute))
        plan.planned_minutes = placed_minutes
        return plan

    def plan_range(
        self,
        start_date: _dt.date,
        days: int,
        activities: Sequence[Activity],
        context: SchedulingContext,
        *,
        today: Optional[_dt.date] = None,
    ) -> list[DayPlan]:
        """برنامهٔ چندروزه.

        فعالیت‌های جا‌نشده یا ناقص به‌طور خودکار به روز بعد منتقل می‌شوند و
        سن بدهی آن‌ها افزایش می‌یابد (بدون حذف).
        """
        today = today or start_date
        pending: dict[int, Activity] = {
            a.id: a
            for a in activities
            if a.id is not None
            and a.state
            not in {ActivityState.DONE, ActivityState.EXPIRED, ActivityState.DROPPED}
        }
        debt_ages: dict[int, float] = {}
        plans: list[DayPlan] = []

        for offset in range(days):
            date = start_date + _dt.timedelta(days=offset)
            candidates = list(pending.values())
            plan = self.plan_day(date, candidates, context, carried_debt_ages=debt_ages)
            plans.append(plan)

            # زمانِ جا‌داده‌شده از باقی‌مانده کم می‌شود؛ فعالیت ناقص به روز
            # بعد منتقل می‌شود و **هرگز بی‌سروصدا حذف نمی‌شود**.
            placed_minutes: dict[int, int] = {}
            for placement in plan.placements:
                placed_minutes[placement.activity_id] = (
                    placed_minutes.get(placement.activity_id, 0) + placement.minutes
                )

            for activity_id, minutes in placed_minutes.items():
                activity = pending.get(activity_id)
                if activity is None:
                    continue
                activity.remaining_minutes = max(
                    0, activity.remaining_minutes - minutes
                )
                if activity.remaining_minutes == 0:
                    del pending[activity_id]
                    debt_ages.pop(activity_id, None)
                else:
                    debt_ages[activity_id] = debt_ages.get(activity_id, 0.0) + 1.0

            for activity_id in list(pending):
                if activity_id not in placed_minutes:
                    debt_ages[activity_id] = debt_ages.get(activity_id, 0.0) + 1.0

        return plans

    # ---- internals ----

    def _place(
        self,
        activity: Activity,
        score: PriorityScore,
        blocks: Sequence[Interval],
        remaining: list[int],
        occupancy: list[list[tuple[int, int]]],
        *,
        budget: int,
        date: _dt.date,
        context: SchedulingContext,
    ) -> tuple[list[Placement], bool]:
        """تلاش برای جای‌گذاری. خروجی: (جای‌گذاری‌ها، کامل جا شد؟)."""
        assert activity.id is not None
        needed = activity.effective_minutes
        if needed <= 0:
            return [], True

        deadline_cutoff = None
        if activity.deadline_type == DeadlineType.HARD and activity.deadline_at is not None:
            deadline_cutoff = activity.deadline_at.date()

        if activity.is_splittable:
            return self._place_splittable(
                activity,
                score,
                blocks,
                remaining,
                occupancy,
                budget=budget,
                date=date,
                context=context,
                deadline_cutoff=deadline_cutoff,
            )
        return self._place_whole(
            activity,
            score,
            blocks,
            remaining,
            occupancy,
            budget=budget,
            date=date,
            context=context,
            deadline_cutoff=deadline_cutoff,
        )

    # ---- جای‌گذاری کامل (تقسیم‌ناپذیر) ----

    def _place_whole(
        self,
        activity: Activity,
        score: PriorityScore,
        blocks: Sequence[Interval],
        remaining: list[int],
        occupancy: list[list[tuple[int, int]]],
        *,
        budget: int,
        date: _dt.date,
        context: SchedulingContext,
        deadline_cutoff: Optional[_dt.date],
    ) -> tuple[list[Placement], bool]:
        assert activity.id is not None
        needed = activity.effective_minutes

        if needed > activity.max_chunk:
            return [], False
        if needed > budget:
            return [], False

        for index in self._candidate_blocks(blocks, remaining, context, activity):
            block = blocks[index]
            if remaining[index] < needed:
                continue
            start = self._find_free_start(block, occupancy[index], needed)
            if start is None:
                continue
            end = start + needed
            remaining[index] -= needed
            occupancy[index].append((start, end))
            return (
                [
                    Placement(
                        activity_id=activity.id,
                        title=activity.title,
                        date=date,
                        start_minute=start,
                        end_minute=end,
                        minutes=needed,
                        score=score.total,
                        reasons=self._placement_reasons(activity, score),
                        chunk_index=1,
                        chunk_total=1,
                    )
                ],
                True,
            )
        return [], False

    # ---- جای‌گذاری تقسیم‌پذیر ----

    def _place_splittable(
        self,
        activity: Activity,
        score: PriorityScore,
        blocks: Sequence[Interval],
        remaining: list[int],
        occupancy: list[list[tuple[int, int]]],
        *,
        budget: int,
        date: _dt.date,
        context: SchedulingContext,
        deadline_cutoff: Optional[_dt.date],
    ) -> tuple[list[Placement], bool]:
        assert activity.id is not None
        total_needed = activity.effective_minutes

        placed: list[Placement] = []
        left = total_needed
        min_chunk = max(1, min(activity.min_chunk, self.settings.scheduler.split_min_chunk))
        max_chunk = max(min_chunk, activity.max_chunk)
        local_budget = budget

        while left > 0 and local_budget > 0:
            chosen: Optional[tuple[int, int, int]] = None
            for index in self._candidate_blocks(blocks, remaining, context, activity):
                block = blocks[index]
                space = remaining[index]
                if space <= 0:
                    continue
                chunk = min(space, left, max_chunk, local_budget)
                if chunk < min_chunk and chunk < left:
                    # این قطعه خیلی کوتاه است و باقی‌مانده را کامل نمی‌کند.
                    continue
                start = self._find_free_start(block, occupancy[index], chunk)
                if start is None:
                    continue
                chosen = (index, start, chunk)
                break

            if chosen is None:
                break

            index, start, chunk = chosen
            block = blocks[index]
            end = start + chunk
            remaining[index] -= chunk
            occupancy[index].append((start, end))
            placed.append(
                Placement(
                    activity_id=activity.id,
                    title=activity.title,
                    date=date,
                    start_minute=start,
                    end_minute=end,
                    minutes=chunk,
                    score=score.total,
                    reasons=self._placement_reasons(activity, score),
                    chunk_index=len(placed) + 1,
                    chunk_total=0,
                )
            )
            left -= chunk
            local_budget -= chunk

        if not placed:
            return [], False

        complete = left <= 0
        total = len(placed)
        for placement in placed:
            placement.chunk_total = total
        return placed, complete

    # ---- کمک‌کننده‌ها ----

    def _candidate_blocks(
        self,
        blocks: Sequence[Interval],
        remaining: Sequence[int],
        context: SchedulingContext,
        activity: Activity,
    ) -> list[int]:
        """اندیس بلوک‌های مجاز به‌ترتیب اولویت.

        بلوک‌های «پربازده» برای کارهای پرانرژی مقدم‌اند؛ بقیه به ترتیب زمانی.
        """
        prefer_peak = (
            activity.energy_need == EnergyNeed.HIGH and bool(context.peak_hours)
        )
        candidates: list[tuple[int, int, int]] = []
        for index, block in enumerate(blocks):
            if remaining[index] <= 0:
                continue
            peak = 1 if (prefer_peak and _is_peak(block.start, block.end, context.peak_hours)) else 0
            candidates.append((0 if peak else 1, block.start, index))
        candidates.sort()
        return [item[2] for item in candidates]

    @staticmethod
    def _find_free_start(
        block: Interval, occupied: Sequence[tuple[int, int]], needed: int
    ) -> Optional[int]:
        """اولین نقطهٔ آزاد در بلوک که ``needed`` دقیقه جا شود."""
        cursor = block.start
        for start, end in sorted(occupied):
            if end <= cursor:
                continue
            if start - cursor >= needed:
                return cursor
            cursor = max(cursor, end)
        if block.end - cursor >= needed:
            return cursor
        return None

    def _placement_reasons(
        self, activity: Activity, score: PriorityScore
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        if activity.deadline_type == DeadlineType.HARD and activity.deadline_at is not None:
            reasons.append("مهلت سخت دارد و باید رعایت شود.")
        elif activity.deadline_at is not None:
            reasons.append("مهلت نرم دارد.")
        for label, value in score.components:
            if value <= 0:
                continue
            if label == "ضعف مبحث × اهمیت":
                reasons.append("ضعف مبحث با اهمیت بالا در آزمون هدف.")
            elif label == "فعالیت‌های مسدود":
                reasons.append("فعالیت‌های دیگری به این کار وابسته‌اند.")
            elif label == "مرور سررسید":
                reasons.append("مرور این مبحث سررسید شده بود.")
            elif label == "سن عقب‌افتادگی":
                reasons.append("این کار مدتی از موعد گذشته است.")
        if not reasons:
            reasons.append("در اولویت عادی صف کارها قرار دارد.")
        return tuple(dict.fromkeys(reasons))

    def _unplaced_reason(
        self,
        activity: Activity,
        budget: int,
        capacity: CapacityBreakdown,
    ) -> str:
        if budget <= 0:
            return "ظرفیت امروز پر شده است."
        if not activity.is_splittable and activity.effective_minutes > activity.max_chunk:
            return "فعالیت تقسیم‌ناپذیر است و از حداکثر اندازهٔ بلوک بزرگ‌تر است."
        if not activity.is_splittable:
            return "بلوک پیوستهٔ کافی برای این فعالیت تقسیم‌ناپذیر وجود ندارد."
        if activity.effective_minutes > budget:
            return "زمان باقی‌ماندهٔ امروز برای این کار کافی نیست."
        return "در بلوک‌های باقی‌مانده جا نشد."


# ---------------------------------------------------------------------------
# تشخیص تعارض رویدادهای ثابت
# ---------------------------------------------------------------------------


def detect_fixed_conflicts(date: _dt.date, context: SchedulingContext) -> list[str]:
    """هم‌پوشانی رویدادهای ثابت یک روز را گزارش می‌کند.

    مثال واقعی: یکشنبه کلاس شیمی ۱۵:۰۰–۱۹:۰۰ با کلاس دینی ۱۵:۱۵–۲۰:۴۵.
    """
    weekday = weekday_index(date)
    events = sorted(
        (e for e in context.fixed_events if e.weekday == weekday),
        key=lambda e: e.start_minute,
    )
    messages: list[str] = []
    for index in range(len(events) - 1):
        first, second = events[index], events[index + 1]
        if second.start_minute < first.end_minute:
            messages.append(
                f"تعارض تقویمی در {weekday_name(date)}: «{first.title}» "
                f"({_clock(first.start_minute)}–{_clock(first.end_minute)}) با "
                f"«{second.title}» "
                f"({_clock(second.start_minute)}–{_clock(second.end_minute)}) هم‌پوشانی دارد."
            )
    return messages


def _clock(minute: int) -> str:
    return f"{minute // 60:02d}:{minute % 60:02d}"
