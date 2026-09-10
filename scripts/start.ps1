$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$serviceRoot = Join-Path $projectRoot 'audio-stt'
$modelsRoot = Join-Path $projectRoot 'models\faster-whisper'
$ollamaExe = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'

function Ensure-WhisperModel([string]$Model) {
    $modelPath = Join-Path $modelsRoot "models--Systran--faster-whisper-$Model"
    if (Test-Path $modelPath) {
        Write-Host "[OK] Whisper $Model tersedia"
        return
    }
    Write-Host "[SETUP] Mengunduh Whisper $Model..." -ForegroundColor Yellow
    & $python -c "from faster_whisper import WhisperModel; WhisperModel('$Model', device='cpu', compute_type='int8', download_root=r'$modelsRoot'); print('Whisper $Model siap')"
}

Write-Host ''
Write-Host 'Memulai STT Local' -ForegroundColor Cyan

Push-Location $serviceRoot
try {
    $python = 'python'
    & $python --version | Out-Null

    try {
        & $python -c "import fastapi, sounddevice, webrtcvad, faster_whisper" | Out-Null
        Write-Host '[OK] Dependensi Python tersedia'
    } catch {
        Write-Host '[SETUP] Memasang dependensi Python...' -ForegroundColor Yellow
        & $python -m pip install -r requirements.txt
    }

    New-Item -ItemType Directory -Path $modelsRoot -Force | Out-Null
    Ensure-WhisperModel 'small'
    Ensure-WhisperModel 'medium'

    if (Test-Path $ollamaExe) {
        $ollamaModels = & $ollamaExe list 2>&1 | Out-String
        if ($ollamaModels -match 'qwen2\.5:3b') {
            Write-Host '[OK] Qwen 3B tersedia'
        } else {
            Write-Host '[SETUP] Mengunduh Qwen 3B untuk LLM Editor...' -ForegroundColor Yellow
            & $ollamaExe pull qwen2.5:3b
        }
    } else {
        Write-Host '[INFO] Ollama belum ada. STT tetap berjalan tanpa LLM Editor.' -ForegroundColor DarkYellow
        Write-Host '       Install Ollama dari https://ollama.com/download/windows, lalu jalankan script ini lagi.'
    }

    Write-Host ''
    Write-Host 'Aplikasi aktif di http://127.0.0.1:8000' -ForegroundColor Green
    & $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
} finally {
    Pop-Location
}
