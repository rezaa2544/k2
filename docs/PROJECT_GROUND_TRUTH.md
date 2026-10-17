# حقیقت زمینهٔ پروژه — K2

تاریخ ثبت: ۱۴۰۵/۰۷/۲۴ (2026-10-17)
این سند پیش از هر تغییر کد نوشته شد و وضعیت واقعی محیط و محدودیت‌ها را ثبت می‌کند.

---

## ۱. ماهیت پروژه

* نام: **K2 — مشاور هوشمند کنکور**
* نوع: نرم‌افزار دسکتاپ فارسی، راست‌چین، آفلاین‌محور برای دانش‌آموزان کنکور.
* **پروژهٔ کاملاً جدید.** هیچ کد، مدل داده یا نیازمندی از پروژهٔ قبلی (Payesh) وام گرفته نشده است. تاریخچهٔ مخزن فقط شامل K2 است.
* بستهٔ تحقیق (۴ سند اصلی + اسناد تجمیعی) **منجمد و مرجع** است؛ پژوهش از نو انجام نشد.

---

## ۲. وضعیت محیط هنگام شروع

| مؤلفه | مقدار |
|---|---|
| سیستم‌عامل | Debian GNU/Linux 13 (kernel 6.1.158)، x86_64 |
| CPU / حافظه | ۲ هسته / ۲۱ گیگابایت آزاد |
| پایتون | ۳.۱۳.۱۶ در `/usr/local/bin/python3` |
| pip | PyPI در دسترس (PySide6، jdatetime، PyInstaller نصب شدند) |
| git | ۲.۴۷.۳، بدون اعتبارنامهٔ GitHub |
| gh CLI | وجود ندارد |
| Wine | در ابتدا نبود؛ بعداً `wine64 10.0` نصب شد (`/usr/lib/wine/wine64`) با `sudo` بدون رمز |
| Xvfb | بعداً نصب شد برای بررسی اجرای گرافیکی |

### ابزارهای بررسی‌شده و نتیجه

| ابزار | نتیجه |
|---|---|
| `list_connector_tools service=github` | `{"status": "unsupported"}` — اتصال GitHub در Arena وجود ندارد |
| `https://api.github.com/repos/rezaa2544/k2` | HTTP ۴۰۴ |
| `https://github.com/rezaa2544/k2` | HTTP ۴۰۴ |
| `https://github.com` | HTTP ۲۰۰ — شبکه کار می‌کند، فقط احراز هویت نیست |
| جست‌وجوی توکن/کلید SSH/netrc/credential helper | هیچ‌کدام یافت نشد |

**نتیجهٔ قطعی:** ساخت مخزن و push در این محیط **غیرممکن** است. این کار به کاربر واگذار شده و دستورهای دقیق آن در `KNOWN_LIMITATIONS.md` آمده است. هیچ ادعایی دربارهٔ ساخت یا push مخزن، بدون مدرک، مطرح نشده است.

---

## ۳. محدودیت‌های کلیدی بسته‌بندی که در ابتدا شناسایی شدند

1. **PyInstaller روی لینوکس نمی‌تواند EXE ویندوز بسازد.** راه‌حل: `k2.spec` + `build_windows.ps1` + گردش‌کار `windows-latest`. در نهایت، با Wine + پایتون ویندوزی، EXE واقعی ساخته و **اجرا** شد.
2. **نصب‌کنندهٔ رسمی پایتون ویندوز ۳۲بیتی است** و زیر `wine64` اجرا نمی‌شود (`syswow64/ntdll.dll` پیدا نشد). راه‌حل: بستهٔ nuget پایتون ۶۴بیتی.
3. **PySide6 6.12.0 ویندوز به `icuuc.dll` سیستمی نیاز دارد** که Wine عرضه نمی‌کند. با بررسی مستقیم جدول ایمپورت چرخاب‌ها ثابت شد و نسخه به ۶.۹.۱ تغییر کرد.
4. **«build موفق» کافی نیست.** اولین build موفق بود ولی EXE هنگام اجرا به‌علت ایمپورت نسبی در `__main__.py` و سپس کدگذاری `cp1252` کنسول شکست خورد. هر دو با اجرای واقعی کشف و رفع شدند (D-013، D-014، D-020).

---

## ۴. دامنهٔ تغییر

**در محدوده:** پروژهٔ جدید در مسیر `/home/user/k2/` شامل سورس، تست، مستندات، بسته‌بندی و گردش‌کار.

**خارج از محدوده (دست‌نخورده):** هر پروژه یا مخزن دیگری؛ تنظیمات سیستم کاربر؛ هر مخزن GitHub موجود.

**قاعدهٔ ایمنی:** اگر `rezaa2544/k2` در آینده موجود بود و محتوای متفاوتی داشت، **نباید حذف یا بازنویسی شود** — فقط گزارش داده شود.

---

## ۵. فهرست فایل‌های منبع اولیه (خوانده‌شده کامل)

```
uploads/ARENA_KICKOFF_PROMPT_K2.md.txt
uploads/MASTER_EXECUTION_PROMPT.md
uploads/MASTER_PRODUCT_BLUEPRINT.md
uploads/UNIFIED_REQUIREMENTS_CATALOG.md
uploads/01_EVIDENCE_LEARNING_EXAM_ANALYSIS.md
uploads/02_PLANNING_ENGINE_AND_BACKLOG.md
uploads/03_KONKUR_CONTEXT_AND_TOOL_ANALYSIS.md
uploads/04_ADVISOR_ENGINE_SRS_AND_ROADMAP.md
uploads/IMPLEMENTATION_ROADMAP_AND_TEST_GATES.md
uploads/RESEARCH_DECISIONS_AND_EVIDENCE.md
uploads/SECTION_3_IMPLEMENTATION_PLAN.md
uploads/USER_SCHEDULE_AND_ONBOARDING.md
uploads/README.md
uploads/REPOSITORY_DOCUMENTATION_STATUS.md
```

انواع: ۱۴ فایل، ۱٬۷۴۶ خط. همه خوانده شدند.

---

## ۶. تصمیم‌های ثبت‌شده

گاه‌نامهٔ کامل در [DECISION_LOG.md](DECISION_LOG.md) با ۲۱ تصمیم (D-001 تا D-021).

---

## ۷. وضعیت فعلی (به‌روزرسانی پس از پیاده‌سازی)

* ۱۷۰ تست، همه پاس.
* EXE ویندوز ۶۴بیتی ساخته و در دو حالت headless و گرافیکی اجرا شد.
* ۱۱ سند در `docs/` + README فارسی.
* مخزن محلی با ۱۱ commit؛ **بدون remote و بدون push** (به‌دلیل نبود اعتبارنامه).

