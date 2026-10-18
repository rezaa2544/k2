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
