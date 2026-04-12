param(
    [string]$WorkspaceRoot,
    [string]$ConfigPath = $(Join-Path (Split-Path -Parent $PSScriptRoot) ".llm-wiki\config.json"),
    [switch]$SkipGitvizz
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
        $bashScript = Join-Path $scriptDir "check_llm_wiki_memory.sh"
        if (Test-Path $bashScript) {
            $bashArgs = @()
            if ($SkipGitvizz) { $bashArgs += "--skip-gitvizz" }
            if ($WorkspaceRoot) {
                $bashArgs += (Join-Path $WorkspaceRoot ".llm-wiki\config.json")
            } elseif ($ConfigPath) {
                $bashArgs += $ConfigPath
            }
            & $bash $bashScript @bashArgs
            exit $LASTEXITCODE
        }
    }
}

if ($WorkspaceRoot -and (-not $PSBoundParameters.ContainsKey("ConfigPath") -or [string]::IsNullOrWhiteSpace($ConfigPath))) {
    $ConfigPath = Join-Path $WorkspaceRoot ".llm-wiki\config.json"
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

function Get-CommandInvocation {
    param(
        [string]$CommandName,
        [string[]]$Arguments
    )

    if ([string]::IsNullOrWhiteSpace($CommandName)) {
        throw "Command name is required."
    }

    if ($CommandName.EndsWith(".js")) {
        return [pscustomobject]@{
            Command = "node"
            Arguments = @($CommandName) + $Arguments
        }
    }

    return [pscustomobject]@{
        Command = $CommandName
        Arguments = @($Arguments)
    }
}

function Resolve-OptionalPath {
    param(
        [string]$PathValue,
        [string]$WorkspaceRoot
    )

    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        return $null
    }

    try {
        if ([System.IO.Path]::IsPathRooted($PathValue)) {
            return [System.IO.Path]::GetFullPath($PathValue)
        }
    } catch {
        return $PathValue
    }

    return [System.IO.Path]::GetFullPath((Join-Path $WorkspaceRoot $PathValue))
}

if (-not (Test-Path $ConfigPath)) {
    Write-Error "Stack config not found: $ConfigPath"
    exit 1
}

$config = Get-Content -Path $ConfigPath -Raw | ConvertFrom-Json
$workspaceRoot = Split-Path -Parent (Split-Path -Parent $ConfigPath)
$qmdCommandCandidates = @()
if ($config.pk_qmd.local_command_candidates) {
    foreach ($candidate in $config.pk_qmd.local_command_candidates) {
        $qmdCommandCandidates += (Resolve-OptionalPath -PathValue ([string]$candidate) -WorkspaceRoot $workspaceRoot)
    }
}
$qmdCommand = $config.pk_qmd.command
foreach ($candidate in $qmdCommandCandidates) {
    if (Test-Path $candidate) {
        $qmdCommand = $candidate
        break
    }
}
$brvCommandCandidates = @()
if ($config.byterover.local_command_candidates) {
    foreach ($candidate in $config.byterover.local_command_candidates) {
        $brvCommandCandidates += (Resolve-OptionalPath -PathValue ([string]$candidate) -WorkspaceRoot $workspaceRoot)
    }
}
$brvCommand = $config.byterover.command
foreach ($candidate in $brvCommandCandidates) {
    if (Test-Path $candidate) {
        $brvCommand = $candidate
        break
    }
}
$collectionName = if ($config.pk_qmd.collection_name) { $config.pk_qmd.collection_name } else { [IO.Path]::GetFileName($workspaceRoot.TrimEnd('\', '/')).ToLowerInvariant().Replace(' ', '-') }
$frontendUrl = $config.gitvizz.frontend_url
$backendUrl = $config.gitvizz.backend_url
$skillScriptRelative = if ($config.skills -and $config.skills.script_path) { [string]$config.skills.script_path } else { "scripts/llm_wiki_skill_mcp.py" }
$skillRegistryRelative = if ($config.skills -and $config.skills.registry_path) { [string]$config.skills.registry_path } else { ".llm-wiki/skills-registry.json" }
$pipelineConfig = $config.skills.pipeline
$briefDirRelative = if ($pipelineConfig -and $pipelineConfig.brief_dir) { [string]$pipelineConfig.brief_dir } else { ".llm-wiki/skill-pipeline/briefs" }
$deltaDirRelative = if ($pipelineConfig -and $pipelineConfig.delta_dir) { [string]$pipelineConfig.delta_dir } else { ".llm-wiki/skill-pipeline/deltas" }
$validationDirRelative = if ($pipelineConfig -and $pipelineConfig.validation_dir) { [string]$pipelineConfig.validation_dir } else { ".llm-wiki/skill-pipeline/validations" }
$packetDirRelative = if ($pipelineConfig -and $pipelineConfig.packet_dir) { [string]$pipelineConfig.packet_dir } else { ".llm-wiki/skill-pipeline/packets" }
$skillScriptPath = Join-Path $workspaceRoot $skillScriptRelative
$skillRegistryPath = Join-Path $workspaceRoot $skillRegistryRelative
$briefDir = Join-Path $workspaceRoot $briefDirRelative
$deltaDir = Join-Path $workspaceRoot $deltaDirRelative
$validationDir = Join-Path $workspaceRoot $validationDirRelative
$packetDir = Join-Path $workspaceRoot $packetDirRelative
$failures = New-Object System.Collections.Generic.List[string]

Write-Output "=== llm-wiki-memory health check ==="
Write-Output "Config: $ConfigPath"
if ($config.memory_base) {
    Write-Output "Memory base: $($config.memory_base.name) -> $($config.memory_base.vault_path)"
    if ($config.memory_base.vault_id) {
        Write-Output "Memory base id: $($config.memory_base.vault_id)"
    }
}

if (-not ((Get-Command $qmdCommand -ErrorAction SilentlyContinue) -or (Test-Path $qmdCommand))) {
    $failures.Add("Missing pk-qmd command: $qmdCommand")
} else {
    Write-Output "`n=== pk-qmd ==="
    try {
        $invocation = Get-CommandInvocation -CommandName $qmdCommand -Arguments @("status")
        & $invocation.Command @($invocation.Arguments)
    } catch {
        Write-Warning "pk-qmd status failed: $($_.Exception.Message)"
    }

    try {
        $helpInvocation = Get-CommandInvocation -CommandName $qmdCommand -Arguments @()
        $helpText = & $helpInvocation.Command @($helpInvocation.Arguments) 2>&1 | Out-String
        if ($helpText -match "collection add") {
            $collectionInvocation = Get-CommandInvocation -CommandName $qmdCommand -Arguments @("collection", "list")
            $collections = & $collectionInvocation.Command @($collectionInvocation.Arguments) 2>&1 | Out-String
            if ($collections -notmatch "(?m)^$([regex]::Escape($collectionName))\s+\(qmd://") {
                $failures.Add("Missing qmd collection: $collectionName")
            }
        } else {
            Write-Warning "$qmdCommand does not expose collection commands; collection bootstrap could not be verified."
        }
    } catch {
        Write-Warning "qmd collection verification failed: $($_.Exception.Message)"
    }
}

if (-not ((Get-Command $brvCommand -ErrorAction SilentlyContinue) -or (Test-Path $brvCommand))) {
    $failures.Add("Missing Byterover command: $brvCommand")
} else {
    Write-Output "`n=== Byterover ==="
    try {
        & $brvCommand status
    } catch {
        Write-Warning "brv status failed: $($_.Exception.Message)"
    }

    if (-not $env:BYTEROVER_API_KEY) {
        Write-Warning "BYTEROVER_API_KEY is not set. Login or export the API key before first use."
    }

    if (-not (Test-Path (Join-Path $workspaceRoot ".brv\config.json"))) {
        $failures.Add("Missing BRV workspace config: $(Join-Path $workspaceRoot '.brv\config.json')")
    }
}

Write-Output "`n=== Skill Pipeline ==="
if (-not (Test-Path $skillScriptPath)) {
    $failures.Add("Missing skill MCP script: $skillScriptPath")
}
if (-not (Test-Path $skillRegistryPath)) {
    $failures.Add("Missing skill registry: $skillRegistryPath")
} else {
    try {
        $skillRegistry = Get-Content -Raw -Path $skillRegistryPath | ConvertFrom-Json
        if (-not $skillRegistry.PSObject.Properties.Name.Contains("packets")) {
            $failures.Add("Skill registry missing packets collection: $skillRegistryPath")
        }
    } catch {
        $failures.Add("Skill registry is not valid JSON: $skillRegistryPath")
    }
}
if (-not (Test-Path $briefDir)) {
    $failures.Add("Missing skill brief directory: $briefDir")
}
if (-not (Test-Path $deltaDir)) {
    $failures.Add("Missing skill delta directory: $deltaDir")
}
if (-not (Test-Path $validationDir)) {
    $failures.Add("Missing skill validation directory: $validationDir")
}
if (-not (Test-Path $packetDir)) {
    $failures.Add("Missing skill packet directory: $packetDir")
}

Write-Output "`n=== GitVizz ==="
Write-Output "Frontend: $frontendUrl"
Write-Output "Backend:  $backendUrl"

if ($SkipGitvizz) {
    Write-Output "GitVizz checks skipped."
} else {
    if (-not (Test-TcpUrl -Url $frontendUrl)) {
        $failures.Add("GitVizz frontend is not reachable: $frontendUrl")
    }

    if (-not (Test-TcpUrl -Url $backendUrl)) {
        $failures.Add("GitVizz backend is not reachable: $backendUrl")
    }
}

if ($failures.Count -gt 0) {
    Write-Error ($failures -join "`n")
    exit 1
}

Write-Output "`nHealth check passed."
