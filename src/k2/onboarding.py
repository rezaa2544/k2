"""راه‌اندازی مرحله‌ای و مدیریت داده‌های ورودی کاربر."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional, Sequence

from .domain.models import FixedEvent

#: نام روزها به ترتیب شنبه‌محور برای نگاشت.
DAY_ORDER = ("شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه")


def _minutes(hour: int, minute: int = 0) -> int:
    return hour * 60 + minute


def _parse_clock(text: str) -> int:
    hour, _, minute = text.partition(":")
    return _minutes(int(hour), int(minute or 0))


@dataclass
class ScheduleConflict:
    """تعارض بین دو رویداد ثابت."""

    weekday: int
    first_title: str
    second_title: str
    first_range: str
    second_range: str
    question: str = ""
    blocking: bool = True

    @property
    def day_name(self) -> str:
        return DAY_ORDER[self.weekday]

    def describe(self) -> str:
        return (
            f"تعارض در {self.day_name}: «{self.first_title}» ({self.first_range}) با "
            f"«{self.second_title}» ({self.second_range}) هم‌پوشانی دارد."
        )


def detect_event_conflicts(events: Sequence[FixedEvent]) -> list[ScheduleConflict]:
    """تعارض‌های واقعی بین رویدادهای ذخیره‌شده را می‌یابد.

    رویداد ضبط‌شده غیرهم‌زمان است و مانع برنامه‌ریزی در همان بازه نمی‌شود؛
    اما دو تعهد هم‌زمانِ زنده/ثابت به‌عنوان تعارض مسدودکننده گزارش می‌شوند.
    همهٔ جفت‌ها بررسی می‌شوند تا تعارض‌های تودرتو هم از قلم نیفتند.
    """
    result: list[ScheduleConflict] = []
    by_day: dict[int, list[FixedEvent]] = {}
    for event in events:
        if event.end_minute > event.start_minute:
            by_day.setdefault(event.weekday, []).append(event)
    for weekday, day_events in by_day.items():
        ordered = sorted(day_events, key=lambda item: (item.start_minute, item.end_minute))
        for index, first in enumerate(ordered):
            for second in ordered[index + 1:]:
                if second.start_minute >= first.end_minute:
                    break
                if first.is_recorded or second.is_recorded:
                    continue
                result.append(
                    ScheduleConflict(
                        weekday=weekday,
                        first_title=first.title,
                        second_title=second.title,
                        first_range=(
                            f"{first.start_minute // 60:02d}:{first.start_minute % 60:02d}–"
                            f"{first.end_minute // 60:02d}:{first.end_minute % 60:02d}"
                        ),
                        second_range=(
                            f"{second.start_minute // 60:02d}:{second.start_minute % 60:02d}–"
                            f"{second.end_minute // 60:02d}:{second.end_minute % 60:02d}"
                        ),
                        question=(
                            "یکی از رویدادها را ضبط‌شده/غیرهم‌زمان علامت بزنید یا زمان را اصلاح کنید."
                        ),
                        blocking=True,
                    )
                )
    return result


# ---------------------------------------------------------------------------
# مراحل راه‌اندازی
# ---------------------------------------------------------------------------


@dataclass
class OnboardingStep:
    """یک مرحله از مصاحبهٔ راه‌اندازی."""

    key: str
    title: str
    description: str
    kind: str  # text | choice | number | date | schedule | confirm
    options: tuple[str, ...] = ()
    required: bool = False
    #: پرسش‌های باز که باید از کاربر پرسیده شود.
    blocking_question: str = ""


ONBOARDING_STEPS: tuple[OnboardingStep, ...] = (
    OnboardingStep(
        key="student_name", title="نام داوطلب",
        description="نامی که در گزارش‌ها استفاده می‌شود.", kind="text",
    ),
    OnboardingStep(
        key="exam_group", title="رشتهٔ آزمایشی",
        description="یکی از سه گروه اصلی را انتخاب کنید؛ انتخاب‌های قبلی با تغییر رشته حذف نمی‌شوند.",
        kind="choice", options=("علوم تجربی", "علوم ریاضی و فنی", "علوم انسانی"), required=True,
    ),
    OnboardingStep(
        key="exam_year", title="سال آزمون هدف",
        description="مواد و ضرایب هر سال جدا هستند؛ دادهٔ سال قبل خودکار به سال دیگر منتقل نمی‌شود.",
        kind="choice", options=("۱۴۰۵", "۱۴۰۶", "سال دیگر / هنوز مشخص نیست"), required=True,
    ),
    OnboardingStep(
        key="exam_name", title="نام آزمون هدف",
        description="مثلاً «کنکور سراسری».", kind="text", required=True,
    ),
    OnboardingStep(
        key="exam_date", title="تاریخ آزمون هدف",
        description="تاریخ شمسی اختیاری است؛ اگر هنوز اعلام نشده، خالی بگذارید.", kind="date",
    ),
    OnboardingStep(
        key="exam_date_status", title="وضعیت تاریخ آزمون",
        description="رسمی، تخمینی یا نامشخص.", kind="choice",
        options=("رسمی (منبع ثبت‌شده)", "تخمینی", "نامشخص"), required=True,
    ),
    OnboardingStep(
        key="exam_source", title="منبع تاریخ و مقررات",
        description="عنوان یا پیوند اطلاعیه را ثبت کنید؛ منبع ضریب درس جداگانه در کاتالوگ نمایش داده می‌شود.", kind="text",
    ),
    OnboardingStep(
        key="subjects", title="درس‌های آزمون و سوابق",
        description="مواد آزمون تخصصی و درس‌های سوابق تحصیلی جدا برچسب می‌خورند. انتخاب همه یا گزینشی ممکن است.",
        kind="multiselect", required=True,
    ),
    OnboardingStep(
        key="books", title="کتاب‌های هر درس",
        description="کاتالوگ کتاب‌ها با پایه، کد و پیوند رسمی کتاب درسی پیش‌پر می‌شود؛ انتخاب/لغو انتخاب شما ذخیره می‌شود.",
        kind="books",
    ),
    OnboardingStep(
        key="class_attendance", title="کلاس کنکوری مؤسسه",
        description="آیا کلاس زنده/حضوری یا آنلاینِ مؤسسه دارید؟ اگر بله، درس، روز و زمان هر جلسه را ثبت کنید.",
        kind="choice", options=("بله", "خیر"), required=True,
    ),
    OnboardingStep(
        key="classes", title="زمان کلاس‌های مؤسسه",
        description="هر جلسه را با درس، روز هفته و ساعت شروع/پایان اضافه کنید. جلسهٔ ضبط‌شده را هم می‌توانید جداگانه علامت بزنید.",
        kind="events",
    ),
    OnboardingStep(
        key="weekly_schedule", title="آزمون‌ها و تعهدهای ثابت",
        description="آزمون آزمایشی، رفت‌وآمد و دیگر تعهدهای ثابت هفتگی را ثبت کنید؛ هیچ رویدادی از پیش ساخته نشده است.",
        kind="events",
    ),
    OnboardingStep(
        key="sleep_time", title="ساعت خواب و بیداری",
        description="بازهٔ معمول خواب را وارد کنید؛ نمونهٔ قالب: ۲۳:۰۰ تا ۰۶:۰۰. این مقدار فقط زمانی ذخیره می‌شود که خودتان وارد کنید.",
        kind="text", required=True,
    ),
    OnboardingStep(
        key="min_sleep", title="حداقل خواب مورد نظر",
        description="چند دقیقه خواب کمینه می‌خواهی؟ خواب هرگز قربانی جبران عقب‌افتادگی نمی‌شود؛ اگر ظرفیت کم بیاید، برنامه کوتاه می‌شود نه خواب.",
        kind="choice",
        options=("۳۰۰ (۵ ساعت)", "۳۶۰ (۶ ساعت)", "۴۲۰ (۷ ساعت)",
                 "۴۸۰ (۸ ساعت)", "۵۴۰ (۹ ساعت)"),
    ),
    OnboardingStep(
        key="routines", title="خواب، غذا، استراحت و کارهای ثابت",
        description="وعده‌ها، استراحت، بهداشت و هر کار دلخواه را با بازه و روزهای تکرار اضافه کنید. خواب شب را در مرحلهٔ قبل وارد کنید.",
        kind="routines",
    ),
    OnboardingStep(
        key="comprehensive_exam_cycle", title="چرخهٔ آزمون جامع",
        description=(
            "آزمون جامع و تحلیل آن دو کار مستقل‌اند. روز هفته، بازهٔ ساعت و "
            "تناوب را خودت تعریف کن — مثلاً هر دو هفته یک بار، پنجشنبه، "
            "۰۸:۰۰ تا ۱۲:۰۰. هیچ ساعتی از پیش پر نمی‌شود؛ اگر حالا نمی‌خواهی "
            "ثبت کنی، «هنوز مشخص نیست» را انتخاب کن."
        ),
        kind="exam_cycle",
    ),
    OnboardingStep(
        key="comprehensive_exam_date", title="تاریخ ۳۰ مهر به کدام سال است؟",
        description="اگر تاریخ «۳۰ مهر» را داری، سال آن را از تقویم خودت تأیید کن. خالی بگذاشتن یعنی «نامشخص»؛ سال حدس زده نمی‌شود.",
        kind="text",
    ),
    OnboardingStep(
        key="typical_durations", title="طول معمول هر نوع کار",
        description="به‌ترتیب تست زمان‌دار، تحلیل تست، تثبیت و تکلیف را با دقیقه وارد کن؛ مثلاً ۵۰، ۳۵، ۲۵، ۴۰. این اعداد فرضیهٔ محافظه‌کارانه‌اند و بعد از نمونه‌های واقعی‌ات کالیبره می‌شوند.",
        kind="text",
    ),
    OnboardingStep(
        key="priority_mode", title="روش اولویت‌بندی خودکار",
        description="ضریب رسمی آزمون با وزن شخصی یکی نیست. حالت خودکار فقط ضریب آزمون را به‌صورت یک تعدیل‌گرِ شفاف در اولویت فعالیت‌ها لحاظ می‌کند؛ وزن شخصی شما تغییر نمی‌کند.",
        kind="choice", options=("خودکار با توجه به ضریب آزمون", "فقط وزن شخصی من"), required=True,
    ),
    OnboardingStep(
        key="energy_level", title="سطح انرژی معمول",
        description="خودگزارشی: ۱ کم، ۲ متوسط، ۳ خوب.", kind="number", options=("۱", "۲", "۳"),
    ),
    OnboardingStep(
        key="peak_hours", title="ساعت‌های پربازده",
        description="مثل «۱۶:۰۰–۱۸:۰۰, ۲۰:۰۰–۲۲:۰۰» (اختیاری).", kind="text",
    ),
    OnboardingStep(
        key="topic_levels", title="سطح اولیهٔ هر مبحث",
        description="سطح در سطح مبحث سنجیده می‌شود، نه یک برچسب کلی برای کل درس. این گام اختیاری است؛ بعداً در صفحهٔ «مباحث و تسلط» برای هر مبحث جدا تکمیل می‌شود.",
        kind="text",
    ),
    OnboardingStep(
        key="previous_results", title="نتایج آزمون قبلی",
        description="اختیاری؛ بعداً هم قابل ثبت است.", kind="text",
    ),
    OnboardingStep(
        key="confirm", title="تأیید نهایی",
        description="خلاصهٔ داده‌های واردشده را ببینید و تأیید کنید.", kind="confirm", required=True,
    ),
)

@dataclass
class OnboardingState:
    """وضعیت مصاحبهٔ راه‌اندازی (قابل ذخیره و ادامه)."""

    values: dict[str, str] = field(default_factory=dict)
    completed_steps: set[str] = field(default_factory=set)
    current_index: int = 0

    @property
    def is_finished(self) -> bool:
        return "confirm" in self.completed_steps

    def current_step(self) -> Optional[OnboardingStep]:
        if self.current_index >= len(ONBOARDING_STEPS):
            return None
        return ONBOARDING_STEPS[self.current_index]

    def unresolved_blocking_questions(self) -> list[str]:
        """پرسش‌های مسدودکننده‌ای که هنوز بی‌پاسخ‌اند."""
        return [
            step.blocking_question
            for step in ONBOARDING_STEPS
            if step.blocking_question
            and step.key not in self.completed_steps
        ]

    def to_json(self) -> str:
        return json.dumps(
            {
                "values": self.values,
                "completed_steps": sorted(self.completed_steps),
                "current_index": self.current_index,
                "current_step_key": (
                    ONBOARDING_STEPS[self.current_index].key
                    if 0 <= self.current_index < len(ONBOARDING_STEPS) else ""
                ),
                "flow_version": 2,
            },
            ensure_ascii=False,
        )

    @classmethod
    def from_json(cls, text: str) -> "OnboardingState":
        raw = json.loads(text)
        values = dict(raw.get("values", {}))
        # Remove only the retired UI's generated summary/answer, never JSON
        # event data or real calendar records supplied by the user.
        old_schedule = values.get("weekly_schedule")
        legacy_summary = isinstance(old_schedule, str) and not old_schedule.lstrip().startswith("[")
        if legacy_summary:
            values.pop("weekly_schedule", None)
        values.pop("sunday_recorded", None)
        completed_steps = set(raw.get("completed_steps", []))
        if legacy_summary:
            completed_steps.discard("weekly_schedule")
        completed_steps.discard("sunday_recorded")
        current_index = int(raw.get("current_index", 0))
        saved_key = str(raw.get("current_step_key", ""))
        keys = [step.key for step in ONBOARDING_STEPS]
        if saved_key in keys:
            current_index = keys.index(saved_key)
        elif int(raw.get("flow_version", 1)) < 2:
            # Migrate the former flow by step identity, not by assuming that
            # the user's saved interview has the same number/order of screens.
            if legacy_summary and current_index > 11:
                current_index -= 1
            old_keys = (
                "student_name", "exam_group", "exam_year", "exam_name", "exam_date",
                "exam_date_status", "exam_source", "subjects", "books", "sleep_time",
                "weekly_schedule", "energy_level", "peak_hours", "previous_results", "confirm",
            )
            if 0 <= current_index < len(old_keys) and old_keys[current_index] in keys:
                current_index = keys.index(old_keys[current_index])
        current_index = max(0, min(current_index, len(ONBOARDING_STEPS) - 1))
        return cls(
            values=values,
            completed_steps=completed_steps,
            current_index=current_index,
        )

    def set_value(self, key: str, value: str) -> None:
        self.values[key] = value

    def complete_step(self, key: str) -> None:
        self.completed_steps.add(key)
        # حرکت به گام بعد
        keys = [step.key for step in ONBOARDING_STEPS]
        if key in keys:
            self.current_index = min(len(ONBOARDING_STEPS), keys.index(key) + 1)


def parse_clock_pair(text: str) -> Optional[tuple[int, int]]:
    """«۲۳:۰۰ تا ۰۶:۰۰» ⇒ (۱۳۸۰, ۳۶۰)."""
    from .jdate import normalize_digits

    normalized = normalize_digits(text).replace("–", "-").replace("—", "-")
    parts = [p.strip() for p in normalized.replace("تا", "-").split("-") if p.strip()]
    if len(parts) != 2:
        return None
    try:
        start = _parse_clock(parts[0])
        end = _parse_clock(parts[1])
    except ValueError:
        return None
    return start, end


def parse_subjects(text: str) -> list[tuple[str, float]]:
    """«ریاضی:۳, فیزیک:۳» ⇒ [("ریاضی", ۳.۰), ...]."""
    from .jdate import normalize_digits

    result: list[tuple[str, float]] = []
    for chunk in normalize_digits(text).split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" in chunk:
            name, _, coefficient = chunk.partition(":")
            try:
                value = float(coefficient.strip())
            except ValueError:
                value = 1.0
            result.append((name.strip(), value))
        else:
            result.append((chunk, 1.0))
    return result


def summarize(state: OnboardingState) -> list[str]:
    """خلاصهٔ ورودی واقعی برای پیش‌نمایشِ تأیید."""
    values = state.values

    def count_rows(key: str) -> int:
        try:
            result = json.loads(values.get(key, "[]"))
            return len(result) if isinstance(result, list) else 0
        except (ValueError, TypeError):
            return 0

    try:
        selected = json.loads(values.get("subjects", "[]"))
        selected_text = "، ".join(map(str, selected)) if isinstance(selected, list) else str(selected)
    except (ValueError, TypeError):
        selected_text = values.get("subjects", "")
    books = []
    try:
        books = json.loads(values.get("books", "[]"))
    except (ValueError, TypeError):
        pass
    selected_books = sum(1 for row in books if isinstance(row, dict) and row.get("selected")) if isinstance(books, list) else 0
    return [
        f"نام: {values.get('student_name') or '—'}",
        f"گروه/رشته: {values.get('exam_group') or '—'}",
        f"سال آزمون: {values.get('exam_year') or '—'}",
        f"آزمون: {values.get('exam_name') or '—'}",
        f"تاریخ: {values.get('exam_date') or 'ثبت‌نشده'} ({values.get('exam_date_status') or 'نامشخص'})",
        f"درس‌ها/دسته‌های انتخابی: {selected_text or '—'}",
        f"کتاب‌های انتخابی: {selected_books}",
        f"حضور در کلاس مؤسسه: {values.get('class_attendance') or '—'}؛ جلسه‌های واردشده: {count_rows('classes')}",
        f"آزمون‌ها/تعهدهای هفتگی: {count_rows('weekly_schedule')}",
        f"روال‌های ثابت: {count_rows('routines')}؛ بازهٔ خواب: {values.get('sleep_time') or '—'}",
        f"اولویت‌بندی: {values.get('priority_mode') or '—'}",
    ]
