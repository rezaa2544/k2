"""تخمین زمان فعالیت و کالیبراسیون از دادهٔ واقعی (EST-01/EST-02).

قاعده: تا پیش از جمع‌آوری حداقل ۵ نمونه، پیش‌فرض **محافظه‌کارانه** استفاده
می‌شود (ضریب ۱٫۳ روی برآورد کاربر).
"""

from __future__ import annotations

import datetime as _dt
import statistics
from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence

from .config import Settings
from .domain.enums import ActivityType
from .domain.models import Activity

#: ضریب پیش‌فرض وقتی داده کافی نیست (فرضیهٔ محصول [H]).
DEFAULT_RATIO = 1.30


@dataclass
class TypeCalibration:
    """کالیبراسیون برای یک نوع فعالیت."""

    activity_type: ActivityType
    samples: int = 0
    ratio: float = DEFAULT_RATIO
    median_ratio: float = DEFAULT_RATIO

    @property
    def is_calibrated(self) -> bool:
        return self.samples >= 5


@dataclass
class EstimationModel:
    """مدل تخمین زمان بر پایهٔ تاریخچهٔ کاربر."""

    calibrations: dict[ActivityType, TypeCalibration] = field(default_factory=dict)
    global_samples: int = 0
    global_ratio: float = DEFAULT_RATIO

    def ratio_for(self, activity_type: ActivityType) -> float:
        calibration = self.calibrations.get(activity_type)
        if calibration and calibration.is_calibrated:
            return calibration.ratio
        return DEFAULT_RATIO

    def predict(self, activity: Activity) -> int:
        """زمان پیش‌بینی‌شدهٔ انجام یک فعالیت به دقیقه."""
        if activity.remaining_minutes > 0:
            return activity.remaining_minutes
        ratio = self.ratio_for(activity.type)
        return int(round(activity.est_minutes * ratio))


def _percentile(values: Sequence[float], fraction: float) -> float:
    if not values:
        return DEFAULT_RATIO
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def calibrate(
    activities: Sequence[Activity],
    *,
    settings: Optional[Settings] = None,
    since: Optional[_dt.date] = None,
) -> EstimationModel:
    """کالیبراسیون از فعالیت‌های انجام‌شده.

    برای هر نوع فعالیت، نسبت ``actual/est`` جمع‌آوری و صدک ۷۰ آن به‌عنوان
    ضریب پیش‌بینی استفاده می‌شود (سند ۲، بخش ۳).
    """
    settings = settings or Settings()
    minimum = settings.advisor.calibration_min_samples
    percentile = settings.advisor.calibration_percentile

    buckets: dict[ActivityType, list[float]] = {}
    all_ratios: list[float] = []

    for activity in activities:
        if activity.actual_minutes <= 0 or activity.est_minutes <= 0:
            continue
        if since is not None and activity.created_at is not None:
            if activity.created_at.date() < since:
                continue
        ratio = activity.actual_minutes / activity.est_minutes
        buckets.setdefault(activity.type, []).append(ratio)
        all_ratios.append(ratio)

    model = EstimationModel()
    for activity_type, ratios in buckets.items():
        model.calibrations[activity_type] = TypeCalibration(
            activity_type=activity_type,
            samples=len(ratios),
            ratio=_percentile(ratios, percentile) if len(ratios) >= minimum else DEFAULT_RATIO,
            median_ratio=statistics.median(ratios),
        )

    model.global_samples = len(all_ratios)
    model.global_ratio = (
        _percentile(all_ratios, percentile) if len(all_ratios) >= minimum else DEFAULT_RATIO
    )
    return model


def focus_factor_from_history(
    activities: Sequence[Activity],
    *,
    days: int = 14,
    settings: Optional[Settings] = None,
) -> float:
    """ضریب تمرکز از تاریخچهٔ اجرا.

    نسبت «دقیقهٔ عمیق واقعی» به «دقیقهٔ برنامه‌ریزی‌شده» در ۱۴ روز گذشته.
    """
    settings = settings or Settings()
    if not activities:
        return settings.capacity.focus_factor

    planned = 0
    actual = 0
    for activity in activities:
        if activity.actual_minutes <= 0:
            continue
        planned += activity.est_minutes
        actual += activity.actual_minutes
    if planned <= 0:
        return settings.capacity.focus_factor

    ratio = actual / planned
    # محدودسازی به بازهٔ منطقی
    return max(0.2, min(1.2, ratio))


def estimation_bias_report(
    activities: Sequence[Activity], settings: Optional[Settings] = None
) -> dict[str, float]:
    """گزارش خطای تخمین به تفکیک نوع فعالیت (بازخورد آموزشی)."""
    settings = settings or Settings()
    minimum = settings.advisor.calibration_min_samples
    result: dict[str, float] = {}
    buckets: dict[ActivityType, list[tuple[int, int]]] = {}
    for activity in activities:
        if activity.actual_minutes <= 0 or activity.est_minutes <= 0:
            continue
        buckets.setdefault(activity.type, []).append(
            (activity.est_minutes, activity.actual_minutes)
        )
    for activity_type, pairs in buckets.items():
        if len(pairs) < minimum:
            result[activity_type.value] = float("nan")
            continue
        ratios = [actual / est for est, actual in pairs]
        result[activity_type.value] = (statistics.median(ratios) - 1.0) * 100.0
    return result
