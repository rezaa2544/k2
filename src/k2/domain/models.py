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
    DeadlineKind,
    DeadlineType,
    EnergyNeed,
    ErrorCode,
    ExamKind,
    FeasibilityAction,
    FinalStage,
    FixedEventKind,
    KonkurStage,
    MasteryLevel,
    ProblemKind,
    ProblemStatus,
    ReviewState,
    RoutineKind,
    RoutineScope,
    ScopeStatus,
    SessionKind,
    StudyPhase,
    TrackKind,
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
    """مبحث زیرمجموعهٔ یک درس.

    هر مبحث **دو مسیر مستقل** دارد (بند ۱۳): مسیر کنکور برای تست‌های
    چندگزینه‌ای و مسیر نهایی/مدرک برای سؤال تشریحی و کتاب درسی. پیشرفت
    هر مسیر جداگانه ذخیره می‌شود و جایگزین یکدیگر نیستند.
    """

    id: Optional[int] = None
    subject_id: Optional[int] = None
    subject_name: str = ""
    name: str = ""
    content_type: ContentType = ContentType.CONCEPTUAL
    scope_status: ScopeStatus = ScopeStatus.UNKNOWN
    mastery: MasteryLevel = MasteryLevel.L0
    self_assessed: Optional[int] = None
    notes: str = ""
    #: پلهٔ فعلی مسیر کنکور و نهایی (مقدار پایدار در پایگاه داده).
    konkur_stage: str = KonkurStage.CONCEPTUAL.value
    final_stage: str = FinalStage.TEXTBOOK_STUDY.value
    #: شناسهٔ آخرین شاهد تأییدکنندهٔ هر مسیر (سنجش/تست/تمرین تشریحی).
    konkur_evidence_id: Optional[int] = None
    final_evidence_id: Optional[int] = None
    #: این مبحث پیش‌نیاز چند مبحث دیگر است (۰..۱) — فاکتور اولویت (بند ۱۴).
    prerequisite_share: float = 0.0
    #: سهم لازم این مبحث در سؤال‌های تشریحی نهایی (۰..۱) [H].
    final_exam_share: float = 0.0
    #: برآورد زمان تکمیل هر دو مسیر (دقیقه) — بر پایهٔ دادهٔ واقعی کاربر.
    estimated_minutes: Optional[int] = None

    @property
    def konkur_stage_enum(self) -> KonkurStage:
        try:
            return KonkurStage(self.konkur_stage)
        except ValueError:
            return KonkurStage.CONCEPTUAL

    @property
    def final_stage_enum(self) -> FinalStage:
        try:
            return FinalStage(self.final_stage)
        except ValueError:
            return FinalStage.TEXTBOOK_STUDY


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
    #: هر چند هفته یک بار تکرار می‌شود (۱ = هر هفته). چرخهٔ آزمون جامع
    #: مثلاً «هر دو هفته» است و نباید هر هفته زمان ببندد.
    every_weeks: int = 1
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
class SyllabusSection:
    """وضعیت مطالعهٔ یک گفتار از سرفصل رسمی.

    ``title`` خالی یعنی نام رسمی کتاب استفاده شود. هشت سؤال وضعیت همان
    پرسش‌های پیش‌نمایش هستند تا دادهٔ دسکتاپ و وب یک معنی داشته باشند.
    اگر ردیفی نباشد یعنی گفتار هنوز ارزیابی نشده — نه اینکه صفر باشد.
    """

    subject: str
    grade: int
    chapter: int
    section: int
    title: str = ""
    teaching: Optional[str] = None
    study: Optional[str] = None
    comprehension: Optional[str] = None
    consolidation: Optional[str] = None
    testing: Optional[str] = None
    analysis: Optional[str] = None
    essay: Optional[str] = None
    speed: Optional[str] = None
    mastery: Optional[float] = None
    notes: str = ""
    updated_at: str = ""

    @property
    def answered(self) -> int:
        return sum(
            1
            for value in (
                self.teaching, self.study, self.comprehension, self.consolidation,
                self.testing, self.analysis, self.essay, self.speed,
            )
            if value
        )

    @property
    def is_assessed(self) -> bool:
        return bool(self.updated_at)


@dataclass
class SyllabusChapterEdit:
    """ویرایش کاربر روی یک فصل: تغییر عنوان یا ورود/پاک‌کردن تعداد گفتار.

    ``sections`` مقدار ``None`` یعنی «نامشخص»؛ برنامه هرگز صفر یا عددی که
    کاربر نگرفته است حدس نمی‌زند.
    """

    subject: str
    grade: int
    chapter: int
    title: str = ""
    sections: Optional[int] = None
    confirmed: bool = False
    updated_at: str = ""


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
    difficulty: float = 3.0
    lapses: int = 0
    last_review: Optional[_dt.date] = None
    due_date: Optional[_dt.date] = None
    state: ReviewState = ReviewState.NEW
    last_grade: Optional[int] = None
    last_time_ratio: Optional[float] = None
    content: str = ""
    created_at: Optional[_dt.datetime] = None
    success_streak: int = 0
    #: مدل حافظهٔ DSR (سند تحقیق ۵): پایداری به روز و بازیابی‌پذیری ۰..۱.
    #: برای رکوردهای قدیمی که مهاجرت نکرده‌اند صفر است و از interval برآورد می‌شود.
    stability_days: float = 0.0
    retrievability: float = 1.0


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
    #: پیوست نتیجهٔ آزمون (تصویر کارت پاسخ یا فایل) — فقط نگه‌داری می‌شود؛
    #: برنامه تصویر را «نمی‌خوانَد» و اعداد را کاربر وارد می‌کند.
    attachment_path: Optional[str] = None
    attachment_name: str = ""
    attachment_sha256: Optional[str] = None
    attachment_bytes: int = 0
    attachment_note: str = ""


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


# ---------------------------------------------------------------------------
# مهلت‌های من (بند ۱۲)
# ---------------------------------------------------------------------------


@dataclass
class TopicDeadline:
    """یک مهلت از میان چهار مهلت هر مبحث.

    «مهلت تثبیت نهایی» مرجع بازمحاسبهٔ تاریخ سایر مهلت‌هاست: از آن روز
    به عقب برمی‌گردیم و می‌بینیم هر پله چند روز وقت می‌خواهد.
    """

    id: Optional[int] = None
    topic_id: Optional[int] = None
    subject_id: Optional[int] = None
    topic_name: str = ""
    subject_name: str = ""
    kind: DeadlineKind = DeadlineKind.INITIAL_LEARNING
    target_date: Optional[_dt.date] = None
    #: هدف درصدی برای تست/آزمون این مهلت (۰..۱۰۰) — اختیاری.
    target_percent: Optional[float] = None
    #: هدف سطح تسلط (L0..L4) — اختیاری.
    target_level: Optional[str] = None
    #: هدف برای کدام مسیر است: کنکور (تستی) یا نهایی (تشریحی/مدرک).
    target_track: TrackKind = TrackKind.KONKUR
    #: آیا این مهلت، مهلت مادرِ بازمحاسبه است؟
    is_master: bool = False
    note: str = ""
    created_at: Optional[_dt.datetime] = None
    updated_at: Optional[_dt.datetime] = None

    @property
    def days_remaining(self) -> Optional[int]:
        if self.target_date is None:
            return None
        return (self.target_date - _dt.date.today()).days

    @property
    def has_measurable_target(self) -> bool:
        """هدف سنجش‌شدنی دارد؟ بدون آن، تکمیل مهلت قابل اثبات نیست."""
        return self.target_percent is not None or self.target_level is not None


@dataclass
class DeadlineMilestone:
    """یک پله در بازمحاسبهٔ تاریخ‌های یک مبحث."""

    kind: DeadlineKind
    label: str
    date: Optional[_dt.date] = None
    minutes: int = 0
    note: str = ""


@dataclass
class DeadlineSuggestion:
    """پیشنهاد وقتی مهلت با ظرفیت واقعی هم‌خوان نیست (بند ۱۲)."""

    action: FeasibilityAction
    title: str
    detail: str
    #: تأثیر تقریبی بر تاریخ (مثبت = عقب کشیدن مهلت).
    shift_days: int = 0


@dataclass
class TopicDeadlinePlan:
    """نتیجهٔ بازمحاسبهٔ یک مبحث از مهلت تثبیت نهایی به عقب."""

    topic_id: int
    topic_name: str = ""
    subject_name: str = ""
    milestones: list[DeadlineMilestone] = field(default_factory=list)
    total_minutes: int = 0
    capacity_minutes_per_day: int = 0
    required_days: float = 0.0
    available_days: int = 0
    #: کمبود تقویمی: چند روز بیش از بازهٔ باقی‌مانده لازم است (جلوگیری از
    #: برنامهٔ «شدنی» که فقط به‌خاطر ظرفیت بالا به نظر می‌رسد شدنی است).
    missing_days: int = 0
    feasible: bool = True
    warnings: list[str] = field(default_factory=list)
    suggestions: list[DeadlineSuggestion] = field(default_factory=list)

    @property
    def start_date(self) -> Optional[_dt.date]:
        for milestone in self.milestones:
            if milestone.kind == DeadlineKind.START:
                return milestone.date
        return None

    @property
    def consolidation_date(self) -> Optional[_dt.date]:
        for milestone in self.milestones:
            if milestone.kind == DeadlineKind.FINAL_CONSOLIDATION:
                return milestone.date
        return None

    @property
    def overload_minutes(self) -> int:
        """چقدر کار بیش از ظرفیت باقی‌مانده است (صفر = قابل اجرا).

        دو منبع کمبود حساب می‌شود: حجم کار بیش از ظرفیت باقی‌مانده، و
        کمبود تقویمی (پله‌ها با فاصلهٔ ایمن در بازهٔ باقی‌مانده جا نمی‌شوند).
        """
        if self.capacity_minutes_per_day <= 0:
            return max(0, self.total_minutes)
        volume_shortfall = max(
            0, self.total_minutes - self.available_days * self.capacity_minutes_per_day
        )
        return volume_shortfall + self.missing_days * self.capacity_minutes_per_day


# ---------------------------------------------------------------------------
# ساعت مطالعه (بند ۱۵)
# ---------------------------------------------------------------------------


@dataclass
class StudySession:
    """یک جلسهٔ مطالعه/کلاس/تست/تحلیل/مرور.

    ``minutes`` همیشه **خالص** است: از بازهٔ شروع تا پایان، زمان استراحت
    (پause) کم می‌شود. زمان کلاس جداگانه ثبت می‌شود تا مطالعهٔ مستقل پنهان
    نشود.
    """

    id: Optional[int] = None
    subject_id: Optional[int] = None
    subject_name: str = ""
    topic_id: Optional[int] = None
    topic_name: str = ""
    activity_id: Optional[int] = None
    kind: SessionKind = SessionKind.STUDY
    #: ``timer`` = با تایمر درون‌برنامه‌ای، ``manual`` = ثبت دستی.
    mode: str = "timer"
    started_at: Optional[_dt.datetime] = None
    ended_at: Optional[_dt.datetime] = None
    #: مجموع ثانیه‌های استراحت در این جلسه.
    paused_seconds: int = 0
    #: لحظهٔ آخرین استراحت (اگر تایمر متوقف مانده باشد) — برای این‌که
    #: زمان بسته‌بودن برنامه به‌عنوان مطالعه شمرده نشود.
    paused_at: Optional[_dt.datetime] = None
    #: دقیقهٔ خالص مؤثر.
    minutes: int = 0
    note: str = ""
    created_at: Optional[_dt.datetime] = None
    updated_at: Optional[_dt.datetime] = None

    @property
    def gross_seconds(self) -> int:
        """بازهٔ کل از شروع تا پایان (شامل استراحت)."""
        if self.started_at is None or self.ended_at is None:
            return 0
        return int((self.ended_at - self.started_at).total_seconds())

    @property
    def is_running(self) -> bool:
        return self.started_at is not None and self.ended_at is None

    @property
    def is_class_time(self) -> bool:
        return self.kind in {
            SessionKind.LIVE_CLASS,
            SessionKind.RECORDED_CLASS,
        }


@dataclass
class StudySessionRevision:
    """تاریخچهٔ اصلاح یک جلسهٔ ثبت‌شده (بند ۱۵)."""

    id: Optional[int] = None
    session_id: Optional[int] = None
    at: Optional[_dt.datetime] = None
    field_name: str = ""
    old_value: str = ""
    new_value: str = ""
    reason: str = ""


@dataclass
class SessionTotals:
    """جمع‌های خالص روزانه/هفتگی به تفکیک نوع."""

    label: str = ""
    total_minutes: int = 0
    class_minutes: int = 0
    independent_minutes: int = 0
    test_minutes: int = 0
    analysis_minutes: int = 0
    review_minutes: int = 0
    consolidation_minutes: int = 0
    session_count: int = 0

    @property
    def independent_share(self) -> float:
        if self.total_minutes <= 0:
            return 0.0
        return self.independent_minutes / self.total_minutes


# ---------------------------------------------------------------------------
# مشکلات یادگیری (بند ۱۷)
# ---------------------------------------------------------------------------


@dataclass
class LearningProblem:
    """یک مشکل یادگیری که خود کاربر ثبت می‌کند و پیگیری می‌شود."""

    id: Optional[int] = None
    subject_id: Optional[int] = None
    subject_name: str = ""
    topic_id: Optional[int] = None
    topic_name: str = ""
    kind: ProblemKind = ProblemKind.CONCEPTUAL_GAP
    title: str = ""
    description: str = ""
    #: شدت خودگزارشی ۱..۵ — از عملکرد محاسبه نمی‌شود.
    severity: int = 3
    status: ProblemStatus = ProblemStatus.OPEN
    #: پیوست اختیاری (عکس از دفتر، تصویر سؤال) — نگه‌داری می‌شود، خوانده
    #: نمی‌شود؛ اعداد و توضیح را خودت وارد می‌کنی.
    attachment_path: Optional[str] = None
    attachment_name: str = ""
    attachment_sha256: Optional[str] = None
    attachment_bytes: int = 0
    first_seen: Optional[_dt.date] = None
    last_seen: Optional[_dt.date] = None
    #: تعداد دفعاتی که این مشکل در آزمون‌ها دیده شده است.
    occurrences: int = 0
    resolution_note: str = ""
    created_at: Optional[_dt.datetime] = None
    updated_at: Optional[_dt.datetime] = None

    @property
    def is_open(self) -> bool:
        return self.status in {ProblemStatus.OPEN, ProblemStatus.IN_PROGRESS}


@dataclass
class LearningProblemEvent:
    """یک اقدام یا بروزرسانی روی یک مشکل یادگیری."""

    id: Optional[int] = None
    problem_id: Optional[int] = None
    at: Optional[_dt.datetime] = None
    #: kind: opened | progressed | resolved | relapsed | evidence
    kind: str = "progressed"
    note: str = ""


# ---------------------------------------------------------------------------
# بازبینی شبانه (بند ۱۶)
# ---------------------------------------------------------------------------


@dataclass
class NightlyChange:
    """یک تغییر در بازسازی برنامه با دلیل و تأثیر روی مهلت‌ها."""

    title: str
    reason: str
    deadline_impact: str = ""
    severity: str = "info"  # info | warning | critical


@dataclass
class NightlyReview:
    """بازبینی پایان روز و بازسازی روزهای بعد (بند ۱۶)."""

    date: Optional[_dt.date] = None
    planned_minutes: int = 0
    done_minutes: int = 0
    class_minutes: int = 0
    independent_minutes: int = 0
    completed: list[str] = field(default_factory=list)
    incomplete: list[str] = field(default_factory=list)
    better: list[str] = field(default_factory=list)
    worse: list[str] = field(default_factory=list)
    deadline_risks: list[str] = field(default_factory=list)
    capacity_risks: list[str] = field(default_factory=list)
    changes: list[NightlyChange] = field(default_factory=list)

    @property
    def completion_ratio(self) -> float:
        if self.planned_minutes <= 0:
            return 0.0
        return self.done_minutes / self.planned_minutes

    @property
    def has_blocking_issue(self) -> bool:
        return any(change.severity == "critical" for change in self.changes)


__all__ = [
    "Activity",
    "ActivityEvent",
    "ActivityState",
    "ActivityType",
    "AdvisorSuggestion",
    "Bottleneck",
    "ContentType",
    "DateStatus",
    "DeadlineKind",
    "DeadlineMilestone",
    "DeadlineSuggestion",
    "DeadlineType",
    "EnergyNeed",
    "ErrorCode",
    "ErrorRecord",
    "EventException",
    "ExamAttempt",
    "ExamKind",
    "ExamProfile",
    "ExamQuestion",
    "FeasibilityAction",
    "FinalStage",
    "FixedEvent",
    "FixedEventKind",
    "KonkurStage",
    "LearningProblem",
    "LearningProblemEvent",
    "MasteryLevel",
    "NightlyChange",
    "NightlyReview",
    "Placement",
    "ProblemKind",
    "ProblemStatus",
    "ReviewItem",
    "ReviewLog",
    "ReviewState",
    "Routine",
    "RoutineKind",
    "RoutineScope",
    "ScopeStatus",
    "SessionKind",
    "SessionTotals",
    "StudyPhase",
    "StudySession",
    "SyllabusChapterEdit",
    "SyllabusSection",
    "StudySessionRevision",
    "Subject",
    "Topic",
    "TopicDeadline",
    "TopicDeadlinePlan",
    "TrackKind",
    "UnplacedActivity",
    "WeeklyReport",
]
