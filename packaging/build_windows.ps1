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

Write-Step "اجرای واقعی EXE (حالت headless)"
# build موفق به‌معنی اجرای موفق نیست؛ این مرحله باید یک کد خروج صفر بدهد.
$SmokeDb = Join-Path $WorkDir 'smoke.db'
$smokeLog = & $Exe --db $SmokeDb --headless 2>&1
$smokeExit = $LASTEXITCODE
$smokeLog | ForEach-Object { Write-Host "    $_" }
if ($smokeExit -ne 0) { throw "اجرای EXE با exit=$smokeExit شکست خورد." }
Write-Ok "EXE اجرا شد و کد خروج صفر داد."

Write-Step "خلاصه"
Write-Host "خروجی : $OutputDir"
Write-Host "EXE   : $Exe"
Write-Host "اندازه : $((Get-Item $Exe).Length) بایت"
Write-Host "`nگام‌های باقی‌مانده برای انتشار:"
Write-Host "  1) امضای دیجیتال کد با گواهی Code Signing (اختیاری ولی توصیه‌شده)"
Write-Host "  2) ساخت نصب‌کننده با Inno Setup از همین پوشه (اختیاری)"
Write-Host "  3) آزمون روی ویندوز تمیز ۱۰/۱۱ (بدون پایتون نصب‌شده)"
Write-Host "  4) انتشار در GitHub Releases"
