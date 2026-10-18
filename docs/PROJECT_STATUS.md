# وضعیت پروژه — K2

تاریخ گزارش: ۱۴۰۵/۰۷/۲۶ (2026-10-18)
شاخهٔ کاری: `arena/947664ef-k2` — مخزن محلی: `/home/user/k2` (remote: `github.com/rezaa2544/k2`)

---

## ۱. خلاصهٔ اجرایی

**وضعیت این workspace در این نوبت:** `HEAD=4bb774a` روی شاخهٔ `arena/947664ef-k2`؛ تغییرهای محلی این نوبت ثبت/commit شده و push به همان شاخه انجام شده است. reset/checkout/stash انجام نشد.

**تمرکز این نوبت روی سه شکاف محصول بود** (بازخورد کاربر: «برنامه‌ها نیازهای منو برآورده نکرده»):

1. **تثبیت حافظه به‌جای تیک «انجام‌شده»** — `src/k2/consolidation.py` مدل DSR
   (Difficulty/Stability/Retrievability) و **نردبان تثبیت S0–S5** را پیاده می‌کند.
   هر مبحث فقط با شاهد عملکردی (score ≥ آستانهٔ [H]) و در پنجرهٔ زمانی خودش از یک
   پله به پلهٔ بعد می‌رود: دیده‌شده → بازیابی اولیه ≤۲۴ ساعت (پیش از خواب) →
   فاصله‌دار → تأخیری → انتقالی (سؤال تازه/ترکیبی) → نگهداری. پلهٔ از موعد گذشته
   وضعیت «عقب‌افتاده» می‌گیرد و در صف جبران قرار می‌گیرد؛ هیچ‌وقت بی‌صدا حذف نمی‌شود.
2. **پیش‌بینی ماندگاری تا روز آزمون** — `forecast_retention` با فرمول FSRS
   (`R(t,S) = (1 + 19t/81S)^−0.5`) درصد بازیابی‌پذیریِ هر مبحث در روز آزمون را
   بر پایهٔ پایداریِ مشتق‌شده از مرورهای واقعی همان کاربر پیش‌بینی می‌کند؛ در نبود
   داده، عددی ساخته نمی‌شود. این یک **پیش‌بینی** است، نه تضمین حافظه.
3. **برنامهٔ سه‌مسیره و امکان‌سنجی** — `src/k2/streams.py` ظرفیت مؤثر هر روز را بین
   «مبحث جدید / جبران عقب‌افتادگی / تثبیت» تقسیم می‌کند (کف تثبیت ۲۰٪، سقف ۴۵٪،
   سقف جبران ۴۰٪، کف مطلب جدید ۱۵٪). `catchup_plan` بدهی را قدم‌به‌قدم روی روزها
   پخش می‌کند (حداکثر به‌اندازهٔ بلوک مجاز در هر روز) و باقی‌مانده را صریح گزارش
   می‌کند؛ `assess_feasibility` اگر کار تا آزمون جا نشود، سطح و چهار گزینهٔ
   **پیشنهادی** (نه خودکار) می‌دهد.

همراه این موتورها: `src/k2/learning_science.py` با ۲۰ شواهد مستقل (testing effect،
spacing، interleaving، worked examples/expertise reversal، تثبیت در خواب، desirable
difficulties، DSR/FSRS، hypercorrection) که هر توصیهٔ موتور به شناسهٔ آن‌ها پیوند
می‌خورد؛ کاتالوگ فرضیه‌محور ۲۱۴ مبحث برای ۲۰ ترکیب درس/گروه
(`konkur_catalog.TOPICS_BY_COURSE` + `service.seed_topics_from_catalog`) تا کاربر
بتواند سریع شروع کند و خودش تأیید/حذف کند؛ و نمای «تثبیت حافظه» در رابط کاربری
(صفحهٔ نهم) با توزیع مسیرها، امکان‌سنجی، صف جبران و جدول نردبان.

`ReviewItem` دو ستون جدید `stability_days` و `retrievability` گرفت،
`difficulty` از int به float تغییر کرد (تطابق با مدل DSR)، و `schema.py` به
نسخهٔ ۵ با `MIGRATION_5` رسید؛ `repositories.py` هر دو ستون را با fallback
سازگار با نسخهٔ پیشین می‌خواند و می‌نویسد. سندٔ کامل شواهد و نگاشت شواهد به کد:
`docs/research/05_MEMORY_CONSOLIDATION_AND_STREAMS.md`.

در این نوبت، کل suite با **۲۶۶ تست موفق** اجرا شد (پیش‌تر ۲۰۳)؛ `compileall`،
Node parse روی JS ترکیب‌شدهٔ preview، بازتولید Preview و `git diff --check` نیز
پاس شدند. Preview HTML در همان commit به‌روز شد (درگاه CI). آزمون DOM واقعی
مرورگر انجام نشده. **build/اجرای EXE ویندوز برای این working tree انجام نشده** و
ZIP موجود مربوط به build قبلی است.

**Windows:** build/اجرای EXE این working tree انجام نشده؛ بسته و شواهد Windows
Actions موجود مربوط به build قبلی‌اند. GUI روی Windows فیزیکی، نصب تمیز و امضای
دیجیتال همچنان تأیید نشده‌اند.

---

---

## ۲. وضعیت دروازه‌ها (Gates)

| دروازه | موضوع | وضعیت | شواهد |
|---|---|---|---|
| Gate 0 | شناخت مخزن، ثبت وضعیت، مستندات اولیه | ✅ | `docs/PROJECT_GROUND_TRUTH.md` و تاریخچهٔ commit در Git |
| Gate 1 | مدل داده و هستهٔ آفلاین | ✅ | `storage/` + `test_storage.py` (۱۳ تست) |
| Gate 2 | راه‌اندازی و تقویم ثابت | ✅ | `onboarding.py` + `test_onboarding.py` (۱۴ تست) |
| Gate 3 | ظرفیت و زمان‌بند | ✅ | `capacity.py`، `scheduler.py` + تست‌ها |
| Gate 4 | چرخهٔ فعالیت و عقب‌افتادگی | ✅ | `activity_lifecycle.py`، `backlog.py` |
| Gate 5 | چرخهٔ یادگیری و مرور | ✅ | `review_engine.py` + ۱۷ تست + مدل DSR در `consolidation.py` |
| Gate 6 | آزمون، بانک خطا و موتور مشاور | ✅ | `exam_analysis.py`، `advisor_engine.py` + ۲۶ تست |
| Gate 7 | گزارش‌ها و UX | ✅ | `reporting.py`، ۹ صفحهٔ UI + ۱۹ تست GUI |
| Gate 9 | تثبیت حافظه، سه مسیر و امکان‌سنجی | ✅ | `consolidation.py`، `streams.py`، `learning_science.py` + ۶۴ تست تازه + نمای تثبیت |
| Gate 8 | بسته‌بندی و اعتبارسنجی | ⚠️ **تاریخی؛ working tree فعلی نیازمند build** | [Windows Actions پیشین](https://github.com/rezaa2544/k2/actions/runs/39058074025) و ZIP آن نسخه؛ به تغییرهای فعلی تعمیم داده نمی‌شوند |

---

## ۳. اجرای تست‌ها — دستور و نتیجهٔ واقعی

```bash
cd /home/user/k2
export PYTHONPATH="$PWD/src"
export QT_QPA_PLATFORM=offscreen
python3 -m pytest tests -q
```

```
266 passed  # run in current local working tree on 2026-10-18
```

> جدول تفکیکی فایل‌های زیر از snapshot قدیمی‌تر است؛ جمع 203 تستِ بالا نتیجهٔ اجرای جاری را نشان می‌دهد. تست‌های تازهٔ `test_learning_evidence.py` و `test_preview.py` نیز در همین اجرا بودند.

| فایل | تعداد (snapshot قبلی) |
|---|---|
| `tests/test_jdate.py` | 10 |
| `tests/test_capacity.py` | 13 |
| `tests/test_scheduler.py` | 15 |
| `tests/test_activity_lifecycle.py` | 13 |
| `tests/test_review_engine.py` | 17 |
| `tests/test_exam_analysis.py` | 10 |
| `tests/test_storage.py` | 13 |
| `tests/test_invariants.py` | 10 |
| `tests/test_edge_cases.py` | 16 |
| `tests/test_onboarding.py` | 15 |
| `tests/test_advisor.py` | 18 |
| `tests/test_reporting.py` | 10 |
| `tests/test_gui.py` | 22 |
| `tests/test_app.py` | 2 |
| `tests/test_windows_download.py` | 3 |
| `tests/test_e2e_scenario.py` | 4 |
| `tests/test_subject_selection.py` | 3 |
| `tests/test_konkur_catalog.py` | 5 |
| `tests/test_learning_science.py` | 7 |
| `tests/test_consolidation.py` | 27 |
| `tests/test_streams.py` | 13 |
| `tests/test_consolidation_service.py` | 14 |
| `tests/test_learning_evidence.py` | 3 |
| `tests/test_preview.py` | 3 |
| **مجموع** | **۲۶۶** |

محیط تست این نوبت: Linux / Python 3.11.2 / PySide6 6.9.1، با `QT_QPA_PLATFORM=offscreen` و کتابخانه‌های استاب موقت در `/tmp` (بدون دسترسی به apt). workflowهای GitHub در مخزن تعریف شده‌اند، اما برای این working tree اجرا نشده‌اند.

---

## ۴. وضعیت اجرایی ویندوز (شواهد نسخهٔ قبلی، نه working tree فعلی)

موارد زیر فقط برای artifact/build قبلی‌اند؛ از روی آن‌ها موفقیت build این نوبت نتیجه گرفته نمی‌شود.

| گام | نتیجهٔ build قبلی |
|---|---|
| ساخت با PyInstaller 6.22.3 روی `windows-latest` | ✅ موفق؛ [run 39058074025](https://github.com/rezaa2544/k2/actions/runs/39058074025) |
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

* `HEAD=3d6605a` است، اما working tree تغییرات محلی دارد. هیچ reset/checkout/stash انجام نشده؛ `git remote -v` خروجی ندارد و تغییرهای این گزارش push نشده‌اند.
* `downloads/K2-windows-x64.zip` شامل `K2.exe` و `_internal` است، اما artifact تاریخی است و پس از تغییرهای جاری بازسازی یا اجرا نشده.
* GUI روی Windows فیزیکی، نصب تمیز، build Windows همین revision و آزمون میدانی تأیید نشده‌اند. GitHub workflow تعریف شده، اما برای این tree اجرا نشده.

---

## ۷. کارهای باقی‌مانده

### ۷.۱ ضروری برای «آمادهٔ انتشار»

1. فراهم‌کردن remote مجاز یا runner ویندوز و اجرای Windows CI روی همین revision؛ build، headless smoke و ZIP تازه را تولید و تأیید کند.
2. فقط پس از build موفق، به‌روزرسانی/انتشار عادی با حفظ تاریخچه؛ این مورد هنوز به‌علت نبود remote ممکن نیست.
3. بازبینی منوها در **GUI build تازه روی ویندوز ۱۰/۱۱ فیزیکی**.
4. تست روی **نصب تمیز** (بدون Python، بدون Qt).
5. **امضای دیجیتال** کد (برای کاهش هشدار آنتی‌ویروس).
6. ساخت **نصب‌کنندهٔ Inno Setup** (`packaging/k2.iss`).
7. انتشار Release نسخه‌دار (با tag؛ گردش‌کار آن را به‌صورت draft می‌سازد).

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
