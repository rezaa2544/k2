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
    DeadlineKind,
    DeadlineType,
    EnergyNeed,
    ErrorCode,
    ExamKind,
    FixedEventKind,
    KonkurStage,
    FinalStage,
    MasteryLevel,
    ProblemKind,
    ProblemStatus,
    ReviewState,
    RoutineKind,
    RoutineScope,
    ScopeStatus,
    SessionKind,
    TrackKind,
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
    LearningProblem,
    LearningProblemEvent,
    LearningEvidence,
    ReviewItem,
    ReviewLog,
    Routine,
    StudySession,
    StudySessionRevision,
    Subject,
    SyllabusChapterEdit,
    SyllabusSection,
    Topic,
    TopicDeadline,
    Textbook,
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


def _clamp01(value: Optional[float]) -> float:
    """سهم‌ها را در بازهٔ ۰..۱ نگه می‌دارد تا دادهٔ خراب اولویت را نشکند."""
    try:
        return max(0.0, min(1.0, float(value or 0.0)))
    except (TypeError, ValueError):
        return 0.0


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
                 negative_marking_ratio, percentage_formula, regulation_version, exam_year, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                profile.exam_year,
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
                   regulation_version = ?, exam_year = ?
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
                profile.exam_year,
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
            exam_year=row["exam_year"],
            created_at=_parse_datetime(row["created_at"]),
        )

    # ---- درس و مبحث ----

    def create_subject(self, subject: Subject) -> int:
        cursor = self.conn.execute(
            """INSERT INTO subject
                (exam_profile_id, name, coefficient, topic_weight, is_selected,
                 exam_coefficient, exam_coefficient_status, exam_coefficient_source,
                 academic_coefficient, academic_coefficient_status, academic_coefficient_source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                subject.exam_profile_id,
                subject.name,
                subject.coefficient,
                subject.topic_weight,
                1 if subject.is_selected else 0,
                subject.exam_coefficient,
                subject.exam_coefficient_status,
                subject.exam_coefficient_source,
                subject.academic_coefficient,
                subject.academic_coefficient_status,
                subject.academic_coefficient_source,
            ),
        )
        subject.id = cursor.lastrowid
        return subject.id

    def update_subject(self, subject: Subject) -> None:
        self.conn.execute(
            """UPDATE subject SET name = ?, coefficient = ?, topic_weight = ?,
                 is_selected = ?, exam_coefficient = ?, exam_coefficient_status = ?,
                 exam_coefficient_source = ?, academic_coefficient = ?,
                 academic_coefficient_status = ?, academic_coefficient_source = ?
               WHERE id = ?""",
            (
                subject.name,
                subject.coefficient,
                subject.topic_weight,
                1 if subject.is_selected else 0,
                subject.exam_coefficient,
                subject.exam_coefficient_status,
                subject.exam_coefficient_source,
                subject.academic_coefficient,
                subject.academic_coefficient_status,
                subject.academic_coefficient_source,
                subject.id,
            ),
        )

    def list_subjects(
        self, exam_profile_id: Optional[int] = None, *, include_unselected: bool = True
    ) -> list[Subject]:
        clauses: list[str] = []
        params: list[Any] = []
        if exam_profile_id is not None:
            clauses.append("exam_profile_id = ?")
            params.append(exam_profile_id)
        if not include_unselected:
            clauses.append("is_selected = 1")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self.conn.execute(
            f"SELECT * FROM subject{where} ORDER BY id", params
        ).fetchall()
        return [
            Subject(
                id=row["id"],
                exam_profile_id=row["exam_profile_id"],
                name=row["name"],
                coefficient=row["coefficient"],
                topic_weight=row["topic_weight"],
                is_selected=bool(row["is_selected"]),
                exam_coefficient=row["exam_coefficient"],
                exam_coefficient_status=row["exam_coefficient_status"],
                exam_coefficient_source=row["exam_coefficient_source"],
                academic_coefficient=row["academic_coefficient"],
                academic_coefficient_status=row["academic_coefficient_status"],
                academic_coefficient_source=row["academic_coefficient_source"],
            )
            for row in rows
        ]

    def create_textbook(self, book: Textbook) -> int:
        cursor = self.conn.execute(
            """INSERT INTO textbook
                (exam_profile_id, subject_id, title, book_code, grade, edition_year,
                 source_url, source_status, is_selected)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                book.exam_profile_id, book.subject_id, book.title, book.book_code,
                book.grade, book.edition_year, book.source_url, book.source_status,
                1 if book.is_selected else 0,
            ),
        )
        book.id = cursor.lastrowid
        return book.id

    def save_textbook_selection(self, book: Textbook) -> int:
        row = self.conn.execute(
            """SELECT id FROM textbook WHERE exam_profile_id = ?
               AND IFNULL(subject_id, -1) = IFNULL(?, -1)
               AND title = ? AND book_code = ? ORDER BY id LIMIT 1""",
            (book.exam_profile_id, book.subject_id, book.title, book.book_code),
        ).fetchone()
        if row:
            book.id = row["id"]
            self.conn.execute(
                """UPDATE textbook SET grade = ?, edition_year = ?, source_url = ?,
                     source_status = ?, is_selected = ? WHERE id = ?""",
                (
                    book.grade, book.edition_year, book.source_url, book.source_status,
                    1 if book.is_selected else 0, book.id,
                ),
            )
            return book.id
        return self.create_textbook(book)

    def list_textbooks(
        self, exam_profile_id: int, *, subject_id: Optional[int] = None,
        include_unselected: bool = True,
    ) -> list[Textbook]:
        clauses = ["exam_profile_id = ?"]
        params: list[Any] = [exam_profile_id]
        if subject_id is not None:
            clauses.append("subject_id = ?")
            params.append(subject_id)
        if not include_unselected:
            clauses.append("is_selected = 1")
        rows = self.conn.execute(
            "SELECT * FROM textbook WHERE " + " AND ".join(clauses) + " ORDER BY id",
            params,
        ).fetchall()
        return [
            Textbook(
                id=row["id"], exam_profile_id=row["exam_profile_id"],
                subject_id=row["subject_id"], title=row["title"],
                book_code=row["book_code"], grade=row["grade"],
                edition_year=row["edition_year"], source_url=row["source_url"],
                source_status=row["source_status"],
                is_selected=bool(row["is_selected"]),
            )
            for row in rows
        ]

    def set_subject_selected(self, subject_id: int, selected: bool) -> None:
        self.conn.execute(
            "UPDATE subject SET is_selected = ? WHERE id = ?",
            (1 if selected else 0, subject_id),
        )

    def set_textbook_selected(self, textbook_id: int, selected: bool) -> None:
        self.conn.execute(
            "UPDATE textbook SET is_selected = ? WHERE id = ?",
            (1 if selected else 0, textbook_id),
        )

    def create_topic(self, topic: Topic) -> int:
        cursor = self.conn.execute(
            "INSERT INTO topic (subject_id, name, content_type, scope_status, mastery, "
            "self_assessed, notes, konkur_stage, final_stage, prerequisite_share, "
            "final_exam_share, estimated_minutes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                topic.subject_id,
                topic.name,
                topic.content_type.value,
                topic.scope_status.value,
                topic.mastery.name,
                topic.self_assessed,
                topic.notes,
                topic.konkur_stage,
                topic.final_stage,
                _clamp01(topic.prerequisite_share),
                _clamp01(topic.final_exam_share),
                topic.estimated_minutes,
            ),
        )
        topic.id = cursor.lastrowid
        return topic.id

    def update_topic(self, topic: Topic) -> None:
        """همهٔ فیلدهای قابل ویرایش مبحث را ذخیره می‌کند."""
        if topic.id is None:
            raise ValueError("برای ویرایش، مبحث باید شناسهٔ ذخیره‌شده داشته باشد.")
        self.conn.execute(
            "UPDATE topic SET name = ?, content_type = ?, scope_status = ?, mastery = ?, "
            "self_assessed = ?, notes = ?, konkur_stage = ?, final_stage = ?, "
            "konkur_evidence_id = ?, final_evidence_id = ?, prerequisite_share = ?, "
            "final_exam_share = ?, estimated_minutes = ? WHERE id = ?",
            (
                topic.name,
                topic.content_type.value,
                topic.scope_status.value,
                topic.mastery.name,
                topic.self_assessed,
                topic.notes,
                topic.konkur_stage,
                topic.final_stage,
                topic.konkur_evidence_id,
                topic.final_evidence_id,
                _clamp01(topic.prerequisite_share),
                _clamp01(topic.final_exam_share),
                topic.estimated_minutes,
                topic.id,
            ),
        )

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
                konkur_stage=row["konkur_stage"] or KonkurStage.CONCEPTUAL.value,
                final_stage=row["final_stage"] or FinalStage.TEXTBOOK_STUDY.value,
                konkur_evidence_id=row["konkur_evidence_id"],
                final_evidence_id=row["final_evidence_id"],
                prerequisite_share=float(row["prerequisite_share"] or 0.0),
                final_exam_share=float(row["final_exam_share"] or 0.0),
                estimated_minutes=row["estimated_minutes"],
            )
            for row in rows
        ]

    def update_topic_mastery(self, topic_id: int, level: MasteryLevel) -> None:
        self.conn.execute(
            "UPDATE topic SET mastery = ? WHERE id = ?", (level.name, topic_id)
        )

    def create_learning_evidence(self, evidence: LearningEvidence) -> int:
        if evidence.topic_id is None or evidence.observed_on is None:
            raise ValueError("شاهد عملکرد باید به مبحث و تاریخ مشخص وصل باشد.")
        if not 0.0 <= float(evidence.score) <= 1.0:
            raise ValueError("نمرهٔ عملکرد باید بین صفر و یک باشد.")
        if not 1 <= int(evidence.confidence) <= 4:
            raise ValueError("اطمینان باید بین ۱ تا ۴ باشد.")
        cursor = self.conn.execute(
            "INSERT INTO learning_evidence (topic_id, observed_on, source, score, "
            "item_count, confidence, duration_seconds, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                evidence.topic_id,
                evidence.observed_on.isoformat(),
                evidence.source,
                float(evidence.score),
                max(0, int(evidence.item_count)),
                int(evidence.confidence),
                evidence.duration_seconds,
                evidence.note,
            ),
        )
        evidence.id = cursor.lastrowid
        return evidence.id

    def list_learning_evidence(self, topic_id: Optional[int] = None) -> list[LearningEvidence]:
        if topic_id is None:
            rows = self.conn.execute(
                "SELECT * FROM learning_evidence ORDER BY observed_on, id"
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM learning_evidence WHERE topic_id = ? "
                "ORDER BY observed_on, id", (topic_id,)
            ).fetchall()
        return [
            LearningEvidence(
                id=row["id"], topic_id=row["topic_id"],
                observed_on=_parse_date(row["observed_on"]), source=row["source"],
                score=float(row["score"]), item_count=int(row["item_count"]),
                confidence=int(row["confidence"]), duration_seconds=row["duration_seconds"],
                note=row["note"],
            )
            for row in rows
        ]

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

    def update_fixed_event(self, event: FixedEvent) -> None:
        self.conn.execute(
            """UPDATE fixed_event SET title = ?, kind = ?, subject_id = ?, weekday = ?,
                 start_minute = ?, end_minute = ?, is_recorded = ?, notes = ? WHERE id = ?""",
            (
                event.title, event.kind.value, event.subject_id, event.weekday,
                event.start_minute, event.end_minute, 1 if event.is_recorded else 0,
                event.notes, event.id,
            ),
        )

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

    def update_routine(self, routine: Routine) -> None:
        self.conn.execute(
            """UPDATE routine SET title = ?, kind = ?, start_minute = ?, end_minute = ?,
                 weekdays = ?, scope = ?, counts_as_study = ? WHERE id = ?""",
            (
                routine.title, routine.kind.value, routine.start_minute,
                routine.end_minute, json.dumps(sorted(routine.weekdays)),
                routine.scope.value, 1 if routine.counts_as_study else 0, routine.id,
            ),
        )

    def delete_routine(self, routine_id: int) -> None:
        self.conn.execute("DELETE FROM routine WHERE id = ?", (routine_id,))

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
            "last_grade, last_time_ratio, content, created_at, success_streak, "
            "stability_days, retrievability) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                item.stability_days,
                item.retrievability,
            ),
        )
        item.id = cursor.lastrowid
        return item.id

    def update_review_item(self, item: ReviewItem) -> None:
        self.conn.execute(
            "UPDATE review_item SET interval_days = ?, ease = ?, difficulty = ?, "
            "lapses = ?, last_review = ?, due_date = ?, state = ?, last_grade = ?, "
            "last_time_ratio = ?, success_streak = ?, stability_days = ?, "
            "retrievability = ? WHERE id = ?",
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
                item.stability_days,
                item.retrievability,
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
                stability_days=(
                    row["stability_days"]
                    if "stability_days" in row.keys() and row["stability_days"]
                    else 0.0
                ),
                retrievability=(
                    row["retrievability"]
                    if "retrievability" in row.keys() and row["retrievability"] is not None
                    else 1.0
                ),
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
            "total, correct, wrong, blank, duration_minutes, raw_score, percentage, note, "
            "attachment_path, attachment_name, attachment_sha256, attachment_bytes, "
            "attachment_note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                attempt.attachment_path,
                attempt.attachment_name,
                attempt.attachment_sha256,
                attempt.attachment_bytes,
                attempt.attachment_note,
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
                attachment_path=row["attachment_path"],
                attachment_name=row["attachment_name"] or "",
                attachment_sha256=row["attachment_sha256"],
                attachment_bytes=row["attachment_bytes"] or 0,
                attachment_note=row["attachment_note"] or "",
            )
            for row in rows
        ]

    def update_attempt(self, attempt: ExamAttempt) -> None:
        """به‌روزرسانی یک نوبت آزمون (برای پیوست نتیجهٔ آزمون)."""
        if attempt.id is None:
            raise ValueError("برای به‌روزرسانی، شناسهٔ نوبت آزمون لازم است.")
        self.conn.execute(
            "UPDATE exam_attempt SET attachment_path=?, attachment_name=?, "
            "attachment_sha256=?, attachment_bytes=?, attachment_note=?, note=? "
            "WHERE id=?",
            (
                attempt.attachment_path,
                attempt.attachment_name,
                attempt.attachment_sha256,
                attempt.attachment_bytes,
                attempt.attachment_note,
                attempt.note,
                attempt.id,
            ),
        )
        self.conn.commit()

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


    # ---- مهلت‌های مبحث (بند ۱۲) ----

    def create_topic_deadline(self, deadline: TopicDeadline) -> int:
        if deadline.topic_id is None:
            raise ValueError("مهلت باید به یک مبحث وصل باشد.")
        if deadline.target_date is None:
            raise ValueError("تاریخ مهلت لازم است.")
        if deadline.target_percent is not None and not 0 <= float(deadline.target_percent) <= 100:
            raise ValueError("درصد هدف باید بین صفر و صد باشد.")
        now = _now()
        cursor = self.conn.execute(
            "INSERT INTO topic_deadline (topic_id, subject_id, kind, target_date, "
            "target_percent, target_level, target_track, is_master, note, created_at, "
            "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                deadline.topic_id,
                deadline.subject_id,
                deadline.kind.value,
                _date_str(deadline.target_date),
                deadline.target_percent,
                deadline.target_level,
                deadline.target_track.value,
                1 if deadline.is_master else 0,
                deadline.note,
                _datetime_str(now),
                _datetime_str(now),
            ),
        )
        deadline.id = cursor.lastrowid
        deadline.created_at = now
        deadline.updated_at = now
        return deadline.id

    def update_topic_deadline(self, deadline: TopicDeadline) -> None:
        if deadline.id is None:
            raise ValueError("برای ویرایش مهلت، شناسه لازم است.")
        if deadline.target_percent is not None and not 0 <= float(deadline.target_percent) <= 100:
            raise ValueError("درصد هدف باید بین صفر و صد باشد.")
        now = _now()
        self.conn.execute(
            "UPDATE topic_deadline SET target_date = ?, target_percent = ?, "
            "target_level = ?, target_track = ?, is_master = ?, note = ?, "
            "updated_at = ? WHERE id = ?",
            (
                _date_str(deadline.target_date),
                deadline.target_percent,
                deadline.target_level,
                deadline.target_track.value,
                1 if deadline.is_master else 0,
                deadline.note,
                _datetime_str(now),
                deadline.id,
            ),
        )
        deadline.updated_at = now

    # ------------------------------------------------------------------
    # سرفصل رسمی: فصل و گفتار
    # ------------------------------------------------------------------

    _SECTION_FIELDS = (
        "title", "teaching", "study", "comprehension", "consolidation",
        "testing", "analysis", "essay", "speed", "mastery", "notes", "updated_at",
    )

    def upsert_syllabus_section(self, record: SyllabusSection) -> None:
        """ثبت یا به‌روزرسانی وضعیت یک گفتار (idempotent روی کلید طبیعی)."""
        values = [getattr(record, name) for name in self._SECTION_FIELDS]
        self.conn.execute(
            "INSERT INTO syllabus_section (subject, grade, chapter, section, "
            + ", ".join(self._SECTION_FIELDS)
            + ") VALUES (?, ?, ?, ?, "
            + ", ".join("?" * len(self._SECTION_FIELDS))
            + ") ON CONFLICT(subject, grade, chapter, section) DO UPDATE SET "
            + ", ".join(f"{name} = excluded.{name}" for name in self._SECTION_FIELDS),
            (record.subject, int(record.grade), int(record.chapter),
             int(record.section), *values),
        )

    def list_syllabus_sections(
        self, subject: Optional[str] = None, grade: Optional[int] = None
    ) -> list[SyllabusSection]:
        clauses: list[str] = []
        params: list[Any] = []
        if subject is not None:
            clauses.append("subject = ?")
            params.append(subject)
        if grade is not None:
            clauses.append("grade = ?")
            params.append(int(grade))
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self.conn.execute(
            "SELECT * FROM syllabus_section" + where
            + " ORDER BY subject, grade, chapter, section",
            params,
        ).fetchall()
        return [self._section_from_row(row) for row in rows]

    def get_syllabus_section(
        self, subject: str, grade: int, chapter: int, section: int
    ) -> Optional[SyllabusSection]:
        row = self.conn.execute(
            "SELECT * FROM syllabus_section WHERE subject = ? AND grade = ? "
            "AND chapter = ? AND section = ?",
            (subject, int(grade), int(chapter), int(section)),
        ).fetchone()
        return self._section_from_row(row) if row else None

    def delete_syllabus_section(
        self, subject: str, grade: int, chapter: int, section: int
    ) -> bool:
        cursor = self.conn.execute(
            "DELETE FROM syllabus_section WHERE subject = ? AND grade = ? "
            "AND chapter = ? AND section = ?",
            (subject, int(grade), int(chapter), int(section)),
        )
        return cursor.rowcount > 0

    @staticmethod
    def _section_from_row(row: sqlite3.Row) -> SyllabusSection:
        return SyllabusSection(
            subject=row["subject"],
            grade=int(row["grade"]),
            chapter=int(row["chapter"]),
            section=int(row["section"]),
            title=row["title"] or "",
            teaching=row["teaching"],
            study=row["study"],
            comprehension=row["comprehension"],
            consolidation=row["consolidation"],
            testing=row["testing"],
            analysis=row["analysis"],
            essay=row["essay"],
            speed=row["speed"],
            mastery=row["mastery"],
            notes=row["notes"] or "",
            updated_at=row["updated_at"] or "",
        )

    def upsert_syllabus_chapter(self, edit: SyllabusChapterEdit) -> None:
        self.conn.execute(
            "INSERT INTO syllabus_chapter (subject, grade, chapter, title, "
            "sections, confirmed, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(subject, grade, chapter) DO UPDATE SET "
            "title = excluded.title, sections = excluded.sections, "
            "confirmed = excluded.confirmed, updated_at = excluded.updated_at",
            (edit.subject, int(edit.grade), int(edit.chapter), edit.title,
             edit.sections, 1 if edit.confirmed else 0, edit.updated_at),
        )

    def list_syllabus_chapter_edits(
        self, subject: Optional[str] = None, grade: Optional[int] = None
    ) -> list[SyllabusChapterEdit]:
        clauses: list[str] = []
        params: list[Any] = []
        if subject is not None:
            clauses.append("subject = ?")
            params.append(subject)
        if grade is not None:
            clauses.append("grade = ?")
            params.append(int(grade))
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self.conn.execute(
            "SELECT * FROM syllabus_chapter" + where
            + " ORDER BY subject, grade, chapter",
            params,
        ).fetchall()
        return [
            SyllabusChapterEdit(
                subject=row["subject"],
                grade=int(row["grade"]),
                chapter=int(row["chapter"]),
                title=row["title"] or "",
                sections=row["sections"],
                confirmed=bool(row["confirmed"]),
                updated_at=row["updated_at"] or "",
            )
            for row in rows
        ]

    def get_syllabus_chapter(
        self, subject: str, grade: int, chapter: int
    ) -> Optional[SyllabusChapterEdit]:
        row = self.conn.execute(
            "SELECT * FROM syllabus_chapter WHERE subject = ? AND grade = ? "
            "AND chapter = ?",
            (subject, int(grade), int(chapter)),
        ).fetchone()
        if not row:
            return None
        return SyllabusChapterEdit(
            subject=row["subject"],
            grade=int(row["grade"]),
            chapter=int(row["chapter"]),
            title=row["title"] or "",
            sections=row["sections"],
            confirmed=bool(row["confirmed"]),
            updated_at=row["updated_at"] or "",
        )

    def delete_topic_deadline(self, deadline_id: int) -> None:
        self.conn.execute("DELETE FROM topic_deadline WHERE id = ?", (deadline_id,))

    def set_master_deadline(self, topic_id: int, deadline_id: int) -> None:
        """یک مهلت را به‌عنوان مهلت مادرِ بازمحاسبه انتخاب می‌کند."""
        self.conn.execute(
            "UPDATE topic_deadline SET is_master = 0 WHERE topic_id = ?", (topic_id,)
        )
        self.conn.execute(
            "UPDATE topic_deadline SET is_master = 1 WHERE id = ? AND topic_id = ?",
            (deadline_id, topic_id),
        )

    def list_topic_deadlines(
        self, topic_id: Optional[int] = None
    ) -> list[TopicDeadline]:
        if topic_id is None:
            rows = self.conn.execute(
                "SELECT d.*, t.name AS topic_name, s.name AS subject_name "
                "FROM topic_deadline d "
                "LEFT JOIN topic t ON t.id = d.topic_id "
                "LEFT JOIN subject s ON s.id = d.subject_id "
                "ORDER BY d.target_date, d.id"
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT d.*, t.name AS topic_name, s.name AS subject_name "
                "FROM topic_deadline d "
                "LEFT JOIN topic t ON t.id = d.topic_id "
                "LEFT JOIN subject s ON s.id = d.subject_id "
                "WHERE d.topic_id = ? ORDER BY d.target_date, d.id",
                (topic_id,),
            ).fetchall()
        return [self._topic_deadline_from_row(row) for row in rows]

    def _topic_deadline_from_row(self, row: sqlite3.Row) -> TopicDeadline:
        try:
            kind = DeadlineKind(row["kind"])
        except ValueError:
            kind = DeadlineKind.INITIAL_LEARNING
        try:
            track = TrackKind(row["target_track"])
        except ValueError:
            track = TrackKind.KONKUR
        return TopicDeadline(
            id=row["id"],
            topic_id=row["topic_id"],
            subject_id=row["subject_id"],
            topic_name=row["topic_name"] or "",
            subject_name=row["subject_name"] or "",
            kind=kind,
            target_date=_parse_date(row["target_date"]),
            target_percent=row["target_percent"],
            target_level=row["target_level"],
            target_track=track,
            is_master=bool(row["is_master"]),
            note=row["note"],
            created_at=_parse_datetime(row["created_at"]),
            updated_at=_parse_datetime(row["updated_at"]),
        )

    # ---- ساعت مطالعه (بند ۱۵) ----

    def create_study_session(self, session: StudySession) -> int:
        if session.started_at is None:
            raise ValueError("زمان شروع جلسه لازم است.")
        if session.minutes < 0:
            raise ValueError("دقیقهٔ جلسه نمی‌تواند منفی باشد.")
        now = _now()
        cursor = self.conn.execute(
            "INSERT INTO study_session (subject_id, topic_id, activity_id, kind, mode, "
            "started_at, ended_at, paused_seconds, paused_at, minutes, note, "
            "created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session.subject_id,
                session.topic_id,
                session.activity_id,
                session.kind.value,
                session.mode,
                _datetime_str(session.started_at),
                _datetime_str(session.ended_at),
                max(0, int(session.paused_seconds)),
                _datetime_str(session.paused_at),
                max(0, int(session.minutes)),
                session.note,
                _datetime_str(now),
                _datetime_str(now),
            ),
        )
        session.id = cursor.lastrowid
        session.created_at = now
        session.updated_at = now
        return session.id

    def update_study_session(self, session: StudySession) -> None:
        if session.id is None:
            raise ValueError("برای ویرایش جلسه، شناسه لازم است.")
        if session.minutes < 0:
            raise ValueError("دقیقهٔ جلسه نمی‌تواند منفی باشد.")
        now = _now()
        self.conn.execute(
            "UPDATE study_session SET subject_id = ?, topic_id = ?, activity_id = ?, "
            "kind = ?, mode = ?, started_at = ?, ended_at = ?, paused_seconds = ?, "
            "paused_at = ?, minutes = ?, note = ?, updated_at = ? WHERE id = ?",
            (
                session.subject_id,
                session.topic_id,
                session.activity_id,
                session.kind.value,
                session.mode,
                _datetime_str(session.started_at),
                _datetime_str(session.ended_at),
                max(0, int(session.paused_seconds)),
                _datetime_str(session.paused_at),
                max(0, int(session.minutes)),
                session.note,
                _datetime_str(now),
                session.id,
            ),
        )
        session.updated_at = now

    def delete_study_session(self, session_id: int) -> None:
        self.conn.execute("DELETE FROM study_session WHERE id = ?", (session_id,))

    def list_study_sessions(
        self,
        start: Optional[_dt.date] = None,
        end: Optional[_dt.date] = None,
        topic_id: Optional[int] = None,
    ) -> list[StudySession]:
        clauses: list[str] = []
        params: list[Any] = []
        if start is not None:
            clauses.append("date(s.started_at) >= date(?)")
            params.append(start.isoformat())
        if end is not None:
            clauses.append("date(s.started_at) <= date(?)")
            params.append(end.isoformat())
        if topic_id is not None:
            clauses.append("s.topic_id = ?")
            params.append(topic_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            "SELECT s.*, t.name AS topic_name, su.name AS subject_name "
            f"FROM study_session s "
            "LEFT JOIN topic t ON t.id = s.topic_id "
            "LEFT JOIN subject su ON su.id = s.subject_id "
            f"{where} ORDER BY s.started_at DESC, s.id DESC",
            params,
        ).fetchall()
        return [self._study_session_from_row(row) for row in rows]

    def get_study_session(self, session_id: int) -> Optional[StudySession]:
        row = self.conn.execute(
            "SELECT s.*, t.name AS topic_name, su.name AS subject_name "
            "FROM study_session s "
            "LEFT JOIN topic t ON t.id = s.topic_id "
            "LEFT JOIN subject su ON su.id = s.subject_id "
            "WHERE s.id = ?",
            (session_id,),
        ).fetchone()
        return self._study_session_from_row(row) if row else None

    def running_study_session(self) -> Optional[StudySession]:
        """جلسهٔ ناتمام را برمی‌گرداند — پس از بستن برنامه هم حفظ می‌شود."""
        row = self.conn.execute(
            "SELECT s.*, t.name AS topic_name, su.name AS subject_name "
            "FROM study_session s "
            "LEFT JOIN topic t ON t.id = s.topic_id "
            "LEFT JOIN subject su ON su.id = s.subject_id "
            "WHERE s.ended_at IS NULL ORDER BY s.started_at DESC LIMIT 1"
        ).fetchone()
        return self._study_session_from_row(row) if row else None

    def _study_session_from_row(self, row: sqlite3.Row) -> StudySession:
        try:
            kind = SessionKind(row["kind"])
        except ValueError:
            kind = SessionKind.STUDY
        return StudySession(
            id=row["id"],
            subject_id=row["subject_id"],
            subject_name=row["subject_name"] or "",
            topic_id=row["topic_id"],
            topic_name=row["topic_name"] or "",
            activity_id=row["activity_id"],
            kind=kind,
            mode=row["mode"],
            started_at=_parse_datetime(row["started_at"]),
            ended_at=_parse_datetime(row["ended_at"]),
            paused_seconds=int(row["paused_seconds"] or 0),
            paused_at=_parse_datetime(row["paused_at"]),
            minutes=int(row["minutes"] or 0),
            note=row["note"],
            created_at=_parse_datetime(row["created_at"]),
            updated_at=_parse_datetime(row["updated_at"]),
        )

    def add_session_revision(self, revision: StudySessionRevision) -> int:
        if revision.session_id is None:
            raise ValueError("تاریخچهٔ اصلاح باید به یک جلسه وصل باشد.")
        cursor = self.conn.execute(
            "INSERT INTO study_session_revision (session_id, at, field_name, "
            "old_value, new_value, reason) VALUES (?, ?, ?, ?, ?, ?)",
            (
                revision.session_id,
                _datetime_str(revision.at or _now()),
                revision.field_name,
                revision.old_value,
                revision.new_value,
                revision.reason,
            ),
        )
        revision.id = cursor.lastrowid
        return revision.id

    def list_session_revisions(self, session_id: int) -> list[StudySessionRevision]:
        rows = self.conn.execute(
            "SELECT * FROM study_session_revision WHERE session_id = ? "
            "ORDER BY at, id",
            (session_id,),
        ).fetchall()
        return [
            StudySessionRevision(
                id=row["id"],
                session_id=row["session_id"],
                at=_parse_datetime(row["at"]),
                field_name=row["field_name"],
                old_value=row["old_value"],
                new_value=row["new_value"],
                reason=row["reason"],
            )
            for row in rows
        ]

    # ---- مشکلات یادگیری (بند ۱۷) ----

    def create_learning_problem(self, problem: LearningProblem) -> int:
        title = problem.title.strip()
        if not title:
            raise ValueError("عنوان مشکل یادگیری لازم است.")
        if not 1 <= int(problem.severity) <= 5:
            raise ValueError("شدت باید بین ۱ تا ۵ باشد.")
        now = _now()
        cursor = self.conn.execute(
            "INSERT INTO learning_problem (subject_id, topic_id, kind, title, "
            "description, severity, status, first_seen, last_seen, occurrences, "
            "resolution_note, created_at, updated_at, attachment_path, "
            "attachment_name, attachment_sha256, attachment_bytes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                problem.subject_id,
                problem.topic_id,
                problem.kind.value,
                title,
                problem.description,
                int(problem.severity),
                problem.status.value,
                _date_str(problem.first_seen or _dt.date.today()),
                _date_str(problem.last_seen or problem.first_seen or _dt.date.today()),
                max(0, int(problem.occurrences)),
                problem.resolution_note,
                _datetime_str(now),
                _datetime_str(now),
                problem.attachment_path,
                problem.attachment_name,
                problem.attachment_sha256,
                problem.attachment_bytes,
            ),
        )
        problem.id = cursor.lastrowid
        problem.created_at = now
        problem.updated_at = now
        if problem.first_seen is None:
            problem.first_seen = _dt.date.today()
        if problem.last_seen is None:
            problem.last_seen = problem.first_seen
        self.add_problem_event(
            LearningProblemEvent(
                problem_id=problem.id, kind="opened", note="ثبت مشکل یادگیری"
            )
        )
        return problem.id

    def update_learning_problem(self, problem: LearningProblem) -> None:
        if problem.id is None:
            raise ValueError("برای ویرایش مشکل، شناسه لازم است.")
        if not problem.title.strip():
            raise ValueError("عنوان مشکل یادگیری لازم است.")
        if not 1 <= int(problem.severity) <= 5:
            raise ValueError("شدت باید بین ۱ تا ۵ باشد.")
        now = _now()
        self.conn.execute(
            "UPDATE learning_problem SET subject_id = ?, topic_id = ?, kind = ?, "
            "title = ?, description = ?, severity = ?, status = ?, first_seen = ?, "
            "last_seen = ?, occurrences = ?, resolution_note = ?, updated_at = ?, "
            "attachment_path = ?, attachment_name = ?, attachment_sha256 = ?, "
            "attachment_bytes = ? WHERE id = ?",
            (
                problem.subject_id,
                problem.topic_id,
                problem.kind.value,
                problem.title.strip(),
                problem.description,
                int(problem.severity),
                problem.status.value,
                _date_str(problem.first_seen),
                _date_str(problem.last_seen),
                max(0, int(problem.occurrences)),
                problem.resolution_note,
                _datetime_str(now),
                problem.attachment_path,
                problem.attachment_name,
                problem.attachment_sha256,
                problem.attachment_bytes,
                problem.id,
            ),
        )
        problem.updated_at = now

    def delete_learning_problem(self, problem_id: int) -> None:
        self.conn.execute("DELETE FROM learning_problem WHERE id = ?", (problem_id,))

    def list_learning_problems(
        self, status: Optional[ProblemStatus] = None, topic_id: Optional[int] = None
    ) -> list[LearningProblem]:
        clauses: list[str] = []
        params: list[Any] = []
        if status is not None:
            clauses.append("p.status = ?")
            params.append(status.value)
        if topic_id is not None:
            clauses.append("p.topic_id = ?")
            params.append(topic_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            "SELECT p.*, t.name AS topic_name, s.name AS subject_name "
            "FROM learning_problem p "
            "LEFT JOIN topic t ON t.id = p.topic_id "
            "LEFT JOIN subject s ON s.id = p.subject_id "
            f"{where} ORDER BY p.severity DESC, p.updated_at DESC, p.id DESC",
            params,
        ).fetchall()
        return [self._learning_problem_from_row(row) for row in rows]

    def _learning_problem_from_row(self, row: sqlite3.Row) -> LearningProblem:
        try:
            kind = ProblemKind(row["kind"])
        except ValueError:
            kind = ProblemKind.CONCEPTUAL_GAP
        try:
            status = ProblemStatus(row["status"])
        except ValueError:
            status = ProblemStatus.OPEN
        return LearningProblem(
            id=row["id"],
            subject_id=row["subject_id"],
            subject_name=row["subject_name"] or "",
            topic_id=row["topic_id"],
            topic_name=row["topic_name"] or "",
            kind=kind,
            title=row["title"],
            description=row["description"],
            severity=int(row["severity"]),
            status=status,
            first_seen=_parse_date(row["first_seen"]),
            last_seen=_parse_date(row["last_seen"]),
            occurrences=int(row["occurrences"] or 0),
            resolution_note=row["resolution_note"],
            attachment_path=row["attachment_path"],
            attachment_name=row["attachment_name"] or "",
            attachment_sha256=row["attachment_sha256"],
            attachment_bytes=row["attachment_bytes"] or 0,
            created_at=_parse_datetime(row["created_at"]),
            updated_at=_parse_datetime(row["updated_at"]),
        )

    def add_problem_event(self, event: LearningProblemEvent) -> int:
        if event.problem_id is None:
            raise ValueError("رویداد مشکل باید به یک مشکل وصل باشد.")
        cursor = self.conn.execute(
            "INSERT INTO learning_problem_event (problem_id, at, kind, note) "
            "VALUES (?, ?, ?, ?)",
            (
                event.problem_id,
                _datetime_str(event.at or _now()),
                event.kind,
                event.note,
            ),
        )
        event.id = cursor.lastrowid
        return event.id

    def list_problem_events(self, problem_id: int) -> list[LearningProblemEvent]:
        rows = self.conn.execute(
            "SELECT * FROM learning_problem_event WHERE problem_id = ? ORDER BY at, id",
            (problem_id,),
        ).fetchall()
        return [
            LearningProblemEvent(
                id=row["id"],
                problem_id=row["problem_id"],
                at=_parse_datetime(row["at"]),
                kind=row["kind"],
                note=row["note"],
            )
            for row in rows
        ]

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
