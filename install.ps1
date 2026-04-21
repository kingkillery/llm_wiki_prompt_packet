param(
    [string]$Vault = $env:LLM_WIKI_VAULT,
    [string]$Targets = $(if ($env:LLM_WIKI_TARGETS) { $env:LLM_WIKI_TARGETS } else { "claude,antigravity,codex,droid,pi" }),
    [string]$Ref = $(if ($env:LLM_WIKI_REF) { $env:LLM_WIKI_REF } else { "main" }),
    [ValidateSet("local", "global")]
    [string]$InstallScope = $(if ($env:LLM_WIKI_INSTALL_SCOPE) { $env:LLM_WIKI_INSTALL_SCOPE } else { "local" }),
    [switch]$GlobalInstall,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Test-IsWindows {
    if ($PSVersionTable.PSVersion.Major -lt 6) {
        return $true
    }
    if ($null -ne $IsWindows) {
        return [bool]$IsWindows
    }
    return $env:OS -eq "Windows_NT"
}

if (-not (Test-IsWindows)) {
    $bash = Get-Command bash -ErrorAction SilentlyContinue
    if ($bash) {
        $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
        $bashScript = Join-Path $scriptDir "install.sh"
        if (Test-Path $bashScript) {
            if ($Vault) { $env:LLM_WIKI_VAULT = $Vault }
            if ($Targets) { $env:LLM_WIKI_TARGETS = $Targets }
            if ($Ref) { $env:LLM_WIKI_REF = $Ref }
            if ($InstallScope) { $env:LLM_WIKI_INSTALL_SCOPE = $InstallScope }
            if ($env:LLM_WIKI_INSTALL_MODE) { $env:LLM_WIKI_INSTALL_MODE = $env:LLM_WIKI_INSTALL_MODE }
            if ($Force -or $env:LLM_WIKI_FORCE -eq "1") { $env:LLM_WIKI_FORCE = "1" }
            & $bash $bashScript
            exit $LASTEXITCODE
        }
    }
}

if ($GlobalInstall) {
    $InstallScope = "global"
}
$env:LLM_WIKI_INSTALL_SCOPE = $InstallScope

if (-not $Vault) {
    $Vault = Read-Host "Vault folder to index [current directory]"
    if (-not $Vault) {
        $Vault = (Get-Location).Path
    }
}

$Vault = $Vault.Trim()
if (-not (Test-Path -LiteralPath $Vault -PathType Container)) {
    throw "Vault does not exist: $Vault"
}

$Vault = (Resolve-Path -LiteralPath $Vault).Path
$installMode = if ($env:LLM_WIKI_INSTALL_MODE) { $env:LLM_WIKI_INSTALL_MODE } else { "packet" }

$repo = "kingkillery/llm_wiki_prompt_packet"
$zipUrl = "https://github.com/$repo/archive/$Ref.zip"
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("llm-wiki-prompt-packet-" + [guid]::NewGuid().ToString("N"))
$zipPath = "$tempRoot.zip"

try {
    New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath
    Expand-Archive -Path $zipPath -DestinationPath $tempRoot -Force

    $packetRoot = Get-ChildItem -Path $tempRoot -Directory | Select-Object -First 1
    if (-not $packetRoot) {
        throw "Unable to find extracted packet root."
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        $python = Get-Command py -ErrorAction SilentlyContinue
    }
    if (-not $python) {
        throw "Python is required but was not found in PATH."
    }

    $installerName = "install_obsidian_agent_memory.py"
    if ($installMode -eq "g-kade") {
        $installerName = "install_g_kade_workspace.py"
    }
    $installer = Join-Path $packetRoot.FullName "installers/$installerName"
    if (-not (Test-Path $installer)) {
        throw "Installer not found in downloaded packet: $installer"
    }

    if ($installMode -eq "g-kade") {
        $installArgs = @($installer, "--workspace", $Vault, "--targets", $Targets)
    } else {
        $installArgs = @($installer, "--vault", $Vault, "--targets", $Targets)
    }
    if ($Force -or $env:LLM_WIKI_FORCE -eq "1") {
        $installArgs += "--force"
    }
    if ($env:LLM_WIKI_SKIP_HOME_SKILLS -eq "1") {
        $installArgs += "--skip-home-skills"
    }
    if ($installMode -eq "g-kade" -and $env:LLM_WIKI_SKIP_SETUP -eq "1") {
        $installArgs += "--skip-setup"
    }

    if ($python.Name -eq "py") {
        & py @installArgs
    } else {
        & python @installArgs
    }

    if ($installMode -ne "g-kade" -and $env:LLM_WIKI_SKIP_SETUP -ne "1") {
        $setupHelper = Join-Path $Vault "scripts/setup_llm_wiki_memory.ps1"
        if (-not (Test-Path $setupHelper)) {
            throw "Setup helper not found: $setupHelper"
        }
        & $setupHelper
    }

    exit $LASTEXITCODE
} finally {
    if (Test-Path $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
