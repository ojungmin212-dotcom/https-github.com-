$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$bridge = Join-Path $repoRoot "native\namu_bridge\bin\Win32\Release\namu_bridge.exe"
$envFile = Join-Path $repoRoot ".env"

function Read-PlainSecret($prompt) {
    $secure = Read-Host $prompt -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

if (-not (Test-Path $bridge)) {
    Write-Host "Building 32-bit Namu bridge..."
    & (Join-Path $repoRoot "native\namu_bridge\build.ps1")
}

if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            return
        }
        $parts = $line.Split("=", 2)
        [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
    }
}

if (-not $env:APIF_NAMU_QV_PATH) {
    $env:APIF_NAMU_QV_PATH = Read-Host "OpenAPI folder path"
}

Write-Host ""
Write-Host "Namu login quote test"
Write-Host "Do not paste these values into chat. Type them only in this window."
Write-Host ""

$env:APIF_NAMU_USER_ID = Read-Host "HTS/OpenAPI ID"
$env:APIF_NAMU_USER_PASSWORD = Read-PlainSecret "HTS/OpenAPI password"
$env:APIF_NAMU_CERT_PASSWORD = Read-PlainSecret "Certificate password, press Enter if not needed"
$symbol = Read-Host "Stock code to test, default 005930"
if (-not $symbol) {
    $symbol = "005930"
}

Write-Host ""
Write-Host "Loading wmca.dll..."
'{"command":"ping"}' | & $bridge

Write-Host ""
Write-Host "Requesting quote for $symbol..."
$request = '{"command":"quote","symbol":"' + $symbol + '"}'
$request | & $bridge

Write-Host ""
Read-Host "Press Enter to close"
