# وضعیت پروژه — K2

تاریخ گزارش: ۱۴۰۵/۰۷/۲۴ (2026-10-17)
شاخه: `main` — مخزن محلی: `/home/user/k2`

---

## ۱. خلاصهٔ اجرایی

پیاده‌سازی دامنه، موتورهای تصمیم‌گیری و ذخیره‌سازی کامل شده است. منوهای «برنامه» و «راهنما» با استایل خوانا و میانبرهای صفحه‌کلید به‌روزرسانی شده‌اند؛ **۱۷۴ تست** در محیط لینوکس پاس شده و گردش‌کار Windows نیز در [GitHub Actions](https://github.com/rezaa2544/k2/actions/runs/39051925261) تست‌ها، ساخت PyInstaller و اجرای headless EXE را با موفقیت گذرانده است. ZIP کامل one-folder شامل `_internal` و checksum تازه در مخزن ثبت شده و به‌صورت خودکار پس از هر build موفق Windows به‌روز می‌شود. تصویر داشبورد `docs/images/k2-dashboard.png` مربوط به build قبلی است و اسکرین‌شات GUI ویندوزی از build جدید نداریم. راهنمای توکن‌ها و اصول طراحی در `docs/UI_UX_GUIDE.md` آمده است.

آنچه هنوز **تأیید نشده**: نمایش گرافیکی build جدید روی ویندوز فیزیکی، تست نصب تمیز، امضای دیجیتال و آزمون میدانی کاربران.

---

## ۲. وضعیت دروازه‌ها (Gates)

| دروازه | موضوع | وضعیت | شواهد |
|---|---|---|---|
| Gate 0 | شناخت مخزن، ثبت وضعیت، مستندات اولیه | ✅ | `docs/PROJECT_GROUND_TRUTH.md` و تاریخچهٔ commit در Git |
| Gate 1 | مدل داده و هستهٔ آفلاین | ✅ | `storage/` + `test_storage.py` (۱۱ تست) |
| Gate 2 | راه‌اندازی و تقویم ثابت | ✅ | `onboarding.py` + `test_onboarding.py` (۱۲ تست) |
| Gate 3 | ظرفیت و زمان‌بند | ✅ | `capacity.py`، `scheduler.py` + تست‌ها |
| Gate 4 | چرخهٔ فعالیت و عقب‌افتادگی | ✅ | `activity_lifecycle.py`، `backlog.py` |
| Gate 5 | چرخهٔ یادگیری و مرور | ✅ | `review_engine.py` + ۱۷ تست |
| Gate 6 | آزمون، بانک خطا و موتور مشاور | ✅ | `exam_analysis.py`، `advisor_engine.py` + ۲۶ تست |
| Gate 7 | گزارش‌ها و UX | ✅ | `reporting.py`، ۸ صفحهٔ UI + ۱۴ تست GUI |
| Gate 8 | بسته‌بندی و اعتبارسنجی | ✅ **ساخت و headless verify در CI** | [Windows Actions موفق](https://github.com/rezaa2544/k2/actions/runs/39051925261)، ZIP کامل ثبت شد؛ GUI روی ویندوز فیزیکی و نصب تمیز هنوز تأیید نشده |

---

## ۳. اجرای تست‌ها — دستور و نتیجهٔ واقعی

```bash
cd /home/user/k2
export PYTHONPATH="$PWD/src"
export QT_QPA_PLATFORM=offscreen
python3 -m pytest tests -q
```

```
174 passed
```

| فایل | تعداد |
|---|---|
| `tests/test_jdate.py` | 10 |
| `tests/test_capacity.py` | 12 |
| `tests/test_scheduler.py` | 15 |
| `tests/test_activity_lifecycle.py` | 13 |
| `tests/test_review_engine.py` | 17 |
| `tests/test_exam_analysis.py` | 10 |
| `tests/test_storage.py` | 11 |
| `tests/test_invariants.py` | 10 |
| `tests/test_edge_cases.py` | 16 |
| `tests/test_onboarding.py` | 12 |
| `tests/test_advisor.py` | 16 |
| `tests/test_reporting.py` | 10 |
| `tests/test_gui.py` | 14 |
| `tests/test_app.py` | 2 |
| `tests/test_windows_download.py` | 2 |
| `tests/test_e2e_scenario.py` | 4 |
| **مجموع** | **174** |

محیط اجرا: تست محلی در Debian 13 / Python 3.13 / PySide6 6.9.1؛ build و smoke test ویندوز در GitHub Actions / `windows-latest` / Python 3.12.

---

## ۴. وضعیت اجرایی ویندوز

| گام | نتیجه |
|---|---|
| ساخت با PyInstaller 6.22.3 روی `windows-latest` | ✅ موفق؛ [run 39051925261](https://github.com/rezaa2544/k2/actions/runs/39051925261) |
| اجرای واقعی `K2.exe --headless` | ✅ موفق؛ process exit code صفر و پایگاه داده ساخته شد |
| ZIP توزیع one-folder | ✅ ثبت در `downloads/K2-windows-x64.zip`؛ `K2.exe` و `_internal` هر دو حاضرند |
| وضوح منوها | ✅ تست GUI و پیش‌نمایش Qt offscreen؛ GUI build تازه روی ویندوز فیزیکی **هنوز دیده نشده** |
| اجرای گرافیکی build قبلی زیر Wine | ✅ پیش‌تر انجام شد؛ این شاهد مربوط به build قبلی است، نه نسخهٔ تازهٔ منوها |
| ویندوز فیزیکی و نصب تمیز | ⚠️ هنوز تأیید نشده |

---

## ۵. پوشش نیازمندی‌ها

نگاشت کامل در [TRACEABILITY_MATRIX.md](TRACEABILITY_MATRIX.md). خلاصه:

* **P0:** ۴۲ نیازمندی — همه پیاده‌سازی و تست شده‌اند.
* **P1:** ۱۲ نیازمندی — ۱۱ کامل؛ `SUB-02` (ماتریس روش‌های آموزشی برای هر درس کنکوری) به‌صورت چارچوب کلی (ماتریس فاز×سطح + نگاشت نوع محتوا) پیاده شده، نه به‌صورت جدول اختصاصی هر ۹ درس.
* **P2:** ۲ نیازمندی — `SCH-06` (CP-SAT) عمداً انجام نشده (تصمیم D-007)؛ `BEH-03` (دفترچهٔ قبل آزمون) عمداً پیاده نشده.

---

## ۶. وضعیت Git

* مخزن محلی `/home/user/k2` روی شاخهٔ `main` به مخزن عمومی `rezaa2544/k2` push شده است.
* آخرین بستهٔ کامل در `downloads/K2-windows-x64.zip` است؛ build و checksum آن در GitHub Actions ساخته و به همان شاخه push شد.
* تاریخچه با push عادی حفظ شده است؛ force-push یا حذف فایل GitHub انجام نشده است.

---

## ۷. کارهای باقی‌مانده

### ۷.۱ ضروری برای «آمادهٔ انتشار»

1. بازبینی منوها در **GUI build تازه روی ویندوز ۱۰/۱۱ فیزیکی**.
2. تست روی **نصب تمیز** (بدون Python، بدون Qt).
3. **امضای دیجیتال** کد (برای کاهش هشدار آنتی‌ویروس).
4. ساخت **نصب‌کنندهٔ Inno Setup** (`packaging/k2.iss`).
5. انتشار Release نسخه‌دار (با tag؛ گردش‌کار آن را به‌صورت draft می‌سازد).

### ۷.۲ مهم (نه مسدودکننده)

6. آزمون میدانی با ۳ تا ۵ دانش‌آموز (بازهٔ فاز ۸ نقشهٔ راه).
7. خروجی PDF گزارش (DATA-03 اکنون فقط CSV دارد).
8. جدول روش‌های آموزشی اختصاصی هر درس کنکوری (SUB-02).
9. نسخه‌بندی taxonomy خطا (ERR-01 می‌گوید نسخه‌بندی‌شده).
10. بررسی دسترس‌پذیری با صفحه‌خوان واقعی.

### ۷.۳ اختیاری

11. سنجش اثر بخش CP-SAT (SCH-06) — فقط اگر روش قاعده‌محور در عمل کافی نبود.
12. چندپروفایلی آزمون.
13. بهبود برآورد زمان با دادهٔ واقعی بیشتر (EST-02).

---

## ۸. محدودیت‌های آگاهانهٔ محصول (نه نقص)

* اعداد تجربی فرضیه‌اند و در تنظیمات قابل تغییرند.
* تاریخ رسمی آزمون، ضرایب، قوانین و نمرهٔ منفی **حدس زده نمی‌شوند**.
* تاریخ نمونهٔ «۳۰ مهر» بدون سال است و **سال آن حدس زده نشده**.
* تعارض یکشنبه (شیمی/دینی) تا پاسخ کاربر **باز** می‌ماند.
* هیچ چت‌بات آزاد، استریک، رتبه‌بندی یا تشخیص روان‌شناختی وجود ندارد.
