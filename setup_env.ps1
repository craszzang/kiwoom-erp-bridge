# -*- coding: utf-8 -*-
# Ű�� OpenAPI�� 32��Ʈ Python ����ȯ�� ��ġ
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $env:LOCALAPPDATA "kiwoom-trader\.venv32"

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

Write-Host "=== Ű�� �ڵ��Ÿ� ȯ�� ��ġ ===" -ForegroundColor Cyan
Write-Host "������Ʈ: $Root"
Write-Host "����ȯ��: $VenvDir"

if (-not (Test-Path "C:\OpenAPI\khopenapi.ocx")) {
    Write-Warning "C:\OpenAPI\khopenapi.ocx ���� - Ű�� OpenAPI+ ��ġ �ʿ�"
}

$python32 = Find-Python32
if (-not $python32) {
    Write-Host "32��Ʈ Python ��ġ �� (winget)..." -ForegroundColor Yellow
    winget install --id Python.Python.3.11 --architecture x86 --accept-package-agreements --accept-source-agreements
    $python32 = Find-Python32
}

if (-not $python32) {
    Write-Host "32��Ʈ Python ��ġ ����" -ForegroundColor Red
    Write-Host "https://www.python.org/downloads/windows/ ���� 32-bit ��ġ �� �����"
    exit 1
}

Write-Host "32��Ʈ Python: $python32" -ForegroundColor Green

if (-not (Test-Path $VenvDir)) {
    New-Item -ItemType Directory -Force -Path (Split-Path $VenvDir) | Out-Null
    & $python32 -m venv $VenvDir
}

$venvPython = Join-Path $VenvDir "Scripts\python.exe"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $Root "requirements.txt")

$cfg = Join-Path $Root "config.yaml"
$cfgExample = Join-Path $Root "config.yaml.example"
if (-not (Test-Path $cfg) -and (Test-Path $cfgExample)) {
    Copy-Item $cfgExample $cfg
}

Write-Host ""
Write-Host "��ġ �Ϸ�." -ForegroundColor Green
Write-Host "  Python: $venvPython"
Write-Host "  ����: �������_����.bat �Ǵ� run.bat excel"
