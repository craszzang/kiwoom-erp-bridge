# Kiwoom OpenAPI: install 32-bit Python + project venv
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $Root ".venv32"

function Find-Python32 {
    $candidates = @(
        (Join-Path $env:LocalAppData "Programs\Python\Python311-32\python.exe"),
        (Join-Path $env:LocalAppData "Programs\Python\Python310-32\python.exe"),
        "C:\Python311-32\python.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) {
            $arch = & $c -c "import struct; print(struct.calcsize('P') * 8)"
            if ($arch -eq "32") { return $c }
        }
    }
    return $null
}

Write-Host "=== Kiwoom env setup ===" -ForegroundColor Cyan
Write-Host "Project: $Root"
Write-Host "Venv: $VenvDir"

if (-not (Test-Path "C:\OpenAPI\khopenapi.ocx")) {
    Write-Warning "C:\OpenAPI\khopenapi.ocx missing - install Kiwoom OpenAPI+"
}

$python32 = Find-Python32
if (-not $python32) {
    Write-Host "Installing 32-bit Python via winget..." -ForegroundColor Yellow
    winget install --id Python.Python.3.11 --architecture x86 --accept-package-agreements --accept-source-agreements
    $python32 = Find-Python32
}

if (-not $python32) {
    Write-Host "32-bit Python not found. Install from python.org (Windows x86)" -ForegroundColor Red
    exit 1
}

Write-Host "32-bit Python: $python32" -ForegroundColor Green

if (Test-Path $VenvDir) {
    $cfg = Join-Path $VenvDir "pyvenv.cfg"
    if (Test-Path $cfg) {
        $broken = $false
        try {
            & (Join-Path $VenvDir "Scripts\python.exe") -c "import sys; print(sys.version)" | Out-Null
        } catch {
            $broken = $true
        }
        if ($broken) {
            Remove-Item -Recurse -Force $VenvDir
        }
    }
}

if (-not (Test-Path $VenvDir)) {
    & $python32 -m venv $VenvDir
}

$venvPython = Join-Path $VenvDir "Scripts\python.exe"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $Root "requirements.txt")

$cfgYaml = Join-Path $Root "config.yaml"
$cfgExample = Join-Path $Root "config.automation.yaml"
if (-not (Test-Path $cfgYaml) -and (Test-Path $cfgExample)) {
    Copy-Item $cfgExample $cfgYaml
}

Write-Host ""
Write-Host "Done. Python: $venvPython" -ForegroundColor Green
