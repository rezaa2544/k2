; ---------------------------------------------------------------------------
; نصب‌کنندهٔ استاندارد ویندوز برای «مشاور هوشمند کنکور» (K2)
;
; این اسکریپت با Inno Setup 6 ساخته می‌شود (روی runner ویندوز موجود است):
;     iscc packaging\k2_installer.iss
;
; مسیرهای نسبی نسبت به پوشهٔ همین فایل حل می‌شوند (packaging/)، نه نسبت به
; پوشه‌ای که iscc از آن اجرا شده. پس output\K2 یعنی packaging\output\K2.
;
; چه چیزی «استاندارد» می‌کند:
;   * نصب در Program Files با دسترسی مدیر (PrivilegesRequired=admin)
;   * میان‌بر در منوی Start و روی دسکتاپ
;   * ثبت در «برنامه‌ها و قابلیت‌ها» ویندوز با امکان حذف نصب تمیز
;   * AppId ثابت: ارتقا و حذف نصب نسخهٔ قبل درست کار می‌کند
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
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName}
VersionInfoProductName={#MyAppName}
DefaultDirName={autopf}\{#MyAppNameEn}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; نصب خاموش (CI) و نصب عادی هر دو باید میان‌بر بسازند. با AllowNoIcons=yes
; گزینهٔ «پوشهٔ Start Menu نساز» وجود دارد و در نصب خاموش رفتارش معلوم نیست.
AllowNoIcons=no
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=output
OutputBaseFilename=K2-Setup-{#MyAppVersion}
SetupIconFile=..\src\k2\ui\assets\k2.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
DisableWelcomePage=no
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
RestartApplications=no
AppMutex=K2KonkurAdvisorMutex,Global\K2KonkurAdvisorMutex

[Languages]
Name: "farsi"; MessagesFile: "innosetup\Languages\Farsi.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
; متن فارسی برای صفحهٔ خوش‌آمد و پایان، حتی اگر فایل زبان کامل نباشد.
farsi.WelcomeLabel1=به نصب‌کنندهٔ {#MyAppName} خوش آمدید
farsi.WelcomeLabel2=این برنامه {#MyAppName} را روی رایانهٔ شما نصب می‌کند.%n%nپیش از شروع، توصیه می‌شود همهٔ برنامه‌های دیگر را ببندید.
farsi.FinishedHeadingLabel=نصب {#MyAppName} کامل شد
farsi.FinishedLabel=نصب کامل شد. برنامه را از میان‌برهای ساخته‌شده باز کنید.
farsi.ClickInstall=نصب

[Tasks]
; توجه: در [Tasks] فلگ checked وجود ندارد — تسک به‌صورت پیش‌فرض انتخاب
; شده است و فقط unchecked می‌تواند آن را خاموش کند. گذاشتن checked
; خطای کامپایل می‌دهد.
Name: "desktopicon"; Description: "ساخت میان‌بر روی دسکتاپ"; GroupDescription: "میان‌برها:"
Name: "desktopicon\common"; Description: "برای همهٔ کاربران این رایانه"; GroupDescription: "میان‌برها:"; Flags: exclusive
Name: "desktopicon\user"; Description: "فقط برای من"; GroupDescription: "میان‌برها:"; Flags: unchecked exclusive

[Files]
; کل خروجی PyInstaller (K2.exe + پوشهٔ _internal) به‌صورت کامل کپی می‌شود.
Source: "output\K2\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; نکته: فایل‌های داده و فونت‌ها داخل _internal هستند و همین یک خط آن‌ها را
; هم می‌آورد؛ پس هیچ فایلی دستی اضافه نمی‌شود.

[Icons]
; میان‌برهای Start Menu هیچ Tasks ندارند، پس همیشه ساخته می‌شوند — حتی در
; نصب خاموش. میان‌بر میزکار به تسک desktopicon وابسته است و CI آن را با
; /MERGETASKS=desktopicon صریحاً انتخاب می‌کند.
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\حذف نصب {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "اجرای {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; پوشهٔ دادهٔ کاربر حذف نمی‌شود؛ فقط فایل‌های نصب‌شدهٔ برنامه پاک می‌شوند.
Type: filesandordirs; Name: "{app}"

[Code]
// اگر نسخهٔ قبلی در حال اجرا باشد، نصب‌کننده نمی‌تواند فایل‌ها را بنویسد.
function InitializeSetup(): Boolean;
begin
  Result := True;
  if CheckForMutexes('{#MyAppId}') then
  begin
    if MsgBox('برنامهٔ «{#MyAppName}» در حال اجراست.' + #13#10 +
              'لطفاً آن را ببندید و دوباره «تأیید» را بزنید.', mbConfirmation, MB_OKCANCEL) = IDCANCEL then
      Result := False;
  end;
end;
