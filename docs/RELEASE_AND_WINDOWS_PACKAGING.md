# انتشار و بسته‌بندی ویندوز — K2

نسخهٔ سند: 1.0 — آخرین به‌روزرسانی: ۱۴۰۵/۰۷/۲۵ (2026-10-17)

---

## ۱. وضعیت واقعی (بدون اغراق)

> **هشدار تازگی:** شواهد، اندازه و هش‌های این سند/جدول زیر مربوط به build قبلی است (تاریخچهٔ سند آن را به commit `b5419f5` و Windows Actions پیوند می‌دهد). در workspace فعلی `HEAD=3d6605a` و درخت کاری شامل تغییرات محلی متعدد است. جادوگر جدید، catalog ۱۴۰۶ و آزمون‌های تازه در آن ZIP اثبات نشده‌اند. این نوبت Windows EXE دوباره ساخته نشده و ZIP نباید به‌عنوان بستهٔ همگام با کد فعلی معرفی شود.

| مورد | آخرین وضعیت قابل اثبات | شواهد/دامنه |
|---|---|---|
| EXE/ZIP ویندوز قبلی | ✅ build تاریخی موفق | [Windows Actions run 39058074025](https://github.com/rezaa2544/k2/actions/runs/39058074025)؛ به نسخهٔ کد آن run محدود است. |
| اجرای واقعی EXE قبلی با `--headless` | ✅ در آن run گزارش شده | exit code صفر و ساخته‌شدن DB طبق گزارش ثبت‌شدهٔ همان run. |
| build Windows از working tree فعلی | ⚠️ **انجام‌نشده** | این محیط Windows، `pwsh`، `gh` و remote قابل استفادهٔ git ندارد؛ این نوبت امکان اجرای build ویندوز/ارسال به CI فراهم نشد. |
| تست/اجرای Windows فیزیکی | ❌ تأییدنشده | اجرای GUI روی Windows فیزیکی و Windows تمیز بدون Python در شواهد موجود نیست. |
| امضای دیجیتال / GitHub Release | ❌ انجام‌نشده | نیازمند گواهی و انتشار رسمی. |
| Push از این workspace | ❌ انجام‌نشده | در checkout فعلی remote نمایش داده نشد؛ هیچ pushی در این نوبت انجام نشده است. |

> **قاعدهٔ این پروژه:** «ساخته شد» با «اجرا شد» یکی نیست. هش قبلی به build فعلی تعمیم داده نمی‌شود.

> **شاهد تاریخی 2026-10-17:** بستهٔ پیشین در Windows Actions ساخته شد؛ آزمون‌ها و smoke test آن نسخه موفق گزارش شدند. این شاهد، build نهایی تغییرهای فعلی را ثابت نمی‌کند.
---

## ۲. مشخصات خروجی (ارقام زیر artifact نسخهٔ قبلی‌اند)

Metadata مرجع executable برای اسکریپت ساخت: `packaging/output/K2/K2.exe` — ۲٬۱۱۶٬۱۲۵ بایت. این مقدار و checksumهای زیر فقط وقتی به build جاری قابل انتساب‌اند که Windows packaging مجدداً اجرا و metadata به‌روزرسانی شود.

```
packaging/output/K2/
├── K2.exe              ۲٬۱۱۶٬۱۲۵ بایت   (بوت‌لودر PyInstaller + آرشیو)
└── _internal/          ~۱۱۰ مگابایت       (Qt6، shiboken6، پایتون، فونت‌ها)
    ├── PySide6/
    ├── k2/ui/assets/fonts/Vazirmatn-{Regular,Bold}.ttf
    └── ...
```

SHA-256:

```
6296c9a9c650401532dd917d801b00860f80f9ff494020ba09796549941791ad  K2.exe
9f4b49b99ab1b98089487ba2dc9f9433c8e6795e1376ba4481ba0eec5c979595  K2-windows-x64.zip
```

نسخهٔ ساخت محلی در `release/K2-windows-x64.zip` می‌ماند (خروجی در `.gitignore` است). برای درخواست دانلود مستقیم کاربر، همان بسته در `downloads/K2-windows-x64.zip` نیز در مخزن ثبت شده است (۴۹٬۸۲۱٬۶۱۳ بایت؛ حدود ۴۵ MiB). این آرشیو شامل `K2.exe` و `_internal/` است؛ فایل EXE به‌تنهایی اجراشدنی نیست.

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
* در بازبینی 2026-10-17، ۱۸۹ تست با PySide6 6.9.1 در لینوکس محلی و GitHub Actions (Linux/Windows) پاس شد. Windows Actions همین commit EXE را ساخت و smoke test `--headless` را با exit code صفر و ایجاد DB گذراند. اجرای GUI روی Windows فیزیکی تأییدنشده است.

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
| 1 | `pytest tests -q` همه پاس | ✅ ۱۸۹ تست محلی (Linux؛ تغییرهای جاری) |
| 2 | `K2.exe --headless` کد خروج ۰ | ✅ Windows Actions جاری؛ DB ساخته شد |
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
