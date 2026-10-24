<#
.SYNOPSIS
    ساخت اجرایی ویندوزی «مشاور هوشمند کنکور» (K2).

.DESCRIPTION
    این اسکریپت باید روی ویندوز ۱۰/۱۱ اجرا شود. یک محیط مجازی مستقل
    Python می‌سازد، وابستگی‌ها را نصب می‌کند، تست‌ها را اجرا می‌کند و سپس
    با PyInstaller خروجی را در packaging/output/K2 می‌سازد.

    نکتهٔ مهم: build موفق به‌معنی اجرای موفق نیست. اسکریپت پس از ساخت،
    اجرای واقعی EXE را در حالت --headless (بدون نمایشگر) بررسی می‌کند و
    در صورت شکست، خطا برمی‌گرداند.

.PARAMETER SkipTests
    اجرای تست‌ها را رد می‌کند (توصیه نمی‌شود).

.PARAMETER Clean
    پیش از ساخت، پوشه‌های build/dist را پاک می‌کند.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\packaging\build_windows.ps1
#>

[CmdletBinding()]
param(
    [switch]$SkipTests,
    [switch]$Clean
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot   = Split-Path -Parent $PSScriptRoot
$ProjectDir = Join-Path $RepoRoot 'packaging'
$OutputDir  = Join-Path $ProjectDir 'output'
$WorkDir    = Join-Path $ProjectDir 'work'
$VenvDir    = Join-Path $WorkDir 'venv'
$SpecFile   = Join-Path $RepoRoot 'k2.spec'

function Write-Step { param([string]$Text) Write-Host "`n=== $Text ===" -ForegroundColor Cyan }
function Write-Ok   { param([string]$Text) Write-Host "[OK] $Text" -ForegroundColor Green }
function Write-Warn { param([string]$Text) Write-Host "[WARN] $Text" -ForegroundColor Yellow }

Write-Step "بررسی پیش‌نیازها"
$python = $null
foreach ($candidate in @('py -3.12', 'py -3.11', 'python')) {
    try {
        $ver = & cmd /c "$candidate --version 2>&1"
        if ($LASTEXITCODE -eq 0) { $python = $candidate; break }
    } catch { }
}
if (-not $python) { throw "پایتون ۳.۱۱+ پیدا نشد. 'py -3.12' یا 'python' را در PATH قرار دهید." }
Write-Ok "پایتون: $python (& $python --version 2>&1)"

if ($Clean) {
    Write-Step "پاک‌سازی خروجی‌های قبلی"
    foreach ($path in @($OutputDir, $WorkDir, (Join-Path $RepoRoot 'build'), (Join-Path $RepoRoot 'dist'))) {
        if (Test-Path $path) { Remove-Item -Recurse -Force $path; Write-Ok "حذف $path" }
    }
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
New-Item -ItemType Directory -Force -Path $WorkDir  | Out-Null

Write-Step "ساخت محیط مجازی"
if (-not (Test-Path (Join-Path $VenvDir 'Scripts\python.exe'))) {
    & cmd /c "$python -m venv `"$VenvDir`""
    if ($LASTEXITCODE -ne 0) { throw "ساخت venv ناموفق بود." }
}
$VenvPy = Join-Path $VenvDir 'Scripts\python.exe'
Write-Ok "محیط مجازی: $VenvPy"

Write-Step "نصب وابستگی‌ها"
& $VenvPy -m pip install --upgrade pip | Out-Null
& $VenvPy -m pip install -r (Join-Path $RepoRoot 'requirements.txt')
& $VenvPy -m pip install -r (Join-Path $RepoRoot 'requirements-dev.txt')
& $VenvPy -m pip install "pyinstaller>=6.0"
if ($LASTEXITCODE -ne 0) { throw "نصب وابستگی‌ها ناموفق بود." }
Write-Ok "وابستگی‌ها نصب شدند."

if (-not $SkipTests) {
    Write-Step "اجرای تست‌ها"
    Push-Location $RepoRoot
    $env:PYTHONPATH = Join-Path $RepoRoot 'src'
    $env:QT_QPA_PLATFORM = 'offscreen'
    & $VenvPy -m pytest tests -q
    $testExit = $LASTEXITCODE
    Pop-Location
    if ($testExit -ne 0) { throw "تست‌ها پاس نشدند (exit=$testExit). ساخت متوقف شد." }
    Write-Ok "همهٔ تست‌ها پاس شدند."
} else {
    Write-Warn "اجرای تست‌ها طبق درخواست رد شد."
}

Write-Step "ساخت با PyInstaller"
Push-Location $RepoRoot
$env:PYTHONPATH = Join-Path $RepoRoot 'src'
& $VenvPy -m PyInstaller $SpecFile --noconfirm --distpath $OutputDir --workpath $WorkDir
$buildExit = $LASTEXITCODE
Pop-Location
if ($buildExit -ne 0) { throw "PyInstaller با exit=$buildExit شکست خورد." }

$Exe = Join-Path $OutputDir 'K2\K2.exe'
if (-not (Test-Path $Exe)) { throw "EXE ساخته نشد: $Exe" }
Write-Ok "EXE ساخته شد: $Exe"

Write-Step "بررسی نشستن آیکن روی EXE"
# «مسیر آیکن داده شده» به‌معنای «آیکن روی EXE نشسته» نیست. اگر فایل نباشد یا
# PyInstaller آن را جا ندهد، build موفق می‌شود ولی کاربر آیکن پیش‌فرض را می‌بیند.
$Icon = Join-Path $RepoRoot "src\k2\ui\assets\k2.ico"
if (-not (Test-Path $Icon)) { throw "فایل آیکن پیدا نشد: $Icon" }
& $VenvPy (Join-Path $RepoRoot "packaging\verify_exe_icon.py") $Exe $Icon
if ($LASTEXITCODE -ne 0) { throw "آیکن برنامه داخل EXE نشسته نیست (exit=$LASTEXITCODE)." }
Write-Ok "آیکن برنامه داخل EXE نشسته است."

Write-Step "اجرای واقعی EXE (حالت headless)"
# خروجی PyInstaller این پروژه windowed است؛ Start-Process کد خروج را
# مستقل از نوع GUI/console فایل EXE به‌درستی برمی‌گرداند.
$SmokeDb = Join-Path $WorkDir 'smoke.db'
$SmokeStdout = Join-Path $WorkDir 'smoke.stdout.txt'
$SmokeStderr = Join-Path $WorkDir 'smoke.stderr.txt'
Remove-Item $SmokeDb, $SmokeStdout, $SmokeStderr -Force -ErrorAction SilentlyContinue
$SmokeArguments = "--db `"$SmokeDb`" --headless"
$SmokeProcess = Start-Process -FilePath $Exe -ArgumentList $SmokeArguments -PassThru -Wait `
    -RedirectStandardOutput $SmokeStdout -RedirectStandardError $SmokeStderr
$smokeExit = $SmokeProcess.ExitCode
foreach ($LogFile in @($SmokeStdout, $SmokeStderr)) {
    if (Test-Path $LogFile) { Get-Content $LogFile | ForEach-Object { Write-Host "    $_" } }
}
if ($smokeExit -ne 0) { throw "اجرای EXE با exit=$smokeExit شکست خورد." }
if (-not (Test-Path $SmokeDb)) { throw "EXE پایگاه دادهٔ smoke test را نساخت." }
Write-Ok "EXE اجرا شد، پایگاه داده ساخت و کد خروج صفر داد."

Write-Step "امضای دیجیتال (اختیاری)"
# اگر گواهی در محیط تنظیم شده باشد امضا می‌کنیم؛ وگرنه با اعلام صریح رد می‌شویم.
function Get-Signtool {
  $cmd = Get-Command signtool -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  foreach ($root in @("${env:ProgramFiles(x86)}", "$env:ProgramFiles")) {
    foreach ($kit in (Get-ChildItem (Join-Path $root "Windows Kits\10\bin") -Directory -ErrorAction SilentlyContinue |
                      Sort-Object Name -Descending)) {
      foreach ($arch in @("x64", "x86")) {
        $candidate = Join-Path $kit.FullName "$arch\signtool.exe"
        if (Test-Path $candidate) { return $candidate }
      }
    }
  }
  return $null
}
$PfxPath = $env:K2_CERTIFICATE_PFX
if (-not $PfxPath) {
  Write-Warn "K2_CERTIFICATE_PFX تنظیم نشده؛ artifact بدون امضا می‌ماند (هشدار SmartScreen)."
} elseif (-not (Test-Path $PfxPath)) {
  throw "K2_CERTIFICATE_PFX به فایل غیرموجود اشاره می‌کند: $PfxPath"
} else {
  $signtool = Get-Signtool
  if (-not $signtool) { throw "signtool پیدا نشد." }
  & $signtool sign /f $PfxPath /p $env:K2_CERTIFICATE_PASSWORD /fd SHA256 `
    /tr "http://timestamp.digicert.com" /td SHA256 $Exe
  if ($LASTEXITCODE -ne 0) { throw "امضای K2.exe با exit=$LASTEXITCODE شکست خورد." }
  & $signtool verify /pa $Exe
  if ($LASTEXITCODE -ne 0) { throw "امضای K2.exe راستی‌آزمایی نشد." }
  Write-Ok "K2.exe امضا شد."
}

Write-Step "ساخت نصب‌کنندهٔ استاندارد (Inno Setup)"
# نصب‌کننده گام اجباری است: کاربر نباید ZIP را باز کند و دنبال K2.exe بگردد.
$Iscc = Get-Command iscc -ErrorAction SilentlyContinue
if (-not $Iscc) {
    foreach ($candidate in @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe")) {
        if (Test-Path $candidate) { $Iscc = Get-Item $candidate; break }
    }
}
if (-not $Iscc) { throw "Inno Setup پیدا نشد. از https://jrsoftware.org/isdl.php نصب کنید." }
Write-Ok "Inno Setup: $($Iscc.Source)"
& $Iscc.Source (Join-Path $RepoRoot 'packaging\k2_installer.iss')
if ($LASTEXITCODE -ne 0) { throw "ساخت نصب‌کننده با exit=$LASTEXITCODE شکست خورد." }
$Setup = Get-ChildItem -Path $OutputDir -Filter 'K2-Setup-*.exe' |
    Sort-Object LastWriteTime | Select-Object -Last 1
if (-not $Setup) { throw "فایل نصب‌کننده ساخته نشد." }
Write-Ok "نصب‌کننده ساخته شد: $($Setup.FullName) ($($Setup.Length) بایت)"

Write-Step "امضای نصب‌کننده (اختیاری)"
$PfxPath = $env:K2_CERTIFICATE_PFX
if ($PfxPath -and (Test-Path $PfxPath)) {
  $signtool = Get-Signtool
  & $signtool sign /f $PfxPath /p $env:K2_CERTIFICATE_PASSWORD /fd SHA256 `
    /tr "http://timestamp.digicert.com" /td SHA256 $Setup.FullName
  if ($LASTEXITCODE -ne 0) { throw "امضای نصب‌کننده با exit=$LASTEXITCODE شکست خورد." }
  & $signtool verify /pa $Setup.FullName
  if ($LASTEXITCODE -ne 0) { throw "امضای نصب‌کننده راستی‌آزمایی نشد." }
  Write-Ok "نصب‌کننده امضا شد."
} else {
  Write-Warn "نصب‌کننده بدون امضا می‌ماند."
}

Write-Step "خلاصه"
Write-Host "خروجی : $OutputDir"
Write-Host "EXE   : $Exe"
Write-Host "نصب‌کننده: $($Setup.FullName)"
Write-Host "اندازه : $((Get-Item $Exe).Length) بایت"
Write-Host "`nگام‌های باقی‌مانده برای انتشار:"
Write-Host "  1) امضای دیجیتال کد با گواهی Code Signing (اختیاری ولی توصیه‌شده)"
Write-Host "  2) آزمون نصب‌کنندهٔ ساخته‌شده روی ویندوز تمیز (بدون پایتون)"
Write-Host "  3) آزمون روی ویندوز تمیز ۱۰/۱۱ (بدون پایتون نصب‌شده)"
Write-Host "  4) انتشار در GitHub Releases"
