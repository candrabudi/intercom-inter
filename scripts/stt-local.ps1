param(
    [ValidateSet('check', 'setup', 'run')]
    [string]$Action = 'check',
    [switch]$WithMedium,
    [switch]$WithLlm
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$serviceRoot = Join-Path $projectRoot 'audio-stt'
$modelsRoot = Join-Path $projectRoot 'models\faster-whisper'
$ollamaExe = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'

function Write-Check([string]$Label, [bool]$Ok, [string]$Detail) {
    $mark = if ($Ok) { '[OK]' } else { '[--]' }
    Write-Host "$mark $Label : $Detail"
}

function Test-WhisperModel([string]$Model) {
    $modelPath = Join-Path $modelsRoot "models--Systran--faster-whisper-$Model"
    $exists = Test-Path $modelPath
    Write-Check "Whisper $Model" $exists $(if ($exists) { 'tersedia lokal' } else { 'belum diunduh' })
    return $exists
}

function Get-PythonCommand {
    $venvPython = Join-Path $serviceRoot '.venv\Scripts\python.exe'
    if (Test-Path $venvPython) { return $venvPython }
    return 'python'
}

Write-Host ''
Write-Host 'STT Local - Pemeriksaan dan Pengelola Runtime' -ForegroundColor Cyan
Write-Host "Project: $projectRoot"
Write-Host ''

$python = Get-PythonCommand
try {
    $pythonVersion = & $python --version 2>&1
    Write-Check 'Python' $true $pythonVersion
} catch {
    Write-Check 'Python' $false 'Python 3.11 tidak ditemukan.'
    exit 1
}

Push-Location $serviceRoot
try {
    try {
        & $python -c "import fastapi, sounddevice, webrtcvad, faster_whisper; print('ready')" | Out-Null
        Write-Check 'Dependensi STT' $true 'FastAPI, audio, VAD, dan faster-whisper siap'
    } catch {
        Write-Check 'Dependensi STT' $false 'Jalankan setup untuk memasang requirements.txt'
    }

    $smallReady = Test-WhisperModel 'small'
    $mediumReady = Test-WhisperModel 'medium'

    $ollamaExists = Test-Path $ollamaExe
    Write-Check 'Ollama' $ollamaExists $(if ($ollamaExists) { 'runtime ditemukan' } else { 'belum terpasang' })
    if ($ollamaExists) {
        try {
            $models = & $ollamaExe list 2>&1 | Out-String
            $qwenReady = $models -match 'qwen2\.5:3b'
            Write-Check 'Qwen 3B editor' $qwenReady $(if ($qwenReady) { 'tersedia lokal' } else { 'belum diunduh' })
        } catch {
            Write-Check 'Qwen 3B editor' $false 'Ollama tidak dapat merespons'
        }
    }

    if ($Action -eq 'setup') {
        Write-Host ''
        Write-Host 'Menyiapkan runtime yang dipilih...' -ForegroundColor Yellow
        & $python -m pip install -r requirements.txt
        if (-not $smallReady) {
            & $python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8', download_root=r'$modelsRoot'); print('Whisper small siap')"
        }
        if ($WithMedium -and -not $mediumReady) {
            & $python -c "from faster_whisper import WhisperModel; WhisperModel('medium', device='cpu', compute_type='int8', download_root=r'$modelsRoot'); print('Whisper medium siap')"
        }
        if ($WithLlm) {
            if (-not $ollamaExists) {
                throw 'Ollama belum terpasang. Instal dari https://ollama.com/download/windows, lalu jalankan script ini lagi.'
            }
            & $ollamaExe pull qwen2.5:3b
        }
    }

    if ($Action -eq 'run') {
        Write-Host ''
        Write-Host 'Menjalankan aplikasi di http://127.0.0.1:8000' -ForegroundColor Green
        & $python -m uvicorn stt_local.main:app --app-dir src --host 127.0.0.1 --port 8000
    }
} finally {
    Pop-Location
}
