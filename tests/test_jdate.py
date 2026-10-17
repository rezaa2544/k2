"""تست تقویم شمسی، هفتهٔ شنبه‌محور و متن فارسی (CAL-01/CAL-02)."""

from __future__ import annotations

import datetime as _dt

import pytest

from k2.jdate import (
    WEEKDAY_NAMES,
    format_jalali,
    format_jalali_long,
    format_minutes,
    format_number,
    is_jalali_leap_year,
    normalize_digits,
    parse_gregorian_date,
    parse_jalali_date,
    persian_digits,
    to_gregorian,
    to_jalali,
    week_days,
    week_start,
    weekday_index,
    weekday_name,
)


def test_gregorian_to_jalali_known_dates():
    j = to_jalali(_dt.date(2026, 10, 16))
    assert (j.year, j.month, j.day) == (1405, 7, 24)
    assert to_gregorian(1405, 7, 24) == _dt.date(2026, 10, 16)
    j2 = to_jalali(_dt.date(2026, 3, 21))
    assert (j2.year, j2.month, j2.day) == (1405, 1, 1)
    assert to_gregorian(1405, 1, 1) == _dt.date(2026, 3, 21)


def test_roundtrip_over_many_dates():
    start = _dt.date(2020, 1, 1)
    for offset in range(0, 365 * 6, 17):
        value = start + _dt.timedelta(days=offset)
        j = to_jalali(value)
        assert to_gregorian(j.year, j.month, j.day) == value


def test_leap_year():
    assert is_jalali_leap_year(1403) is True
    assert is_jalali_leap_year(1404) is False
    assert to_gregorian(1403, 12, 30) == _dt.date(2025, 3, 20)
    # ۳۰ اسفند در سال غیرکبیسه نامعتبر است.
    with pytest.raises(ValueError):
        to_gregorian(1404, 12, 30)


def test_week_starts_on_saturday():
    # ۱۴۰۵/۰۷/۲۴ برابر جمعهٔ ۲۰۲۶/۱۰/۱۶ است.
    friday = _dt.date(2026, 10, 16)
    assert weekday_index(friday) == 6
    assert weekday_name(friday) == "جمعه"
    assert week_start(friday) == _dt.date(2026, 10, 10)
    assert weekday_index(_dt.date(2026, 10, 10)) == 0
    assert weekday_name(_dt.date(2026, 10, 10)) == "شنبه"
    assert WEEKDAY_NAMES[0] == "شنبه"


def test_week_days_are_seven_consecutive():
    days = week_days(_dt.date(2026, 10, 10), 7)
    assert len(days) == 7
    assert days[0] == _dt.date(2026, 10, 10)
    assert days[-1] == _dt.date(2026, 10, 16)
    for index in range(6):
        assert days[index + 1] - days[index] == _dt.timedelta(days=1)


def test_parse_jalali_with_persian_digits():
    value = parse_jalali_date("۱۴۰۵/۰۷/۲۴")
    assert value == _dt.date(2026, 10, 16)
    assert parse_jalali_date("1405-07-24") == value
    assert parse_jalali_date("1405.7.4") == _dt.date(2026, 9, 26)


def test_parse_jalali_rejects_garbage():
    with pytest.raises(ValueError):
        parse_jalali_date("فردا")
    with pytest.raises(ValueError):
        parse_jalali_date("1405/13/01")


def test_parse_gregorian():
    assert parse_gregorian_date("2026-10-16") == _dt.date(2026, 10, 16)
    with pytest.raises(ValueError):
        parse_gregorian_date("16/10/2026")


def test_persian_digits():
    assert persian_digits("1405") == "۱۴۰۵"
    assert normalize_digits("۱۴۰۵") == "1405"
    assert normalize_digits("٤٥٦") == "456"
    assert format_number(1234, persian=False) == "1,234"
    assert format_number(1234).isdigit() is False


def test_format_helpers():
    assert format_minutes(0) == "۰ دقیقه"
    assert format_minutes(45) == "۴۵ دقیقه"
    assert "ساعت" in format_minutes(120)
    assert "ساعت" in format_minutes(150)
    assert format_jalali(_dt.date(2026, 10, 16)).startswith("جمعه")
    assert "مهر" in format_jalali_long(_dt.date(2026, 10, 16))
