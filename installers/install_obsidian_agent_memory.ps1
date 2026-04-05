param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsToPass
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) {
    $Python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $Python) {
    Write-Error "Python is required but was not found in PATH."
    exit 1
}

if ($Python.Name -eq "py") {
    & py "$ScriptDir/install_obsidian_agent_memory.py" @ArgsToPass
} else {
    & python "$ScriptDir/install_obsidian_agent_memory.py" @ArgsToPass
}
exit $LASTEXITCODE
