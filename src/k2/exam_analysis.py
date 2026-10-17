"""ثبت آزمون، محاسبهٔ درصد و تحلیل خطا (سند تحقیق ۱، بخش ۴).

قاعده: **هیچ فرمول ثابتی برای همهٔ آزمون‌ها وجود ندارد**؛ فرمول از پروفایل
آزمون خوانده می‌شود (درصد خام یا درصد با نمرهٔ منفی).
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence

from .domain.enums import ErrorCode, ExamKind
from .domain.learning import remediation_for
from .domain.models import (
    Activity,
    ActivityType,
    DeadlineType,
    EnergyNeed,
    ErrorRecord,
    ExamAttempt,
    ExamProfile,
    ExamQuestion,
)


@dataclass
class AttemptResult:
    """نتیجهٔ محاسبهٔ نمرهٔ یک نوبت آزمون."""

    total: int
    correct: int
    wrong: int
    blank: int
    raw_score: float
    percentage: float
    formula_used: str
    notes: tuple[str, ...] = ()


def compute_attempt(
    *,
    total: int,
    correct: int,
    wrong: int,
    blank: int,
    profile: Optional[ExamProfile] = None,
    duration_minutes: int = 0,
) -> AttemptResult:
    """محاسبهٔ نمرهٔ یک نوبت آزمون بر اساس پروفایل."""
    notes: list[str] = []
    if total <= 0:
        return AttemptResult(
            total=total,
            correct=correct,
            wrong=wrong,
            blank=blank,
            raw_score=0.0,
            percentage=0.0,
            formula_used="none",
            notes=("تعداد سؤال مشخص نشده است؛ درصد محاسبه نشد.",),
        )

    if correct + wrong + blank != total:
        notes.append(
            f"مجموع درست/غلط/نزده ({correct + wrong + blank}) با تعداد سؤال "
            f"({total}) برابر نیست."
        )

    formula = profile.percentage_formula if profile else "raw"
    negative_ratio = profile.negative_marking_ratio if profile else 0.0

    raw_score = (correct / total) * 100.0

    if formula == "negative" and negative_ratio > 0:
        score = ((correct - wrong * negative_ratio) / total) * 100.0
        formula_used = f"negative({negative_ratio})"
        if score < 0:
            notes.append("نمرهٔ محاسبه‌شده منفی شد؛ در گزارش‌ها به‌صورت منفی نمایش داده می‌شود.")
    else:
        score = raw_score
        formula_used = "raw"
        if formula == "negative" and negative_ratio <= 0:
            notes.append(
                "فرمول «با نمرهٔ منفی» انتخاب شده بود ولی ضریب نمرهٔ منفی صفر است؛ "
                "درصد خام محاسبه شد."
            )

    if duration_minutes > 0:
        per_question = duration_minutes / total
        notes.append(f"میانگین زمان هر سؤال: {per_question:.1f} دقیقه.")

    return AttemptResult(
        total=total,
        correct=correct,
        wrong=wrong,
        blank=blank,
        raw_score=raw_score,
        percentage=score,
        formula_used=formula_used,
        notes=tuple(notes),
    )


@dataclass
class TopicWeakness:
    """شاخص ضعف یک مبحث = تعداد خطا × وزن اهمیت (سند ۱، بخش ۴.۳)."""

    topic_id: Optional[int]
    topic_name: str
    subject_name: str
    error_count: int = 0
    weight: float = 1.0
    blank_count: int = 0

    @property
    def weakness(self) -> float:
        return self.error_count * self.weight

    @property
    def blank_penalty(self) -> float:
        """نزده‌ها سیگنال سرعت هستند و جدا شمرده می‌شوند."""
        return self.blank_count * self.weight


@dataclass
class ErrorBreakdown:
    """تفکیک خطاها بر پایهٔ کد علت."""

    counts: dict[ErrorCode, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.counts.values())

    def top(self, limit: int = 3) -> list[tuple[ErrorCode, int]]:
        return sorted(self.counts.items(), key=lambda item: (-item[1], item[0].value))[:limit]

    def ratio(self, code: ErrorCode) -> float:
        if not self.total:
            return 0.0
        return self.counts.get(code, 0) / self.total


def build_error_breakdown(
    questions: Sequence[ExamQuestion], errors: Sequence[ErrorRecord] = ()
) -> ErrorBreakdown:
    """شمارش خطاها بر پایهٔ کد علت."""
    breakdown = ErrorBreakdown()
    for question in questions:
        if question.status == "wrong" and question.error_code is not None:
            breakdown.counts[question.error_code] = (
                breakdown.counts.get(question.error_code, 0) + 1
            )
    for error in errors:
        if error.code is not None:
            breakdown.counts[error.code] = breakdown.counts.get(error.code, 0) + 1
    return breakdown


def build_topic_weakness(
    questions: Sequence[ExamQuestion],
    *,
    topic_names: Optional[dict[int, tuple[str, str]]] = None,
    weights: Optional[dict[int, float]] = None,
) -> list[TopicWeakness]:
    """محاسبهٔ ضعف مبحث‌محور."""
    topic_names = topic_names or {}
    weights = weights or {}
    result: dict[int, TopicWeakness] = {}

    for question in questions:
        key = question.topic_id if question.topic_id is not None else -1
        if key not in result:
            subject_name, topic_name = topic_names.get(key, ("", "عمومی"))
            result[key] = TopicWeakness(
                topic_id=question.topic_id,
                topic_name=topic_name,
                subject_name=subject_name,
                weight=weights.get(key, 1.0),
            )
        entry = result[key]
        if question.status == "wrong":
            entry.error_count += 1
        elif question.status == "blank":
            entry.blank_count += 1

    return sorted(result.values(), key=lambda item: -item.weakness)


@dataclass
class RemediationPlan:
    """فعالیت‌های اصلاحی ساخته‌شده از خطاهای یک آزمون (ERR-02)."""

    activities: list[Activity] = field(default_factory=list)
    records: list[ErrorRecord] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def build_remediation(
    *,
    errors: Sequence[ErrorRecord],
    attempt: ExamAttempt,
    topic_names: Optional[dict[int, tuple[str, str]]] = None,
    now: Optional[_dt.datetime] = None,
) -> RemediationPlan:
    """از هر خطا یک فعالیت اصلاحی با مهلت و آزمون مجدد می‌سازد."""
    now = now or _dt.datetime.now()
    topic_names = topic_names or {}
    plan = RemediationPlan()

    grouped: dict[tuple[ErrorCode, Optional[int]], list[ErrorRecord]] = {}
    for error in errors:
        grouped.setdefault((error.code, error.topic_id), []).append(error)

    for (code, topic_id), group in grouped.items():
        subject_name, topic_name = topic_names.get(topic_id or -1, ("", "این مبحث"))
        remediation = remediation_for(code)
        title = remediation.title_template.format(topic=topic_name or "مبحث")
        deadline = now + _dt.timedelta(hours=remediation.deadline_hours)
        activity = Activity(
            title=title,
            type=remediation.activity_type,
            subject_id=group[0].subject_id,
            subject_name=subject_name,
            topic_id=topic_id,
            topic_name=topic_name,
            est_minutes=remediation.default_minutes,
            remaining_minutes=remediation.default_minutes,
            min_chunk=20,
            max_chunk=90,
            splittable=remediation.activity_type
            not in {ActivityType.TIMED_TEST, ActivityType.EXAM},
            deadline_type=DeadlineType.SOFT,
            deadline_at=deadline,
            energy_need=EnergyNeed.HIGH
            if remediation.activity_type == ActivityType.REMEDIATION
            else EnergyNeed.MEDIUM,
            origin=f"exam:{attempt.id}",
        )
        plan.activities.append(activity)
        for error in group:
            error.resolution_activity_id = None  # پس از ذخیرهٔ فعالیت پر می‌شود
            plan.records.append(error)
        plan.notes.append(
            f"{len(group)} خطای {code.label} در «{topic_name or 'مبحث عمومی'}» ⇒ "
            f"«{title}» با مهلت {remediation.deadline_hours} ساعت. "
            f"آزمون مجدد: {remediation.retest_description}."
        )

    return plan


@dataclass
class RepeatedErrorStat:
    """شاخص «خطای تکراری» (ERR-03)."""

    topic_id: Optional[int]
    topic_name: str
    code: ErrorCode
    occurrences: int
    last_seen: Optional[_dt.date]

    @property
    def is_repeated(self) -> bool:
        return self.occurrences >= 2


def repeated_errors(
    errors: Sequence[ErrorRecord],
    *,
    topic_names: Optional[dict[int, tuple[str, str]]] = None,
) -> list[RepeatedErrorStat]:
    """خطاهایی که بیش از یک‌بار تکرار شده‌اند."""
    topic_names = topic_names or {}
    buckets: dict[tuple[Optional[int], ErrorCode], list[ErrorRecord]] = {}
    for error in errors:
        buckets.setdefault((error.topic_id, error.code), []).append(error)

    stats: list[RepeatedErrorStat] = []
    for (topic_id, code), group in buckets.items():
        if len(group) < 2:
            continue
        subject_name, topic_name = topic_names.get(topic_id or -1, ("", "مبحث عمومی"))
        last_seen = max(
            (error.created_at.date() for error in group if error.created_at),
            default=None,
        )
        stats.append(
            RepeatedErrorStat(
                topic_id=topic_id,
                topic_name=topic_name,
                code=code,
                occurrences=len(group),
                last_seen=last_seen,
            )
        )
    stats.sort(key=lambda item: (-item.occurrences, item.topic_name))
    return stats


def exam_kind_label(kind: ExamKind) -> str:
    """برچسب نوع آزمون — گزارش آزمون مؤسسه با آزمون رسمی مخلوط نمی‌شود."""
    return {
        ExamKind.OFFICIAL: "رسمی",
        ExamKind.MOCK: "شبیه‌سازی",
        ExamKind.INSTITUTE: "مؤسسه",
        ExamKind.DIAGNOSTIC: "تشخیصی",
    }[kind]
