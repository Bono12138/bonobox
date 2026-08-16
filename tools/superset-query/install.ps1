param(
    [ValidateSet("Codex", "Cursor")]
    [string]$Target = "Codex",
    [string]$Destination = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceSkill = Join-Path $packageRoot "query-superset"
$requirements = Join-Path $packageRoot "requirements.txt"

if (-not (Test-Path $sourceSkill)) {
    throw "Missing query-superset folder: $sourceSkill"
}

if (-not $Destination) {
    if ($Target -eq "Cursor") {
        $Destination = Join-Path $env:USERPROFILE ".cursor\skills\query-superset"
    } else {
        $Destination = Join-Path $env:USERPROFILE ".codex\skills\query-superset"
    }
}

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    $pythonArgs = @()
    $pythonExe = $python.Source
} else {
    $python = Get-Command py -ErrorAction SilentlyContinue
    if (-not $python) {
        throw "Python 3.10 or newer is required. Install Python, then rerun this script."
    }
    $pythonArgs = @("-3")
    $pythonExe = $python.Source
}

$versionText = & $pythonExe @pythonArgs --version 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "Python could not be started: $versionText"
}
$versionValue = & $pythonExe @pythonArgs -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "Python version could not be read: $versionValue"
}
try {
    $pythonVersion = [version]$versionValue.Trim()
} catch {
    throw "Unexpected Python version: $versionValue"
}
if ($pythonVersion -lt [version]"3.10") {
    throw "Python 3.10 or newer is required. Found $pythonVersion."
}

if ((Test-Path $Destination) -and (-not $Force)) {
    throw "Destination already exists: $Destination. Rerun with -Force only after reviewing the existing installation."
}

$parent = Split-Path -Parent $Destination
New-Item -ItemType Directory -Force -Path $parent | Out-Null
$staging = Join-Path $parent (".query-superset-install-" + [guid]::NewGuid().ToString("N"))
$backup = $null
try {
    Copy-Item -Path $sourceSkill -Destination $staging -Recurse

    & $pythonExe @pythonArgs -m pip install --user -r $requirements
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed. The existing Skill was not changed."
    }

    $tests = Join-Path $staging "scripts\test_superset_query.py"
    & $pythonExe @pythonArgs $tests
    if ($LASTEXITCODE -ne 0) {
        throw "Unit tests failed. The existing Skill was not changed."
    }

    if (Test-Path $Destination) {
        $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $backupCandidate = "$Destination.backup-$stamp"
        Move-Item -Path $Destination -Destination $backupCandidate
        $backup = $backupCandidate
    }
    Move-Item -Path $staging -Destination $Destination
    if ($backup) {
        Write-Host "Previous installation moved to $backup"
    }
} catch {
    if ($backup -and (Test-Path $backup)) {
        if (Test-Path $Destination) {
            Remove-Item -Path $Destination -Recurse -Force
        }
        Move-Item -Path $backup -Destination $Destination
    }
    throw
} finally {
    if (Test-Path $staging) {
        Remove-Item -Path $staging -Recurse -Force
    }
}

Write-Host "PASS installed=$Destination"
Write-Host "PASS python=$pythonVersion"
Write-Host "PASS unit_tests"
Write-Host "NEXT run configure, auth, and doctor from the installed Skill directory"
