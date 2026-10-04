# Fetch the official Deno x64 release and verify its published SHA-256.
param([string]$Python = "$PSScriptRoot\..\.venv\Scripts\python.exe")
$ErrorActionPreference = 'Stop'
& $Python "$PSScriptRoot\fetch_tools.py" deno
if ($LASTEXITCODE -ne 0) { throw 'Deno download/verification failed.' }
