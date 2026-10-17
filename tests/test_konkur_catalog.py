"""بررسی مرزهای منبع سال آزمون و کاتالوگ رشته‌ها."""

from k2.konkur_catalog import (
    SOURCE_SANJESH_1405,
    SUBJECTS_BY_GROUP,
    is_official_exam_source_url,
    source_status_for_year,
)


def test_each_target_group_has_subjects_without_official_coefficients():
    assert set(SUBJECTS_BY_GROUP) == {"علوم تجربی", "علوم ریاضی و فنی", "علوم انسانی"}
    assert all(subjects for subjects in SUBJECTS_BY_GROUP.values())
    assert SOURCE_SANJESH_1405.verification == "reported_official_primary_pdf_not_directly_verified"


def test_exam_year_does_not_inherit_prior_year_sources():
    assert source_status_for_year(1405) == "reported_official_primary_pdf_not_directly_verified"
    assert source_status_for_year(1406) == "official_1406_dataset_not_loaded"
    assert source_status_for_year(None) == "year_not_set"


def test_official_exam_source_requires_exact_official_host_not_substring():
    assert is_official_exam_source_url("https://www.sanjesh.org/notice")
    assert is_official_exam_source_url("https://sccr.ir/news/27129")
    assert is_official_exam_source_url("http://medu.gov.ir/")
    assert not is_official_exam_source_url("https://sanjesh.org.example.com/notice")
    assert not is_official_exam_source_url("https://example.com/sanjesh.org")
    assert not is_official_exam_source_url("https://chap.sch.ir/books/13227")
    assert not is_official_exam_source_url("file:///tmp/source")
    assert not is_official_exam_source_url("https://sanjesh.org@evil.example/notice")
