param(
    [switch]$WithMedium,
    [switch]$WithLlm
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$serviceRoot = Join-Path $projectRoot 'audio-stt'
$modelsRoot = Join-Path $projectRoot 'models\faster-whisper'
$ollamaExe = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'

function Get-Python {
    $python311 = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'
    if (Test-Path $python311) { return $python311 }

    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) {
        & $launcher.Source -3.11 --version 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { return "$($launcher.Source) -3.11" }
    }

    Write-Host '[SETUP] Python 3.11 belum tersedia. Memasang versi yang kompatibel...' -ForegroundColor Yellow
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) { throw 'Python dan winget tidak tersedia. Instal Python 3.11 terlebih dahulu dari https://www.python.org/downloads/' }
    & $winget.Source install --id Python.Python.3.11 --exact --accept-package-agreements --accept-source-agreements
    if (-not (Test-Path $python311)) { throw 'Python 3.11 belum dapat ditemukan setelah instalasi.' }
    return $python311
}

function Ensure-Model([string]$Model) {
    $modelPath = Join-Path $modelsRoot "models--Systran--faster-whisper-$Model"
    if (Test-Path $modelPath) { Write-Host "[OK] Whisper $Model tersedia"; return }
    Write-Host "[SETUP] Mengunduh Whisper $Model..." -ForegroundColor Yellow
    $downloadCode = "from faster_whisper import WhisperModel; WhisperModel('$Model', device='cpu', compute_type='int8', download_root=r'$modelsRoot')"
    $job = Start-Job -ScriptBlock {
        param($pythonExe, $code)
        & $pythonExe -c $code
        exit $LASTEXITCODE
    } -ArgumentList $python, $downloadCode
    while ($job.State -eq 'Running') {
        $bytes = if (Test-Path $modelPath) { (Get-ChildItem $modelPath -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum } else { 0 }
        $megabytes = [math]::Round($bytes / 1MB, 1)
        Write-Host "`r[DOWNLOAD] Whisper ${Model}: $megabytes MB diterima..." -NoNewline
        Start-Sleep -Seconds 5
    }
    Write-Host ''
    Receive-Job $job | Write-Host
    $failed = $job.State -ne 'Completed' -or $job.ChildJobs[0].JobStateInfo.State -eq 'Failed'
    Remove-Job $job -Force
    if ($failed) { throw "Gagal mengunduh Whisper $Model. Periksa koneksi internet." }
    Write-Host "[OK] Whisper $Model siap"
}

Write-Host ''
Write-Host 'Menyiapkan STT Local' -ForegroundColor Cyan
$systemPython = Get-Python
$venvPython = Join-Path $serviceRoot '.venv\Scripts\python.exe'
Push-Location $serviceRoot
try {
    if (-not (Test-Path $venvPython)) {
        Write-Host '[SETUP] Membuat virtual environment...' -ForegroundColor Yellow
        if ($systemPython -like '* -3.11') {
            $parts = $systemPython -split ' ', 2
            & $parts[0] $parts[1] -m venv .venv
        } else {
            & $systemPython -m venv .venv
        }
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
    if ($WithMedium) { Ensure-Model 'medium' }
    if ($WithLlm) {
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
    } else {
        Write-Host '[INFO] LLM Editor tidak diaktifkan pada setup default.'
    }
} finally { Pop-Location }
