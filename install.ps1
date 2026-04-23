[CmdletBinding()]
param(
    [string]$Vault = $env:LLM_WIKI_VAULT,
    [string]$Targets = $(if ($env:LLM_WIKI_TARGETS) { $env:LLM_WIKI_TARGETS } else { "claude,antigravity,codex,droid,pi" }),
    [string]$Ref = $(if ($env:LLM_WIKI_REF) { $env:LLM_WIKI_REF } else { "main" }),
    [ValidateSet("local", "global")]
    [string]$InstallScope = $(if ($env:LLM_WIKI_INSTALL_SCOPE) { $env:LLM_WIKI_INSTALL_SCOPE } else { "local" }),
    [ValidateSet("packet", "g-kade")]
    [string]$Mode = $(if ($env:LLM_WIKI_INSTALL_MODE) { $env:LLM_WIKI_INSTALL_MODE } else { "packet" }),
    [switch]$GlobalInstall,
    [switch]$WireRepo,
    [switch]$GlobalWire,
    [switch]$NoGlobalWire,
    [switch]$Unattended,
    [switch]$Force,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

function Show-Usage {
    Write-Host @'
llm_wiki_prompt_packet installer (PowerShell)

Modes:
  packet   (default) Install the packet into a vault folder.
  g-kade   Wire the packet into a target repo as a workspace.

Convenience:
  -WireRepo         Shorthand for -Mode g-kade with current directory as project
                    root and -GlobalWire enabled. The one-command path for
                    "wire this packet into the repo I am in".
  -GlobalWire       After install, write the LLM Wiki section into
                    ~/.claude/CLAUDE.md and copy wiki-*.md commands into
                    ~/.claude/commands/. Default-on for -WireRepo.
  -NoGlobalWire     Disable global Claude wiring even with -WireRepo.
  -GlobalInstall    Install scope: global (vs default local).

Examples:
  & ([scriptblock]::Create((irm https://raw.githubusercontent.com/kingkillery/llm_wiki_prompt_packet/main/install.ps1)))
  & ([scriptblock]::Create((irm https://raw.githubusercontent.com/kingkillery/llm_wiki_prompt_packet/main/install.ps1))) -WireRepo
  & ([scriptblock]::Create((irm https://raw.githubusercontent.com/kingkillery/llm_wiki_prompt_packet/main/install.ps1))) -Mode g-kade -Vault C:\path\to\repo
'@
}


if ($Help) { Show-Usage; exit 0 }

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
            if ($Mode) { $env:LLM_WIKI_INSTALL_MODE = $Mode }
            if ($Force -or $env:LLM_WIKI_FORCE -eq "1") { $env:LLM_WIKI_FORCE = "1" }
            $bashArgs = @($bashScript)
            if ($WireRepo) { $bashArgs += "--wire-repo" }
            if ($GlobalWire) { $bashArgs += "--global-wire" }
            if ($NoGlobalWire) { $bashArgs += "--no-global-wire" }
            if ($Mode -and -not $WireRepo) { $bashArgs += @("--mode", $Mode) }
            & $bash @bashArgs
            exit $LASTEXITCODE
        }
    }
}

if ($GlobalInstall) {
    $InstallScope = "global"
}
$env:LLM_WIKI_INSTALL_SCOPE = $InstallScope

# WireRepo: shorthand for "g-kade mode + current dir + global wire on".
if ($WireRepo) {
    $Mode = "g-kade"
    if (-not $Vault) { $Vault = (Get-Location).Path }
    if (-not $NoGlobalWire) { $GlobalWire = $true }
}

# Resolve effective global-wire flag (CLI wins over env, NoGlobalWire wins over GlobalWire).
$effectiveGlobalWire = $false
if ($env:LLM_WIKI_GLOBAL_WIRE -eq "1") { $effectiveGlobalWire = $true }
if ($GlobalWire) { $effectiveGlobalWire = $true }
if ($NoGlobalWire) { $effectiveGlobalWire = $false }
$env:LLM_WIKI_INSTALL_MODE = $Mode

if (-not $Vault) {
    if ($Unattended) {
        $Vault = (Get-Location).Path
    } else {
        $promptLabel = if ($Mode -eq "g-kade") { "Project root to wire" } else { "Vault folder to index" }
        $Vault = Read-Host "$promptLabel [current directory]"
        if (-not $Vault) {
            $Vault = (Get-Location).Path
        }
    }
}

$Vault = $Vault.Trim()
if (-not (Test-Path -LiteralPath $Vault -PathType Container)) {
    throw "Target does not exist: $Vault"
}

$Vault = (Resolve-Path -LiteralPath $Vault).Path

$targetLabel = if ($Mode -eq "g-kade") { "project" } else { "vault" }
$globalWireLabel = if ($effectiveGlobalWire) { "on" } else { "off" }
Write-Host ">> llm_wiki_prompt_packet install"
Write-Host ">>   mode        = $Mode"
Write-Host ">>   $targetLabel     = $Vault"
Write-Host ">>   targets     = $Targets"
Write-Host ">>   ref         = $Ref"
Write-Host ">>   scope       = $InstallScope"
Write-Host ">>   global-wire = $globalWireLabel"

$repo = "kingkillery/llm_wiki_prompt_packet"
$zipUrl = "https://github.com/$repo/archive/$Ref.zip"
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("llm-wiki-prompt-packet-" + [guid]::NewGuid().ToString("N"))
$zipPath = "$tempRoot.zip"

# Preflight: detect missing required tools BEFORE network fetch and any state changes.
# Prefer the local checkout's preflight.py so a user running install.ps1 from a clone
# gets the check before download. After extraction (below) we trust this same script.
$scriptDirLocal = Split-Path -Parent $MyInvocation.MyCommand.Path
$localPreflight = Join-Path $scriptDirLocal "installers/preflight.py"
$skipPreflight = ($env:LLM_WIKI_SKIP_PREFLIGHT -eq "1")
if (-not $skipPreflight -and (Test-Path $localPreflight)) {
    $preflightPython = Get-Command python -ErrorAction SilentlyContinue
    if (-not $preflightPython) { $preflightPython = Get-Command py -ErrorAction SilentlyContinue }
    if ($preflightPython) {
        $preArgs = @($localPreflight, "--mode", $Mode)
        if ($preflightPython.Name -eq "py") {
            & py @preArgs
        } else {
            & python @preArgs
        }
        if ($LASTEXITCODE -ne 0) {
            Write-Error "preflight failed - re-run after installing the listed tools, or set LLM_WIKI_SKIP_PREFLIGHT=1 to bypass."
            exit $LASTEXITCODE
        }
    }
}

try {
    New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath
    Expand-Archive -Path $zipPath -DestinationPath $tempRoot -Force

    $packetRoot = Get-ChildItem -Path $tempRoot -Directory | Select-Object -First 1
    if (-not $packetRoot) {
        throw "Unable to find extracted packet root."
    }

    # Fallback preflight for piped installs (irm | iex) where the local-checkout
    # branch above could not resolve a script path. Only the temp dir has been
    # written so far - failing here is reverted by the finally block.
    $extractedPreflight = Join-Path $packetRoot.FullName "installers/preflight.py"
    if (-not $skipPreflight -and -not (Test-Path $localPreflight) -and (Test-Path $extractedPreflight)) {
        $preflightPython = Get-Command python -ErrorAction SilentlyContinue
        if (-not $preflightPython) { $preflightPython = Get-Command py -ErrorAction SilentlyContinue }
        if ($preflightPython) {
            $preArgs = @($extractedPreflight, "--mode", $Mode)
            if ($preflightPython.Name -eq "py") {
                & py @preArgs
            } else {
                & python @preArgs
            }
            if ($LASTEXITCODE -ne 0) {
                Write-Error "preflight failed - re-run after installing the listed tools, or set LLM_WIKI_SKIP_PREFLIGHT=1 to bypass."
                exit $LASTEXITCODE
            }
        }
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        $python = Get-Command py -ErrorAction SilentlyContinue
    }
    if (-not $python) {
        throw "Python is required but was not found in PATH."
    }

    $installerName = "install_obsidian_agent_memory.py"
    if ($Mode -eq "g-kade") {
        $installerName = "install_g_kade_workspace.py"
    }
    $installer = Join-Path $packetRoot.FullName "installers/$installerName"
    if (-not (Test-Path $installer)) {
        throw "Installer not found in downloaded packet: $installer"
    }

    if ($Mode -eq "g-kade") {
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
    if ($Mode -eq "g-kade" -and $env:LLM_WIKI_SKIP_SETUP -eq "1") {
        $installArgs += "--skip-setup"
    }

    if ($python.Name -eq "py") {
        & py @installArgs
    } else {
        & python @installArgs
    }

    if ($Mode -ne "g-kade" -and $env:LLM_WIKI_SKIP_SETUP -ne "1") {
        $setupHelper = Join-Path $Vault "scripts/setup_llm_wiki_memory.ps1"
        if (-not (Test-Path $setupHelper)) {
            throw "Setup helper not found: $setupHelper"
        }
        & $setupHelper
    }

    if ($effectiveGlobalWire) {
        $wireHelper = Join-Path $packetRoot.FullName "installers/wire_global_claude.py"
        if (Test-Path $wireHelper) {
            Write-Host ">> wiring global Claude config (~/.claude/CLAUDE.md, ~/.claude/commands/)"
            $wireArgs = @($wireHelper, "--vault", $Vault)
            if ($python.Name -eq "py") {
                & py @wireArgs
            } else {
                & python @wireArgs
            }
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "global Claude wiring exited with code $LASTEXITCODE"
            }
        } else {
            Write-Warning "wire_global_claude.py not found in packet; skipping global wire"
        }
    }

    if ($WireRepo -or $env:LLM_WIKI_RUN_HEALTH_CHECK -eq "1") {
        $checkHelper = Join-Path $Vault "scripts/check_llm_wiki_memory.ps1"
        if (Test-Path $checkHelper) {
            Write-Host ">> running health check"
            & $checkHelper
            $healthRc = $LASTEXITCODE
            if ($healthRc -ne 0) {
                # Exit code propagates so chained commands honor failure.
                # Set LLM_WIKI_HEALTH_CHECK_NONFATAL=1 to keep warn-only behavior.
                if ($env:LLM_WIKI_HEALTH_CHECK_NONFATAL -eq "1") {
                    Write-Warning "health check reported issues (LLM_WIKI_HEALTH_CHECK_NONFATAL=1, continuing)"
                } else {
                    Write-Error "health check failed (exit $healthRc); set LLM_WIKI_HEALTH_CHECK_NONFATAL=1 to ignore"
                    exit $healthRc
                }
            }
        } else {
            Write-Warning "health check not found at $checkHelper"
        }
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
