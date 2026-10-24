"""سرفصل رسمی درس‌ها: فصل و گفتار، وضعیت مطالعه و اثر آن بر برنامه‌ریزی.

چرا این ماژول جدا است: دادهٔ «فصل/گفتار» از کتاب درسی می‌آید و ثابت است،
ولی وضعیت هر گفتار (تدریس، مطالعه، درک، تثبیت، تست، تحلیل خطا، تمرین
تشریحی، سرعت) پیشرفت واقعی کاربر است. این دو را از هم جدا نگه می‌داریم تا:

* پاک‌کردن یا بازچینانی کتاب، پیشرفت ثبت‌شدهٔ کاربر را از بین نبرد؛
* برنامه هیچ‌وقت نامی برای گفتار نسازد که در کتاب نیست؛
* نسخهٔ دسکتاپ و پیش‌نمایش وب یک معنی واحد داشته باشند (همان شناسهٔ
  پایدار ``درس|پایه|فصل|گفتار`` و همان هشت سؤال).
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Optional, Sequence

from .domain.models import SyllabusChapterEdit, SyllabusSection
from . import konkur_catalog

#: هشت سؤال وضعیت هر گفتار. ترتیب و کلیدها با پیش‌نمایش وب یکی است.
ASSESS_QUESTIONS: tuple[dict, ...] = (
    {
        "key": "teaching",
        "title": "سؤال ۱ از ۸ · تدریس",
        "hint": "وضعیت کلاس یا تدریس این گفتار",
        "options": (
            ("not_taught", "هنوز تدریس نشده"),
            ("taught", "تدریس شده"),
            ("partial", "بخشی از تدریس را از دست داده‌ام"),
            ("missed", "کلاس را از دست داده‌ام و باید جبران کنم"),
            ("repair", "نیاز به رفع اشکال از تدریس دارم"),
            ("unknown", "نمی‌دانم / نیاز به ارزیابی"),
        ),
    },
    {
        "key": "study",
        "title": "سؤال ۲ از ۸ · مطالعه",
        "hint": "مطالعهٔ محتوای این گفتار",
        "options": (
            ("not_started", "هنوز مطالعه نکرده‌ام"),
            ("started", "مطالعه را شروع کرده‌ام ولی کامل نیست"),
            ("complete", "کامل خوانده‌ام"),
            ("read_unsure", "قبلاً خوانده‌ام اما مطمئن نیستم همه‌اش را یادم باشد"),
            ("need_reread", "نیاز دارم دوباره مطالعه کنم"),
            ("unknown", "نمی‌دانم / نیاز به ارزیابی"),
        ),
    },
    {
        "key": "comprehension",
        "title": "سؤال ۳ از ۸ · فهم مطلب",
        "hint": "این با «تمام‌شدن مطالعه» یکی نیست",
        "options": (
            ("not_understood", "مطلب را نفهمیده‌ام"),
            ("partial", "بخشی از مطلب را متوجه شده‌ام"),
            ("mostly", "کلیت مطلب را فهمیده‌ام ولی نکات مبهم دارم"),
            ("well", "مطلب را خوب فهمیده‌ام"),
            ("repair", "نیاز به رفع اشکال دارم"),
            ("unknown", "نمی‌دانم / نیاز به ارزیابی"),
        ),
    },
    {
        "key": "consolidation",
        "title": "سؤال ۴ از ۸ · تثبیت",
        "hint": "مرور و تثبیت؛ جدا از مطالعه",
        "options": (
            ("not_reviewed", "هنوز مرور نکرده‌ام"),
            ("initial", "مرور اولیه انجام شده ولی تثبیت نشده"),
            ("consolidated", "مرور و تثبیت انجام شده"),
            ("risk", "قبلاً تثبیت شده ولی احتمال فراموشی وجود دارد"),
            ("unknown", "نمی‌دانم به تثبیت رسیده‌ام یا نه"),
        ),
    },
    {
        "key": "testing",
        "title": "سؤال ۵ از ۸ · تست‌زنی",
        "hint": "تست مبحثی و زمان‌دار این گفتار",
        "options": (
            ("not_tested", "هنوز تست نزده‌ام"),
            ("few", "تست کم زده‌ام"),
            ("topic_tested", "تست مبحثی زده‌ام"),
            ("enough_errors", "تست کافی زده‌ام ولی اشتباه زیاد دارم"),
            ("satisfactory", "تست زده‌ام و عملکردم رضایت‌بخش بوده"),
            ("retake", "باید تست‌های قبلی را دوباره بزنم"),
            ("unknown", "نمی‌دانم / نیاز به ارزیابی"),
        ),
    },
    {
        "key": "analysis",
        "title": "سؤال ۶ از ۸ · تحلیل آزمون و اشتباهات",
        "hint": "تحلیل جداست از خود آزمون",
        "options": (
            ("not_analyzed", "هنوز تحلیل نکرده‌ام"),
            ("partial", "بخشی از آزمون را تحلیل کرده‌ام"),
            ("full", "تحلیل کامل شده"),
            ("known_not_fixed", "اشتباهاتم را می‌دانم ولی هنوز اصلاح نکرده‌ام"),
            ("fixed", "اشتباهاتم را بررسی و اصلاح کرده‌ام"),
        ),
    },
    {
        "key": "essay",
        "title": "سؤال ۷ از ۸ · آمادگی تشریحی",
        "hint": "برای امتحانات نهایی؛ مستقل از وضعیت کنکور",
        "options": (
            ("not_done", "سؤال تشریحی حل نکرده‌ام"),
            ("flawed", "پاسخ‌نویسی را تمرین کرده‌ام ولی اشکال دارم"),
            ("practiced", "تمرین تشریحی انجام داده‌ام"),
            ("ready", "پاسخ‌هایم را بررسی کرده‌ام و آمادگی مناسبی دارم"),
            ("unknown", "نمی‌دانم / نیاز به ارزیابی"),
        ),
    },
    {
        "key": "speed",
        "title": "سؤال ۸ از ۸ · سرعت پاسخ‌دهی زمان‌دار",
        "hint": "مهارت در شرایط زمان‌دار؛ جدا از درست یا غلط بودن",
        "options": (
            ("slow", "درست حل می‌کنم ولی زمان زیادی می‌برد"),
            ("partial_time", "بعضی سؤال‌ها را در زمان لازم حل می‌کنم"),
            ("timed_ok", "در زمان لازم پاسخ می‌دهم"),
            ("panic", "زمان‌دار بودن استرس می‌سازد و کار را خراب می‌کند"),
            ("unknown", "نمی‌دانم / نیاز به ارزیابی"),
        ),
    },
)

ASSESS_KEYS: tuple[str, ...] = tuple(q["key"] for q in ASSESS_QUESTIONS)

#: نگاشت پاسخ → نوع نیاز باز و برچسب آن. «زمان کافی دارم» عمداً نیامده
#: چون چیزی برای جبران ندارد.
NEED_MAP: tuple[tuple[str, tuple[str, ...], str, str], ...] = (
    ("teaching", ("missed", "repair"), "class", "عقب‌افتادگی کلاس یا جبران تدریس"),
    ("study", ("not_started", "started", "need_reread"), "study", "مطالعه ناقص"),
    (
        "comprehension",
        ("not_understood", "partial", "repair"),
        "concept",
        "نفهمیدن یا نیاز به رفع اشکال",
    ),
    (
        "consolidation",
        ("not_reviewed", "initial", "risk", "unknown"),
        "consolidation",
        "تثبیت ناقص",
    ),
    (
        "testing",
        ("not_tested", "few", "enough_errors", "retake"),
        "testing",
        "تست‌نزدن یا اشتباه زیاد",
    ),
    (
        "analysis",
        ("not_analyzed", "partial", "known_not_fixed"),
        "analysis",
        "تحلیل‌نکردن آزمون",
    ),
    ("essay", ("not_done", "flawed"), "essay", "تمرین تشریحی انجام‌نشده"),
    ("speed", ("slow", "partial_time", "panic"), "testing", "تمرین زمان‌دار ناکافی"),
)


# ---------------------------------------------------------------------------
# کلید پایدار
# ---------------------------------------------------------------------------


def topic_id(subject: str, grade: int, chapter: int, section: int) -> str:
    """شناسهٔ پایدار گفتار — همان قالب پیش‌نمایش وب."""
    return f"{subject}|{int(grade)}|{int(chapter)}|{int(section)}"


def split_topic_id(tid: str) -> Optional[dict]:
    """تجزیهٔ شناسهٔ گفتار؛ اگر ساختار درست نبود ``None``."""
    parts = str(tid).split("|")
    if len(parts) != 4:
        return None
    subject, grade, chapter, section = parts
    try:
        return {
            "subject": subject,
            "grade": int(grade),
            "chapter": int(chapter),
            "section": int(section),
        }
    except ValueError:
        return None


def chapter_key(subject: str, grade: int, chapter: int) -> str:
    return f"{subject}|{int(grade)}|{int(chapter)}"


#: نام کتاب درسی هر درس عمومی.
GENERAL_BOOK_LABEL: dict[str, str] = konkur_catalog.GENERAL_BOOK_LABEL


def general_grades(subject: str) -> tuple[int, ...]:
    """پایه‌های یک درس عمومی — منبع حقیقت، کاتالوگ است (نه نسخهٔ موازی)."""
    return konkur_catalog.general_grades(subject)


def general_rows(subject: str, grade: int) -> list[dict]:
    """ردیف‌های خام فصل یک درس عمومی برای یک پایه.

    ترتیب: فهرست تأییدشدهٔ همان پایه ← فصل فرضیِ «نامشخص». هیچ‌وقت عددی
    که در کتاب نیست ساخته نمی‌شود.
    """
    if subject not in konkur_catalog.GENERAL_SUBJECT_SYLLABUS:
        return []
    verified = konkur_catalog.GENERAL_SUBJECT_CHAPTERS.get(subject, {}).get(
        int(grade)
    )
    if verified:
        return [dict(row) for row in verified]
    # پایه‌ای که فهرست رسمی ندارد: یک فصل فرضی با عدد نامشخص
    return [
        {
            "no": int(grade),
            "title": f"{GENERAL_BOOK_LABEL.get(subject, subject)} · پایهٔ {grade}",
            "sections": None,
            "note": konkur_catalog.general_subject_note(subject),
        }
    ]


def general_chapter(subject: str, grade: int) -> Optional[ChapterView]:
    """فصل فرضی درس عمومی (وقتی فهرست رسمی برای آن پایه ثبت نشده)."""
    rows = general_rows(subject, grade)
    if len(rows) != 1 or rows[0].get("topics"):
        return None
    row = rows[0]
    return ChapterView(
        no=int(row["no"]),
        title=row["title"],
        base_title=row["title"],
        sections=None,
        base_sections=None,
        topics=None,
        note=row.get("note", ""),
        subject=subject,
        grade=int(grade),
    )


def raw_chapters(subject: str, grade: int) -> list[dict]:
    """ردیف‌های خام فصل برای یک درس/پایه (کاتالوگ + درس‌های عمومی)."""
    base = list(konkur_catalog.syllabus_for(subject, grade))
    if base:
        return base
    return general_rows(subject, grade)


# ---------------------------------------------------------------------------
# نمای فصل و گفتار (ادغام کاتالوگ با ویرایش کاربر)
# ---------------------------------------------------------------------------


@dataclass
class ChapterView:
    """یک فصل با ادغام دادهٔ کتاب و ویرایش کاربر."""

    no: int
    title: str
    base_title: str
    sections: Optional[int]
    base_sections: Optional[int]
    topics: Optional[tuple[str, ...]]
    note: str = ""
    subject: str = ""
    grade: int = 0
    #: اگر پر باشد این فصل فقط برای آن گروه آموزشی معنا دارد (مثل
    #: «ترمودینامیک» که فقط در فیزیک دهم رشتهٔ ریاضی تدریس می‌شود).
    group_only: str = ""

    @property
    def is_unknown(self) -> bool:
        return self.sections is None

    def applies_to(self, group: str) -> bool:
        """آیا این فصل برای گروه آموزشی داده‌شده معنا دارد؟"""
        if not self.group_only:
            return True
        return group == self.group_only

    @property
    def is_count_only(self) -> bool:
        """فصلی که فقط عدد دارد و نام گفتار ثبت نشده است."""
        return self.sections is not None and self.topics is None


@dataclass
class SectionView:
    """یک گفتار با برچسب و وضعیت کاربر."""

    subject: str
    grade: int
    chapter: int
    no: int
    label: str
    official_title: Optional[str]
    edited_title: str
    record: Optional[SyllabusSection]

    @property
    def id(self) -> str:
        return topic_id(self.subject, self.grade, self.chapter, self.no)

    @property
    def is_assessed(self) -> bool:
        return bool(self.record and self.record.updated_at)

    @property
    def answered(self) -> int:
        return self.record.answered if self.record else 0

    @property
    def needs(self) -> list[dict]:
        return section_needs(self.record)

    @property
    def mastery(self) -> Optional[float]:
        return section_mastery(self.record)


def chapter_view(
    subject: str,
    grade: int,
    chapter_no: int,
    edit: Optional[SyllabusChapterEdit] = None,
) -> Optional[ChapterView]:
    """فصل ``chapter_no`` را با ادغام ویرایش کاربر می‌سازد."""
    raw = next(
        (c for c in raw_chapters(subject, grade) if int(c["no"]) == int(chapter_no)), None
    )
    if raw is None:
        return None
    topics = raw.get("topics")
    base_sections = raw.get("sections")
    if topics:
        base_sections = len(topics)
    sections = base_sections
    title = raw.get("title", "")
    note = raw.get("note", "") or ""
    if edit is not None:
        if edit.title:
            title = edit.title
        if edit.confirmed:
            # ادیت تأییدشده از کتاب مقدم است؛ ``None`` یعنی کاربر عمداً
            # «نامشخص» را انتخاب کرده، نه اینکه عدد کتاب برگردد.
            sections = None if edit.sections is None else int(edit.sections)
        elif edit.sections is not None:
            sections = int(edit.sections)
    return ChapterView(
        no=int(chapter_no),
        title=title,
        base_title=raw.get("title", ""),
        sections=sections,
        base_sections=base_sections,
        topics=tuple(t[0] for t in topics) if topics else None,
        note=note,
        subject=subject,
        grade=int(grade),
        group_only=raw.get("group_only", "") or "",
    )


def chapters(
    subject: str,
    grade: int,
    edits: Optional[Sequence[SyllabusChapterEdit]] = None,
) -> list[ChapterView]:
    """همهٔ فصل‌های یک درس/پایه با ادغام ویرایش‌های کاربر."""
    by_key = {chapter_key(e.subject, e.grade, e.chapter): e for e in (edits or ())}
    out: list[ChapterView] = []
    for raw in raw_chapters(subject, grade):
        no = int(raw["no"])
        view = chapter_view(subject, grade, no, by_key.get(chapter_key(subject, grade, no)))
        if view is not None:
            out.append(view)
    return out


def section_label(chapter: ChapterView, section_no: int, record: Optional[SyllabusSection]) -> str:
    """عنوان قابل نمایش گفتار.

    ترتیب: ویرایش کاربر ← نام رسمی کتاب ← «گفتار N · نام ثبت نشده».
    نامی ساخته نمی‌شود.
    """
    if record is not None and record.title:
        return record.title
    if chapter.topics and 1 <= section_no <= len(chapter.topics):
        return chapter.topics[section_no - 1]
    return f"گفتار {section_no} · نام ثبت نشده"


def sections(
    subject: str,
    grade: int,
    chapter: ChapterView,
    records: Optional[Sequence[SyllabusSection]] = None,
) -> list[SectionView]:
    """گفتارهای یک فصل؛ اگر تعداد نامشخص باشد فهرست خالی است."""
    if chapter.sections is None:
        return []
    by_no = {int(r.section): r for r in (records or ())}
    out: list[SectionView] = []
    for no in range(1, int(chapter.sections) + 1):
        record = by_no.get(no)
        official = None
        if chapter.topics and 1 <= no <= len(chapter.topics):
            official = chapter.topics[no - 1]
        out.append(
            SectionView(
                subject=subject,
                grade=grade,
                chapter=chapter.no,
                no=no,
                label=section_label(chapter, no, record),
                official_title=official,
                edited_title=record.title if record else "",
                record=record,
            )
        )
    return out


# ---------------------------------------------------------------------------
# وضعیت
# ---------------------------------------------------------------------------


def section_needs(record: Optional[SyllabusSection]) -> list[dict]:
    """نیازهای باز یک گفتار؛ گفتار ارزیابی‌نشده هیچ نیازی نمی‌سازد."""
    if record is None or not record.updated_at:
        return []
    out: list[dict] = []
    for key, values, need_type, label in NEED_MAP:
        value = getattr(record, key, None)
        if value in values:
            out.append({"type": need_type, "label": label, "question": key})
    return out


def section_mastery(record: Optional[SyllabusSection]) -> Optional[float]:
    """تسلط خوداظهاری؛ ``None`` اگر کاربر مطمئن نیست."""
    if record is None or record.mastery is None:
        return None
    value = float(record.mastery)
    if value != value:  # NaN
        return None
    return max(0.0, min(100.0, value))


def section_badge(record: Optional[SyllabusSection]) -> tuple[str, str]:
    """(متن، لحن) وضعیت کوتاه گفتار."""
    if record is None or not record.updated_at:
        return ("ارزیابی نشده", "warn")
    needs = section_needs(record)
    if not needs:
        return ("نیازی باز نیست", "ok")
    if len(needs) >= 3:
        return (f"{len(needs)} نیاز باز", "danger")
    return (f"{len(needs)} نیاز باز", "backlog")


def new_record(subject: str, grade: int, chapter: int, section: int) -> SyllabusSection:
    return SyllabusSection(subject=subject, grade=grade, chapter=chapter, section=section)


def now_iso() -> str:
    return _dt.datetime.now().replace(microsecond=0).isoformat()


def save_record(
    record: SyllabusSection,
    answers: dict,
    mastery: Optional[float] = None,
    notes: str = "",
) -> SyllabusSection:
    """پاسخ‌های هشت سؤال را روی رکورد می‌نشاند و زمان را به‌روز می‌کند.

    فقط کلیدهای شناخته‌شده پذیرفته می‌شوند تا دادهٔ بی‌ربط ذخیره نشود.
    """
    for key in ASSESS_KEYS:
        if key in answers:
            value = answers[key]
            setattr(record, key, value if value else None)
    record.mastery = mastery
    record.notes = notes or ""
    record.updated_at = now_iso()
    return record


# ---------------------------------------------------------------------------
# خلاصهٔ پیشرفت
# ---------------------------------------------------------------------------


@dataclass
class SyllabusProgress:
    """خلاصهٔ پوشش سرفصل برای گزارش و «کار بعدی»."""

    chapters: int = 0
    sections: int = 0
    assessed: int = 0
    open_needs: int = 0
    unknown_chapters: int = 0

    @property
    def coverage(self) -> Optional[float]:
        """درصد گفتارهای ارزیابی‌شده؛ ``None`` اگر هیچ گفتاری شناخته نشود."""
        if not self.sections:
            return None
        return 100.0 * self.assessed / self.sections


def progress(
    subject: Optional[str] = None,
    grade: Optional[int] = None,
    *,
    chapter_views: Optional[Sequence[ChapterView]] = None,
    records: Optional[Sequence[SyllabusSection]] = None,
) -> SyllabusProgress:
    """پیشرفت سرفصل را از دادهٔ واقعی می‌سازد (هیچ عددی حدس نمی‌زند)."""
    if chapter_views is None:
        chapter_views = (
            chapters(subject or "", grade or 0)
            if subject is not None and grade is not None
            else []
        )
    records = records or []
    by_id = {topic_id(r.subject, r.grade, r.chapter, r.section): r for r in records}
    out = SyllabusProgress()
    for chapter in chapter_views:
        out.chapters += 1
        if chapter.sections is None:
            out.unknown_chapters += 1
            continue
        for no in range(1, int(chapter.sections) + 1):
            out.sections += 1
            record = by_id.get(
                topic_id(chapter.subject, chapter.grade, chapter.no, no)
            )
            if record is not None and record.updated_at:
                out.assessed += 1
                out.open_needs += len(section_needs(record))
    return out
