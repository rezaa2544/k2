"""لایهٔ دسترسی به داده (Repository).

همهٔ تبدیل‌ها بین ردیف‌های SQLite و مدل‌های دامنه اینجا انجام می‌شود تا
منطق دامنه از SQL دور بماند.
"""

from __future__ import annotations

import datetime as _dt
import json
import sqlite3
from typing import Any, Iterable, Optional, Sequence

from ..domain.enums import (
    ActivityState,
    ActivityType,
    ContentType,
    DateStatus,
    DeadlineType,
    EnergyNeed,
    ErrorCode,
    ExamKind,
    FixedEventKind,
    MasteryLevel,
    ReviewState,
    RoutineKind,
    RoutineScope,
    ScopeStatus,
)
from ..domain.models import (
    Activity,
    ActivityEvent,
    ErrorRecord,
    EventException,
    ExamAttempt,
    ExamProfile,
    ExamQuestion,
    FixedEvent,
    ReviewItem,
    ReviewLog,
    Routine,
    Subject,
    Topic,
)
from ..domain.state_machine import validate_transition

# ---------------------------------------------------------------------------
# کمک‌کننده‌های تبدیل
# ---------------------------------------------------------------------------


def _date_str(value: Optional[_dt.date]) -> Optional[str]:
    return value.isoformat() if value else None


def _parse_date(value: Optional[str]) -> Optional[_dt.date]:
    if not value:
        return None
    try:
        return _dt.date.fromisoformat(value)
    except ValueError:  # pragma: no cover - دادهٔ خراب
        return None


def _datetime_str(value: Optional[_dt.datetime]) -> Optional[str]:
    return value.isoformat(timespec="seconds") if value else None


def _parse_datetime(value: Optional[str]) -> Optional[_dt.datetime]:
    if not value:
        return None
    try:
        return _dt.datetime.fromisoformat(value)
    except ValueError:  # pragma: no cover
        return None


def _now() -> _dt.datetime:
    return _dt.datetime.now().replace(microsecond=0)


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


class Repository:
    """تمام دسترسی‌های دادهٔ برنامه."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # ---- پروفایل آزمون ----

    def create_exam_profile(self, profile: ExamProfile) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO exam_profile
                (name, group_name, target_date, date_status, source_note,
                 negative_marking_ratio, percentage_formula, regulation_version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile.name,
                profile.group_name,
                _date_str(profile.target_date),
                profile.date_status.value,
                profile.source_note,
                profile.negative_marking_ratio,
                profile.percentage_formula,
                profile.regulation_version,
                _datetime_str(profile.created_at or _now()),
            ),
        )
        profile.id = cursor.lastrowid
        return profile.id

    def update_exam_profile(self, profile: ExamProfile) -> None:
        self.conn.execute(
            """
            UPDATE exam_profile
               SET name = ?, group_name = ?, target_date = ?, date_status = ?,
                   source_note = ?, negative_marking_ratio = ?, percentage_formula = ?,
                   regulation_version = ?
             WHERE id = ?
            """,
            (
                profile.name,
                profile.group_name,
                _date_str(profile.target_date),
                profile.date_status.value,
                profile.source_note,
                profile.negative_marking_ratio,
                profile.percentage_formula,
                profile.regulation_version,
                profile.id,
            ),
        )

    def list_exam_profiles(self) -> list[ExamProfile]:
        rows = self.conn.execute(
            "SELECT * FROM exam_profile ORDER BY id"
        ).fetchall()
        return [self._exam_profile_from_row(row) for row in rows]

    def get_exam_profile(self, profile_id: int) -> Optional[ExamProfile]:
        row = self.conn.execute(
            "SELECT * FROM exam_profile WHERE id = ?", (profile_id,)
        ).fetchone()
        return self._exam_profile_from_row(row) if row else None

    def _exam_profile_from_row(self, row: sqlite3.Row) -> ExamProfile:
        return ExamProfile(
            id=row["id"],
            name=row["name"],
            group_name=row["group_name"],
            target_date=_parse_date(row["target_date"]),
            date_status=DateStatus(row["date_status"]),
            source_note=row["source_note"],
            negative_marking_ratio=row["negative_marking_ratio"],
            percentage_formula=row["percentage_formula"],
            regulation_version=row["regulation_version"],
            created_at=_parse_datetime(row["created_at"]),
        )

    # ---- درس و مبحث ----

    def create_subject(self, subject: Subject) -> int:
        cursor = self.conn.execute(
            "INSERT INTO subject (exam_profile_id, name, coefficient, topic_weight) "
            "VALUES (?, ?, ?, ?)",
            (
                subject.exam_profile_id,
                subject.name,
                subject.coefficient,
                subject.topic_weight,
            ),
        )
        subject.id = cursor.lastrowid
        return subject.id

    def list_subjects(self, exam_profile_id: Optional[int] = None) -> list[Subject]:
        if exam_profile_id is None:
            rows = self.conn.execute("SELECT * FROM subject ORDER BY id").fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM subject WHERE exam_profile_id = ? ORDER BY id",
                (exam_profile_id,),
            ).fetchall()
        return [
            Subject(
                id=row["id"],
                exam_profile_id=row["exam_profile_id"],
                name=row["name"],
                coefficient=row["coefficient"],
                topic_weight=row["topic_weight"],
            )
            for row in rows
        ]

    def create_topic(self, topic: Topic) -> int:
        cursor = self.conn.execute(
            "INSERT INTO topic (subject_id, name, content_type, scope_status, mastery, "
            "self_assessed, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                topic.subject_id,
                topic.name,
                topic.content_type.value,
                topic.scope_status.value,
                topic.mastery.name,
                topic.self_assessed,
                topic.notes,
            ),
        )
        topic.id = cursor.lastrowid
        return topic.id

    def list_topics(self, subject_id: Optional[int] = None) -> list[Topic]:
        if subject_id is None:
            rows = self.conn.execute("SELECT * FROM topic ORDER BY id").fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM topic WHERE subject_id = ? ORDER BY id", (subject_id,)
            ).fetchall()
        names = {s.id: s.name for s in self.list_subjects()}
        return [
            Topic(
                id=row["id"],
                subject_id=row["subject_id"],
                subject_name=names.get(row["subject_id"], ""),
                name=row["name"],
                content_type=ContentType(row["content_type"]),
                scope_status=ScopeStatus(row["scope_status"]),
                mastery=MasteryLevel[row["mastery"]],
                self_assessed=row["self_assessed"],
                notes=row["notes"],
            )
            for row in rows
        ]

    def update_topic_mastery(self, topic_id: int, level: MasteryLevel) -> None:
        self.conn.execute(
            "UPDATE topic SET mastery = ? WHERE id = ?", (level.name, topic_id)
        )

    # ---- رویداد ثابت ----

    def create_fixed_event(self, event: FixedEvent) -> int:
        cursor = self.conn.execute(
            "INSERT INTO fixed_event (title, kind, subject_id, weekday, start_minute, "
            "end_minute, is_recorded, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event.title,
                event.kind.value,
                event.subject_id,
                event.weekday,
                event.start_minute,
                event.end_minute,
                1 if event.is_recorded else 0,
                event.notes,
            ),
        )
        event.id = cursor.lastrowid
        return event.id

    def list_fixed_events(self) -> list[FixedEvent]:
        rows = self.conn.execute("SELECT * FROM fixed_event ORDER BY id").fetchall()
        subjects = {s.id: s.name for s in self.list_subjects()}
        return [
            FixedEvent(
                id=row["id"],
                title=row["title"],
                kind=FixedEventKind(row["kind"]),
                subject_id=row["subject_id"],
                subject_name=subjects.get(row["subject_id"], ""),
                weekday=row["weekday"],
                start_minute=row["start_minute"],
                end_minute=row["end_minute"],
                is_recorded=bool(row["is_recorded"]),
                notes=row["notes"],
            )
            for row in rows
        ]

    def delete_fixed_event(self, event_id: int) -> None:
        self.conn.execute("DELETE FROM fixed_event WHERE id = ?", (event_id,))

    # ---- کارهای ضروری ----

    def create_routine(self, routine: Routine) -> int:
        cursor = self.conn.execute(
            "INSERT INTO routine (title, kind, start_minute, end_minute, weekdays, "
            "scope, counts_as_study) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                routine.title,
                routine.kind.value,
                routine.start_minute,
                routine.end_minute,
                json.dumps(sorted(routine.weekdays)),
                routine.scope.value,
                1 if routine.counts_as_study else 0,
            ),
        )
        routine.id = cursor.lastrowid
        return routine.id

    def list_routines(self) -> list[Routine]:
        rows = self.conn.execute("SELECT * FROM routine ORDER BY id").fetchall()
        result: list[Routine] = []
        for row in rows:
            try:
                weekdays = frozenset(json.loads(row["weekdays"]))
            except (TypeError, json.JSONDecodeError):  # pragma: no cover
                weekdays = frozenset(range(7))
            result.append(
                Routine(
                    id=row["id"],
                    title=row["title"],
                    kind=RoutineKind(row["kind"]),
                    start_minute=row["start_minute"],
                    end_minute=row["end_minute"],
                    weekdays=weekdays,
                    scope=RoutineScope(row["scope"]),
                    counts_as_study=bool(row["counts_as_study"]),
                )
            )
        return result

    # ---- استثناها ----

    def create_exception(self, exception: EventException) -> int:
        cursor = self.conn.execute(
            "INSERT INTO event_exception (event_id, date, cancelled, new_start_minute, "
            "new_end_minute, reason) VALUES (?, ?, ?, ?, ?, ?)",
            (
                exception.event_id,
                _date_str(exception.date),
                1 if exception.cancelled else 0,
                exception.new_start_minute,
                exception.new_end_minute,
                exception.reason,
            ),
        )
        exception.id = cursor.lastrowid
        return exception.id

    def list_exceptions(
        self, date: Optional[_dt.date] = None
    ) -> list[EventException]:
        if date is None:
            rows = self.conn.execute("SELECT * FROM event_exception").fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM event_exception WHERE date = ?", (date.isoformat(),)
            ).fetchall()
        return [
            EventException(
                id=row["id"],
                event_id=row["event_id"],
                date=_parse_date(row["date"]),
                cancelled=bool(row["cancelled"]),
                new_start_minute=row["new_start_minute"],
                new_end_minute=row["new_end_minute"],
                reason=row["reason"],
            )
            for row in rows
        ]

    # ---- فعالیت ----

    def create_activity(self, activity: Activity) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO activity
                (title, type, subject_id, topic_id, est_minutes, actual_minutes,
                 remaining_minutes, min_chunk, max_chunk, splittable, deadline_type,
                 deadline_at, depends_on, state, state_reason, energy_need, created_at,
                 first_planned_at, times_rescheduled, resume_marker, origin, source_ref)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '')
            """,
            (
                activity.title,
                activity.type.value,
                activity.subject_id,
                activity.topic_id,
                activity.est_minutes,
                activity.actual_minutes,
                activity.remaining_minutes,
                activity.min_chunk,
                activity.max_chunk,
                1 if activity.splittable else 0,
                activity.deadline_type.value,
                _datetime_str(activity.deadline_at),
                json.dumps(list(activity.depends_on)),
                activity.state.value,
                activity.state_reason,
                activity.energy_need.value,
                _datetime_str(activity.created_at or _now()),
                _datetime_str(activity.first_planned_at),
                activity.times_rescheduled,
                activity.resume_marker,
                activity.origin,
            ),
        )
        activity.id = cursor.lastrowid
        return activity.id

    def update_activity(self, activity: Activity) -> None:
        self.conn.execute(
            """
            UPDATE activity
               SET title = ?, type = ?, subject_id = ?, topic_id = ?, est_minutes = ?,
                   actual_minutes = ?, remaining_minutes = ?, min_chunk = ?, max_chunk = ?,
                   splittable = ?, deadline_type = ?, deadline_at = ?, depends_on = ?,
                   state = ?, state_reason = ?, energy_need = ?, first_planned_at = ?,
                   times_rescheduled = ?, resume_marker = ?, origin = ?
             WHERE id = ?
            """,
            (
                activity.title,
                activity.type.value,
                activity.subject_id,
                activity.topic_id,
                activity.est_minutes,
                activity.actual_minutes,
                activity.remaining_minutes,
                activity.min_chunk,
                activity.max_chunk,
                1 if activity.splittable else 0,
                activity.deadline_type.value,
                _datetime_str(activity.deadline_at),
                json.dumps(list(activity.depends_on)),
                activity.state.value,
                activity.state_reason,
                activity.energy_need.value,
                _datetime_str(activity.first_planned_at),
                activity.times_rescheduled,
                activity.resume_marker,
                activity.origin,
                activity.id,
            ),
        )

    def get_activity(self, activity_id: int) -> Optional[Activity]:
        row = self.conn.execute(
            "SELECT * FROM activity WHERE id = ?", (activity_id,)
        ).fetchone()
        if not row:
            return None
        subjects = {s.id: s.name for s in self.list_subjects()}
        topics = {t.id: t.name for t in self.list_topics()}
        return self._activity_from_row(row, subjects, topics)

    def list_activities(
        self, states: Optional[Sequence[ActivityState]] = None
    ) -> list[Activity]:
        subjects = {s.id: s.name for s in self.list_subjects()}
        topics = {t.id: t.name for t in self.list_topics()}
        if states:
            placeholders = ",".join("?" for _ in states)
            rows = self.conn.execute(
                f"SELECT * FROM activity WHERE state IN ({placeholders}) ORDER BY id",
                tuple(s.value for s in states),
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM activity ORDER BY id").fetchall()
        return [self._activity_from_row(row, subjects, topics) for row in rows]

    def _activity_from_row(
        self,
        row: sqlite3.Row,
        subjects: Optional[dict[int, str]] = None,
        topics: Optional[dict[int, str]] = None,
    ) -> Activity:
        subjects = subjects or {}
        topics = topics or {}
        try:
            depends_on = tuple(json.loads(row["depends_on"]))
        except (TypeError, json.JSONDecodeError):  # pragma: no cover
            depends_on = ()
        return Activity(
            id=row["id"],
            title=row["title"],
            type=ActivityType(row["type"]),
            subject_id=row["subject_id"],
            subject_name=subjects.get(row["subject_id"], ""),
            topic_id=row["topic_id"],
            topic_name=topics.get(row["topic_id"], ""),
            est_minutes=row["est_minutes"],
            actual_minutes=row["actual_minutes"],
            remaining_minutes=row["remaining_minutes"],
            min_chunk=row["min_chunk"],
            max_chunk=row["max_chunk"],
            splittable=bool(row["splittable"]),
            deadline_type=DeadlineType(row["deadline_type"]),
            deadline_at=_parse_datetime(row["deadline_at"]),
            depends_on=depends_on,
            state=ActivityState(row["state"]),
            state_reason=row["state_reason"],
            energy_need=EnergyNeed(row["energy_need"]),
            created_at=_parse_datetime(row["created_at"]),
            first_planned_at=_parse_datetime(row["first_planned_at"]),
            times_rescheduled=row["times_rescheduled"],
            resume_marker=row["resume_marker"],
            origin=row["origin"],
        )

    def transition_activity(
        self,
        activity: Activity,
        target: ActivityState,
        *,
        reason: str = "",
        at: Optional[_dt.datetime] = None,
    ) -> None:
        """گذار وضعیت با اعتبارسنجی و ثبت تاریخچه."""
        source = activity.state
        validate_transition(source, target)
        activity.state = target
        activity.state_reason = reason
        self.update_activity(activity)
        self.conn.execute(
            "INSERT INTO activity_event (activity_id, at, kind, from_state, to_state, note) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                activity.id,
                _datetime_str(at or _now()),
                "state_change",
                source.value,
                target.value,
                reason,
            ),
        )

    def log_activity_event(
        self,
        activity_id: int,
        *,
        kind: str,
        note: str = "",
        at: Optional[_dt.datetime] = None,
    ) -> None:
        self.conn.execute(
            "INSERT INTO activity_event (activity_id, at, kind, note) VALUES (?, ?, ?, ?)",
            (activity_id, _datetime_str(at or _now()), kind, note),
        )

    def list_activity_events(self, activity_id: int) -> list[ActivityEvent]:
        rows = self.conn.execute(
            "SELECT * FROM activity_event WHERE activity_id = ? ORDER BY id",
            (activity_id,),
        ).fetchall()
        return [
            ActivityEvent(
                id=row["id"],
                activity_id=row["activity_id"],
                at=_parse_datetime(row["at"]),
                kind=row["kind"],
                from_state=ActivityState(row["from_state"]) if row["from_state"] else None,
                to_state=ActivityState(row["to_state"]) if row["to_state"] else None,
                note=row["note"],
            )
            for row in rows
        ]

    # ---- برنامه ----

    def replace_schedule(
        self, date: _dt.date, placements: Iterable[Any]
    ) -> None:
        """جای‌گزینی برنامهٔ یک روز (برنامهٔ قبلی این روز پاک می‌شود)."""
        self.conn.execute("DELETE FROM schedule_slot WHERE date = ?", (date.isoformat(),))
        now = _datetime_str(_now())
        for placement in placements:
            self.conn.execute(
                "INSERT INTO schedule_slot (activity_id, date, start_minute, end_minute, "
                "minutes, score, reasons, chunk_index, chunk_total, generated_at, is_current) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
                (
                    placement.activity_id,
                    date.isoformat(),
                    placement.start_minute,
                    placement.end_minute,
                    placement.minutes,
                    placement.score,
                    json.dumps(list(placement.reasons), ensure_ascii=False),
                    placement.chunk_index,
                    placement.chunk_total,
                    now,
                ),
            )

    def list_schedule(self, date: _dt.date) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT s.*, a.title AS activity_title FROM schedule_slot s "
            "LEFT JOIN activity a ON a.id = s.activity_id "
            "WHERE s.date = ? ORDER BY s.start_minute",
            (date.isoformat(),),
        ).fetchall()

    # ---- مرور ----

    def create_review_item(self, item: ReviewItem) -> int:
        cursor = self.conn.execute(
            "INSERT INTO review_item (subject_id, topic_id, label, item_type, "
            "interval_days, ease, difficulty, lapses, last_review, due_date, state, "
            "last_grade, last_time_ratio, content, created_at, success_streak) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                item.subject_id,
                item.topic_id,
                item.label,
                item.item_type,
                item.interval_days,
                item.ease,
                item.difficulty,
                item.lapses,
                _date_str(item.last_review),
                _date_str(item.due_date),
                item.state.value,
                item.last_grade,
                item.last_time_ratio,
                item.content,
                _datetime_str(item.created_at or _now()),
                item.success_streak,
            ),
        )
        item.id = cursor.lastrowid
        return item.id

    def update_review_item(self, item: ReviewItem) -> None:
        self.conn.execute(
            "UPDATE review_item SET interval_days = ?, ease = ?, difficulty = ?, "
            "lapses = ?, last_review = ?, due_date = ?, state = ?, last_grade = ?, "
            "last_time_ratio = ?, success_streak = ? WHERE id = ?",
            (
                item.interval_days,
                item.ease,
                item.difficulty,
                item.lapses,
                _date_str(item.last_review),
                _date_str(item.due_date),
                item.state.value,
                item.last_grade,
                item.last_time_ratio,
                item.success_streak,
                item.id,
            ),
        )

    def list_review_items(self) -> list[ReviewItem]:
        rows = self.conn.execute("SELECT * FROM review_item ORDER BY id").fetchall()
        return [
            ReviewItem(
                id=row["id"],
                subject_id=row["subject_id"],
                topic_id=row["topic_id"],
                label=row["label"],
                item_type=row["item_type"],
                interval_days=row["interval_days"],
                ease=row["ease"],
                difficulty=row["difficulty"],
                lapses=row["lapses"],
                last_review=_parse_date(row["last_review"]),
                due_date=_parse_date(row["due_date"]),
                state=ReviewState(row["state"]),
                last_grade=row["last_grade"],
                last_time_ratio=row["last_time_ratio"],
                content=row["content"],
                created_at=_parse_datetime(row["created_at"]),
                success_streak=row["success_streak"],
            )
            for row in rows
        ]

    def add_review_log(self, log: ReviewLog) -> int:
        cursor = self.conn.execute(
            "INSERT INTO review_log (item_id, at, grade, confidence, seconds, note) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                log.item_id,
                _datetime_str(log.at or _now()),
                log.grade,
                log.confidence,
                log.seconds,
                log.note,
            ),
        )
        log.id = cursor.lastrowid
        return log.id

    def list_review_logs(self, item_id: Optional[int] = None) -> list[ReviewLog]:
        if item_id is None:
            rows = self.conn.execute("SELECT * FROM review_log ORDER BY id").fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM review_log WHERE item_id = ? ORDER BY id", (item_id,)
            ).fetchall()
        return [
            ReviewLog(
                id=row["id"],
                item_id=row["item_id"],
                at=_parse_datetime(row["at"]),
                grade=row["grade"],
                confidence=row["confidence"],
                seconds=row["seconds"],
                note=row["note"],
            )
            for row in rows
        ]

    # ---- آزمون ----

    def create_attempt(self, attempt: ExamAttempt) -> int:
        cursor = self.conn.execute(
            "INSERT INTO exam_attempt (exam_profile_id, name, kind, taken_at, subject_id, "
            "total, correct, wrong, blank, duration_minutes, raw_score, percentage, note) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                attempt.exam_profile_id,
                attempt.name,
                attempt.kind.value,
                _datetime_str(attempt.taken_at or _now()),
                attempt.subject_id,
                attempt.total,
                attempt.correct,
                attempt.wrong,
                attempt.blank,
                attempt.duration_minutes,
                attempt.raw_score,
                attempt.percentage,
                attempt.note,
            ),
        )
        attempt.id = cursor.lastrowid
        return attempt.id

    def list_attempts(self) -> list[ExamAttempt]:
        rows = self.conn.execute("SELECT * FROM exam_attempt ORDER BY taken_at").fetchall()
        subjects = {s.id: s.name for s in self.list_subjects()}
        return [
            ExamAttempt(
                id=row["id"],
                exam_profile_id=row["exam_profile_id"],
                name=row["name"],
                kind=ExamKind(row["kind"]),
                taken_at=_parse_datetime(row["taken_at"]),
                subject_id=row["subject_id"],
                subject_name=subjects.get(row["subject_id"], ""),
                total=row["total"],
                correct=row["correct"],
                wrong=row["wrong"],
                blank=row["blank"],
                duration_minutes=row["duration_minutes"],
                raw_score=row["raw_score"],
                percentage=row["percentage"],
                note=row["note"],
            )
            for row in rows
        ]

    def create_question(self, question: ExamQuestion) -> int:
        cursor = self.conn.execute(
            "INSERT INTO exam_question (attempt_id, subject_id, topic_id, number, status, "
            "error_code, seconds, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                question.attempt_id,
                question.subject_id,
                question.topic_id,
                question.number,
                question.status,
                question.error_code.value if question.error_code else None,
                question.seconds,
                question.note,
            ),
        )
        question.id = cursor.lastrowid
        return question.id

    def list_questions(self, attempt_id: int) -> list[ExamQuestion]:
        rows = self.conn.execute(
            "SELECT * FROM exam_question WHERE attempt_id = ? ORDER BY number, id",
            (attempt_id,),
        ).fetchall()
        return [
            ExamQuestion(
                id=row["id"],
                attempt_id=row["attempt_id"],
                subject_id=row["subject_id"],
                topic_id=row["topic_id"],
                number=row["number"],
                status=row["status"],
                error_code=ErrorCode(row["error_code"]) if row["error_code"] else None,
                seconds=row["seconds"],
                note=row["note"],
            )
            for row in rows
        ]

    def create_error_record(self, error: ErrorRecord) -> int:
        cursor = self.conn.execute(
            "INSERT INTO error_record (attempt_id, question_id, code, topic_id, subject_id, "
            "created_at, resolution_activity_id, resolved_at, retest_attempt_id, note) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                error.attempt_id,
                error.question_id,
                error.code.value,
                error.topic_id,
                error.subject_id,
                _datetime_str(error.created_at or _now()),
                error.resolution_activity_id,
                _datetime_str(error.resolved_at),
                error.retest_attempt_id,
                error.note,
            ),
        )
        error.id = cursor.lastrowid
        return error.id

    def list_error_records(
        self, attempt_id: Optional[int] = None
    ) -> list[ErrorRecord]:
        if attempt_id is None:
            rows = self.conn.execute("SELECT * FROM error_record ORDER BY id").fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM error_record WHERE attempt_id = ? ORDER BY id",
                (attempt_id,),
            ).fetchall()
        return [
            ErrorRecord(
                id=row["id"],
                attempt_id=row["attempt_id"],
                question_id=row["question_id"],
                code=ErrorCode(row["code"]),
                topic_id=row["topic_id"],
                subject_id=row["subject_id"],
                created_at=_parse_datetime(row["created_at"]),
                resolution_activity_id=row["resolution_activity_id"],
                resolved_at=_parse_datetime(row["resolved_at"]),
                retest_attempt_id=row["retest_attempt_id"],
                note=row["note"],
            )
            for row in rows
        ]

    def link_error_to_activity(self, error_id: int, activity_id: int) -> None:
        self.conn.execute(
            "UPDATE error_record SET resolution_activity_id = ? WHERE id = ?",
            (activity_id, error_id),
        )

    # ---- راه‌اندازی ----

    def save_onboarding_step(
        self, step_key: str, value: str, *, completed: bool = False
    ) -> None:
        self.conn.execute(
            "INSERT INTO onboarding_step (step_key, value, completed, updated_at) "
            "VALUES (?, ?, ?, ?) ON CONFLICT(step_key) DO UPDATE SET "
            "value = excluded.value, completed = excluded.completed, "
            "updated_at = excluded.updated_at",
            (step_key, value, 1 if completed else 0, _datetime_str(_now())),
        )

    def load_onboarding(self) -> dict[str, str]:
        rows = self.conn.execute("SELECT step_key, value FROM onboarding_step").fetchall()
        return {row["step_key"]: row["value"] for row in rows}

    def onboarding_completed(self) -> bool:
        row = self.conn.execute(
            "SELECT COUNT(*) AS c FROM onboarding_step WHERE completed = 1"
        ).fetchone()
        return bool(row and row["c"] > 0)

    # ---- تنظیمات کلید/مقدار ----

    def set_setting(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        row = self.conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def commit(self) -> None:
        self.conn.commit()
