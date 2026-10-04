param(
    [string]$Python = "$PSScriptRoot\..\.venv\Scripts\python.exe"
)
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path "$PSScriptRoot\..").Path
$Python = (Get-Command $Python -ErrorAction Stop).Source
$buildSavedPath = $env:PATH
Push-Location $repoRoot
try {
    & "$PSScriptRoot\fetch_ffmpeg.ps1" -Python $Python
    & "$PSScriptRoot\fetch_deno.ps1" -Python $Python
    & $Python "$PSScriptRoot\build_support.py"
    if ($LASTEXITCODE -ne 0) { throw 'Build preparation failed.' }
    # Keep unrelated developer DLLs (for example Poppler's ICU) out of analysis.
    # Python/package native dependencies are located from the selected interpreter.
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    & $Python -m PyInstaller --noconfirm --clean "$repoRoot\mediagrab.spec"
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
    $appDirectory = Join-Path $repoRoot 'dist\MediaGrab'
    foreach ($tool in @('ffmpeg', 'ffprobe')) {
        Copy-Item -LiteralPath "$repoRoot\vendor\packaging\ffmpeg\$tool.exe" -Destination $appDirectory
    }
    Copy-Item -LiteralPath "$repoRoot\vendor\packaging\deno\deno.exe" -Destination $appDirectory
    foreach ($notice in @('LICENSE', 'THIRD_PARTY_NOTICES.md', 'README.md')) {
        Copy-Item -LiteralPath (Join-Path $repoRoot $notice) -Destination $appDirectory
    }
    & "$PSScriptRoot\smoke_frozen.ps1" -AppDirectory $appDirectory
    $appVersion = (Get-Content -LiteralPath "$repoRoot\build\version.txt" -Raw).Trim()
    $zipPath = Join-Path $repoRoot "dist\MediaGrab-$appVersion-windows-x64.zip"
    # ZipFile avoids Compress-Archive's hidden-file omissions and 2 GiB member limit.
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath }
    [System.IO.Compression.ZipFile]::CreateFromDirectory($appDirectory, $zipPath)
    $digest = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
    "$digest  $([System.IO.Path]::GetFileName($zipPath))" | Set-Content -LiteralPath "$zipPath.sha256" -Encoding ascii
    Write-Host "Built $zipPath"
    Write-Host "SHA-256 $digest"
} finally {
    $env:PATH = $buildSavedPath
    Pop-Location
}
