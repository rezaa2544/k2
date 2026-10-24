"""تست‌های سرفصل رسمی در نسخهٔ دسکتاپ (فصل/گفتار + وضعیت + اثر بر برنامه).

چرا این فایل جدا است: پیش‌نمایش وب سرفصل را داخل صفحهٔ «مباحث» نشان
می‌دهد، ولی دسکتاپ صفحهٔ مستقل «سرفصل درس‌ها» دارد. هر دو باید یک معنی
داشته باشند: همان شناسهٔ پایدار ``درس|پایه|فصل|گفتار``، همان هشت سؤال، و
همین قاعده که نام گفتار هرگز ساخته نمی‌شود.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.gui

from PySide6.QtCore import Qt  # noqa: E402

from k2 import konkur_catalog, syllabus as syl  # noqa: E402
from k2.service import AdvisorService  # noqa: E402
from k2.ui.views.syllabus import SyllabusPage  # noqa: E402

CHEMI = "شیمی"
RIAZI = "ریاضی"
FIZIK = "فیزیک"
GENERAL = "فارسی"


@pytest.fixture()
def page(qapp, tmp_path, monkeypatch):
    """صفحهٔ سرفصل روی پایگاه دادهٔ موقت."""
    from k2.ui.views import settings as settings_view

    monkeypatch.setattr(settings_view, "notify", lambda *a, **k: None)
    service = AdvisorService(tmp_path / "syllabus.db")
    widget = SyllabusPage(service)
    yield widget, service
    widget.deleteLater()
    service.close()


def _select(page: SyllabusPage, subject: str, grade: int) -> None:
    page.subject_combo.setCurrentIndex(page.subject_combo.findData(subject))
    page.grade_combo.setCurrentIndex(page.grade_combo.findData(grade))
    page._reload()


def _open_chapter(page: SyllabusPage, chapter_no: int):
    for row in range(page.chapter_table.rowCount()):
        item = page.chapter_table.item(row, 0)
        if item is not None and item.data(Qt.UserRole) == chapter_no:
            page.chapter_table.setCurrentCell(row, 0)
            break
    return page._selected_chapter()


# ---------------------------------------------------------------------------
# بخش اول — بانک درس خالی نیست و دستی تایپ نمی‌شود
# ---------------------------------------------------------------------------


def test_bank_is_not_empty_after_launch(page):
    """بانک سرفصل بعد از باز شدن برنامه خالی نیست."""
    widget, _service = page
    _select(widget, CHEMI, 10)
    assert len(widget._chapters) == 3
    assert [c.sections for c in widget._chapters] == [7, 7, 7]
    chapter = _open_chapter(widget, 1)
    assert chapter is not None
    assert len(widget._sections) == 7


def test_every_course_and_grade_has_a_syllabus(page):
    """همهٔ درس‌های تخصصی و درس‌های عمومی سرفصل دارند."""
    _widget, service = page
    names = service.syllabus_courses()
    for name in (CHEMI, RIAZI, FIZIK, "زیست‌شناسی", "زمین‌شناسی"):
        assert name in names, name
    assert GENERAL in names, GENERAL
    for name in konkur_catalog.GENERAL_SUBJECT_SYLLABUS:
        assert name in names, name


def test_all_sections_are_named_or_explicitly_unknown():
    """هیچ گفتار بی‌نام پنهانی نیست: یا نام رسمی دارد یا «نام ثبت نشده»."""
    for name, by_grade in konkur_catalog.SYLLABUS_BY_COURSE.items():
        for grade, chapters in by_grade.items():
            for chapter in chapters:
                topics = chapter.get("topics")
                sections = chapter.get("sections")
                if topics:
                    assert sections == len(topics), (name, grade, chapter["no"])
                    for title, verified in topics:
                        if title is None:
                            # نام رسمی پیدا نشده؛ باید صریحاً «ساخته نشده»
                            # علامت خورده باشد، نه اینکه خالی رها شود.
                            assert verified is False, (name, grade, chapter["no"])
                            continue
                        assert title and title.strip(), (name, grade, chapter["no"])
                        assert verified is True, (name, grade, chapter["no"], title)
                elif sections is None:
                    # نبود داده صریح است، نه صفر
                    assert chapter.get("title"), (name, grade, chapter["no"])


def test_section_ids_are_stable_and_unique():
    """شناسهٔ گفتار پایدار و یکتاست."""
    seen: set[str] = set()
    for name, by_grade in konkur_catalog.SYLLABUS_BY_COURSE.items():
        for grade, chapters in by_grade.items():
            for chapter in chapters:
                topics = chapter.get("topics")
                if not topics:
                    continue
                for index in range(1, len(topics) + 1):
                    tid = syl.topic_id(name, grade, chapter["no"], index)
                    assert tid == f"{name}|{grade}|{chapter['no']}|{index}"
                    assert tid not in seen, tid
                    seen.add(tid)
    assert len(seen) >= 300


def test_verified_counts_match_official_book(page):
    """شمارش گفتارهای تأییدشده با فهرست رسمی کتاب می‌خواند."""
    _widget, service = page
    assert service.syllabus_progress(CHEMI, 10).sections == 21
    assert service.syllabus_progress(CHEMI, 11).sections == 19
    assert service.syllabus_progress(CHEMI, 12).sections == 17
    assert service.syllabus_progress(RIAZI, 10).sections == 23
    assert service.syllabus_progress(RIAZI, 11).sections == 20
    assert service.syllabus_progress(FIZIK, 10).sections == 23
    assert service.syllabus_progress(FIZIK, 11).sections == 28
    assert service.syllabus_progress("زیست‌شناسی", 10).sections == 22
    assert service.syllabus_progress("زمین‌شناسی", 12).sections == 50


# ---------------------------------------------------------------------------
# بخش دوم — باز کردن درس/پایه/فصل/گفتار و ثبت وضعیت
# ---------------------------------------------------------------------------


def test_user_can_open_course_grade_chapter_and_section(page):
    """کاربر می‌تواند درس، پایه، فصل و گفتار را باز کند."""
    widget, _service = page
    _select(widget, "زیست‌شناسی", 10)
    chapter = _open_chapter(widget, 1)
    assert chapter is not None
    assert chapter.title == "دنیای زنده"
    assert len(widget._sections) == 3
    labels = [s.label for s in widget._sections]
    assert "زیست‌شناسی چیست؟" in labels
    for section in widget._sections:
        assert section.id.startswith("زیست‌شناسی|10|1|")


def test_section_status_persists_across_reopen(page):
    """وضعیت گفتار ثبت، بسته و دوباره باز می‌شود و می‌ماند."""
    widget, service = page
    _select(widget, CHEMI, 10)
    _open_chapter(widget, 1)
    service.syllabus_save_section(
        CHEMI, 10, 1, 1,
        {
            "teaching": "taught",
            "study": "complete",
            "comprehension": "well",
            "consolidation": "initial",
            "testing": "few",
            "analysis": "not_analyzed",
            "essay": "not_done",
            "speed": "slow",
        },
        mastery=62,
        notes="فصل ۳ پیش‌نیاز است",
    )
    # بستن و باز کردن دوبارهٔ صفحه
    widget._reload()
    _open_chapter(widget, 1)
    section = next(s for s in widget._sections if s.no == 1)
    assert section.is_assessed
    assert section.answered == 8
    assert abs(section.mastery - 62) < 0.01
    assert section.record.notes == "فصل ۳ پیش‌نیاز است"
    # رکورد واقعاً در پایگاه داده است، نه فقط در حافظهٔ صفحه
    again = service.syllabus_section_record(CHEMI, 10, 1, 1)
    assert again is not None and again.answered == 8


def test_section_status_survives_service_restart(tmp_path, monkeypatch):
    """وضعیت گفتار با بستن و باز کردن برنامه از بین نمی‌رود."""
    from k2.ui.views import settings as settings_view

    monkeypatch.setattr(settings_view, "notify", lambda *a, **k: None)
    db = tmp_path / "restart.db"
    first = AdvisorService(db)
    first.syllabus_save_section(CHEMI, 10, 2, 3, {"study": "complete"}, mastery=80)
    first.close()

    second = AdvisorService(db)
    record = second.syllabus_section_record(CHEMI, 10, 2, 3)
    assert record is not None
    assert record.study == "complete"
    assert abs(record.mastery - 80) < 0.01
    second.close()


def test_unnamed_section_is_marked_not_invented(page):
    """گفتار بی‌نامِ فصلِ فقط‌عدد‌دار «نام ثبت نشده» می‌شود، نه نام جعلی."""
    widget, service = page
    service.syllabus_set_chapter_count(GENERAL, 10, 10, 5)
    _select(widget, GENERAL, 10)
    _open_chapter(widget, 10)
    assert len(widget._sections) == 5
    for section in widget._sections:
        assert section.official_title is None
        assert "نام ثبت نشده" in section.label
        assert section.label != f"گفتار {section.no}"


def test_rename_and_delete_round_trip(page):
    """تغییر نام گفتار ذخیره می‌شود و بازگشت به نام رسمی ممکن است."""
    widget, service = page
    _select(widget, CHEMI, 10)
    _open_chapter(widget, 1)
    service.syllabus_rename_section(CHEMI, 10, 1, 1, "پدیدایش عنصرها (نام خودم)")
    widget._reload()
    _open_chapter(widget, 1)
    assert next(s for s in widget._sections if s.no == 1).label == "پدیدایش عنصرها (نام خودم)"
    service.syllabus_rename_section(CHEMI, 10, 1, 1, "")
    widget._reload()
    _open_chapter(widget, 1)
    section = next(s for s in widget._sections if s.no == 1)
    assert section.label == "عنصرها چگونه پدید آمدند؟"
    assert section.official_title == "عنصرها چگونه پدید آمدند؟"


def test_delete_removes_only_user_state_not_the_book(page):
    """حذف گفتار فقط وضعیت کاربر را پاک می‌کند؛ کتاب در حال حاضر می‌ماند."""
    widget, service = page
    _select(widget, CHEMI, 10)
    service.syllabus_save_section(CHEMI, 10, 1, 1, {"study": "complete"})
    assert service.syllabus_delete_section(CHEMI, 10, 1, 1) is True
    assert service.syllabus_delete_section(CHEMI, 10, 1, 1) is False
    widget._reload()
    _open_chapter(widget, 1)
    assert len(widget._sections) == 7
    assert next(s for s in widget._sections if s.no == 1).label == (
        "عنصرها چگونه پدید آمدند؟"
    )


# ---------------------------------------------------------------------------
# بخش سوم — اثر وضعیت گفتار بر برنامه‌ریزی و گزارش
# ---------------------------------------------------------------------------


def test_section_status_changes_the_next_action(page):
    """تغییر وضعیت گفتار، «کار بعدی» را عوض می‌کند."""
    _widget, service = page
    before = service.next_action()
    assert "جبران" not in before.title
    service.syllabus_save_section(
        CHEMI, 10, 1, 1, {"study": "not_started", "testing": "not_tested"}
    )
    after = service.next_action()
    assert "جبران" in after.title
    assert "شیمی" in after.reason
    assert "مطالعه ناقص" in after.reason


def test_open_needs_show_up_in_the_weekly_report(page):
    """نیاز باز گفتار در گزارش هفتگی دیده می‌شود."""
    _widget, service = page
    service.syllabus_save_section(CHEMI, 10, 1, 1, {"study": "not_started"})
    service.syllabus_save_section(CHEMI, 10, 2, 1, {"testing": "not_tested"})
    report = service.weekly_report()
    joined = "\n".join(report.notes)
    assert "نیاز باز سرفصل" in joined
    assert "2 گفتار" in joined
    changes = "\n".join(report.next_week_changes)
    assert "پوشش سرفصل" in changes
    assert "306" in changes


def test_progress_counts_only_real_answers(page):
    """پوشش از پاسخ‌های واقعی ساخته می‌شود؛ گفتار ارزیابی‌نشده صفر نیست."""
    _widget, service = page
    progress = service.syllabus_progress(CHEMI, 10)
    assert progress.chapters == 3
    assert progress.sections == 21
    assert progress.assessed == 0
    assert progress.open_needs == 0
    assert progress.coverage == 0.0
    service.syllabus_save_section(CHEMI, 10, 1, 1, {"study": "complete"})
    progress = service.syllabus_progress(CHEMI, 10)
    assert progress.assessed == 1
    assert progress.open_needs == 0
    assert abs(progress.coverage - 100.0 / 21) < 0.01


def test_unknown_chapters_are_reported_as_unknown_not_zero(page):
    """فصل نامشخص در پیشرفت «نامشخص» می‌ماند، نه صفر."""
    _widget, service = page
    _select(page[0], GENERAL, 10)
    progress = service.syllabus_progress(GENERAL, 10)
    assert progress.chapters == 1
    assert progress.sections == 0
    assert progress.unknown_chapters == 1
    assert progress.coverage is None


# ---------------------------------------------------------------------------
# بخش چهارم — بازخوانی دادهٔ اولیه duplicate نمی‌سازد
# ---------------------------------------------------------------------------


def test_reloading_initial_data_creates_no_duplicates(page):
    """بازخوانی دادهٔ اولیه هیچ فصل یا گفتار تکراری نمی‌سازد."""
    widget, service = page
    _select(widget, CHEMI, 10)
    first_chapters = [c.no for c in widget._chapters]
    first_sections = [s.no for s in widget._sections]
    for _ in range(3):
        widget.refresh()
    assert [c.no for c in widget._chapters] == first_chapters
    assert [s.no for s in widget._sections] == first_sections
    # رکوردهای کاربر هم تکراری نمی‌شوند
    service.syllabus_save_section(CHEMI, 10, 1, 1, {"study": "complete"})
    service.syllabus_save_section(CHEMI, 10, 1, 1, {"study": "complete"})
    rows = service.repo.list_syllabus_sections(CHEMI, 10)
    assert len([r for r in rows if r.chapter == 1 and r.section == 1]) == 1


def test_chapter_count_edit_never_becomes_zero(page):
    """خالی کردن تعداد گفتار «نامشخص» می‌شود، نه صفر."""
    widget, service = page
    _select(widget, CHEMI, 10)
    service.syllabus_set_chapter_count(CHEMI, 10, 1, None)
    widget._reload()
    chapter = next(c for c in widget._chapters if c.no == 1)
    assert chapter.sections is None
    assert chapter.is_unknown
    # ارزیابی روی فصل نامشخص ممکن نیست
    with pytest.raises(ValueError):
        service.syllabus_save_section(CHEMI, 10, 1, 1, {"study": "complete"})
    service.syllabus_set_chapter_count(CHEMI, 10, 1, 7)
    widget._reload()
    assert next(c for c in widget._chapters if c.no == 1).sections == 7


def test_section_outside_range_is_rejected(page):
    """گفتار بیرون از بازهٔ فصل پذیرفته نمی‌شود."""
    _widget, service = page
    with pytest.raises(ValueError):
        service.syllabus_save_section(CHEMI, 10, 1, 99, {"study": "complete"})
    with pytest.raises(ValueError):
        service.syllabus_save_section(CHEMI, 10, 99, 1, {"study": "complete"})


def test_progress_is_not_lost_when_chapter_count_shrinks(page):
    """کوتاه کردن تعداد گفتار، وضعیت گفتارهای باقی‌مانده را پاک نمی‌کند."""
    _widget, service = page
    service.syllabus_save_section(CHEMI, 10, 1, 1, {"study": "complete"})
    service.syllabus_set_chapter_count(CHEMI, 10, 1, 3)
    assert service.syllabus_section_record(CHEMI, 10, 1, 1) is not None
    service.syllabus_set_chapter_count(CHEMI, 10, 1, 7)
    record = service.syllabus_section_record(CHEMI, 10, 1, 1)
    assert record is not None and record.study == "complete"
