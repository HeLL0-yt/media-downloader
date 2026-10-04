# Fetch a Windows build linked by ffmpeg.org; FFmpeg itself publishes source only.
param([string]$Python = "$PSScriptRoot\..\.venv\Scripts\python.exe")
$ErrorActionPreference = 'Stop'
& $Python "$PSScriptRoot\fetch_tools.py" ffmpeg
if ($LASTEXITCODE -ne 0) { throw 'FFmpeg download/verification failed.' }
