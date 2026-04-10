param(
    [string]$ConfigPath,
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
    [switch]$SkipGitvizz,
    [switch]$SkipGitvizzStart,
    [switch]$AllowGlobalToolInstall,
    [switch]$VerifyOnly
)

$ErrorActionPreference = "Stop"

function Resolve-ScriptWorkspaceRoot {
    $scriptParent = Split-Path -Parent $PSScriptRoot
    $scriptGrandparent = Split-Path -Parent $scriptParent

    if (Test-Path (Join-Path $scriptParent ".llm-wiki\config.json")) {
        return $scriptParent
    }

    if (Test-Path (Join-Path $scriptGrandparent ".llm-wiki\config.json")) {
        return $scriptGrandparent
    }

    return $scriptParent
}

function Test-EnvFlag {
    param([string]$Name)

    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($value)) {
        return $false
    }
    return $value.Trim().ToLowerInvariant() -in @("1", "true", "yes", "on")
}

function Get-WorkspaceRoot {
    $resolvedRoot = Resolve-ScriptWorkspaceRoot
    if (Test-Path (Join-Path $resolvedRoot ".llm-wiki\config.json")) {
        return $resolvedRoot
    }
    return (Get-Location).Path
}

if (-not $PSBoundParameters.ContainsKey("ConfigPath") -or [string]::IsNullOrWhiteSpace($ConfigPath)) {
    $ConfigPath = Join-Path (Resolve-ScriptWorkspaceRoot) ".llm-wiki\config.json"
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

function Ensure-LocalQmdManifest {
    param(
        [string]$WorkspaceRoot,
        [string]$RepoUrl
    )

    $manifestPath = Get-LocalQmdManifestPath -WorkspaceRoot $WorkspaceRoot
    if (Test-Path $manifestPath) {
        return $manifestPath
    }

    $dependencySpec = Resolve-GitSource -RepoUrl $(if ($RepoUrl) { $RepoUrl } else { "https://github.com/kingkillery/pk-qmd" })
    $rootPackagePath = Join-Path $WorkspaceRoot "package.json"
    if (Test-Path $rootPackagePath) {
        try {
            $rootPackage = Get-Content -Path $rootPackagePath -Raw | ConvertFrom-Json
            $rootDependency = $rootPackage.dependencies.'@kingkillery/pk-qmd'
            if (-not [string]::IsNullOrWhiteSpace($rootDependency)) {
                $dependencySpec = [string]$rootDependency
            }
        } catch {
        }
    }

    $manifestDir = Split-Path -Parent $manifestPath
    if (-not (Test-Path $manifestDir)) {
        New-Item -ItemType Directory -Force -Path $manifestDir | Out-Null
    }

    $manifest = [ordered]@{
        name = "llm-wiki-memory-local"
        private = $true
        version = "0.1.0"
        description = "Local dependency bundle for llm-wiki-memory"
        dependencies = [ordered]@{
            "@kingkillery/pk-qmd" = $dependencySpec
        }
    }

    Set-Content -Path $manifestPath -Value (($manifest | ConvertTo-Json -Depth 5) + "`n") -Encoding utf8
    return $manifestPath
}

function Get-LocalQmdCommandPath {
    param([string]$WorkspaceRoot)
    $isWindows = $false
    if ($PSVersionTable.PSVersion -lt "6.0" -or $IsWindows) {
        $isWindows = $true
    }

    $candidates = @((Join-Path $WorkspaceRoot ".llm-wiki\node_modules\@kingkillery\pk-qmd\dist\cli\qmd.js"))
    if (-not $isWindows) {
        $candidates += @(
            (Join-Path $WorkspaceRoot ".llm-wiki\node_modules\.bin\pk-qmd"),
            (Join-Path $WorkspaceRoot ".llm-wiki\node_modules\.bin\pk-qmd.ps1"),
            (Join-Path $WorkspaceRoot ".llm-wiki\node_modules\.bin\pk-qmd.cmd")
        )
    }

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }
    return $null
}

function Get-LocalQmdSourceCommandPath {
    param([string]$SourcePath)

    if ([string]::IsNullOrWhiteSpace($SourcePath)) {
        return $null
    }

    $candidates = @(
        (Join-Path $SourcePath "dist\cli\qmd.js"),
        (Join-Path $SourcePath "bin\qmd.ps1"),
        (Join-Path $SourcePath "bin\qmd.cmd"),
        (Join-Path $SourcePath "bin\qmd"),
        (Join-Path $SourcePath "bin\pk-qmd.ps1"),
        (Join-Path $SourcePath "bin\pk-qmd.cmd"),
        (Join-Path $SourcePath "bin\pk-qmd")
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }
    return $null
}

function Resolve-InstalledQmdCommand {
    param(
        [string]$RequestedCommand,
        [string]$WorkspaceRoot
    )

    $localCommand = Get-LocalQmdCommandPath -WorkspaceRoot $WorkspaceRoot
    if ($localCommand) {
        return $localCommand
    }

    if ($RequestedCommand) {
        $requested = Get-Command $RequestedCommand -ErrorAction SilentlyContinue
        if ($requested) {
            return $RequestedCommand
        }
        if (Test-Path $RequestedCommand) {
            return $RequestedCommand
        }
    }

    $defaultQmd = Get-Command "pk-qmd" -ErrorAction SilentlyContinue
    if ($defaultQmd) {
        return "pk-qmd"
    }

    return $null
}

function Get-LocalBrvCommandPath {
    param([string]$WorkspaceRoot)
    $candidates = @(
        (Join-Path $WorkspaceRoot ".llm-wiki\node_modules\.bin\brv.ps1"),
        (Join-Path $WorkspaceRoot ".llm-wiki\node_modules\.bin\brv.cmd"),
        (Join-Path $WorkspaceRoot ".llm-wiki\node_modules\.bin\brv")
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

    $script = @'
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
'@

    $tempScript = [System.IO.Path]::GetTempFileName()
    try {
        Set-Content -Path $tempScript -Value $script -Encoding utf8
        & $PythonCommand $tempScript $TargetPath $ServerKey $CommandName $(if ($FactoryStyle) { "1" } else { "0" }) | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to update MCP config at $TargetPath"
        }
    } finally {
        if (Test-Path $tempScript) {
            Remove-Item -LiteralPath $tempScript -Force -ErrorAction SilentlyContinue
        }
    }
}

function Invoke-JsonMergeServer {
    param(
        [string]$PythonCommand,
        [string]$TargetPath,
        [string]$ServerKey,
        [string]$CommandName,
        [string[]]$Args,
        [switch]$FactoryStyle
    )

    $argsJson = if ($Args) { $Args | ConvertTo-Json -Compress } else { "[]" }
    $script = @'
from pathlib import Path
import json
import sys

path = Path(sys.argv[1]).expanduser()
server_key = sys.argv[2]
command_name = sys.argv[3]
args = json.loads(sys.argv[4])
factory_style = sys.argv[5] == "1"

data = {}
if path.exists():
    raw = path.read_text(encoding="utf-8").strip()
    if raw:
        data = json.loads(raw)

mcp = data.get("mcpServers")
if not isinstance(mcp, dict):
    mcp = {}
data["mcpServers"] = mcp

payload = {"command": command_name, "args": args}
if factory_style:
    payload = {"type": "stdio", "command": command_name, "args": args, "disabled": False}

mcp[server_key] = payload
mcp.pop("qmd", None)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
'@

    $tempScript = [System.IO.Path]::GetTempFileName()
    try {
        Set-Content -Path $tempScript -Value $script -Encoding utf8
        & $PythonCommand $tempScript $TargetPath $ServerKey $CommandName $argsJson $(if ($FactoryStyle) { "1" } else { "0" }) | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to update MCP config at $TargetPath"
        }
    } finally {
        if (Test-Path $tempScript) {
            Remove-Item -LiteralPath $tempScript -Force -ErrorAction SilentlyContinue
        }
    }
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

function Set-CodexMcpServer {
    param(
        [string]$PythonCommand,
        [string]$Path,
        [string]$ServerKey,
        [string]$CommandName,
        [string[]]$Args
    )

    $argsJson = if ($Args) { $Args | ConvertTo-Json -Compress } else { "[]" }
    $script = @'
from pathlib import Path
import json
import re
import sys

path = Path(sys.argv[1]).expanduser()
server_key = sys.argv[2]
command_name = sys.argv[3]
args = json.loads(sys.argv[4])
content = path.read_text(encoding="utf-8") if path.exists() else ""
args_literal = "[" + ", ".join(json.dumps(value) for value in args) + "]"
block = f"[mcp_servers.{server_key}]\ncommand = {json.dumps(command_name)}\nargs = {args_literal}\n"
section = re.compile(rf"(?ms)^\[mcp_servers\.{re.escape(server_key)}\]\r?\n(?:.*?)(?=^\[|\Z)")

if section.search(content):
    content = section.sub(block + "\n", content)
else:
    if content and not content.endswith("\n"):
        content += "\n"
    content += "\n" + block + "\n"

if server_key != "qmd":
    legacy = re.compile(r"(?ms)^\[mcp_servers\.qmd\]\r?\n(?:.*?)(?=^\[|\Z)")
    content = legacy.sub("", content)

path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(content, encoding="utf-8")
'@

    $tempScript = [System.IO.Path]::GetTempFileName()
    try {
        Set-Content -Path $tempScript -Value $script -Encoding utf8
        & $PythonCommand $tempScript $Path $ServerKey $CommandName $argsJson | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to update Codex MCP config at $Path"
        }
    } finally {
        if (Test-Path $tempScript) {
            Remove-Item -LiteralPath $tempScript -Force -ErrorAction SilentlyContinue
        }
    }
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
        $invocation = Get-CommandInvocation -CommandName $CommandName
        $output = & $invocation.Command @($invocation.Arguments) 2>&1 | Out-String
        return $output -match [regex]::Escape($Pattern)
    } catch {
        return $false
    }
}

function Get-CommandInvocation {
    param(
        [string]$CommandName,
        [string[]]$Arguments
    )

    if ([string]::IsNullOrWhiteSpace($CommandName)) {
        throw "Command name is required."
    }

    if ($CommandName.EndsWith(".js")) {
        $node = Get-Command node -ErrorAction SilentlyContinue
        if (-not $node) {
            throw "node is required to run $CommandName"
        }
        return [pscustomobject]@{
            Command = $node.Name
            Arguments = @($CommandName) + $Arguments
        }
    }

    return [pscustomobject]@{
        Command = $CommandName
        Arguments = @($Arguments)
    }
}

function Invoke-CommandChecked {
    param(
        [string]$CommandName,
        [string[]]$Arguments
    )

    $invocation = Get-CommandInvocation -CommandName $CommandName -Arguments $Arguments
    $output = & $invocation.Command @($invocation.Arguments) 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        $argumentText = if ($invocation.Arguments) { $invocation.Arguments -join " " } else { "" }
        $message = "$($invocation.Command) $argumentText failed"
        if (-not [string]::IsNullOrWhiteSpace($output)) {
            $message += ": $($output.Trim())"
        }
        throw $message
    }
    return $output
}

function Install-PacketLocalQmdDependency {
    param(
        [string]$WorkspaceRoot,
        [string]$RepoUrl
    )

    $manifestPath = Ensure-LocalQmdManifest -WorkspaceRoot $WorkspaceRoot -RepoUrl $RepoUrl

    $npm = Get-NpmCommand
    if (-not $npm) {
        return $null
    }

    & $npm install --prefix (Split-Path -Parent $manifestPath) | Out-Null
    return (Get-LocalQmdCommandPath -WorkspaceRoot $WorkspaceRoot)
}

function Install-PacketLocalBrvDependency {
    param([string]$WorkspaceRoot)

    $manifestPath = Get-LocalQmdManifestPath -WorkspaceRoot $WorkspaceRoot
    if (-not (Test-Path $manifestPath)) {
        return $null
    }

    $npm = Get-NpmCommand
    if (-not $npm) {
        return $null
    }

    & $npm install --prefix (Split-Path -Parent $manifestPath) | Out-Null
    return (Get-LocalBrvCommandPath -WorkspaceRoot $WorkspaceRoot)
}

function Resolve-QmdCommand {
    param(
        [string]$RequestedCommand,
        [string]$WorkspaceRoot,
        [string]$SourcePath,
        [string]$RepoUrl,
        [switch]$AllowGlobalToolInstall,
        [switch]$Verify
    )

    $localCommand = Get-LocalQmdCommandPath -WorkspaceRoot $WorkspaceRoot
    if ($localCommand) {
        return [pscustomobject]@{ Command = $localCommand; Installed = $false; Source = "existing" }
    }

    if ($RequestedCommand) {
        $cmd = Get-Command $RequestedCommand -ErrorAction SilentlyContinue
        if ($cmd) {
            return [pscustomobject]@{ Command = $RequestedCommand; Installed = $false; Source = "existing" }
        }
        if (Test-Path $RequestedCommand) {
            return [pscustomobject]@{ Command = $RequestedCommand; Installed = $false; Source = "existing" }
        }
    }

    if ($Verify) {
        return [pscustomobject]@{ Command = $RequestedCommand; Installed = $false; Source = "missing" }
    }

    if ($SourcePath) {
        $sourceCommand = Get-LocalQmdSourceCommandPath -SourcePath $SourcePath
        if ($sourceCommand) {
            return [pscustomobject]@{
                Command = $sourceCommand
                Installed = $false
                Source = "source-checkout"
                Message = "Using pk-qmd from local checkout: $SourcePath"
            }
        }
        if (-not $AllowGlobalToolInstall) {
            return [pscustomobject]@{
                Command = $(if ($RequestedCommand) { $RequestedCommand } else { "pk-qmd" })
                Installed = $false
                Source = "manual-required"
                Message = "pk-qmd global install is disabled. Install from $SourcePath manually or rerun with -AllowGlobalToolInstall."
            }
        }
        $npm = Get-NpmCommand
        if (-not $npm) {
            return [pscustomobject]@{
                Command = $(if ($RequestedCommand) { $RequestedCommand } else { "pk-qmd" })
                Installed = $false
                Source = "manual-required"
                Message = "npm is required to install pk-qmd from $SourcePath."
            }
        }
        & $npm install -g $SourcePath | Out-Null
        $installedCommand = Resolve-InstalledQmdCommand -RequestedCommand $RequestedCommand -WorkspaceRoot $WorkspaceRoot
        if (-not $installedCommand) {
            throw "pk-qmd install completed from $SourcePath but no runnable command was found."
        }
        return [pscustomobject]@{ Command = $installedCommand; Installed = $true; Source = $SourcePath }
    }

    $localInstalled = Install-PacketLocalQmdDependency -WorkspaceRoot $WorkspaceRoot -RepoUrl $RepoUrl
    if ($localInstalled) {
        return [pscustomobject]@{ Command = $localInstalled; Installed = $true; Source = "packet-local" }
    }

    $gitSource = Resolve-GitSource -RepoUrl $RepoUrl
    if (-not $AllowGlobalToolInstall) {
        return [pscustomobject]@{
            Command = $(if ($RequestedCommand) { $RequestedCommand } else { "pk-qmd" })
            Installed = $false
            Source = "manual-required"
            Message = "pk-qmd is missing and packet-local install was unavailable. Install $gitSource manually or rerun with -AllowGlobalToolInstall."
        }
    }

    $npm = Get-NpmCommand
    if (-not $npm) {
        return [pscustomobject]@{
            Command = $(if ($RequestedCommand) { $RequestedCommand } else { "pk-qmd" })
            Installed = $false
            Source = "manual-required"
            Message = "npm is required to install pk-qmd from $gitSource."
        }
    }

    & $npm install -g $gitSource | Out-Null
    $installedCommand = Resolve-InstalledQmdCommand -RequestedCommand $RequestedCommand -WorkspaceRoot $WorkspaceRoot
    if (-not $installedCommand) {
        throw "pk-qmd install completed from $gitSource but no runnable command was found."
    }
    return [pscustomobject]@{ Command = $installedCommand; Installed = $true; Source = $gitSource }
}

function Ensure-QmdAvailable {
    param(
        [string]$WorkspaceRoot,
        [string]$CurrentCommand,
        [string]$SourcePath,
        [string]$RepoUrl,
        [switch]$AllowGlobalToolInstall,
        [switch]$Verify
    )

    return (Resolve-QmdCommand -RequestedCommand $CurrentCommand -WorkspaceRoot $WorkspaceRoot -SourcePath $SourcePath -RepoUrl $RepoUrl -AllowGlobalToolInstall:$AllowGlobalToolInstall -Verify:$Verify)
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
        $collectionOutput = Invoke-CommandChecked -CommandName $CommandName -Arguments @("collection", "list")
    } catch {
        if ($Verify) {
            $results.Add("Unable to read qmd collections with '$CommandName collection list'")
            return $results
        }
        throw
    }

    if ($collectionOutput -notmatch "(?m)^$([regex]::Escape($CollectionName))\s+\(qmd://") {
        if ($Verify) {
            $results.Add("Missing qmd collection: $CollectionName")
            return $results
        }
        Invoke-CommandChecked -CommandName $CommandName -Arguments @("collection", "add", $WorkspaceRoot, "--name", $CollectionName) | Out-Null
        $results.Add("Added qmd collection: $CollectionName")
    } else {
        $results.Add("qmd collection already present: $CollectionName")
    }

    if ($ContextText) {
        $contextPath = "qmd://$CollectionName/"
        $contextOutput = ""
        try {
            $contextOutput = Invoke-CommandChecked -CommandName $CommandName -Arguments @("context", "list")
        } catch {
            $contextOutput = ""
        }

        if ($contextOutput -notmatch [regex]::Escape($contextPath)) {
            if ($Verify) {
                $results.Add("Missing qmd context: $contextPath")
            } else {
                Invoke-CommandChecked -CommandName $CommandName -Arguments @("context", "add", $contextPath, $ContextText) | Out-Null
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
            Invoke-CommandChecked -CommandName "node" -Arguments $runnerArgs | Out-Null
            $results.Add("Ran qmd embed runner")
        } elseif (-not $SkipEmbed) {
            Invoke-CommandChecked -CommandName $CommandName -Arguments @("update") | Out-Null
            Invoke-CommandChecked -CommandName $CommandName -Arguments @("embed") | Out-Null
            if ($env:GEMINI_API_KEY -and (Test-QmdFeature -CommandName $CommandName -Pattern "membed")) {
                Invoke-CommandChecked -CommandName $CommandName -Arguments @("membed") | Out-Null
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
        & $CommandName status --format json | Out-Null
    } finally {
        Pop-Location
    }

    if (Test-Path $configPath) {
        return "Initialized BRV workspace via status"
    }

    return "BRV status ran but no config was created at $configPath"
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
$SkillServerKey = if ($config -and $config.skills.mcp_server_key) { [string]$config.skills.mcp_server_key } else { "llm-wiki-skills" }
$SkillScriptRelativePath = if ($config -and $config.skills.script_path) { [string]$config.skills.script_path } else { "scripts\llm_wiki_skill_mcp.py" }
if (-not $AllowGlobalToolInstall -and (Test-EnvFlag -Name "LLM_WIKI_ALLOW_GLOBAL_TOOL_INSTALL")) {
    $AllowGlobalToolInstall = $true
}

$summary = New-Object System.Collections.Generic.List[string]
$failures = New-Object System.Collections.Generic.List[string]
if ($AllowGlobalToolInstall) {
    $summary.Add("Global tool install fallback enabled")
} else {
    $summary.Add("Global tool install fallback disabled; packet-local installs only")
}

if (-not $SkipQmd) {
    $qmd = Ensure-QmdAvailable -WorkspaceRoot $WorkspaceRoot -CurrentCommand $QmdCommand -SourcePath $QmdSource -RepoUrl $QmdRepoUrl -AllowGlobalToolInstall:$AllowGlobalToolInstall -Verify:$VerifyOnly
    $QmdCommand = $qmd.Command

    switch ($qmd.Source) {
        "existing" { $summary.Add("$QmdCommand already installed") }
        "packet-local" { $summary.Add("Installed packet-local pk-qmd dependency into .llm-wiki") }
        "source-checkout" { $summary.Add($qmd.Message) }
        "manual-required" {
            $failures.Add($qmd.Message)
            $summary.Add($qmd.Message)
        }
        "missing" {
            $failures.Add("Missing pk-qmd command: $QmdCommand")
            $summary.Add("Install pk-qmd from the packet dependency manifest, $QmdRepoUrl, or provide -QmdSource")
        }
        default { $summary.Add("Installed pk-qmd from $($qmd.Source)") }
    }

    if ($qmd.Source -notin @("missing", "manual-required")) {
        try {
            Invoke-CommandChecked -CommandName $QmdCommand -Arguments @("status") | Out-Null
            $summary.Add("pk-qmd verify: ok")
        } catch {
            $failures.Add("pk-qmd status failed: $($_.Exception.Message)")
        }

        if (-not $SkipMcp) {
            $python = Get-PythonCommand
            if (-not $python) {
                throw "Python is required to write MCP config files."
            }
            $userHome = [Environment]::GetFolderPath("UserProfile")

            $qmdServerInvocation = Get-CommandInvocation -CommandName $QmdCommand -Arguments @("mcp")

            Invoke-JsonMergeServer -PythonCommand $python -TargetPath (Join-Path $userHome ".claude\settings.json") -ServerKey "pk-qmd" -CommandName $qmdServerInvocation.Command -Args $qmdServerInvocation.Arguments
            $summary.Add("Updated ~/.claude/settings.json")

            Set-CodexMcpServer -PythonCommand $python -Path (Join-Path $userHome ".codex\config.toml") -ServerKey "pk-qmd" -CommandName $qmdServerInvocation.Command -Args $qmdServerInvocation.Arguments
            $summary.Add("Updated ~/.codex/config.toml")

            Invoke-JsonMergeServer -PythonCommand $python -TargetPath (Join-Path $userHome ".factory\mcp.json") -ServerKey "pk-qmd" -CommandName $qmdServerInvocation.Command -Args $qmdServerInvocation.Arguments -FactoryStyle
            $summary.Add("Updated ~/.factory/mcp.json")

            $skillScriptPath = Join-Path $WorkspaceRoot $SkillScriptRelativePath
            if (Test-Path $skillScriptPath) {
                $skillArgs = @($skillScriptPath, "mcp", "--workspace", $WorkspaceRoot)
                Invoke-JsonMergeServer -PythonCommand $python -TargetPath (Join-Path $userHome ".claude\settings.json") -ServerKey $SkillServerKey -CommandName $python -Args $skillArgs
                $summary.Add("Updated ~/.claude/settings.json for $SkillServerKey")

                Set-CodexMcpServer -PythonCommand $python -Path (Join-Path $userHome ".codex\config.toml") -ServerKey $SkillServerKey -CommandName $python -Args $skillArgs
                $summary.Add("Updated ~/.codex/config.toml for $SkillServerKey")

                Invoke-JsonMergeServer -PythonCommand $python -TargetPath (Join-Path $userHome ".factory\mcp.json") -ServerKey $SkillServerKey -CommandName $python -Args $skillArgs -FactoryStyle
                $summary.Add("Updated ~/.factory/mcp.json for $SkillServerKey")
            } else {
                $summary.Add("Skill MCP script not found, skipping $SkillServerKey MCP wiring")
            }
        }

        if (-not $SkipQmdBootstrap) {
            foreach ($line in (Invoke-QmdCollectionBootstrap -CommandName $QmdCommand -WorkspaceRoot $WorkspaceRoot -CollectionName $QmdCollection -ContextText $QmdContext -SkipEmbed:$SkipQmdEmbed -Verify:$VerifyOnly)) {
                $summary.Add($line)
            }
        }
    }
}

if (-not $SkipBrv) {
    $localBrv = Get-LocalBrvCommandPath -WorkspaceRoot $WorkspaceRoot
    if ($localBrv) {
        $BrvCommand = $localBrv
        $summary.Add("Using packet-local brv dependency at $BrvCommand")
    } else {
        $brvExists = Get-Command $BrvCommand -ErrorAction SilentlyContinue
        if ($brvExists) {
            $summary.Add("$BrvCommand already installed")
        } elseif ($VerifyOnly) {
            $failures.Add("Missing Byterover command: $BrvCommand")
        } else {
            $localInstalledBrv = Install-PacketLocalBrvDependency -WorkspaceRoot $WorkspaceRoot
            if ($localInstalledBrv) {
                $BrvCommand = $localInstalledBrv
                $summary.Add("Installed packet-local brv dependency into .llm-wiki")
            } elseif (-not $AllowGlobalToolInstall) {
                $failures.Add("Missing Byterover command: $BrvCommand")
                $summary.Add("Global brv install is disabled. Install byterover-cli manually or rerun with -AllowGlobalToolInstall.")
            } else {
                $npm = Get-NpmCommand
                if (-not $npm) {
                    $failures.Add("Missing Byterover command: $BrvCommand")
                    $summary.Add("npm is required to install brv.")
                } else {
                    & $npm install -g byterover-cli
                    $summary.Add("Installed brv from npm")
                }
            }
        }
    }

    if ((Get-Command $BrvCommand -ErrorAction SilentlyContinue) -or (Test-Path $BrvCommand)) {
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

if ($SkipGitvizz) {
    $SkipGitvizzStart = $true
}

if (-not $SkipGitvizzStart) {
    $summary.Add((Start-GitVizzIfNeeded -RepoPath $GitvizzRepoPath -FrontendUrl $GitvizzFrontendUrl -BackendUrl $GitvizzBackendUrl -Verify:$VerifyOnly))
}

if ($SkipGitvizz) {
    $summary.Add("GitVizz checks skipped")
} else {
    $gitvizzManaged = -not [string]::IsNullOrWhiteSpace([string]$GitvizzRepoPath)
    $frontendReachable = Test-TcpUrl -Url $GitvizzFrontendUrl
    $backendReachable = Test-TcpUrl -Url $GitvizzBackendUrl

    if ($frontendReachable) {
        $summary.Add("GitVizz frontend reachable: $GitvizzFrontendUrl")
    } else {
        if ($gitvizzManaged) {
            $failures.Add("GitVizz frontend unreachable: $GitvizzFrontendUrl")
        } else {
            $summary.Add("GitVizz frontend unreachable but repo_path is not configured; skipping reachability enforcement during setup")
        }
    }

    if ($backendReachable) {
        $summary.Add("GitVizz backend reachable: $GitvizzBackendUrl")
    } else {
        if ($gitvizzManaged) {
            $failures.Add("GitVizz backend unreachable: $GitvizzBackendUrl")
        } else {
            $summary.Add("GitVizz backend unreachable but repo_path is not configured; skipping reachability enforcement during setup")
        }
    }
}

$summary | ForEach-Object { Write-Output $_ }

if ($failures.Count -gt 0) {
    Write-Error ($failures -join "`n")
    exit 1
}
