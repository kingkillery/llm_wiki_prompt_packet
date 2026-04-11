$ErrorActionPreference = "Stop"

$workspaceRoot = Split-Path -Parent $PSScriptRoot
$targetScript = Join-Path $workspaceRoot "support\scripts\setup_llm_wiki_memory.ps1"

if (-not (Test-Path $targetScript)) {
    throw "Setup helper not found: $targetScript"
}

Push-Location $workspaceRoot
try {
    & $targetScript @args
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
