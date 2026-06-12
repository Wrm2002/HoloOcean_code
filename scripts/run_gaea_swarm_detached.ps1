param(
    [Parameter(Mandatory = $true)]
    [string]$Terrain,

    [string]$OutputDir,

    [string]$GaeaSwarm = "C:\Program Files\QuadSpinner\Gaea 2\Gaea.Swarm.exe",
    [string]$Profile,
    [string]$Region,
    [int]$Seed,
    [string]$VarsFile,
    [string[]]$Var,
    [switch]$IgnoreCache,
    [switch]$SafeMode,
    [int]$TimeoutSeconds = 180,
    [int]$PollSeconds = 2
)

$ErrorActionPreference = "Stop"

$terrainPath = (Resolve-Path -LiteralPath $Terrain).Path
$swarmPath = (Resolve-Path -LiteralPath $GaeaSwarm).Path
$terrainText = Get-Content -LiteralPath $terrainPath -Raw -Encoding UTF8
$destinationMatch = [regex]::Match($terrainText, '"Destination"\s*:\s*"(?<value>[^"]+)"')
$projectOutputDir = $null
if ($destinationMatch.Success) {
    $projectOutputDir = $destinationMatch.Groups["value"].Value.Replace("\\", "\")
}
if (-not $OutputDir) {
    if (-not $projectOutputDir) {
        throw "OutputDir was not provided and no BuildDefinition.Destination was found in $terrainPath."
    }
    $OutputDir = $projectOutputDir
}
elseif ($projectOutputDir) {
    $providedOutput = [System.IO.Path]::GetFullPath($OutputDir).TrimEnd("\")
    $projectOutput = [System.IO.Path]::GetFullPath($projectOutputDir).TrimEnd("\")
    if ($providedOutput -ne $projectOutput) {
        $OutputDir = $projectOutputDir
    }
}
$outputPath = New-Item -ItemType Directory -Force -Path $OutputDir
$outputFullPath = $outputPath.FullName
$startedAt = Get-Date
$wrapperLog = Join-Path $outputFullPath "gaea_swarm_detached_wrapper.log"

"[$startedAt] Starting Gaea Swarm detached" | Set-Content -Path $wrapperLog -Encoding UTF8
"Swarm: $swarmPath" | Add-Content -Path $wrapperLog -Encoding UTF8
"Terrain: $terrainPath" | Add-Content -Path $wrapperLog -Encoding UTF8
"OutputDir: $outputFullPath" | Add-Content -Path $wrapperLog -Encoding UTF8
if ($projectOutputDir -and $PSBoundParameters.ContainsKey("OutputDir")) {
    "ProjectBuildDestination: $projectOutputDir" | Add-Content -Path $wrapperLog -Encoding UTF8
}

$arguments = New-Object System.Collections.Generic.List[string]
$arguments.Add("--filename")
$arguments.Add($terrainPath)
if ($Profile) {
    $arguments.Add("--profile")
    $arguments.Add($Profile)
}
if ($Region) {
    $arguments.Add("--region")
    $arguments.Add($Region)
}
if ($PSBoundParameters.ContainsKey("Seed")) {
    $arguments.Add("--seed")
    $arguments.Add([string]$Seed)
}
if ($IgnoreCache) {
    $arguments.Add("--ignorecache")
}
if ($SafeMode) {
    $arguments.Add("--safemode")
}
if ($VarsFile) {
    $varsFull = (Resolve-Path -LiteralPath $VarsFile).Path
    $arguments.Add("--vars")
    $arguments.Add($varsFull)
}
if ($Var) {
    foreach ($entry in $Var) {
        $arguments.Add("-v")
        $arguments.Add($entry)
    }
}

"Arguments: $($arguments -join ' ')" | Add-Content -Path $wrapperLog -Encoding UTF8

$process = Start-Process `
    -FilePath $swarmPath `
    -ArgumentList $arguments.ToArray() `
    -WorkingDirectory (Split-Path -Parent $swarmPath) `
    -WindowStyle Hidden `
    -PassThru

try {
    $deadline = $startedAt.AddSeconds($TimeoutSeconds)
    $reportJson = Join-Path $outputFullPath "report.json"
    $result = $null

    while ((Get-Date) -lt $deadline) {
        if (Test-Path -LiteralPath $reportJson) {
            $reportFile = Get-Item -LiteralPath $reportJson
            if ($reportFile.LastWriteTime -ge $startedAt) {
                $report = Get-Content -LiteralPath $reportJson -Raw -Encoding UTF8 | ConvertFrom-Json
                if ($report.Result) {
                    $result = [string]$report.Result
                    break
                }
            }
        }

        if ($process.HasExited) {
            break
        }

        Start-Sleep -Seconds $PollSeconds
    }

    $process.Refresh()
    $exportedFiles = Get-ChildItem -LiteralPath $outputFullPath -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -in ".exr", ".r16", ".png", ".tif", ".tiff", ".raw" }

    if ($result -eq "Success") {
        "[$(Get-Date)] Build report says Success." | Add-Content -Path $wrapperLog -Encoding UTF8
        if (-not $process.HasExited) {
            "[$(Get-Date)] Swarm did not exit after reporting success; stopping process $($process.Id)." |
                Add-Content -Path $wrapperLog -Encoding UTF8
            Stop-Process -Id $process.Id -Force
        }
        "Exported files: $($exportedFiles.Count)" | Add-Content -Path $wrapperLog -Encoding UTF8
        exit 0
    }

    if (-not $process.HasExited) {
        "[$(Get-Date)] Timeout waiting for report; stopping process $($process.Id)." |
            Add-Content -Path $wrapperLog -Encoding UTF8
        Stop-Process -Id $process.Id -Force
        exit 124
    }

    "[$(Get-Date)] Swarm exited with code $($process.ExitCode), result=$result, exported=$($exportedFiles.Count)." |
        Add-Content -Path $wrapperLog -Encoding UTF8
    exit $process.ExitCode
}
catch {
    "[$(Get-Date)] Wrapper failed: $($_.Exception.Message)" | Add-Content -Path $wrapperLog -Encoding UTF8
    if ($process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
    }
    throw
}
