. (Join-Path $PSScriptRoot 'env.ps1')
if (-not $env:DATABASE_URL) { throw 'DATABASE_URL is empty. Follow README.md first.' }
$ClinicFlowPython = Join-Path $ClinicFlowRoot '.venv/Scripts/python.exe'
$ClinicFlowVite = Join-Path $ClinicFlowRoot 'frontend/node_modules/vite/bin/vite.js'
if (-not (Test-Path -LiteralPath $ClinicFlowPython) -or -not (Test-Path -LiteralPath $ClinicFlowVite)) {
    throw 'Dependencies are missing. Run ./scripts/setup.ps1 first.'
}
$ClinicFlowLogs = Join-Path $ClinicFlowRoot '.local'
New-Item -ItemType Directory -Path $ClinicFlowLogs -Force | Out-Null
$ClinicFlowState = Join-Path $ClinicFlowLogs 'dev-processes.json'
if (Test-Path -LiteralPath $ClinicFlowState) { throw 'Run ./scripts/stop-dev.ps1 before starting another local session.' }
foreach ($ClinicFlowPort in @(8000, 5173)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $ClinicFlowPort -ErrorAction SilentlyContinue) {
        throw "Port $ClinicFlowPort is busy. Stop its existing owner first."
    }
}
$ClinicFlowProcesses = @()
try {
    $ClinicFlowApi = Start-Process -FilePath $ClinicFlowPython -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000') -WorkingDirectory (Join-Path $ClinicFlowRoot 'backend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $ClinicFlowLogs 'api.log') -RedirectStandardError (Join-Path $ClinicFlowLogs 'api-error.log') -PassThru
    $ClinicFlowProcesses += @{ id = $ClinicFlowApi.Id; started_at = $ClinicFlowApi.StartTime.ToUniversalTime().ToString('o') }
    $ClinicFlowUi = Start-Process -FilePath (Get-Command node).Source -ArgumentList @(('"' + $ClinicFlowVite + '"'), '--host', '127.0.0.1', '--port', '5173', '--strictPort') -WorkingDirectory (Join-Path $ClinicFlowRoot 'frontend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $ClinicFlowLogs 'ui.log') -RedirectStandardError (Join-Path $ClinicFlowLogs 'ui-error.log') -PassThru
    $ClinicFlowProcesses += @{ id = $ClinicFlowUi.Id; started_at = $ClinicFlowUi.StartTime.ToUniversalTime().ToString('o') }
    ConvertTo-Json -InputObject $ClinicFlowProcesses | Set-Content -LiteralPath $ClinicFlowState
    Write-Host 'App: http://127.0.0.1:5173 | API: http://127.0.0.1:8000/api/health'
    Write-Host 'Logs: .local/api-error.log and .local/ui-error.log. Stop with ./scripts/stop-dev.ps1.'
} catch {
    foreach ($ClinicFlowStarted in $ClinicFlowProcesses) { Stop-Process -Id $ClinicFlowStarted.id -ErrorAction SilentlyContinue }
    throw
}

