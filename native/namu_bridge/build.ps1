$ErrorActionPreference = "Stop"

$project = Join-Path $PSScriptRoot "namu_bridge.vcxproj"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$envFile = Join-Path $repoRoot ".env"

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
    throw "APIF_NAMU_QV_PATH is not set. Put the OpenAPI folder path in .env first."
}

$msbuildCommand = Get-Command MSBuild.exe -ErrorAction SilentlyContinue
$msbuildPath = $null
if ($msbuildCommand) {
    $msbuildPath = $msbuildCommand.Source
}

if (-not $msbuildPath) {
    $vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    if (Test-Path $vswhere) {
        $installPath = & $vswhere -latest -products * -requires Microsoft.Component.MSBuild -property installationPath
        if ($installPath) {
            $candidate = Join-Path $installPath "MSBuild\Current\Bin\MSBuild.exe"
            if (Test-Path $candidate) {
                $msbuildPath = $candidate
            }
        }
    }
}

if (-not $msbuildPath) {
    throw "MSBuild.exe was not found. Install Visual Studio Build Tools with C++ desktop development."
}

& $msbuildPath $project /p:Configuration=Release /p:Platform=Win32
