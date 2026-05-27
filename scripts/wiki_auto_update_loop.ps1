#requires -Version 5.1
<#
.SYNOPSIS
    Continuous background wiki auto-update loop.
.DESCRIPTION
    Runs wiki_auto_update.py at regular intervals using the configured
    model pool (LM Studio local + OpenRouter free + SiliconFlow cheap).
#>
param(
    [int]$IntervalSeconds = 300,
    [string]$Workspace = "",
    [switch]$Verbose
)

$ErrorActionPreference = "Continue"

if (-not $Workspace) {
    $Workspace = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command py -ErrorAction SilentlyContinue }
if (-not $python) {
    Write-Host "Python not found. Exiting." -ForegroundColor Red
    exit 1
}

$script = Join-Path $Workspace "scripts\wiki_auto_update.py"
if (-not (Test-Path $script)) {
    Write-Host "Missing wiki_auto_update.py at $script" -ForegroundColor Red
    exit 1
}

Write-Host "Starting continuous wiki auto-update loop..." -ForegroundColor Cyan
Write-Host "Workspace : $Workspace" -ForegroundColor Gray
Write-Host "Interval  : ${IntervalSeconds}s" -ForegroundColor Gray
Write-Host "Press Ctrl+C to stop." -ForegroundColor Gray
Write-Host ""

while ($true) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] Running wiki auto-update..." -ForegroundColor Green

    $args = @($script, "--workspace", $Workspace)
    if ($Verbose) { $args += "--verbose" }

    try {
        & $python.Name @args 2>&1 | ForEach-Object {
            Write-Host "  $_" -ForegroundColor Gray
        }
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            Write-Host "[$timestamp] Exit code: $exitCode" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[$timestamp] ERROR: $_" -ForegroundColor Red
    }

    $nextRun = (Get-Date).AddSeconds($IntervalSeconds).ToString("HH:mm:ss")
    Write-Host "[$timestamp] Next run at $nextRun (sleeping ${IntervalSeconds}s)" -ForegroundColor DarkGray
    Write-Host ""

    Start-Sleep -Seconds $IntervalSeconds
}
