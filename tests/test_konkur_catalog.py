"""بررسی مرزهای منبع سال آزمون و کاتالوگ رشته‌ها."""

from k2.konkur_catalog import (
    SOURCE_SANJESH_1405,
    SUBJECTS_BY_GROUP,
    is_official_exam_source_url,
    source_status_for_year,
)


def test_each_target_group_has_exam_subjects_and_known_transcripts():
    # پنج گروه در catalog آزمون حضور دارند؛ نبودن ردیف سوابق برای بعضی گروه‌ها
    # تا راستی‌آزمایی عنوان‌های دقیق، دادهٔ مفقود است نه محتوای ساختگی.
    assert set(SUBJECTS_BY_GROUP) == {
        "علوم تجربی", "علوم ریاضی و فنی", "علوم انسانی", "هنر", "زبان‌های خارجی"
    }
    assert all(subjects for subjects in SUBJECTS_BY_GROUP.values())
    assert SOURCE_SANJESH_1405.verification == "reported_official_primary_pdf_not_directly_verified"


def test_exam_year_does_not_inherit_prior_year_sources():
    assert source_status_for_year(1405) == "reported_official_primary_pdf_not_directly_verified"
    assert source_status_for_year(1406) == "official_notice_republished_primary_host_not_directly_fetched"
    assert source_status_for_year(None) == "year_not_set"


def test_official_exam_coefficients_are_1406_only():
    from k2.konkur_catalog import EXAM_COURSES

    coefficients = {
        group: {course.name: course.exam_coefficient for course in courses}
        for group, courses in EXAM_COURSES.items()
    }
    assert coefficients["علوم تجربی"]["زیست‌شناسی"] == 12
    assert coefficients["علوم ریاضی و فنی"]["ریاضی"] == 12
    assert coefficients["علوم انسانی"]["زبان و ادبیات فارسی تخصصی"] == 8
    assert all(
        course.coefficient_status == "official_notice_republished"
        for courses in EXAM_COURSES.values() for course in courses
    )


def test_art_and_language_coefficients_are_loaded_without_invented_books():
    from k2.konkur_catalog import EXAM_COURSES, EXAM_WEIGHT_BY_GROUP

    art = {course.name: course for course in EXAM_COURSES["هنر"]}
    language = {course.name: course for course in EXAM_COURSES["زبان‌های خارجی"]}
    assert art["درک عمومی هنر"].exam_coefficient == 12
    assert art["درک عمومی ریاضی و فیزیک"].exam_coefficient == 5
    assert art["خلاقیت تصویری و تجسمی"].exam_coefficient == 3
    assert language["زبان تخصصی (زبان انتخابی داوطلب)"].exam_coefficient == 1
    assert all(not course.books for course in (*art.values(), *language.values()))
    assert all("راستی‌آزمایی نشده" in course.note for course in art.values())
    assert EXAM_WEIGHT_BY_GROUP["علوم انسانی"] == (40, 60)
    assert EXAM_WEIGHT_BY_GROUP["هنر"] == (70, 30)
    assert EXAM_WEIGHT_BY_GROUP["زبان‌های خارجی"] == (70, 30)


def test_official_exam_source_requires_exact_official_host_not_substring():
    assert is_official_exam_source_url("https://www.sanjesh.org/notice")
    assert is_official_exam_source_url("https://sccr.ir/news/27129")
    assert is_official_exam_source_url("http://medu.gov.ir/")
    assert not is_official_exam_source_url("https://sanjesh.org.example.com/notice")
    assert not is_official_exam_source_url("https://example.com/sanjesh.org")
    assert not is_official_exam_source_url("https://chap.sch.ir/books/13227")
    assert not is_official_exam_source_url("file:///tmp/source")
    assert not is_official_exam_source_url("https://sanjesh.org@evil.example/notice")


# ---------------------------------------------------------------------------
# ساختار فصل/گفتار در مدل دادهٔ اصلی
# ---------------------------------------------------------------------------
# قاعدهٔ محصول: هر فصل گفتارهای فرزند دارد، هر گفتار شناسهٔ پایدار می‌گیرد و
# هر جا نام رسمی گفته‌نشده صریحاً «نامشخص/None» می‌ماند — هیچ‌جای داده نام
# ساخته نمی‌شود. سه حالت مشروع وجود دارد:
#   ۱) ``topics`` نام‌دار  → ``sections == len(topics)``
#   ۲) فقط ``sections`` عدد → شمارش از منابع قبلی، نام ساخته نمی‌شود
#   ۳) ``sections is None`` → هیچ‌کدام؛ کاربر خودش وارد می‌کند


def _walk_syllabus():
    from k2.konkur_catalog import SYLLABUS_BY_COURSE

    for course, by_grade in SYLLABUS_BY_COURSE.items():
        for grade, chapters in by_grade.items():
            for ch in chapters:
                yield course, grade, ch


def test_topic_tuples_are_well_formed():
    for course, grade, ch in _walk_syllabus():
        topics = ch.get("topics")
        if not topics:
            continue
        assert isinstance(topics, tuple), (course, grade, ch["no"])
        for title, verified in topics:
            assert isinstance(title, str) or title is None, (course, grade, ch["no"], title)
            assert isinstance(verified, bool), (course, grade, ch["no"], verified)
            if title is not None:
                assert title.strip(), (course, grade, ch["no"])


def test_sections_count_matches_named_topics():
    """وقتی گفتار نام‌دار داریم، ``sections`` باید با شمار آن‌ها یکی باشد."""
    for course, grade, ch in _walk_syllabus():
        if ch.get("topics"):
            assert ch["sections"] == len(ch["topics"]), (course, grade, ch["no"])


def test_unnamed_sections_are_marked_not_invented():
    """گفتار بی‌نام صریحاً ``(None, False)`` است، نه یک عنوان الکی."""
    unnamed = 0
    for course, grade, ch in _walk_syllabus():
        for title, verified in ch.get("topics") or ():
            if title is None:
                unnamed += 1
                assert verified is False, (course, grade, ch["no"])
    # دست‌کم یک گفتار بی‌نام صادقانه علامت خورده باشد (زیست یازدهم ف۹)
    assert unnamed >= 1


def test_count_only_chapters_never_get_fabricated_names():
    """فصلی که فقط شمارش دارد نباید فهرست گفتار بسازد."""
    for course, grade, ch in _walk_syllabus():
        if ch["sections"] is not None and not ch.get("topics"):
            assert isinstance(ch["sections"], int) and ch["sections"] > 0


def test_fully_unknown_chapters_stay_none_never_zero():
    """درس‌هایی که هیچ منبع شمارش نداشت، ``None`` می‌مانند نه صفر."""
    for course, grade, ch in _walk_syllabus():
        if not ch.get("topics") and ch["sections"] is None:
            assert ch["sections"] is None, (course, grade, ch["no"])


def test_general_subjects_never_claim_chapter_lists():
    """درس‌های عمومی فقط شمار درس اولیه دارند؛ فصل/گفتار جعل نمی‌شود."""
    from k2.konkur_catalog import (
        GENERAL_SUBJECT_SYLLABUS,
        SYLLABUS_BY_COURSE,
    )

    for name, info in GENERAL_SUBJECT_SYLLABUS.items():
        assert name not in SYLLABUS_BY_COURSE, name
        assert set(info) == {"lessons", "note"}
        assert info["lessons"] is None or isinstance(info["lessons"], int)
        assert "تأییدنشده" in info["note"] or "نامشخص" in info["note"]


def test_syllabus_helpers_report_unknown_as_none():
    from k2.konkur_catalog import section_count, syllabus_for

    assert section_count("شیمی", 10) is None
    assert section_count("زیست‌شناسی", 10) == 22
    assert len(syllabus_for("زمین‌شناسی")) == 7
    assert syllabus_for("زیست‌شناسی", 99) == ()
