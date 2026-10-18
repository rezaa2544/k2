"""تست ذخیره‌سازی، مهاجرت و پشتیبان/بازیابی (DATA-01/DATA-02)."""

from __future__ import annotations

import datetime as _dt
import sqlite3
from pathlib import Path

import pytest

from k2.domain.enums import ActivityState, ActivityType, DateStatus
from k2.domain.models import Activity, ExamProfile, Subject, Topic
from k2.storage import (
    BackupError,
    MigrationError,
    Repository,
    apply_migrations,
    connect,
    create_backup,
    current_version,
    initialize,
    inspect_backup,
    integrity_check,
    list_backups,
    restore_backup,
    table_counts,
)
from k2.storage.schema import MIGRATIONS, SCHEMA_VERSION


def test_fresh_database_is_created_at_current_version(tmp_path: Path):
    conn = initialize(tmp_path / "new.db")
    assert current_version(conn) == SCHEMA_VERSION
    assert integrity_check(conn) == "ok"
    conn.close()


def test_all_migrations_are_applied_in_order(tmp_path: Path):
    conn = connect(tmp_path / "m.db")
    versions = [version for version, _ in MIGRATIONS]
    assert versions == sorted(versions)
    assert versions[0] == 1
    assert versions[-1] == SCHEMA_VERSION
    apply_migrations(conn)
    assert current_version(conn) == SCHEMA_VERSION
    conn.close()


def test_migration_from_v1_preserves_data(tmp_path: Path):
    """مهاجرت از نسخهٔ ۱ تا نسخهٔ جاری باید داده‌های قبلی را نگه دارد."""
    path = tmp_path / "legacy.db"
    conn = connect(path)
    apply_migrations(conn, target_version=1)
    assert current_version(conn) == 1

    conn.execute(
        "INSERT INTO activity (title, type, created_at) VALUES (?, ?, ?)",
        ("کار قدیمی", "processing", "2026-01-01T00:00:00"),
    )
    conn.commit()
    conn.close()

    conn = connect(path)
    apply_migrations(conn)
    assert current_version(conn) == SCHEMA_VERSION
    row = conn.execute("SELECT title FROM activity").fetchone()
    assert row["title"] == "کار قدیمی"
    # ستون جدید اضافه شده و مقدار پیش‌فرض دارد
    row = conn.execute("SELECT source_ref FROM activity").fetchone()
    assert row["source_ref"] == ""
    # migration 3 داده‌های قدیمی را انتخاب‌شده نگه می‌دارد و وزن رسمی نمی‌سازد.
    assert conn.execute("SELECT is_selected FROM subject").fetchall() == []
    conn.close()


def test_migration_from_v4_adds_memory_columns(tmp_path: Path):
    """مهاجرت ۴→۵ ستون‌های مدل حافظه را اضافه و داده‌های مرور را نگه می‌دارد."""
    path = tmp_path / "v4.db"
    conn = connect(path)
    apply_migrations(conn, target_version=4)
    assert current_version(conn) == 4
    conn.execute(
        "INSERT INTO review_item (label, item_type, due_date, state, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        ("مورد قدیمی", "concept", "2026-01-01", "new", "2026-01-01T00:00:00"),
    )
    conn.commit()
    conn.close()

    conn = connect(path)
    apply_migrations(conn)
    assert current_version(conn) == SCHEMA_VERSION
    row = conn.execute(
        "SELECT label, stability_days, retrievability, difficulty FROM review_item"
    ).fetchone()
    assert row["label"] == "مورد قدیمی"
    # مقدار پیش‌فرض: پایداری صفر (نامعلوم) و بازیابستگی ۱
    assert row["stability_days"] == 0
    assert row["retrievability"] == 1
    assert row["difficulty"] is not None
    conn.close()


def test_future_database_is_rejected(tmp_path: Path):
    conn = connect(tmp_path / "future.db")
    conn.execute("PRAGMA user_version = 999")
    conn.commit()
    with pytest.raises(MigrationError):
        apply_migrations(conn)
    conn.close()


def test_repository_crud_roundtrip(tmp_path: Path):
    conn = initialize(tmp_path / "r.db")
    repo = Repository(conn)

    profile = ExamProfile(
        name="کنکور سراسری",
        group_name="ریاضی",
        target_date=_dt.date(2027, 7, 1),
        date_status=DateStatus.ESTIMATED,
        source_note="پیش‌بینی",
    )
    repo.create_exam_profile(profile)
    assert profile.id is not None

    subject = Subject(name="ریاضی", exam_profile_id=profile.id, coefficient=3.0)
    repo.create_subject(subject)
    topic = Topic(subject_id=subject.id, name="تابع")
    repo.create_topic(topic)

    activity = Activity(
        title="پردازش کلاس",
        type=ActivityType.PROCESSING,
        subject_id=subject.id,
        topic_id=topic.id,
        est_minutes=45,
        remaining_minutes=45,
    )
    repo.create_activity(activity)
    conn.commit()

    loaded = repo.get_activity(activity.id)
    assert loaded is not None
    assert loaded.title == "پردازش کلاس"
    assert loaded.subject_name == "ریاضی"
    assert loaded.topic_name == "تابع"

    subjects = repo.list_subjects()
    assert subjects[0].coefficient == 3.0
    topics = repo.list_topics()
    assert topics[0].subject_name == "ریاضی"
    conn.close()


def test_transition_is_validated_and_logged(tmp_path: Path):
    conn = initialize(tmp_path / "t.db")
    repo = Repository(conn)
    activity = Activity(title="کار", type=ActivityType.PROCESSING)
    repo.create_activity(activity)
    conn.commit()

    repo.transition_activity(activity, ActivityState.READY, reason="آماده")
    assert activity.state == ActivityState.READY
    events = repo.list_activity_events(activity.id)
    assert len(events) == 1
    assert events[0].to_state == ActivityState.READY

    repo.transition_activity(activity, ActivityState.DONE, reason="انجام شد")
    with pytest.raises(ValueError):
        # بازگشت از وضعیت پایانی مجاز نیست
        repo.transition_activity(activity, ActivityState.IN_PROGRESS, reason="نامعتبر")
    conn.close()


def test_backup_and_restore_roundtrip(tmp_path: Path):
    db_path = tmp_path / "k2.db"
    conn = initialize(db_path)
    repo = Repository(conn)
    profile = ExamProfile(name="آزمون هدف")
    repo.create_exam_profile(profile)
    activity = Activity(title="کار ماندگار", type=ActivityType.HOMEWORK)
    repo.create_activity(activity)
    conn.commit()
    before = table_counts(conn)
    conn.close()

    info = create_backup(db_path, tmp_path / "backups")
    assert info.path.exists()
    assert info.schema_version == SCHEMA_VERSION
    assert info.counts == before

    # تغییر داده و سپس بازیابی
    conn = initialize(db_path)
    repo = Repository(conn)
    repo.create_activity(Activity(title="کار اضافه", type=ActivityType.HOMEWORK))
    conn.commit()
    conn.close()

    restored = restore_backup(info.path, db_path)
    assert restored.schema_version == SCHEMA_VERSION
    assert restored.counts == before

    conn = initialize(db_path)
    titles = [row["title"] for row in conn.execute("SELECT title FROM activity")]
    assert titles == ["کار ماندگار"]
    conn.close()


def test_backup_inspection_detects_healthy_file(tmp_path: Path):
    db_path = tmp_path / "k2.db"
    conn = initialize(db_path)
    conn.close()
    info = create_backup(db_path, tmp_path / "backups")
    inspected = inspect_backup(info.path)
    assert inspected.schema_version == SCHEMA_VERSION
    assert list_backups(tmp_path / "backups")


def test_restore_missing_file_raises(tmp_path: Path):
    with pytest.raises(BackupError):
        restore_backup(tmp_path / "nope.k2backup", tmp_path / "k2.db")


def test_restore_rejects_newer_schema(tmp_path: Path):
    db_path = tmp_path / "k2.db"
    conn = initialize(db_path)
    conn.close()
    info = create_backup(db_path, tmp_path / "backups")

    # شبیه‌سازی پشتیبانِ آینده
    conn = connect(info.path)
    conn.execute("PRAGMA user_version = 999")
    conn.commit()
    conn.close()

    with pytest.raises(MigrationError):
        restore_backup(info.path, db_path)


def test_database_works_offline_without_network(tmp_path: Path):
    """هستهٔ برنامه نباید به شبکه نیاز داشته باشد (هیچ اتصال شبکه‌ای ساخته نمی‌شود)."""
    conn = initialize(tmp_path / "offline.db")
    repo = Repository(conn)
    repo.create_exam_profile(ExamProfile(name="آزمون"))
    conn.commit()
    assert table_counts(conn)["exam_profile"] == 1
    conn.close()


def test_migration_v2_to_v3_preserves_profiles_and_separates_coefficient_types(tmp_path: Path):
    path = tmp_path / "v2.db"
    conn = connect(path)
    apply_migrations(conn, target_version=2)
    conn.execute(
        "INSERT INTO exam_profile (name, group_name, created_at) VALUES (?, ?, ?)",
        ("کنکور", "تجربی", "2026-01-01T00:00:00"),
    )
    profile_id = conn.execute("SELECT id FROM exam_profile").fetchone()["id"]
    conn.execute(
        "INSERT INTO subject (exam_profile_id, name, coefficient) VALUES (?, ?, ?)",
        (profile_id, "زیست", 1.0),
    )
    conn.commit()
    conn.close()

    conn = initialize(path)
    repo = Repository(conn)
    profile = repo.get_exam_profile(profile_id)
    subject = repo.list_subjects(profile_id)[0]
    assert profile is not None and profile.exam_year is None
    assert subject.is_selected is True
    assert subject.exam_coefficient is None
    assert subject.academic_coefficient is None
    conn.close()


def test_repository_persists_subject_selection_and_textbooks(tmp_path: Path):
    conn = initialize(tmp_path / "catalog.db")
    repo = Repository(conn)
    profile = ExamProfile(name="آزمون", exam_year=1406)
    repo.create_exam_profile(profile)
    subject = Subject(name="زیست‌شناسی", exam_profile_id=profile.id)
    repo.create_subject(subject)
    from k2.domain.models import Textbook

    book = Textbook(
        exam_profile_id=profile.id, subject_id=subject.id,
        title="زیست‌شناسی (۱)", book_code="110216", grade="دهم",
        source_url="https://chap.sch.ir/", source_status="official_catalog",
    )
    repo.create_textbook(book)
    repo.set_subject_selected(subject.id, False)
    repo.set_textbook_selected(book.id, False)
    conn.commit()

    assert repo.get_exam_profile(profile.id).exam_year == 1406
    assert repo.list_subjects(profile.id)[0].is_selected is False
    assert repo.list_textbooks(profile.id)[0].is_selected is False
    assert repo.list_subjects(profile.id, include_unselected=False) == []
    assert repo.list_textbooks(profile.id, include_unselected=False) == []
    conn.close()
