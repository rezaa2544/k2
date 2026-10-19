"""تست‌های موتور تثبیت: مدل DSR، نردبان تثبیت، بدهی و مشاوره."""

from __future__ import annotations

import datetime as _dt

import pytest

from k2 import consolidation as c
from k2.config import Settings
from k2.domain.models import ReviewItem
from k2.review_engine import apply_review, create_review_item

TODAY = _dt.date(2026, 10, 18)
EXAM = _dt.date(2027, 6, 15)


# ---------------------------------------------------------------------------
# مدل حافظهٔ DSR
# ---------------------------------------------------------------------------


class TestDSRModel:
    def test_retrievability_at_stability_is_90_percent(self):
        # تعریف مدل: R(t=S) دقیقاً ۰٫۹ است.
        assert c.retrievability(10, 10) == pytest.approx(0.9, abs=1e-9)

    def test_retrievability_decays_monotonically(self):
        values = [c.retrievability(days, 5.0) for days in (0, 1, 2, 5, 10, 30)]
        assert all(a >= b for a, b in zip(values, values[1:]))
        assert values[0] == pytest.approx(1.0)

    def test_zero_stability_means_zero_retrievability(self):
        assert c.retrievability(5, 0) == 0.0

    def test_days_until_retrievability_matches_stability_at_90(self):
        # S روزهایی است که طول می‌کشد R به ۹۰٪ برسد.
        assert c.days_until_retrievability(0.9, 12.0) == pytest.approx(12.0, rel=1e-6)

    def test_next_interval_equals_stability_at_target(self):
        assert c.next_interval_days(stability=8.0, target_retention=0.9) == pytest.approx(
            8.0, rel=1e-6
        )

    def test_next_interval_respects_exam_cap(self):
        # ۳۰ روز تا آزمون × ۱۵٪ = ۴٫۵ روز سقف
        interval = c.next_interval_days(
            stability=100.0, target_retention=0.9, days_to_exam=30, spacing_ratio=0.15
        )
        assert interval == pytest.approx(4.5)

    def test_stability_grows_more_when_retrieval_is_harder(self):
        hard = c.stability_after_success(
            stability=3.0, difficulty=5.0, retrievability_now=0.55, grade=3
        )
        easy = c.stability_after_success(
            stability=3.0, difficulty=5.0, retrievability_now=0.95, grade=3
        )
        assert hard > easy > 3.0

    def test_easier_items_grow_more(self):
        easy_item = c.stability_after_success(
            stability=3.0, difficulty=2.0, retrievability_now=0.7, grade=3
        )
        hard_item = c.stability_after_success(
            stability=3.0, difficulty=9.0, retrievability_now=0.7, grade=3
        )
        assert easy_item > hard_item

    def test_lapse_reduces_but_keeps_stability(self):
        after = c.stability_after_lapse(10.0)
        assert 0 < after < 10.0
        assert after == pytest.approx(10.0 * c.DEFAULT_DSR_WEIGHTS.lapse_recovery)

    def test_difficulty_mean_reverts(self):
        # نمرهٔ پایین سختی را بالا می‌برد، ولی به مقدار میانگین میل دارد.
        value = 3.0
        for _ in range(20):
            value = c.difficulty_update(value, 0)
        assert 3.0 < value < 5.0
        value = 3.0
        for _ in range(20):
            value = c.difficulty_update(value, 4)
        assert 1.0 < value < 3.0

    def test_initial_stability_by_grade(self):
        assert c.initial_stability(0) < c.initial_stability(2) < c.initial_stability(4)


# ---------------------------------------------------------------------------
# نردبان تثبیت
# ---------------------------------------------------------------------------


def _evidence(*rows):
    return [
        c.StageEvidence(at, source, score) for at, source, score in rows
    ]


class TestConsolidationLadder:
    def test_unseen_topic_is_not_started(self):
        result = c.assess_topic_consolidation(
            topic_id=1,
            topic_name="هضم",
            evidence=[],
            today=TODAY,
            exam_date=EXAM,
        )
        assert result.status == "not_started"
        assert result.stages[0].stage == c.ConsolidationStage.ENCODE
        assert not result.stages[0].done

    def test_full_ladder_marks_consolidated(self):
        evidence = _evidence(
            (_dt.date(2026, 10, 1), "study", 1.0),
            (_dt.date(2026, 10, 2), "review", 0.9),      # S1 ≤ ۱ روز
            (_dt.date(2026, 10, 5), "review", 0.85),     # S2 فاصله‌دار
            (_dt.date(2026, 10, 12), "delayed", 0.8),    # S3 تأخیری
            (_dt.date(2026, 10, 26), "transfer", 0.9),   # S4 انتقالی
            (_dt.date(2026, 11, 20), "mixed_exam", 0.88),  # S5 نگهداری
        )
        result = c.assess_topic_consolidation(
            topic_id=2,
            topic_name="تکامل",
            evidence=evidence,
            stability=25.0,
            last_review=_dt.date(2026, 11, 20),
            today=TODAY,
            exam_date=EXAM,
        )
        assert result.consolidated
        assert result.status == "consolidated"
        assert result.current_stage == c.ConsolidationStage.MAINTENANCE
        assert all(stage.done for stage in result.stages)

    def test_same_day_retrieval_cannot_confirm_spaced_stage(self):
        evidence = _evidence(
            (_dt.date(2026, 10, 10), "study", 1.0),
            (_dt.date(2026, 10, 10), "review", 0.95),
        )
        result = c.assess_topic_consolidation(
            topic_id=3,
            topic_name="سلول",
            evidence=evidence,
            stability=0.5,
            last_review=_dt.date(2026, 10, 10),
            today=TODAY,
            exam_date=EXAM,
        )
        stages = {s.stage: s.done for s in result.stages}
        assert stages[c.ConsolidationStage.FIRST_RETRIEVAL] is True
        assert stages[c.ConsolidationStage.SPACED] is False
        assert result.status == "behind"

    def test_overdue_stage_is_debt(self):
        evidence = _evidence((_dt.date(2026, 10, 1), "study", 1.0))
        result = c.assess_topic_consolidation(
            topic_id=4,
            topic_name="ژنتیک",
            evidence=evidence,
            last_review=_dt.date(2026, 10, 1),
            today=TODAY,
            exam_date=EXAM,
        )
        assert result.status == "behind"
        overdue = [s for s in result.stages if s.overdue]
        assert overdue

    def test_low_score_evidence_does_not_confirm(self):
        evidence = _evidence(
            (_dt.date(2026, 10, 1), "study", 1.0),
            (_dt.date(2026, 10, 2), "review", 0.2),
        )
        settings = Settings()
        settings.consolidation.stage_evidence_score = 0.7
        result = c.assess_topic_consolidation(
            topic_id=5,
            topic_name="ژنتیک",
            evidence=evidence,
            today=TODAY,
            exam_date=EXAM,
            settings=settings,
        )
        assert not result.stages[1].done

    def test_forecast_retention_flags_at_risk(self):
        # پایداری کم ⇒ پیش‌بینی پایین ⇒ at_risk (هیچ پله‌ای عقب‌افتاده نیست)
        evidence = _evidence((TODAY, "study", 1.0))
        result = c.assess_topic_consolidation(
            topic_id=6,
            topic_name="هضم",
            evidence=evidence,
            stability=1.0,
            last_review=TODAY,
            today=TODAY,
            exam_date=EXAM,
        )
        assert result.forecast_retention < 0.5
        assert result.status == "at_risk"
        assert any("ماندگاری" in note for note in result.notes)

    def test_overdue_takes_precedence_over_forecast(self):
        # هم عقب‌افتاده هم پیش‌بینی پایین ⇒ «عقب‌افتاده» با یادداشت پیش‌بینی
        evidence = _evidence((_dt.date(2026, 10, 15), "study", 1.0))
        result = c.assess_topic_consolidation(
            topic_id=8,
            topic_name="هضم",
            evidence=evidence,
            stability=1.0,
            last_review=_dt.date(2026, 10, 16),
            today=TODAY,
            exam_date=EXAM,
        )
        assert result.status == "behind"
        assert any("ماندگاری" in note for note in result.notes)

    def test_stage_dates_compress_near_exam(self):
        settings = Settings()
        settings.consolidation.transfer_days = 14.0
        evidence = _evidence((_dt.date(2026, 10, 17), "study", 1.0))
        near_exam = _dt.date(2026, 10, 28)
        result = c.assess_topic_consolidation(
            topic_id=7,
            topic_name="تست",
            evidence=evidence,
            today=TODAY,
            exam_date=near_exam,
            settings=settings,
        )
        transfer_stage = result.stages[-2]
        # ۱۰ روز × ۱۵٪ = ۱٫۵ ⇒ موعد فشرده
        assert transfer_stage.due_date <= _dt.date(2026, 10, 19)

    def test_settings_view_reads_config(self):
        settings = Settings()
        settings.consolidation.target_retention = 0.85
        view = c.consolidation_settings(settings)
        assert view.target_retention == 0.85


# ---------------------------------------------------------------------------
# اعمال مرور روی مدل حافظه
# ---------------------------------------------------------------------------


class TestApplyReviewToMemory:
    def test_first_success_sets_stability_and_interval(self):
        item = create_review_item(label="مفهوم سلول", today=TODAY)
        update = c.apply_review_to_memory(item, grade=3, today=TODAY, exam_date=EXAM)
        assert item.stability_days > 0
        assert item.interval_days > 0
        assert 0 < item.retrievability <= 1
        assert update["new_stability"] == item.stability_days

    def test_lapse_reduces_stability(self):
        item = create_review_item(label="مفهوم سلول", today=TODAY)
        c.apply_review_to_memory(item, grade=3, today=TODAY)
        before = item.stability_days
        c.apply_review_to_memory(item, grade=1, today=TODAY)
        assert item.stability_days < before
        assert item.state.value == "relearn"

    def test_repeated_success_grows_stability(self):
        item = create_review_item(label="واژه", today=TODAY)
        c.apply_review_to_memory(item, grade=3, today=TODAY)
        first = item.stability_days
        for offset in range(1, 6):
            c.apply_review_to_memory(
                item, grade=3, today=TODAY + _dt.timedelta(days=offset)
            )
        assert item.stability_days > first

    def test_apply_review_engine_uses_dsr(self):
        item = create_review_item(label="تست", today=TODAY)
        update = apply_review(item, 3, today=TODAY, exam_date=EXAM)
        assert item.stability_days > 0
        assert item.due_date > TODAY
        assert update.new_due == item.due_date


# ---------------------------------------------------------------------------
# بدهی تثبیت و مشاوره
# ---------------------------------------------------------------------------


class TestConsolidationDebtAndAdvice:
    def _behind_topic(self):
        evidence = _evidence((_dt.date(2026, 10, 1), "study", 1.0))
        return c.assess_topic_consolidation(
            topic_id=9,
            topic_name="ژنتیک",
            subject_name="زیست‌شناسی",
            evidence=evidence,
            last_review=_dt.date(2026, 10, 1),
            today=TODAY,
            exam_date=EXAM,
        )

    def test_debt_prioritizes_by_age_and_weight(self):
        behind = self._behind_topic()
        fresh = _evidence((_dt.date(2026, 10, 17), "study", 1.0))
        on_track = c.assess_topic_consolidation(
            topic_id=10,
            topic_name="سلول",
            subject_name="زیست‌شناسی",
            evidence=fresh,
            last_review=_dt.date(2026, 10, 17),
            today=TODAY,
            exam_date=EXAM,
        )
        debts = c.consolidation_debt(
            [behind, on_track], TODAY, subject_weights={"زیست‌شناسی": 12.0}
        )
        assert debts
        assert debts[0].topic_name == "ژنتیک"
        assert debts[0].priority > 0

    def test_advice_for_each_status(self):
        behind = self._behind_topic()
        title, reason, evidence_ids = c.consolidation_advice(behind)
        assert "جبران" in title
        assert evidence_ids

        not_started = c.assess_topic_consolidation(
            topic_id=11, topic_name="نیاز", evidence=[], today=TODAY
        )
        title, _, _ = c.consolidation_advice(not_started)
        assert "یادگیری اولیه" in title

    def test_forecast_buckets(self):
        behind = self._behind_topic()
        forecast = c.forecast_retention([behind])
        assert len(forecast.behind) == 1
        assert forecast.coverage == 0.0
        assert forecast.average_forecast >= 0.0
