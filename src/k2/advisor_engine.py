"""موتور مشاور تطبیقی (سند تحقیق ۴).

چرخه: مصاحبه → سنجش مبحثی → تشخیص گلوگاه → فاز زمانی → تجویز → پایش.

این موتور **قاعده‌محور و توضیح‌پذیر** است؛ چت‌بات آزاد یا API بیرونی در
آن نقشی ندارد (NFR-02).
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Optional, Sequence

from .config import Settings
from .domain.enums import (
    ActivityType,
    Bottleneck,
    ErrorCode,
    MasteryLevel,
    StudyPhase,
)
from .domain.learning import (
    LearningActivityTemplate,
    prescription_matrix,
    recommended_methods,
    subject_default_content_type,
)
from .domain.models import (
    Activity,
    AdvisorSuggestion,
    DeadlineType,
    EnergyNeed,
    ErrorRecord,
    ExamAttempt,
    ExamQuestion,
    Topic,
)

# ---------------------------------------------------------------------------
# فاز زمانی
# ---------------------------------------------------------------------------

PHASE_LABELS: dict[StudyPhase, str] = {
    StudyPhase.FOUNDATION: "بنیان",
    StudyPhase.CONSOLIDATION: "تثبیت",
    StudyPhase.INTENSIFICATION: "تشدید",
    StudyPhase.SUMMARIZATION: "جمع‌بندی",
    StudyPhase.FINAL_DAYS: "روزهای آخر",
    StudyPhase.UNKNOWN: "نامشخص",
}


def determine_phase(
    days_until_exam: Optional[int], settings: Optional[Settings] = None
) -> StudyPhase:
    """فاز زمانی بر پایهٔ فاصله تا آزمون.

    مرزها **فرضیهٔ محصول [H]** هستند و قابل تنظیم‌اند (سند ۴، بخش ۱.۴).
    """
    settings = settings or Settings()
    a = settings.advisor
    if days_until_exam is None:
        return StudyPhase.UNKNOWN
    if days_until_exam <= 0:
        return StudyPhase.FINAL_DAYS
    if days_until_exam <= a.phase_final_days:
        return StudyPhase.FINAL_DAYS
    if days_until_exam <= a.phase_summarization_days:
        return StudyPhase.SUMMARIZATION
    if days_until_exam <= a.phase_intensification_days:
        return StudyPhase.INTENSIFICATION
    if days_until_exam <= a.phase_consolidation_days:
        return StudyPhase.CONSOLIDATION
    return StudyPhase.FOUNDATION


# ---------------------------------------------------------------------------
# سنجش سطح مبحث
# ---------------------------------------------------------------------------


@dataclass
class MasteryEvidence:
    """یک شاهد عملکردی برای سنجش تسلط."""

    at: _dt.date
    source: str  # diagnostic | exam | review | transfer | self_report
    score: float  # ۰..۱
    note: str = ""


@dataclass
class MasteryAssessment:
    """نتیجهٔ سنجش تسلط یک مبحث (MAST-01)."""

    topic_id: Optional[int]
    topic_name: str
    level: MasteryLevel
    confidence: float
    reasons: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        return self.level.label


def assess_mastery(
    *,
    topic_id: Optional[int],
    topic_name: str,
    evidence: Sequence[MasteryEvidence],
    self_assessed: Optional[int] = None,
    settings: Optional[Settings] = None,
) -> MasteryAssessment:
    """تسلط را از **عملکرد** استنباط می‌کند، نه از حس دانش‌آموز.

    خودسنجی تنها در صورتی وارد محاسبه می‌شود که شاهد عملکردی وجود نداشته
    باشد و آن‌وقت با وزن کمتر (سند ۱، اصل ۵؛ سند ۴، بخش ۱.۲).
    """
    settings = settings or Settings()
    a = settings.advisor
    reasons: list[str] = []

    performance = [e for e in evidence if e.source != "self_report"]
    if performance:
        # شواهد جدیدتر وزن بیشتری دارند.
        ordered = sorted(performance, key=lambda e: e.at)
        weights = [1.0 + 0.5 * index for index in range(len(ordered))]
        total_weight = sum(weights)
        score = sum(e.score * w for e, w in zip(ordered, weights)) / total_weight
        confidence = min(1.0, 0.4 + 0.15 * len(performance))
        sources = {e.source for e in performance}
        if "transfer" in sources:
            reasons.append("شاهد انتقال به سؤال جدید وجود دارد.")
        if "review" in sources:
            reasons.append("شاهد بازیابی فعال وجود دارد.")
        if "exam" in sources:
            reasons.append("شاهد آزمون وجود دارد.")
        if "diagnostic" in sources:
            reasons.append("شاهد آزمون تشخیصی وجود دارد.")
        if "self_report" in {e.source for e in evidence}:
            reasons.append("خودسنجی ثبت شده اما وزن کمتری دارد.")
    elif self_assessed is not None:
        score = max(0.0, min(1.0, self_assessed / 4.0))
        confidence = 0.25
        reasons.append("فقط خودسنجی در دسترس است؛ اطمینان پایین است.")
    else:
        score = 0.0
        confidence = 0.1
        reasons.append("شاهدی برای این مبحث ثبت نشده است.")

    if score <= a.mastery_l1_max:
        level = MasteryLevel.L1 if score > 0 else MasteryLevel.L0
    elif score <= a.mastery_l2_max:
        level = MasteryLevel.L2
    elif score <= a.mastery_l3_max:
        level = MasteryLevel.L3
    else:
        level = MasteryLevel.L4

    if level == MasteryLevel.L0:
        reasons.append("عملکرد ثبت‌شده‌ای وجود ندارد؛ مبحث «ندیده» فرض شد.")

    return MasteryAssessment(
        topic_id=topic_id,
        topic_name=topic_name,
        level=level,
        confidence=confidence,
        reasons=tuple(reasons),
    )


# ---------------------------------------------------------------------------
# تشخیص گلوگاه
# ---------------------------------------------------------------------------


@dataclass
class BottleneckAssessment:
    """گلوگاه یک درس به‌همراه شواهد (ADV-01)."""

    subject_name: str
    bottleneck: Bottleneck
    evidence: tuple[str, ...] = ()
    score: float = 0.0


def detect_bottleneck(
    *,
    subject_name: str,
    errors: Sequence[ErrorRecord],
    questions: Sequence[ExamQuestion] = (),
    review_grades: Sequence[int] = (),
    adherence: Optional[float] = None,
    debt_ratio: Optional[float] = None,
    settings: Optional[Settings] = None,
) -> BottleneckAssessment:
    """تشخیص گلوگاه اصلی یک درس (سند ۴، بخش ۱.۳).

    هیچ تشخیص پزشکی یا روان‌شناختی انجام نمی‌شود؛ «فشار» فقط یک برچسب
    توصیفی از دادهٔ خودگزارشی است.
    """
    settings = settings or Settings()
    evidence: list[str] = []
    scores: dict[Bottleneck, float] = {}

    if errors:
        total = len(errors)
        counts: dict[ErrorCode, int] = {}
        for error in errors:
            counts[error.code] = counts.get(error.code, 0) + 1

        knowledge = counts.get(ErrorCode.E1, 0) + counts.get(ErrorCode.E2, 0)
        method = counts.get(ErrorCode.E3, 0) + counts.get(ErrorCode.E9, 0)
        accuracy = counts.get(ErrorCode.E4, 0) + counts.get(ErrorCode.E5, 0)
        speed = counts.get(ErrorCode.E6, 0)
        comprehension = counts.get(ErrorCode.E7, 0)
        guessing = counts.get(ErrorCode.E8, 0)

        scores[Bottleneck.KNOWLEDGE] = knowledge / total
        scores[Bottleneck.METHOD] = method / total
        scores[Bottleneck.ACCURACY] = accuracy / total
        scores[Bottleneck.SPEED] = speed / total
        scores[Bottleneck.RETENTION] = guessing / total
        if comprehension:
            evidence.append("خطای «برداشت اشتباه از سؤال» ثبت شده است.")

        if knowledge:
            evidence.append(
                f"{knowledge} خطای E1/E2 (ضعف مفهومی/فراموشی) از {total} خطا."
            )
        if method:
            evidence.append(f"{method} خطای E3/E9 (ضعف روش حل/تشخیص تیپ).")
        if accuracy:
            evidence.append(f"{accuracy} خطای E4/E5 (محاسباتی/بی‌دقتی).")
        if speed:
            evidence.append(f"{speed} خطای E6 (کمبود زمان).")

    if questions:
        blanks = sum(1 for q in questions if q.status == "blank")
        if blanks:
            scores[Bottleneck.SPEED] = scores.get(Bottleneck.SPEED, 0) + blanks / max(
                1, len(questions)
            )
            evidence.append(f"{blanks} سؤال نزده شده است.")

    if review_grades:
        average = sum(review_grades) / (4.0 * len(review_grades))
        if average < 0.6:
            scores[Bottleneck.RETENTION] = scores.get(Bottleneck.RETENTION, 0) + (
                0.6 - average
            )
            evidence.append(
                f"میانگین نمرهٔ مرورهای اخیر {average:.0%} است؛ ماندگاری ضعیف است."
            )

    if adherence is not None and adherence < 0.6:
        scores[Bottleneck.EXECUTION] = 0.6 - adherence
        evidence.append(f"نرخ تحقق برنامه {adherence:.0%} است؛ اجرای برنامه ضعیف است.")

    if debt_ratio is not None and debt_ratio > 0.7:
        scores[Bottleneck.EXECUTION] = scores.get(Bottleneck.EXECUTION, 0) + 0.2
        evidence.append("نسبت بدهی بالای ۰٫۷ است؛ فشار اجرایی وجود دارد.")

    if not scores:
        return BottleneckAssessment(
            subject_name=subject_name,
            bottleneck=Bottleneck.NONE,
            evidence=("دادهٔ کافی برای تشخیص گلوگاه وجود ندارد.",),
            score=0.0,
        )

    best = max(scores.items(), key=lambda item: (item[1], item[0].value))
    if best[1] <= 0:
        return BottleneckAssessment(
            subject_name=subject_name,
            bottleneck=Bottleneck.NONE,
            evidence=("شواهد کافی برای تعیین گلوگاه نبود.",),
            score=0.0,
        )

    return BottleneckAssessment(
        subject_name=subject_name,
        bottleneck=best[0],
        evidence=tuple(evidence),
        score=best[1],
    )


# ---------------------------------------------------------------------------
# تجویز
# ---------------------------------------------------------------------------


@dataclass
class Prescription:
    """تجویز یک مبحث بر پایهٔ فاز × سطح (سند ۴، بخش ۱.۵)."""

    topic_id: Optional[int]
    topic_name: str
    subject_name: str
    phase: StudyPhase
    level: MasteryLevel
    activities: list[Activity] = field(default_factory=list)
    methods: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


def prescribe_for_topic(
    *,
    topic: Topic,
    subject_name: str,
    phase: StudyPhase,
    level: MasteryLevel,
    deadline: Optional[_dt.datetime] = None,
    settings: Optional[Settings] = None,
) -> Prescription:
    """ساخت فعالیت‌های پیشنهادی برای یک مبحث."""
    settings = settings or Settings()
    templates = prescription_matrix(phase, level)
    content_type = topic.content_type or subject_default_content_type(subject_name)
    methods = recommended_methods(content_type)

    activities: list[Activity] = []
    for template in templates:
        activities.append(
            Activity(
                title=template.title_template.format(topic=topic.name or "مبحث"),
                type=template.activity_type,
                subject_id=topic.subject_id,
                subject_name=subject_name,
                topic_id=topic.id,
                topic_name=topic.name,
                est_minutes=template.default_minutes,
                remaining_minutes=template.default_minutes,
                min_chunk=20,
                max_chunk=90,
                splittable=template.activity_type
                not in {ActivityType.TIMED_TEST, ActivityType.EXAM},
                deadline_type=DeadlineType.SOFT,
                deadline_at=deadline,
                energy_need=EnergyNeed(template.energy)
                if template.energy in {e.value for e in EnergyNeed}
                else EnergyNeed.MEDIUM,
                origin="advisor",
            )
        )

    notes = (
        f"فاز «{PHASE_LABELS[phase]}» × سطح «{level.label}».",
        f"نوع محتوا: {content_type.label}.",
        f"معیار اتمام هر فعالیت: {templates[0].completion_criteria}"
        if templates
        else "برای این خانهٔ ماتریس الگوی فعالیتی تعریف نشده است.",
    )
    return Prescription(
        topic_id=topic.id,
        topic_name=topic.name,
        subject_name=subject_name,
        phase=phase,
        level=level,
        activities=activities,
        methods=methods,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# «کار بعدی»
# ---------------------------------------------------------------------------


def next_action(
    *,
    topic_name: str,
    level: MasteryLevel,
    phase: StudyPhase,
    bottleneck: Bottleneck,
    evidence: Sequence[str] = (),
) -> AdvisorSuggestion:
    """یک اقدام اولویت‌دار با **یک دلیل کوتاه** (ADV-03)."""
    if bottleneck == Bottleneck.KNOWLEDGE:
        title = f"بازآموزی {topic_name}"
        reason = f"گلوگاه «دانش/مفهوم» است: {evidence[0]}" if evidence else (
            f"گلوگاه «دانش/مفهوم» در «{topic_name}» است."
        )
    elif bottleneck == Bottleneck.METHOD:
        title = f"تمرین تیپ‌محور {topic_name}"
        reason = "گلوگاه «روش حل/تیپ» است؛ تمرین هم‌تیپ لازم است."
    elif bottleneck == Bottleneck.SPEED:
        title = f"تست زمان‌دار {topic_name}"
        reason = "گلوگاه «سرعت» است؛ سؤال‌های انتهایی نزده می‌شوند."
    elif bottleneck == Bottleneck.ACCURACY:
        title = f"تمرین دقیق {topic_name}"
        reason = "گلوگاه «دقت» است؛ خطاهای محاسباتی/بی‌دقتی پرتکرار است."
    elif bottleneck == Bottleneck.RETENTION:
        title = f"مرور فاصله‌دار {topic_name}"
        reason = "ماندگاری ضعیف است؛ بازیابی فعال باید بیشتر شود."
    elif bottleneck == Bottleneck.EXECUTION:
        title = f"کار کوتاه {topic_name}"
        reason = "اجرای برنامه ضعیف است؛ کار را کوچک‌تر کنید."
    else:
        title = f"تمرین مستقل {topic_name}"
        reason = f"سطح فعلی {level.label} در فاز «{PHASE_LABELS[phase]}» است."

    return AdvisorSuggestion(
        activity_id=None,
        title=title,
        reason=reason,
        action_type="activity",
        score=1.0,
    )
