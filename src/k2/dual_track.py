"""دو مسیر مستقل هر مبحث: کنکور و نهایی/مدرک (بند ۱۳).

هر مبحث دو مسیر **متفاوت اما همبسته** دارد:

* مسیر کنکور: مطالعهٔ مفهومی → تست تدریس → تست زمان‌دار → تحلیل گزینه‌ها
  → مرور خطاها → آزمون ترکیبی.
* مسیر نهایی: مطالعهٔ دقیق کتاب → تعریف‌ها و روابط → جزئیات → تمرین تشریحی
  → سؤال‌های نمونهٔ معتبر → بررسی کامل‌بودن و نشانه‌گذاری → آزمون جامع نهایی.

قانون سخت محصول: **هیچ مسیری جای مسیر دیگر را نمی‌گیرد.** تمرین تشریحی
به آمادگی تست کمک می‌کند، اما تست زمان‌دار را جایگزین نمی‌کند و برعکس.
هر پیشرفت بین دو پله نیازمند **شاهد** است؛ تیک زدن تقویمی پذیرفته نیست.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

from .domain.enums import (
    ContentType,
    FinalStage,
    KonkurStage,
    MasteryLevel,
    TrackKind,
)
from .domain.models import LearningEvidence, Topic

# ---------------------------------------------------------------------------
# نردبان هر مسیر
# ---------------------------------------------------------------------------

KONKUR_LADDER: tuple[KonkurStage, ...] = (
    KonkurStage.CONCEPTUAL,
    KonkurStage.TEACHING_TEST,
    KonkurStage.TIMED_TEST,
    KonkurStage.OPTION_ANALYSIS,
    KonkurStage.ERROR_REVIEW,
    KonkurStage.MIXED_EXAM,
)

FINAL_LADDER: tuple[FinalStage, ...] = (
    FinalStage.TEXTBOOK_STUDY,
    FinalStage.DEFINITIONS,
    FinalStage.DETAIL_MAP,
    FinalStage.DESCRIPTIVE_PRACTICE,
    FinalStage.SAMPLE_QUESTIONS,
    FinalStage.COMPLETENESS_CHECK,
    FinalStage.MOCK_FINAL,
)

#: منبع شاهدِ مورد انتظار برای هر پلهٔ مسیر کنکور.
KONKUR_EVIDENCE_SOURCE: dict[KonkurStage, str] = {
    KonkurStage.CONCEPTUAL: "diagnostic",
    KonkurStage.TEACHING_TEST: "teaching_test",
    KonkurStage.TIMED_TEST: "timed_test",
    KonkurStage.OPTION_ANALYSIS: "option_analysis",
    KonkurStage.ERROR_REVIEW: "error_review",
    KonkurStage.MIXED_EXAM: "mixed_exam",
}

#: منبع شاهدِ مورد انتظار برای هر پلهٔ مسیر نهایی.
FINAL_EVIDENCE_SOURCE: dict[FinalStage, str] = {
    FinalStage.TEXTBOOK_STUDY: "diagnostic",
    FinalStage.DEFINITIONS: "definitions",
    FinalStage.DETAIL_MAP: "detail_map",
    FinalStage.DESCRIPTIVE_PRACTICE: "descriptive_practice",
    FinalStage.SAMPLE_QUESTIONS: "sample_questions",
    FinalStage.COMPLETENESS_CHECK: "completeness_check",
    FinalStage.MOCK_FINAL: "mock_final",
}

#: فعالیت متناظر هر پله در سیستم فعالیت‌ها (برای ساخت برنامه).
KONKUR_ACTIVITY: dict[KonkurStage, str] = {
    KonkurStage.CONCEPTUAL: "processing",
    KonkurStage.TEACHING_TEST: "independent_practice",
    KonkurStage.TIMED_TEST: "timed_test",
    KonkurStage.OPTION_ANALYSIS: "test_analysis",
    KonkurStage.ERROR_REVIEW: "remediation",
    KonkurStage.MIXED_EXAM: "mixed_practice",
}

FINAL_ACTIVITY: dict[FinalStage, str] = {
    FinalStage.TEXTBOOK_STUDY: "processing",
    FinalStage.DEFINITIONS: "processing",
    FinalStage.DETAIL_MAP: "summary",
    FinalStage.DESCRIPTIVE_PRACTICE: "independent_practice",
    FinalStage.SAMPLE_QUESTIONS: "independent_practice",
    FinalStage.COMPLETENESS_CHECK: "rework",
    FinalStage.MOCK_FINAL: "timed_test",
}

#: کمینهٔ نمرهٔ شاهد برای تأیید هر پله [H] — قابل تنظیم در تنظیمات.
DEFAULT_STAGE_EVIDENCE_SCORE = 0.70

#: پیام ثابتِ قانون «جایگزینی ممنوع».
NO_SUBSTITUTION_NOTE = (
    "تمرین تشریحی مسیر نهایی به آمادگی تست کمک می‌کند ولی تست زمان‌دارِ "
    "مسیر کنکور را جایگزین نمی‌کند؛ برعکس هم صدق می‌کند."
)


@dataclass
class TrackProgress:
    """پیشرفت یک مبحث در یک مسیر."""

    track: TrackKind
    stage: str
    stage_label: str
    index: int
    total_stages: int
    next_stage: Optional[str] = None
    next_stage_label: str = ""
    evidence_count: int = 0
    #: آیا شاهد کافی برای عبور از پلهٔ فعلی ثبت شده است؟
    evidence_ready: bool = False
    missing_evidence: str = ""
    blocked_reason: str = ""
    completed: bool = False

    @property
    def progress_percent(self) -> float:
        if self.total_stages <= 0:
            return 0.0
        return round(100.0 * self.index / self.total_stages, 1)

    @property
    def ladder_text(self) -> str:
        return f"{self.index + 1} از {self.total_stages}"


@dataclass
class DualTrackView:
    """نمای هر دو مسیر یک مبحث به‌همراه قانون جایگزینی."""

    topic_id: int
    topic_name: str = ""
    konkur: Optional[TrackProgress] = None
    final: Optional[TrackProgress] = None
    warnings: list[str] = field(default_factory=list)

    @property
    def both_tracks_ready(self) -> bool:
        return bool(
            self.konkur
            and self.final
            and self.konkur.evidence_ready
            and self.final.evidence_ready
        )

    @property
    def substitution_risk(self) -> str:
        """اگر یک مسیر جلوتر باشد، هشدار جایگزینی داده می‌شود."""
        if not self.konkur or not self.final:
            return ""
        gap = abs(self.konkur.index - self.final.index)
        if gap < 2:
            return ""
        ahead = "کنکور" if self.konkur.index > self.final.index else "نهایی"
        behind = "نهایی" if ahead == "کنکور" else "کنکور"
        return (
            f"مسیر {ahead} {gap} پله جلوتر است؛ مراقب باش کار مسیر {behind} را "
            f"جایگزین نکنی. {NO_SUBSTITUTION_NOTE}"
        )


def ladder_for(track: TrackKind) -> tuple:
    return KONKUR_LADDER if track == TrackKind.KONKUR else FINAL_LADDER


def stage_label(stage: str) -> str:
    """برچسب فارسی یک پله از هر مسیر."""
    try:
        return KonkurStage(stage).label
    except ValueError:
        pass
    try:
        return FinalStage(stage).label
    except ValueError:
        return stage


def evidence_source_for(track: TrackKind, stage: str) -> str:
    table = KONKUR_EVIDENCE_SOURCE if track == TrackKind.KONKUR else FINAL_EVIDENCE_SOURCE
    try:
        key = KonkurStage(stage) if track == TrackKind.KONKUR else FinalStage(stage)
    except ValueError:
        return "diagnostic"
    return table.get(key, "diagnostic")


def activity_type_for(track: TrackKind, stage: str) -> str:
    table = KONKUR_ACTIVITY if track == TrackKind.KONKUR else FINAL_ACTIVITY
    try:
        key = KonkurStage(stage) if track == TrackKind.KONKUR else FinalStage(stage)
    except ValueError:
        return "processing"
    return table.get(key, "processing")


def track_progress(
    topic: Topic,
    track: TrackKind,
    evidences: Sequence[LearningEvidence],
    *,
    min_score: float = DEFAULT_STAGE_EVIDENCE_SCORE,
) -> TrackProgress:
    """پیشرفت یک مسیر را از روی پلهٔ ذخیره‌شده و شواهد ثبت‌شده می‌سازد."""
    ladder = ladder_for(track)
    current = topic.konkur_stage if track == TrackKind.KONKUR else topic.final_stage
    try:
        index = next(i for i, stage in enumerate(ladder) if stage.value == current)
    except StopIteration:
        index = 0
    expected_source = evidence_source_for(track, ladder[index].value)
    matching = [
        e
        for e in evidences
        if e.topic_id == topic.id and e.source == expected_source and e.score >= min_score
    ]
    evidence_ready = bool(matching)
    next_stage = ladder[index + 1] if index + 1 < len(ladder) else None
    progress = TrackProgress(
        track=track,
        stage=ladder[index].value,
        stage_label=ladder[index].label,
        index=index,
        total_stages=len(ladder),
        next_stage=next_stage.value if next_stage else None,
        next_stage_label=next_stage.label if next_stage else "",
        evidence_count=len(matching),
        evidence_ready=evidence_ready,
        completed=index + 1 >= len(ladder) and evidence_ready,
    )
    if not evidence_ready:
        progress.missing_evidence = (
            f"برای تأیید پلهٔ «{ladder[index].label}» به شاهد «{expected_source}» "
            f"با نمرهٔ حداقل {min_score:.0%} نیاز است."
        )
    return progress


def dual_track_view(
    topic: Topic,
    evidences: Sequence[LearningEvidence],
    *,
    min_score: float = DEFAULT_STAGE_EVIDENCE_SCORE,
) -> DualTrackView:
    """هر دو مسیر یک مبحث."""
    view = DualTrackView(topic_id=int(topic.id or 0), topic_name=topic.name)
    view.konkur = track_progress(topic, TrackKind.KONKUR, evidences, min_score=min_score)
    view.final = track_progress(topic, TrackKind.FINAL, evidences, min_score=min_score)
    risk = view.substitution_risk
    if risk:
        view.warnings.append(risk)
    for progress in (view.konkur, view.final):
        if progress and progress.missing_evidence:
            view.warnings.append(
                f"مسیر {progress.track.label}: {progress.missing_evidence}"
            )
    return view


def advance_stage(
    topic: Topic,
    track: TrackKind,
    evidence: LearningEvidence,
    *,
    min_score: float = DEFAULT_STAGE_EVIDENCE_SCORE,
) -> tuple[bool, str]:
    """اگر شاهد کافی باشد، یک پله جلو می‌رود.

    خروجی: ``(تغییر_کرد, پیام)``. بدون شاهد، هیچ پیشرفتی ثبت نمی‌شود.
    """
    if evidence.topic_id != topic.id:
        return False, "شاهد به این مبحث وصل نیست."
    if evidence.score < min_score:
        return False, (
            f"نمرهٔ شاهد ({evidence.score:.0%}) کمتر از حد لازم "
            f"({min_score:.0%}) است؛ پله تأیید نشد."
        )
    ladder = ladder_for(track)
    current = topic.konkur_stage if track == TrackKind.KONKUR else topic.final_stage
    try:
        index = next(i for i, stage in enumerate(ladder) if stage.value == current)
    except StopIteration:
        return False, "پلهٔ فعلی در نردبان شناخته نشد."
    expected = evidence_source_for(track, ladder[index].value)
    if evidence.source != expected:
        return False, (
            f"این شاهد برای پلهٔ «{ladder[index].label}» کافی نیست؛ "
            f"منبع مورد انتظار «{expected}» است."
        )
    if index + 1 >= len(ladder):
        return False, "این مسیر به آخرین پله رسیده است."
    next_stage = ladder[index + 1]
    if track == TrackKind.KONKUR:
        topic.konkur_stage = next_stage.value
        topic.konkur_evidence_id = evidence.id
    else:
        topic.final_stage = next_stage.value
        topic.final_evidence_id = evidence.id
    return True, f"پلهٔ «{next_stage.label}» با شاهد تأیید شد."


def regression_after_failure(
    topic: Topic,
    track: TrackKind,
    *,
    score: float,
    min_score: float = DEFAULT_STAGE_EVIDENCE_SCORE,
) -> str:
    """اگر شاهد جدید ضعیف باشد، به پلهٔ قبل برمی‌گردد (بدون حذف تاریخچه)."""
    if score >= min_score:
        return ""
    ladder = ladder_for(track)
    current = topic.konkur_stage if track == TrackKind.KONKUR else topic.final_stage
    try:
        index = next(i for i, stage in enumerate(ladder) if stage.value == current)
    except StopIteration:
        return ""
    if index <= 0:
        return ""
    previous = ladder[index - 1]
    if track == TrackKind.KONKUR:
        topic.konkur_stage = previous.value
    else:
        topic.final_stage = previous.value
    return (
        f"نمرهٔ شاهد ({score:.0%}) کمتر از حد لازم بود؛ مبحث به پلهٔ "
        f"«{previous.label}» برگشت. تاریخچهٔ شواهد دست‌نخورده می‌ماند."
    )


def missing_steps(
    topic: Topic, evidences: Sequence[LearningEvidence]
) -> list[str]:
    """گام‌های ناقص هر دو مسیر — ورودی صفحهٔ «مباحث» و بازبینی شبانه."""
    messages: list[str] = []
    for track in (TrackKind.KONKUR, TrackKind.FINAL):
        progress = track_progress(topic, track, evidences)
        if progress.missing_evidence:
            messages.append(f"{track.label}: {progress.missing_evidence}")
    return messages


def stage_for_content_type(
    track: TrackKind, content_type: ContentType
) -> str:
    """پلهٔ پیشنهادی شروع بر پایهٔ نوع محتوا — فقط نقطهٔ شروع، نه قانون."""
    if track == TrackKind.KONKUR:
        return KonkurStage.CONCEPTUAL.value
    if content_type in {ContentType.MEMORIZATION, ContentType.VOCABULARY}:
        return FinalStage.DEFINITIONS.value
    return FinalStage.TEXTBOOK_STUDY.value


def mastery_ceiling(mastery: MasteryLevel) -> int:
    """سطح تسلط به عدد برای مقایسه با پله‌ها."""
    return int(mastery.value) if isinstance(mastery, MasteryLevel) else 0


__all__ = [
    "DEFAULT_STAGE_EVIDENCE_SCORE",
    "FINAL_ACTIVITY",
    "FINAL_EVIDENCE_SOURCE",
    "FINAL_LADDER",
    "KONKUR_ACTIVITY",
    "KONKUR_EVIDENCE_SOURCE",
    "KONKUR_LADDER",
    "NO_SUBSTITUTION_NOTE",
    "DualTrackView",
    "TrackProgress",
    "activity_type_for",
    "advance_stage",
    "dual_track_view",
    "evidence_source_for",
    "ladder_for",
    "mastery_ceiling",
    "missing_steps",
    "regression_after_failure",
    "stage_for_content_type",
    "stage_label",
    "track_progress",
]
