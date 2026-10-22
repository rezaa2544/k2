"""تست‌های فاکتورهای تازهٔ اولویت و محافظ حذف‌نشدن (بند ۱۴)."""

from __future__ import annotations

import datetime as _dt

import pytest

from k2.config import Settings
from k2.domain.enums import ActivityType, DeadlineType
from k2.domain.models import Activity
from k2.scheduler import (
    TopicFactors,
    compute_priority,
    drop_order,
    progress_probability,
    protected_minutes,
    protect_reason,
)

TODAY = _dt.date(2026, 10, 23)


def _activity(**kwargs) -> Activity:
    defaults = dict(
        id=1,
        title="تمرین مشتق",
        type=ActivityType.INDEPENDENT_PRACTICE,
        est_minutes=60,
        remaining_minutes=0,
        max_chunk=90,
        min_chunk=20,
    )
    defaults.update(kwargs)
    return Activity(**defaults)


def test_priority_has_all_nine_factors():
    score = compute_priority(
        _activity(),
        today=TODAY,
        settings=Settings(),
        topic_factors=TopicFactors(
            prerequisite_share=0.5,
            final_exam_share=0.4,
            forgetting_rate=0.8,
            topic_deadline_days=10,
            remaining_minutes=100,
            available_minutes=200,
        ),
    )
    labels = [label for label, _ in score.components]
    for expected in (
        "پیش‌نیاز بودن",
        "سهم آزمون نهایی",
        "سرعت فراموشی",
        "مهلت مبحث",
        "احتمال پیشرفت",
    ):
        assert expected in labels
    assert len(labels) == 11


def test_prerequisite_topic_outranks_equivalent_topic():
    settings = Settings()
    base = compute_priority(_activity(), today=TODAY, settings=settings)
    prereq = compute_priority(
        _activity(),
        today=TODAY,
        settings=settings,
        topic_factors=TopicFactors(prerequisite_share=1.0),
    )
    assert prereq.total > base.total


def test_final_exam_share_raises_priority():
    settings = Settings()
    base = compute_priority(_activity(), today=TODAY, settings=settings)
    final = compute_priority(
        _activity(),
        today=TODAY,
        settings=settings,
        topic_factors=TopicFactors(final_exam_share=1.0),
    )
    assert final.total > base.total


def test_fast_forgetting_topic_comes_earlier():
    settings = Settings()
    slow = compute_priority(
        _activity(), today=TODAY, settings=settings,
        topic_factors=TopicFactors(forgetting_rate=0.1),
    )
    fast = compute_priority(
        _activity(), today=TODAY, settings=settings,
        topic_factors=TopicFactors(forgetting_rate=0.9),
    )
    assert fast.total > slow.total


def test_closer_topic_deadline_raises_priority():
    settings = Settings()
    far = compute_priority(
        _activity(), today=TODAY, settings=settings,
        topic_factors=TopicFactors(topic_deadline_days=60),
    )
    near = compute_priority(
        _activity(), today=TODAY, settings=settings,
        topic_factors=TopicFactors(topic_deadline_days=3),
    )
    assert near.total > far.total


def test_unknown_topic_deadline_does_not_crash():
    """دادهٔ ناقص نباید اولویت‌دهی را از کار بیندازد."""
    score = compute_priority(
        _activity(),
        today=TODAY,
        settings=Settings(),
        topic_factors=TopicFactors(topic_deadline_days=None),
    )
    assert score.component("مهلت مبحث") == 0.0


def test_progress_probability_is_clamped():
    assert progress_probability(0, 0) == 1.0
    assert progress_probability(100, 0) == 0.0
    assert progress_probability(100, 50) == 0.5
    assert progress_probability(100, 500) == 1.0


def test_achievable_topic_scores_above_impossible_one():
    settings = Settings()
    achievable = compute_priority(
        _activity(), today=TODAY, settings=settings,
        topic_factors=TopicFactors(remaining_minutes=60, available_minutes=600),
    )
    impossible = compute_priority(
        _activity(), today=TODAY, settings=settings,
        topic_factors=TopicFactors(remaining_minutes=600, available_minutes=60),
    )
    assert achievable.total > impossible.total


def test_weights_are_user_adjustable():
    settings = Settings()
    settings.scheduler.w_prerequisite = 0.0
    zeroed = compute_priority(
        _activity(), today=TODAY, settings=settings,
        topic_factors=TopicFactors(prerequisite_share=1.0),
    )
    assert zeroed.component("پیش‌نیاز بودن") == 0.0
    settings.scheduler.w_prerequisite = 5.0
    boosted = compute_priority(
        _activity(), today=TODAY, settings=settings,
        topic_factors=TopicFactors(prerequisite_share=1.0),
    )
    assert boosted.component("پیش‌نیاز بودن") == 5.0


def test_no_topic_is_dropped_merely_for_being_hard():
    """مبحث سخت و ضعیف ولی مهم نباید «قابل حذف» شمرده شود."""
    activity = _activity(
        deadline_type=DeadlineType.SOFT, type=ActivityType.INDEPENDENT_PRACTICE
    )
    # ضعف ثبت‌شده در آزمون + اهمیت ⇒ محافظت (سختی به‌تنهایی دلیل حذف نیست)
    weak_but_important = protect_reason(
        activity, TopicFactors(importance=1.0, exam_weakness=0.9)
    )
    assert "ضعف ثبت‌شده" in weak_but_important
    # پیش‌نیاز بودن به‌تنهایی کافی است
    assert protect_reason(activity, TopicFactors(prerequisite_share=0.3)) != ""
    # سهم آزمون نهایی به‌تنهایی کافی است
    assert protect_reason(activity, TopicFactors(final_exam_share=0.5)) != ""
    # مبحث سختِ بی‌اهمیت و بی‌پیش‌نیاز استثنا ندارد
    assert protect_reason(activity, TopicFactors(importance=0.2, exam_weakness=0.9)) == ""


def test_hard_deadline_always_protects():
    activity = _activity(deadline_type=DeadlineType.HARD)
    assert protect_reason(activity, TopicFactors()) != ""


def test_drop_order_never_puts_hard_but_important_first():
    """ترتیب کنارگذاشتن بر اساس امتیاز است، نه سختی."""
    settings = Settings()
    easy_low = _activity(id=1, title="آسان و کم‌اهمیت", est_minutes=30)
    hard_important = _activity(id=2, title="سخت و مهم", est_minutes=90)
    scores = {
        1: compute_priority(easy_low, today=TODAY, settings=settings),
        2: compute_priority(
            hard_important,
            today=TODAY,
            settings=settings,
            topic_factors=TopicFactors(prerequisite_share=1.0, importance=1.0),
        ),
    }
    order = drop_order([easy_low, hard_important], scores)
    assert order[0].title == "آسان و کم‌اهمیت"
    assert order[-1].title == "سخت و مهم"


def test_protected_minutes_respects_capacity_floor():
    settings = Settings()
    settings.scheduler.hard_topic_floor_ratio = 0.20
    activities = [
        _activity(id=1, topic_id=10, est_minutes=60),
        _activity(id=2, topic_id=20, est_minutes=45),
    ]
    factors = {
        10: TopicFactors(prerequisite_share=1.0),
        20: TopicFactors(),
    }
    minutes = protected_minutes(activities, factors, 300, settings=settings)
    assert minutes == 60  # کف ۲۰٪ از ۳۰۰ دقیقه
    assert protected_minutes([], {}, 300, settings=settings) == 0


def test_all_factors_present_in_settings():
    settings = Settings()
    w = settings.scheduler
    assert w.w_prerequisite > 0
    assert w.w_final_exam_share > 0
    assert w.w_forgetting_rate > 0
    assert w.w_topic_deadline > 0
    assert w.w_progress_probability > 0
    assert 0 < w.hard_topic_floor_ratio < 1


@pytest.mark.parametrize(
    "kwargs",
    [
        {"prerequisite_share": 0.7},
        {"final_exam_share": 0.6},
        {"forgetting_rate": 0.5},
        {"topic_deadline_days": 4},
    ],
)
def test_each_new_factor_increases_the_score(kwargs):
    settings = Settings()
    base = compute_priority(_activity(), today=TODAY, settings=settings)
    boosted = compute_priority(
        _activity(), today=TODAY, settings=settings, topic_factors=TopicFactors(**kwargs)
    )
    assert boosted.total > base.total
