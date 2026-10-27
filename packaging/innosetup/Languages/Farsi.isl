; ---------------------------------------------------------------------------
; فایل زبان فارسی کامل برای Inno Setup 6
;
; چرا کامل: Inno Setup برای هر پیامی که در فایل زبان نباشد، به‌صورت خودکار به
; زبان انگلیسی برمی‌گردد. نتیجه یک نصب‌کنندهٔ «نیمهٔ فارسی» است که بعضی صفحه‌ها
; فارسی و بعضی انگلیسی‌اند. این فایل همهٔ پیامی را پوشش می‌دهد که جادوارهای
; این نصب‌کننده نمایش داده می‌شوند، تا هیچ صفحه‌ای انگلیسی نماند.
;
; نکته: [Messages] فقط پیام‌های استاندارد Inno Setup 6 را می‌پذیرد. کلید
; ناشناخته در زمان کامپایل نادیده گرفته می‌شود، نه اینکه خطا بدهد.
; ---------------------------------------------------------------------------

[LangOptions]
LanguageName=فارسی
LanguageID=$0429
LanguageCodePage=1256
RightToLeft=yes

[Messages]

; --- عنوان پنجره‌ها و منوی «درباره» ---
SetupAppTitle=نصب برنامه
SetupWindowTitle=نصب %1
UninstallAppTitle=حذف نصب برنامه
UninstallAppFullTitle=حذف نصب %1

AboutSetupMenuItem=دربارهٔ نصب‌کننده...
AboutSetupTitle=دربارهٔ نصب‌کننده
AboutSetupMessage=%1 نسخهٔ %2%n%n%1 صفحهٔ اصلی:%n%3

; --- دکمه‌ها ---
ClickNext=بعدی >
ClickInstall=نصب
ClickFinish=پایان
ClickCancel=انصراف
ClickOK=تأیید
ClickYes=بله
ClickYesToAll=بله به همه
ClickNo=خیر
ClickNoToAll=خیر به همه
ClickBrowse=مرور...
ClickWizardBrowse=مرور...
ClickNewFolder=پوشهٔ جدید

ButtonBack=< بازگشت
ButtonNext=بعدی >
ButtonInstall=نصب
ButtonOK=تأیید
ButtonCancel=انصراف
ButtonYes=بله
ButtonYesToAll=بله به همه
ButtonNo=خیر
ButtonNoToAll=خیر به همه
ButtonBrowse=مرور...
ButtonWizardBrowse=مرور...
ButtonNewFolder=پوشهٔ جدید
ButtonFinish=پایان

; --- خروج و قطع نصب ---
ExitSetupTitle=خروج از نصب‌کننده
ExitSetupMessage=نصب کامل نشده است. اگر حالا خارج شوید، برنامه نصب نخواهد شد.%n%nمی‌توانید این نصب‌کننده را دوباره اجرا کنید تا نصب کامل شود.%n%nخارج می‌شوید？

; --- انتخاب زبان ---
SelectLanguageTitle=زبان نصب‌کننده
SelectLanguageLabel=زبانی که هنگام نصب استفاده می‌شود انتخاب کنید:

; --- صفحهٔ خوش‌آمد ---
WelcomeLabel1=به نصب‌کنندهٔ [name] خوش آمدید
WelcomeLabel2=این برنامه [name/ver] را روی رایانهٔ شما نصب می‌کند.%n%nپیش از شروع، توصیه می‌کنیم همهٔ برنامه‌های دیگر را ببندید.

; --- صفحهٔ گذرواژه ---
PasswordTitle=گذرواژهٔ نصب
PasswordDescription=این نصب‌کننده با گذرواژه محافظت شده است.
PasswordEditLabel=گذرواژه:
PasswordIncorrectPassword=گذرواژه درست نیست. دوباره تلاش کنید.

; --- صفحهٔ توافق‌نامه ---
WizardLicense=توافق‌نامهٔ استفاده
LicenseLabel3=لطفاً این اطلاعات را قبل از ادامه بخوانید.
LicenseAccepted=توافق‌نامه را می‌پذیرم
LicenseNotAccepted=توافق‌نامه را نمی‌پذیرم

; --- صفحهٔ اطلاعات پیش از نصب ---
WizardInfoBefore=اطلاعات پیش از نصب
InfoBeforeLabel=لطفاً این اطلاعات را قبل از ادامه بخوانید.
InfoBeforeClickLabel=برای ادامه، «بعدی» را بزنید.

; --- صفحهٔ اطلاعات کاربر ---
WizardUserInfo=اطلاعات کاربر
UserInfoDesc=اطلاعات خود را وارد کنید:
UserInfoName=نام کاربر:
UserInfoOrg=سازمان:
UserInfoSerial=شمارهٔ سریال:
UserInfoNameRequired=باید یک نام وارد کنید.

; --- صفحهٔ پوشهٔ مقصد ---
WizardSelectDir=انتخاب پوشهٔ مقصد
SelectDirDesc=نرم‌افزار کجا نصب شود؟
SelectDirLabel3=نصب‌کننده، [name] را در این پوشه نصب می‌کند.
SelectDirBrowseLabel=برای ادامه، «بعدی» را بزنید. برای انتخاب پوشهٔ دیگر، «مرور...» را بزنید.
DiskSpaceMBLabel=حداقل [mb] مگابایت فضای خالی لازم است.
CannotInstallToNetworkDrive=نصب‌کننده نمی‌تواند روی درایو شبکه نصب کند. یک درایو محلی انتخاب کنید.
CannotInstallToUNCPath=نصب‌کننده نمی‌تواند روی مسیر UNC نصب کند. یک درایو محلی انتخاب کنید.
InvalidPath=باید مسیر کامل با حرف درایو وارد شود؛ مثلاً:%n%nC:\Program Files\K2
InvalidDrive=درایو یا اشتراک UNC انتخاب‌شده وجود ندارد یا در دسترس نیست. یک درایو دیگر انتخاب کنید.
DiskSpaceWarningTitle=فضای کافی نیست
DiskSpaceWarning=نصب نیاز به حداقل %1 کیلوبایت فضای خالی دارد، اما درایو انتخاب‌شده فقط %2 کیلوبایت فضای خالی دارد.%n%nبا این حال ادامه می‌دهید؟
DirNameTooLong=نام پوشه یا مسیر آن بیش از حد بلند است.
InvalidDirName=نام پوشه معتبر نیست.
BadDirName32=نام پوشه نباید هیچ‌یک از این نویسه‌ها را داشته باشد:%n%n%1
DirExistsTitle=پوشه وجود دارد
DirExists=پوشهٔ «%1» از قبل وجود دارد.%n%nبا این حال در آن پوشه نصب شود؟
DirDoesntExistTitle=پوشه وجود ندارد
DirDoesntExist=پوشهٔ «%1» وجود ندارد. این پوشه ساخته شود؟

; --- صفحهٔ اجزا و گونهٔ نصب ---
WizardSelectComponents=انتخاب اجزا
SelectComponentsDesc=کدام اجزا نصب شوند؟
SelectComponentsLabel2=اجزایی که نصب می‌شوند را انتخاب کنید و مواردی که نمی‌خواهید بردارید.
SelectComponentsGroupLabel=اجزا:
TypesGroupLabel=گونهٔ نصب:
ComponentsDiskSpaceLabel=برای انتخاب‌های کنونی حداقل [mb] مگابایت فضای لازم است.
FullInstallation=نصب کامل
CompactInstallation=نصب فشرده
CustomInstallation=نصب دلخواه
TypicalInstallation=نصب معمول
NoIconsInstall=فقط برنامه، بدون میان‌بر
DeveloperInstall=نصب توسعه‌دهنده
ServerInstall=نصب سرور

; --- صفحهٔ پوشهٔ منوی Start ---
WizardSelectProgramGroup=انتخاب پوشهٔ منوی Start
SelectStartMenuFolderDesc=میان‌برها کجا گذاشته شوند؟
SelectStartMenuFolderLabel3=نصب‌کننده، میان‌برهای برنامه را در این پوشهٔ منوی Start می‌گذارد.
SelectStartMenuFolderBrowseLabel=برای ادامه، «بعدی» را بزنید. برای انتخاب پوشهٔ دیگر، «مرور...» را بزنید.
MustEnterGroupName=باید یک نام پوشه وارد کنید.
GroupNameTooLong=نام پوشه یا مسیر آن بیش از حد بلند است.
GroupNameInvalid=نام پوشه معتبر نیست.
BadGroupName=نام پوشه نباید هیچ‌یک از این نویسه‌ها را داشته باشد:%n%n%1
NoProgramGroupCheck2=هیچ پوشه‌ای در منوی Start ساخته نشود

; --- صفحهٔ کارهای افزودنی ---
WizardSelectTasks=انتخاب کارهای افزودنی
SelectTasksDesc=کدام کارهای افزودنی هنگام نصب انجام شود؟
SelectTasksLabel2=کارهای افزودنی که هنگام نصب انجام شوند را انتخاب کنید:
SelectTasksGroupLabel=کارهای افزودنی:

; --- صفحهٔ آماده‌باش نصب ---
WizardReady=آمادهٔ نصب
ReadyLabel1=نصب‌کننده آمادهٔ نصب [name] روی رایانهٔ شماست.
ReadyLabel2a=برای شروع نصب، «نصب» را بزنید. برای بازبینی یا تغییر تنظیمات، «بازگشت» را بزنید.
ReadyLabel2b=برای شروع نصب، «نصب» را بزنید.
ReadyMemoType=گونهٔ نصب:
ReadyMemoComponents=اجزای انتخاب‌شده:
ReadyMemoGroup=پوشهٔ منوی Start:
ReadyMemoTasks=کارهای افزودنی:
ReadyMemoDir=پوشهٔ مقصد:

; --- آماده‌سازی و نصب ---
WizardPreparing=آماده‌سازی
PreparingLabel=در حال آماده‌سازی نصب [name]...
PreparingDesc=نصب‌کننده در حال آماده‌سازی روی رایانهٔ شماست.

WizardInstalling=در حال نصب
InstallingLabel=لطفاً صبر کنید تا [name] نصب شود.

; --- صفحهٔ پایان ---
WizardFinished=پایان نصب
FinishedHeadingLabel=پایان نصب [name]
FinishedLabel=نصب [name] کامل شد. برنامه را از میان‌برهای ساخته‌شده باز کنید.
FinishedLabelNoIcons=نصب [name] کامل شد.

; --- تأیید حذف نصب ---
ConfirmTitle=تأیید
ConfirmUninstall=آیا از حذف نصب کامل %1 و همهٔ اجزای آن مطمئنید؟
ConfirmUninstallYes=بله، حذف نصب شود
ConfirmUninstallNo=خیر، نگه دار

UninstalledAll=%1 با موفقیت حذف نصب شد.
UninstalledMost=حذف نصب %1 کامل شد.%n%nبعضی اجزا را نصب‌کننده نتوانست حذف کند؛ می‌توانید خودتان آن‌ها را پاک کنید.
UninstalledAndNeedsRestart=برای کامل شدن حذف نصب %1، رایانه باید دوباره راه‌اندازی شود.%n%nحالا راه‌اندازی مجدد شود؟
UninstallDataCorrupted=فایل نصب‌شده معتبر نیست؛ حذف نصب انجام نشد.

; --- عنوان‌های صفحه‌های حذف نصب ---
WizardUninstalling=در حال حذف نصب
UninstallingLabel=لطفاً صبر کنید تا %1 حذف نصب شود.
StatusUninstalling=در حال حذف نصب %1

; --- نوار وضعیت ---
StatusLabel=لطفاً صبر کنید:
StatusExtractFiles=استخراج فایل‌ها
StatusCreateIcons=ساخت میان‌برها
StatusCreateIniEntries=ساخت ورودی‌های INI
StatusRunProgram=پایان نصب؛ اجرای %1
StatusRegisterFiles=ثبت فایل‌ها
StatusUnregisterFiles=لغو ثبت فایل‌ها
StatusSavingUninstall=ذخیرهٔ اطلاعات حذف نصب
StatusRollback=بازگرداندن تغییرات

; --- خطاها ---
ErrorTitle=خطا
ErrorCreatingDir=نصب‌کننده نتوانست پوشهٔ «%1» را بسازد.
ErrorRegisterOcx=خطا در ثبت DLL/OCX:%n%1
ErrorWritingFile=خطا در نوشتن فایل:%n%1
ErrorRegisterServer=نصب‌کننده نتوانست فایل را ثبت کند:%n%1
ErrorRegSvr32Failed=دستور regsvr32 با کد خروج %1 شکست خورد.
ErrorRegisterTypeLib=نصب‌کننده نتوانست کتابخانهٔ نوع را ثبت کند:%n%1
ErrorUnregisterTypeLib=نصب‌کننده نتوانست ثبت کتابخانهٔ نوع را لغو کند:%n%1
ErrorUnregisterServer=نصب‌کننده نتوانست فایل را از ثبت خارج کند:%n%1
ErrorUnregSvr32Failed=دستور regsvr32 /u با کد خروج %1 شکست خورد.
ErrorCreatingTemp=نصب‌کننده نتوانست فایلی را در پوشهٔ مقصد بسازد:%n%1
ErrorReadingSource=نصب‌کننده نتوانست فایل منبع را بخواند:%n%1
ErrorCopying=نصب‌کننده نتوانست فایل را کپی کند:%n%1
ErrorReplacingExistingFile=نصب‌کننده نتوانست فایل موجود را جایگزین کند:%n%1
ErrorRestartReplace=جایگزینی پس از راه‌اندازی مجدد انجام نشد:%n%1
ErrorRenamingTemp=نصب‌کننده نتوانست فایلی را در پوشهٔ مقصد تغییر نام دهد:%n%1
ErrorRegisterServerMissingExport=سرور نمی‌تواند DllRegisterServer را صادر کند.
ErrorOpeningReadme=نصب‌کننده نتوانست فایل «خواندمه» را باز کند:%n%1
ErrorRestartingComputer=نصب‌کننده نتوانست رایانه را دوباره راه‌اندازی کند. این کار را خودتان انجام دهید.
ErrorFatal=نصب به‌دلیل خطای زیر متوقف شد:%n%1
ErrorInternal=خطای داخلی (%1)
ErrorInternal2=خطای داخلی: %1
ErrorFunctionFailedNoCode=%1 شکست خورد.
ErrorFunctionFailedWithCode=%1 شکست خورد؛ کد %2.

; --- خطاهای معماری و نسخهٔ ویندوز ---
OnlyOnThisArch=این برنامه فقط روی ویندوز ۶۴ بیتی نصب می‌شود.
OnlyOnTheseArchitectures=این برنامه فقط روی این معماری‌های ویندوز نصب می‌شود:%n%n%1
WinVersionTooLowError=این برنامه نیاز به %1 نسخهٔ %2 یا بالاتر دارد.%n%nرایانهٔ شما %3 نسخهٔ %4 را اجرا می‌کند.
WinVersionTooHighError=این برنامه روی %1 نسخهٔ %2 یا بالاتر نصب نمی‌شود.%n%nرایانهٔ شما %3 نسخهٔ %4 را اجرا می‌کند.
MissingWOW64APIs=این نصب‌کننده برای اجرا روی ویندوز ۶۴ بیتی به امکاناتی نیاز دارد که در نسخهٔ فعلی سیستم شما موجود نیست. برای رفع مشکل، بستهٔ سرویس پک %1 را نصب کنید.

; --- انتخاب دسترسی (مدیر / کاربر کنونی) ---
PrivilegesRequiredOverrideTitle=انتخاب حالت نصب
PrivilegesRequiredInstruction=این برنامه را چطور نصب می‌کنید؟
PrivilegesRequiredOverrideModeApplication=نصب برای همهٔ کاربران این رایانه (نیازمند دسترسی مدیر)
PrivilegesRequiredOverrideModeCurrentUser=نصب فقط برای کاربر کنونی من

; --- مرورگر پوشه و تأیید حذف فایل ---
BrowseDialogTitle=مرور برای پوشه
BrowseDialogLabel=یک پوشه از فهرست زیر انتخاب کنید، سپس «تأیید» را بزنید.
NewFolderName=پوشهٔ جدید
DeletePrompt=فایل «%1» حذف شود؟
SelectAllLabel=انتخاب همه
DeselectAllLabel=لغو انتخاب همه

; --- نشانه‌گذاری انتخابی در فهرست‌ها ---

; --- پیام‌های مربوط به میان‌برها ---
