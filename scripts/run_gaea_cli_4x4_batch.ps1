param(
    [string]$SourceTileDir,
    [string]$TemplateTerrain = "D:\WRM_Gaea_Windows_Handoff_20260603\05_return_to_linux\x0_y0_gui_build.terrain",
    [string]$Workspace = "C:\WRM_Gaea_CLI_Batch_4x4_20260609",
    [string]$OutputRoot,
    [string]$Profile,
    [string]$Region,
    [int]$Seed,
    [string]$VarsFile,
    [string[]]$Var,
    [switch]$IgnoreCache,
    [switch]$SafeMode,
    [int]$TimeoutSecondsPerTile = 180,
    [switch]$StopOnFailure
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $SourceTileDir) {
    $SourceTileDir = Join-Path $repoRoot "wrm_projects\02_bigworld_terrain_generation\outputs\generated_terrain_4k_windows_20260609\r16"
}
if (-not $OutputRoot) {
    $OutputRoot = Join-Path $repoRoot "wrm_projects\03_gaea_heightfield_workflow\02_gaea_export_dropbox\gaea_4k_cli_batch_20260609"
}

$sourceFull = (Resolve-Path -LiteralPath $SourceTileDir).Path
$templateFull = (Resolve-Path -LiteralPath $TemplateTerrain).Path
$workspaceFull = (New-Item -ItemType Directory -Force -Path $Workspace).FullName
$inputDir = (New-Item -ItemType Directory -Force -Path (Join-Path $workspaceFull "inputs")).FullName
$projectDir = (New-Item -ItemType Directory -Force -Path (Join-Path $workspaceFull "projects")).FullName
$outputRootFull = (New-Item -ItemType Directory -Force -Path $OutputRoot).FullName
$summaryCsv = Join-Path $outputRootFull "gaea_cli_4x4_batch_summary.csv"
$summaryJson = Join-Path $outputRootFull "gaea_cli_4x4_batch_summary.json"

$tiles = Get-ChildItem -LiteralPath $sourceFull -Filter "terrain_x*_y*.r16" |
    Sort-Object Name

if ($tiles.Count -ne 16) {
    throw "Expected 16 terrain_x*_y*.r16 files in $sourceFull, found $($tiles.Count)."
}

$templateText = Get-Content -LiteralPath $templateFull -Raw -Encoding UTF8
$results = New-Object System.Collections.Generic.List[object]
$wrapper = Join-Path $PSScriptRoot "run_gaea_swarm_detached.ps1"

foreach ($tile in $tiles) {
    if ($tile.BaseName -notmatch "terrain_x(?<x>\d+)_y(?<y>\d+)") {
        throw "Unexpected tile name: $($tile.Name)"
    }

    $x = [int]$Matches.x
    $y = [int]$Matches.y
    $tileId = "x${x}_y${y}"
    $rawPath = Join-Path $inputDir "$tileId.raw"
    $terrainPath = Join-Path $projectDir "$tileId.terrain"
    $tileOut = Join-Path $outputRootFull $tileId

    New-Item -ItemType Directory -Force -Path $tileOut | Out-Null
    Get-ChildItem -LiteralPath $tileOut -File -ErrorAction SilentlyContinue | Remove-Item -Force
    Copy-Item -LiteralPath $tile.FullName -Destination $rawPath -Force

    $rawJsonPath = $rawPath.Replace("\", "\\")
    $outJsonPath = $tileOut.Replace("\", "\\")
    $projectText = $templateText
    $projectText = [regex]::Replace($projectText, '"FileName"\s*:\s*"[^"]+"', '"FileName": "' + $rawJsonPath + '"')
    $projectText = [regex]::Replace($projectText, '"Destination"\s*:\s*"[^"]+"', '"Destination": "' + $outJsonPath + '"')
    Set-Content -LiteralPath $terrainPath -Value $projectText -Encoding UTF8

    $startedAt = Get-Date
    $wrapperArgs = @(
        "-ExecutionPolicy", "Bypass",
        "-File", $wrapper,
        "-Terrain", $terrainPath,
        "-OutputDir", $tileOut,
        "-TimeoutSeconds", [string]$TimeoutSecondsPerTile
    )
    if ($Profile) {
        $wrapperArgs += @("-Profile", $Profile)
    }
    if ($Region) {
        $wrapperArgs += @("-Region", $Region)
    }
    if ($PSBoundParameters.ContainsKey("Seed")) {
        $wrapperArgs += @("-Seed", [string]$Seed)
    }
    if ($VarsFile) {
        $wrapperArgs += @("-VarsFile", $VarsFile)
    }
    if ($Var) {
        foreach ($entry in $Var) {
            $wrapperArgs += @("-Var", $entry)
        }
    }
    if ($IgnoreCache) {
        $wrapperArgs += "-IgnoreCache"
    }
    if ($SafeMode) {
        $wrapperArgs += "-SafeMode"
    }

    & powershell @wrapperArgs
    $exitCode = $LASTEXITCODE

    $reportPath = Join-Path $tileOut "report.json"
    $reportResult = $null
    $nodeCount = $null
    $duration = $null
    if (Test-Path -LiteralPath $reportPath) {
        $report = Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $reportResult = [string]$report.Result
        $nodeCount = $report.NodeCount
        $duration = [string]$report.Duration
    }

    $exportCount = @(Get-ChildItem -LiteralPath $tileOut -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -in ".exr", ".r16", ".png", ".tif", ".tiff", ".raw" }).Count

    $row = [pscustomobject]@{
        tile = $tileId
        source = $tile.FullName
        terrain = $terrainPath
        output_dir = $tileOut
        wrapper_exit = $exitCode
        report_result = $reportResult
        node_count = $nodeCount
        duration = $duration
        export_count = $exportCount
        profile = $Profile
        region = $Region
        seed = if ($PSBoundParameters.ContainsKey("Seed")) { $Seed } else { $null }
        vars_file = $VarsFile
        vars = if ($Var) { $Var -join ";" } else { $null }
        started_at = $startedAt.ToString("s")
        ended_at = (Get-Date).ToString("s")
    }
    $results.Add($row)
    $results | Export-Csv -LiteralPath $summaryCsv -NoTypeInformation -Encoding UTF8
    $results | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $summaryJson -Encoding UTF8

    if (($exitCode -ne 0 -or $reportResult -ne "Success") -and $StopOnFailure) {
        throw "Gaea tile $tileId failed: exit=$exitCode result=$reportResult"
    }
}

$failed = @($results | Where-Object { $_.wrapper_exit -ne 0 -or $_.report_result -ne "Success" })
if ($failed.Count -gt 0) {
    Write-Host "Gaea CLI batch finished with failures: $($failed.Count)/$($results.Count)"
    exit 1
}

Write-Host "Gaea CLI batch succeeded: $($results.Count)/$($results.Count)"
Write-Host "OutputRoot: $outputRootFull"
Write-Host "Summary: $summaryCsv"
exit 0
