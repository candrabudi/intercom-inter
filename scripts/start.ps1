$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot

# Satu perintah untuk device baru maupun device yang sudah siap. Default memakai Whisper small.
& (Join-Path $PSScriptRoot 'setup.ps1')

$serviceRoot = Join-Path $projectRoot 'audio-stt'
$python = Join-Path $serviceRoot '.venv\Scripts\python.exe'
Set-Location $serviceRoot
Write-Host ''
Write-Host 'Aplikasi aktif di http://127.0.0.1:8000' -ForegroundColor Green
& $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
