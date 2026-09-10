$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$serviceRoot = Join-Path $projectRoot 'audio-stt'
$modelsRoot = Join-Path $projectRoot 'models\faster-whisper'
$ollamaExe = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'

function Get-Python {
    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    Write-Host '[SETUP] Memasang Python 3.11...' -ForegroundColor Yellow
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) { throw 'Python dan winget tidak tersedia. Instal Python 3.11 terlebih dahulu dari https://www.python.org/downloads/' }
    & $winget.Source install --id Python.Python.3.11 --exact --accept-package-agreements --accept-source-agreements
    $pythonPath = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'
    if (-not (Test-Path $pythonPath)) { throw 'Python belum dapat ditemukan setelah instalasi.' }
    return $pythonPath
}

function Ensure-Model([string]$Model) {
    $modelPath = Join-Path $modelsRoot "models--Systran--faster-whisper-$Model"
    if (Test-Path $modelPath) { Write-Host "[OK] Whisper $Model tersedia"; return }
    Write-Host "[SETUP] Mengunduh Whisper $Model..." -ForegroundColor Yellow
    & $python -c "from faster_whisper import WhisperModel; WhisperModel('$Model', device='cpu', compute_type='int8', download_root=r'$modelsRoot')"
    if ($LASTEXITCODE -ne 0) { throw "Gagal mengunduh Whisper $Model. Periksa koneksi internet." }
}

Write-Host ''
Write-Host 'Menyiapkan STT Local' -ForegroundColor Cyan
$systemPython = Get-Python
$venvPython = Join-Path $serviceRoot '.venv\Scripts\python.exe'
Push-Location $serviceRoot
try {
    if (-not (Test-Path $venvPython)) {
        Write-Host '[SETUP] Membuat virtual environment...' -ForegroundColor Yellow
        & $systemPython -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Gagal membuat virtual environment Python.' }
    }
    $python = $venvPython
    $dependenciesReady = $false
    try {
        & $python -c "import fastapi, sounddevice, webrtcvad, faster_whisper" 2>$null | Out-Null
        $dependenciesReady = $LASTEXITCODE -eq 0
    } catch {
        # A new virtual environment has no packages yet. This is an expected setup state.
        $dependenciesReady = $false
    }
    if (-not $dependenciesReady) {
        Write-Host '[SETUP] Memasang seluruh Python requirements...' -ForegroundColor Yellow
        & $python -m pip install --upgrade pip
        & $python -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) { throw 'Gagal memasang Python requirements. Periksa koneksi internet.' }
    }
    try {
        & $python -c "import fastapi, sounddevice, webrtcvad, faster_whisper" 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Dependency Python belum siap setelah instalasi.' }
    } catch {
        throw 'Dependency Python belum siap setelah instalasi.'
    }
    Write-Host '[OK] Python dan seluruh requirements siap'
    New-Item -ItemType Directory -Path $modelsRoot -Force | Out-Null
    Ensure-Model 'small'
    Ensure-Model 'medium'
    if (-not (Test-Path $ollamaExe)) {
        Write-Host '[SETUP] Memasang Ollama...' -ForegroundColor Yellow
        irm https://ollama.com/install.ps1 | iex
    }
    if (-not (Test-Path $ollamaExe)) { throw 'Ollama belum dapat ditemukan setelah instalasi.' }
    $ollamaModels = & $ollamaExe list 2>&1 | Out-String
    if ($ollamaModels -notmatch 'qwen2\.5:3b') {
        Write-Host '[SETUP] Mengunduh Qwen 3B...' -ForegroundColor Yellow
        & $ollamaExe pull qwen2.5:3b
        if ($LASTEXITCODE -ne 0) { throw 'Gagal mengunduh Qwen 3B. Periksa koneksi internet.' }
    }
    Write-Host '[OK] Qwen 3B tersedia'
} finally { Pop-Location }
