param(
    [string]$RepoPath = (Resolve-Path ".").Path,
    [string]$Endpoint = "http://localhost:8003/api/local/index-repo",
    [string]$RepoName = "",
    [string]$Branch = "",
    [string]$OutDir = "",
    [string]$Token = ""
)

$ErrorActionPreference = "Stop"

function Get-RelativePath {
    param(
        [string]$BasePath,
        [string]$FullPath
    )

    $base = (Resolve-Path $BasePath).ProviderPath.TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    $full = (Resolve-Path $FullPath).ProviderPath
    $prefix = $base + [IO.Path]::DirectorySeparatorChar
    if ($full.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $full.Substring($prefix.Length)
    }
    return Split-Path -Leaf $full
}

function Test-IngestExcluded {
    param([string]$RelativePath)

    $normalized = $RelativePath.Replace("\", "/")
    $segments = $normalized.Split("/", [System.StringSplitOptions]::RemoveEmptyEntries)
    $excludedSegments = @(".git", ".chainlit", ".tmp", "deps", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache")

    foreach ($segment in $segments) {
        if ($excludedSegments -contains $segment) {
            return $true
        }
    }

    if ($normalized -like ".llm-wiki/node_modules/*" -or $normalized -like ".llm-wiki/tools/*") {
        return $true
    }
    if ($normalized -like ".brv/context-tree/*") {
        return $true
    }

    return $false
}

function Get-IngestFiles {
    param([string]$RootPath)

    $stack = New-Object System.Collections.Generic.Stack[string]
    $stack.Push((Resolve-Path $RootPath).ProviderPath)
    while ($stack.Count -gt 0) {
        $current = $stack.Pop()
        Get-ChildItem -LiteralPath $current -Force -ErrorAction SilentlyContinue | ForEach-Object {
            $relative = Get-RelativePath -BasePath $RootPath -FullPath $_.FullName
            if (Test-IngestExcluded -RelativePath $relative) {
                return
            }
            if ($_.PSIsContainer) {
                $stack.Push($_.FullName)
            } else {
                $_
            }
        }
    }
}

$RepoPath = (Resolve-Path $RepoPath).ProviderPath
if (-not $RepoName) {
    $RepoName = Split-Path -Leaf $RepoPath
}
if (-not $Branch) {
    $gitBranch = ""
    try {
        $gitBranch = (& git -C $RepoPath branch --show-current 2>$null).Trim()
    } catch {
        $gitBranch = ""
    }
    $Branch = if ($gitBranch) { $gitBranch } else { "working-tree" }
}
if (-not $OutDir) {
    $OutDir = Join-Path $RepoPath ".tmp\gitvizz-ingest"
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$safeBranch = ($Branch -replace '[^A-Za-z0-9._-]', '-')
$zipPath = Join-Path $OutDir "$RepoName-$safeBranch.zip"
$responsePath = Join-Path $OutDir "local-index-response.json"
Remove-Item -LiteralPath $zipPath -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $responsePath -Force -ErrorAction SilentlyContinue

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$zip = [System.IO.Compression.ZipFile]::Open($zipPath, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    Get-IngestFiles -RootPath $RepoPath | ForEach-Object {
        $relative = Get-RelativePath -BasePath $RepoPath -FullPath $_.FullName
        if (-not (Test-IngestExcluded -RelativePath $relative)) {
            $entryName = $relative.Replace("\", "/")
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $_.FullName, $entryName) | Out-Null
        }
    }
} finally {
    $zip.Dispose()
}

$curlArgs = @(
    "-sS",
    "-w", "%{http_code}",
    "-o", $responsePath
)
if ($Token) {
    $curlArgs += @("-H", "X-Local-Ingest-Token: $Token")
}
$curlArgs += @(
    "-F", "zip_file=@$zipPath;type=application/zip",
    "-F", "repo_name=$RepoName",
    "-F", "branch=$Branch",
    $Endpoint
)

$status = & curl.exe @curlArgs
if ($LASTEXITCODE -ne 0) {
    throw "curl.exe failed with exit code $LASTEXITCODE"
}
if ($status -lt 200 -or $status -ge 300) {
    $body = if (Test-Path -LiteralPath $responsePath) { Get-Content -LiteralPath $responsePath -Raw } else { "" }
    throw "GitVizz local ingest failed with HTTP $status. $body"
}

$response = Get-Content -LiteralPath $responsePath -Raw | ConvertFrom-Json
[pscustomobject]@{
    repo_id = $response.repo_id
    repo_name = $response.repo_name
    branch = $response.branch
    text_chars = $response.text_chars
    structure_files = $response.structure_files
    graph_nodes = $response.graph_nodes
    graph_edges = $response.graph_edges
    zip_path = $zipPath
    response_path = $responsePath
}
