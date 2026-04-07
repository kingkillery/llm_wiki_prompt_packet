param(
    [string]$ConfigPath = $(Join-Path (Split-Path -Parent $PSScriptRoot) ".llm-wiki\config.json")
)

$ErrorActionPreference = "Stop"

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

if (-not (Test-Path $ConfigPath)) {
    Write-Error "Stack config not found: $ConfigPath"
    exit 1
}

$config = Get-Content -Path $ConfigPath -Raw | ConvertFrom-Json
$brvCommand = $config.byterover.command
$workspaceRoot = Split-Path -Parent (Split-Path -Parent $ConfigPath)
$qmdCommandCandidates = @()
if ($config.pk_qmd.local_command_candidates) {
    foreach ($candidate in $config.pk_qmd.local_command_candidates) {
        $qmdCommandCandidates += (Join-Path $workspaceRoot $candidate)
    }
}
$qmdCommand = $config.pk_qmd.command
foreach ($candidate in $qmdCommandCandidates) {
    if (Test-Path $candidate) {
        $qmdCommand = $candidate
        break
    }
}
$collectionName = if ($config.pk_qmd.collection_name) { $config.pk_qmd.collection_name } else { [IO.Path]::GetFileName($workspaceRoot.TrimEnd('\', '/')).ToLowerInvariant().Replace(' ', '-') }
$frontendUrl = $config.gitvizz.frontend_url
$backendUrl = $config.gitvizz.backend_url
$failures = New-Object System.Collections.Generic.List[string]

Write-Output "=== llm-wiki-memory health check ==="
Write-Output "Config: $ConfigPath"

if (-not (Get-Command $qmdCommand -ErrorAction SilentlyContinue)) {
    $failures.Add("Missing pk-qmd command: $qmdCommand")
} else {
    Write-Output "`n=== pk-qmd ==="
    try {
        & $qmdCommand status
    } catch {
        Write-Warning "pk-qmd status failed: $($_.Exception.Message)"
    }

    try {
        $helpText = & $qmdCommand 2>&1 | Out-String
        if ($helpText -match "pk-qmd collection add") {
            $collections = & $qmdCommand collection list 2>&1 | Out-String
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

if (-not (Get-Command $brvCommand -ErrorAction SilentlyContinue)) {
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

Write-Output "`n=== GitVizz ==="
Write-Output "Frontend: $frontendUrl"
Write-Output "Backend:  $backendUrl"

if (-not (Test-TcpUrl -Url $frontendUrl)) {
    $failures.Add("GitVizz frontend is not reachable: $frontendUrl")
}

if (-not (Test-TcpUrl -Url $backendUrl)) {
    $failures.Add("GitVizz backend is not reachable: $backendUrl")
}

if ($failures.Count -gt 0) {
    Write-Error ($failures -join "`n")
    exit 1
}

Write-Output "`nHealth check passed."
