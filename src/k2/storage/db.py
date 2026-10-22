"""اتصال به پایگاه داده، مهاجرت و مدیریت تراکنش."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from .schema import MIGRATIONS, SCHEMA_VERSION


class MigrationError(RuntimeError):
    """خطا در اجرای مهاجرت."""


def connect(path: Path | str) -> sqlite3.Connection:
    """اتصال به پایگاه دادهٔ SQLite با تنظیمات مناسب برای برنامهٔ دسکتاپ."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def current_version(conn: sqlite3.Connection) -> int:
    """نسخهٔ فعلی schema."""
    row = conn.execute("PRAGMA user_version").fetchone()
    return int(row[0]) if row else 0


def apply_migrations(conn: sqlite3.Connection, target_version: Optional[int] = None) -> int:
    """اجرای مهاجرت‌های لازم و بازگرداندن نسخهٔ نهایی.

    اگر نسخهٔ فعلی از نسخهٔ هدف جلوتر باشد (پایگاه دادهٔ آینده)، خطا داده
    می‌شود تا دادهٔ ناشناخته بی‌سروصدا بازنویسی نشود.
    """
    version = current_version(conn)
    if target_version is None:
        target_version = SCHEMA_VERSION
    if version > target_version:
        raise MigrationError(
            f"نسخهٔ پایگاه داده ({version}) از نسخهٔ پشتیبانی‌شده ({target_version}) "
            "جدیدتر است؛ برنامه این پایگاه داده را باز نمی‌کند."
        )

    for migration_version, script in MIGRATIONS:
        if migration_version <= version:
            continue
        if migration_version > target_version:
            break
        try:
            conn.executescript(script)
            conn.execute(f"PRAGMA user_version = {int(migration_version)}")
            conn.commit()
        except sqlite3.Error as exc:  # pragma: no cover - مسیر خطای مهاجرت
            conn.rollback()
            raise MigrationError(
                f"مهاجرت به نسخهٔ {migration_version} ناموفق بود: {exc}"
            ) from exc
        version = migration_version

    return version


def initialize(path: Path | str) -> sqlite3.Connection:
    """ساخت/به‌روزرسانی پایگاه داده و بازگرداندن اتصال."""
    conn = connect(path)
    apply_migrations(conn)
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """تراکنش اتمیک."""
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def integrity_check(conn: sqlite3.Connection) -> str:
    """بررسی یکپارچگی پایگاه داده."""
    row = conn.execute("PRAGMA integrity_check").fetchone()
    return str(row[0]) if row else "unknown"


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """شمارش رکوردهای جدول‌های اصلی (برای بازیابی پشتیبان)."""
    tables = [
        "exam_profile",
        "subject",
        "topic",
        "fixed_event",
        "routine",
        "activity",
        "activity_event",
        "schedule_slot",
        "review_item",
        "review_log",
        "exam_attempt",
        "exam_question",
        "error_record",
        "topic_deadline",
        "study_session",
        "study_session_revision",
        "learning_problem",
        "learning_problem_event",
        "onboarding_step",
    ]
    counts: dict[str, int] = {}
    for table in tables:
        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        counts[table] = int(row[0]) if row else 0
    return counts
