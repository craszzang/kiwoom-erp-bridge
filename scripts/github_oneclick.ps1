# Create GitHub repo "kiwoom-erp-bridge" and push (one browser login)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$RepoName = "kiwoom-erp-bridge"
Set-Location $Root

function Find-Gh {
    $candidates = @(
        (Get-Command gh -ErrorAction SilentlyContinue).Source,
        "$env:ProgramFiles\GitHub CLI\gh.exe",
        "${env:ProgramFiles(x86)}\GitHub CLI\gh.exe"
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path -LiteralPath $c)) { return $c }
    }
    throw "gh not found. Run: winget install GitHub.cli"
}

$gh = Find-Gh
Write-Host "=== GitHub one-click setup ===" -ForegroundColor Cyan
Write-Host "Repository name: $RepoName"
Write-Host ""

& $gh auth status 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "GitHub login (browser opens once)..." -ForegroundColor Yellow
    & $gh auth login -w -p https -h github.com
}

$user = (& $gh api user -q .login).Trim()
$full = "$user/$RepoName"
Write-Host "Account: $user" -ForegroundColor Green
Write-Host "Full repo: $full"

python scripts/build_sync_manifest.py
python scripts/make_client_zip.py

if (-not (Test-Path ".git")) {
    git init
    git branch -M main
}

git add -A
git diff --staged --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -m "setup: kiwoom ERP bridge + GitHub auto-release"
}

$repoExists = $false
try {
    & $gh repo view $full *> $null
    if ($LASTEXITCODE -eq 0) { $repoExists = $true }
} catch {
    $repoExists = $false
}

if (-not $repoExists) {
    Write-Host "Creating public repo $RepoName ..." -ForegroundColor Yellow
    & $gh repo create $RepoName --public --description "Kiwoom ERP remote UI + bridge" --source=. --remote=origin --push
} else {
    Write-Host "Repo exists, pushing..." -ForegroundColor Yellow
    git remote remove origin 2>$null
    git remote add origin "https://github.com/$full.git"
    git push -u origin main
}

"$full" | Out-File -FilePath (Join-Path $Root "github_repo.txt") -Encoding utf8NoBOM
python scripts/make_client_zip.py

Write-Host ""
Write-Host "Done!" -ForegroundColor Green
Write-Host "  https://github.com/$full"
Write-Host "  Actions tab -> client release workflow"
Write-Host "  Customer update.github_repo = $full"
