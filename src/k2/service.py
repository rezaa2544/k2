"""لایهٔ سرویس: اتصال پایگاه داده به موتورهای دامنه.

این لایه، APIای است که رابط کاربری (و تست‌های end-to-end) استفاده می‌کنند.
هیچ منطق دامنه‌ای اینجا نیست؛ فقط هماهنگی و تراکنش.
"""

from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from . import activity_lifecycle, advisor_engine, backlog as backlog_mod, capacity
from . import exam_analysis, onboarding, reporting, review_engine
from .config import Settings, database_path
from .domain.enums import (
    ActivityState,
    DateStatus,
    EnergyNeed,
    ErrorCode,
    ExamKind,
    MasteryLevel,
    ReviewState,
    RoutineScope,
)
from .domain.models import (
    Activity,
    ActivityType,
    AdvisorSuggestion,
    DayPlan,
    ErrorRecord,
    ExamAttempt,
    ExamProfile,
    ExamQuestion,
    LearningEvidence,
    ReviewItem,
    ReviewLog,
    Subject,
    Topic,
    WeeklyReport,
)
from .estimation import EstimationModel, calibrate
from .scheduler import Scheduler, SchedulingContext
from .storage import Repository, create_backup, initialize, restore_backup

#: کلیدهای ذخیرهٔ تنظیمات کاربر در جدول ``settings``.
KEY_WAKE = "daily.wake_minute"
KEY_SLEEP = "daily.sleep_minute"
KEY_ENERGY = "daily.energy_level"
KEY_PEAK = "daily.peak_hours"
KEY_SUBJECT_RATIOS = "estimation.subject_ratios"

# Upgrade-only fingerprints of the exact seed dataset shipped by earlier builds.
# They are never inserted or displayed; cleanup runs only when the legacy import
# marker is present and the complete, unmodified rows still match exactly.
LEGACY_IMPORTED_EVENT_SIGNATURES = frozenset({
    ("زیست", "live_class", None, 0, 900, 1140, False, ""),
    ("فیزیک", "live_class", None, 0, 1170, 1365, False, ""),
    ("شیمی", "live_class", None, 1, 900, 1140, False, ""),
    ("دینی", "live_class", None, 1, 915, 1245, False, "هم‌پوشان با شیمی — باید در راه‌اندازی روشن شود کدام ضبط‌شده است."),
    ("زبان انگلیسی", "live_class", None, 1, 1260, 1380, False, ""),
    ("ریاضی", "live_class", None, 2, 1170, 1380, False, ""),
    ("زمین‌شناسی (ضبط‌شده)", "recorded_class", None, 2, 0, 0, True, "کلاس ضبط‌شده؛ زمان جداگانه لازم دارد و باید به‌صورت فعالیت قابل تقسیم ثبت شود."),
    ("زیست", "live_class", None, 3, 900, 1140, False, ""),
    ("عربی", "live_class", None, 3, 1155, 1260, False, ""),
    ("فیزیک", "live_class", None, 4, 900, 1170, False, ""),
    ("شیمی", "live_class", None, 4, 1170, 1365, False, ""),
    ("فارسی", "live_class", None, 5, 795, 885, False, ""),
    ("هویت اجتماعی", "live_class", None, 5, 900, 990, False, ""),
    ("ریاضی", "live_class", None, 6, 720, 900, False, ""),
})
LEGACY_IMPORTED_ROUTINE_SIGNATURES = frozenset({
    ("خواب شب", "sleep", 1380, 360, (0, 1, 2, 3, 4, 5, 6), "daily", False),
    ("خواب روز (چرت)", "sleep", 780, 810, (0, 1, 2, 3, 4, 5, 6), "daily", False),
    ("صبحانه", "meal", 420, 450, (0, 1, 2, 3, 4, 5, 6), "daily", False),
    ("ناهار", "meal", 750, 780, (0, 1, 2, 3, 4, 5, 6), "daily", False),
    ("شام", "meal", 1200, 1245, (0, 1, 2, 3, 4, 5, 6), "daily", False),
    ("استراحت", "rest", 990, 1005, (0, 1, 2, 3, 4, 5, 6), "daily", False),
    ("حمام", "hygiene", 1365, 1380, (0, 1, 2, 3, 4, 5, 6), "daily", False),
})


@dataclass
class DayContext:
    """خلاصهٔ وضعیت یک روز برای داشبورد."""

    date: _dt.date
    capacity: capacity.CapacityBreakdown
    plan: DayPlan
    backlog: backlog_mod.BacklogSummary


class AdvisorService:
    """سرویس اصلی برنامه."""

    def __init__(
        self,
        db_path: Optional[Path | str] = None,
        settings: Optional[Settings] = None,
    ):
        self.db_path = Path(db_path) if db_path is not None else database_path()
        self.conn = initialize(self.db_path)
        self.repo = Repository(self.conn)
        self._remove_untouched_legacy_schedule_seed()
        self.settings = settings or Settings.load()
        self.scheduler = Scheduler(self.settings)
        self._estimation = EstimationModel()

    # ------------------------------------------------------------------
    # چرخهٔ عمر
    # ------------------------------------------------------------------

    def close(self) -> None:
        self.conn.close()

    def commit(self) -> None:
        self.conn.commit()

    def _remove_untouched_legacy_schedule_seed(self) -> None:
        """فقط bundle نمونهٔ قدیمیِ دست‌نخورده را با marker معتبر پاک می‌کند.

        اگر حتی یک رویداد/روال تغییر کرده، رکوردی اضافه شده یا استثنایی ثبت
        شده باشد، هیچ‌چیز حذف نمی‌شود تا دادهٔ واقعی کاربر محفوظ بماند.
        """
        if self.repo.get_setting("schedule.sample_imported") != "1":
            return
        events = self.repo.list_fixed_events()
        routines = self.repo.list_routines()
        event_signatures = frozenset(
            (
                item.title, item.kind.value, item.subject_id, item.weekday,
                item.start_minute, item.end_minute, item.is_recorded, item.notes,
            )
            for item in events
        )
        routine_signatures = frozenset(
            (
                item.title, item.kind.value, item.start_minute, item.end_minute,
                tuple(sorted(item.weekdays)), item.scope.value, item.counts_as_study,
            )
            for item in routines
        )
        if (
            len(events) != len(LEGACY_IMPORTED_EVENT_SIGNATURES)
            or len(routines) != len(LEGACY_IMPORTED_ROUTINE_SIGNATURES)
            or event_signatures != LEGACY_IMPORTED_EVENT_SIGNATURES
            or routine_signatures != LEGACY_IMPORTED_ROUTINE_SIGNATURES
        ):
            return
        event_ids = tuple(item.id for item in events if item.id is not None)
        placeholders = ",".join("?" for _ in event_ids)
        if event_ids and self.conn.execute(
            f"SELECT 1 FROM event_exception WHERE event_id IN ({placeholders}) LIMIT 1",
            event_ids,
        ).fetchone():
            return

        for item in events:
            self.repo.delete_fixed_event(int(item.id))
        for item in routines:
            self.repo.delete_routine(int(item.id))
        self.repo.set_setting("schedule.sample_imported", "legacy-cleaned")
        self.conn.commit()

    # ------------------------------------------------------------------
    # تنظیمات کاربر
    # ------------------------------------------------------------------

    @property
    def wake_minute(self) -> int:
        value = self.repo.get_setting(KEY_WAKE)
        return int(value) if value else 6 * 60

    @wake_minute.setter
    def wake_minute(self, value: int) -> None:
        self.repo.set_setting(KEY_WAKE, str(int(value)))
        self.conn.commit()

    @property
    def sleep_minute(self) -> int:
        value = self.repo.get_setting(KEY_SLEEP)
        return int(value) if value else 23 * 60

    @sleep_minute.setter
    def sleep_minute(self, value: int) -> None:
        self.repo.set_setting(KEY_SLEEP, str(int(value)))
        self.conn.commit()

    @property
    def energy_level(self) -> int:
        value = self.repo.get_setting(KEY_ENERGY)
        return int(value) if value else 2

    @energy_level.setter
    def energy_level(self, value: int) -> None:
        self.repo.set_setting(KEY_ENERGY, str(int(value)))
        self.conn.commit()

    @property
    def peak_hours(self) -> list[tuple[int, int]]:
        raw = self.repo.get_setting(KEY_PEAK)
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:  # pragma: no cover
            return []
        result: list[tuple[int, int]] = []
        for item in data:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                result.append((int(item[0]), int(item[1])))
        return result

    @peak_hours.setter
    def peak_hours(self, value: Sequence[tuple[int, int]]) -> None:
        self.repo.set_setting(KEY_PEAK, json.dumps([list(v) for v in value]))
        self.conn.commit()

    # ------------------------------------------------------------------
    # پروفایل آزمون
    # ------------------------------------------------------------------

    def active_exam_profile(self) -> Optional[ExamProfile]:
        profiles = self.repo.list_exam_profiles()
        return profiles[0] if profiles else None

    def selected_subjects(self) -> list[Subject]:
        """درس‌های فعال پروفایل جاری؛ درس‌های غیرفعال از تاریخچه حذف نمی‌شوند."""
        profile = self.active_exam_profile()
        return self.repo.list_subjects(
            profile.id if profile else None, include_unselected=False
        )

    def create_exam_profile(self, profile: ExamProfile) -> int:
        profile_id = self.repo.create_exam_profile(profile)
        self.conn.commit()
        return profile_id

    def update_exam_profile(self, profile: ExamProfile) -> None:
        self.repo.update_exam_profile(profile)
        self.conn.commit()

    def create_subject(self, subject: Subject) -> int:
        subject_id = self.repo.create_subject(subject)
        self.conn.commit()
        return subject_id

    def create_topic(self, topic: Topic) -> int:
        topic_id = self.repo.create_topic(topic)
        self.conn.commit()
        return topic_id

    def update_topic_mastery(self, topic_id: int, level: MasteryLevel) -> None:
        """تغییر دستی فقط با برچسب خودکار/کاربر در لایهٔ UI ثبت می‌شود."""
        self.repo.update_topic_mastery(topic_id, level)
        self.conn.commit()

    def list_topics(self, subject_id: Optional[int] = None) -> list[Topic]:
        return self.repo.list_topics(subject_id)

    def list_learning_evidence(self, topic_id: Optional[int] = None) -> list[LearningEvidence]:
        return self.repo.list_learning_evidence(topic_id)

    def assess_topic(self, topic_id: int) -> advisor_engine.MasteryAssessment:
        topic = next((t for t in self.repo.list_topics() if t.id == topic_id), None)
        if topic is None:
            raise ValueError("مبحث یافت نشد.")
        evidence = [
            advisor_engine.MasteryEvidence(
                at=item.observed_on or _dt.date.today(), source=item.source,
                score=item.score, note=item.note,
            )
            for item in self.repo.list_learning_evidence(topic_id)
        ]
        return advisor_engine.assess_mastery(
            topic_id=topic.id, topic_name=topic.name, evidence=evidence,
            self_assessed=topic.self_assessed, settings=self.settings,
        )

    def record_learning_evidence(self, evidence: LearningEvidence) -> advisor_engine.MasteryAssessment:
        if evidence.observed_on is None:
            evidence.observed_on = _dt.date.today()
        if evidence.observed_on > _dt.date.today():
            raise ValueError("تاریخ سنجش نمی‌تواند در آینده باشد.")
        if not 0 <= evidence.score <= 1:
            raise ValueError("درصد پاسخ درست باید بین صفر و یک باشد.")
        if evidence.source not in {"diagnostic", "delayed", "transfer", "mixed_exam", "review"}:
            raise ValueError("نوع شاهد سنجش معتبر نیست.")
        if evidence.item_count < 0 or evidence.confidence not in {1, 2, 3, 4}:
            raise ValueError("تعداد آیتم یا میزان اطمینان نامعتبر است.")
        if evidence.duration_seconds is not None and evidence.duration_seconds < 0:
            raise ValueError("زمان پاسخ‌گویی نمی‌تواند منفی باشد.")
        self.repo.create_learning_evidence(evidence)
        assessment = self.assess_topic(int(evidence.topic_id))
        self.repo.update_topic_mastery(int(evidence.topic_id), assessment.level)
        self.conn.commit()
        return assessment

    def recommend_topic(self, topic_id: int) -> tuple[advisor_engine.MasteryAssessment, advisor_engine.Prescription]:
        topic = next((t for t in self.repo.list_topics() if t.id == topic_id), None)
        if topic is None:
            raise ValueError("مبحث یافت نشد.")
        assessment = self.assess_topic(topic_id)
        profile = self.active_exam_profile()
        deadline = (
            _dt.datetime.combine(profile.target_date, _dt.time(23, 59))
            if profile and profile.target_date else None
        )
        prescription = advisor_engine.prescribe_for_topic(
            topic=topic, subject_name=topic.subject_name,
            phase=self.study_phase(), level=assessment.level,
            deadline=deadline, settings=self.settings,
        )
        return assessment, prescription

    def generate_topic_pathway(self, topic_id: int) -> list[Activity]:
        """پیشنهاد درس‌محور را به فعالیت‌های واقعی تبدیل کند، بدون تکرار بازها."""
        _assessment, prescription = self.recommend_topic(topic_id)
        existing = [a for a in self.repo.list_activities() if a.topic_id == topic_id]
        open_titles = {
            a.title for a in existing
            if a.state not in {ActivityState.DONE, ActivityState.DROPPED, ActivityState.EXPIRED}
        }
        completed_titles = {a.title for a in existing if a.state == ActivityState.DONE}
        created: list[Activity] = []
        for activity in prescription.activities:
            if activity.title in open_titles or activity.title in completed_titles:
                continue
            self.repo.create_activity(activity)
            created.append(activity)
        self.conn.commit()
        return created

    # ------------------------------------------------------------------
    # تقویم
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_event_time(event) -> None:
        if not event.title.strip():
            raise ValueError("عنوان رویداد نمی‌تواند خالی باشد.")
        if not 0 <= event.weekday <= 6:
            raise ValueError("روز هفته باید بین شنبه تا جمعه باشد.")
        if not (0 <= event.start_minute < event.end_minute <= 1440):
            raise ValueError("بازهٔ رویداد باید در همان روز و با پایان بعد از شروع باشد.")

    @staticmethod
    def _validate_routine_time(routine) -> None:
        if not routine.title.strip():
            raise ValueError("عنوان بازهٔ ضروری نمی‌تواند خالی باشد.")
        if not (0 <= routine.start_minute <= 1439 and 0 <= routine.end_minute <= 1440):
            raise ValueError("ساعت بازه باید در محدودهٔ یک شبانه‌روز باشد.")
        if routine.start_minute == routine.end_minute:
            raise ValueError("شروع و پایان بازه نمی‌توانند یکسان باشند.")
        if not routine.weekdays or any(day not in range(7) for day in routine.weekdays):
            raise ValueError("حداقل یک روز معتبر برای تکرار انتخاب کنید.")

    def create_fixed_event(self, event) -> int:
        self._validate_event_time(event)
        event_id = self.repo.create_fixed_event(event)
        self.conn.commit()
        return event_id

    def update_fixed_event(self, event) -> None:
        self._validate_event_time(event)
        self.repo.update_fixed_event(event)
        self.conn.commit()

    def delete_fixed_event(self, event_id: int) -> None:
        self.repo.delete_fixed_event(event_id)
        self.conn.commit()

    def create_routine(self, routine) -> int:
        self._validate_routine_time(routine)
        routine_id = self.repo.create_routine(routine)
        self.conn.commit()
        return routine_id

    def update_routine(self, routine) -> None:
        self._validate_routine_time(routine)
        self.repo.update_routine(routine)
        self.conn.commit()

    def delete_routine(self, routine_id: int) -> None:
        self.repo.delete_routine(routine_id)
        self.conn.commit()

    def schedule_conflicts(self) -> list[onboarding.ScheduleConflict]:
        """تعارض‌های رویدادهای واقعی ثبت‌شده."""
        return onboarding.detect_event_conflicts(self.repo.list_fixed_events())

    # ------------------------------------------------------------------
    # برنامه‌ریزی
    # ------------------------------------------------------------------

    def build_context(self, date: Optional[_dt.date] = None) -> SchedulingContext:
        return SchedulingContext(
            wake_minute=self.wake_minute,
            sleep_minute=self.sleep_minute,
            fixed_events=self.repo.list_fixed_events(),
            routines=self.repo.list_routines(),
            exceptions=self.repo.list_exceptions(date),
            energy_level=self.energy_level,
            peak_hours=self.peak_hours,
            focus_factor=self._focus_factor(),
            settings=self.settings,
        )

    def _focus_factor(self) -> float:
        activities = self.repo.list_activities()
        finished = [a for a in activities if a.actual_minutes > 0]
        if len(finished) < 5:
            return self.settings.capacity.focus_factor
        from .estimation import focus_factor_from_history

        return focus_factor_from_history(finished, settings=self.settings)

    def plan_day(self, date: Optional[_dt.date] = None) -> DayPlan:
        """برنامهٔ یک روز را می‌سازد و ذخیره می‌کند."""
        date = date or _dt.date.today()
        activities = self._schedulable_activities(date)
        plan = self.scheduler.plan_day(date, activities, self.build_context(date))
        self.repo.replace_schedule(date, plan.placements)
        self._stamp_first_planned(plan)
        self.conn.commit()
        return plan

    def plan_range(
        self, start: Optional[_dt.date] = None, days: int = 7
    ) -> list[DayPlan]:
        start = start or _dt.date.today()
        activities = self._schedulable_activities(start)
        plans = self.scheduler.plan_range(
            start, days, activities, self.build_context(start)
        )
        for plan in plans:
            self.repo.replace_schedule(plan.date, plan.placements)
            self._stamp_first_planned(plan)
        self.conn.commit()
        return plans

    def _stamp_first_planned(self, plan: DayPlan) -> None:
        """ثبت زمان «اولین برنامه‌ریزی» برای فعالیت‌های تازه جا‌داده‌شده."""
        now = _dt.datetime.now().replace(microsecond=0)
        placed_ids = {p.activity_id for p in plan.placements}
        if not placed_ids:
            return
        for activity in self.repo.list_activities():
            if activity.id in placed_ids and activity.first_planned_at is None:
                activity.first_planned_at = now
                self.repo.update_activity(activity)

    def _schedulable_activities(self, date: _dt.date) -> list[Activity]:
        """فعالیت‌هایی که کاندید برنامه‌ریزی هستند."""
        activities = self.repo.list_activities()
        activity_lifecycle.refresh_dependency_states(activities)
        activity_lifecycle.mark_overdue(activities, date)

        blocked_counts = activity_lifecycle.count_blocked_dependents(activities)
        review_items = self.repo.list_review_items()
        today = _dt.date.today()
        weakness = self._topic_weakness()

        active_profile = self.active_exam_profile()
        profile_subjects = self.repo.list_subjects(
            active_profile.id if active_profile else None, include_unselected=True
        )
        subject_by_id = {subject.id: subject for subject in profile_subjects}
        exam_priority_enabled = self.repo.get_setting("priority.use_exam_coefficients") != "0"
        comparable_coefficients = [
            float(subject.exam_coefficient)
            for subject in profile_subjects
            if subject.exam_coefficient is not None
            and subject.exam_coefficient_status == "official_notice_republished"
            and float(subject.exam_coefficient) > 0
        ]
        max_exam_coefficient = max(comparable_coefficients, default=0.0)

        for activity in activities:
            activity.blocked_dependents = blocked_counts.get(activity.id or -1, 0)
            if activity.topic_id is not None:
                activity.topic_weakness = weakness.get(activity.topic_id, 0.0)
                subject = subject_by_id.get(activity.subject_id)
                if subject:
                    # درس از فهرست فعال خارج شده اما فعالیت قدیمی پنهان نمی‌شود؛
                    # وزن اهمیتش در اولویت خودکار کاهش می‌یابد تا انتخاب جاری اثر داشته باشد.
                    selection_factor = 1.0 if subject.is_selected else 0.25
                    # ضریب آزمون فقط یک تعدیل‌گرِ اولویت خودکار است؛ هرگز در
                    # ضریب شخصی/وزن مبحث ذخیره یا بازنویسی نمی‌شود.
                    exam_factor = 1.0
                    if (
                        exam_priority_enabled
                        and max_exam_coefficient > 0
                        and subject.exam_coefficient is not None
                        and subject.exam_coefficient_status == "official_notice_republished"
                    ):
                        # بازهٔ ضریب ۰٫۵ تا ۱٫۵؛ انتخاب شخصی و ضعف مبحث جدا می‌مانند.
                        exam_factor = 0.5 + float(subject.exam_coefficient) / max_exam_coefficient
                    activity.topic_weight = subject.effective_weight * selection_factor * exam_factor
                else:
                    activity.topic_weight = 1.0
            overdue_days = 0.0
            for item in review_items:
                if item.topic_id == activity.topic_id and item.due_date:
                    overdue_days = max(
                        overdue_days, float((today - item.due_date).days)
                    )
            activity.review_overdue_days = max(0.0, overdue_days)

        return [
            a
            for a in activities
            if a.state
            in {
                ActivityState.PLANNED,
                ActivityState.READY,
                ActivityState.BLOCKED,
                ActivityState.OVERDUE,
                ActivityState.PARTIAL,
                ActivityState.IN_PROGRESS,
            }
        ]

    def _topic_weakness(self) -> dict[int, float]:
        """ضعف مبحث از آخرین آزمون‌ها (نرمال‌شده به بازهٔ ۰..۱)."""
        attempts = self.repo.list_attempts()
        errors = self.repo.list_error_records()
        if not attempts:
            return {}
        latest_attempt = max(
            (a for a in attempts if a.taken_at),
            key=lambda a: a.taken_at,
            default=None,
        )
        if latest_attempt is None or not latest_attempt.id:
            return {}
        relevant = [e for e in errors if e.attempt_id == latest_attempt.id]
        if not relevant:
            return {}
        counts: dict[int, int] = {}
        for error in relevant:
            if error.topic_id is None:
                continue
            counts[error.topic_id] = counts.get(error.topic_id, 0) + 1
        maximum = max(counts.values()) or 1
        return {topic_id: count / maximum for topic_id, count in counts.items()}

    # ------------------------------------------------------------------
    # فعالیت‌ها
    # ------------------------------------------------------------------

    def list_activities(self) -> list[Activity]:
        return self.repo.list_activities()

    def create_activity(self, activity: Activity) -> int:
        activity_id = self.repo.create_activity(activity)
        # فعالیت وابسته باید بلافاصله «مسدود» شود، نه اینکه تا برنامه‌ریزی بعدی
        # به‌اشتباه «آماده» به نظر برسد.
        self._refresh_dependencies()
        self.conn.commit()
        return activity_id

    def _refresh_dependencies(self) -> None:
        activities = self.repo.list_activities()
        for activity, _state in activity_lifecycle.refresh_dependency_states(activities):
            self.repo.update_activity(activity)

    def start_activity(self, activity_id: int) -> None:
        activity = self.repo.get_activity(activity_id)
        if activity is None:
            raise ValueError("فعالیت یافت نشد.")
        activity_lifecycle.start_activity(activity)
        self.repo.update_activity(activity)
        self.repo.log_activity_event(
            activity_id, kind="start", note="کاربر فعالیت را شروع کرد."
        )
        self.conn.commit()

    def complete_activity(self, activity_id: int, actual_minutes: int) -> None:
        activity = self.repo.get_activity(activity_id)
        if activity is None:
            raise ValueError("فعالیت یافت نشد.")
        outcome = activity_lifecycle.complete_activity(
            activity, actual_minutes=actual_minutes, settings=self.settings
        )
        self.repo.update_activity(activity)
        self.repo.log_activity_event(
            activity_id,
            kind="complete",
            note=outcome.message,
        )
        # با تکمیل پیش‌نیاز، فعالیت‌های وابسته آزاد می‌شوند.
        self._refresh_dependencies()
        self.conn.commit()

    def partial_activity(
        self,
        activity_id: int,
        actual_minutes: int,
        resume_marker: Optional[int] = None,
    ) -> int:
        activity = self.repo.get_activity(activity_id)
        if activity is None:
            raise ValueError("فعالیت یافت نشد.")
        outcome = activity_lifecycle.partial_activity(
            activity,
            actual_minutes=actual_minutes,
            resume_marker=resume_marker,
            settings=self.settings,
        )
        self.repo.update_activity(activity)
        self.repo.log_activity_event(
            activity_id, kind="partial", note=outcome.message
        )
        self.conn.commit()
        return outcome.remaining_minutes

    def defer_activity(self, activity_id: int, reason: str) -> None:
        activity = self.repo.get_activity(activity_id)
        if activity is None:
            raise ValueError("فعالیت یافت نشد.")
        activity_lifecycle.defer_activity(activity, reason=reason)
        self.repo.update_activity(activity)
        self.repo.log_activity_event(
            activity_id, kind="defer", note=f"تعویق: {reason}"
        )
        self.conn.commit()

    def drop_activity(self, activity_id: int, reason: str) -> None:
        activity = self.repo.get_activity(activity_id)
        if activity is None:
            raise ValueError("فعالیت یافت نشد.")
        activity_lifecycle.drop_activity(activity, reason=reason)
        self.repo.update_activity(activity)
        self.repo.log_activity_event(
            activity_id, kind="drop", note=f"حذف با تأیید کاربر: {reason}"
        )
        self._refresh_dependencies()
        self.conn.commit()

    def expire_activity(self, activity_id: int, reason: str) -> None:
        activity = self.repo.get_activity(activity_id)
        if activity is None:
            raise ValueError("فعالیت یافت نشد.")
        activity_lifecycle.expire_activity(activity, reason=reason)
        self.repo.update_activity(activity)
        self.repo.log_activity_event(
            activity_id, kind="expire", note=f"انقضا: {reason}"
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # بدهی
    # ------------------------------------------------------------------

    def backlog(self, date: Optional[_dt.date] = None) -> backlog_mod.BacklogSummary:
        date = date or _dt.date.today()
        breakdown = self.build_context(date).capacity_for(date)
        return backlog_mod.build_backlog(
            date=date,
            activities=self.repo.list_activities(),
            daily_capacity_minutes=breakdown.capacity_minutes,
            settings=self.settings,
        )

    def minimal_day(self, date: Optional[_dt.date] = None) -> backlog_mod.MinimalDayPlan:
        date = date or _dt.date.today()
        breakdown = self.build_context(date).capacity_for(date)
        return backlog_mod.build_minimal_day(
            date=date,
            activities=self.repo.list_activities(),
            capacity_minutes=breakdown.capacity_minutes,
            settings=self.settings,
        )

    def triage(self, date: Optional[_dt.date] = None) -> backlog_mod.TriageList:
        date = date or _dt.date.today()
        breakdown = self.build_context(date).capacity_for(date)
        return backlog_mod.build_triage(
            activities=self.repo.list_activities(),
            date=date,
            capacity_minutes=breakdown.capacity_minutes,
            settings=self.settings,
        )

    # ------------------------------------------------------------------
    # مرور
    # ------------------------------------------------------------------

    def list_review_items(self) -> list[ReviewItem]:
        return self.repo.list_review_items()

    def create_review_item(self, item: ReviewItem) -> int:
        item_id = self.repo.create_review_item(item)
        self.conn.commit()
        return item_id

    def record_review(
        self,
        item_id: int,
        *,
        correct: bool,
        confidence: int = 2,
        seconds: Optional[int] = None,
        time_ratio: Optional[float] = None,
        today: Optional[_dt.date] = None,
    ) -> review_engine.ReviewUpdate:
        today = today or _dt.date.today()
        items = self.repo.list_review_items()
        item = next((i for i in items if i.id == item_id), None)
        if item is None:
            raise ValueError("آیتم مرور یافت نشد.")

        grade = review_engine.grade_from_result(
            correct=correct, confidence=confidence, time_ratio=time_ratio
        )
        profile = self.active_exam_profile()
        update = review_engine.apply_review(
            item,
            grade,
            today=today,
            exam_date=profile.target_date if profile else None,
            settings=self.settings,
            confidence=confidence,
            time_ratio=time_ratio,
        )
        self.repo.update_review_item(item)
        self.repo.add_review_log(
            ReviewLog(
                item_id=item_id,
                at=_dt.datetime.combine(today, _dt.datetime.now().time()),
                grade=grade,
                confidence=confidence,
                seconds=seconds,
            )
        )
        if item.topic_id is not None:
            self.repo.create_learning_evidence(
                LearningEvidence(
                    topic_id=item.topic_id,
                    observed_on=today,
                    source="review",
                    score=1.0 if correct else 0.0,
                    item_count=1,
                    confidence=confidence,
                    duration_seconds=seconds,
                    note=f"مرور فعال: {item.label}",
                )
            )
            assessment = self.assess_topic(item.topic_id)
            self.repo.update_topic_mastery(item.topic_id, assessment.level)
        self.conn.commit()
        return update

    def due_review_items(self, today: Optional[_dt.date] = None) -> list[ReviewItem]:
        today = today or _dt.date.today()
        return review_engine.due_items(self.repo.list_review_items(), today)

    # ------------------------------------------------------------------
    # آزمون
    # ------------------------------------------------------------------

    def record_attempt(
        self,
        *,
        name: str,
        total: int,
        correct: int,
        wrong: int,
        blank: int,
        kind: ExamKind = ExamKind.MOCK,
        subject_id: Optional[int] = None,
        duration_minutes: int = 0,
        taken_at: Optional[_dt.datetime] = None,
        questions: Sequence[ExamQuestion] = (),
        note: str = "",
    ) -> ExamAttempt:
        """ثبت یک نوبت آزمون و محاسبهٔ درصد بر اساس پروفایل."""
        profile = self.active_exam_profile()
        result = exam_analysis.compute_attempt(
            total=total,
            correct=correct,
            wrong=wrong,
            blank=blank,
            profile=profile,
            duration_minutes=duration_minutes,
        )
        attempt = ExamAttempt(
            exam_profile_id=profile.id if profile else None,
            name=name,
            kind=kind,
            taken_at=taken_at or _dt.datetime.now(),
            subject_id=subject_id,
            total=total,
            correct=correct,
            wrong=wrong,
            blank=blank,
            duration_minutes=duration_minutes,
            raw_score=result.raw_score,
            percentage=result.percentage,
            note=note,
        )
        attempt_id = self.repo.create_attempt(attempt)
        attempt.id = attempt_id

        for question in questions:
            question.attempt_id = attempt_id
            self.repo.create_question(question)
            if question.status == "wrong" and question.error_code is not None:
                self.repo.create_error_record(
                    ErrorRecord(
                        attempt_id=attempt_id,
                        question_id=question.id,
                        code=question.error_code,
                        topic_id=question.topic_id,
                        subject_id=question.subject_id,
                        created_at=attempt.taken_at,
                    )
                )
        self.conn.commit()
        return attempt

    def list_attempts(self) -> list[ExamAttempt]:
        return self.repo.list_attempts()

    def build_remediation(
        self, attempt_id: int
    ) -> exam_analysis.RemediationPlan:
        """ساخت فعالیت‌های اصلاحی از خطاهای یک آزمون (ERR-02)."""
        errors = self.repo.list_error_records(attempt_id)
        attempts = self.repo.list_attempts()
        attempt = next((a for a in attempts if a.id == attempt_id), None)
        if attempt is None:
            raise ValueError("نوبت آزمون یافت نشد.")

        topic_names = {
            t.id: (t.subject_name, t.name) for t in self.repo.list_topics()
        }
        plan = exam_analysis.build_remediation(
            errors=errors, attempt=attempt, topic_names=topic_names
        )
        for activity, error in zip(plan.activities, plan.records):
            activity_id = self.repo.create_activity(activity)
            error.resolution_activity_id = activity_id
            self.repo.update_activity(activity)
        self.conn.commit()
        return plan

    # ------------------------------------------------------------------
    # مشاوره
    # ------------------------------------------------------------------

    def study_phase(self) -> advisor_engine.StudyPhase:
        profile = self.active_exam_profile()
        days = profile.days_remaining if profile else None
        return advisor_engine.determine_phase(days, self.settings)

    def next_action(self) -> AdvisorSuggestion:
        """«کار بعدی» با یک دلیل کوتاه (ADV-03)."""
        activities = self.repo.list_activities()
        pending = [
            a
            for a in activities
            if a.state
            in {
                ActivityState.PLANNED,
                ActivityState.READY,
                ActivityState.OVERDUE,
                ActivityState.PARTIAL,
            }
        ]
        if pending:
            pending.sort(
                key=lambda a: (a.deadline_at or _dt.datetime.max, -a.est_minutes)
            )
            best = pending[0]
            reason = "این کار زودترین مهلت را در صف کارهای باقی‌مانده دارد."
            if best.deadline_type.value == "hard":
                reason = "مهلت سخت دارد و رعایت آن الزامی است."
            elif best.state == ActivityState.OVERDUE:
                reason = "این کار از موعد گذشته و در صف عقب‌افتادگی است."
            elif best.remaining_minutes > 0:
                reason = "ادامهٔ کار نیمه‌تمام قبلی است."
            return AdvisorSuggestion(
                activity_id=best.id,
                title=best.title,
                reason=reason,
                action_type="activity",
            )

        profile = self.active_exam_profile()
        phase = advisor_engine.determine_phase(
            profile.days_remaining if profile else None, self.settings
        )
        return AdvisorSuggestion(
            activity_id=None,
            title="ثبت یک کار تازه یا انجام یک آزمون",
            reason=(
                f"کارِ بازمانده‌ای در صف نیست. فاز فعلی: "
                f"«{advisor_engine.PHASE_LABELS[phase]}»."
            ),
            action_type="prompt",
        )

    def weekly_report(
        self, end_date: Optional[_dt.date] = None
    ) -> WeeklyReport:
        end_date = end_date or _dt.date.today()
        start_date = end_date - _dt.timedelta(days=6)
        return reporting.build_weekly_report(
            start_date=start_date,
            end_date=end_date,
            activities=self.repo.list_activities(),
            attempts=self.repo.list_attempts(),
            errors=self.repo.list_error_records(),
            review_logs=self.repo.list_review_logs(),
        )

    def daily_report(self, date: Optional[_dt.date] = None) -> reporting.DailyReport:
        date = date or _dt.date.today()
        plan = self.plan_day(date)
        return reporting.build_daily_report(
            date=date, plan=plan, activities=self.repo.list_activities()
        )

    # ------------------------------------------------------------------
    # پشتیبان‌گیری
    # ------------------------------------------------------------------

    def backup(self, backup_dir: Optional[Path | str] = None):
        self.conn.commit()
        return create_backup(
            self.db_path, backup_dir, app_version=_app_version()
        )

    def restore(self, backup_path: Path | str):
        self.conn.close()
        info = restore_backup(backup_path, self.db_path)
        self.conn = initialize(self.db_path)
        self.repo = Repository(self.conn)
        return info

    # ------------------------------------------------------------------
    # راه‌اندازی
    # ------------------------------------------------------------------

    def onboarding_state(self) -> onboarding.OnboardingState:
        raw = self.repo.get_setting("onboarding.state")
        if not raw:
            return onboarding.OnboardingState()
        try:
            return onboarding.OnboardingState.from_json(raw)
        except (ValueError, json.JSONDecodeError):  # pragma: no cover
            return onboarding.OnboardingState()

    def save_onboarding_state(self, state: onboarding.OnboardingState) -> None:
        self.repo.set_setting("onboarding.state", state.to_json())
        self.conn.commit()

    def onboarding_completed(self) -> bool:
        """فقط پس از تأیید نهایی، اجرای خودکار راه‌انداز متوقف می‌شود."""
        return self.onboarding_state().is_finished


def _app_version() -> str:
    from . import __version__

    return __version__
