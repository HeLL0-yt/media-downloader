param([string]$AppDirectory = "$PSScriptRoot\..\dist\MediaGrab")
$ErrorActionPreference = 'Stop'
$sourceDirectory = (Resolve-Path -LiteralPath $AppDirectory).Path
$smokeDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ("MediaGrab-smoke-" + [guid]::NewGuid())
$savedPath = $env:PATH
$savedPlatform = $env:QT_QPA_PLATFORM
try {
    New-Item -ItemType Directory -Path $smokeDirectory | Out-Null
    Copy-Item -LiteralPath $sourceDirectory -Destination (Join-Path $smokeDirectory 'app') -Recurse
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
    $exePath = Join-Path $smokeDirectory 'app\MediaGrab.exe'
    foreach ($mode in @('self-check', 'smoke-test')) {
        $report = Join-Path $smokeDirectory "$mode.json"
        $outPath = Join-Path $smokeDirectory "$mode.stdout.txt"
        $errPath = Join-Path $smokeDirectory "$mode.stderr.txt"
        $child = Start-Process -FilePath $exePath -ArgumentList @("--$mode", '--report', "`"$report`"") `
            -WorkingDirectory $smokeDirectory -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput $outPath -RedirectStandardError $errPath
        if (-not $child.WaitForExit(60000)) {
            $child.Kill()
            $child.WaitForExit()
            throw "$mode timed out; deployment check failed."
        }
        $child.Refresh()
        if ($child.ExitCode -ne 0) {
            if (Test-Path -LiteralPath $report) { Get-Content -LiteralPath $report }
            Get-Content -LiteralPath $errPath
            throw "$mode failed with exit code $($child.ExitCode)."
        }
        $result = Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
        if (-not $result.ok -or -not $result.frozen) { throw 'Expected a successful frozen check.' }
        $consoleReport = Get-Content -LiteralPath $outPath -Raw | ConvertFrom-Json
        if (-not $consoleReport.ok) { throw 'Redirected windowed stdout did not report success.' }
        foreach ($tool in @('ffmpeg', 'ffprobe', 'deno')) {
            $entry = $result.environment | Where-Object name -EQ $tool
            if ($entry.severity -ne 'ok' -or (Split-Path $entry.path) -ne (Split-Path $exePath)) {
                throw "$tool did not use the executable beside MediaGrab.exe."
            }
        }
        Write-Host "$mode passed: MediaGrab $($result.version), $($result.extractors) extractors"
        $result.environment | Where-Object name -In @('ffmpeg', 'ffprobe', 'deno') | Format-Table name,version,path
    }
} finally {
    $env:PATH = $savedPath
    if ($null -eq $savedPlatform) { Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue }
    else { $env:QT_QPA_PLATFORM = $savedPlatform }
    # Resolve and bound the target before removing this script's unique temporary copy.
    if (Test-Path -LiteralPath $smokeDirectory) {
        $resolvedSmoke = (Resolve-Path -LiteralPath $smokeDirectory).Path
        $tempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd('\') + '\'
        if (-not $resolvedSmoke.StartsWith($tempRoot, [System.StringComparison]::OrdinalIgnoreCase) `
            -or (Split-Path $resolvedSmoke -Leaf) -notlike 'MediaGrab-smoke-*') {
            throw 'Refusing to remove a path outside the designated temporary smoke directory.'
        }
        Remove-Item -LiteralPath $resolvedSmoke -Recurse -Force
    }
}
