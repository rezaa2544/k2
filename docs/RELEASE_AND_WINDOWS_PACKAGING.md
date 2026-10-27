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
| امضای دیجیتال / GitHub Release | ⚠️ خط لوله آماده، گواهی لازم | `signtool sign` + `verify` در CI پیاده و آزموده شده؛ برای امضای واقعی باید گواهیCode Signing داده شود (بند ۱۱). |
| Push از این workspace | ❌ انجام‌نشده | در checkout فعلی remote نمایش داده نشد؛ هیچ pushی در این نوبت انجام نشده است. |

> **قاعدهٔ این پروژه:** «ساخته شد» با «اجرا شد» یکی نیست. هش قبلی به build فعلی تعمیم داده نمی‌شود.

> **شاهد تاریخی 2026-10-17:** بستهٔ پیشین در Windows Actions ساخته شد؛ آزمون‌ها و smoke test آن نسخه موفق گزارش شدند. این شاهد، build نهایی تغییرهای فعلی را ثابت نمی‌کند.
---

## ۲. مشخصات خروجی (ارقام زیر artifact نسخهٔ قبلی‌اند)

Metadata مرجع executable برای اسکریپت ساخت: `packaging/output/K2/K2.exe` — ۳٬۰۹۶٬۳۷۰ بایت. این مقدار و checksumهای زیر فقط وقتی به build جاری قابل انتساب‌اند که Windows packaging مجدداً اجرا و metadata به‌روزرسانی شود.

```
packaging/output/K2/
├── K2.exe              ۳٬۰۹۶٬۳۷۰ بایت   (بوت‌لودر PyInstaller + آرشیو)
└── _internal/          ~۱۱۰ مگابایت       (Qt6، shiboken6، پایتون، فونت‌ها)
    ├── PySide6/
    ├── k2/ui/assets/fonts/Vazirmatn-{Regular,Bold}.ttf
    └── ...
```

SHA-256:

```
4dffa63db90b42cf0d02deb23ccd727115f7dafbd0785376b648e732f7048192  K2.exe
38686b6c0d28e656ed1a83deaea0439aecfe1c5bbf76864e22636085f6ef9f2a  K2-windows-x64.zip
3574d73cad26b4f7b20cbb5899351d4d09b6491b4d95262e19a9b9eb288fec61  K2-Setup-1.0.0.exe
```

نسخهٔ ساخت محلی در `release/K2-windows-x64.zip` می‌ماند (خروجی در `.gitignore` است). برای درخواست دانلود مستقیم کاربر، همان بسته در `downloads/K2-windows-x64.zip` نیز در مخزن ثبت شده است (۵۷٬۳۶۹٬۱۷۸ بایت؛ حدود ۴۵ MiB). این آرشیو شامل `K2.exe` و `_internal/` است؛ فایل EXE به‌تنهایی اجراشدنی نیست.

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

### ۶.۱ وضعیت همگام‌سازی باندل (آخرین بررسی)

قاعدهٔ این پروژه این است که هر تغییری در `src/` یا `k2.spec` باید
`preview/K2-preview.html` را در همان کامیت تازه کند؛ دروازهٔ
`.github/workflows/tests.yml` همین را می‌سنجد.

اما **بستهٔ ویندوز در این محیط لینوکسی بازسازی نمی‌شود**: PyInstaller
کراس‌کامپایل نمی‌کند و محیط ساخت پنجرهٔ ویندوزی ندارد. بنابراین وضعیت هر دو
باندل این است:

| باندل | چه کسی تازه می‌کند | وضعیت فعلی |
| --- | --- | --- |
| `preview/K2-preview.html` + `downloads/K2-preview-html.zip` | همینجا (اسکریپت `preview/build_preview.py` و `build_preview_zip.py`) | همگام با کامیت `599d411` (مهر `7fe6bee`) |
| `downloads/K2-windows-x64.zip` | گردش‌کار `build-windows` روی `main` | **کهنه** — از build پیشین است و هیچ مهر نسخهٔ سورس ندارد |

مرحلهٔ `Refresh the repository download bundle` با این شرط اجرا می‌شود:

```
github.ref == 'refs/heads/main' && github.event_name != 'pull_request'
```

یعنی روی PR اجرا **نمی‌شود**. پس تا وقتی این شاخه ادغام نشده، ZIP ویندوز در
مخزن نسخهٔ قدیمی است.

شاهد آخرین بررسی (PR #10، کامیت `599d411`): گردش‌کار `build-windows` با
موفقیت تمام شد — ۴۴۳ تست ویندوزی، ساخت EXE با PyInstaller، و **اجرای واقعی
EXE** (`--headless` با ساخت پایگاه داده و کد خروج ۰). این ثابت می‌کند کد جاری
قابل بیلد و اجراست، نه اینکه ZIP کامیت‌شده تازه باشد.

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

## ۸. نصب‌کنندهٔ استاندارد ویندوز (Inno Setup)

کاربر باید بتواند فایل `exe` را همان‌طور که هر نرم‌افزار ویندوزی را نصب می‌کند نصب کند؛ نه اینکه ZIP را باز کند و دنبال `K2.exe` بگردد. پس نصب‌کننده بخشی اجباری از ساخت است، نه اختیاری.

### ۸.۱ فایل اسکریپت

`packaging/k2_installer.iss` (Inno Setup 6، ساخته و آزمایش‌شده در CI):

```ini
[Setup]
AppId={{7C4E9A21-3B5D-4E8F-9A6C-1D2B3F4E5A60}}
AppName=K2 Konkur Advisor
AppVersion=1.0.0
DefaultDirName={autopf}\K2 Konkur Advisor
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
SetupIconFile=src\k2\ui\assets\k2.ico
OutputBaseFilename=K2-Setup-1.0.0
```

`AppId` یک GUID ثابت است و **هرگز تغییر نمی‌کند**؛ همین شناسه است که باعث می‌شود ویندوز نصب‌های بعدی را به‌روزرسانی ببیند نه نصب تکراری.

### ۸.۲ چه چیزی استاندارد است

| قابلیت | پیاده‌سازی |
|---|---|
| نصب در Program Files | `DefaultDirName={autopf}\...` + `PrivilegesRequired=admin` |
| صفحهٔ توافق‌نامهٔ استفاده | `LicenseFile=EULA.txt` — پذیرش صریح کاربر |
| صفحهٔ پوشهٔ مقصد | پیش‌فرض Inno (غیرفعال نشده) |
| صفحهٔ پوشهٔ منوی Start | `DisableProgramGroupPage=no` |
| صفحهٔ گونهٔ نصب | `[Types]` با «نصب کامل» و «نصب دلخواه» (`iscustom`) |
| اجزای قابل انتخاب | `[Components]` — برنامه `fixed`، راهنمای کاربر اختیاری |
| کارهای افزودنی | `[Tasks]` — میان‌بر میزکار (per-user/common) + `AllowNoIcons=yes` |
| فهرست Start-Menu | `[Icons]` با `{group}` (برنامه، راهنما، حذف نصب) |
| میان‌بر میزکار | `[Tasks]` اختیاری (per-user و common) |
| ثبت در Add/Remove Programs | خودکار توسط Inno Setup با `AppId` ثابت + `AppComments`/`AppContact`/`AppPublisher`/`AppVersion` |
| حذف استاندارد | `{uninstallexe}` + `UninstallDisplayIcon` + `UninstallDisplayName` |
| ارتقای تمیز | `[InstallDelete]` پوشهٔ مستندات کهنه را پیش از کپی پاک می‌کند |
| جلوگیری از نصب هم‌زمان | `AppMutex` (mutex واقعی در `src/k2/app.py`) + `CloseApplications=yes` |
| فارسی و راست‌چین | `packaging/innosetup/Languages/Farsi.isl` کامل با `RightToLeft=yes` |
| حفظ دادهٔ کاربر | `[UninstallDelete]` فقط `{app}` را پاک می‌کند |

#### ۸.۲.۰ فایل زبان فارسی کامل

`Farsi.isl` همهٔ پیام‌های صفحه‌هایی را که این نصب‌کننده نشان می‌دهد پوشش
می‌دهد (۱۸۰ پیام). چرا لازم بود: Inno Setup برای هر پیامی که در فایل زبان
نباشد **خودکار به انگلیسی برمی‌گردد**؛ نتیجه نصب‌کننده‌ای بود که بعضی
صفحه‌ها فارسی و بعضی انگلیسی‌اند و برای کاربر «ناقص» به نظر می‌رسید.
تست `test_persian_language_file_covers_every_wizard_page_shown` دقیقاً همان
فهرست پیام‌های موردنیاز را از روی خود `.iss` می‌سازد و ترجمه‌نشده‌ها را
می‌گیرد، پس اگر صفحهٔ تازه‌ای اضافه شود تست می‌شکند.

#### ۸.۲.۱ راهنمای کاربر نصب‌شده (چرا HTML و نه Markdown)

`packaging/USER_GUIDE.html` یک فایل خودبسندهٔ فارسی و راست‌چین است که در
`{app}\docs` نصب می‌شود، میان‌بر منوی Start می‌گیرد و تیک صفحهٔ پایان را
دارد. عمداً Markdown نیست: ویندوز به‌صورت پیش‌فرض برنامه‌ای برای `.md`
ندارد و باز کردنش می‌شکند، ولی HTML را همیشه مرورگر پیش‌فرض باز می‌کند.
فایل هیچ پیوند بیرونی و هیچ جاوااسکریپتی ندارد تا آفلاین خوانده شود.

#### ۸.۲.۲ قفل نسخهٔ یگانه (single instance)

نصب‌کننده با `AppMutex=K2KonkurAdvisorMutex` می‌پرسد «برنامه باز است؟». این
اعلام فقط وقتی معنا دارد که خود برنامه همان mutex را بسازد؛ پس
`src/k2/app.py` در مسیر گرافیکی (نه `--headless`) با
`ctypes.WinDLL("kernel32").CreateMutexW` یک mutex سراسری می‌سازد و handle را
تا پایان عمر فرایند نگه می‌دارد. اگر نسخهٔ دیگری باز باشد، پنجرهٔ دومی باز
نمی‌شود و پیام فارسی نشان داده می‌شود.

نکته‌های طراحی:

* روی غیر ویندوز هیچ قفلی ساخته نمی‌شود؛ تابع همیشه `True` برمی‌گرداند.
* هر خطایی در ساخت mutex برنامه را متوقف نمی‌کند (بهتر از برنامهٔ خراب).
* `--headless` قفل نمی‌گیرد، چون هم بررسی سلامت است و هم نصب‌کننده در CI پس
  از اجرای health-check باید بتواند نصب دوم (ارتقا) را انجام دهد.

قبلاً نصب‌کننده یک بخش `[Code]` داشت که با `CheckForMutexes` دنبال mutexی
روی GUID می‌گشت، در حالی که هیچ فرایندی آن را نمی‌ساخت — پس همیشه `False`
برمی‌گرداند و بی‌اثر بود. آن بخش حذف شد و مکانیزم واقعی جایگزین شد.

### ۸.۳ ساخت در CI

گردش‌کار `.github/workflows/build-windows.yml` سه گام تازه دارد:

1. `Build the standard Windows installer (Inno Setup)` — `iscc packaging\k2_installer.iss`
2. `Verify the installer is a standard Windows package` — امضای `MZ` و متادیتای `ProductName`
3. `Upload the installer` — artifact + ضمیمهٔ release

Inno Setup 6.7.1 روی `windows-latest` از پیش نصب است و نیازی به نصب دستی نیست. نصب‌کنندهٔ ساخته‌شده در `downloads/K2-Setup-1.0.0.exe` نیز در مخزن ثبت شده است (۳۹٬۳۰۹٬۱۷۰ بایت) تا دانلود مستقیم کار کند.

### ۸.۴ ساخت محلی

```powershell
iscc packaging\k2_installer.iss
```

خروجی در `packaging/output/K2-Setup-1.0.0.exe` می‌آید. پیش‌نیاز: پوشهٔ `packaging/output/K2/` از گام PyInstaller موجود باشد.


## ۹. بررسی‌های پیش از انتشار (چک‌لیست)

| # | بررسی | وضعیت |
|---|---|---|
| 1 | `pytest tests -q` همه پاس | ✅ ۵۳۷ تست (Linux + Windows Actions) |
| 2 | `K2.exe --headless` کد خروج ۰ | ✅ Windows Actions |
| 3 | آیکن برنامه داخل EXE نشسته باشد | ✅ `packaging/verify_exe_icon.py` بخش منابع PE را می‌خواند و با `k2.ico` مقایسه می‌کند |
| 4 | نصب‌کننده استاندارد ساخته شود | ✅ Inno Setup روی `windows-latest` |
| 5 | نصب واقعی روی ویندوز | ✅ گام `Install the built installer on Windows` — نصب خاموش، بررسی فایل‌ها، رجیستری، میان‌برها، اجرای برنامه |
| 6 | نصب دوم ارتقا باشد نه نصب تکراری | ✅ همان گام، با شمارش ورودی‌های رجیستری |
| 7 | حذف نصب تمیز باشد | ✅ گام `Uninstall and verify the user's data survives` — پوشهٔ برنامه و رجیستری پاک، دادهٔ کاربر حفظ |
| 8 | مسیر پایگاه داده با نویسهٔ فارسی | ✅ تست خودکار |
| 9 | قطع اینترنت و کارکرد هسته | ✅ تست خودکار |
| 10 | پشتیبان‌گیری و بازیابی | ✅ تست خودکار |
| 11 | امضای دیجیتال | ⚠️ خط لوله آماده و آزموده؛ گواهی لازم است (بند ۱۱) |
| 12 | آزمون روی ویندوز ۱۰/۱۱ فیزیکی | ⚠️ روی `windows-latest` (Windows Server 2025) انجام شد؛ دستگاه فیزیکی نه |
| 13 | آزمون میدانی ۳ تا ۵ کاربر | ❌ انجام‌نشده |

---

---

## ۱۰. آیکنِ داخل EXE

`k2.spec` مسیر `src\k2\ui\assets\k2.ico` را به PyInstaller می‌دهد، ولی
«مسیر داده شده» به‌معنای «آیکن روی EXE نشسته» نیست. اگر فایل نباشد یا
PyInstaller آن را جا ندهد، build موفق می‌شود ولی کاربر آیکن پیش‌فرض را
می‌بیند.

`packaging/verify_exe_icon.py` بخش منابع (`.rsrc`) فایل PE را می‌خواند:

* `RT_ICON`ها را استخراج و با فریم‌های فایل `.ico` **بایت‌به‌بایت** مقایسه
  می‌کند (PyInstaller در `CopyIcons_FromIco` محتوای فریم را دست‌نخورده
  می‌نویسد).
* `RT_GROUP_ICON` را می‌خواند و اندازه‌های اعلام‌شده را با فایل `.ico`
  می‌سنجد (اندازهٔ هر entry در `ICONDIRENTRY` **۱۶ بایت** است، نه ۱۴).
* اگر روزی PyInstaller بازکدوانی کرد، به مقایسهٔ تصویر رمزگشایی‌شده با
  Pillow برمی‌گردد.

در CI گام `Verify the application icon is embedded in the EXE` این بررسی را
اجرا می‌کند و در صورت نبود آیکن، build را می‌شکند.

---

## ۱۱. امضای دیجیتال

### ۱۱.۱ چه چیزی آماده است

خط لولهٔ امضا پیاده شده و در CI **آزموده** می‌شود. خودآزمایی دو نیمهٔ جدا
دارد، چون ریسکشان یکی نیست:

**نیمهٔ یک — «امضا و خواندن امضا» (آزموده‌شده روی `windows-latest`):**
گواهی خودامضای موقت ساخته می‌شود، یک **کپی** از `K2.exe` در
`%RUNNER_TEMP%` با `signtool sign` امضا می‌شود، و بعد همان امضا با
`Get-AuthenticodeSignature` خوانده و سه چیز سنجیده می‌شود: امضا **موجود
است**، با محتوای فایل **می‌خواند** (`HashMismatch` نیست)، و به **همان
گواهی موقت ما** تعلق دارد. کل این نیمه حدود ۴ ثانیه طول می‌کشد و به
زنجیرهٔ اعتماد ویندوز وابسته نیست.

**نیمهٔ دو — «راستی‌آزمایی با زنجیرهٔ اعتماد» (روی runner اثبات‌نشده):**
گواهی به انبار ریشهٔ همین کاربر افزوده و با `signtool verify /pa`
راستی‌آزمایی می‌شود. همین نیمه روی `windows-latest` آویزان می‌ماند —
**نوشتن در انبار ریشهٔ ویندوز در نشست غیرتعاملی گیر می‌کند** (لاگ مرحله‌ای
این را دقیقاً نشان داد: گواهی در ثانیهٔ ۲ ساخته شد، PFX در ثانیهٔ ۲ صادر
شد، و بعد `$rootStore.Add($cert)` دیگر برنگشت). پس این نیمه به‌صورت
**فرزندِ با مهلت ۱۲۰ ثانیه‌ای** اجرا می‌شود؛ اگر آویزان شد `::warning::`
می‌دهد و رد می‌شود، بدون اینکه نتیجهٔ نیمهٔ یک را از دست بدهد.

تفکیک این دو از قبل یک باگ واقعی بود: نیمهٔ حساس به نیمهٔ اختیاری گره
خورده بود، و چون نیمهٔ اختیاری بلاتعویف بود، **هیچ‌کدام** اجرا نمی‌شد.

منطق هر دو در `packaging/signing_selftest.ps1` است و در بلاک `finally`
حتی در صورت خطا هم پاک‌سازی می‌شود — گواهی از انبار شخصی و (اگر نیمهٔ دو
فرصت کرده باشد) از انبار ریشه برداشته می‌شود، تا گواهی خودامضا هرگز به
artifact نرسد. کل خودآزمایی هم به‌صورت فرزندِ با مهلت ۵ دقیقه‌ای اجرا
می‌شود تا اگر آویزان شد، گام‌های نصب و حذف نصب اجرا نشوند.
  > نکتهٔ صادقانه: نیمهٔ یک روی `windows-latest` **اجرا و موفق شد**
  > (امضا انجام شد، امضا خوانده شد، و به گواهی درست مقایسه شد). نیمهٔ دو
  > هنوز روی این runner **اثبات‌نشده** است، چون نوشتن در انبار ریشه
  > غیرتعاملی گیر می‌کند.
* گام `Sign artifacts for release` وقتی سکرت گواهی موجود باشد، `K2.exe` را
  امضا و راستی‌آزمایی می‌کند.
* گام `Sign the installer` همان کار را روی `K2-Setup-*.exe` می‌کند تا
  SmartScreen هنگام اجرای نصب‌کننده هشدار ندهد.

### ۱۱.۲ چه چیزی لازم است (فقط شما می‌توانید فراهم کنید)

امضای واقعی به گواهی Code Signing از یک مرجع معتبر نیاز دارد که خرید و
تأیید هویت می‌خواهد؛ این کار از این محیط ممکن نیست. برای فعال‌سازی:

1. گواهی `.pfx` را بگیرید (از CA یا Azure Trusted Signing).
2. در مخزن، سکرت‌های زیر را تنظیم کنید:
   * `WINDOWS_CERTIFICATE_PFX_BASE64` — محتوای base64 فایل `.pfx`
   * `WINDOWS_CERTIFICATE_PASSWORD` — گذرواژهٔ آن
3. متغیر `WINDOWS_SIGNING_ENABLED` را `true` بگذارید (اختیاری؛ وجود سکرت
   خودبه‌خود کافی است).

اگر `WINDOWS_SIGNING_ENABLED=true` باشد ولی گواهی نباشد، build **شکست
می‌خورد** — بی‌صدا رد نمی‌شود. اگر هیچ‌کدام نباشد، artifact بدون امضا منتشر
می‌شود و CI با `::notice::` صریحاً اعلام می‌کند.

### ۱۱.۳ ساخت محلی

```powershell
$env:K2_CERTIFICATE_PFX = "C:\path\to\certificate.pfx"
$env:K2_CERTIFICATE_PASSWORD = "..."
powershell -ExecutionPolicy Bypass -File .\packaging\build_windows.ps1
```

بدون این متغیرها، اسکریپت با هشدار صریح ادامه می‌دهد و artifact بدون امضا
می‌ماند.

---

## ۱۲. شمارهٔ نسخه و انتشار

* نسخه در `src/k2/__init__.py` (`__version__ = "1.0.0"`) و `pyproject.toml` تعریف می‌شود — این دو باید همیشه همگام باشند.
* برچسب git پیشنهادی: `v1.0.0`
* گردش‌کار CI با برچسب `v*` یک Release پیش‌نویس (draft) می‌سازد.
* **انتشار عمومی تنها پس از امضای دیجیتال و آزمون روی ویندوز تمیز توصیه می‌شود** — چون فایل‌های EXE بدون امضا توسط برخی آنتی‌ویروس‌ها قرنطینه می‌شوند.
