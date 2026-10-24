"""تقویم آزمون سراسری: چه چیزی رسمی است و چه چیزی پیش‌بینی.

چرا این ماژول جدا است: تاریخ کنکور تا اعلام اطلاعیهٔ سازمان سنجش «نامشخص»
است و هیچ تاریخی که از روال سال‌های گذشته حدس زده شود «تاریخ رسمی» نیست. این
ماژول مرز را صریح نگه می‌دارد:

* ``ANNOUNCED`` — حقایقی که سازمان سنجش اعلام کرده (ساختار نمره‌دهی، نوبت
  آزمون‌های دیگر). این‌ها روی برنامه‌ریزی اثر می‌گذارند.
* ``PREDICTION`` — بازهٔ تاریخی که از روال سال‌های گذشته گرفته شده. فقط
  پیشنهادِ «تاریخ هدف شخصی» است و هرگز به‌جای تاریخ رسمی نمایش داده نمی‌شود.

بررسی روز: ۲۰۲۶-۱۰-۲۴. منبع‌ها در ``SOURCES`` ثبت شده‌اند.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Optional

#: روز بررسی اطلاعات. اگر از این تاریخ گذشته باشد، وضعیت را دوباره بسنج.
CHECKED_ON = _dt.date(2026, 10, 24)

#: حقایق اعلام‌شدهٔ سازمان سنجش برای کنکور ۱۴۰۶ (تأییدشده، نه پیش‌بینی).
ANNOUNCED: tuple[dict, ...] = (
    {
        "key": "score_split",
        "text": "در گروه‌های ریاضی، تجربی و انسانی ۶۰٪ نمرهٔ کل از سوابق "
                "تحصیلی و ۴۰٪ از آزمون اختصاصی است.",
        "effect": "سوابق تحصیلی وزن برابر با نیمی از آزمون دارد؛ برنامه فقط "
                  "روی آزمون اختصاصی بسته نمی‌شود.",
    },
    {
        "key": "grade_eleven_definitive",
        "text": "نمرهٔ پایهٔ یازدهم در کنکور ۱۴۰۶ قطعی است (دیگر به‌صورت "
                "رتبه‌بندی/گرایش نیست).",
        "effect": "پایهٔ یازدهم دیگر «پایهٔ گذرگاهی» نیست و باید مثل پایهٔ "
                  "دوازدهم برنامه‌ریزی شود.",
    },
)

#: چه چیزی هنوز اعلام نشده و برنامه چگونه صادقانه با آن رفتار می‌کند.
UNANNOUNCED: tuple[dict, ...] = (
    {
        "key": "exam_date",
        "text": "تاریخ برگزاری کنکور سراسری ۱۴۰۶ هنوز اعلام نشده است.",
        "behaviour": "هیچ تاریخی در برنامه ثابت نمی‌شود؛ کاربر یک «تاریخ هدف "
                     "شخصی» می‌گذارد که صریحاً با برچسب «تخمینی/شخصی» دیده "
                     "می‌شود، نه تاریخ رسمی.",
    },
)

#: پیش‌بینی بازهٔ برگزاری از روی روال سال‌های گذشته. **پیش‌بینی است، نه
#: تاریخ رسمی** و هرگز به‌عنوان منبع معتبر معرفی نمی‌شود.
PREDICTION: dict = {
    "label": "پیش‌بینی از روی روال سال‌های گذشته — تاریخ رسمی نیست",
    "window": ("۱۴۰۶/۰۴/۱۱", "۱۴۰۶/۰۴/۱۵"),
    "basis": "کنکور ۱۴۰۵ در ۲۹ و ۳۰ مرداد ۱۴۰۵ برگزار شد؛ برگزاری در تیرماه "
             "روال معمول سال‌های اخیر است.",
}

#: منابع بررسی‌شده (برای شفافیت؛ برنامه به این نشانی‌ها وصل نمی‌شود).
SOURCES: tuple[dict, ...] = (
    {"title": "پایگاه اطلاع‌رسانی سازمان سنجش", "url": "https://www.sanjesh.org",
     "note": "مرجع معتبر تاریخ و مقررات؛ تا اعلام اطلاعیه هر عددی پیش‌بینی است."},
    {"title": "خبرگزاری رکنا — جزئیات کنکور ۱۴۰۶",
     "url": "https://www.rokna.net/",
     "note": "اعلام ۶۰٪ سوابق + ۴۰٪ اختصاصی و قطعی‌بودن پایهٔ یازدهم."},
    {"title": "کافه‌نت — تقویم کنکور",
     "url": "https://cafeneti.com/taghvim-konkor/",
     "note": "ثبت نبود تاریخ رسمی ۱۴۰۶ و تاریخ برگزاری ۱۴۰۵."},
)


@dataclass
class CalendarStatus:
    """وضعیت تقویم آزمون: چه چیزی اعلام شده و چه چیزی نه."""

    checked_on: _dt.date = CHECKED_ON
    announced: tuple[dict, ...] = field(default_factory=lambda: ANNOUNCED)
    unannounced: tuple[dict, ...] = field(default_factory=lambda: UNANNOUNCED)
    prediction: dict = field(default_factory=lambda: dict(PREDICTION))
    sources: tuple[dict, ...] = field(default_factory=lambda: SOURCES)

    @property
    def date_is_announced(self) -> bool:
        return not any(item["key"] == "exam_date" for item in self.unannounced)

    @property
    def is_stale(self) -> bool:
        """اگر بررسی بیش از ۳۰ روز پیش بوده باشد، دوباره سنجیده شود."""
        return (_dt.date.today() - self.checked_on).days > 30

    def summary(self) -> str:
        """یک خط خلاصه برای نمایش در رابط کاربری."""
        if self.date_is_announced:
            return "تاریخ آزمون اعلام شده است."
        return (
            "تاریخ کنکور ۱۴۰۶ هنوز اعلام نشده؛ برنامه روی «تاریخ هدف شخصی» "
            "کار می‌کند که با برچسب «تخمینی» دیده می‌شود."
        )


def status() -> CalendarStatus:
    return CalendarStatus()


def prediction_window() -> tuple[str, str]:
    """بازهٔ پیش‌بینی‌شده به‌صورت (شروع، پایان) شمسی — صرفاً پیشنهاد."""
    return (PREDICTION["window"][0], PREDICTION["window"][1])


def prediction_label() -> str:
    return PREDICTION["label"]


def announced_effects() -> list[str]:
    """اثر حقایق اعلام‌شده روی برنامه‌ریزی."""
    return [item["effect"] for item in ANNOUNCED]


def planning_hint(profile) -> Optional[str]:
    """راهنمای صادقانه برای تاریخ هدف، بر پایهٔ پروفایل کاربر.

    اگر کاربر تاریخی ثبت کرده و وضعیتش «نامشخص» است، یادآوری می‌شود که این
    تاریخ هدف شخصی است نه تاریخ رسمی. اگر پروفایلی نباشد، ``None``.
    """
    if profile is None:
        return None
    if profile.target_date is None:
        return (
            "تاریخ آزمون اعلام نشده؛ یک تاریخ هدف شخصی بگذار تا برنامه فاز و "
            "مهلت داشته باشد. این تاریخ با برچسب «تخمینی» نمایش داده می‌شود."
        )
    if profile.date_status.value == "official":
        return None
    return (
        f"تاریخ {profile.target_date} هدف شخصی توست، نه تاریخ رسمی آزمون. "
        "با اطلاعیهٔ سازمان سنجش به‌روزش کن."
    )
