"""پشتیبان‌گیری و بازیابی (DATA-02).

از «API پشتیبان SQLite» استفاده می‌شود تا فایل پشتیبان در حتی هنگام
نوشته‌شدن پایگاه داده هم سالم باشد. هنگام بازیابی، نسخهٔ schema و
یکپارچگی فایل بررسی می‌شود.
"""

from __future__ import annotations

import datetime as _dt
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .db import apply_migrations, connect, current_version, integrity_check, table_counts

BACKUP_SUFFIX = ".k2backup"


class BackupError(RuntimeError):
    """خطا در پشتیبان‌گیری یا بازیابی."""


@dataclass
class BackupInfo:
    """فرادادهٔ یک فایل پشتیبان."""

    path: Path
    schema_version: int
    created_at: _dt.datetime
    counts: dict[str, int]
    app_version: str = ""

    def to_json(self) -> str:
        return json.dumps(
            {
                "path": str(self.path),
                "schema_version": self.schema_version,
                "created_at": self.created_at.isoformat(timespec="seconds"),
                "counts": self.counts,
                "app_version": self.app_version,
            },
            ensure_ascii=False,
            indent=2,
        )

    @classmethod
    def from_json(cls, text: str) -> "BackupInfo":
        raw = json.loads(text)
        return cls(
            path=Path(raw["path"]),
            schema_version=int(raw["schema_version"]),
            created_at=_dt.datetime.fromisoformat(raw["created_at"]),
            counts=dict(raw.get("counts", {})),
            app_version=raw.get("app_version", ""),
        )


def default_backup_dir() -> Path:
    """پوشهٔ پیش‌فرض پشتیبان‌ها."""
    from ..config import app_data_dir

    return app_data_dir() / "backups"


def create_backup(
    db_path: Path | str,
    backup_dir: Optional[Path | str] = None,
    *,
    app_version: str = "",
) -> BackupInfo:
    """یک نسخهٔ پشتیبان کامل از پایگاه داده می‌سازد."""
    source = Path(db_path)
    if not source.exists():
        raise BackupError(f"پایگاه داده یافت نشد: {source}")

    target_dir = Path(backup_dir) if backup_dir is not None else default_backup_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    target = target_dir / f"k2-backup-{stamp}{BACKUP_SUFFIX}"
    # اگر در یک ثانیه دو پشتیبان گرفته شود، نام یکتا می‌سازیم تا پشتیبان
    # قبلی بی‌صدا بازنویسی (و دادهٔ کاربر از دست) نشود.
    if target.exists():
        counter = 2
        while True:
            candidate = target_dir / f"k2-backup-{stamp}-{counter}{BACKUP_SUFFIX}"
            if not candidate.exists():
                target = candidate
                break
            counter += 1

    src_conn = connect(source)
    try:
        version = current_version(src_conn)
        counts = table_counts(src_conn)
        dst_conn = sqlite3.connect(str(target))
        try:
            with dst_conn:
                src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
    finally:
        src_conn.close()

    info = BackupInfo(
        path=target,
        schema_version=version,
        created_at=_dt.datetime.now(),
        counts=counts,
        app_version=app_version,
    )
    sidecar = target.with_suffix(target.suffix + ".json")
    sidecar.write_text(info.to_json(), encoding="utf-8")
    return info


def inspect_backup(backup_path: Path | str) -> BackupInfo:
    """فرادادهٔ یک فایل پشتیبان را می‌خواند و اعتبارسنجی می‌کند."""
    path = Path(backup_path)
    if not path.exists():
        raise BackupError(f"فایل پشتیبان یافت نشد: {path}")

    conn = connect(path)
    try:
        integrity = integrity_check(conn)
        if integrity != "ok":
            raise BackupError(f"فایل پشتیبان سالم نیست: {integrity}")
        version = current_version(conn)
        counts = table_counts(conn)
    finally:
        conn.close()

    sidecar = path.with_suffix(path.suffix + ".json")
    created_at = _dt.datetime.fromtimestamp(path.stat().st_mtime)
    app_version = ""
    if sidecar.exists():
        try:
            info = BackupInfo.from_json(sidecar.read_text(encoding="utf-8"))
            created_at = info.created_at
            app_version = info.app_version
        except (OSError, ValueError, KeyError):  # pragma: no cover
            pass

    return BackupInfo(
        path=path,
        schema_version=version,
        created_at=created_at,
        counts=counts,
        app_version=app_version,
    )


def restore_backup(
    backup_path: Path | str,
    db_path: Path | str,
    *,
    apply_pending_migrations: bool = True,
) -> BackupInfo:
    """پایگاه داده را از فایل پشتیبان بازیابی می‌کند.

    نسخهٔ schema بررسی می‌شود؛ اگر پشتیبان قدیمی‌تر باشد، مهاجرت‌های لازم
    اعمال می‌شوند. اگر پشتیبان جدیدتر از نسخهٔ پشتیبانی‌شدهٔ برنامه باشد،
    بازیابی رد می‌شود.
    """
    backup = Path(backup_path)
    target = Path(db_path)

    if not backup.exists():
        raise BackupError(f"فایل پشتیبان یافت نشد: {backup}")

    source_conn = connect(backup)
    try:
        integrity = integrity_check(source_conn)
        if integrity != "ok":
            raise BackupError(f"فایل پشتیبان سالم نیست: {integrity}")
        backup_version = current_version(source_conn)

        target.parent.mkdir(parents=True, exist_ok=True)
        # از فایل پشتیبان یک کپی موقت می‌گیریم تا اگر چیزی خراب شد،
        # پایگاه دادهٔ فعلی سالم بماند.
        staging = target.with_suffix(".restore-tmp")
        if staging.exists():
            staging.unlink()
        dst_conn = sqlite3.connect(str(staging))
        try:
            with dst_conn:
                source_conn.backup(dst_conn)
        finally:
            dst_conn.close()
    finally:
        source_conn.close()

    # اعتبارسنجی فایل موقت پیش از جایگزینی
    check_conn = connect(staging)
    try:
        if integrity_check(check_conn) != "ok":
            raise BackupError("فایل بازیابی‌شده پس از انتقال سالم نیست.")
        if apply_pending_migrations:
            apply_migrations(check_conn)
        counts = table_counts(check_conn)
        final_version = current_version(check_conn)
    except Exception:
        check_conn.close()
        if staging.exists():
            staging.unlink()
        raise
    check_conn.close()

    if target.exists():
        target.unlink()
    for suffix in ("-wal", "-shm"):
        extra = Path(str(target) + suffix)
        if extra.exists():
            extra.unlink()
    staging.replace(target)

    return BackupInfo(
        path=backup,
        schema_version=final_version,
        created_at=_dt.datetime.now(),
        counts=counts,
        app_version="",
    )


def list_backups(backup_dir: Optional[Path | str] = None) -> list[Path]:
    """فهرست فایل‌های پشتیبان موجود."""
    target = Path(backup_dir) if backup_dir is not None else default_backup_dir()
    if not target.exists():
        return []
    return sorted(
        (p for p in target.glob(f"*{BACKUP_SUFFIX}") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
