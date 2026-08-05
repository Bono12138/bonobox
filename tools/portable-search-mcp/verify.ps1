param(
    [switch]$Live
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = Join-Path $packageRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw 'The local environment was not found. Run install.ps1 first.'
}

$arguments = @((Join-Path $packageRoot 'smoke_test.py'))
if ($Live) { $arguments += '--live' }
& $pythonPath @arguments
if ($LASTEXITCODE -ne 0) { throw 'Verification failed.' }
