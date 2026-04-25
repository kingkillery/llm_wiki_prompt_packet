param(
    [string]$WorkspaceRoot = "",
    [string]$ConfigPath = "",
    [string]$QmdSource = "",
    [string]$QmdRepoUrl = "",
    [string]$QmdCommand = "",
    [string]$QmdCollection = "",
    [string]$QmdContext = "",
    [string]$BrvCommand = "",
    [string]$GitvizzFrontendUrl = "",
    [string]$GitvizzBackendUrl = "",
    [string]$GitvizzRepoUrl = "",
    [string]$GitvizzCheckoutPath = "",
    [string]$GitvizzRepoPath = "",
    [switch]$SkipQmd,
    [switch]$SkipMcp,
    [switch]$SkipQmdBootstrap,
    [switch]$SkipQmdEmbed,
    [switch]$SkipBrv,
    [switch]$SkipBrvInit,
    [switch]$SkipGitvizz,
    [switch]$SkipGitvizzStart,
    [switch]$AllowGlobalToolInstall,
    [switch]$VerifyOnly,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$ErrorActionPreference = "Stop"

$repoRoot = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { (Get-Location).Path }
if (-not $repoRoot) {
    $repoRoot = (Get-Location).Path
}
if (-not $WorkspaceRoot) {
    $WorkspaceRoot = $repoRoot
}
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
$runtimeScript = Join-Path $repoRoot "support\scripts\llm_wiki_memory_runtime.py"

if (-not (Test-Path $runtimeScript)) {
    throw "Missing shared runtime: $runtimeScript"
}

Push-Location $repoRoot
try {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) { $python = Get-Command py -ErrorAction SilentlyContinue }
    if (-not $python) { throw "Python is required to run check_llm_wiki_memory.ps1" }

    $runtimeArgs = @("check", "--workspace=$WorkspaceRoot")
    $optionMap = @{
        ConfigPath = "config-path"; QmdSource = "qmd-source"; QmdRepoUrl = "qmd-repo-url";
        QmdCommand = "qmd-command"; QmdCollection = "qmd-collection"; QmdContext = "qmd-context";
        BrvCommand = "brv-command"; GitvizzFrontendUrl = "gitvizz-frontend-url";
        GitvizzBackendUrl = "gitvizz-backend-url"; GitvizzRepoUrl = "gitvizz-repo-url";
        GitvizzCheckoutPath = "gitvizz-checkout-path"; GitvizzRepoPath = "gitvizz-repo-path"
    }
    foreach ($key in $optionMap.Keys) {
        $value = Get-Variable -Name $key -ValueOnly
        if (-not [string]::IsNullOrWhiteSpace([string]$value)) {
            $runtimeArgs += "--$($optionMap[$key])=$value"
        }
    }
    $switchMap = @{
        SkipQmd = "skip-qmd"; SkipMcp = "skip-mcp"; SkipQmdBootstrap = "skip-qmd-bootstrap";
        SkipQmdEmbed = "skip-qmd-embed"; SkipBrv = "skip-brv"; SkipBrvInit = "skip-brv-init";
        SkipGitvizz = "skip-gitvizz"; SkipGitvizzStart = "skip-gitvizz-start";
        AllowGlobalToolInstall = "allow-global-tool-install"; VerifyOnly = "verify-only"
    }
    foreach ($key in $switchMap.Keys) {
        $value = Get-Variable -Name $key -ValueOnly
        if ($value.IsPresent) { $runtimeArgs += "--$($switchMap[$key])" }
    }
    if ($Arguments) { $runtimeArgs += $Arguments }

    if ($python.Name -eq "py") {
        & py -3 $runtimeScript @runtimeArgs
    } else {
        & $python.Name $runtimeScript @runtimeArgs
    }
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
