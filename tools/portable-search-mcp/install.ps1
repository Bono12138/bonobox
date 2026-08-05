param(
    [switch]$ConfigurationOnly,
    [string]$PythonExecutable
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$serverPath = Join-Path $packageRoot 'ddgs-mcp-server.py'

if (-not (Test-Path -LiteralPath $serverPath -PathType Leaf)) {
    throw 'The package is incomplete: ddgs-mcp-server.py is missing.'
}

if (-not $PythonExecutable) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw 'Python 3.10 or newer was not found. Install Python, then run this script again.'
    }
    $PythonExecutable = $pythonCommand.Source
}

$resolvedPython = (Get-Command $PythonExecutable -ErrorAction Stop).Source
$versionText = & $resolvedPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to run the selected Python executable.'
}
$versionParts = $versionText.Trim().Split('.')
if ([int]$versionParts[0] -lt 3 -or ([int]$versionParts[0] -eq 3 -and [int]$versionParts[1] -lt 10)) {
    throw 'Python 3.10 or newer is required.'
}

$activePython = $resolvedPython
if (-not $ConfigurationOnly) {
    $venvRoot = Join-Path $packageRoot '.venv'
    $venvPython = Join-Path $venvRoot 'Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
        & $resolvedPython -m venv $venvRoot
        if ($LASTEXITCODE -ne 0) { throw 'Failed to create the local Python environment.' }
    }
    $activePython = $venvPython
    & $activePython -m pip install --disable-pip-version-check -r (Join-Path $packageRoot 'requirements.lock.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install the locked dependencies.' }
}

$config = [ordered]@{
    mcpServers = [ordered]@{
        'portable-search' = [ordered]@{
            command = $activePython
            args = @($serverPath)
            env = @{}
            type = 'stdio'
        }
    }
}
$configPath = Join-Path $packageRoot 'mcp-config.local.json'
$config | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $configPath -Encoding UTF8

Write-Output ('PASS configuration=' + $configPath)
Write-Output 'Copy the portable-search entry into the MCP configuration of your agent host, then restart that host.'

if (-not $ConfigurationOnly) {
    & $activePython (Join-Path $packageRoot 'smoke_test.py')
    if ($LASTEXITCODE -ne 0) { throw 'The local MCP protocol check failed.' }
}
