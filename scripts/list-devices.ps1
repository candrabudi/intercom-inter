$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$serviceRoot = Join-Path $projectRoot 'audio-stt'
Set-Location $serviceRoot

if (Test-Path '.venv\Scripts\python.exe') {
    & '.venv\Scripts\python.exe' -c "from app.devices import list_devices; from pprint import pprint; pprint(list_devices())"
} else {
    python -c "from app.devices import list_devices; from pprint import pprint; pprint(list_devices())"
}
