param(
    [string]$SkillPath = "",
    [switch]$Live
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $SkillPath) {
    $SkillPath = Join-Path $packageRoot "query-superset"
}

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    $pythonArgs = @()
    $pythonExe = $python.Source
} else {
    $python = Get-Command py -ErrorAction SilentlyContinue
    if (-not $python) {
        throw "Python 3.10 or newer is required."
    }
    $pythonArgs = @("-3")
    $pythonExe = $python.Source
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

$skillFile = Join-Path $SkillPath "SKILL.md"
$client = Join-Path $SkillPath "scripts\superset_query.py"
$tests = Join-Path $SkillPath "scripts\test_superset_query.py"
$agentConfig = Join-Path $SkillPath "agents\openai.yaml"
$capabilities = Join-Path $SkillPath "references\capabilities.md"
foreach ($required in @($skillFile, $client, $tests, $agentConfig, $capabilities)) {
    if (-not (Test-Path $required)) {
        throw "Missing required file: $required"
    }
}

& $pythonExe @pythonArgs $tests
if ($LASTEXITCODE -ne 0) {
    throw "Unit tests failed."
}
Write-Host "PASS structure"
Write-Host "PASS unit_tests"
Write-Host "PASS python=$pythonVersion"

if ($Live) {
    & $pythonExe @pythonArgs $client status
    if ($LASTEXITCODE -ne 0) {
        throw "Configuration is incomplete. Run configure and auth first."
    }
    & $pythonExe @pythonArgs $client doctor
    if ($LASTEXITCODE -ne 0) {
        throw "Live SELECT 1 failed."
    }
    Write-Host "PASS live_select_1"
} else {
    Write-Host "SKIP live_select_1 (rerun with -Live after configure and auth)"
}
