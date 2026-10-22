"""تایمر مطالعهٔ درون‌برنامه‌ای و جمع‌های خالص روزانه/هفتگی (بند ۱۵).

قواعد محصول:

* دقیقهٔ ثبت‌شده همیشه **خالص** است — زمان استراحت از بازهٔ شروع تا پایان
  کم می‌شود. کلاس جدا از مطالعهٔ مستقل شمرده می‌شود تا ساعت درس، ساعت
  مطالعهٔ شخصی را پنهان نکند.
* اصلاح یک جلسهٔ ثبت‌شده از حذف و بازنویسی عبور نمی‌کند؛ مقدار قبلی در
  ``study_session_revision`` می‌ماند و تاریخچهٔ تغییر دیده می‌شود.
* جلسهٔ ناتمام در پایگاه داده می‌ماند، بنابراین بستن و باز کردن برنامه
  تایمر را از بین نمی‌برد.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Optional, Sequence

from .domain.enums import SessionKind
from .domain.models import (
    LearningProblem,
    SessionTotals,
    StudySession,
    StudySessionRevision,
    TopicDeadline,
)

#: انواع جلسه‌ای که «زمان کلاس» شمرده می‌شوند و از مطالعهٔ مستقل جدا هستند.
CLASS_KINDS = frozenset({SessionKind.LIVE_CLASS, SessionKind.RECORDED_CLASS})

#: انواعی که به «تست/تحلیل/مرور/تثبیت» نگاشت می‌شوند.
ANALYSIS_KINDS = frozenset({SessionKind.ANALYSIS})
TEST_KINDS = frozenset({SessionKind.TEST})
REVIEW_KINDS = frozenset({SessionKind.REVIEW})
CONSOLIDATION_KINDS = frozenset({SessionKind.CONSOLIDATION})


@dataclass
class TimerSnapshot:
    """وضعیت لحظه‌ای تایمر برای نمایش در رابط کاربری."""

    running: bool = False
    paused: bool = False
    elapsed_seconds: int = 0
    paused_seconds: int = 0
    net_seconds: int = 0
    kind: SessionKind = SessionKind.STUDY
    topic_id: Optional[int] = None
    started_at: Optional[_dt.datetime] = None

    @property
    def net_minutes(self) -> int:
        return int(self.net_seconds // 60)

    @property
    def display(self) -> str:
        """نمایش ساعت:دقیقه:ثانیه."""
        total = max(0, int(self.net_seconds))
        hours, rem = divmod(total, 3600)
        minutes, seconds = divmod(rem, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class StudyTimer:
    """تایمر واقعی با start/pause/resume/stop.

    تایمر از ساعت دیوار («wall clock») استفاده می‌کند، پس اگر برنامه بسته
    و باز شود هم می‌توان آن را ادامه داد؛ هیچ حلقهٔ شمارش در حافظه‌ای
    نگه نداریم که با بستن برنامه از بین برود.
    """

    def __init__(
        self,
        session: Optional[StudySession] = None,
        *,
        now: Optional[_dt.datetime] = None,
    ):
        self._session = session
        self._paused = False
        self._last_resume: Optional[_dt.datetime] = None
        #: لحظهٔ شروع استراحتِ باز (در پایگاه داده ذخیره شده است).
        self._pause_started: Optional[_dt.datetime] = None
        if session is not None and session.ended_at is None:
            # جلسهٔ ناتمامِ ذخیره‌شده: تایمر در حالت pause بازگشایی می‌شود
            # تا زمان بسته‌بودن برنامه به‌عنوان مطالعه شمرده نشود.
            self._paused = True
            self._pause_started = session.paused_at
        self._now_override = now

    # ---- ابزار ----

    def _now(self) -> _dt.datetime:
        if self._now_override is None:
            return _dt.datetime.now()
        return self._now_override()

    @property
    def session(self) -> Optional[StudySession]:
        return self._session

    @property
    def is_active(self) -> bool:
        return self._session is not None and self._session.ended_at is None

    def snapshot(self) -> TimerSnapshot:
        if self._session is None or self._session.started_at is None:
            return TimerSnapshot()
        session = self._session
        now = self._now()
        elapsed = max(0, int((now - session.started_at).total_seconds()))
        paused = int(session.paused_seconds)
        if self._paused:
            # استراحتِ در جریان (چه همین نشست، چه از نشستِ قبلیِ ذخیره‌شده)
            # هنوز به paused_seconds اضافه نشده است.
            pause_start = self._last_resume or self._pause_started
            if pause_start is not None:
                paused += max(0, int((now - pause_start).total_seconds()))
        return TimerSnapshot(
            running=session.ended_at is None and not self._paused,
            paused=session.ended_at is None and self._paused,
            elapsed_seconds=elapsed,
            paused_seconds=paused,
            net_seconds=max(0, elapsed - paused),
            kind=session.kind,
            topic_id=session.topic_id,
            started_at=session.started_at,
        )

    # ---- چرخهٔ عمر ----

    def start(
        self,
        *,
        kind: SessionKind = SessionKind.STUDY,
        subject_id: Optional[int] = None,
        topic_id: Optional[int] = None,
        activity_id: Optional[int] = None,
        note: str = "",
    ) -> StudySession:
        """جلسهٔ تازه را آغاز می‌کند."""
        if self.is_active:
            raise RuntimeError("یک جلسهٔ مطالعه در حال اجراست؛ ابتدا آن را ببند.")
        started = self._now().replace(microsecond=0)
        self._session = StudySession(
            subject_id=subject_id,
            topic_id=topic_id,
            activity_id=activity_id,
            kind=kind,
            mode="timer",
            started_at=started,
            ended_at=None,
            paused_seconds=0,
            minutes=0,
            note=note,
        )
        self._paused = False
        self._last_resume = started
        return self._session

    def pause(self) -> TimerSnapshot:
        """استراحت را باز می‌کند.

        جمع استراحت‌ها همین لحظه به‌روز نمی‌شود؛ تنها نقطهٔ شروع استراحت
        ذخیره می‌شود تا اگر برنامه بسته شد، زمان بسته‌بودن هم جزء استراحت
        بماند و به‌عنوان مطالعه شمرده نشود.
        """
        if not self.is_active or self._paused:
            return self.snapshot()
        now = self._now()
        self._paused = True
        self._last_resume = None
        self._pause_started = now.replace(microsecond=0)
        self._session.paused_at = self._pause_started
        return self.snapshot()

    def resume(self) -> TimerSnapshot:
        if not self.is_active or not self._paused:
            return self.snapshot()
        now = self._now()
        # استراحتی که از نشست قبلی (مثلاً وقتی برنامه بسته بود) باز مانده
        # بود، همین حالا به جمع استراحت‌ها اضافه می‌شود.
        if self._pause_started is not None:
            self._session.paused_seconds += max(
                0, int((now - self._pause_started).total_seconds())
            )
            self._pause_started = None
            self._session.paused_at = None
        self._paused = False
        self._last_resume = now
        return self.snapshot()

    def toggle(self) -> TimerSnapshot:
        """یک دکمه برای pause/resume."""
        if self._paused:
            return self.resume()
        return self.pause()

    def stop(self, *, note: str = "") -> StudySession:
        """جلسه را می‌بندد و دقیقهٔ خالص را نهایی می‌کند."""
        if not self.is_active:
            raise RuntimeError("جلسهٔ فعالی برای بستن نیست.")
        now = self._now().replace(microsecond=0)
        if self._paused and self._pause_started is not None:
            # استراحت تا لحظهٔ پایان ادامه داشته است؛ به جمع استراحت‌ها
            # اضافه می‌شود تا دقیقهٔ خالص واقعی بماند.
            self._session.paused_seconds += max(
                0, int((now - self._pause_started).total_seconds())
            )
        self._session.ended_at = now
        self._session.paused_at = None
        self._session.minutes = net_minutes(self._session)
        if note:
            self._session.note = note
        self._paused = False
        self._last_resume = None
        return self._session

    def discard(self) -> None:
        """جلسهٔ فعال را دور می‌اندازد (ثبت نمی‌شود)."""
        self._session = None
        self._paused = False
        self._last_resume = None
        self._pause_started = None


def net_minutes(session: StudySession) -> int:
    """دقیقهٔ خالص یک جلسه: بازهٔ کل منهای استراحت."""
    if session.started_at is None:
        return 0
    end = session.ended_at or _dt.datetime.now()
    gross = max(0, int((end - session.started_at).total_seconds()))
    return max(0, (gross - max(0, int(session.paused_seconds))) // 60)


def session_is_class(session: StudySession) -> bool:
    return session.kind in CLASS_KINDS


def totals_for(
    sessions: Sequence[StudySession], label: str = ""
) -> SessionTotals:
    """جمع خالص با تفکیک کلاس / مطالعهٔ مستقل / تست / تحلیل / مرور / تثبیت."""
    totals = SessionTotals(label=label)
    for session in sessions:
        minutes = max(0, int(session.minutes))
        totals.total_minutes += minutes
        totals.session_count += 1
        if session.kind in CLASS_KINDS:
            totals.class_minutes += minutes
        elif session.kind in TEST_KINDS:
            totals.test_minutes += minutes
        elif session.kind in ANALYSIS_KINDS:
            totals.analysis_minutes += minutes
        elif session.kind in REVIEW_KINDS:
            totals.review_minutes += minutes
        elif session.kind in CONSOLIDATION_KINDS:
            totals.consolidation_minutes += minutes
        else:
            totals.independent_minutes += minutes
    return totals


def daily_totals(sessions: Sequence[StudySession]) -> dict[_dt.date, SessionTotals]:
    """جمع روزانه؛ کلید تاریخ شمسیِ میلادیِ روز است."""
    buckets: dict[_dt.date, list[StudySession]] = {}
    for session in sessions:
        if session.started_at is None:
            continue
        buckets.setdefault(session.started_at.date(), []).append(session)
    return {
        day: totals_for(day_sessions, label=day.isoformat())
        for day, day_sessions in sorted(buckets.items())
    }


def week_bounds(day: _dt.date) -> tuple[_dt.date, _dt.date]:
    """مرزبندی هفتهٔ شنبه‌محور."""
    offset = (day.weekday() + 2) % 7  # شنبه = ۰
    start = day - _dt.timedelta(days=offset)
    return start, start + _dt.timedelta(days=6)


def weekly_totals(
    sessions: Sequence[StudySession], day: Optional[_dt.date] = None
) -> SessionTotals:
    """جمع هفتگی شامل روز مورد نظر."""
    day = day or _dt.date.today()
    start, end = week_bounds(day)
    in_week = [
        s for s in sessions if s.started_at and start <= s.started_at.date() <= end
    ]
    return totals_for(in_week, label=f"{start.isoformat()}..{end.isoformat()}")


def planned_vs_actual(
    planned_minutes: int, sessions: Sequence[StudySession]
) -> dict[str, object]:
    """مقایسهٔ برنامه‌ریزی‌شده با اجراشده به‌همراه نسبت و پیام."""
    totals = totals_for(sessions)
    planned = max(0, int(planned_minutes))
    actual = totals.total_minutes
    ratio = (actual / planned) if planned > 0 else 0.0
    if planned == 0:
        message = "برای این بازه برنامه‌ای ثبت نشده است."
    elif actual >= planned:
        message = "اجرا از برنامه بیشتر یا مساوی آن است."
    elif ratio >= 0.75:
        message = "اجرا نزدیک به برنامه است."
    else:
        message = "اجرا کمتر از برنامه است؛ علت را در بازبینی شبانه ثبت کن."
    return {
        "planned_minutes": planned,
        "actual_minutes": actual,
        "class_minutes": totals.class_minutes,
        "independent_minutes": totals.independent_minutes,
        "ratio": round(ratio, 3),
        "message": message,
    }


def revise_session(
    session: StudySession,
    *,
    field_name: str,
    new_value: object,
    reason: str,
    now: Optional[_dt.datetime] = None,
) -> StudySessionRevision:
    """یک فیلد از جلسه را اصلاح می‌کند و تاریخچه می‌سازد.

    مقدار قبلی هرگز بازنویسی نمی‌شود؛ در جدول تاریخچه می‌ماند.
    """
    if session.id is None:
        raise ValueError("برای اصلاح، جلسه باید ذخیره‌شده باشد.")
    allowed = {
        "minutes": int,
        "kind": str,
        "topic_id": int,
        "subject_id": int,
        "note": str,
        "started_at": str,
        "ended_at": str,
    }
    if field_name not in allowed:
        raise ValueError(f"فیلد «{field_name}» قابل اصلاح نیست.")
    old_value = getattr(session, field_name)
    if field_name in {"minutes", "topic_id", "subject_id"}:
        old_text = "" if old_value is None else str(old_value)
    elif field_name == "kind":
        old_text = getattr(old_value, "value", str(old_value))
    else:
        old_text = str(old_value)

    if field_name == "minutes":
        value = int(new_value)
        if value < 0:
            raise ValueError("دقیقهٔ جلسه نمی‌تواند منفی باشد.")
        session.minutes = value
        new_text = str(value)
    elif field_name == "kind":
        kind = new_value if isinstance(new_value, SessionKind) else SessionKind(str(new_value))
        session.kind = kind
        new_text = kind.value
    elif field_name in {"topic_id", "subject_id"}:
        setattr(session, field_name, int(new_value) if new_value is not None else None)
        new_text = "" if new_value is None else str(new_value)
    else:
        setattr(session, field_name, str(new_value))
        new_text = str(new_value)

    session.mode = session.mode or "manual"
    if session.mode == "timer" and field_name in {"minutes", "started_at", "ended_at"}:
        session.mode = "corrected"
    return StudySessionRevision(
        session_id=session.id,
        at=(now or _dt.datetime.now()).replace(microsecond=0),
        field_name=field_name,
        old_value=old_text,
        new_value=new_text,
        reason=reason.strip() or "اصلاح دستی",
    )


def session_kind_label(kind: SessionKind) -> str:
    return kind.label


def open_problems_for_topic(
    problems: Sequence[LearningProblem], topic_id: Optional[int]
) -> list[LearningProblem]:
    """مشکلات باز یک مبحث — ورودی صفحهٔ مشکلات و اولویت‌دهی."""
    if topic_id is None:
        return [p for p in problems if p.is_open and p.topic_id is None]
    return [p for p in problems if p.is_open and p.topic_id == topic_id]


def deadline_link_note(deadline: TopicDeadline, sessions: Sequence[StudySession]) -> str:
    """پیام اتصال جلسات به یک مهلت (برای صفحهٔ مهلت‌ها)."""
    minutes = deadline_progress_ratio(deadline, sessions)
    if minutes <= 0:
        return "هنوز زمانی به این مهلت اختصاص نیافته است."
    return f"{int(minutes)} دقیقه تا این مهلت ثبت شده است."


__all__ = [
    "ANALYSIS_KINDS",
    "CLASS_KINDS",
    "CONSOLIDATION_KINDS",
    "REVIEW_KINDS",
    "TEST_KINDS",
    "StudyTimer",
    "TimerSnapshot",
    "daily_totals",
    "deadline_link_note",
    "net_minutes",
    "open_problems_for_topic",
    "planned_vs_actual",
    "revise_session",
    "session_is_class",
    "session_kind_label",
    "totals_for",
    "week_bounds",
    "weekly_totals",
]
