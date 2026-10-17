"""پارامترهای قابل تنظیم محصول.

قاعده محصول (سند اجرایی، بند ۹): هیچ عدد الگوریتمی که شواهد قطعی ندارد
نباید به‌عنوان «حقیقت» در کد ثابت شود. همهٔ اعداد زیر **فرضیهٔ محصول**
هستند ([H])، برچسب‌دار، قابل تنظیم و در رابط کاربری قابل ویرایش‌اند.

هر مقدار `Settings` از یک فایل JSON در پوشهٔ دادهٔ کاربر خوانده می‌شود و
در صورت نبود فایل، پیش‌فرض‌های زیر استفاده می‌شوند.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# مسیرهای داده
# ---------------------------------------------------------------------------


def app_data_dir() -> Path:
    """پوشهٔ دادهٔ کاربر (مناسب ویندوز/لینوکس/مک)."""
    override = os.environ.get("K2_DATA_DIR")
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "K2KonkurAdvisor"
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "k2"
    return Path.home() / ".local" / "share" / "k2"


def database_path() -> Path:
    return app_data_dir() / "k2.db"


def settings_path() -> Path:
    return app_data_dir() / "settings.json"


# ---------------------------------------------------------------------------
# تنظیمات
# ---------------------------------------------------------------------------


@dataclass
class CapacitySettings:
    """پارامترهای ظرفیت روزانه (سند تحقیق ۲، بخش ۲)."""

    #: حاشیهٔ اطمینان؛ فرضیهٔ محصول [H] — «همیشه کمی کمتر از ظرفیت».
    safety_margin: float = 0.20
    #: ضریب تمرکز؛ تا دادهٔ واقعی کاربر جمع نشود محافظه‌کارانه است [H].
    focus_factor: float = 0.60
    #: ضریب انرژی بر پایهٔ خودگزارشی روزانه (۱→۰٫۶، ۲→۰٫۸، ۳→۱٫۰) [H].
    energy_factors: dict[int, float] = field(
        default_factory=lambda: {1: 0.60, 2: 0.80, 3: 1.00}
    )
    #: حداقل/حداکثر اندازهٔ بلوک مطالعه به دقیقه.
    min_block_minutes: int = 30
    max_block_minutes: int = 90
    #: تعداد روزهایی که «ظرفیت قابل جبران» برای نسبت بدهی محاسبه می‌شود.
    recovery_window_days: int = 7


@dataclass
class SchedulerSettings:
    """وزن‌های امتیاز اولویت (سند تحقیق ۲، بخش ۷). همه فرضیه [H]."""

    w_deadline: float = 3.0
    w_blocked_dependents: float = 2.0
    w_topic_weakness: float = 2.0
    w_review_overdue: float = 2.0
    w_debt_age: float = 1.0
    w_time_cost: float = 0.5
    #: ضریب اضافه برای مهلت سخت نسبت به مهلت نرم.
    hard_deadline_multiplier: float = 3.0
    #: سقف تعداد بازچینی خودکار برنامه در روز (SCH-05).
    max_auto_reschedules_per_day: int = 2
    #: حداقل نسبت زمانی که یک فعالیت تقسیم‌پذیر باید در یک بلوک بگیرد.
    split_min_chunk: int = 20


@dataclass
class ReviewSettings:
    """پارامترهای مرور تطبیقی (سند تحقیق ۱، بخش ۳)."""

    ease_initial: float = 2.0
    ease_min: float = 1.3
    ease_max: float = 2.8
    ease_delta_success: float = 0.05
    ease_delta_hard: float = 0.20
    ease_delta_guessed: float = 0.05
    #: فاصلهٔ سقف: نسبتی از روزهای باقی‌مانده تا آزمون [H].
    exam_cap_ratio: float = 0.25
    #: سقف روزانهٔ مرور به‌صورت نسبتی از ظرفیت روز [H].
    daily_review_cap_ratio: float = 0.30
    #: تعداد دفعات فراموشی که آیتم را به «تکراری/leech» تبدیل می‌کند.
    leech_lapse_threshold: int = 4
    #: اگر آیتم بیش از این ضریب از موعد گذشته باشد، بدهی مرور فشرده می‌شود.
    overdue_compression_factor: float = 2.0
    #: حداقل تعداد مرور پیاپی موفق برای ورود به حالت نگهداری.
    maintenance_streak: int = 3
    #: اولین بازیابی حداکثر چند ساعت پس از یادگیری.
    first_review_hours: int = 24
    #: سقف بیشینهٔ فاصلهٔ مرور (روز) — جلوگیری از سرریز تاریخ و مرور بی‌پایان.
    max_interval_days: int = 365


@dataclass
class BacklogSettings:
    """سطوح بدهی و سقف جبران (سند تحقیق ۲، بخش ۱۱)."""

    green_max: float = 0.30
    yellow_max: float = 0.70
    orange_max: float = 1.00
    #: سقف کار جبرانی روزانه به‌صورت نسبتی از ظرفیت [H].
    compensation_cap_ratio: float = 0.30
    #: سهم ظرفیت روز حداقلی نسبت به ظرفیت معمول [H].
    minimal_day_ratio: float = 0.30
    #: بار روز اول پس از وقفهٔ چندروزه [H].
    return_load_ratio: float = 0.40
    #: تعداد روزی که وقفه «چندروزه» شمرده می‌شود.
    break_threshold_days: int = 3
    #: تعداد روزی که بدهی مرور پس از وقفه تخلیه می‌شود.
    review_backlog_drain_days: int = 5


@dataclass
class AdvisorSettings:
    """فازهای زمانی و سطوح تسلط (سند تحقیق ۴، بخش ۱)."""

    #: نوارهای فاز بر حسب **حداکثر** روز باقی‌مانده تا آزمون [H] — نه قانون علمی.
    #: روزهای آخر: ≤ ۷ روز | جمع‌بندی: ≤ ۳۰ روز | تشدید: ≤ ۹۰ روز |
    #: تثبیت: ≤ ۱۸۰ روز | بنیان: بیشتر از ۱۸۰ روز.
    phase_final_days: int = 7
    phase_summarization_days: int = 30
    phase_intensification_days: int = 90
    phase_consolidation_days: int = 180
    #: آستانه‌های سطح تسلط L0..L4 [H].
    mastery_l1_max: float = 0.40
    mastery_l2_max: float = 0.70
    mastery_l3_max: float = 0.85
    #: حداقل نمونهٔ لازم برای کالیبراسیون تخمین زمان (EST-02).
    calibration_min_samples: int = 5
    #: ضریب تخمین وقتی داده کافی نیست [H].
    calibration_default_ratio: float = 1.30
    #: صدکی از نسبت‌های گذشته که برای تخمین استفاده می‌شود [H].
    calibration_percentile: float = 0.70


@dataclass
class UiSettings:
    """تنظیمات نمایش."""

    persian_digits: bool = True
    font_family: str = "Vazirmatn"
    font_size: int = 11
    week_starts_on: str = "saturday"  # هفتهٔ شنبه‌محور


@dataclass
class Settings:
    """تنظیمات کامل برنامه."""

    capacity: CapacitySettings = field(default_factory=CapacitySettings)
    scheduler: SchedulerSettings = field(default_factory=SchedulerSettings)
    review: ReviewSettings = field(default_factory=ReviewSettings)
    backlog: BacklogSettings = field(default_factory=BacklogSettings)
    advisor: AdvisorSettings = field(default_factory=AdvisorSettings)
    ui: UiSettings = field(default_factory=UiSettings)

    # ---- بارگذاری/ذخیره ----

    @classmethod
    def load(cls, path: Path | str | None = None) -> "Settings":
        """تنظیمات را از فایل JSON می‌خواند؛ نبود فایل یا کلید نامعتبر خطا نیست."""
        target = Path(path) if path is not None else settings_path()
        settings = cls()
        if not target.exists():
            return settings
        try:
            raw = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return settings
        if not isinstance(raw, dict):
            return settings
        for f in fields(cls):
            if f.name not in raw:
                continue
            section = getattr(settings, f.name)
            value = raw[f.name]
            if isinstance(value, dict) and hasattr(section, "__dataclass_fields__"):
                for sub in fields(section):
                    if sub.name in value:
                        setattr(section, sub.name, value[sub.name])
        return settings

    def save(self, path: Path | str | None = None) -> Path:
        """تنظیمات را در فایل JSON ذخیره می‌کند و مسیر آن را برمی‌گرداند."""
        target = Path(path) if path is not None else settings_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return target

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
