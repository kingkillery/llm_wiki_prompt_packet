param(
    [string]$Vault = $env:LLM_WIKI_VAULT,
    [string]$Targets = $(if ($env:LLM_WIKI_TARGETS) { $env:LLM_WIKI_TARGETS } else { "claude,antigravity,codex,droid" }),
    [string]$Ref = $(if ($env:LLM_WIKI_REF) { $env:LLM_WIKI_REF } else { "main" }),
    [switch]$Force
)

$ErrorActionPreference = "Stop"

if (-not $Vault) {
    $Vault = (Get-Location).Path
}

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

    $installer = Join-Path $packetRoot.FullName "installers/install_obsidian_agent_memory.py"
    if (-not (Test-Path $installer)) {
        throw "Installer not found in downloaded packet: $installer"
    }

    $installArgs = @($installer, "--vault", $Vault, "--targets", $Targets)
    if ($Force -or $env:LLM_WIKI_FORCE -eq "1") {
        $installArgs += "--force"
    }

    if ($python.Name -eq "py") {
        & py @installArgs
    } else {
        & python @installArgs
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
