param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot,
    [string]$Targets = "claude,antigravity,codex,droid,pi",
    [ValidateSet("local", "global")]
    [string]$InstallScope = "local",
    [string]$HomeRoot = [Environment]::GetFolderPath("UserProfile"),
    [switch]$SkipHomeSkills,
    [switch]$AllowGlobalToolInstall,
    [switch]$EnableGitvizz,
    [switch]$SkipSetup,
    [switch]$PreflightOnly,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$toolset = Join-Path $PSScriptRoot "llm_wiki_packet.ps1"
if (-not (Test-Path -LiteralPath $toolset)) {
    throw "Missing packet CLI wrapper: $toolset"
}

$argsToPass = @(
    "init",
    "--project-root", $ProjectRoot,
    "--targets", $Targets,
    "--install-scope", $InstallScope,
    "--home-root", $HomeRoot
)

if ($SkipHomeSkills) {
    $argsToPass += "--skip-home-skills"
}
if ($AllowGlobalToolInstall) {
    $argsToPass += "--allow-global-tool-install"
}
if ($EnableGitvizz) {
    $argsToPass += "--enable-gitvizz"
}
if ($SkipSetup) {
    $argsToPass += "--skip-setup"
}
if ($PreflightOnly) {
    $argsToPass += "--preflight-only"
}
if ($Force) {
    $argsToPass += "--force"
}

& $toolset @argsToPass
exit $LASTEXITCODE
