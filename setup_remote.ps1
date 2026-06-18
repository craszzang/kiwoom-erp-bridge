# Remote client setup (64-bit Python, no Kiwoom)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $env:LOCALAPPDATA "kiwoom-trader\.venv-remote"
$ReqFile = Join-Path $Root "requirements-remote.txt"

function Test-RealPython([string]$Exe) {
    if (-not $Exe -or -not (Test-Path -LiteralPath $Exe)) { return $false }
    if ($Exe -match "WindowsApps") { return $false }
    try {
        $out = & $Exe -c "import sys; print(sys.executable)" 2>$null
        return [bool]$out
    } catch {
        return $false
    }
}

function Find-Python {
    $candidates = [System.Collections.Generic.List[string]]::new()
    foreach ($name in @("Python312", "Python311", "Python310")) {
        $candidates.Add((Join-Path $env:LocalAppData "Programs\Python\$name\python.exe"))
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($tag in @("-3.12", "-3.11", "-3.10")) {
            try {
                $resolved = & py $tag -c "import sys; print(sys.executable)" 2>$null
                if ($resolved) { $candidates.Add($resolved.Trim()) }
            } catch {}
        }
    }
    $fromPath = (Get-Command python -ErrorAction SilentlyContinue).Source
    if ($fromPath) { $candidates.Add($fromPath) }

    foreach ($c in $candidates) {
        if (Test-RealPython $c) { return $c }
    }
    return $null
}

function Ensure-Venv([string]$BasePython, [string]$TargetDir) {
    $venvPython = Join-Path $TargetDir "Scripts\python.exe"
    if (Test-RealPython $venvPython) { return $venvPython }

    if (Test-Path -LiteralPath $TargetDir) {
        Write-Host "Broken venv removed, recreating..." -ForegroundColor Yellow
        Remove-Item -LiteralPath $TargetDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $TargetDir) | Out-Null
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    & $BasePython -m venv $TargetDir
    if (-not (Test-RealPython $venvPython)) {
        throw "venv creation failed: $venvPython"
    }
    return $venvPython
}

Write-Host "=== ERP Remote UI Setup ===" -ForegroundColor Cyan
Write-Host "Folder: $Root"
Write-Host "Venv: $VenvDir"
Write-Host ""

$python = Find-Python
if (-not $python) {
    Write-Host "Installing Python 3.12 (winget)..." -ForegroundColor Yellow
    winget install --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    Start-Sleep -Seconds 3
    $python = Find-Python
}

if (-not $python) {
    Write-Host ""
    Write-Host "[ERROR] Real Python not found." -ForegroundColor Red
    Write-Host "Windows Store python stub cannot be used."
    Write-Host "Install from https://www.python.org/downloads/"
    Write-Host "Check 'Add python.exe to PATH', then rerun setup_remote.bat"
    exit 1
}

Write-Host "Python: $python" -ForegroundColor Green

try {
    $venvPython = Ensure-Venv -BasePython $python -TargetDir $VenvDir
} catch {
    Write-Host ""
    Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "Installing packages (PyQt5, requests...)..." -ForegroundColor Yellow
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r $ReqFile

Write-Host ""
Write-Host "Done!" -ForegroundColor Green
Write-Host "  Python: $venvPython"
Write-Host "  Next: run 재고실적_집계-원격.bat"
