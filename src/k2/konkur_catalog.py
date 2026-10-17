"""پیش‌فهرست رشته‌ها برای راه‌اندازی K2.

این فایل عمداً هیچ ضریب آزمون اختصاصی یا ضریب سوابق تحصیلی وارد نمی‌کند.
فهرست درس‌ها فقط راهنمای اولیه است؛ پیش از محاسبهٔ وزن هر درس باید دادهٔ
سال هدف از سند رسمی همان سال در بخش «منابع» ثبت شود.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogSource:
    title: str
    url: str
    publisher: str
    inspected_on: str
    verification: str
    note: str


SOURCE_SANJESH_1405 = CatalogSource(
    title="فهرست دروس و کتاب‌های منبع آزمون سراسری ۱۴۰۵",
    url=(
        "https://www.yjc.ir/fa/news/9004576/"
        "%D9%81%D9%87%D8%B1%D8%B3%D8%AA-%D8%AF%D8%B1%D9%88%D8%B3-%D9%88-"
        "%DA%A9%D8%AA%D8%A7%D8%A8%E2%80%8C%D9%87%D8%A7%DB%8C-%D9%85%D9%86%D8%A8%D8%B9-"
        "%D8%B3%D8%A4%D8%A7%D9%84%D8%A7%D8%AA-%D8%A2%D8%B2%D9%85%D9%88%D9%86-"
        "%D8%B3%D8%B1%D8%A7%D8%B3%D8%B1%DB%8C-%D8%B3%D8%A7%D9%84-%DB%B1%DB%B4%DB%B0%DB%B5-"
        "%D9%85%D9%86%D8%AA%D8%B4%D8%B1-%D8%B4%D8%AF"
    ),
    publisher="اطلاعیهٔ سازمان سنجش؛ گزارش بازنشرشده توسط باشگاه خبرنگاران جوان",
    inspected_on="2026-10-17",
    verification="reported_official_primary_pdf_not_directly_verified",
    note=(
        "این منبع گزارش می‌کند فهرست دروس/کتاب‌های ۱۴۰۵ در سنجش منتشر شده؛ "
        "فایل اصلی سنجش در بررسی حاضر مستقیماً دریافت/بازخوانی نشد. بنابراین "
        "این فهرست برای پیشنهاد اولیه است، نه مبنای ضریب یا ادعای رسمی قطعی."
    ),
)

SOURCE_TEXTBOOKS = CatalogSource(
    title="پایگاه رسمی کتاب‌های درسی، اداره کل نظارت بر نشر و توزیع مواد آموزشی",
    url="https://chap.sch.ir/",
    publisher="وزارت آموزش و پرورش",
    inspected_on="2026-10-17",
    verification="official_catalog_source",
    note=(
        "برای ثبت عنوان/کد/پایه و ویرایش کتاب، صفحهٔ همان کتاب باید به‌صورت "
        "مستقل بازبینی شود."
    ),
)

# عناوین کمینه برای شروع. هر عنوان صرفاً انتخاب‌پذیر است؛ ضرایب و تطبیق
# سالانه عمداً خالی‌اند تا بدون سند رسمی در برنامه‌ریزی اثر نگذارند.
SUBJECTS_BY_GROUP: dict[str, tuple[str, ...]] = {
    "علوم تجربی": (
        "زیست‌شناسی", "شیمی", "فیزیک", "ریاضی", "زمین‌شناسی",
    ),
    "علوم ریاضی و فنی": (
        "ریاضیات", "فیزیک", "شیمی",
    ),
    "علوم انسانی": (
        "ریاضی و آمار", "اقتصاد", "علوم و فنون ادبی", "عربی تخصصی",
        "تاریخ", "جغرافیا", "علوم اجتماعی", "فلسفه و منطق", "روان‌شناسی",
    ),
}

GROUPS = tuple(SUBJECTS_BY_GROUP)
EXAM_YEAR_OPTIONS = ("۱۴۰۵", "۱۴۰۶", "سال دیگر / هنوز مشخص نیست")


def source_status_for_year(year: int | None) -> str:
    """وضعیت بستهٔ منبع برای سال انتخابی، بدون تعمیم سال قبل به سال جدید."""
    if year == 1405:
        return SOURCE_SANJESH_1405.verification
    if year == 1406:
        return "official_1406_dataset_not_loaded"
    return "year_not_set"
