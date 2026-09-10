$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$serviceRoot = Join-Path $projectRoot 'audio-stt'
$modelsRoot = Join-Path $projectRoot 'models\faster-whisper'
$ollamaExe = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'

function Get-Python {
    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }

    Write-Host '[SETUP] Python 3.11 belum ada. Memasang melalui winget...' -ForegroundColor Yellow
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw 'Python 3.11 belum tersedia dan winget tidak ditemukan. Instal Python 3.11 dari https://www.python.org/downloads/ lalu jalankan script ini lagi.'
    }
    & $winget.Source install --id Python.Python.3.11 --exact --accept-package-agreements --accept-source-agreements
    $knownPython = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'
    if (-not (Test-Path $knownPython)) {
        throw 'Instalasi Python selesai, tetapi terminal belum menemukan Python. Tutup PowerShell, buka kembali, lalu jalankan script ini lagi.'
    }
    return $knownPython
}

function Ensure-Ollama {
    if (Test-Path $ollamaExe) { return }
    Write-Host '[SETUP] Ollama belum ada. Mengunduh dan memasang runtime lokal...' -ForegroundColor Yellow
    irm https://ollama.com/install.ps1 | iex
    if (-not (Test-Path $ollamaExe)) {
        throw 'Ollama belum dapat ditemukan setelah instalasi. Tutup PowerShell, buka kembali, lalu jalankan script ini lagi.'
    }
}

function Ensure-WhisperModel([string]$Model) {
    $modelPath = Join-Path $modelsRoot "models--Systran--faster-whisper-$Model"
    if (Test-Path $modelPath) {
        Write-Host "[OK] Whisper $Model tersedia"
        return
    }
    Write-Host "[SETUP] Mengunduh Whisper $Model..." -ForegroundColor Yellow
    & $python -c "from faster_whisper import WhisperModel; WhisperModel('$Model', device='cpu', compute_type='int8', download_root=r'$modelsRoot'); print('Whisper $Model siap')"
    if ($LASTEXITCODE -ne 0) {
        throw "Gagal mengunduh Whisper $Model. Pastikan dependency Python dan koneksi internet tersedia."
    }
}

Write-Host ''
Write-Host 'Memulai STT Local' -ForegroundColor Cyan

Push-Location $serviceRoot
try {
    $systemPython = Get-Python
    $venvPython = Join-Path $serviceRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path $venvPython)) {
        Write-Host '[SETUP] Membuat virtual environment Python...' -ForegroundColor Yellow
        & $systemPython -m venv .venv
    }
    $python = $venvPython
    Write-Host "[OK] Python: $(& $python --version)"

    try {
        & $python -c "import fastapi, sounddevice, webrtcvad, faster_whisper" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Dependency belum terpasang.' }
        Write-Host '[OK] Dependensi Python tersedia'
    } catch {
        Write-Host '[SETUP] Memasang dependency requirements.txt...' -ForegroundColor Yellow
        & $python -m pip install --upgrade pip
        if ($LASTEXITCODE -ne 0) { throw 'Gagal memperbarui pip.' }
        & $python -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) { throw 'Gagal memasang requirements.txt. Periksa koneksi internet dan pesan pip di atas.' }
        & $python -c "import fastapi, sounddevice, webrtcvad, faster_whisper" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Dependency Python masih tidak dapat diimpor setelah instalasi.' }
        Write-Host '[OK] Dependensi Python berhasil dipasang'
    }

    New-Item -ItemType Directory -Path $modelsRoot -Force | Out-Null
    Ensure-WhisperModel 'small'
    Ensure-WhisperModel 'medium'

    Ensure-Ollama
    $ollamaModels = & $ollamaExe list 2>&1 | Out-String
    if ($ollamaModels -match 'qwen2\.5:3b') {
        Write-Host '[OK] Qwen 3B tersedia'
    } else {
        Write-Host '[SETUP] Mengunduh Qwen 3B untuk LLM Editor...' -ForegroundColor Yellow
        & $ollamaExe pull qwen2.5:3b
    }

    Write-Host ''
    Write-Host 'Aplikasi aktif di http://127.0.0.1:8000' -ForegroundColor Green
    & $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
} finally {
    Pop-Location
}
