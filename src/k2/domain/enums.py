"""枚举‌های دامنهٔ محصول.

هر enum یک مقدار متنی پایدار (مقدار ذخیره‌شده در پایگاه داده) دارد تا
مهاجرت‌های بعدی شکننده نباشند.
"""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """پایهٔ enum متنی با ``str``/``label`` خوانا."""

    def __new__(cls, value: str, label: str = ""):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj._label_ = label or value
        return obj

    @property
    def label(self) -> str:
        return getattr(self, "_label_", self.value)


class ActivityState(StrEnum):
    """ماشین حالت فعالیت (سند تحقیق ۲، بخش ۵)."""

    PLANNED = ("planned", "برنامه‌ریزی‌شده")
    READY = ("ready", "آماده")
    BLOCKED = ("blocked", "مسدود")
    IN_PROGRESS = ("in_progress", "در حال انجام")
    PARTIAL = ("partial", "ناقص")
    DONE = ("done", "انجام‌شده")
    OVERDUE = ("overdue", "عقب‌افتاده")
    DEFERRED = ("deferred", "به تعویق افتاده")
    EXPIRED = ("expired", "منقضی")
    DROPPED = ("dropped", "حذف‌شده")


class ActivityType(StrEnum):
    """انواع فعالیت (سند تحقیق ۲، بخش ۴)."""

    RECORDED_CLASS = ("recorded_class", "کلاس ضبط‌شده")
    LIVE_CLASS = ("live_class", "کلاس حضوری/آنلاین")
    HOMEWORK = ("homework", "تکلیف")
    PROCESSING = ("processing", "پردازش اولیه")
    GUIDED_EXAMPLE = ("guided_example", "مثال هدایت‌شده")
    INDEPENDENT_PRACTICE = ("independent_practice", "تمرین مستقل")
    MIXED_PRACTICE = ("mixed_practice", "تمرین درهم‌آمیخته")
    TIMED_TEST = ("timed_test", "تست زمان‌دار")
    TEST_ANALYSIS = ("test_analysis", "تحلیل تست")
    CONSOLIDATION = ("consolidation", "تثبیت")
    REMEDIATION = ("remediation", "رفع اشکال")
    REWORK = ("rework", "حل مجدد")
    REVIEW = ("review", "مرور سررسید")
    EXAM = ("exam", "آزمون")
    SUMMARY = ("summary", "جمع‌بندی")


class DeadlineType(StrEnum):
    HARD = ("hard", "سخت")
    SOFT = ("soft", "نرم")
    NONE = ("none", "بدون مهلت")


class EnergyNeed(StrEnum):
    HIGH = ("high", "زیاد")
    MEDIUM = ("medium", "متوسط")
    LOW = ("low", "کم")


class ContentType(StrEnum):
    """نوع محتوای مبحث؛ راهبرد یادگیری از این می‌آید نه از سبک یادگیری."""

    MEMORIZATION = ("memorization", "حفظی")
    CONCEPTUAL = ("conceptual", "مفهومی")
    CALCULATIONAL = ("calculational", "محاسباتی")
    TEXTUAL = ("textual", "متنی")
    VOCABULARY = ("vocabulary", "واژگانی")
    DIAGRAM = ("diagram", "نموداری/شکلی")
    PRACTICAL = ("practical", "عملی/مهارتی")


class ErrorCode(StrEnum):
    """طبقه‌بندی علت خطا (سند تحقیق ۱، بخش ۴.۲)."""

    E1 = ("E1", "ضعف مفهومی")
    E2 = ("E2", "فراموشی")
    E3 = ("E3", "ضعف روش حل")
    E4 = ("E4", "خطای محاسباتی")
    E5 = ("E5", "بی‌دقتی")
    E6 = ("E6", "کمبود زمان")
    E7 = ("E7", "برداشت اشتباه از سؤال")
    E8 = ("E8", "حدس")
    E9 = ("E9", "ناتوانی در تشخیص تیپ")


class MasteryLevel(int, Enum):
    """سطح تسلط مبحث (L0..L4) — سند تحقیق ۴، بخش ۱.۲."""

    L0 = 0
    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4

    @property
    def label(self) -> str:
        return {
            0: "L0 — ندیده",
            1: "L1 — مبتدی",
            2: "L2 — متوسط",
            3: "L3 — خوب",
            4: "L4 — مسلط",
        }[self.value]


class ReviewState(StrEnum):
    """حالت یک آیتم مرور (سند تحقیق ۱، بخش ۳.۲)."""

    NEW = ("new", "جدید")
    LEARNING = ("learning", "در حال یادگیری")
    REVIEW = ("review", "مرور")
    RELEARN = ("relearn", "یادگیری مجدد")
    LEECH = ("leech", "تکراری — نیازمند تغییر روش")
    MAINTENANCE = ("maintenance", "نگهداری")


class FixedEventKind(StrEnum):
    LIVE_CLASS = ("live_class", "کلاس حضوری")
    ONLINE_CLASS = ("online_class", "کلاس آنلاین زنده")
    RECORDED_CLASS = ("recorded_class", "کلاس ضبط‌شده")
    EXAM = ("exam", "آزمون")
    COMMITMENT = ("commitment", "تعهد شخصی")


class RoutineKind(StrEnum):
    """بازه‌های ضروری روزانه (سند تحقیق ۲، بخش ۲)."""

    SLEEP = ("sleep", "خواب")
    MEAL = ("meal", "غذا")
    REST = ("rest", "استراحت")
    HYGIENE = ("hygiene", "بهداشت/حمام")
    COMMUTE = ("commute", "رفت‌وآمد")
    OTHER = ("other", "سایر")


class ExamKind(StrEnum):
    OFFICIAL = ("official", "رسمی")
    MOCK = ("mock", "شبیه‌سازی")
    INSTITUTE = ("institute", "مؤسسه")
    DIAGNOSTIC = ("diagnostic", "تشخیصی")


class ScopeStatus(StrEnum):
    """وضعیت بودجه‌بندی مبحث (سند بخش ۳، بند ۳)."""

    IN_SCOPE = ("in_scope", "در بودجه")
    OUT_OF_SCOPE = ("out_of_scope", "خارج از بودجه")
    UNKNOWN = ("unknown", "نامشخص")
    CHANGED_PENDING = ("changed_pending", "تغییری — نیازمند تأیید")


class DateStatus(StrEnum):
    """وضعیت رسمی‌بودن تاریخ آزمون (سند تحقیق ۳، بخش ۱)."""

    OFFICIAL = ("official", "رسمی (منبع ثبت‌شده)")
    ESTIMATED = ("estimated", "تخمینی")
    UNKNOWN = ("unknown", "نامشخص")


class StudyPhase(StrEnum):
    """فازهای زمانی (سند تحقیق ۴، بخش ۱.۴) — مرزها تنظیمی‌اند."""

    FOUNDATION = ("foundation", "بنیان")
    CONSOLIDATION = ("consolidation", "تثبیت")
    INTENSIFICATION = ("intensification", "تشدید")
    SUMMARIZATION = ("summarization", "جمع‌بندی")
    FINAL_DAYS = ("final_days", "روزهای آخر")
    UNKNOWN = ("unknown", "نامشخص")


class Bottleneck(StrEnum):
    """گلوگاه آموزشی (سند تحقیق ۴، بخش ۱.۳) — غیرپزشکی."""

    KNOWLEDGE = ("knowledge", "دانش/مفهوم")
    METHOD = ("method", "روش حل/تیپ")
    SPEED = ("speed", "سرعت")
    ACCURACY = ("accuracy", "دقت")
    RETENTION = ("retention", "ماندگاری")
    EXECUTION = ("execution", "مدیریت زمان/اجرا")
    PRESSURE = ("pressure", "فشار خودگزارشی")
    NONE = ("none", "گلوگاه مشخصی دیده نشد")


class DebtLevel(StrEnum):
    GREEN = ("green", "سبز")
    YELLOW = ("yellow", "زرد")
    ORANGE = ("orange", "نارنجی")
    RED = ("red", "قرمز")


class RoutineScope(StrEnum):
    """یک‌روزدرمیان یا روزانه."""

    DAILY = ("daily", "روزانه")
    ALTERNATE = ("alternate", "یک‌روزدرمیان")
