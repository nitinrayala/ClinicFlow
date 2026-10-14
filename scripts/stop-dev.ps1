$ErrorActionPreference = 'Stop'
$ClinicFlowRoot = Split-Path -Parent $PSScriptRoot
$ClinicFlowState = Join-Path $ClinicFlowRoot '.local/dev-processes.json'
if (-not (Test-Path -LiteralPath $ClinicFlowState)) {
    Write-Host 'There is no tracked local session.'
    exit 0
}
foreach ($ClinicFlowSaved in Get-Content -Raw -LiteralPath $ClinicFlowState | ConvertFrom-Json) {
    $ClinicFlowProcess = Get-Process -Id $ClinicFlowSaved.id -ErrorAction SilentlyContinue
    if ($ClinicFlowProcess -and $ClinicFlowProcess.StartTime.ToUniversalTime().ToString('o') -eq $ClinicFlowSaved.started_at) {
        Stop-Process -Id $ClinicFlowProcess.Id
    }
}
Remove-Item -LiteralPath $ClinicFlowState
Write-Host 'Tracked local servers stopped. PostgreSQL remains running.'

