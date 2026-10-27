; ---------------------------------------------------------------------------
; نصب‌کنندهٔ استاندارد ویندوز برای «مشاور هوشمند کنکور» (K2)
;
; این اسکریپت با Inno Setup 6 ساخته می‌شود (روی runner ویندوز موجود است):
;     iscc packaging\k2_installer.iss
;
; مسیرهای نسبی نسبت به پوشهٔ همین فایل حل می‌شوند (packaging/)، نه نسبت به
; پوشه‌ای که iscc از آن اجرا شده. پس output\K2 یعنی packaging\output\K2.
;
; چه چیزی «استاندارد و کامل» می‌کند (همان چیزی که هر نصب‌کنندهٔ ویندوز دارد):
;   * نصب در Program Files با دسترسی مدیر (PrivilegesRequired=admin)
;   * صفحهٔ توافق‌نامهٔ استفاده با پذیرش صریح کاربر (LicenseFile)
;   * صفحهٔ انتخاب پوشهٔ مقصد و انتخاب پوشهٔ منوی Start
;   * صفحهٔ گونهٔ نصب (کامل/دلخواه) با اجزای قابل انتخاب ([Types]+[Components])
;   * میان‌بر در منوی Start و روی دسکتاپ، با امکان انصراف کاربر
;   * ثبت کامل در «برنامه‌ها و قابلیت‌ها» ویندوز: نام، ناشر، نسخه، آیکن،
;     توضیح، نشانی وب و مسیر حذف نصب تمیز
;   * AppId ثابت: ارتقا و حذف نصب نسخهٔ قبل درست کار می‌کند
;   * [InstallDelete]: با ارتقا، فایل‌های کهنهٔ نسخهٔ قبل باقی نمی‌مانند
;   * بدون هیچ پنجرهٔ خط فرمان (CMD) — خروجی PyInstaller هم windowed است
; ---------------------------------------------------------------------------

#define MyAppName "مشاور هوشمند کنکور"
#define MyAppNameEn "K2 Konkur Advisor"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "K2 Team"
#define MyAppURL "https://github.com/rezaa2544/k2"
#define MyAppExeName "K2.exe"

; شناسهٔ پایدار برنامه. این GUID را هرگز تغییر ندهید؛ وگرنه ویندوز نسخهٔ
; نصب‌شده را نمی‌شناسد و ارتقا/حذف نصب خراب می‌شود.
#define MyAppId "{7C4E9A21-3B5D-4E8F-9A6C-1D2B3F4E5A60}"

[Setup]
AppId={#StringChange(MyAppId, '{', '{{')}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
; این‌ها در «برنامه‌ها و قابلیت‌ها» ویندوز دیده می‌شوند؛ نصب‌کنندهٔ استاندارد
; همهٔ آن‌ها را پر می‌کند.
AppComments=مشاور مطالعهٔ آفلاین و راست‌چین برای کنکور؛ برنامه‌ریزی روزانه و هفتگی، مرور تطبیقی و پیگیری تسلط
AppContact={#MyAppURL}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName}
VersionInfoProductName={#MyAppName}
VersionInfoCopyright=© 2026 K2 Team
DefaultDirName={autopf}\{#MyAppNameEn}
DefaultGroupName={#MyAppName}
; صفحهٔ انتخاب پوشهٔ منوی Start باید دیده شود؛ مثل هر نصب‌کنندهٔ استاندارد،
; کاربر حق دارد پوشهٔ میان‌برها را عوض کند.
DisableProgramGroupPage=no
; اگر کاربر هیچ پوشهٔ منوی Start نخواهد، این حق را دارد. این گزینه فقط روی
; میان‌برهای {group} اثر دارد؛ میان‌بر میزکار تسک خودش را دارد.
AllowNoIcons=yes
; نصب خاموش (CI) و نصب عادی هر دو باید میان‌بر بسازند. با AllowNoIcons=yes
; گزینهٔ «پوشهٔ Start Menu نساز» وجود دارد و در نصب خاموش، پیش‌فرض‌ها بر
; جای می‌مانند.
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=output
OutputBaseFilename=K2-Setup-{#MyAppVersion}
SetupIconFile=..\src\k2\ui\assets\k2.ico
; توافق‌نامهٔ استفاده؛ صفحهٔ پذیرش آن مثل همهٔ نصب‌کننده‌ها دیده می‌شود.
LicenseFile=EULA.txt
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
DisableWelcomePage=no
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
; ورودی رجیستری «برنامه‌ها و قابلیت‌ها» باید اندازهٔ تخمینی و نشانی وب را
; هم داشته باشد؛ Inno این‌ها را خودش می‌نویسد ولی باید AllowNoIcons و
; CreateUninstallRegKey فعال باشند.
CreateUninstallRegKey=yes
Uninstallable=yes
UpdateUninstallLogName=yes
CloseApplications=yes
RestartApplications=no
AppMutex=K2KonkurAdvisorMutex,Global\K2KonkurAdvisorMutex

[Languages]
Name: "farsi"; MessagesFile: "innosetup\Languages\Farsi.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

; توضیح: [Messages] اینجا عمداً خالی است. قبلاً چند پیام فارسی اینجا با
; پیشوند farsi. بازنویسی می‌شد؛ حالا همهٔ پیام‌ها در Farsi.isl هستند تا یک
; منبع واحد برای ترجمه باشد و هیچ صفحه‌ای به انگلیسی برنگردد.

[Types]
; صفحهٔ گونهٔ نصب. «دلخواه» با iscustom، انتخاب دستی اجزا را باز می‌کند.
Name: "full"; Description: "نصب کامل"
Name: "custom"; Description: "نصب دلخواه"; Flags: iscustom

[Components]
; برنامه خودش الزامی است؛ مستندات اختیاری است تا کاربر بتواند نصب سبک‌تری
; بگیرد. هر دو در صفحهٔ گونهٔ نصب انتخاب می‌شوند.
Name: "main"; Description: "برنامهٔ مشاور هوشمند کنکور (اجباری)"; Types: full custom; Flags: fixed
Name: "docs"; Description: "راهنمای کاربر و مستندات"; Types: full

[Tasks]
; توجه: در [Tasks] فلگ checked وجود ندارد — تسک به‌صورت پیش‌فرض انتخاب
; شده است و فقط unchecked می‌تواند آن را خاموش کند. گذاشتن checked
; خطای کامپایل می‌دهد.
Name: "desktopicon"; Description: "ساخت میان‌بر روی دسکتاپ"; GroupDescription: "میان‌برها:"
Name: "desktopicon\common"; Description: "برای همهٔ کاربران این رایانه"; GroupDescription: "میان‌برها:"; Flags: exclusive
Name: "desktopicon\user"; Description: "فقط برای من"; GroupDescription: "میان‌برها:"; Flags: unchecked exclusive

[Files]
; کل خروجی PyInstaller (K2.exe + پوشهٔ _internal) به‌صورت کامل کپی می‌شود.
Source: "output\K2\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
; نکته: فایل‌های داده و فونت‌ها داخل _internal هستند و همین یک خط آن‌ها را
; هم می‌آورد؛ پس هیچ فایلی دستی اضافه نمی‌شود.

; راهنمای کاربر: یک فایل HTML خودبسنده. چرا HTML و نه Markdown: ویندوز
; به‌صورت پیش‌فرض برنامه‌ای برای .md ندارد و باز کردنش می‌شکند، ولی HTML را
; همیشه با مرورگر پیش‌فرض باز می‌کند. فایل آفلاین است و هیچ پیوند بیرونی
; ندارد تا بدون اینترنت خوانده شود.
Source: "USER_GUIDE.html"; DestDir: "{app}\docs"; Flags: ignoreversion; Components: docs

[Icons]
; میان‌برهای Start Menu هیچ Tasks ندارند، پس همیشه ساخته می‌شوند — حتی در
; نصب خاموش. میان‌بر میزکار به تسک desktopicon وابسته است و CI آن را با
; /MERGETASKS=desktopicon صریحاً انتخاب می‌کند.
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\حذف نصب {#MyAppName}"; Filename: "{uninstallexe}"
; راهنمای کاربر کنار میان‌بر برنامه، تا از همان منوی Start قابل خواندن باشد.
Name: "{group}\راهنمای کاربر"; Filename: "{app}\docs\USER_GUIDE.html"; Components: docs
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "اجرای {#MyAppName}"; Flags: nowait postinstall skipifsilent
; خواندن راهنما از صفحهٔ پایان، مثل نصب‌کننده‌های استاندارد. unchecked
; یعنی کاربر خودش تیک می‌زند؛ کسی راهنما را اجباراً روی صورتش باز نمی‌کند.
Filename: "{app}\docs\USER_GUIDE.html"; Description: "خواندن راهنمای کاربر"; Flags: nowait postinstall skipifsilent shellexec unchecked; Components: docs

[UninstallDelete]
; پوشهٔ دادهٔ کاربر حذف نمی‌شود؛ فقط فایل‌های نصب‌شدهٔ برنامه پاک می‌شوند.
Type: filesandordirs; Name: "{app}"

[InstallDelete]
; ارتقای تمیز: پوشهٔ مستندات نسخهٔ قبل پیش از کپی فایل‌های تازه پاک می‌شود.
; بدون این، اگر کاربر این بار جزء «راهنمای کاربر» را بردارد، فایل کهنه روی
; دیسک می‌ماند. دادهٔ کاربر در این پوشه نیست، پس این کار با اطلاعات کاربر
; کاری ندارد؛ پوشهٔ دادهٔ کاربر فقط با حذف نصب دست‌نخورده می‌ماند.
Type: filesandordirs; Name: "{app}\docs"

; نکته: بخش [Code] عمداً حذف شده است. در آن یک CheckForMutexes روی GUID بود
; که هیچ فرایندی آن mutex را نمی‌ساخت، پس همیشه False برمی‌گرداند و بی‌اثر
; بود — اسکریپت چیزی را ادعا می‌کرد که انجام نمی‌داد. «برنامهٔ در حال اجرا»
; را خودِ Inno به‌صورت بومی می‌گیرد: AppMutex نام mutex مشترکی را اعلام
; می‌کند که src/k2/app.py واقعاً می‌سازد، و CloseApplications=yes فایل
; قفل‌شدهٔ K2.exe را می‌بندد.
