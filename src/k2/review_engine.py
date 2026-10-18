"""موتور مرور تطبیقی (سند تحقیق ۱، بخش ۳).

نکات کلیدی که در این پیاده‌سازی رعایت شده‌اند:
  * الگوی ثابت «۱-۳-۷-۱۴-۳۰» به‌عنوان قانون علمی استفاده **نمی‌شود**.
  * فاصلهٔ بعدی از عملکرد، دشواری، زمان و فاصله تا آزمون محاسبه می‌شود.
  * سقف فاصله وابسته به روزهای باقی‌مانده تا آزمون است (اصل ۳ سند ۱).
  * سقف روزانهٔ مرور از ظرفیت روز مشتق می‌شود تا «بهمن مرور» رخ ندهد.
  * آیتم‌های پرتکراراً فراموش‌شده (leech) به تغییر روش تبدیل می‌شوند، نه تکرار بیشتر.
  * مدل حافظهٔ DSR (پایداری/بازیابی‌پذیری) روی موعد بعدی سوار می‌شود
    (سند تحقیق ۵): مرور نزدیکِ مرز فراموشی، رشد پایداری بیشتری می‌دهد.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Optional, Sequence

from . import consolidation as _consolidation
from .config import Settings
from .domain.enums import ReviewState
from .domain.models import ReviewItem

#: نمرهٔ عملکرد g (۰ تا ۴) — سند تحقیق ۱، بخش ۳.۳.
GRADE_LABELS: dict[int, str] = {
    0: "غلط و حتی با دیدن پاسخ مفهوم را نمی‌فهمد",
    1: "غلط، اما با دیدن پاسخ یادش آمد",
    2: "درست ولی کند یا با اطمینان پایین/حدسی",
    3: "درست، با زمان و اطمینان عادی",
    4: "درست، سریع، با اطمینان بالا",
}


@dataclass
class ReviewUpdate:
    """نتیجهٔ به‌روزرسانی یک آیتم مرور."""

    item: ReviewItem
    old_interval: float
    new_interval: float
    old_due: Optional[_dt.date]
    new_due: Optional[_dt.date]
    state_changed: bool
    notes: tuple[str, ...] = ()

    @property
    def interval_delta(self) -> float:
        return self.new_interval - self.old_interval


def grade_from_result(
    *,
    correct: bool,
    confidence: int,
    time_ratio: Optional[float] = None,
) -> int:
    """تبدیل نتیجهٔ مرور به نمرهٔ g.

    Args:
        correct: آیا پاسخ درست بود؟
        confidence: اطمینان خودگزارشی ۱..۳.
        time_ratio: نسبت زمان پاسخ به زمان هدف (اختیاری).
    """
    if not correct:
        # g=0 (نفهمیدن) در UI جداگانه گرفته می‌شود؛ اینجا پیش‌فرض g=1 است.
        return 1
    if time_ratio is not None and time_ratio > 1.5:
        return 2
    if confidence <= 1:
        return 2
    if time_ratio is not None and time_ratio <= 0.8 and confidence >= 3:
        return 4
    return 3


def apply_review(
    item: ReviewItem,
    grade: int,
    *,
    today: _dt.date,
    exam_date: Optional[_dt.date] = None,
    settings: Optional[Settings] = None,
    confidence: int = 2,
    time_ratio: Optional[float] = None,
) -> ReviewUpdate:
    """یک مرور را ثبت و فاصلهٔ بعدی را محاسبه می‌کند."""
    settings = settings or Settings()
    review = settings.review

    old_interval = item.interval_days
    old_due = item.due_date
    old_state = item.state
    notes: list[str] = []

    if grade < 0 or grade > 4:
        raise ValueError("نمرهٔ عملکرد باید بین ۰ تا ۴ باشد.")

    if grade <= 1:
        item.lapses += 1
        item.interval_days = 1.0
        item.ease = max(review.ease_min, item.ease - review.ease_delta_hard)
        item.state = ReviewState.RELEARN
        notes.append("پاسخ نادرست؛ فاصله به ۱ روز بازگشت و آیتم به وضعیت «یادگیری مجدد» رفت.")
        if item.lapses >= review.leech_lapse_threshold:
            item.state = ReviewState.LEECH
            notes.append(
                "تعداد فراموشی‌ها به آستانهٔ «تکراری» رسید؛ تکرار بیشتر کمکی نمی‌کند و باید روش تغییر کند."
            )
        item.success_streak = 0
    elif grade == 2:
        item.interval_days = max(item.interval_days + 1.0, item.interval_days * 1.2)
        item.ease = max(review.ease_min, item.ease - review.ease_delta_guessed)
        item.state = ReviewState.LEARNING if item.interval_days < 3 else ReviewState.REVIEW
        item.success_streak = 0
        notes.append("پاسخ درست ولی کند یا کم‌اطمینان؛ فاصله فقط کمی افزایش یافت.")
    else:
        factor = item.ease * (1.3 if grade == 4 else 1.0)
        item.interval_days = max(1.0, item.interval_days * factor)
        if grade == 4:
            item.ease = min(review.ease_max, item.ease + review.ease_delta_success)
        item.success_streak += 1
        item.state = ReviewState.REVIEW
        if grade == 3:
            notes.append("پاسخ درست با زمان و اطمینان عادی.")

    # تعدیل سختی: مطلب سخت‌تر ⇒ فاصلهٔ کوتاه‌تر
    difficulty_factor = 1.15 - 0.05 * max(1, min(5, item.difficulty))
    item.interval_days = max(0.5, item.interval_days * difficulty_factor)
    # گردکردن برای جلوگیری از خطای ممیز شناور
    item.interval_days = round(item.interval_days, 4)

    # سقف وابسته به آزمون (اصل ۳ سند ۱)
    if exam_date is not None:
        days_left = (exam_date - today).days
        if days_left <= 0:
            item.interval_days = min(item.interval_days, 1.0)
            notes.append("روز آزمون گذشته یا امروز است؛ فاصلهٔ مرور به ۱ روز محدود شد.")
        else:
            cap = review.exam_cap_ratio * days_left
            if item.interval_days > cap:
                item.interval_days = max(0.5, cap)
                notes.append(
                    f"فاصلهٔ مرور به سقف وابسته به آزمون ({review.exam_cap_ratio:.0%} "
                    f"از {days_left} روز باقی‌مانده) محدود شد."
                )
            # حالت نگهداری: مرورهای پیاپی موفق با فاصلهٔ حداکثری
            if (
                item.success_streak >= review.maintenance_streak
                and item.interval_days >= cap
            ):
                item.state = ReviewState.MAINTENANCE
                notes.append(
                    "آیتم به وضعیت «نگهداری» رفت؛ فقط در آزمون‌های ترکیبی ظاهر می‌شود."
                )

    # سقف بیشینهٔ فاصله (پیش از محاسبهٔ موعد)
    item.interval_days = min(item.interval_days, float(review.max_interval_days))

    item.last_review = today
    item.last_grade = grade
    item.last_time_ratio = time_ratio
    item.due_date = today + _dt.timedelta(days=int(round(item.interval_days)))

    # لایهٔ مدل حافظهٔ DSR: پایداری و موعد بر پایهٔ هدف بازیابی (سند تحقیق ۵).
    _consolidation.apply_review_to_memory(
        item,
        grade=grade,
        today=today,
        exam_date=exam_date,
        settings=settings,
    )
    item.due_date = today + _dt.timedelta(days=int(round(item.interval_days)))

    return ReviewUpdate(
        item=item,
        old_interval=old_interval,
        new_interval=item.interval_days,
        old_due=old_due,
        new_due=item.due_date,
        state_changed=old_state != item.state,
        notes=tuple(notes),
    )


def create_review_item(
    *,
    label: str,
    subject_id: Optional[int] = None,
    topic_id: Optional[int] = None,
    item_type: str = "concept",
    difficulty: float = 3.0,
    today: Optional[_dt.date] = None,
    settings: Optional[Settings] = None,
) -> ReviewItem:
    """ساخت آیتم مرور تازه با فاصلهٔ اولیهٔ حداکثر ۲۴ ساعت."""
    settings = settings or Settings()
    today = today or _dt.date.today()
    return ReviewItem(
        label=label,
        subject_id=subject_id,
        topic_id=topic_id,
        item_type=item_type,
        difficulty=float(difficulty),
        ease=settings.review.ease_initial,
        interval_days=1.0,
        state=ReviewState.NEW,
        due_date=today + _dt.timedelta(days=1),
        created_at=_dt.datetime.combine(today, _dt.time.min),
        stability_days=0.0,
        retrievability=1.0,
    )


def stability_from_interval(item: ReviewItem) -> float:
    """برآورد پایداری برای رکوردهای قدیمی از فاصلهٔ فعلی (مهاجرت داده).

    با هدف بازیابی پیش‌فرض ۹۰٪: S = t / (۹۰٪^-۲ − ۱) × ۱۹/۸۱ ≈ t × ۰٫۴۷.
    """
    if item.stability_days and item.stability_days > 0:
        return item.stability_days
    interval = max(0.5, float(item.interval_days or 0.0))
    return round(interval * _consolidation.FORGETTING_FACTOR / 0.2346, 4)


def due_items(
    items: Sequence[ReviewItem], today: _dt.date, *, include_maintenance: bool = False
) -> list[ReviewItem]:
    """آیتم‌های سررسیدشده تا امروز."""
    result = [
        item
        for item in items
        if item.due_date is not None
        and item.due_date <= today
        and item.state != ReviewState.LEECH
        and (include_maintenance or item.state != ReviewState.MAINTENANCE)
    ]
    result.sort(key=lambda item: (item.due_date or today, -(item.lapses)))
    return result


def review_budget_minutes(capacity_minutes: int, settings: Optional[Settings] = None) -> int:
    """سقف زمان روزانهٔ مرور بر پایهٔ ظرفیت روز."""
    settings = settings or Settings()
    return int(capacity_minutes * settings.review.daily_review_cap_ratio)


def needs_retention_check(
    item: ReviewItem, today: _dt.date, settings: Optional[Settings] = None
) -> bool:
    """آیا بدهی مرور باید به‌جای مرور فوری، با آزمون نمونه‌ای سنجیده شود؟"""
    settings = settings or Settings()
    if item.due_date is None or item.interval_days <= 0:
        return False
    overdue = (today - item.due_date).days
    return overdue > settings.review.overdue_compression_factor * item.interval_days


def retention_check_sample(
    items: Sequence[ReviewItem], today: _dt.date, settings: Optional[Settings] = None
) -> list[ReviewItem]:
    """نمونهٔ کوچکی از آیتم‌های عقب‌افتاده برای سنجش ماندگاری."""
    settings = settings or Settings()
    candidates = [item for item in items if needs_retention_check(item, today, settings)]
    if not candidates:
        return []
    # نمونه‌گیری قطعی (بدون تصادف) تا نتیجهٔ تست‌ها بازتولیدپذیر باشد.
    limit = max(1, len(candidates) // 4)
    return candidates[:limit]


def compress_review_backlog(
    items: Sequence[ReviewItem],
    today: _dt.date,
    settings: Optional[Settings] = None,
) -> dict[int, str]:
    """سطح‌بندی صف مرور: «حیاتی» / «مهم» / «اختیاری».

    برای جلوگیری از «بهمن مرور»، صف به سه سطح تقسیم و طی چند روز تخلیه می‌شود.
    """
    settings = settings or Settings()
    result: dict[int, str] = {}
    overdue = sorted(
        (item for item in items if item.due_date and item.due_date <= today),
        key=lambda item: (-item.lapses, item.due_date or today),
    )
    total = len(overdue)
    for index, item in enumerate(overdue):
        ratio = index / total if total else 0
        if item.lapses >= 2 or ratio < 0.33:
            result[item.id or -1] = "حیاتی"
        elif ratio < 0.67:
            result[item.id or -1] = "مهم"
        else:
            result[item.id or -1] = "اختیاری"
    return result


def retention_signal(
    recent_grades: Sequence[int], *, threshold: float = 0.70
) -> bool:
    """آیا افت ماندگاری رخ داده است؟

    نمرهٔ g به درصد تبدیل می‌شود: g/4. اگر میانگین از آستانه پایین‌تر باشد،
    یعنی مرورهای اخیر به اندازه کافی موفق نبوده‌اند (سند ۱، بخش ۳.۷).
    """
    if not recent_grades:
        return False
    average = sum(recent_grades) / (4.0 * len(recent_grades))
    return average < threshold
