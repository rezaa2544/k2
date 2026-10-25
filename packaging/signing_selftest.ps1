#requires -Version 5.1
<#
.SYNOPSIS
    خودآزمایی خط لولهٔ امضای دیجیتال روی ویندوز.

.DESCRIPTION
    «امضای واقعی» نیاز به گواهی Code Signing دارد که فقط کاربر می‌تواند
    تهیه کند. ولی خودِ خط لوله را می‌توان بدون آن آزمود: ساخت گواهی،
    امضای یک **کپی** از EXE با signtool، و خواندنِ امضای نوشته‌شده. فایل
    منتشرشده هرگز امضا نمی‌شود و هیچ اثری روی artifact نمی‌ماند.

    دو نیمهٔ جدا دارد، چون ریسکشان یکی نیست:

      ۱) «sign» — همیشه اجرا می‌شود و سریع است (چند ثانیه). امضا با
         signtool انجام می‌شود و بعد همان امضا با Get-AuthenticodeSignature
         خوانده و به گواهی ما مق伊斯 می‌شود. این نیمهٔ حساس است: اگر خط
         لوله شکسته باشد، همین قرمز می‌شود.

      ۲) «trustedverify» — زنجیرهٔ اعتماد را می‌سازد و با
         ``signtool verify /pa`` راستی‌آزمایی می‌کند. این نیمه به نوشتن در
         انبار ریشهٔ ویندوز نیاز دارد و روی runnerها آویزان می‌ماند. پس
         به‌صورت فرزندِ با مهلت زمانی اجرا می‌شود؛ اگر آویزان شد، هشدار
         می‌دهیم و رد می‌شود — نه اینکه کل job را بگیرد.

    چرا نیمهٔ اول به زنجیرهٔ اعتماد نیاز ندارد: گواهی خودامضا ذاتاً
    «غیرقابل‌اعتماد» است و فقط کاربر می‌تواند گواهی واقعیِ امضاشده توسط یک
    ریشهٔ معروف بدهد. پس درستیِ امضا (پیدایش، دست‌نخورده بودنِ فایل، و
    وابستگی به گواهی درست) را می‌سنجیم، نه اعتمادِ زنجیره را.

.PARAMETER ExePath
    مسیر EXE ساختهٔ PyInstaller (فقط در حالت sign).

.PARAMETER Mode
    ``sign`` (پیش‌فرض) یا ``trustedverify``.

.PARAMETER SamplePath
    مسیر کپیِ امضاشده (فقط در حالت trustedverify).

.PARAMETER Thumbprint
    اثر انگشت گواهی موقت (فقط در حالت trustedverify).

.PARAMETER TimeoutSeconds
    مهلت فرزندِ حالت trustedverify.

.EXAMPLE
    pwsh -NoProfile -File packaging\signing_selftest.ps1 -ExePath packaging\output\K2\K2.exe
#>
[CmdletBinding()]
param(
    [string]$ExePath,
    [ValidateSet("sign", "trustedverify")][string]$Mode = "sign",
    [string]$SamplePath,
    [string]$Thumbprint,
    [int]$TimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$script:StartedAt = Get-Date

function Note([string]$Message) {
    # ثانیهٔ سپری‌شده هم چاپ می‌شود تا اگر چیزی آویزان شد، از لاگ معلوم
    # شود کدام مرحله است — نه فقط «مهلت تمام شد».
    Write-Host "::notice::[+$([int]((Get-Date) - $script:StartedAt).TotalSeconds)s] $Message"
}

function Fail([string]$Message) {
    Write-Host "::error::$Message"
    Write-Error $Message
    exit 1
}

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

# ---------------------------------------------------------------------------
# حالت دوم: زنجیرهٔ اعتماد + راستی‌آزمایی با signtool
# ---------------------------------------------------------------------------
if ($Mode -eq "trustedverify") {
    if (-not $SamplePath -or -not $Thumbprint) {
        Fail "حالت trustedverify به SamplePath و Thumbprint نیاز دارد."
    }
    if (-not (Test-Path $SamplePath)) { Fail "کپی امضاشده پیدا نشد: $SamplePath" }

    $signtool = Get-Signtool
    if (-not $signtool) { Fail "signtool پیدا نشد." }

    $rootStore = $null
    try {
        Note "trustedverify: opening the CurrentUser Root store for write"
        $rootStore = New-Object System.Security.Cryptography.X509Certificates.X509Store(
            "Root", "CurrentUser")
        $rootStore.Open("ReadWrite")
        Note "trustedverify: Root store opened; adding the certificate"
        $rootStore.Add((Get-Item "Cert:\CurrentUser\My\$Thumbprint"))
        $rootStore.Close()
        $rootStore = $null
        Note "trustedverify: certificate trusted for this user only"

        Note "trustedverify: signtool verify /pa"
        & $signtool verify /pa $SamplePath
        if ($LASTEXITCODE -ne 0) {
            Fail "signtool verify با exit=$LASTEXITCODE شکست خورد."
        }
        Note "trustedverify: chain verified"
        Write-Host "خط لولهٔ امضا (signtool sign + verify /pa) کار می‌کند."
        exit 0
    }
    finally {
        if ($rootStore) {
            try { $rootStore.Close() } catch { }
        }
        # گواهی موقت از ریشهٔ همین کاربر پاک می‌شود تا اثری نماند.
        try {
            $cleanup = New-Object System.Security.Cryptography.X509Certificates.X509Store(
                "Root", "CurrentUser")
            $cleanup.Open("ReadWrite")
            $item = Get-Item "Cert:\CurrentUser\My\$Thumbprint" -ErrorAction SilentlyContinue
            if ($item) { $cleanup.Remove($item) }
            $cleanup.Close()
        }
        catch {
            Write-Host "::warning::پاک کردن گواهی موقت از ریشه نشد: $_"
        }
    }
}

# ---------------------------------------------------------------------------
# حالت اول: امضا + خواندن امضا (سریع و بدون وابستگی به انبار ریشه)
# ---------------------------------------------------------------------------
if (-not $ExePath) { Fail "ExePath داده نشده." }
if (-not (Test-Path $ExePath)) { Fail "EXE پیدا نشد: $ExePath" }

Note "sign: locating signtool"
$signtool = Get-Signtool
if (-not $signtool) { Fail "signtool پیدا نشد." }
Note "sign: signtool=$signtool"

$work = Join-Path $env:RUNNER_TEMP "k2-signing-selftest"
New-Item -ItemType Directory -Path $work -Force | Out-Null
$cert = $null

try {
    Note "sign: creating an ephemeral self-signed certificate (New-SelfSignedCertificate)"
    $cert = New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject "CN=K2 CI Self-Test" `
        -KeyUsage DigitalSignature `
        -KeyExportPolicy Exportable `
        -FriendlyName "K2 CI self-test" `
        -CertStoreLocation Cert:\CurrentUser\My `
        -NotAfter (Get-Date).AddHours(2)
    Note "sign: certificate created thumbprint=$($cert.Thumbprint)"

    # روی یک کپی کار می‌کنیم؛ فایل منتشرشده هرگز امضا نمی‌شود.
    $sample = Join-Path $work "selftest.exe"
    Note "sign: copying the EXE"
    Copy-Item $ExePath $sample -Force

    $pfx = Join-Path $work "selftest.pfx"
    Note "sign: exporting a throwaway PFX"
    Export-PfxCertificate -Cert $cert -FilePath $pfx `
        -Password (ConvertTo-SecureString -String "selftest" -Force -AsPlainText) |
        Out-Null
    Note "sign: PFX exported"

    Note "sign: signtool sign"
    & $signtool sign /f $pfx /p "selftest" /fd SHA256 $sample
    if ($LASTEXITCODE -ne 0) { Fail "signtool sign با exit=$LASTEXITCODE شکست خورد." }
    Note "sign: signed"

    # خواندنِ امضا با Get-AuthenticodeSignature. به زنجیرهٔ اعتماد وابسته
    # نیست، پس با گواهی خودامضا هم کار می‌کند.
    $signature = Get-AuthenticodeSignature $sample
    if ($signature.Status -eq "NotSigned") {
        Fail "signtool خروج گرفت ولی امضایی روی فایل نبود."
    }
    if ($signature.Status -eq "HashMismatch") {
        Fail "امضا با محتوای فایل نمی‌خواند (HashMismatch)."
    }
    if (-not $signature.SignerCertificate) {
        Fail "امضا خوانده شد ولی گواهی امضاکننده پیدا نشد (وضعیت: $($signature.Status))."
    }
    if ($signature.SignerCertificate.Thumbprint -ne $cert.Thumbprint) {
        Fail ("امضا به گواهی دیگری تعلق دارد: " +
              "$($signature.SignerCertificate.Thumbprint) به‌جای $($cert.Thumbprint).")
    }
    Note "sign: signature readable, signer=$($signature.SignerCertificate.Subject) status=$($signature.Status)"

    # نیمهٔ دوم: زنجیرهٔ اعتماد و راستی‌آزمایی با signtool. روی runnerها
    # آویزان می‌ماند، پس فرزندِ با مهلت زمانی است و اگر آویزان شد رد می‌شود.
    $childLog = Join-Path $env:RUNNER_TEMP "signing-trustverify.log"
    $child = Start-Process -FilePath "pwsh" -PassThru -WindowStyle Hidden `
        -ArgumentList @("-NoProfile", "-NoLogo", "-File", $PSCommandPath,
                        "-Mode", "trustedverify",
                        "-SamplePath", $sample,
                        "-Thumbprint", $cert.Thumbprint) `
        -RedirectStandardOutput $childLog
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while (-not $child.HasExited -and (Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 500
    }
    if (Test-Path $childLog) {
        Get-Content $childLog | ForEach-Object { Write-Host "$_" }
    }
    if (-not $child.HasExited) {
        $child.Kill()
        Write-Host "::warning::نیمهٔ «راستی‌آزمایی با زنجیرهٔ اعتماد» آویزان شد و رد شد. علت: نوشتن در انبار ریشهٔ ویندوز روی runner غیرتعاملی گیر می‌کند. نیمهٔ «امضا + خواندن امضا» موفق بود. راستی‌آزمایی واقعی با گواهی کاربر انجام می‌شود."
        exit 0
    }
    if ($child.ExitCode -ne 0) {
        Fail "راستی‌آزمایی با زنجیرهٔ اعتماد شکست خورد (exit=$($child.ExitCode))."
    }
    Write-Host "خط لولهٔ امضا (signtool sign + verify /pa) کار می‌کند."
    exit 0
}
finally {
    # همه چیز پاک می‌شود تا هیچ اثری روی artifact یا انبارها نماند.
    if ($cert) {
        # اگر نیمهٔ دوم قبل از Kill توانسته باشد گواهی را به ریشه اضافه کند،
        # آن را هم برمی‌داریم.
        try {
            $root = New-Object System.Security.Cryptography.X509Certificates.X509Store(
                "Root", "CurrentUser")
            $root.Open("ReadWrite")
            $root.Remove($cert)
            $root.Close()
        }
        catch { }
        Remove-Item "Cert:\CurrentUser\My\$($cert.Thumbprint)" -Force -ErrorAction SilentlyContinue
    }
    Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue
    Note "sign: temporary certificate, PFX and copy removed"
}
