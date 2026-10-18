"""توزیع بار سه‌مسیره: مطلب جدید + جبران عقب‌افتادگی + تثبیت، هم‌زمان.

خواستهٔ اصلی محصول: «مطالب افتاده قبل از آزمون تکمیل شود و هم‌زمان مطالب
جدید تزریق شود». این موتور ظرفیت واقعی روز را بین سه مسیر تقسیم می‌کند:

1. **تثبیت** — مرورهای سررسید و جبران بدهی نردبان تثبیت. سهم کف دارد؛
   هرگز صفر نمی‌شود چون «بهمن مرور» یعنی فراموشی همان مبحثی که قبلاً
   یاد گرفته شده (اثر فاصله/بازیابی — سپدیا ۲۰۰۶؛ روئیگر و کارپیک ۲۰۰۶).
2. **جبران** — کارهای عقب‌افتادهٔ قدیمی (کلاس/تمرین انجام‌نشده). سقف
   روزانه دارد تا برنامه با شوک جبران از بین نرود.
3. **مطلب جدید** — پیشروی در دروس؛ سهم کف دارد تا نزدیک آزمون،
   پوشش کامل مطالب از بین نرود.

همهٔ نسبت‌ها فرضیهٔ محصول [H] و در ``StreamSettings`` قابل تنظیم‌اند.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Optional, Sequence

from .config import Settings


@dataclass
class StreamAllocation:
    """تقسیم ظرفیت یک روز بین سه مسیر."""

    date: Optional[_dt.date] = None
    capacity_minutes: int = 0
    new_minutes: int = 0
    catchup_minutes: int = 0
    consolidation_minutes: int = 0
    reserve_minutes: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def total_minutes(self) -> int:
        return self.new_minutes + self.catchup_minutes + self.consolidation_minutes

    def as_dict(self) -> dict[str, int]:
        return {
            "new": self.new_minutes,
            "catchup": self.catchup_minutes,
            "consolidation": self.consolidation_minutes,
            "reserve": self.reserve_minutes,
        }


@dataclass
class FeasibilityVerdict:
    """حکم امکان‌سنجی: آیا کارِ باقی‌مانده تا آزمون جا می‌شود؟"""

    feasible: bool
    level: str = "ok"  # ok | tight | infeasible
    required_minutes: int = 0
    available_minutes: int = 0
    deficit_minutes: int = 0
    required_daily_minutes: float = 0.0
    available_daily_minutes: float = 0.0
    days_left: Optional[int] = None
    notes: list[str] = field(default_factory=list)
    options: list[str] = field(default_factory=list)

    @property
    def ratio(self) -> float:
        """نسبت کار لازم به کار ممکن؛ >۱ یعنی جا نمی‌شود."""
        if self.available_minutes <= 0:
            return 0.0 if self.required_minutes <= 0 else 99.0
        return self.required_minutes / self.available_minutes


def allocate_streams(
    *,
    capacity_minutes: int,
    review_load_minutes: int = 0,
    catchup_debt_minutes: int = 0,
    new_load_minutes: int = 0,
    days_to_exam: Optional[int] = None,
    date: Optional[_dt.date] = None,
    settings: Optional[Settings] = None,
) -> StreamAllocation:
    """ظرفیت روز را بین سه مسیر توزیع می‌کند.

    الگو [H]:
      * تثبیت = بیشینه(بار مرور سررسید، کفِ ظرفیت) و حداکثر سقفِ ظرفیت؛
        اگر بار مرور از «آستانهٔ هجوم» بیشتر شد، تا سقف بالا می‌رود.
      * جبران = کمینه(بدهی ÷ روزهای باقی‌مانده، سقف جبران).
      * جدید = باقی‌مانده، با کفِ محافظتی تا وقتی آزمون دور است.
      * حاشیهٔ ایمنی به‌عنوان ذخیرهٔ بدون‌برنامه حفظ می‌شود.
    """
    settings = settings or Settings()
    s = settings.streams
    capacity = max(0, int(capacity_minutes))
    allocation = StreamAllocation(date=date, capacity_minutes=capacity)

    if capacity <= 0:
        allocation.notes.append("ظرفیت امروز صفر است؛ هیچ مسیری برنامه‌ریزی نمی‌شود.")
        return allocation

    consolidation = review_load_minutes
    floor = int(capacity * s.consolidation_floor_ratio)
    cap = int(capacity * s.consolidation_cap_ratio)
    surge = int(capacity * s.consolidation_surge_ratio)
    if consolidation < floor:
        allocation.notes.append(
            f"سهم تثبیت به کف {floor} دقیقه افزایش یافت تا ماندگاری حفظ شود."
        )
        consolidation = floor
    if consolidation > surge:
        consolidation = min(cap, consolidation)
        if consolidation >= cap:
            allocation.notes.append(
                "بار مرور از آستانهٔ هجوم گذشته؛ تثبیت تا سقف ظرفیت بالا رفت "
                "و بخشی از بار به روزهای بعد پخش می‌شود."
            )
    else:
        consolidation = min(consolidation, cap)
    allocation.consolidation_minutes = max(0, consolidation)

    remaining = capacity - allocation.consolidation_minutes
    catchup_cap = int(capacity * s.catchup_cap_ratio)
    catchup = 0
    if catchup_debt_minutes > 0 and remaining > 0:
        if days_to_exam is not None and days_to_exam > 0:
            catchup = min(catchup_debt_minutes // max(1, days_to_exam), catchup_cap)
        else:
            catchup = min(catchup_cap, catchup_debt_minutes)
        catchup = min(catchup, remaining)
        if catchup < catchup_debt_minutes:
            allocation.notes.append(
                f"بدهی جبرانی {catchup_debt_minutes} دقیقه است؛ امروز {catchup} دقیقه "
                "در سقف روزانهٔ جبران جا شد و بقیه در روزهای بعد پله‌پله پیش می‌رود."
            )
    allocation.catchup_minutes = max(0, catchup)

    remaining = capacity - allocation.consolidation_minutes - allocation.catchup_minutes
    new_minutes = min(max(0, new_load_minutes), remaining)
    # کف محافظتی مطلب جدید تا پوشش کامل مطالب حفظ شود (اگر آزمون نزدیک نباشد).
    new_floor = int(capacity * s.new_floor_ratio)
    if new_minutes < new_floor and new_load_minutes > new_minutes:
        shortfall = new_floor - new_minutes
        new_minutes = min(new_load_minutes, new_minutes + shortfall)
    allocation.new_minutes = max(0, min(new_minutes, remaining))

    allocation.reserve_minutes = max(
        0,
        capacity
        - allocation.consolidation_minutes
        - allocation.catchup_minutes
        - allocation.new_minutes,
    )
    if allocation.reserve_minutes > 0:
        allocation.notes.append(
            f"{allocation.reserve_minutes} دقیقه به‌عنوان حاشیهٔ آزاد بی‌برنامه ماند."
        )
    return allocation


def assess_feasibility(
    *,
    new_load_minutes: int,
    catchup_debt_minutes: int,
    consolidation_load_minutes: int,
    daily_capacity_minutes: int,
    days_to_exam: Optional[int],
    settings: Optional[Settings] = None,
) -> FeasibilityVerdict:
    """آیا همهٔ کارهای لازم تا آزمون جا می‌شود؟

    ساده و محافظه‌کارانه: کار لازم = مطلب جدید + بدهی جبران + بار تثبیت
    (بار تثبیت به‌صورت میانگین روزانهٔ باقی‌مانده تخمین زده می‌شود).
    اگر روزهای باقی‌مانده نامعلوم باشد، verdict خنثی است.
    """
    verdict = FeasibilityVerdict(
        feasible=True,
        required_minutes=int(new_load_minutes + catchup_debt_minutes),
        available_minutes=0,
        days_left=days_to_exam,
    )
    if days_to_exam is None or days_to_exam <= 0:
        verdict.level = "unknown"
        verdict.notes.append(
            "تاریخ آزمون نامشخص است؛ امکان‌سنجی عددی انجام نمی‌شود و برنامه بر "
            "پایهٔ ظرفیت روزانه پیش می‌رود."
        )
        return verdict

    days = days_to_exam
    available = int(daily_capacity_minutes * days)
    consolidation_daily = int(consolidation_load_minutes / max(1, days))
    required = int(new_load_minutes + catchup_debt_minutes + consolidation_daily * days)
    verdict.required_minutes = required
    verdict.available_minutes = available
    verdict.deficit_minutes = max(0, required - available)
    verdict.required_daily_minutes = required / days
    verdict.available_daily_minutes = daily_capacity_minutes

    if verdict.deficit_minutes <= 0:
        verdict.level = "ok"
        verdict.feasible = True
        verdict.notes.append(
            f"کار لازم روزانه {verdict.required_daily_minutes:.0f} دقیقه در مقابل "
            f"ظرفیت {daily_capacity_minutes} دقیقه؛ برنامه در محدودهٔ واقع‌بینانه است."
        )
        return verdict

    verdict.feasible = False
    if verdict.ratio <= 1.15:
        verdict.level = "tight"
    else:
        verdict.level = "infeasible"
    verdict.notes.append(
        f"کمبود {verdict.deficit_minutes} دقیقه ({verdict.ratio:.0%} کار لازم در "
        "مقابل ظرفیت باقی‌مانده). بدون تصمیم، بخشی از مطالب تثبیت‌نشده می‌ماند."
    )
    verdict.options = _feasibility_options(verdict, settings)
    return verdict


def _feasibility_options(
    verdict: FeasibilityVerdict, settings: Optional[Settings]
) -> list[str]:
    """گزینه‌های تصمیم مثل یک مشاور واقعی — هیچ‌کدام خودکار اعمال نمی‌شوند."""
    deficit_hours = verdict.deficit_minutes / 60.0
    options = [
        f"کاهش دامنه: حداقل {deficit_hours:.1f} ساعت از مبحث‌های کم‌ضریب‌تر را "
        "به فهرست «خارج از بودجه» ببرید (با تأیید خودتان).",
        "افزایش ظرفیت واقعی: خواب/بیداری، انرژی و تمرکز را بازبینی کنید؛ "
        "افزایش بی‌آنکه خواب کاهش یابد، خودش ظرفیت را کم می‌کند.",
        "جایگزینی روش: برای بخشی از مبحث‌ها به‌جای مطالعهٔ مجدد، آزمون/بازیابی "
        "فعال بگذارید؛ همان زمان، ماندگاری بیشتری می‌سازد.",
        "اولویت‌بندی ضرایب: وقت بیشتر به دروس با ضرریب بالا؛ دروس ضعیف‌تر را "
        "حداقلی و تثبیت‌محور ادامه دهید.",
    ]
    return options


@dataclass
class CatchupQuota:
    """سهم جبران یک کار عقب‌افتاده در یک روز."""

    day_offset: int
    date: _dt.date
    minutes: int
    activity_id: int
    title: str


def catchup_plan(
    *,
    debts: Sequence[tuple[int, str, int]],
    start_date: _dt.date,
    days: int,
    daily_budget_minutes: int,
    settings: Optional[Settings] = None,
) -> list[CatchupQuota]:
    """بدهی‌ها را پله‌پله روی روزها پخش می‌کند.

    ``debts``: جفت‌های (activity_id, title, remaining_minutes) مرتب‌شده بر
    اساس اولویت (قدیمی/مهم‌تر اول). هر روز تا ``daily_budget_minutes`` پر
    می‌شود؛ هیچ کاری بی‌صدا حذف نمی‌شود و باقی‌مانده صریح گزارش می‌شود.
    """
    settings = settings or Settings()
    max_chunk = max(1, settings.capacity.max_block_minutes)
    queue: list[list] = [[aid, title, minutes] for aid, title, minutes in debts]
    plan: list[CatchupQuota] = []
    for offset in range(max(0, days)):
        date = start_date + _dt.timedelta(days=offset)
        budget = max(0, int(daily_budget_minutes))
        index = 0
        while budget > 0 and index < len(queue):
            item = queue[index]
            take = min(item[2], budget, max_chunk)
            if take <= 0:
                index += 1
                continue
            plan.append(
                CatchupQuota(
                    day_offset=offset,
                    date=date,
                    minutes=take,
                    activity_id=item[0],
                    title=item[1],
                )
            )
            item[2] -= take
            budget -= take
            if item[2] <= 0:
                queue.pop(index)
                continue
            index += 1
        if not queue:
            break
    return plan


__all__ = [
    "CatchupQuota",
    "FeasibilityVerdict",
    "StreamAllocation",
    "allocate_streams",
    "assess_feasibility",
    "catchup_plan",
]
