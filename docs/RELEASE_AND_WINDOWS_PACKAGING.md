# انتشار و بسته‌بندی ویندوز — K2

نسخهٔ سند: 1.0 — آخرین به‌روزرسانی: ۱۴۰۵/۰۷/۲۴ (2026-10-17)

---

## ۱. وضعیت واقعی (بدون اغراق)

| مورد | وضعیت | شواهد |
|---|---|---|
| ساخت EXE ویندوز ۶۴بیتی | ✅ **انجام شد** | `packaging/output/K2/K2.exe` — ۱٬۹۹۱٬۸۸۴ بایت (PySide6 6.9.1؛ بازسازی‌شده پس از بهبود UI/UX) |
| اجرای واقعی EXE در حالت `--headless` | ✅ **انجام شد** (exit code صفر، پایگاه داده ساخته شد) | [Windows Actions موفق](https://github.com/rezaa2544/k2/actions/runs/39051925261) روی `windows-latest` |
| اجرای GUI نسخهٔ تازهٔ منوها | ⚠️ **تأییدنشده روی Windows فیزیکی** | تست GUI و پیش‌نمایش Qt offscreen پاس شده؛ اسکرین‌شات `docs/images/k2-dashboard.png` مربوط به build قبلی است |
| اجرا روی ویندوز فیزیکی ۱۰/۱۱ | ❌ **انجام‌نشده** | در این محیط دسترسی به ویندوز واقعی نبود |
| تست روی ویندوز تمیز بدون پایتون | ❌ **انجام‌نشده** | نیازمند دسترسی به ماشین/ماشین‌مجاز ویندوز |
| امضای دیجیتال | ❌ انجام‌نشده | نیازمند گواهی Code Signing |
| انتشار در GitHub Releases | ❌ انجام‌نشده | ZIP کامل در مخزن موجود است؛ Release رسمی با tag نسخه ساخته می‌شود |

> **قاعدهٔ این پروژه:** «ساخته شد» با «اجرا شد» یکی نیست. هر ادعای بالا با فرمان و خروجی واقعی پشتیبانی شده است.

---

## ۲. مشخصات خروجی

```
packaging/output/K2/
├── K2.exe              ۱٬۹۹۱٬۸۸۴ بایت   (بوت‌لودر PyInstaller + آرشیو)
└── _internal/          ~۱۱۰ مگابایت       (Qt6، shiboken6، پایتون، فونت‌ها)
    ├── PySide6/
    ├── k2/ui/assets/fonts/Vazirmatn-{Regular,Bold}.ttf
    └── ...
```

SHA-256:

```
0430c36b0b457bfcdaee31d4ea8fe9ef5573e600fc067d1551f2f0388bbcc17c  K2.exe
45ab60600344043e603ab6273e7de5e024f2839ab7e3944ac0ca15b49715d68e  K2-windows-x64.zip
```

نسخهٔ ساخت محلی در `release/K2-windows-x64.zip` می‌ماند (خروجی در `.gitignore` است). برای درخواست دانلود مستقیم کاربر، همان بسته در `downloads/K2-windows-x64.zip` نیز در مخزن ثبت شده است (۴۹٬۶۹۷٬۶۱۰ بایت؛ حدود ۴۵ MiB). این آرشیو شامل `K2.exe` و `_internal/` است؛ فایل EXE به‌تنهایی اجراشدنی نیست.

---

## ۳. چرا توزیع پوشه‌ای (one-folder) و نه تک‌فایل؟

* `--onefile` هر بار کل محتوا (۱۱۰ مگابایت) را در `%TEMP%` استخراج می‌کند: کند، مستعد خطای آنتی‌ویروس، و مشکل‌ساز برای مسیرهای دارای نویسهٔ فارسی.
* توزیع پوشه‌ای، شروع فوری، مسیرهای قابل‌پیش‌بینی و امکان ساخت نصب‌کنندهٔ Inno Setup را فراهم می‌کند.
* حجم ۱۱۰ مگابایت برای یک برنامهٔ دسکتاپ کامل قابل‌قبول است.

---

## ۴. تصمیم حیاتی: نسخهٔ PySide6

### ۴.۱ چه اتفاقی افتاد

هنگام ساخت اولین EXE با **PySide6 6.12.0**، اجرای گرافیکی با این خطا متوقف شد:

```
ImportError: DLL load failed while importing QtWidgets: Module not found.
# لایهٔ زیرین:
err:module:import_dll Library icuuc.dll (which is needed by Qt6Core.dll) not found
```

### ۴.۲ ریشهٔ مشکل

`Qt6Core.dll` در نسخه‌های ۶.۱۰ به بعد **به‌صورت ایمپورت ایستا** به `icuuc.dll` (و طبق گزارش‌ها `icu.dll` و پوشهٔ `Windows\Globalization`) نیاز دارد. این‌ها **DLLهای خودِ سیستم‌عامل ویندوز** هستند:

* از ویندوز ۱۰ نسخهٔ ۱۷۰۳ به بعد و ویندوز ۱۱ موجودند.
* در هیچ چرخاب PyPI از PySide6 (از ۶.۶.۱ تا ۶.۱۲.۰) همراه نیستند.
* Wine آن‌ها را عرضه نمی‌کند (به همین دلیل اجرای گرافیکی زیر Wine شکست خورد).

این موضوع با **بررسی مستقیم جدول ایمپورت** چرخاب‌ها ثابت شد، نه با حدس:

```bash
python packaging/inspect_wheel_dll.py 6.12.0   # → icuuc.dll
python packaging/inspect_wheel_dll.py 6.9.1    # → بدون icuuc.dll
python packaging/inspect_wheel_dll.py 6.8.3    # → بدون icuuc.dll
python packaging/inspect_wheel_dll.py 6.7.3    # → بدون icuuc.dll
python packaging/inspect_wheel_dll.py 6.6.1    # → بدون icuuc.dll
```

### ۴.۳ تصمیم

**PySide6 به نسخهٔ `6.9.1` تثبیت شد** (در `requirements.txt` و `pyproject.toml`).

* مزیت: اجرایی روی ویندوزهای گسترده‌تر، بدون وابستگی به DLL سیستمی ICU، و قابل‌اجرا و قابل‌آزمایش در محیط Wine.
* هزینه: از ویژگی‌های تازهٔ Qt 6.10+ محروم می‌شویم — اما محصول ما از آن‌ها استفاده نمی‌کند.
* تأیید: ۱۷۴ تست محلی با ۶.۹.۱ پاس شد؛ Windows Actions نیز تست‌ها، build و smoke test headless نسخهٔ تازه را موفق انجام داد. اجرای GUI نسخهٔ منوهای جدید روی Windows فیزیکی هنوز بررسی نشده است.

> اگر در آینده به ۶.۱۰+ مهاجرت کردیم، باید «کپی چهار مورد ICU از System32 ویندوز ۱۱» را به فرایند build اضافه کنیم یا از CI روی `windows-latest` (که ویندوز ۲۰۲۲ دارد) بسته‌بندی کنیم.

---

## ۵. ساخت روی ویندوز (روش پیشنهادی و رسمی)

```powershell
git clone https://github.com/rezaa2544/k2.git
cd k2
powershell -ExecutionPolicy Bypass -File .\packaging\build_windows.ps1
```

اسکریپت این توالی را اجرا می‌کند و در صورت هر خطا متوقف می‌شود:

1. ساخت محیط مجازی در `packaging/work/venv`
2. نصب `requirements.txt` + `requirements-dev.txt` + `pyinstaller`
3. **اجرای کل تست‌ها** (`pytest tests -q`) — در صورت شکست، build انجام نمی‌شود
4. ساخت با `k2.spec`
5. **اجرای واقعی EXE** با `Start-Process -Wait` و بررسی exit code + ساخته‌شدن پایگاه داده؛ این روش برای فایل GUI-subsystem هم قابل‌اعتماد است
6. چاپ خلاصهٔ خروجی

خروجی: `packaging/output/K2/K2.exe`

---

## ۶. ساخت خودکار در CI

`.github/workflows/build-windows.yml` روی `windows-latest`:

```
checkout → setup-python 3.12 → install → pytest → pyinstaller → verify(execute) → rebuild ZIP + checksum → push package → upload artifact
```

مرحلهٔ `verify` از `Start-Process -Wait -PassThru` استفاده می‌کند تا exit code واقعی فایل EXE (حتی با `console=False`) را دریافت کند و ساخته‌شدن پایگاه داده را نیز بررسی کند. تنها پس از موفقیت verify، ZIP کامل و checksumها به `main` push می‌شوند.

بدون این مرحله، یک build «موفق» ولی غیرقابل‌اجرا می‌تواند منتشر شود — همان چیزی که در همین پروژه رخ داد (D-013).

---

## ۷. ساخت در این محیط (لینوکس) — چگونه انجام شد

برای تولید EXE ویندوزی از لینوکس، از **Wine + پایتون ویندوز** استفاده شد:

```bash
# ۱) پایتون ۶۴بیتی ویندوز (بستهٔ قابل‌حمل nuget، بدون نیاز به نصب‌کنندهٔ گرافیکی)
curl -L -o python.nupkg https://www.nuget.org/api/v2/package/python/3.12.7
mkdir winpy && (cd winpy && unzip -oq ../python.nupkg)
cp -r winpy/tools "$WINEPREFIX/drive_c/Python312"

# ۲) نصب وابستگی‌های ویندوزی
wine64 "C:\\Python312\\python.exe" -m pip install PySide6==6.9.1 jdatetime pyinstaller

# ۳) ساخت
wine64 "C:\\Python312\\python.exe" -m PyInstaller k2.spec --noconfirm \
    --distpath "Z:\\home\\user\\k2\\packaging\\output" \
    --workpath "Z:\\home\\user\\k2\\packaging\\work"

# ۴) اجرای واقعی
wine64 "Z:\\...\\K2.exe" --db "Z:\\tmp\\k2-smoke.db" --headless
```

نکته: نسخهٔ ۳۲بیتی Wine لازم نیست؛ چرخاب nuget کاملاً ۶۴بیتی است. (نصیب‌کنندهٔ رسمی `python-3.12.7-amd64.exe` ۳۲بیتی است و زیر `wine64` اجرا نمی‌شود.)

---

## ۸. نصب‌کنندهٔ اختیاری (Inno Setup)

پس از ساخت، می‌توان از پوشهٔ خروجی یک نصب‌کننده ساخت. نمونهٔ `packaging/k2.iss`:

```ini
[Setup]
AppName=مشاور هوشمند کنکور
AppVersion=1.0.0
DefaultDirName={autopf}\K2
DefaultGroupName=K2
OutputBaseFilename=K2-Setup-1.0.0
ArchitecturesInstallIn64BitMode=x64
Compression=lzma2
SolidCompression=yes

[Files]
Source: "output\K2\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\مشاور هوشمند کنکور"; Filename: "{app}\K2.exe"
Name: "{group}\حذف K2"; Filename: "{uninstallexe}"
```

این فایل **ساخته و آزمایش نشده** (Inno Setup روی این محیط موجود نیست) — فقط دستورالعمل است.

---

## ۹. بررسی‌های پیش از انتشار (چک‌لیست)

| # | بررسی | وضعیت |
|---|---|---|
| 1 | `pytest tests -q` همه پاس | ✅ ۱۷۰ تست |
| 2 | `K2.exe --headless` کد خروج ۰ | ✅ زیر Wine |
| 3 | `K2.exe` گرافیکی باز می‌شود | ✅ زیر Wine + Xvfb |
| 4 | اجرا روی ویندوز ۱۰/۱۱ فیزیکی | ❌ انجام‌نشده |
| 5 | اجرا روی ویندوز تمیز بدون پایتون | ❌ انجام‌نشده |
| 6 | مسیر پایگاه داده با نویسهٔ فارسی | ✅ تست خودکار (`test_persian_path_*`) |
| 7 | قطع اینترنت و کارکرد هسته | ✅ تست خودکار (`test_offline_operation_without_network`) |
| 8 | پشتیبان‌گیری و بازیابی | ✅ تست خودکار + اجرای EXE روی پایگاه دادهٔ موجود |
| 9 | بستن و بازکردن دوباره | ✅ تست خودکار (`test_reopening_application_keeps_state`) |
| 10 | امضای دیجیتال | ❌ انجام‌نشده |
| 11 | آزمون میدانی ۳ تا ۵ کاربر | ❌ انجام‌نشده |

---

## ۱۰. شمارهٔ نسخه و انتشار

* نسخه در `src/k2/__init__.py` (`__version__ = "1.0.0"`) و `pyproject.toml` تعریف می‌شود — این دو باید همیشه همگام باشند.
* برچسب git پیشنهادی: `v1.0.0`
* گردش‌کار CI با برچسب `v*` یک Release پیش‌نویس (draft) می‌سازد.
* **انتشار عمومی تنها پس از امضای دیجیتال و آزمون روی ویندوز تمیز توصیه می‌شود** — چون فایل‌های EXE بدون امضا توسط برخی آنتی‌ویروس‌ها قرنطینه می‌شوند.
