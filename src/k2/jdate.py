"""ابزارهای تقویم شمسی، تاریخ و متن فارسی.

قرارداد ذخیره‌سازی (سند اجرایی، بند «راهبرد فنی»):
  * تاریخ‌ها در پایگاه داده به‌صورت **میلادی ISO** (``YYYY-MM-DD``) ذخیره می‌شوند.
  * زمان‌ها به‌صورت **ISO محلی بدون منطقهٔ زمانی** (``YYYY-MM-DDTHH:MM:SS``).
  * تبدیل به شمسی فقط در لایهٔ نمایش انجام می‌شود.

هفته در این محصول **شنبه‌محور** است: شنبه = ۰ ... جمعه = ۶.
"""

from __future__ import annotations

import datetime as _dt
import re
from typing import Iterable

import jdatetime

#: نام روزهای هفته به‌ترتیب شنبه‌محور.
WEEKDAY_NAMES = (
    "شنبه",
    "یکشنبه",
    "دوشنبه",
    "سه‌شنبه",
    "چهارشنبه",
    "پنجشنبه",
    "جمعه",
)

#: نام ماه‌های شمسی.
JALALI_MONTH_NAMES = (
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
)

_LATIN_TO_PERSIAN = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
_PERSIAN_TO_LATIN = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
_ARABIC_TO_LATIN = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

_JALALI_DATE_RE = re.compile(r"^\s*(\d{3,4})[/\-.](\d{1,2})[/\-.](\d{1,2})\s*$")
_GREGORIAN_DATE_RE = re.compile(r"^\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*$")


# ---------------------------------------------------------------------------
# تبدیل تاریخ
# ---------------------------------------------------------------------------


def to_jalali(value: _dt.date) -> jdatetime.date:
    """تبدیل تاریخ میلادی به شمسی."""
    return jdatetime.date.fromgregorian(date=value)


def to_gregorian(year: int, month: int, day: int) -> _dt.date:
    """تبدیل تاریخ شمسی به میلادی.

   Raises:
        ValueError: اگر تاریخ شمسی معتبر نباشد (مثلاً ۳۰ اسفند در سال غیرکبیسه).
    """
    try:
        return jdatetime.date(year, month, day).togregorian()
    except ValueError as exc:  # pragma: no cover - بستگی به رفتار jdatetime
        raise ValueError(f"تاریخ شمسی نامعتبر: {year}/{month}/{day}") from exc


def is_jalali_leap_year(year: int) -> bool:
    """آیا سال شمسی کبیسه است؟"""
    return bool(jdatetime.date(year, 1, 1).isleap())


def parse_jalali_date(text: str) -> _dt.date:
    """رشتهٔ «۱۴۰۵/۰۷/۲۴» را به تاریخ میلادی تبدیل می‌کند.

    اعداد فارسی و عربی پذیرفته می‌شوند.
    """
    normalized = normalize_digits(text)
    match = _JALALI_DATE_RE.match(normalized)
    if not match:
        raise ValueError(f"قالب تاریخ شمسی نامعتبر: {text!r} (نمونهٔ درست: ۱۴۰۵/۰۷/۲۴)")
    year, month, day = (int(g) for g in match.groups())
    return to_gregorian(year, month, day)


def parse_gregorian_date(text: str) -> _dt.date:
    """رشتهٔ «2026-10-16» را به تاریخ میلادی تبدیل می‌کند."""
    match = _GREGORIAN_DATE_RE.match(normalize_digits(text))
    if not match:
        raise ValueError(f"قالب تاریخ میلادی نامعتبر: {text!r} (نمونهٔ درست: 2026-10-16)")
    year, month, day = (int(g) for g in match.groups())
    return _dt.date(year, month, day)


def format_jalali(value: _dt.date, *, with_weekday: bool = True) -> str:
    """قالب‌بندی تاریخ شمسی برای نمایش."""
    j = to_jalali(value)
    core = f"{j.year}/{j.month:02d}/{j.day:02d}"
    if not with_weekday:
        return core
    return f"{weekday_name(value)} {core}"


def format_jalali_long(value: _dt.date) -> str:
    """«شنبه ۲۴ مهر ۱۴۰۵»."""
    j = to_jalali(value)
    return (
        f"{weekday_name(value)} {j.day} {JALALI_MONTH_NAMES[j.month - 1]} {j.year}"
    )


# ---------------------------------------------------------------------------
# هفتهٔ شنبه‌محور
# ---------------------------------------------------------------------------


def weekday_index(value: _dt.date) -> int:
    """شمارهٔ روز هفته با شروع از شنبه (شنبه=۰ ... جمعه=۶)."""
    # ``date.weekday()`` با دوشنبه=۰ شروع می‌شود؛ شنبه = ۵.
    return (value.weekday() + 2) % 7


def weekday_name(value: _dt.date) -> str:
    return WEEKDAY_NAMES[weekday_index(value)]


def week_start(value: _dt.date) -> _dt.date:
    """شنبهٔ ابتدای هفتهٔ شامل ``value``."""
    return value - _dt.timedelta(days=weekday_index(value))


def week_days(start: _dt.date, count: int = 7) -> list[_dt.date]:
    """فهرست روزهای هفته از ``start`` به بعد."""
    return [start + _dt.timedelta(days=i) for i in range(count)]


# ---------------------------------------------------------------------------
# متن‌های فارسی
# ---------------------------------------------------------------------------


def normalize_digits(text: str) -> str:
    """تبدیل ارقام فارسی/عربی به ارقام لاتین."""
    return text.translate(_PERSIAN_TO_LATIN).translate(_ARABIC_TO_LATIN)


def persian_digits(text: str) -> str:
    """تبدیل ارقام لاتین به ارقام فارسی."""
    return text.translate(_LATIN_TO_PERSIAN)


def format_number(value: float, *, digits: int = 0, persian: bool = True) -> str:
    """قالب‌بندی عدد با جداکنندهٔ هزارگان."""
    if digits:
        rendered = f"{value:,.{digits}f}"
    else:
        rendered = f"{round(value):,}"
    return persian_digits(rendered) if persian else rendered


def format_minutes(total_minutes: float, *, persian: bool = True) -> str:
    """«۲ ساعت و ۳۰ دقیقه»."""
    total = int(round(max(0.0, total_minutes)))
    hours, minutes = divmod(total, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{format_number(hours, persian=persian)} ساعت")
    if minutes:
        parts.append(f"{format_number(minutes, persian=persian)} دقیقه")
    if not parts:
        parts.append("۰ دقیقه" if persian else "0 minutes")
    return " و ".join(parts)


def format_clock(hour: int, minute: int = 0, *, persian: bool = True) -> str:
    """«۱۵:۳۰»."""
    rendered = f"{hour:02d}:{minute:02d}"
    return persian_digits(rendered) if persian else rendered


def clock_to_minutes(hour: int, minute: int = 0) -> int:
    return hour * 60 + minute


def minutes_to_clock(total: int) -> tuple[int, int]:
    total = max(0, min(24 * 60 - 1, int(total)))
    return divmod(total, 60)


def format_datetime(value: _dt.datetime, *, persian: bool = True) -> str:
    """«شنبه ۲۴ مهر ۱۴۰۵ — ۱۵:۳۰»."""
    clock = format_clock(value.hour, value.minute, persian=persian)
    return f"{format_jalali_long(value.date())} — {clock}"


def date_range_label(start: _dt.date, end: _dt.date) -> str:
    """بازهٔ تاریخ شمسی برای نمایش."""
    return f"{format_jalali_long(start)} تا {format_jalali_long(end)}"


def days_between(start: _dt.date, end: _dt.date) -> int:
    """فاصلهٔ روزها (end - start)."""
    return (end - start).days


def clamp_date(value: _dt.date, low: _dt.date, high: _dt.date) -> _dt.date:
    return max(low, min(high, value))


def iter_dates(start: _dt.date, end: _dt.date) -> Iterable[_dt.date]:
    """پیمایش بازهٔ تاریخ شمسی/میلادی شامل هر دو انتها."""
    current = start
    while current <= end:
        yield current
        current += _dt.timedelta(days=1)
