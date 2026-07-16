param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("MU", "SNDK", "WDC", "STX")]
    [string]$Ticker,

    [ValidateSet("1y", "2y", "5y", "10y", "max")]
    [string]$Period = "5y",

    [Parameter(Mandatory = $true)]
    [string]$IndustryRunManifest,

    [switch]$Child
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $PSScriptRoot

if (-not $Child) {
    $scriptArgument = '"{0}"' -f $PSCommandPath
    $arguments = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $scriptArgument,
        "-Child",
        "-Ticker", $Ticker,
        "-Period", $Period,
        "-IndustryRunManifest", ('"{0}"' -f $IndustryRunManifest)
    )

    $process = Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList $arguments `
        -WorkingDirectory $scriptRoot `
        -WindowStyle Normal `
        -Wait `
        -PassThru

    exit $process.ExitCode
}

$host.UI.RawUI.WindowTitle = "stock-memory-analyzer - panda_data login"
Write-Host "stock-memory-analyzer" -ForegroundColor Cyan
Write-Host "Credentials are requested locally and are not written to files or logs."
Write-Host ""

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python 3 is required. This window will close automatically." -ForegroundColor Red
    Start-Sleep -Seconds 4
    exit 4
}

Set-Location $scriptRoot
python utils/industry_refresh.py precheck --manifest $IndustryRunManifest --ticker $Ticker
if ($LASTEXITCODE -ne 0) {
    Write-Host "Industry data is not ready. No credentials were requested." -ForegroundColor Red
    Start-Sleep -Seconds 4
    exit 5
}

python analyze.py --check-deps
if ($LASTEXITCODE -ne 0) {
    Write-Host "Dependencies are not ready. Install requirements.txt and retry." -ForegroundColor Red
    Write-Host "This window will close automatically."
    Start-Sleep -Seconds 4
    exit 3
}

$username = $null
$securePassword = $null
$passwordPointer = [IntPtr]::Zero
$password = $null
$exitCode = 1

try {
    $username = Read-Host "panda_data account"
    if ([string]::IsNullOrWhiteSpace($username)) {
        Write-Host "Account is required." -ForegroundColor Red
        exit 2
    }

    $securePassword = Read-Host "panda_data password (hidden)" -AsSecureString
    $passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
    $password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
    if ([string]::IsNullOrEmpty($password)) {
        Write-Host "Password is required." -ForegroundColor Red
        exit 2
    }

    $env:PANDA_DATA_USERNAME = $username
    $env:PANDA_DATA_PASSWORD = $password

    python analyze.py --ticker $Ticker --period $Period --industry-run-manifest $IndustryRunManifest
    $exitCode = $LASTEXITCODE
}
finally {
    Remove-Item Env:PANDA_DATA_USERNAME -ErrorAction SilentlyContinue
    Remove-Item Env:PANDA_DATA_PASSWORD -ErrorAction SilentlyContinue

    if ($passwordPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
    }
    if ($null -ne $securePassword) {
        $securePassword.Dispose()
    }

    $password = $null
    $username = $null
}

exit $exitCode
