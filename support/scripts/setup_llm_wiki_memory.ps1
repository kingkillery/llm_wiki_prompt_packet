param(
    [string]$ConfigPath = $(Join-Path (Split-Path -Parent $PSScriptRoot) ".llm-wiki\config.json"),
    [string]$QmdSource = $env:LLM_WIKI_QMD_SOURCE,
    [string]$QmdRepoUrl = $env:LLM_WIKI_QMD_REPO_URL,
    [string]$QmdCommand = $env:LLM_WIKI_QMD_COMMAND,
    [string]$QmdCollection = $env:LLM_WIKI_QMD_COLLECTION,
    [string]$QmdContext = $env:LLM_WIKI_QMD_CONTEXT,
    [string]$BrvCommand = $env:LLM_WIKI_BRV_COMMAND,
    [string]$GitvizzFrontendUrl = $env:LLM_WIKI_GITVIZZ_FRONTEND_URL,
    [string]$GitvizzBackendUrl = $env:LLM_WIKI_GITVIZZ_BACKEND_URL,
    [string]$GitvizzRepoPath = $env:LLM_WIKI_GITVIZZ_REPO_PATH,
    [switch]$SkipQmd,
    [switch]$SkipMcp,
    [switch]$SkipQmdBootstrap,
    [switch]$SkipQmdEmbed,
    [switch]$SkipBrvInit,
    [switch]$SkipBrv,
    [switch]$SkipGitvizzStart,
    [switch]$VerifyOnly
)

$ErrorActionPreference = "Stop"

function Get-WorkspaceRoot {
    $scriptParent = Split-Path -Parent $PSScriptRoot
    if (Test-Path (Join-Path $scriptParent ".llm-wiki\config.json")) {
        return $scriptParent
    }
    return (Get-Location).Path
}

function Get-ConfigValue {
    param(
        [string]$Preferred,
        [object]$Fallback
    )

    if ($Preferred) {
        return $Preferred
    }
    return $Fallback
}

function Get-PythonCommand {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return $python.Name }
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { return $py.Name }
    return $null
}

function Get-NpmCommand {
    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if ($npm) { return $npm.Name }
    $npmCmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($npmCmd) { return $npmCmd.Name }
    return $null
}

function Get-LocalQmdManifestPath {
    param([string]$WorkspaceRoot)
    return (Join-Path $WorkspaceRoot ".llm-wiki\package.json")
}

function Get-LocalQmdCommandPath {
    param([string]$WorkspaceRoot)
    $candidates = @(
        (Join-Path $WorkspaceRoot ".llm-wiki\node_modules\.bin\pk-qmd.cmd"),
        (Join-Path $WorkspaceRoot ".llm-wiki\node_modules\.bin\pk-qmd.ps1"),
        (Join-Path $WorkspaceRoot ".llm-wiki\node_modules\.bin\pk-qmd")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }
    return $null
}

function Resolve-GitSource {
    param([string]$RepoUrl)
    if ($RepoUrl.StartsWith("git+")) {
        return $RepoUrl
    }
    if ($RepoUrl.EndsWith(".git")) {
        return "git+$RepoUrl"
    }
    return "git+$RepoUrl.git"
}

function Invoke-JsonMerge {
    param(
        [string]$PythonCommand,
        [string]$TargetPath,
        [string]$ServerKey,
        [string]$CommandName,
        [switch]$FactoryStyle
    )

    $script = @"
from pathlib import Path
import json
import sys

path = Path(sys.argv[1]).expanduser()
server_key = sys.argv[2]
command_name = sys.argv[3]
factory_style = sys.argv[4] == "1"

data = {}
if path.exists():
    raw = path.read_text(encoding="utf-8").strip()
    if raw:
        data = json.loads(raw)

mcp = data.get("mcpServers")
if not isinstance(mcp, dict):
    mcp = {}
data["mcpServers"] = mcp

payload = {"command": command_name, "args": ["mcp"]}
if factory_style:
    payload = {"type": "stdio", "command": command_name, "args": ["mcp"], "disabled": False}

mcp[server_key] = payload
mcp.pop("qmd", None)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
"@

    & $PythonCommand -c $script $TargetPath $ServerKey $CommandName $(if ($FactoryStyle) { "1" } else { "0" }) | Out-Null
}

function Set-CodexMcp {
    param(
        [string]$Path,
        [string]$CommandName
    )

    $content = ""
    if (Test-Path $Path) {
        $content = Get-Content -Path $Path -Raw
    }

    $block = @"
[mcp_servers.pk-qmd]
command = "$CommandName"
args = ["mcp"]
"@

    $sectionPattern = "(?ms)^\[mcp_servers\.pk-qmd\]\r?\n(?:.*?)(?=^\[|\z)"
    if ($content -match "(?m)^\[mcp_servers\.pk-qmd\]") {
        $content = [regex]::Replace($content, $sectionPattern, "$block`n")
    } else {
        if ($content -and -not $content.EndsWith("`n")) {
            $content += "`n"
        }
        $content += "`n$block`n"
    }

    $legacyPattern = "(?ms)^\[mcp_servers\.qmd\]\r?\n(?:.*?)(?=^\[|\z)"
    $content = [regex]::Replace($content, $legacyPattern, "")

    $parent = Split-Path -Parent $Path
    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    Set-Content -Path $Path -Value $content -Encoding utf8
}

function Test-TcpUrl {
    param([string]$Url)

    $uri = [System.Uri]$Url
    $port = if ($uri.Port -gt 0) { $uri.Port } elseif ($uri.Scheme -eq "https") { 443 } else { 80 }
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect($uri.Host, $port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(3000)) {
            return $false
        }
        $client.EndConnect($async) | Out-Null
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

function Start-GitVizzIfNeeded {
    param(
        [string]$RepoPath,
        [string]$FrontendUrl,
        [string]$BackendUrl,
        [switch]$Verify
    )

    if ((Test-TcpUrl -Url $FrontendUrl) -and (Test-TcpUrl -Url $BackendUrl)) {
        return "GitVizz already reachable"
    }

    if ($Verify) {
        return "GitVizz is not reachable"
    }

    if (-not $RepoPath) {
        return "GitVizz repo path not configured; set LLM_WIKI_GITVIZZ_REPO_PATH or gitvizz.repo_path to auto-launch"
    }

    if (-not (Test-Path (Join-Path $RepoPath "docker-compose.yaml"))) {
        return "GitVizz repo path missing docker-compose.yaml: $RepoPath"
    }

    Push-Location $RepoPath
    try {
        & docker-compose up -d --build
    } finally {
        Pop-Location
    }

    if ((Test-TcpUrl -Url $FrontendUrl) -and (Test-TcpUrl -Url $BackendUrl)) {
        return "Launched GitVizz via docker-compose"
    }

    return "GitVizz launch attempted but endpoints are still unreachable"
}

function Test-QmdFeature {
    param(
        [string]$CommandName,
        [string]$Pattern
    )

    try {
        $output = & $CommandName 2>&1 | Out-String
        return $output -match [regex]::Escape($Pattern)
    } catch {
        return $false
    }
}

function Install-PacketLocalQmdDependency {
    param([string]$WorkspaceRoot)

    $manifestPath = Get-LocalQmdManifestPath -WorkspaceRoot $WorkspaceRoot
    if (-not (Test-Path $manifestPath)) {
        return $null
    }

    $npm = Get-NpmCommand
    if (-not $npm) {
        throw "npm is required to install the packet-local pk-qmd dependency."
    }

    & $npm install --prefix (Split-Path -Parent $manifestPath)
    return (Get-LocalQmdCommandPath -WorkspaceRoot $WorkspaceRoot)
}

function Resolve-QmdCommand {
    param(
        [string]$RequestedCommand,
        [string]$WorkspaceRoot
    )

    $localCommand = Get-LocalQmdCommandPath -WorkspaceRoot $WorkspaceRoot
    if ($localCommand) {
        return $localCommand
    }

    if ($RequestedCommand) {
        $cmd = Get-Command $RequestedCommand -ErrorAction SilentlyContinue
        if ($cmd) {
            return $RequestedCommand
        }
        if (Test-Path $RequestedCommand) {
            return $RequestedCommand
        }
    }

    return $RequestedCommand
}

function Ensure-QmdAvailable {
    param(
        [string]$WorkspaceRoot,
        [string]$CurrentCommand,
        [string]$SourcePath,
        [string]$RepoUrl,
        [switch]$Verify
    )

    $resolved = Resolve-QmdCommand -RequestedCommand $CurrentCommand -WorkspaceRoot $WorkspaceRoot
    if ($resolved) {
        return [pscustomobject]@{ Command = $resolved; Installed = $false; Source = "existing" }
    }

    if ($Verify) {
        return [pscustomobject]@{ Command = $CurrentCommand; Installed = $false; Source = "missing" }
    }

    if ($SourcePath) {
        $npm = Get-NpmCommand
        if (-not $npm) {
            throw "npm is required to install pk-qmd from a local checkout."
        }
        & $npm install -g $SourcePath
        $installedCommand = if ($CurrentCommand) { $CurrentCommand } else { "pk-qmd" }
        return [pscustomobject]@{ Command = $installedCommand; Installed = $true; Source = $SourcePath }
    }

    $localInstalled = Install-PacketLocalQmdDependency -WorkspaceRoot $WorkspaceRoot
    if ($localInstalled) {
        return [pscustomobject]@{ Command = $localInstalled; Installed = $true; Source = "packet-local" }
    }

    $npm = Get-NpmCommand
    if (-not $npm) {
        throw "npm is required to install pk-qmd."
    }

    $gitSource = Resolve-GitSource -RepoUrl $RepoUrl
    & $npm install -g $gitSource
    $installedCommand = if ($CurrentCommand) { $CurrentCommand } else { "pk-qmd" }
    return [pscustomobject]@{ Command = $installedCommand; Installed = $true; Source = $gitSource }
}

function Invoke-QmdCollectionBootstrap {
    param(
        [string]$CommandName,
        [string]$WorkspaceRoot,
        [string]$CollectionName,
        [string]$ContextText,
        [switch]$SkipEmbed,
        [switch]$Verify
    )

    $results = New-Object System.Collections.Generic.List[string]

    if (-not (Test-QmdFeature -CommandName $CommandName -Pattern "collection add")) {
        $results.Add("$CommandName does not expose collection commands. Install the richer pk-qmd fork before bootstrapping the vault.")
        return $results
    }

    $collectionOutput = ""
    try {
        $collectionOutput = & $CommandName collection list 2>&1 | Out-String
    } catch {
        if ($Verify) {
            $results.Add("Unable to read qmd collections with '$CommandName collection list'")
            return $results
        }
    }

    if ($collectionOutput -notmatch "(?m)^$([regex]::Escape($CollectionName))\s+\(qmd://") {
        if ($Verify) {
            $results.Add("Missing qmd collection: $CollectionName")
            return $results
        }
        & $CommandName collection add $WorkspaceRoot --name $CollectionName
        $results.Add("Added qmd collection: $CollectionName")
    } else {
        $results.Add("qmd collection already present: $CollectionName")
    }

    if ($ContextText) {
        $contextPath = "qmd://$CollectionName/"
        $contextOutput = ""
        try {
            $contextOutput = & $CommandName context list 2>&1 | Out-String
        } catch {
            $contextOutput = ""
        }

        if ($contextOutput -notmatch [regex]::Escape($contextPath)) {
            if ($Verify) {
                $results.Add("Missing qmd context: $contextPath")
            } else {
                & $CommandName context add $contextPath $ContextText
                $results.Add("Added qmd context: $contextPath")
            }
        } else {
            $results.Add("qmd context already present: $contextPath")
        }
    }

    if (-not $Verify) {
        $runnerPath = Join-Path $WorkspaceRoot "scripts\qmd_embed_runner.mjs"
        $node = Get-Command node -ErrorAction SilentlyContinue
        if ($node -and (Test-Path $runnerPath)) {
            $runnerArgs = @($runnerPath, "--workspace", $WorkspaceRoot, "--collection", $CollectionName)
            if ($SkipEmbed) {
                $runnerArgs += "--skip-text"
                $runnerArgs += "--skip-update"
            } elseif ($env:GEMINI_API_KEY) {
                $runnerArgs += "--include-images"
            }
            & node @runnerArgs
            $results.Add("Ran qmd embed runner")
        } elseif (-not $SkipEmbed) {
            & $CommandName update
            & $CommandName embed
            if ($env:GEMINI_API_KEY -and (Test-QmdFeature -CommandName $CommandName -Pattern "membed")) {
                & $CommandName membed
                $results.Add("Ran qmd text + image embeddings")
            } else {
                $results.Add("Ran qmd text embeddings")
            }
        }
    }

    return $results
}

function Initialize-BrvWorkspace {
    param(
        [string]$CommandName,
        [string]$WorkspaceRoot,
        [switch]$Verify
    )

    $configPath = Join-Path $WorkspaceRoot ".brv\config.json"
    if (Test-Path $configPath) {
        return "BRV workspace already initialized"
    }

    if ($Verify) {
        return "Missing BRV workspace config: $configPath"
    }

    Push-Location $WorkspaceRoot
    try {
        & $CommandName init
    } finally {
        Pop-Location
    }

    if (Test-Path $configPath) {
        return "Initialized BRV workspace"
    }

    return "BRV init ran but no config was created at $configPath"
}

function Test-BrvStatus {
    param([string]$CommandName)

    try {
        $output = & $CommandName status --format json 2>&1 | Out-String
        return [pscustomobject]@{ Ok = $true; Output = $output.Trim() }
    } catch {
        return [pscustomobject]@{ Ok = $false; Output = $_.Exception.Message }
    }
}

function Get-BrvProviders {
    param([string]$CommandName)

    try {
        $raw = & $CommandName providers list --format json 2>&1 | Out-String
        return $raw | ConvertFrom-Json
    } catch {
        return $null
    }
}

$WorkspaceRoot = Get-WorkspaceRoot
$config = $null
if (Test-Path $ConfigPath) {
    $config = Get-Content -Path $ConfigPath -Raw | ConvertFrom-Json
}

$QmdRepoUrl = Get-ConfigValue -Preferred $QmdRepoUrl -Fallback $(if ($config) { $config.pk_qmd.repo_url } else { "https://github.com/kingkillery/pk-qmd" })
$QmdCommand = Get-ConfigValue -Preferred $QmdCommand -Fallback $(if ($config) { $config.pk_qmd.command } else { "pk-qmd" })
$QmdCollection = Get-ConfigValue -Preferred $QmdCollection -Fallback $(if ($config -and $config.pk_qmd.collection_name) { $config.pk_qmd.collection_name } else { [IO.Path]::GetFileName($WorkspaceRoot.TrimEnd('\', '/')).ToLowerInvariant().Replace(' ', '-') })
$QmdContext = Get-ConfigValue -Preferred $QmdContext -Fallback $(if ($config -and $config.pk_qmd.context) { $config.pk_qmd.context } else { "Primary llm-wiki-memory vault for $WorkspaceRoot" })
$BrvCommand = Get-ConfigValue -Preferred $BrvCommand -Fallback $(if ($config) { $config.byterover.command } else { "brv" })
$GitvizzFrontendUrl = Get-ConfigValue -Preferred $GitvizzFrontendUrl -Fallback $(if ($config) { $config.gitvizz.frontend_url } else { "http://localhost:3000" })
$GitvizzBackendUrl = Get-ConfigValue -Preferred $GitvizzBackendUrl -Fallback $(if ($config) { $config.gitvizz.backend_url } else { "http://localhost:8003" })
$GitvizzRepoPath = Get-ConfigValue -Preferred $GitvizzRepoPath -Fallback $(if ($config) { $config.gitvizz.repo_path } else { $null })

$summary = New-Object System.Collections.Generic.List[string]
$failures = New-Object System.Collections.Generic.List[string]

if (-not $SkipQmd) {
    $qmd = Ensure-QmdAvailable -WorkspaceRoot $WorkspaceRoot -CurrentCommand $QmdCommand -SourcePath $QmdSource -RepoUrl $QmdRepoUrl -Verify:$VerifyOnly
    $QmdCommand = $qmd.Command

    switch ($qmd.Source) {
        "existing" { $summary.Add("$QmdCommand already installed") }
        "packet-local" { $summary.Add("Installed packet-local pk-qmd dependency into .llm-wiki") }
        "missing" {
            $failures.Add("Missing pk-qmd command: $QmdCommand")
            $summary.Add("Install pk-qmd from the packet dependency manifest, $QmdRepoUrl, or provide -QmdSource")
        }
        default { $summary.Add("Installed pk-qmd from $($qmd.Source)") }
    }

    if ($qmd.Source -ne "missing") {
        try {
            & $QmdCommand status
            $summary.Add("pk-qmd verify: ok")
        } catch {
            $failures.Add("pk-qmd status failed: $($_.Exception.Message)")
        }

        if (-not $SkipMcp) {
            $python = Get-PythonCommand
            if (-not $python) {
                throw "Python is required to write MCP config files."
            }
            $home = [Environment]::GetFolderPath("UserProfile")

            Invoke-JsonMerge -PythonCommand $python -TargetPath (Join-Path $home ".claude\settings.json") -ServerKey "pk-qmd" -CommandName $QmdCommand
            $summary.Add("Updated ~/.claude/settings.json")

            Set-CodexMcp -Path (Join-Path $home ".codex\config.toml") -CommandName $QmdCommand
            $summary.Add("Updated ~/.codex/config.toml")

            Invoke-JsonMerge -PythonCommand $python -TargetPath (Join-Path $home ".factory\mcp.json") -ServerKey "pk-qmd" -CommandName $QmdCommand -FactoryStyle
            $summary.Add("Updated ~/.factory/mcp.json")
        }

        if (-not $SkipQmdBootstrap) {
            foreach ($line in (Invoke-QmdCollectionBootstrap -CommandName $QmdCommand -WorkspaceRoot $WorkspaceRoot -CollectionName $QmdCollection -ContextText $QmdContext -SkipEmbed:$SkipQmdEmbed -Verify:$VerifyOnly)) {
                $summary.Add($line)
            }
        }
    }
}

if (-not $SkipBrv) {
    $brvExists = Get-Command $BrvCommand -ErrorAction SilentlyContinue
    if ($brvExists) {
        $summary.Add("$BrvCommand already installed")
    } elseif ($VerifyOnly) {
        $failures.Add("Missing Byterover command: $BrvCommand")
    } else {
        $npm = Get-NpmCommand
        if (-not $npm) {
            throw "npm is required to install brv."
        }
        & $npm install -g byterover-cli
        $summary.Add("Installed brv from npm")
    }

    if ((Get-Command $BrvCommand -ErrorAction SilentlyContinue)) {
        $brvStatus = Test-BrvStatus -CommandName $BrvCommand
        if ($brvStatus.Ok) {
            $summary.Add("brv verify: ok")
        } else {
            $failures.Add("brv status failed: $($brvStatus.Output)")
        }

        $providers = Get-BrvProviders -CommandName $BrvCommand
        if ($providers -and $providers.success -and $providers.data.providers) {
            $connectedProvider = $providers.data.providers | Where-Object { $_.isConnected -eq $true } | Select-Object -First 1
            if ($connectedProvider) {
                $summary.Add("brv provider connected: $($connectedProvider.id)")
            } else {
                $summary.Add("Next BRV steps: connect a provider before using brv_query/brv_curate, e.g. 'brv providers connect byterover' or another supported provider")
            }
        }

        if (-not $env:BYTEROVER_API_KEY) {
            $summary.Add("Optional BRV cloud auth: brv login --api-key <key> or export BYTEROVER_API_KEY")
        }

        if (-not $SkipBrvInit) {
            $summary.Add((Initialize-BrvWorkspace -CommandName $BrvCommand -WorkspaceRoot $WorkspaceRoot -Verify:$VerifyOnly))
        }
    }
}

if (-not $SkipGitvizzStart) {
    $summary.Add((Start-GitVizzIfNeeded -RepoPath $GitvizzRepoPath -FrontendUrl $GitvizzFrontendUrl -BackendUrl $GitvizzBackendUrl -Verify:$VerifyOnly))
}

if (Test-TcpUrl -Url $GitvizzFrontendUrl) {
    $summary.Add("GitVizz frontend reachable: $GitvizzFrontendUrl")
} else {
    $failures.Add("GitVizz frontend unreachable: $GitvizzFrontendUrl")
}

if (Test-TcpUrl -Url $GitvizzBackendUrl) {
    $summary.Add("GitVizz backend reachable: $GitvizzBackendUrl")
} else {
    $failures.Add("GitVizz backend unreachable: $GitvizzBackendUrl")
}

$summary | ForEach-Object { Write-Output $_ }

if ($failures.Count -gt 0) {
    Write-Error ($failures -join "`n")
    exit 1
}
