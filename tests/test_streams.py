"""تست‌های توزیع بار سه‌مسیره و امکان‌سنجی."""

from __future__ import annotations

import datetime as _dt

import pytest

from k2 import streams
from k2.config import Settings

TODAY = _dt.date(2026, 10, 18)


class TestAllocateStreams:
    def test_three_streams_fit_capacity(self):
        allocation = streams.allocate_streams(
            capacity_minutes=300,
            review_load_minutes=40,
            catchup_debt_minutes=600,
            new_load_minutes=500,
            days_to_exam=60,
            date=TODAY,
        )
        total = (
            allocation.new_minutes
            + allocation.catchup_minutes
            + allocation.consolidation_minutes
        )
        assert total <= 300
        assert allocation.reserve_minutes == 300 - total
        assert allocation.new_minutes > 0
        assert allocation.consolidation_minutes > 0

    def test_consolidation_never_zero_even_without_due_reviews(self):
        allocation = streams.allocate_streams(
            capacity_minutes=240,
            review_load_minutes=0,
            catchup_debt_minutes=0,
            new_load_minutes=1000,
            days_to_exam=200,
        )
        assert allocation.consolidation_minutes >= 240 * 0.2

    def test_catchup_respects_daily_cap(self):
        settings = Settings()
        settings.streams.catchup_cap_ratio = 0.4
        allocation = streams.allocate_streams(
            capacity_minutes=200,
            review_load_minutes=0,
            catchup_debt_minutes=100000,
            new_load_minutes=0,
            days_to_exam=300,
            settings=settings,
        )
        assert allocation.catchup_minutes <= 200 * 0.4 + 1

    def test_catchup_spread_over_remaining_days(self):
        # ۱۰۰۰ دقیقه بدهی در ۱۰ روز ⇒ ۱۰۰ دقیقه در روز (کمتر از سقف)
        allocation = streams.allocate_streams(
            capacity_minutes=600,
            review_load_minutes=30,
            catchup_debt_minutes=1000,
            new_load_minutes=300,
            days_to_exam=10,
        )
        assert allocation.catchup_minutes == pytest.approx(100, abs=1)

    def test_zero_capacity_is_safe(self):
        allocation = streams.allocate_streams(
            capacity_minutes=0, review_load_minutes=10, new_load_minutes=10
        )
        assert allocation.total_minutes == 0
        assert allocation.notes

    def test_review_surge_expands_consolidation_to_cap(self):
        settings = Settings()
        settings.streams.consolidation_surge_ratio = 0.3
        settings.streams.consolidation_cap_ratio = 0.45
        allocation = streams.allocate_streams(
            capacity_minutes=400,
            review_load_minutes=1000,  # بار سنگین مرور
            catchup_debt_minutes=0,
            new_load_minutes=0,
            days_to_exam=100,
            settings=settings,
        )
        assert allocation.consolidation_minutes == pytest.approx(400 * 0.45, abs=1)
        assert any("سقف" in note for note in allocation.notes)


class TestFeasibility:
    def test_feasible_when_capacity_covers_work(self):
        verdict = streams.assess_feasibility(
            new_load_minutes=10000,
            catchup_debt_minutes=1000,
            consolidation_load_minutes=2000,
            daily_capacity_minutes=300,
            days_to_exam=60,
        )
        assert verdict.feasible
        assert verdict.level == "ok"
        assert verdict.deficit_minutes == 0
        assert verdict.notes

    def test_infeasible_reports_deficit_and_options(self):
        verdict = streams.assess_feasibility(
            new_load_minutes=60000,
            catchup_debt_minutes=20000,
            consolidation_load_minutes=5000,
            daily_capacity_minutes=200,
            days_to_exam=40,
        )
        assert not verdict.feasible
        assert verdict.level in {"tight", "infeasible"}
        assert verdict.deficit_minutes > 0
        assert verdict.options  # مشاور واقعی گزینه می‌دهد

    def test_unknown_exam_date_is_neutral(self):
        verdict = streams.assess_feasibility(
            new_load_minutes=1000,
            catchup_debt_minutes=0,
            consolidation_load_minutes=0,
            daily_capacity_minutes=200,
            days_to_exam=None,
        )
        assert verdict.level == "unknown"
        assert not verdict.options


class TestCatchupPlan:
    def test_plan_spreads_debt_without_dropping(self):
        plan = streams.catchup_plan(
            debts=[(1, "آزمون تست", 300), (2, "تمرین", 200)],
            start_date=TODAY,
            days=7,
            daily_budget_minutes=90,
        )
        assert plan
        total = sum(q.minutes for q in plan)
        assert total == 500  # در پنجرهٔ ۷ روز همه جا می‌شود و هیچ‌چیز حذف نمی‌شود
        # ترتیب: کار اول پر می‌شود بعد کار دوم
        assert plan[0].activity_id == 1
        assert plan[-1].activity_id == 2

    def test_plan_is_bounded_by_window(self):
        plan = streams.catchup_plan(
            debts=[(1, "آزمون تست", 300)],
            start_date=TODAY,
            days=2,
            daily_budget_minutes=90,
        )
        assert sum(q.minutes for q in plan) == 180  # باقی‌مانده صریح است، نه حذف

    def test_plan_respects_max_block(self):
        settings = Settings()
        settings.capacity.max_block_minutes = 60
        plan = streams.catchup_plan(
            debts=[(1, "کلاس ضبط‌شده", 300)],
            start_date=TODAY,
            days=3,
            daily_budget_minutes=200,
            settings=settings,
        )
        assert all(q.minutes <= 60 for q in plan)

    def test_empty_debt_produces_empty_plan(self):
        plan = streams.catchup_plan(
            debts=[], start_date=TODAY, days=3, daily_budget_minutes=60
        )
        assert plan == []
