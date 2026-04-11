param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$bash = Get-Command bash -ErrorAction SilentlyContinue
if (-not $bash) {
    throw "bash is required to run deploy_compute_engine.sh"
}

& $bash.Source (Join-Path $scriptDir "deploy_compute_engine.sh") @RemainingArgs
exit $LASTEXITCODE
