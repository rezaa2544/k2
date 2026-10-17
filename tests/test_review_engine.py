"""تست موتور مرور تطبیقی (REV-01 تا REV-04)."""

from __future__ import annotations

import datetime as _dt

import pytest

from k2.config import Settings
from k2.domain.enums import ReviewState
from k2.review_engine import (
    GRADE_LABELS,
    apply_review,
    compress_review_backlog,
    create_review_item,
    due_items,
    grade_from_result,
    needs_retention_check,
    retention_check_sample,
    retention_signal,
    review_budget_minutes,
)

TODAY = _dt.date(2026, 10, 10)


def _item(**kwargs):
    item = create_review_item(label="مفهوم نیرو", today=TODAY)
    for key, value in kwargs.items():
        setattr(item, key, value)
    return item


def test_grade_labels_cover_five_levels():
    assert set(GRADE_LABELS) == {0, 1, 2, 3, 4}


def test_grade_from_result_mapping():
    assert grade_from_result(correct=False, confidence=1) == 1
    assert grade_from_result(correct=True, confidence=1) == 2
    assert grade_from_result(correct=True, confidence=3, time_ratio=2.0) == 2
    assert grade_from_result(correct=True, confidence=2) == 3
    assert grade_from_result(correct=True, confidence=3, time_ratio=0.5) == 4


def test_new_item_due_within_one_day():
    item = _item()
    assert item.due_date == TODAY + _dt.timedelta(days=1)
    assert item.state == ReviewState.NEW


def test_successful_review_increases_interval():
    item = _item(interval_days=2.0, ease=2.0)
    update = apply_review(item, 3, today=TODAY, settings=Settings())
    assert update.new_interval > update.old_interval
    assert item.state == ReviewState.REVIEW
    assert item.due_date is not None and item.due_date > TODAY


def test_fast_confident_answer_increases_more():
    slow = _item(interval_days=2.0, ease=2.0)
    fast = _item(interval_days=2.0, ease=2.0)
    apply_review(slow, 3, today=TODAY, settings=Settings())
    apply_review(fast, 4, today=TODAY, settings=Settings())
    assert fast.interval_days > slow.interval_days
    assert fast.ease > slow.ease


def test_failed_review_resets_interval_and_increases_lapse():
    item = _item(interval_days=10.0, ease=2.0)
    update = apply_review(item, 0, today=TODAY, settings=Settings())
    assert item.interval_days == 1.0
    assert item.lapses == 1
    assert item.state == ReviewState.RELEARN
    assert item.ease < 2.0
    assert update.notes


def test_repeated_failures_mark_item_as_leech():
    item = _item(interval_days=5.0, ease=2.0)
    for _ in range(4):
        apply_review(item, 1, today=TODAY, settings=Settings())
    assert item.lapses == 4
    assert item.state == ReviewState.LEECH
    assert any("تکراری" in note for note in apply_review(
        item, 1, today=TODAY, settings=Settings()
    ).notes)


def test_ease_is_bounded():
    item = _item(ease=2.75)
    for _ in range(20):
        apply_review(item, 4, today=TODAY, settings=Settings())
    assert item.ease <= Settings().review.ease_max

    item2 = _item(ease=1.35)
    for _ in range(20):
        apply_review(item2, 0, today=TODAY, settings=Settings())
    assert item2.ease >= Settings().review.ease_min


def test_interval_capped_by_days_to_exam():
    settings = Settings()
    exam = TODAY + _dt.timedelta(days=20)
    item = _item(interval_days=1.0, ease=2.8)
    apply_review(item, 4, today=TODAY, exam_date=exam, settings=settings)
    cap = settings.review.exam_cap_ratio * 20
    assert item.interval_days <= cap + 0.001
    assert item.due_date is not None


def test_maintenance_state_after_success_streak():
    settings = Settings()
    exam = TODAY + _dt.timedelta(days=10)
    item = _item(interval_days=1.0, ease=2.8)
    for _ in range(settings.review.maintenance_streak + 1):
        apply_review(item, 3, today=TODAY, exam_date=exam, settings=settings)
    assert item.state == ReviewState.MAINTENANCE


def test_due_items_excludes_leech_and_maintenance():
    due = _item(due_date=TODAY - _dt.timedelta(days=1))
    leech = _item(due_date=TODAY - _dt.timedelta(days=1))
    leech.state = ReviewState.LEECH
    maintenance = _item(due_date=TODAY - _dt.timedelta(days=1))
    maintenance.state = ReviewState.MAINTENANCE
    future = _item(due_date=TODAY + _dt.timedelta(days=5))
    result = due_items([due, leech, maintenance, future], TODAY)
    assert [i.label for i in result] == ["مفهوم نیرو"]


def test_review_budget_is_share_of_capacity():
    settings = Settings()
    budget = review_budget_minutes(600, settings)
    assert budget == int(600 * settings.review.daily_review_cap_ratio)


def test_overdue_item_needs_retention_check():
    settings = Settings()
    item = _item(interval_days=1.0, due_date=TODAY - _dt.timedelta(days=5))
    assert needs_retention_check(item, TODAY, settings)
    fresh = _item(interval_days=10.0, due_date=TODAY - _dt.timedelta(days=1))
    assert not needs_retention_check(fresh, TODAY, settings)


def test_retention_check_sample_is_deterministic():
    items = []
    for index in range(8):
        item = _item(interval_days=1.0, due_date=TODAY - _dt.timedelta(days=5))
        item.id = index
        items.append(item)
    first = retention_check_sample(items, TODAY, Settings())
    second = retention_check_sample(items, TODAY, Settings())
    assert [i.id for i in first] == [i.id for i in second]
    assert 0 < len(first) < len(items)


def test_compress_review_backlog_has_three_levels():
    items = []
    for index in range(9):
        item = _item(interval_days=1.0, due_date=TODAY - _dt.timedelta(days=1))
        item.id = index
        if index < 3:
            item.lapses = 3
        items.append(item)
    levels = compress_review_backlog(items, TODAY, Settings())
    assert set(levels.values()) == {"حیاتی", "مهم", "اختیاری"}


def test_retention_signal_detects_drop():
    assert retention_signal([0, 0, 0])
    assert not retention_signal([4, 4, 4])
    assert not retention_signal([])


def test_invalid_grade_raises():
    item = _item()
    with pytest.raises(ValueError):
        apply_review(item, 5, today=TODAY, settings=Settings())
