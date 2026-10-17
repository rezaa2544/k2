"""راه‌اندازی مرحله‌ای و دادهٔ نمونهٔ برنامهٔ کاربر (ONB-01 تا ONB-05).

برنامهٔ هفتگی ثبت‌شده **دادهٔ نمونه و قابل ویرایش** است، نه منطق ثابت در کد.
تعارض واقعی یکشنبه (شیمی ۱۵:۰۰–۱۹:۰۰ و دینی ۱۵:۱۵–۲۰:۴۵) عمداً پنهان
نمی‌شود: تا وقتی کاربر مشخص نکند کدام‌یک ضبط‌شده است، این تعارض باز
می‌ماند و برنامهٔ قطعی تولید نمی‌شود.
"""

from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

from .domain.enums import FixedEventKind, RoutineKind, RoutineScope
from .domain.models import FixedEvent, Routine

#: نام روزها به ترتیب شنبه‌محور برای نگاشت.
DAY_ORDER = ("شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه")


def _minutes(hour: int, minute: int = 0) -> int:
    return hour * 60 + minute


@dataclass
class SampleEvent:
    """تعریف یک رویداد نمونه."""

    title: str
    weekday: int
    start: str
    end: str
    kind: FixedEventKind = FixedEventKind.LIVE_CLASS
    subject: str = ""
    is_recorded: bool = False
    notes: str = ""


#: برنامهٔ هفتگی ثبت‌شدهٔ کاربر (سند USER_SCHEDULE_AND_ONBOARDING).
SAMPLE_WEEKLY_EVENTS: tuple[SampleEvent, ...] = (
    SampleEvent("زیست", 0, "15:00", "19:00", subject="زیست"),
    SampleEvent("فیزیک", 0, "19:30", "22:45", subject="فیزیک"),
    SampleEvent("شیمی", 1, "15:00", "19:00", subject="شیمی"),
    SampleEvent(
        "دینی",
        1,
        "15:15",
        "20:45",
        subject="دینی",
        notes="هم‌پوشان با شیمی — باید در راه‌اندازی روشن شود کدام ضبط‌شده است.",
    ),
    SampleEvent("زبان انگلیسی", 1, "21:00", "23:00", subject="انگلیسی"),
    SampleEvent("ریاضی", 2, "19:30", "23:00", subject="ریاضی"),
    SampleEvent(
        "زمین‌شناسی (ضبط‌شده)",
        2,
        "00:00",
        "00:00",
        kind=FixedEventKind.RECORDED_CLASS,
        subject="زمین‌شناسی",
        is_recorded=True,
        notes="کلاس ضبط‌شده؛ زمان جداگانه لازم دارد و باید به‌صورت فعالیت قابل تقسیم ثبت شود.",
    ),
    SampleEvent("زیست", 3, "15:00", "19:00", subject="زیست"),
    SampleEvent("عربی", 3, "19:15", "21:00", subject="عربی"),
    SampleEvent("فیزیک", 4, "15:00", "19:30", subject="فیزیک"),
    SampleEvent("شیمی", 4, "19:30", "22:45", subject="شیمی"),
    SampleEvent("فارسی", 5, "13:15", "14:45", subject="فارسی"),
    SampleEvent("هویت اجتماعی", 5, "15:00", "16:30", subject="هویت اجتماعی"),
    SampleEvent("ریاضی", 6, "12:00", "15:00", subject="ریاضی"),
)

#: نمونهٔ بازه‌های ضروری روزانه (قابل تنظیم).
SAMPLE_ROUTINES: tuple[tuple[str, RoutineKind, str, str, RoutineScope], ...] = (
    ("خواب شب", RoutineKind.SLEEP, "23:00", "06:00", RoutineScope.DAILY),
    ("خواب روز (چرت)", RoutineKind.SLEEP, "13:00", "13:30", RoutineScope.DAILY),
    ("صبحانه", RoutineKind.MEAL, "07:00", "07:30", RoutineScope.DAILY),
    ("ناهار", RoutineKind.MEAL, "12:30", "13:00", RoutineScope.DAILY),
    ("شام", RoutineKind.MEAL, "20:00", "20:45", RoutineScope.DAILY),
    ("استراحت", RoutineKind.REST, "16:30", "16:45", RoutineScope.DAILY),
    ("حمام", RoutineKind.HYGIENE, "22:45", "23:00", RoutineScope.DAILY),
)


def _parse_clock(text: str) -> int:
    hour, _, minute = text.partition(":")
    return _minutes(int(hour), int(minute or 0))


def build_sample_fixed_events() -> list[FixedEvent]:
    """رویدادهای ثابت نمونه به‌صورت مدل دامنه."""
    events: list[FixedEvent] = []
    for sample in SAMPLE_WEEKLY_EVENTS:
        if sample.start == sample.end:
            # زمان‌نامعلوم (مثلاً کلاس ضبط‌شده) ⇒ مدت صفر؛ بعداً تعیین می‌شود.
            start = end = 0
        else:
            start = _parse_clock(sample.start)
            end = _parse_clock(sample.end)
        events.append(
            FixedEvent(
                title=sample.title,
                kind=sample.kind,
                subject_name=sample.subject,
                weekday=sample.weekday,
                start_minute=start,
                end_minute=end,
                is_recorded=sample.is_recorded,
                notes=sample.notes,
            )
        )
    return events


def build_sample_routines() -> list[Routine]:
    """بازه‌های ضروری نمونه."""
    routines: list[Routine] = []
    for title, kind, start, end, scope in SAMPLE_ROUTINES:
        routines.append(
            Routine(
                title=title,
                kind=kind,
                start_minute=_parse_clock(start),
                end_minute=_parse_clock(end),
                weekdays=frozenset(range(7)),
                scope=scope,
                counts_as_study=False,
            )
        )
    return routines


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


def detect_sample_conflicts() -> list[ScheduleConflict]:
    """تعارض‌های برنامهٔ نمونه را پیدا می‌کند (ONB-03)."""
    conflicts: list[ScheduleConflict] = []
    by_day: dict[int, list[SampleEvent]] = {}
    for sample in SAMPLE_WEEKLY_EVENTS:
        if sample.start == sample.end:
            continue
        by_day.setdefault(sample.weekday, []).append(sample)

    for weekday, samples in by_day.items():
        samples = sorted(samples, key=lambda s: _parse_clock(s.start))
        for index in range(len(samples) - 1):
            first, second = samples[index], samples[index + 1]
            if _parse_clock(second.start) < _parse_clock(first.end):
                conflicts.append(
                    ScheduleConflict(
                        weekday=weekday,
                        first_title=first.title,
                        second_title=second.title,
                        first_range=f"{first.start}–{first.end}",
                        second_range=f"{second.start}–{second.end}",
                        question=(
                            "در یکشنبه کدام کلاس ضبط‌شده است: شیمی یا دینی؟ "
                            "تا زمانی که این مشخص نشود، برنامهٔ قطعی تولید نمی‌شود."
                        ),
                    )
                )
    return conflicts


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
        key="student_name",
        title="نام داوطلب",
        description="نامی که در گزارش‌ها استفاده می‌شود.",
        kind="text",
    ),
    OnboardingStep(
        key="exam_group",
        title="گروه/رشتهٔ آزمایشی",
        description="گروه آزمایشی هدف و رشته یا دانشگاه موردنظر (اختیاری).",
        kind="choice",
        options=("علوم تجربی", "علوم ریاضی و فنی", "علوم انسانی", "سایر/تغییر رشته"),
        required=True,
    ),
    OnboardingStep(
        key="exam_year",
        title="سال آزمون هدف",
        description=(
            "سال آزمون را انتخاب کنید. اگر دادهٔ رسمی آن سال در برنامه تأیید نشده باشد، "
            "ضرایب خالی می‌مانند و برای اولویت‌بندی رسمی استفاده نمی‌شوند."
        ),
        kind="choice",
        options=("۱۴۰۵", "۱۴۰۶", "سال دیگر / هنوز مشخص نیست"),
        required=True,
    ),
    OnboardingStep(
        key="exam_name",
        title="نام آزمون هدف",
        description="مثلاً «کنکور سراسری». اطلاعات تاریخ و ضرایب جداگانه وارد می‌شود.",
        kind="text",
        required=True,
    ),
    OnboardingStep(
        key="exam_date",
        title="تاریخ آزمون هدف",
        description=(
            "به‌صورت شمسی وارد کنید (مثل ۱۴۰۵/۰۷/۲۴). اگر تاریخ رسمی هنوز "
            "اعلام نشده، آن را تخمینی وارد کنید."
        ),
        kind="date",
        required=True,
    ),
    OnboardingStep(
        key="exam_date_status",
        title="وضعیت تاریخ آزمون",
        description="آیا تاریخ از منبع رسمی گرفته شده است؟",
        kind="choice",
        options=("رسمی (منبع ثبت‌شده)", "تخمینی", "نامشخص"),
        required=True,
    ),
    OnboardingStep(
        key="exam_source",
        title="منبع تاریخ و مقررات",
        description="عنوان و محل اطلاعیه یا دفترچهٔ رسمی (اختیاری ولی مهم).",
        kind="text",
    ),
    OnboardingStep(
        key="subjects",
        title="انتخاب درس‌ها",
        description=(
            "درس‌های موردنیازتان را انتخاب کنید. انتخاب همه، هیچ‌کدام یا ترکیب دلخواه "
            "ممکن است؛ تغییر رشته انتخاب‌های قبلی را حذف نمی‌کند."
        ),
        kind="multiselect",
        required=True,
    ),
    OnboardingStep(
        key="books",
        title="کتاب‌ها و منابع هر درس",
        description=(
            "برای هر کتاب یک ردیف با قالب «درس | عنوان | کد | پایه | سال چاپ | پیوند منبع» "
            "وارد کنید. موردهای واردشده تا زمان بازبینی پیوند، تأییدنشده می‌مانند."
        ),
        kind="books",
    ),
    OnboardingStep(
        key="sleep_time",
        title="ساعت خواب و بیداری",
        description="مثل «۲۳:۰۰ تا ۰۶:۰۰». خواب محدودیت سخت است.",
        kind="text",
        required=True,
    ),
    OnboardingStep(
        key="weekly_schedule",
        title="برنامهٔ کلاس‌ها و تعهدات",
        description=(
            "برنامهٔ هفتگی ثبت‌شدهٔ شما بارگذاری می‌شود. می‌توانید هر مورد را ویرایش کنید."
        ),
        kind="schedule",
        required=True,
    ),
    OnboardingStep(
        key="sunday_recorded",
        title="کلاس ضبط‌شدهٔ یکشنبه",
        description=(
            "کلاس شیمی و دینی یکشنبه با هم هم‌پوشانی دارند. کدام‌یک ضبط‌شده/غیرهم‌زمان است؟"
        ),
        kind="choice",
        options=("شیمی", "دینی", "هیچ‌کدام (برنامهٔ دیگری دارم)"),
        required=True,
        blocking_question=(
            "در یکشنبه کدام کلاس ضبط‌شده است: شیمی یا دینی؟ تا حل تعارض، "
            "برنامهٔ قطعی تولید نمی‌شود."
        ),
    ),
    OnboardingStep(
        key="energy_level",
        title="سطح انرژی معمول",
        description="خودگزارشی: ۱ کم، ۲ متوسط، ۳ خوب.",
        kind="number",
        options=("۱", "۲", "۳"),
    ),
    OnboardingStep(
        key="peak_hours",
        title="ساعت‌های پربازده",
        description="مثل «۱۶:۰۰–۱۸:۰۰, ۲۰:۰۰–۲۲:۰۰» (اختیاری).",
        kind="text",
    ),
    OnboardingStep(
        key="previous_results",
        title="نتایج آزمون قبلی",
        description="اختیاری. بعداً هم قابل ثبت است.",
        kind="text",
    ),
    OnboardingStep(
        key="confirm",
        title="تأیید نهایی",
        description="خلاصهٔ داده‌های واردشده را ببینید و تأیید کنید.",
        kind="confirm",
        required=True,
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
            },
            ensure_ascii=False,
        )

    @classmethod
    def from_json(cls, text: str) -> "OnboardingState":
        raw = json.loads(text)
        return cls(
            values=dict(raw.get("values", {})),
            completed_steps=set(raw.get("completed_steps", [])),
            current_index=int(raw.get("current_index", 0)),
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
    """خلاصهٔ داده‌های راه‌اندازی برای نمایش."""
    values = state.values
    lines = [
        f"نام: {values.get('student_name', '—')}",
        f"گروه/رشته: {values.get('exam_group', '—')}",
        f"سال آزمون: {values.get('exam_year', '—')}",
        f"آزمون: {values.get('exam_name', '—')}",
        f"تاریخ: {values.get('exam_date', '—')} ({values.get('exam_date_status', '—')})",
        f"دروس: {values.get('subjects', '—')}",
        f"خواب: {values.get('sleep_time', '—')}",
        f"کلاس ضبط‌شدهٔ یکشنبه: {values.get('sunday_recorded', '—')}",
    ]
    return lines
