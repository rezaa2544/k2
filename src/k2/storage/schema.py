"""تعریف schema و مهاجرت‌های پایگاه داده.

هر migration یک اسکریپت SQL و یک شمارهٔ نسخه دارد. نسخهٔ فعلی schema در
``PRAGMA user_version`` نگهداری می‌شود. هیچ تغییری در schema بدون افزودن
migration انجام نمی‌شود.
"""

from __future__ import annotations

SCHEMA_VERSION = 6

#: اسکریپت نسخهٔ ۱ — اسکیمای اولیه.
MIGRATION_1 = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exam_profile (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    name                  TEXT NOT NULL,
    group_name            TEXT NOT NULL DEFAULT '',
    target_date           TEXT,
    date_status           TEXT NOT NULL DEFAULT 'unknown',
    source_note           TEXT NOT NULL DEFAULT '',
    negative_marking_ratio REAL NOT NULL DEFAULT 0,
    percentage_formula    TEXT NOT NULL DEFAULT 'raw',
    regulation_version    TEXT NOT NULL DEFAULT '',
    created_at            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS subject (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_profile_id INTEGER REFERENCES exam_profile(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    coefficient     REAL NOT NULL DEFAULT 1.0,
    topic_weight    REAL
);

CREATE TABLE IF NOT EXISTS topic (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id    INTEGER REFERENCES subject(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    content_type  TEXT NOT NULL DEFAULT 'conceptual',
    scope_status  TEXT NOT NULL DEFAULT 'unknown',
    mastery       TEXT NOT NULL DEFAULT 'L0',
    self_assessed INTEGER,
    notes         TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS fixed_event (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT NOT NULL,
    kind         TEXT NOT NULL DEFAULT 'live_class',
    subject_id   INTEGER REFERENCES subject(id) ON DELETE SET NULL,
    weekday      INTEGER NOT NULL DEFAULT 0,
    start_minute INTEGER NOT NULL DEFAULT 0,
    end_minute   INTEGER NOT NULL DEFAULT 0,
    is_recorded  INTEGER NOT NULL DEFAULT 0,
    notes        TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS routine (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT NOT NULL,
    kind          TEXT NOT NULL DEFAULT 'meal',
    start_minute  INTEGER NOT NULL DEFAULT 0,
    end_minute    INTEGER NOT NULL DEFAULT 0,
    weekdays      TEXT NOT NULL DEFAULT '[0,1,2,3,4,5,6]',
    scope         TEXT NOT NULL DEFAULT 'daily',
    counts_as_study INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS event_exception (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id          INTEGER NOT NULL REFERENCES fixed_event(id) ON DELETE CASCADE,
    date              TEXT NOT NULL,
    cancelled         INTEGER NOT NULL DEFAULT 0,
    new_start_minute  INTEGER,
    new_end_minute    INTEGER,
    reason            TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS activity (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    title             TEXT NOT NULL,
    type              TEXT NOT NULL DEFAULT 'processing',
    subject_id        INTEGER REFERENCES subject(id) ON DELETE SET NULL,
    topic_id          INTEGER REFERENCES topic(id) ON DELETE SET NULL,
    est_minutes       INTEGER NOT NULL DEFAULT 45,
    actual_minutes    INTEGER NOT NULL DEFAULT 0,
    remaining_minutes INTEGER NOT NULL DEFAULT 0,
    min_chunk         INTEGER NOT NULL DEFAULT 20,
    max_chunk         INTEGER NOT NULL DEFAULT 90,
    splittable        INTEGER NOT NULL DEFAULT 1,
    deadline_type     TEXT NOT NULL DEFAULT 'none',
    deadline_at       TEXT,
    depends_on        TEXT NOT NULL DEFAULT '[]',
    state             TEXT NOT NULL DEFAULT 'planned',
    state_reason      TEXT NOT NULL DEFAULT '',
    energy_need       TEXT NOT NULL DEFAULT 'medium',
    created_at        TEXT NOT NULL,
    first_planned_at  TEXT,
    times_rescheduled INTEGER NOT NULL DEFAULT 0,
    resume_marker     INTEGER,
    origin            TEXT NOT NULL DEFAULT 'manual'
);

CREATE TABLE IF NOT EXISTS activity_event (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id INTEGER NOT NULL REFERENCES activity(id) ON DELETE CASCADE,
    at          TEXT NOT NULL,
    kind        TEXT NOT NULL DEFAULT 'state_change',
    from_state  TEXT,
    to_state    TEXT,
    note        TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS schedule_slot (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id  INTEGER NOT NULL REFERENCES activity(id) ON DELETE CASCADE,
    date         TEXT NOT NULL,
    start_minute INTEGER NOT NULL,
    end_minute   INTEGER NOT NULL,
    minutes      INTEGER NOT NULL,
    score        REAL NOT NULL DEFAULT 0,
    reasons      TEXT NOT NULL DEFAULT '[]',
    chunk_index  INTEGER NOT NULL DEFAULT 1,
    chunk_total  INTEGER NOT NULL DEFAULT 1,
    generated_at TEXT NOT NULL,
    is_current   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS review_item (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id     INTEGER,
    topic_id       INTEGER,
    label          TEXT NOT NULL,
    item_type      TEXT NOT NULL DEFAULT 'concept',
    interval_days  REAL NOT NULL DEFAULT 0,
    ease           REAL NOT NULL DEFAULT 2.0,
    difficulty     INTEGER NOT NULL DEFAULT 3,
    lapses         INTEGER NOT NULL DEFAULT 0,
    last_review    TEXT,
    due_date       TEXT,
    state          TEXT NOT NULL DEFAULT 'new',
    last_grade     INTEGER,
    last_time_ratio REAL,
    content        TEXT NOT NULL DEFAULT '',
    created_at     TEXT NOT NULL,
    success_streak INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS review_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id    INTEGER NOT NULL REFERENCES review_item(id) ON DELETE CASCADE,
    at         TEXT NOT NULL,
    grade      INTEGER NOT NULL DEFAULT 0,
    confidence INTEGER NOT NULL DEFAULT 2,
    seconds    INTEGER,
    note       TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS exam_attempt (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_profile_id  INTEGER REFERENCES exam_profile(id) ON DELETE SET NULL,
    name             TEXT NOT NULL,
    kind             TEXT NOT NULL DEFAULT 'mock',
    taken_at         TEXT NOT NULL,
    subject_id       INTEGER REFERENCES subject(id) ON DELETE SET NULL,
    total            INTEGER NOT NULL DEFAULT 0,
    correct          INTEGER NOT NULL DEFAULT 0,
    wrong            INTEGER NOT NULL DEFAULT 0,
    blank            INTEGER NOT NULL DEFAULT 0,
    duration_minutes INTEGER NOT NULL DEFAULT 0,
    raw_score        REAL NOT NULL DEFAULT 0,
    percentage       REAL NOT NULL DEFAULT 0,
    note             TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS exam_question (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER NOT NULL REFERENCES exam_attempt(id) ON DELETE CASCADE,
    subject_id INTEGER,
    topic_id   INTEGER,
    number     INTEGER NOT NULL DEFAULT 0,
    status     TEXT NOT NULL DEFAULT 'correct',
    error_code TEXT,
    seconds    INTEGER,
    note       TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS error_record (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id           INTEGER REFERENCES exam_attempt(id) ON DELETE CASCADE,
    question_id          INTEGER REFERENCES exam_question(id) ON DELETE SET NULL,
    code                 TEXT NOT NULL,
    topic_id             INTEGER,
    subject_id           INTEGER,
    created_at           TEXT NOT NULL,
    resolution_activity_id INTEGER REFERENCES activity(id) ON DELETE SET NULL,
    resolved_at          TEXT,
    retest_attempt_id    INTEGER,
    note                 TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS onboarding_step (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    step_key   TEXT NOT NULL UNIQUE,
    value      TEXT NOT NULL DEFAULT '',
    completed  INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
"""

#: اسکریپت نسخهٔ ۲ — افزودن ستون مرجع منبع و اندیس‌های کارایی.
MIGRATION_2 = """
ALTER TABLE activity ADD COLUMN source_ref TEXT NOT NULL DEFAULT '';
ALTER TABLE topic ADD COLUMN last_review_at TEXT;
CREATE INDEX IF NOT EXISTS idx_schedule_slot_date ON schedule_slot(date);
CREATE INDEX IF NOT EXISTS idx_schedule_slot_activity ON schedule_slot(activity_id);
CREATE INDEX IF NOT EXISTS idx_activity_state ON activity(state);
CREATE INDEX IF NOT EXISTS idx_review_item_due ON review_item(due_date);
CREATE INDEX IF NOT EXISTS idx_exam_attempt_taken ON exam_attempt(taken_at);
"""

#: نسخهٔ ۳ — سال هدف، وضعیت انتخاب درس و منشأ ضرایب به‌صورت تفکیک‌شده.
#: ضریب برنامه‌ریزیِ قدیمی حفظ می‌شود؛ ضرایب آزمون و سوابق تحصیلی ستون‌های جدا دارند.
MIGRATION_3 = """
ALTER TABLE exam_profile ADD COLUMN exam_year INTEGER;
ALTER TABLE subject ADD COLUMN is_selected INTEGER NOT NULL DEFAULT 1;
ALTER TABLE subject ADD COLUMN exam_coefficient REAL;
ALTER TABLE subject ADD COLUMN exam_coefficient_status TEXT NOT NULL DEFAULT 'unknown';
ALTER TABLE subject ADD COLUMN exam_coefficient_source TEXT NOT NULL DEFAULT '';
ALTER TABLE subject ADD COLUMN academic_coefficient REAL;
ALTER TABLE subject ADD COLUMN academic_coefficient_status TEXT NOT NULL DEFAULT 'unknown';
ALTER TABLE subject ADD COLUMN academic_coefficient_source TEXT NOT NULL DEFAULT '';

CREATE TABLE IF NOT EXISTS textbook (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_profile_id INTEGER NOT NULL REFERENCES exam_profile(id) ON DELETE CASCADE,
    subject_id      INTEGER REFERENCES subject(id) ON DELETE SET NULL,
    title           TEXT NOT NULL,
    book_code       TEXT NOT NULL DEFAULT '',
    grade           TEXT NOT NULL DEFAULT '',
    edition_year    INTEGER,
    source_url      TEXT NOT NULL DEFAULT '',
    source_status   TEXT NOT NULL DEFAULT 'user_entered',
    is_selected     INTEGER NOT NULL DEFAULT 1,
    UNIQUE(exam_profile_id, subject_id, title, book_code)
);
CREATE INDEX IF NOT EXISTS idx_subject_profile_selected
    ON subject(exam_profile_id, is_selected);
CREATE INDEX IF NOT EXISTS idx_textbook_profile_subject
    ON textbook(exam_profile_id, subject_id, is_selected);
"""

#: نسخهٔ ۵ — مدل حافظهٔ DSR روی آیتم‌های مرور (سند تحقیق ۵).
#: ستون‌های تازه برای رکوردهای موجود از فاصلهٔ فعلی برآورد می‌شوند.
MIGRATION_5 = """
ALTER TABLE review_item ADD COLUMN stability_days REAL NOT NULL DEFAULT 0;
ALTER TABLE review_item ADD COLUMN retrievability REAL NOT NULL DEFAULT 1;
"""

#: نسخهٔ ۴ — ثبت تاریخچهٔ سنجش عملکردی برای ارزیابی تطبیقی تسلط.
MIGRATION_4 = """
CREATE TABLE IF NOT EXISTS learning_evidence (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id         INTEGER NOT NULL REFERENCES topic(id) ON DELETE CASCADE,
    observed_on      TEXT NOT NULL,
    source           TEXT NOT NULL DEFAULT 'diagnostic',
    score            REAL NOT NULL CHECK(score >= 0 AND score <= 1),
    item_count       INTEGER NOT NULL DEFAULT 0 CHECK(item_count >= 0),
    confidence       INTEGER NOT NULL DEFAULT 2 CHECK(confidence BETWEEN 1 AND 4),
    duration_seconds INTEGER CHECK(duration_seconds IS NULL OR duration_seconds >= 0),
    note             TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_learning_evidence_topic_date
    ON learning_evidence(topic_id, observed_on, id);
"""

#: نسخهٔ ۶ — مهلت‌های مبحث، ساعت مطالعه و مشکلات یادگیری (بندهای ۱۲، ۱۵، ۱۷).
#: این migration هم جدول‌های تازه می‌سازد و هم ستون‌های مسیر دوگانه را به
#: جدول topic اضافه می‌کند. مقادیر پیش‌فرض محافظه‌کارانه‌اند تا رکوردهای
#: موجود بدون از دست دادن اطلاعات به مسیر درست نگاشت شوند.
MIGRATION_6 = """
ALTER TABLE topic ADD COLUMN konkur_stage TEXT NOT NULL DEFAULT 'conceptual';
ALTER TABLE topic ADD COLUMN final_stage TEXT NOT NULL DEFAULT 'textbook_study';
ALTER TABLE topic ADD COLUMN konkur_evidence_id INTEGER;
ALTER TABLE topic ADD COLUMN final_evidence_id INTEGER;
ALTER TABLE topic ADD COLUMN prerequisite_share REAL NOT NULL DEFAULT 0;
ALTER TABLE topic ADD COLUMN final_exam_share REAL NOT NULL DEFAULT 0;
ALTER TABLE topic ADD COLUMN estimated_minutes INTEGER;

CREATE TABLE IF NOT EXISTS topic_deadline (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id       INTEGER NOT NULL REFERENCES topic(id) ON DELETE CASCADE,
    subject_id     INTEGER REFERENCES subject(id) ON DELETE SET NULL,
    kind           TEXT NOT NULL DEFAULT 'initial_learning',
    target_date    TEXT,
    target_percent REAL CHECK(target_percent IS NULL OR (target_percent >= 0 AND target_percent <= 100)),
    target_level   TEXT,
    target_track   TEXT NOT NULL DEFAULT 'konkur',
    is_master      INTEGER NOT NULL DEFAULT 0,
    note           TEXT NOT NULL DEFAULT '',
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_topic_deadline_unique
    ON topic_deadline(topic_id, kind, target_track);
CREATE INDEX IF NOT EXISTS idx_topic_deadline_date ON topic_deadline(target_date);

CREATE TABLE IF NOT EXISTS study_session (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id     INTEGER REFERENCES subject(id) ON DELETE SET NULL,
    topic_id       INTEGER REFERENCES topic(id) ON DELETE SET NULL,
    activity_id    INTEGER REFERENCES activity(id) ON DELETE SET NULL,
    kind           TEXT NOT NULL DEFAULT 'study',
    mode           TEXT NOT NULL DEFAULT 'timer',
    started_at     TEXT NOT NULL,
    ended_at       TEXT,
    paused_seconds INTEGER NOT NULL DEFAULT 0 CHECK(paused_seconds >= 0),
    paused_at      TEXT,
    minutes        INTEGER NOT NULL DEFAULT 0 CHECK(minutes >= 0),
    note           TEXT NOT NULL DEFAULT '',
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_study_session_started ON study_session(started_at);
CREATE INDEX IF NOT EXISTS idx_study_session_topic ON study_session(topic_id, started_at);
CREATE INDEX IF NOT EXISTS idx_study_session_kind ON study_session(kind, started_at);

CREATE TABLE IF NOT EXISTS study_session_revision (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES study_session(id) ON DELETE CASCADE,
    at         TEXT NOT NULL,
    field_name TEXT NOT NULL,
    old_value  TEXT NOT NULL DEFAULT '',
    new_value  TEXT NOT NULL DEFAULT '',
    reason     TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_session_revision_session
    ON study_session_revision(session_id, at);

CREATE TABLE IF NOT EXISTS learning_problem (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id      INTEGER REFERENCES subject(id) ON DELETE SET NULL,
    topic_id        INTEGER REFERENCES topic(id) ON DELETE SET NULL,
    kind            TEXT NOT NULL DEFAULT 'conceptual_gap',
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    severity        INTEGER NOT NULL DEFAULT 3 CHECK(severity BETWEEN 1 AND 5),
    status          TEXT NOT NULL DEFAULT 'open',
    first_seen      TEXT,
    last_seen       TEXT,
    occurrences     INTEGER NOT NULL DEFAULT 0,
    resolution_note TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_learning_problem_status ON learning_problem(status, severity);
CREATE INDEX IF NOT EXISTS idx_learning_problem_topic ON learning_problem(topic_id);

CREATE TABLE IF NOT EXISTS learning_problem_event (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id INTEGER NOT NULL REFERENCES learning_problem(id) ON DELETE CASCADE,
    at         TEXT NOT NULL,
    kind       TEXT NOT NULL DEFAULT 'progressed',
    note       TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_problem_event_problem
    ON learning_problem_event(problem_id, at);
"""

MIGRATIONS: list[tuple[int, str]] = [
    (1, MIGRATION_1),
    (2, MIGRATION_2),
    (3, MIGRATION_3),
    (4, MIGRATION_4),
    (5, MIGRATION_5),
    (6, MIGRATION_6),
]
