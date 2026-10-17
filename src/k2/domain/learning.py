"""قواعد یادگیری: نگاشت درس به روش، ماتریس تجویز و اقدام اصلاحی خطا.

منابع: سند تحقیق ۱ (بخش ۴.۲ و ۵)، سند تحقیق ۴ (بخش ۱.۵ و ۱.۶).

قاعدهٔ کلیدی: **راهبرد از نوع محتوا می‌آید، نه از نام درس** و هرگز از
«سبک یادگیری» دیداری/شنیداری (سند تحقیق ۱، اصل ۱۰).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import (
    ActivityType,
    ContentType,
    ErrorCode,
    MasteryLevel,
    StudyPhase,
)


@dataclass(frozen=True)
class LearningActivityTemplate:
    """الگوی فعالیت پیشنهادی برای یک خانهٔ ماتریس تجویز."""

    activity_type: ActivityType
    title_template: str
    default_minutes: int
    completion_criteria: str
    energy: str = "medium"


# ---------------------------------------------------------------------------
# نگاشت درس → نوع محتوا (قابل ویرایش در تنظیمات؛ این فقط پیش‌فرض است)
# ---------------------------------------------------------------------------

#: نگاشت پیش‌فرض نام درس به نوع محتوا و راهبرد پایه.
#: کلید نرمال‌شدهٔ نام درس است. کاربر می‌تواند در تنظیمات آن را بازنویسی کند.
DEFAULT_SUBJECT_CONTENT_TYPES: dict[str, ContentType] = {
    "ریاضی": ContentType.CALCULATIONAL,
    "ریاضیات": ContentType.CALCULATIONAL,
    "فیزیک": ContentType.CALCULATIONAL,
    "شیمی": ContentType.CALCULATIONAL,
    "زیست": ContentType.MEMORIZATION,
    "زیست‌شناسی": ContentType.MEMORIZATION,
    "زمین‌شناسی": ContentType.CONCEPTUAL,
    "دینی": ContentType.MEMORIZATION,
    "ادبیات": ContentType.TEXTUAL,
    "عربی": ContentType.TEXTUAL,
    "زبان": ContentType.VOCABULARY,
    "انگلیسی": ContentType.VOCABULARY,
    "فارسی": ContentType.TEXTUAL,
    "هویت اجتماعی": ContentType.MEMORIZATION,
    "تاریخ": ContentType.MEMORIZATION,
    "جغرافیا": ContentType.CONCEPTUAL,
    "اقتصاد": ContentType.CALCULATIONAL,
    "فلسفه": ContentType.CONCEPTUAL,
    "روان‌شناسی": ContentType.CONCEPTUAL,
}

#: روش‌های آموزشی پیشنهادی برای هر نوع محتوا (SUB-01).
#: ترتیب = ترتیب توصیه. هر روش به شواهد سند تحقیق ۱ ارجاع دارد.
CONTENT_TYPE_METHODS: dict[ContentType, tuple[str, ...]] = {
    ContentType.MEMORIZATION: (
        "بازیابی فعال بدون نگاه کردن به منبع",
        "پرسش‌سازی از خودت (سؤال بساز، پاسخ بده)",
        "مرور فاصله‌دار تطبیقی",
        "کدگذاری دوگانهٔ متن و شکل",
    ),
    ContentType.CONCEPTUAL: (
        "توضیح با زبان خودت",
        "مثال و ضد مثال",
        "نقشهٔ مفهومی و ارتباط علت و معلول",
        "پرسش «چرا؟»",
    ),
    ContentType.CALCULATIONAL: (
        "مثال حل‌شده کامل",
        "مثال نیمه‌کامل (کاهش تدریجی راهنما)",
        "حل مستقل هم‌تیپ",
        "سؤال انتقالی/ترکیبی",
        "تست زمان‌دار پس از یادگیری اولیه",
    ),
    ContentType.TEXTUAL: (
        "تحلیل متن و نقش اجزا",
        "قاعده همراه با مثال",
        "واژگان با مرور فاصله‌دار",
        "بازیابی گزاره‌ای از متن",
    ),
    ContentType.VOCABULARY: (
        "فلش‌کارت به‌عنوان ابزار بازیابی",
        "بازیابی فعال در هر دو جهت (فارسی→زبان و برعکس)",
        "کاربرد در جمله",
        "مرور فاصله‌دار",
    ),
    ContentType.DIAGRAM: (
        "برچسب‌گذاری شکل از حافظه",
        "توصیف نمودار با زبان خودت",
        "تمرین تفسیر داده",
    ),
}


def subject_default_content_type(subject_name: str) -> ContentType:
    """نوع محتوای پیش‌فرض یک درس.

    اگر درس ناشناخته باشد، «مفهومی» انتخاب می‌شود که خنثی‌ترین گزینه است.
    """
    key = subject_name.strip()
    if key in DEFAULT_SUBJECT_CONTENT_TYPES:
        return DEFAULT_SUBJECT_CONTENT_TYPES[key]
    for name, content_type in DEFAULT_SUBJECT_CONTENT_TYPES.items():
        if name in key or key in name:
            return content_type
    return ContentType.CONCEPTUAL


def recommended_methods(content_type: ContentType) -> tuple[str, ...]:
    """روش‌های آموزشی پیشنهادی برای یک نوع محتوا."""
    return CONTENT_TYPE_METHODS.get(content_type, CONTENT_TYPE_METHODS[ContentType.CONCEPTUAL])


# ---------------------------------------------------------------------------
# ماتریس تجویز: فاز × سطح (سند تحقیق ۴، بخش ۱.۵)
# ---------------------------------------------------------------------------

#: کلید ماتریس: (فاز، سطح) → tuple قالب‌های فعالیت.
#: مقادیر فرضیهٔ محصول [H] و قابل تنظیم‌اند.
PRESCRIPTION_MATRIX: dict[tuple[StudyPhase, MasteryLevel], tuple[LearningActivityTemplate, ...]] = {
    (StudyPhase.FOUNDATION, MasteryLevel.L0): (
        LearningActivityTemplate(
            ActivityType.PROCESSING, "یادگیری اولیه {topic}", 45,
            "جلسهٔ کامل دیده شود و دست‌کم ۳ نقطهٔ ابهام ثبت شود", "high",
        ),
        LearningActivityTemplate(
            ActivityType.GUIDED_EXAMPLE, "مثال حل‌شده {topic}", 40,
            "مراحل حل بدون نگاه بازگو شود", "high",
        ),
        LearningActivityTemplate(
            ActivityType.INDEPENDENT_PRACTICE, "تمرین بلوکی {topic}", 30,
            "حداقل ۸۰٪ پاسخ درست یا فهم همهٔ مراحل", "medium",
        ),
    ),
    (StudyPhase.FOUNDATION, MasteryLevel.L1): (
        LearningActivityTemplate(
            ActivityType.GUIDED_EXAMPLE, "مثال حل‌شده {topic}", 40,
            "مراحل حل بدون نگاه بازگو شود", "high",
        ),
        LearningActivityTemplate(
            ActivityType.INDEPENDENT_PRACTICE, "تمرین مستقل هم‌تیپ {topic}", 35,
            "حداقل ۷۵٪ پاسخ درست", "medium",
        ),
        LearningActivityTemplate(
            ActivityType.REVIEW, "مرور {topic}", 15,
            "بازیابی موفق بدون نگاه", "low",
        ),
    ),
    (StudyPhase.FOUNDATION, MasteryLevel.L2): (
        LearningActivityTemplate(
            ActivityType.PROCESSING, "جمع‌بندی آموزشی {topic}", 25,
            "نقاط مبهم جلسهٔ قبل بسته شود", "medium",
        ),
        LearningActivityTemplate(
            ActivityType.INDEPENDENT_PRACTICE, "تمرین هدایت‌شده {topic}", 35,
            "حداقل ۷۵٪ پاسخ درست", "medium",
        ),
        LearningActivityTemplate(
            ActivityType.TIMED_TEST, "تست زمان‌دار {topic}", 25,
            "زمان ≤ ۱٫۲ برابر هدف و دقت ≥ آستانه", "medium",
        ),
    ),
    (StudyPhase.FOUNDATION, MasteryLevel.L3): (
        LearningActivityTemplate(
            ActivityType.INDEPENDENT_PRACTICE, "تمرین مستقل {topic}", 30,
            "دقت ≥ ۸۰٪", "medium",
        ),
        LearningActivityTemplate(
            ActivityType.TIMED_TEST, "تست زمان‌دار {topic}", 25,
            "زمان ≤ ۱٫۲ برابر هدف", "medium",
        ),
        LearningActivityTemplate(
            ActivityType.REVIEW, "مرور {topic}", 15,
            "بازیابی موفق", "low",
        ),
    ),
    (StudyPhase.FOUNDATION, MasteryLevel.L4): (
        LearningActivityTemplate(
            ActivityType.MIXED_PRACTICE, "تست سطح بالا {topic}", 25,
            "دقت ≥ ۹۰٪", "medium",
        ),
        LearningActivityTemplate(
            ActivityType.REVIEW, "نگهداری {topic}", 15,
            "بازیابی موفق", "low",
        ),
    ),
    (StudyPhase.CONSOLIDATION, MasteryLevel.L0): (
        LearningActivityTemplate(
            ActivityType.REMEDIATION, "بازآموزی {topic}", 45,
            "مثال حل‌شده و تمرین هدایت‌شده تکمیل شود", "high",
        ),
        LearningActivityTemplate(
            ActivityType.REVIEW, "مرور کوتاه {topic}", 15,
            "بازیابی موفق", "low",
        ),
    ),
    (StudyPhase.CONSOLIDATION, MasteryLevel.L1): (
        LearningActivityTemplate(
            ActivityType.REMEDIATION, "بازآموزی {topic}", 40,
            "نقص اصلی جبران شود", "high",
        ),
        LearningActivityTemplate(
            ActivityType.REVIEW, "مرور فاصله‌دار {topic}", 20,
            "بازیابی موفق", "low",
        ),
    ),
    (StudyPhase.CONSOLIDATION, MasteryLevel.L2): (
        LearningActivityTemplate(
            ActivityType.MIXED_PRACTICE, "تمرین مخلوط {topic}", 30,
            "دقت ≥ ۸۰٪", "medium",
        ),
        LearningActivityTemplate(
            ActivityType.TEST_ANALYSIS, "تحلیل خطا {topic}", 25,
            "همهٔ اشتباهات برچسب خورده باشند", "medium",
        ),
        LearningActivityTemplate(
            ActivityType.REVIEW, "مرور {topic}", 15,
            "بازیابی موفق", "low",
        ),
    ),
    (StudyPhase.CONSOLIDATION, MasteryLevel.L3): (
        LearningActivityTemplate(
            ActivityType.MIXED_PRACTICE, "تمرین مخلوط زمان‌دار {topic}", 35,
            "دقت ≥ ۸۰٪ در زمان هدف", "medium",
        ),
        LearningActivityTemplate(
            ActivityType.REVIEW, "مرور {topic}", 15,
            "بازیابی موفق", "low",
        ),
    ),
    (StudyPhase.CONSOLIDATION, MasteryLevel.L4): (
        LearningActivityTemplate(
            ActivityType.MIXED_PRACTICE, "سؤال‌های ترکیبی {topic}", 30,
            "دقت ≥ ۹۰٪", "medium",
        ),
        LearningActivityTemplate(
            ActivityType.REVIEW, "نگهداری {topic}", 15,
            "بازیابی موفق", "low",
        ),
    ),
    (StudyPhase.INTENSIFICATION, MasteryLevel.L0): (
        LearningActivityTemplate(
            ActivityType.REMEDIATION, "هستهٔ مفاهیم {topic}", 30,
            "مفاهیم پایه بسته شود", "high",
        ),
    ),
    (StudyPhase.INTENSIFICATION, MasteryLevel.L1): (
        LearningActivityTemplate(
            ActivityType.REMEDIATION, "رفع ضعف {topic}", 35,
            "خطای E1 کاهش یابد", "high",
        ),
        LearningActivityTemplate(
            ActivityType.TIMED_TEST, "تست زمان‌دار {topic}", 25,
            "دقت ≥ ۷۰٪ در زمان هدف", "medium",
        ),
    ),
    (StudyPhase.INTENSIFICATION, MasteryLevel.L2): (
        LearningActivityTemplate(
            ActivityType.REMEDIATION, "رفع نقطهٔ ضعف {topic}", 30,
            "نرخ خطای تکراری کاهش یابد", "medium",
        ),
        LearningActivityTemplate(
            ActivityType.TIMED_TEST, "تست زمان‌دار {topic}", 25,
            "دقت ≥ ۷۵٪ در زمان هدف", "medium",
        ),
    ),
    (StudyPhase.INTENSIFICATION, MasteryLevel.L3): (
        LearningActivityTemplate(
            ActivityType.TIMED_TEST, "آزمون جامع موضوعی {topic}", 45,
            "دقت ≥ ۸۰٪", "high",
        ),
        LearningActivityTemplate(
            ActivityType.REVIEW, "مرور گسترده {topic}", 20,
            "بازیابی موفق", "low",
        ),
    ),
    (StudyPhase.INTENSIFICATION, MasteryLevel.L4): (
        LearningActivityTemplate(
            ActivityType.TIMED_TEST, "آزمون جامع {topic}", 45,
            "دقت ≥ ۹۰٪", "high",
        ),
        LearningActivityTemplate(
            ActivityType.REVIEW, "نگهداری {topic}", 15,
            "بازیابی موفق", "low",
        ),
    ),
    (StudyPhase.SUMMARIZATION, MasteryLevel.L0): (
        LearningActivityTemplate(
            ActivityType.REMEDIATION, "فهرست خطاهای حیاتی {topic}", 30,
            "فهرست آماده شود", "medium",
        ),
    ),
    (StudyPhase.SUMMARIZATION, MasteryLevel.L1): (
        LearningActivityTemplate(
            ActivityType.REMEDIATION, "فهرست خطاهای حیاتی {topic}", 30,
            "فهرست آماده شود", "medium",
        ),
        LearningActivityTemplate(
            ActivityType.REVIEW, "مرور سبک {topic}", 15,
            "بازیابی موفق", "low",
        ),
    ),
    (StudyPhase.SUMMARIZATION, MasteryLevel.L2): (
        LearningActivityTemplate(
            ActivityType.REWORK, "بانک خطا {topic}", 30,
            "خطاهای ثبت‌شده مرور شوند", "medium",
        ),
        LearningActivityTemplate(
            ActivityType.REVIEW, "مرور {topic}", 15,
            "بازیابی موفق", "low",
        ),
    ),
    (StudyPhase.SUMMARIZATION, MasteryLevel.L3): (
        LearningActivityTemplate(
            ActivityType.REWORK, "بانک خطا {topic}", 30,
            "خطاهای ثبت‌شده مرور شوند", "medium",
        ),
        LearningActivityTemplate(
            ActivityType.TIMED_TEST, "نمونهٔ آزمون {topic}", 40,
            "دقت ≥ ۸۰٪", "high",
        ),
    ),
    (StudyPhase.SUMMARIZATION, MasteryLevel.L4): (
        LearningActivityTemplate(
            ActivityType.REVIEW, "مرور سبک {topic}", 15,
            "بازیابی موفق", "low",
        ),
    ),
    (StudyPhase.FINAL_DAYS, MasteryLevel.L0): (
        LearningActivityTemplate(
            ActivityType.REVIEW, "مرور خیلی سبک {topic}", 10,
            "بازیابی موفق", "low",
        ),
    ),
    (StudyPhase.FINAL_DAYS, MasteryLevel.L1): (
        LearningActivityTemplate(
            ActivityType.REVIEW, "مرور خیلی سبک {topic}", 10,
            "بازیابی موفق", "low",
        ),
    ),
    (StudyPhase.FINAL_DAYS, MasteryLevel.L2): (
        LearningActivityTemplate(
            ActivityType.REVIEW, "مرور سبک {topic}", 10,
            "بازیابی موفق", "low",
        ),
    ),
    (StudyPhase.FINAL_DAYS, MasteryLevel.L3): (
        LearningActivityTemplate(
            ActivityType.REVIEW, "مرور سبک {topic}", 10,
            "بازیابی موفق", "low",
        ),
    ),
    (StudyPhase.FINAL_DAYS, MasteryLevel.L4): (
        LearningActivityTemplate(
            ActivityType.REVIEW, "مرور سبک {topic}", 10,
            "بازیابی موفق", "low",
        ),
    ),
}


def prescription_matrix(
    phase: StudyPhase, level: MasteryLevel
) -> tuple[LearningActivityTemplate, ...]:
    """الگوهای فعالیت برای یک خانهٔ ماتریس (فاز × سطح)."""
    key = (phase, level)
    if key in PRESCRIPTION_MATRIX:
        return PRESCRIPTION_MATRIX[key]
    # جایگزین نزدیک: همان سطح در فاز «بنیان».
    fallback = (StudyPhase.FOUNDATION, level)
    return PRESCRIPTION_MATRIX.get(fallback, ())


# ---------------------------------------------------------------------------
# اقدام اصلاحی برای هر کد خطا (سند تحقیق ۱، بخش ۴.۲)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ErrorRemediation:
    """اقدام اصلاحی متناظر یک کد خطا."""

    code: ErrorCode
    activity_type: ActivityType
    title_template: str
    default_minutes: int
    deadline_hours: int
    retest_description: str
    explanation: str


ERROR_REMEDIATIONS: dict[ErrorCode, ErrorRemediation] = {
    ErrorCode.E1: ErrorRemediation(
        ErrorCode.E1, ActivityType.REMEDIATION, "بازآموزی {topic}", 45, 48,
        "سؤال مشابه تا ۴۸ ساعت",
        "پس از دیدن پاسخ هم مفهوم را نمی‌فهمید؛ نیاز به بازآموزی و مثال حل‌شده است.",
    ),
    ErrorCode.E2: ErrorRemediation(
        ErrorCode.E2, ActivityType.REVIEW, "ورود به صف مرور {topic}", 15, 72,
        "بازیابی در ۱ تا ۳ روز",
        "پس از دیدن پاسخ یادش آمد؛ مسئلهٔ ماندگاری است نه فهم.",
    ),
    ErrorCode.E3: ErrorRemediation(
        ErrorCode.E3, ActivityType.GUIDED_EXAMPLE, "مثال نیمه‌کامل {topic}", 35, 72,
        "۳ سؤال هم‌تیپ",
        "مفهوم را می‌داند اما راه‌حل را شروع نمی‌کند؛ مسئلهٔ روش است.",
    ),
    ErrorCode.E4: ErrorRemediation(
        ErrorCode.E4, ActivityType.INDEPENDENT_PRACTICE, "تمرین محاسباتی دقیق {topic}", 25, 72,
        "تمرین زمان‌دار کوتاه",
        "روش درست بود و عدد اشتباه شد؛ مسئلهٔ دقت محاسبه است.",
    ),
    ErrorCode.E5: ErrorRemediation(
        ErrorCode.E5, ActivityType.INDEPENDENT_PRACTICE, "تمرین کند و دقیق {topic}", 25, 96,
        "رصد روند خطا",
        "سؤال بدخوانده یا گزینه اشتباه علامت شده؛ مسئلهٔ دقت خواندن است.",
    ),
    ErrorCode.E6: ErrorRemediation(
        ErrorCode.E6, ActivityType.TIMED_TEST, "تست زمان‌دار {topic}", 30, 72,
        "شبیه‌سازی آزمون",
        "سؤال‌های انتهایی نزده شدند؛ مسئلهٔ مدیریت زمان است.",
    ),
    ErrorCode.E7: ErrorRemediation(
        ErrorCode.E7, ActivityType.MIXED_PRACTICE, "تحلیل متن سؤال {topic}", 30, 72,
        "سؤال بازنویسی‌شده",
        "صورت سؤال بد فهمیده شده؛ مسئلهٔ تفسیر خواستهٔ سؤال است.",
    ),
    ErrorCode.E8: ErrorRemediation(
        ErrorCode.E8, ActivityType.REVIEW, "مرور بدون گزینه {topic}", 15, 72,
        "بازیابی بدون گزینه",
        "پاسخ حدسی بوده؛ به مرور با اطمینان پایین تبدیل می‌شود.",
    ),
    ErrorCode.E9: ErrorRemediation(
        ErrorCode.E9, ActivityType.MIXED_PRACTICE, "تشخیص تیپ سؤال {topic}", 30, 96,
        "طبقه‌بندی سؤال‌های جدید",
        "نمی‌داند سؤال از چه نوعی است؛ جدول تیپ‌ها لازم است.",
    ),
}


def remediation_for(code: ErrorCode) -> ErrorRemediation:
    """اقدام اصلاحی متناظر یک کد خطا."""
    return ERROR_REMEDIATIONS[code]
