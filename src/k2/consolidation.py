"""موتور تثبیت حافظه — نردبان تثبیت، مدل DSR و پیش‌بینی ماندگاری.

این موتور قلب «مشاور واقعی» محصول است. سه قابلیت کلیدی:

1. **مدل حافظهٔ DSR** (سختی، پایداری، بازیابی‌پذیری) — برگفته از مدل FSRS/DSR:
   ``R(t,S) = (1 + 19t/(81S))^(-0.5)``؛ پایداری S روزهایی است که طول
   می‌کشد بازیابی‌پذیری به ۹۰٪ برسد. هر مرور موفق پایداری را ضربی افزایش
   می‌دهد و مرور در وضعیت «نزدیک به فراموشی» رشد بیشتری می‌دهد
   (دشواری‌های مطلوب؛ Bjork & Bjork 1992).
2. **نردبان تثبیت** — هر مبحث برای «تثبیت‌شده» اعلام شدن باید شواهد
   عملکردیِ هر پله را بدهد: بازیابی اولیه (≤۲۴ ساعت، پس از خواب)،
   بازیابی فاصله‌دار، بازیابی تأخیری، انتقال/ترکیبی، سپس نگهداری.
   این ساختار از تثبیت سیناپسی/سیستمی (Dudai) و اثر آزمون
   (Roediger & Karpicke) می‌آید.
3. **پیش‌بینی ماندگاری و امکان‌سنجی** — با پایداری فعلی هر مبحث،
   احتمال یادآوری در روز آزمون محاسبه و اگر کمتر از هدف باشد،
   برنامه هشدار می‌دهد و مرور اصلاحی می‌گذارد.

همهٔ ضرایب و آستانه‌ها **فرضیهٔ محصول [H]** هستند و در ``ConsolidationSettings``
قابل تنظیم‌اند؛ اعداد شواهدی (مثل نسبت ۱۹/۸۱ در منحنی فراموشی) ثابت مدل‌اند
و برچسب پژوهش دارند.
"""

from __future__ import annotations

import datetime as _dt
import math
from dataclasses import dataclass, field
from typing import Optional, Sequence

from .config import Settings
from .domain.enums import ReviewState
from .domain.models import ReviewItem

# ---------------------------------------------------------------------------
# مدل حافظهٔ DSR
# ---------------------------------------------------------------------------

#: ضرایب منحنی فراموشی FSRS/DSR — ثابتِ مدل، نه فرضیهٔ محصول.
FORGETTING_FACTOR = 19.0 / 81.0
FORGETTING_DECAY = -0.5


def retrievability(days: float, stability: float) -> float:
    """احتمال بازیابی موفق پس از ``days`` روز با پایداری ``stability``.

    ``R(t,S) = (1 + 19t/(81S))^-0.5`` — تعریف مدل DSR/FSRS: در ``t = S``
    دقیقاً ۰٫۹ برمی‌گردد.
    """
    if stability <= 0:
        return 0.0
    days = max(0.0, days)
    return (1.0 + FORGETTING_FACTOR * days / stability) ** FORGETTING_DECAY


def days_until_retrievability(target: float, stability: float) -> float:
    """چند روز طول می‌کشد بازیابی‌پذیری به ``target`` برسد؟

    حل معکوس ``R(t,S) = (1 + f·t/S)^-0.5`` برای t:
    ``t = (target^(1/decay) − 1) · S / f`` که برای target=۰٫۹ دقیقاً S می‌شود.
    """
    if stability <= 0:
        return 0.0
    target = min(max(target, 1e-6), 0.999999)
    return stability * (target ** (1.0 / FORGETTING_DECAY) - 1.0) / FORGETTING_FACTOR


@dataclass(frozen=True)
class DSRWeights:
    """ضرایب رشد پایداری [H] — الهام‌گرفته از FSRS-4.5 ولی ساده‌شده.

    مقادیر پایه از FSRS گرفته شده‌اند؛ برای کنکور با دادهٔ واقعی کاربر
    باید بازکالیبره شوند (مثل خواستهٔ optimization در FSRS).
    """

    #: پایداری اولیه پس از نخستین موفق (ترتیب نمرهٔ ۰..۴)
    initial_stability: tuple[float, float, float, float, float] = (
        0.3, 0.6, 1.4, 2.4, 3.6,
    )
    #: ضریب رشد پایه، تورم سختی، پاداش بازیابی سخت
    growth_base: float = 1.85
    difficulty_damping: float = 0.16
    hard_retrieval_bonus: float = 0.80
    #: پاداش/تعدیل نمرهٔ ۴ و ۲
    easy_bonus: float = 1.30
    #: پس از فراموشی، پایداری به این کسر از مقدار قبلی سقش می‌کند.
    lapse_recovery: float = 0.35


DEFAULT_DSR_WEIGHTS = DSRWeights()


def initial_stability(grade: int, weights: DSRWeights = DEFAULT_DSR_WEIGHTS) -> float:
    """پایداری اولیهٔ یک مبحث تازه بر پایهٔ نمرهٔ نخستین بازیابی."""
    grade = max(0, min(4, grade))
    return weights.initial_stability[grade]


def stability_after_success(
    *,
    stability: float,
    difficulty: float,
    retrievability_now: float,
    grade: int,
    weights: DSRWeights = DEFAULT_DSR_WEIGHTS,
) -> float:
    """پایداری تازه پس از یک مرور موفق (مدل ضربی ساده‌شده).

    رشد = پایه × (۱۱ − سختی) × S^(−تورم) × (exp(پاداش×(۱−R)) − ۱) × تعدیل نمره
    نکتهٔ کلیدی: هر چه بازیابی در لحظهٔ مرور سخت‌تر (R کمتر) بوده، رشد بیشتر
    — دقیقاً پیش‌بینی «دشواری‌های مطلوب».
    """
    difficulty = min(max(difficulty, 1.0), 10.0)
    grade = max(2, min(4, grade))
    retrievability_now = min(max(retrievability_now, 0.01), 0.999)
    base = weights.growth_base
    difficulty_term = (11.0 - difficulty) / 10.0
    damping_term = max(0.05, stability) ** (-weights.difficulty_damping)
    bonus_term = math.exp(weights.hard_retrieval_bonus * (1.0 - retrievability_now)) - 1.0
    grade_term = weights.easy_bonus if grade == 4 else 1.0
    growth = base * difficulty_term * damping_term * bonus_term * grade_term
    return max(0.5, stability * (1.0 + growth))


def stability_after_lapse(
    stability: float, weights: DSRWeights = DEFAULT_DSR_WEIGHTS
) -> float:
    """پس از فراموشی، پایداری سق می‌کند ولی صفر نمی‌شود (یادگیری مجدد سریع‌تر)."""
    return max(0.5, stability * weights.lapse_recovery)


def difficulty_update(
    difficulty: float, grade: int, mean_reversion: float = 0.10
) -> float:
    """سختی پس از یک مرور؛ با میانگرایی به مقدار متوسط (جلوگیری از ease hell)."""
    grade = max(0, min(4, grade))
    delta = (3.0 - grade) * 0.45
    target = 3.0 + delta
    difficulty = difficulty + mean_reversion * (target - difficulty)
    return min(max(difficulty, 1.0), 10.0)


def next_interval_days(
    *,
    stability: float,
    target_retention: float = 0.90,
    days_to_exam: Optional[int] = None,
    spacing_ratio: float = 0.15,
    max_interval: float = 365.0,
) -> float:
    """فاصلهٔ مرور بعدی بر پایهٔ هدف بازیابی و سقف وابسته به آزمون.

    قاعدهٔ «۱۰–۲۰٪» (Cepeda et al. 2008): فاصلهٔ مرور نسبت به روزهای
    باقی‌مانده تا آزمون مقیاس می‌شود تا همهٔ مبحث‌ها پیش از آزمون به
    فاز نگهداری برسند. دو سقف اعمال می‌شود و کوچک‌ترین انتخاب می‌شود.
    """
    if stability <= 0:
        return 1.0
    base = days_until_retrievability(target_retention, stability)
    if days_to_exam is not None and days_to_exam > 0:
        exam_cap = max(1.0, spacing_ratio * days_to_exam)
        base = min(base, exam_cap)
    return max(0.5, min(base, max_interval))


# ---------------------------------------------------------------------------
# نردبان تثبیت
# ---------------------------------------------------------------------------


class ConsolidationStage:
    """پله‌های نردبان تثبیت — مقادیر پایدار ذخیره‌شده در پایگاه داده."""

    ENCODE = "encode"                    # S0 — دیده/یادگیری اولیه
    FIRST_RETRIEVAL = "first_retrieval"  # S1 — ≤ ۲۴ ساعت (تثبیت سیناپسی + خواب)
    SPACED = "spaced"                    # S2 — چند روز (اثر فاصله)
    DELAYED = "delayed"                  # S3 — ~۷ روز (بازیابی تأخیری)
    TRANSFER = "transfer"                # S4 — ترکیبی/انتقالی (interleaving)
    MAINTENANCE = "maintenance"          # S5 — نگهداری


STAGE_LABELS: dict[str, str] = {
    ConsolidationStage.ENCODE: "S0 — یادگیری اولیه",
    ConsolidationStage.FIRST_RETRIEVAL: "S1 — بازیابی اولیه (≤۲۴ ساعت)",
    ConsolidationStage.SPACED: "S2 — بازیابی فاصله‌دار",
    ConsolidationStage.DELAYED: "S3 — بازیابی تأخیری",
    ConsolidationStage.TRANSFER: "S4 — انتقال/ترکیبی",
    ConsolidationStage.MAINTENANCE: "S5 — نگهداری",
}

#: ترتیب پله‌ها برای محاسبهٔ «پلهٔ بعدی».
STAGE_ORDER: tuple[str, ...] = (
    ConsolidationStage.ENCODE,
    ConsolidationStage.FIRST_RETRIEVAL,
    ConsolidationStage.SPACED,
    ConsolidationStage.DELAYED,
    ConsolidationStage.TRANSFER,
    ConsolidationStage.MAINTENANCE,
)

#: منابع شواهد learning_evidence که هر پله را تأیید می‌کنند.
STAGE_EVIDENCE_SOURCES: dict[str, frozenset[str]] = {
    ConsolidationStage.FIRST_RETRIEVAL: frozenset({"review", "retrieval"}),
    ConsolidationStage.SPACED: frozenset({"review", "retrieval"}),
    ConsolidationStage.DELAYED: frozenset({"delayed", "delayed_exam", "review"}),
    ConsolidationStage.TRANSFER: frozenset({"transfer", "mixed_exam", "novel_item"}),
    ConsolidationStage.MAINTENANCE: frozenset({"review", "mixed_exam"}),
}

#: برآورد دقیقهٔ هر پلهٔ تثبیت [H] — برای ساخت فعالیت خودکار تثبیت.
STAGE_MINUTES: dict[str, int] = {
    ConsolidationStage.FIRST_RETRIEVAL: 10,
    ConsolidationStage.SPACED: 15,
    ConsolidationStage.DELAYED: 20,
    ConsolidationStage.TRANSFER: 25,
    ConsolidationStage.MAINTENANCE: 10,
}

#: نوع فعالیت متناسب با هر پله [H] — انتقالی با سؤال تازه/ترکیبی سنجیده می‌شود.
STAGE_ACTIVITY_TYPES: dict[str, str] = {
    ConsolidationStage.FIRST_RETRIEVAL: "review",
    ConsolidationStage.SPACED: "review",
    ConsolidationStage.DELAYED: "timed_test",
    ConsolidationStage.TRANSFER: "mixed_practice",
    ConsolidationStage.MAINTENANCE: "review",
}

#: پیشوند نشانگر پله در state_reason فعالیت‌های خودکار تثبیت.
CONSOLIDATION_MARKER = "consolidation:"


def stage_minutes(stage: str) -> int:
    """دقیقهٔ برآوردی یک پله [H]."""
    return STAGE_MINUTES.get(stage, 15)


def stage_activity_type(stage: str) -> str:
    """نوع فعالیت متناسب با یک پله [H]."""
    return STAGE_ACTIVITY_TYPES.get(stage, "consolidation")


@dataclass(frozen=True)
class ConsolidationSettingsView:
    """نمای خوانا از تنظیمات تثبیت [H]."""

    target_retention: float
    spacing_ratio: float
    first_retrieval_hours: int
    spaced_days: float
    delayed_days: float
    transfer_days: float
    min_evidence_score: float
    stage_spacing_days: float


def consolidation_settings(settings: Optional[Settings] = None) -> ConsolidationSettingsView:
    settings = settings or Settings()
    c = settings.consolidation
    return ConsolidationSettingsView(
        target_retention=c.target_retention,
        spacing_ratio=c.spacing_ratio,
        first_retrieval_hours=c.first_retrieval_hours,
        spaced_days=c.spaced_days,
        delayed_days=c.delayed_days,
        transfer_days=c.transfer_days,
        min_evidence_score=c.stage_evidence_score,
        stage_spacing_days=c.stage_min_spacing_days,
    )


# ---------------------------------------------------------------------------
# وضعیت تثبیت یک مبحث
# ---------------------------------------------------------------------------


@dataclass
class StageProgress:
    """پیشرفت یک پله از نردبان برای یک مبحث."""

    stage: str
    done: bool = False
    evidence_at: Optional[_dt.date] = None
    evidence_score: Optional[float] = None
    due_date: Optional[_dt.date] = None
    overdue: bool = False
    note: str = ""


@dataclass
class TopicConsolidation:
    """وضعیت کامل تثبیت یک مبحث."""

    topic_id: Optional[int]
    topic_name: str
    subject_name: str = ""
    current_stage: str = ConsolidationStage.ENCODE
    stages: list[StageProgress] = field(default_factory=list)
    stability: float = 0.0
    difficulty: float = 5.0
    retrievability_now: float = 0.0
    forecast_retention: float = 0.0
    days_to_exam: Optional[int] = None
    next_due: Optional[_dt.date] = None
    status: str = "not_started"  # not_started | on_track | at_risk | behind | consolidated
    consolidated: bool = False
    notes: list[str] = field(default_factory=list)
    evidence_ids: tuple[str, ...] = ()

    @property
    def stage_label(self) -> str:
        return STAGE_LABELS.get(self.current_stage, self.current_stage)

    @property
    def next_stage(self) -> Optional[str]:
        try:
            index = STAGE_ORDER.index(self.current_stage)
        except ValueError:
            return None
        if index + 1 < len(STAGE_ORDER):
            return STAGE_ORDER[index + 1]
        return None


@dataclass
class StageEvidence:
    """یک شاهد عملکردی ساده‌شده برای ارزیابی نردبان."""

    at: _dt.date
    source: str
    score: float


def _stage_evidence(
    stage: str,
    evidence: Sequence[StageEvidence],
    *,
    min_score: float,
    previous_at: Optional[_dt.date],
    first_review_at: _dt.date,
    stage_spacing_days: float,
) -> Optional[StageEvidence]:
    """قدیمی‌ترین شاهد مناسب و استفاده‌نشده برای یک پله.

    قاعدهٔ اختصاصی هر پله:
      * S1 (بازیابی اولیه): شاهد حداکثر ۱ روز پس از یادگیری — تثبیت سیناپسی
        و بازپخش خواب (CONSOL-01/CONSOL-02).
      * پله‌های بالاتر: فاصلهٔ کمینهٔ ``stage_spacing_days`` از شاهد پیشین
        تا جلسه‌ها «جدا» باشند (اثر فاصله — SPACING-01).
    """
    allowed = STAGE_EVIDENCE_SOURCES.get(stage, frozenset())
    candidates = sorted(
        (
            item
            for item in evidence
            if item.source in allowed and item.score >= min_score
        ),
        key=lambda item: (item.at, -item.score),
    )
    for item in candidates:
        if stage == ConsolidationStage.FIRST_RETRIEVAL:
            gap = (item.at - first_review_at).days
            if 0 <= gap <= 1:
                return item
            continue
        if previous_at is None:
            return item
        gap = (item.at - previous_at).days
        if gap >= stage_spacing_days:
            return item
    return None


def assess_topic_consolidation(
    *,
    topic_id: Optional[int],
    topic_name: str,
    subject_name: str = "",
    evidence: Sequence[StageEvidence],
    stability: float = 0.0,
    difficulty: float = 5.0,
    last_review: Optional[_dt.date] = None,
    today: _dt.date,
    exam_date: Optional[_dt.date] = None,
    settings: Optional[Settings] = None,
) -> TopicConsolidation:
    """وضعیت نردبان تثبیت یک مبحث را از شواهد محاسبه می‌کند.

    قواعد:
      * پلهٔ S1 تنها با شاهد ≤ ``first_retrieval_hours`` پس از آخرین
        یادگیری قابل تأیید است (تثبیت سیناپسی و خواب).
      * پله‌های بالاتر به فاصلهٔ کمینهٔ ``stage_min_spacing_days`` بین
        شواهد نیاز دارند تا «جلسه‌های جدا» واقعی باشند.
      * وضعیت: پلهٔ سررسیدشده بدون شاهد ⇒ «عقب‌افتاده»؛ پلهٔ آینده با
        شواهد کافی ⇒ «در مسیر»؛ همهٔ پله‌ها ⇒ «تثبیت‌شده».
    """
    cfg = consolidation_settings(settings)
    result = TopicConsolidation(
        topic_id=topic_id,
        topic_name=topic_name,
        subject_name=subject_name,
        stability=max(0.0, stability),
        difficulty=difficulty,
        days_to_exam=(exam_date - today).days if exam_date else None,
        evidence_ids=("CONSOL-01", "TESTING-01", "DSR-01"),
    )

    encode_evidence = [e for e in evidence if e.source in {"diagnostic", "study", "class"}]
    encoded = bool(encode_evidence) or stability > 0 or last_review is not None
    result.stages.append(
        StageProgress(
            stage=ConsolidationStage.ENCODE,
            done=encoded,
            evidence_at=(encode_evidence[0].at if encode_evidence else last_review),
            note="مبحث دیده/یادگیری شده است." if encoded else "مبحث هنوز دیده نشده است.",
        )
    )
    if not encoded:
        result.status = "not_started"
        result.notes.append(
            "تا وقتی مبحث یک بار یادگیری نشود، نردبان تثبیت آغاز نمی‌شود."
        )
        return result

    # لنگر نردبان = نخستین بارِ یادگیری (نه آخرین مرور).
    all_evidence = sorted(evidence, key=lambda item: (item.at, item.score))
    first_review_at = (
        encode_evidence[0].at
        if encode_evidence
        else (all_evidence[0].at if all_evidence else (last_review or today))
    )
    previous_at: Optional[_dt.date] = first_review_at

    for stage in STAGE_ORDER[1:]:
        best = _stage_evidence(
            stage,
            evidence,
            min_score=cfg.min_evidence_score,
            previous_at=previous_at,
            first_review_at=first_review_at,
            stage_spacing_days=cfg.stage_spacing_days,
        )
        progress = StageProgress(stage=stage)
        if best is not None:
            progress.done = True
            progress.evidence_at = best.at
            progress.evidence_score = best.score
            previous_at = best.at
        if not progress.done:
            progress.due_date = _stage_due_date(
                stage, first_review_at, cfg, result.days_to_exam
            )
            progress.overdue = bool(
                progress.due_date is not None and progress.due_date < today
            )
        result.stages.append(progress)

    done_stages = [p for p in result.stages if p.done]
    all_done = len(done_stages) == len(STAGE_ORDER)
    result.current_stage = (
        done_stages[-1].stage if done_stages else ConsolidationStage.ENCODE
    )
    result.consolidated = all_done

    pending = [p for p in result.stages if not p.done]
    overdue = [p for p in pending if p.overdue]
    if all_done:
        result.status = "consolidated"
        result.notes.append(
            "همهٔ پله‌های نردبان تثبیت با شواهد عملکردی تکمیل شده است؛ "
            "حفظ نگهداری ادامه دارد."
        )
    elif overdue:
        result.status = "behind"
        result.notes.append(
            f"{len(overdue)} پلهٔ تثبیت از موعد گذشته است؛ در صف جبران قرار گرفت."
        )
    else:
        result.status = "on_track"
        result.notes.append("نردبان تثبیت در مسیر است.")

    # بازیابی‌پذیری فعلی و پیش‌بینی روز آزمون
    forecast_low = False
    if result.stability > 0 and last_review is not None:
        elapsed = max(0.0, (today - last_review).days)
        result.retrievability_now = retrievability(elapsed, result.stability)
        if exam_date:
            horizon = max(0.0, (exam_date - today).days)
            result.forecast_retention = retrievability(horizon, result.stability)
            if not result.consolidated and result.forecast_retention < cfg.target_retention:
                forecast_low = True
    # «عقب‌افتاده» بر «در خطر» اولویت دارد: اقدام جبرانی مشخص‌تر است.
    if overdue:
        result.status = "behind"
        if forecast_low:
            result.notes.append(
                f"پیش‌بینی ماندگاری تا روز آزمون {result.forecast_retention:.0%} است؛ "
                f"کمتر از هدف {cfg.target_retention:.0%}. جبران هرچه سریع‌تر لازم است."
            )
    elif forecast_low:
        result.status = "at_risk"
        result.notes.append(
            f"پیش‌بینی ماندگاری تا روز آزمون {result.forecast_retention:.0%} "
            f"است؛ کمتر از هدف {cfg.target_retention:.0%}. مرور اصلاحی لازم است."
        )
    next_pending = pending[0] if pending else None
    result.next_due = next_pending.due_date if next_pending else None
    return result


def _stage_due_date(
    stage: str,
    first_review_at: _dt.date,
    cfg: ConsolidationSettingsView,
    days_to_exam: Optional[int],
) -> _dt.date:
    """موعد هدف هر پله (فرضیهٔ محصول [H] بر پایهٔ شواهد زمان‌بندی)."""
    if stage == ConsolidationStage.FIRST_RETRIEVAL:
        return first_review_at + _dt.timedelta(days=1)
    if stage == ConsolidationStage.SPACED:
        offset = cfg.spaced_days
    elif stage == ConsolidationStage.DELAYED:
        offset = cfg.delayed_days
    elif stage == ConsolidationStage.TRANSFER:
        offset = cfg.transfer_days
    else:
        offset = cfg.transfer_days + 7
    if days_to_exam is not None and days_to_exam > 0:
        # نزدیک آزمون، موعدها فشرده می‌شوند (قاعدهٔ سقف وابسته به آزمون).
        offset = min(offset, max(1.0, days_to_exam * cfg.spacing_ratio))
    return first_review_at + _dt.timedelta(days=int(round(offset)))


# ---------------------------------------------------------------------------
# به‌روزرسانی مدل حافظه پس از یک مرور
# ---------------------------------------------------------------------------


def apply_review_to_memory(
    item: ReviewItem,
    *,
    grade: int,
    today: _dt.date,
    exam_date: Optional[_dt.date] = None,
    settings: Optional[Settings] = None,
) -> dict:
    """مدل DSR را پس از یک مرور به‌روزرسانی کن و خلاصهٔ تغییرات را ببرگردان.

    این تابع وضعیت ``item`` را تغییر می‌دهد (stability/difficulty/interval).
    """
    cfg = consolidation_settings(settings)
    weights = DEFAULT_DSR_WEIGHTS
    old_stability = item.stability_days
    elapsed = 0.0
    if item.last_review is not None:
        elapsed = max(0.0, float((today - item.last_review).days))
    r_now = retrievability(elapsed, old_stability) if old_stability > 0 else 0.0

    grade = max(0, min(4, grade))
    if grade <= 1:
        new_stability = stability_after_lapse(old_stability, weights)
        if item.state != ReviewState.LEECH:
            item.state = ReviewState.RELEARN
    else:
        if old_stability <= 0:
            new_stability = initial_stability(grade, weights)
        else:
            new_stability = stability_after_success(
                stability=old_stability,
                difficulty=item.difficulty,
                retrievability_now=r_now,
                grade=grade,
                weights=weights,
            )
    item.stability_days = round(new_stability, 4)
    item.difficulty = round(difficulty_update(item.difficulty, grade), 3)

    days_to_exam = (exam_date - today).days if exam_date else None
    interval = next_interval_days(
        stability=item.stability_days,
        target_retention=cfg.target_retention,
        days_to_exam=days_to_exam,
        spacing_ratio=cfg.spacing_ratio,
    )
    if grade <= 1:
        # پس از فراموشی، بازآموزی سریع: بازگشت به ۱ روز (گام relearning)،
        # و در روزهای آخر آزمون نیم‌روز. این با سیاست «اقدام اصلاحی با
        # مهلت» و اثر فراصلاح (HYPER-01) هم‌راستاست.
        interval = 1.0 if (days_to_exam is None or days_to_exam > 1) else 0.5
    item.interval_days = round(interval, 4)
    item.retrievability = round(retrievability(interval, item.stability_days), 4)
    if grade >= 3 and item.success_streak >= 2:
        item.state = ReviewState.MAINTENANCE
    return {
        "old_stability": old_stability,
        "new_stability": item.stability_days,
        "interval": item.interval_days,
        "retrievability_at_due": item.retrievability,
        "grade": grade,
    }


# ---------------------------------------------------------------------------
# پیش‌بینی ماندگاری و امکان‌سنجی
# ---------------------------------------------------------------------------


@dataclass
class RetentionForecast:
    """پیش‌بینی ماندگاری مجموعه‌ای از مبحث‌ها تا روز آزمون."""

    at_risk: list[TopicConsolidation] = field(default_factory=list)
    behind: list[TopicConsolidation] = field(default_factory=list)
    consolidated: list[TopicConsolidation] = field(default_factory=list)
    on_track: list[TopicConsolidation] = field(default_factory=list)
    not_started: list[TopicConsolidation] = field(default_factory=list)
    average_forecast: float = 0.0
    topics: list[TopicConsolidation] = field(default_factory=list)

    @property
    def coverage(self) -> float:
        """سهم مبحث‌هایی که تثبیت شده‌اند یا در مسیرند."""
        if not self.topics:
            return 0.0
        ok = len(self.consolidated) + len(self.on_track)
        return ok / len(self.topics)


def forecast_retention(
    consolidations: Sequence[TopicConsolidation],
) -> RetentionForecast:
    """خلاصهٔ پیش‌بینی ماندگاری برای همهٔ مبحث‌ها."""
    forecast = RetentionForecast(topics=list(consolidations))
    for item in consolidations:
        bucket = {
            "at_risk": forecast.at_risk,
            "behind": forecast.behind,
            "consolidated": forecast.consolidated,
            "on_track": forecast.on_track,
            "not_started": forecast.not_started,
        }.get(item.status)
        if bucket is None:
            bucket = forecast.on_track
        bucket.append(item)
    if forecast.topics:
        forecast.average_forecast = sum(
            t.forecast_retention for t in forecast.topics
        ) / len(forecast.topics)
    return forecast


# ---------------------------------------------------------------------------
# بدهی تثبیت — چه مبحث‌هایی عقب افتاده‌اند
# ---------------------------------------------------------------------------


@dataclass
class ConsolidationDebt:
    """بدهی تثبیت: پله‌هایی که موعدشان گذشته و شاهد نشده است."""

    topic_id: Optional[int]
    topic_name: str
    subject_name: str
    stage: str
    overdue_days: float
    priority: float = 0.0
    reason: str = ""

    @property
    def stage_label(self) -> str:
        return STAGE_LABELS.get(self.stage, self.stage)


def consolidation_debt(
    consolidations: Sequence[TopicConsolidation],
    today: _dt.date,
    *,
    subject_weights: Optional[dict[str, float]] = None,
) -> list[ConsolidationDebt]:
    """فهرست بدهی‌های تثبیت به‌ترتیب اولویت (قدیمی‌ترین و سنگین‌ترین).

    اولویت = سنِ عقب‌افتادی × وزن اهمیت درس (ضرایب آزمون) [H].
    """
    weights = subject_weights or {}
    debts: list[ConsolidationDebt] = []
    for topic in consolidations:
        for stage in topic.stages:
            if stage.done or not stage.overdue or stage.due_date is None:
                continue
            overdue_days = (today - stage.due_date).days
            weight = weights.get(topic.subject_name, 1.0)
            priority = overdue_days * weight
            debts.append(
                ConsolidationDebt(
                    topic_id=topic.topic_id,
                    topic_name=topic.topic_name,
                    subject_name=topic.subject_name,
                    stage=stage.stage,
                    overdue_days=float(overdue_days),
                    priority=round(priority, 3),
                    reason=(
                        f"پلهٔ «{STAGE_LABELS.get(stage.stage, stage.stage)}» "
                        f"{overdue_days} روز از موعد گذشته است."
                    ),
                )
            )
    debts.sort(key=lambda d: (-d.priority, d.topic_name))
    return debts


def consolidation_advice(
    topic: TopicConsolidation, settings: Optional[Settings] = None
) -> tuple[str, str, tuple[str, ...]]:
    """یک اقدام کوتاه + دلیل + شواهد برای یک مبحث (ADV-03).

    خروجی: (عنوان اقدام، دلیل، شناسه‌های شواهد)
    """
    cfg = consolidation_settings(settings)
    if topic.status == "not_started":
        return (
            f"یادگیری اولیهٔ {topic.topic_name}",
            "این مبحث هنوز وارد نردبان تثبیت نشده است.",
            ("WORKED-EX-01", "CONSOL-01"),
        )
    if topic.status == "behind":
        stage = topic.next_stage or ConsolidationStage.SPACED
        return (
            f"جبران تثبیت {topic.topic_name} ({STAGE_LABELS.get(stage, stage)})",
            "پله‌های تثبیت از موعد گذشته‌اند؛ ماندگاری در خطر است.",
            ("TESTING-02", "HYPER-02"),
        )
    if topic.status == "at_risk":
        return (
            f"مرور اصلاحی {topic.topic_name}",
            (
                f"پیش‌بینی ماندگاری تا آزمون {topic.forecast_retention:.0%} است؛ "
                f"کمتر از هدف {cfg.target_retention:.0%}."
            ),
            ("SPACING-02", "DSR-01"),
        )
    if topic.status == "consolidated":
        return (
            f"نگهداری {topic.topic_name}",
            "تثبیت تکمیل است؛ فقط بازیابی سبک نگه داشته می‌شود.",
            ("TESTING-02",),
        )
    return (
        f"بازیابی فعال {topic.topic_name} ({topic.stage_label})",
        "نردبان تثبیت در مسیر است؛ گام بعدی را سریع بگیر.",
        ("TESTING-01", "CONSOL-02"),
    )


__all__ = [
    "ConsolidationDebt",
    "ConsolidationSettingsView",
    "ConsolidationStage",
    "DSRWeights",
    "DEFAULT_DSR_WEIGHTS",
    "RetentionForecast",
    "StageEvidence",
    "StageProgress",
    "STAGE_LABELS",
    "STAGE_MINUTES",
    "STAGE_ORDER",
    "TopicConsolidation",
    "apply_review_to_memory",
    "assess_topic_consolidation",
    "consolidation_advice",
    "consolidation_debt",
    "consolidation_settings",
    "days_until_retrievability",
    "difficulty_update",
    "forecast_retention",
    "initial_stability",
    "next_interval_days",
    "retrievability",
    "stage_activity_type",
    "stage_minutes",
    "stability_after_lapse",
    "stability_after_success",
]
