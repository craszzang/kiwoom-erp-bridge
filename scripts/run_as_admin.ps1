# UAC elevation helper — paths with & in username safe
param(
    [Parameter(Mandatory = $true)]
    [string]$BatPath,
    [string[]]$Args = @("/elevated")
)

if (-not (Test-Path -LiteralPath $BatPath)) {
    Write-Error "Bat not found: $BatPath"
    exit 1
}

$argLine = ($Args | ForEach-Object { '"' + ($_ -replace '"', '""') + '"' }) -join ' '
$inner = "cd /d `"$([IO.Path]::GetDirectoryName($BatPath))`" & `"$BatPath`" $argLine"

Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.MessageBox]::Show(
    "키움 자율봇 로그인 자동시작 등록에 관리자 권한이 필요합니다.`n`n다음 UAC 창에서 [예]를 눌러주세요.",
  "Kiwoom 자동시작 등록",
  [System.Windows.Forms.MessageBoxButtons]::OK,
  [System.Windows.Forms.MessageBoxIcon]::Information
) | Out-Null

Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $inner -Verb RunAs -Wait
exit $LASTEXITCODE
