"""مدل‌های دامنه.

این ماژول فقط ساختار داده و قواعد خالص دارد و به UI یا پایگاه داده وابسته
نیست؛ بنابراین مستقیماً قابل تست واحد است.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Optional

from .enums import (
    ActivityState,
    ActivityType,
    Bottleneck,
    ContentType,
    DateStatus,
    DeadlineType,
    EnergyNeed,
    ErrorCode,
    ExamKind,
    FixedEventKind,
    MasteryLevel,
    ReviewState,
    RoutineKind,
    RoutineScope,
    ScopeStatus,
    StudyPhase,
)


# ---------------------------------------------------------------------------
# پروفایل و آزمون
# ---------------------------------------------------------------------------


@dataclass
class ExamProfile:
    """پروفایل آزمون هدف — کاملاً قابل ویرایش (سند تحقیق ۳، بخش ۲).

    هیچ تاریخ، ضریب، تعداد سؤال یا نمرهٔ منفی جاری در کد ثابت نشده است.
    """

    id: Optional[int] = None
    name: str = "آزمون هدف"
    group_name: str = ""
    target_date: Optional[_dt.date] = None
    date_status: DateStatus = DateStatus.UNKNOWN
    source_note: str = ""
    #: نمرهٔ منفی به‌صورت ضریب (مثلاً ۰٫۲۵ یعنی یک‌چهارم نمرهٔ سؤال).
    negative_marking_ratio: float = 0.0
    #: فرمول درصد: ``"raw"`` (درصد خام) یا ``"negative"`` (با نمرهٔ منفی).
    percentage_formula: str = "raw"
    regulation_version: str = ""
    exam_year: Optional[int] = None
    created_at: Optional[_dt.datetime] = None

    @property
    def days_remaining(self) -> Optional[int]:
        """روزهای باقی‌مانده تا آزمون (نسبت به امروز)."""
        if self.target_date is None:
            return None
        return (self.target_date - _dt.date.today()).days

    @property
    def date_is_confirmed(self) -> bool:
        return self.date_status == DateStatus.OFFICIAL


@dataclass
class Subject:
    """درس با وزن آن در آزمون هدف."""

    id: Optional[int] = None
    name: str = ""
    exam_profile_id: Optional[int] = None
    #: وزن برنامه‌ریزی فردی؛ مستقل از ضرایب رسمی آزمون/سوابق.
    coefficient: float = 1.0
    #: وزن مبحث در محاسبهٔ «ضعف × اهمیت»؛ مقدار دستی بر وزن فردی اولویت دارد.
    topic_weight: Optional[float] = None
    is_selected: bool = True
    exam_coefficient: Optional[float] = None
    exam_coefficient_status: str = "unknown"
    exam_coefficient_source: str = ""
    academic_coefficient: Optional[float] = None
    academic_coefficient_status: str = "unknown"
    academic_coefficient_source: str = ""

    @property
    def effective_weight(self) -> float:
        return self.topic_weight if self.topic_weight is not None else self.coefficient


@dataclass
class Textbook:
    """کتاب درسی/منبع انتخاب‌شده برای یک درس و پروفایل آزمون."""

    id: Optional[int] = None
    exam_profile_id: Optional[int] = None
    subject_id: Optional[int] = None
    title: str = ""
    book_code: str = ""
    grade: str = ""
    edition_year: Optional[int] = None
    source_url: str = ""
    source_status: str = "user_entered"
    is_selected: bool = True


@dataclass
class Topic:
    """مبحث زیرمجموعهٔ یک درس."""

    id: Optional[int] = None
    subject_id: Optional[int] = None
    subject_name: str = ""
    name: str = ""
    content_type: ContentType = ContentType.CONCEPTUAL
    scope_status: ScopeStatus = ScopeStatus.UNKNOWN
    mastery: MasteryLevel = MasteryLevel.L0
    self_assessed: Optional[int] = None
    notes: str = ""


@dataclass
class LearningEvidence:
    """یک سنجش عملکردی مبحث؛ score در بازهٔ ۰..۱ ذخیره می‌شود."""

    id: Optional[int] = None
    topic_id: Optional[int] = None
    observed_on: Optional[_dt.date] = None
    source: str = "diagnostic"  # diagnostic / delayed / transfer / mixed_exam / review
    score: float = 0.0
    item_count: int = 0
    confidence: int = 2  # 1..4; خودگزارشی و جدا از صحت
    duration_seconds: Optional[int] = None
    note: str = ""


# ---------------------------------------------------------------------------
# تقویم
# ---------------------------------------------------------------------------


@dataclass
class FixedEvent:
    """رویداد ثابت هفتگی: کلاس، آزمون یا تعهد."""

    id: Optional[int] = None
    title: str = ""
    kind: FixedEventKind = FixedEventKind.LIVE_CLASS
    subject_id: Optional[int] = None
    subject_name: str = ""
    #: ۰=شنبه ... ۶=جمعه
    weekday: int = 0
    start_minute: int = 0
    end_minute: int = 0
    #: کلاس ضبط‌شده ⇒ فعالیت قابل تقسیم با نقطهٔ توقف.
    is_recorded: bool = False
    notes: str = ""


@dataclass
class Routine:
    """بازهٔ ضروری روزانه: خواب، غذا، استراحت، بهداشت و…"""

    id: Optional[int] = None
    title: str = ""
    kind: RoutineKind = RoutineKind.MEAL
    start_minute: int = 0
    end_minute: int = 0
    #: پوشش هفتگی؛ مثال: ``{0,1,2,3,4,5,6}`` یا ``{0,2,4}`` برای یک‌روزدرمیان.
    weekdays: frozenset[int] = field(default_factory=lambda: frozenset(range(7)))
    scope: RoutineScope = RoutineScope.DAILY
    counts_as_study: bool = False


@dataclass
class EventException:
    """استثنای یک‌باره برای یک رویداد (لغو یا جابه‌جایی)."""

    id: Optional[int] = None
    event_id: Optional[int] = None
    date: Optional[_dt.date] = None
    cancelled: bool = False
    new_start_minute: Optional[int] = None
    new_end_minute: Optional[int] = None
    reason: str = ""


# ---------------------------------------------------------------------------
# فعالیت
# ---------------------------------------------------------------------------


@dataclass
class Activity:
    """کاری که باید انجام شود (سند تحقیق ۲، بخش ۴)."""

    id: Optional[int] = None
    title: str = ""
    type: ActivityType = ActivityType.PROCESSING
    subject_id: Optional[int] = None
    subject_name: str = ""
    topic_id: Optional[int] = None
    topic_name: str = ""
    est_minutes: int = 45
    actual_minutes: int = 0
    remaining_minutes: int = 0
    min_chunk: int = 20
    max_chunk: int = 90
    splittable: bool = True
    deadline_type: DeadlineType = DeadlineType.NONE
    deadline_at: Optional[_dt.datetime] = None
    depends_on: tuple[int, ...] = ()
    state: ActivityState = ActivityState.PLANNED
    state_reason: str = ""
    energy_need: EnergyNeed = EnergyNeed.MEDIUM
    created_at: Optional[_dt.datetime] = None
    first_planned_at: Optional[_dt.datetime] = None
    times_rescheduled: int = 0
    #: نقطهٔ توقف برای فعالیت‌های قابل تقسیم (مثلاً ویدئوی ضبط‌شده).
    resume_marker: Optional[int] = None
    origin: str = "manual"
    #: شدت ضعف مبحث (۰..۱)؛ از عملکرد محاسبه می‌شود.
    topic_weakness: float = 0.0
    #: وزن اهمیت مبحث در آزمون هدف.
    topic_weight: float = 1.0
    #: فاصلهٔ مرور سررسیدشده بر حسب روز (برای امتیازدهی).
    review_overdue_days: float = 0.0
    #: تعداد فعالیت‌هایی که به این فعالیت وابسته‌اند و مسدود شده‌اند.
    blocked_dependents: int = 0

    @property
    def effective_minutes(self) -> int:
        """زمان لازم برای انجام: باقی‌مانده اگر هست، وگرنه برآورد."""
        if self.remaining_minutes > 0:
            return self.remaining_minutes
        return max(0, self.est_minutes)

    @property
    def is_splittable(self) -> bool:
        return bool(self.splittable) and self.type not in {
            ActivityType.TIMED_TEST,
            ActivityType.EXAM,
        }

    @property
    def has_hard_deadline(self) -> bool:
        return self.deadline_type == DeadlineType.HARD


@dataclass
class ActivityEvent:
    """رویداد تاریخچهٔ فعالیت (ACT-04)."""

    id: Optional[int] = None
    activity_id: Optional[int] = None
    at: Optional[_dt.datetime] = None
    kind: str = "state_change"
    from_state: Optional[ActivityState] = None
    to_state: Optional[ActivityState] = None
    note: str = ""


# ---------------------------------------------------------------------------
# برنامه
# ---------------------------------------------------------------------------


@dataclass
class Placement:
    """جای‌گذاری یک فعالیت در یک بلوک زمانی به‌همراه دلیل (SCH-01)."""

    activity_id: int
    title: str
    date: _dt.date
    start_minute: int
    end_minute: int
    minutes: int
    score: float = 0.0
    reasons: tuple[str, ...] = ()
    chunk_index: int = 0
    chunk_total: int = 1

    @property
    def start_clock(self) -> str:
        return f"{self.start_minute // 60:02d}:{self.start_minute % 60:02d}"

    @property
    def end_clock(self) -> str:
        return f"{self.end_minute // 60:02d}:{self.end_minute % 60:02d}"


@dataclass
class UnplacedActivity:
    """فعالیتی که جا نشده است به‌همراه دلیل صریح (SCH-03)."""

    activity_id: int
    title: str
    minutes: int
    reason: str
    details: tuple[str, ...] = ()


@dataclass
class DayPlan:
    """برنامهٔ یک روز."""

    date: _dt.date
    placements: list[Placement] = field(default_factory=list)
    unplaced: list[UnplacedActivity] = field(default_factory=list)
    capacity_minutes: int = 0
    raw_minutes: int = 0
    effective_minutes: int = 0
    planned_minutes: int = 0
    free_minutes: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def margin_minutes(self) -> int:
        return max(0, self.capacity_minutes - self.planned_minutes)

    @property
    def is_over_capacity(self) -> bool:
        return self.planned_minutes > self.capacity_minutes


# ---------------------------------------------------------------------------
# مرور
# ---------------------------------------------------------------------------


@dataclass
class ReviewItem:
    """آیتم مرور (سند تحقیق ۱، بخش ۳.۲)."""

    id: Optional[int] = None
    topic_id: Optional[int] = None
    subject_id: Optional[int] = None
    label: str = ""
    item_type: str = "concept"
    interval_days: float = 0.0
    ease: float = 2.0
    difficulty: int = 3
    lapses: int = 0
    last_review: Optional[_dt.date] = None
    due_date: Optional[_dt.date] = None
    state: ReviewState = ReviewState.NEW
    last_grade: Optional[int] = None
    last_time_ratio: Optional[float] = None
    content: str = ""
    created_at: Optional[_dt.datetime] = None
    success_streak: int = 0


@dataclass
class ReviewLog:
    """ثبت یک مرور."""

    id: Optional[int] = None
    item_id: Optional[int] = None
    at: Optional[_dt.datetime] = None
    grade: int = 0
    confidence: int = 2
    seconds: Optional[int] = None
    note: str = ""


# ---------------------------------------------------------------------------
# آزمون و خطا
# ---------------------------------------------------------------------------


@dataclass
class ExamAttempt:
    """یک نوبت آزمون (سند تحقیق ۱، بخش ۴)."""

    id: Optional[int] = None
    exam_profile_id: Optional[int] = None
    name: str = ""
    kind: ExamKind = ExamKind.MOCK
    taken_at: Optional[_dt.datetime] = None
    subject_id: Optional[int] = None
    subject_name: str = ""
    total: int = 0
    correct: int = 0
    wrong: int = 0
    blank: int = 0
    duration_minutes: int = 0
    raw_score: float = 0.0
    percentage: float = 0.0
    note: str = ""


@dataclass
class ExamQuestion:
    """جزئیات اختیاری در سطح سؤال."""

    id: Optional[int] = None
    attempt_id: Optional[int] = None
    subject_id: Optional[int] = None
    topic_id: Optional[int] = None
    number: int = 0
    status: str = "correct"  # correct | wrong | blank
    error_code: Optional[ErrorCode] = None
    seconds: Optional[int] = None
    note: str = ""


@dataclass
class ErrorRecord:
    """رکورد خطا به‌همراه اقدام اصلاحی (ERR-01/ERR-02)."""

    id: Optional[int] = None
    attempt_id: Optional[int] = None
    question_id: Optional[int] = None
    code: ErrorCode = ErrorCode.E1
    topic_id: Optional[int] = None
    subject_id: Optional[int] = None
    created_at: Optional[_dt.datetime] = None
    resolution_activity_id: Optional[int] = None
    resolved_at: Optional[_dt.datetime] = None
    retest_attempt_id: Optional[int] = None
    note: str = ""


# ---------------------------------------------------------------------------
# مشاوره
# ---------------------------------------------------------------------------


@dataclass
class AdvisorSuggestion:
    """«کار بعدی» به‌همراه یک دلیل کوتاه (ADV-03)."""

    activity_id: Optional[int]
    title: str
    reason: str
    action_type: str = "activity"
    score: float = 0.0


@dataclass
class WeeklyReport:
    """گزارش هفتگی (ADV-04)."""

    start_date: _dt.date
    end_date: _dt.date
    planned_minutes: int = 0
    done_minutes: int = 0
    completed_activities: int = 0
    total_activities: int = 0
    partial_activities: int = 0
    dropped_activities: int = 0
    adherence: float = 0.0
    notes: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    estimate_bias: float = 0.0
    next_week_changes: list[str] = field(default_factory=list)
    accuracy_trend: list[float] = field(default_factory=list)
    repeated_error_rate: float = 0.0


__all__ = [
    "Activity",
    "ActivityEvent",
    "ActivityState",
    "ActivityType",
    "AdvisorSuggestion",
    "Bottleneck",
    "ContentType",
    "DateStatus",
    "DeadlineType",
    "EnergyNeed",
    "ErrorCode",
    "ErrorRecord",
    "EventException",
    "ExamAttempt",
    "ExamKind",
    "ExamProfile",
    "ExamQuestion",
    "FixedEvent",
    "FixedEventKind",
    "MasteryLevel",
    "Placement",
    "ReviewItem",
    "ReviewLog",
    "ReviewState",
    "Routine",
    "RoutineKind",
    "RoutineScope",
    "ScopeStatus",
    "Subject",
    "StudyPhase",
    "Topic",
    "UnplacedActivity",
    "WeeklyReport",
]
