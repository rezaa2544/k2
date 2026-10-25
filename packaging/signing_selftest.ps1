#requires -Version 5.1
<#
.SYNOPSIS
    خودآزمایی خط لولهٔ امضای دیجیتال روی ویندوز.

.DESCRIPTION
    «امضای واقعی» نیاز به گواهی Code Signing دارد که فقط کاربر می‌تواند
    تهیه کند. ولی خودِ خط لوله — ساخت گواهی، امضا با signtool،
    راستی‌آزمایی با signtool و Get-AuthenticodeSignature، و پاک‌سازی —
    را می‌توان بدون آن آزمود.

    این اسکریپت یک گواهی خودامضای موقت می‌سازد، یک **کپی** از EXE را امضا
    و راستی‌آزمایی می‌کند، و بعد گواهی و کپی را کاملاً پاک می‌کند. پس
    فایل منتشرشده هرگز امضاشده نمی‌شود و هیچ اثری روی artifact نمی‌گذارد.

    چرا جدا از گردش‌کار اجرا می‌شود: New-SelfSignedCertificate روی بعضی
    runnerها آویزان می‌ماند. چون یک cmdlet است، از داخل گام Actions
    نمی‌توان آن را با مهلت زمانی محدود کرد. پس گردش‌کار این اسکریپت را
    به‌صورت یک فرprocess جدا و با مهلت زمانی اجرا می‌کند.

.PARAMETER ExePath
    مسیر EXE ساختهٔ PyInstaller.

.PARAMETER TimeoutSeconds
    مهلت کل عملیات (پیش‌فرض ۳۰۰ ثانیه).

.EXAMPLE
    pwsh -NoProfile -File packaging\signing_selftest.ps1 -ExePath packaging\output\K2\K2.exe
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ExePath,
    [int]$TimeoutSeconds = 300
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$script:StartedAt = Get-Date

function Note([string]$Message) {
    # ثانیهٔ سپری‌شده هم چاپ می‌شود تا اگر فرprocess آویزان شد، از لاگ
    # معلوم شود کدام مرحله کند است — نه فقط «مهلت تمام شد».
    Write-Host "::notice::[+$([int]((Get-Date) - $script:StartedAt).TotalSeconds)s] $Message"
}

function Fail([string]$Message) {
    Write-Host "::error::$Message"
    Write-Error $Message
    exit 1
}

if (-not (Test-Path $ExePath)) { Fail "EXE پیدا نشد: $ExePath" }

function Get-Signtool {
    $cmd = Get-Command signtool -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($root in @("${env:ProgramFiles(x86)}", "$env:ProgramFiles")) {
        $kitsRoot = Join-Path $root "Windows Kits\10\bin"
        if (-not (Test-Path $kitsRoot)) { continue }
        foreach ($kit in (Get-ChildItem $kitsRoot -Directory -ErrorAction SilentlyContinue |
                          Sort-Object Name -Descending)) {
            foreach ($arch in @("x64", "x86")) {
                $candidate = Join-Path $kit.FullName "$arch\signtool.exe"
                if (Test-Path $candidate) { return $candidate }
            }
        }
    }
    return $null
}

Note "signing self-test: locating signtool"
$signtool = Get-Signtool
if (-not $signtool) { Fail "signtool پیدا نشد." }
Note "signing self-test: signtool=$signtool"

$work = Join-Path $env:RUNNER_TEMP "k2-signing-selftest"
New-Item -ItemType Directory -Path $work -Force | Out-Null
$cert = $null
$rootStore = $null

try {
    Note "signing self-test: creating an ephemeral self-signed certificate (New-SelfSignedCertificate)"
    $cert = New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject "CN=K2 CI Self-Test" `
        -KeyUsage DigitalSignature `
        -KeyExportPolicy Exportable `
        -FriendlyName "K2 CI self-test" `
        -CertStoreLocation Cert:\CurrentUser\My `
        -NotAfter (Get-Date).AddHours(2)
    Note "signing self-test: certificate created thumbprint=$($cert.Thumbprint)"

    # گواهی را موقتاً به ریشهٔ همین کاربر اضافه می‌کنیم تا زنجیرهٔ
    # راستی‌آزمایی پیدا شود. باز کردن انبار ریشه برای نوشتن روی ویندوز
    # می‌تواند کند یا گیرکننده باشد، پس هر زیرمرحله جداگانه گزارش می‌شود تا
    # از لاگ معلوم شود کدام قسمت مهلت را می‌خورد.
    $sample = Join-Path $work "selftest.exe"
    Note "signing self-test: copying the EXE"
    Copy-Item $ExePath $sample -Force

    $pfx = Join-Path $work "selftest.pfx"
    Note "signing self-test: exporting a throwaway PFX"
    Export-PfxCertificate -Cert $cert -FilePath $pfx `
        -Password (ConvertTo-SecureString -String "selftest" -Force -AsPlainText) |
        Out-Null
    Note "signing self-test: PFX exported"

    Note "signing self-test: opening the CurrentUser Root store for write"
    $rootStore = New-Object System.Security.Cryptography.X509Certificates.X509Store(
        "Root", "CurrentUser")
    $rootStore.Open("ReadWrite")
    Note "signing self-test: Root store opened; adding the certificate"
    $rootStore.Add($cert)
    $rootStore.Close()
    Note "signing self-test: certificate trusted for this user only"

    Note "signing self-test: signtool sign"
    & $signtool sign /f $pfx /p "selftest" /fd SHA256 $sample
    if ($LASTEXITCODE -ne 0) { Fail "signtool sign با exit=$LASTEXITCODE شکست خورد." }
    Note "signing self-test: signed"

    Note "signing self-test: signtool verify /pa"
    & $signtool verify /pa $sample
    if ($LASTEXITCODE -ne 0) { Fail "signtool verify با exit=$LASTEXITCODE شکست خورد." }
    Note "signing self-test: verified"

    $signature = Get-AuthenticodeSignature $sample
    if ($signature.Status -ne "Valid") {
        Fail "وضعیت امضا معتبر نیست: $($signature.Status)"
    }
    Note "signing self-test: signer=$($signature.SignerCertificate.Subject)"

    Write-Host "خط لولهٔ امضا (signtool sign + verify) کار می‌کند."
    exit 0
}
finally {
    # همه چیز را پاک می‌کنیم تا هیچ اثری روی artifact نماند.
    if ($rootStore -and $cert) {
        try {
            $rootStore.Open("ReadWrite")
            $rootStore.Remove($cert)
            $rootStore.Close()
        }
        catch {
            Write-Host "::warning::پاک کردن گواهی موقت از ریشه نشد: $_"
        }
    }
    if ($cert) {
        Remove-Item "Cert:\CurrentUser\My\$($cert.Thumbprint)" -Force -ErrorAction SilentlyContinue
    }
    Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue
    Note "signing self-test: temporary certificate, PFX and copy removed"
}
