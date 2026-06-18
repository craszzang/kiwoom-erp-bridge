# One-time GitHub push + enable auto-release
param(
    [Parameter(Mandatory = $true)]
    [string]$Repo
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] git not installed. Install Git for Windows first." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".git")) {
    git init
    git branch -M main
}

python scripts/build_sync_manifest.py
python scripts/make_client_zip.py

git add .
git status
Write-Host ""
Write-Host "Committing..." -ForegroundColor Yellow
git commit -m "Initial commit: Kiwoom bridge + remote UI" 2>$null
if ($LASTEXITCODE -ne 0) {
    git commit -m "Update: Kiwoom bridge + remote UI"
}

$remote = git remote get-url origin 2>$null
if (-not $remote) {
    git remote add origin "https://github.com/$Repo.git"
}

Write-Host ""
Write-Host "Pushing to https://github.com/$Repo ..." -ForegroundColor Cyan
Write-Host "GitHub login window may appear (browser or token)." -ForegroundColor Yellow
git push -u origin main

Write-Host ""
Write-Host "Done!" -ForegroundColor Green
Write-Host "  1) GitHub repo Settings - Actions - General: Allow all actions"
Write-Host "  2) After push, Actions tab builds client.zip release automatically"
Write-Host "  3) Edit scripts/make_client_zip.py CLIENT_CONFIG github_repo -> $Repo"
Write-Host "  4) Customer config.yaml update.github_repo -> $Repo"
