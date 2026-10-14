. (Join-Path $PSScriptRoot 'env.ps1')
if (-not $env:DATABASE_URL -or -not $env:DEMO_PASSWORD) {
    throw 'Copy .env.example to .env and fill DATABASE_URL and DEMO_PASSWORD. Start PostgreSQL first; see README.md.'
}
Push-Location $ClinicFlowRoot
try {
    if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Creating the Python environment failed.' }
    }
    $ClinicFlowPython = Join-Path $ClinicFlowRoot '.venv/Scripts/python.exe'
    & $ClinicFlowPython -m pip install -r backend/requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { throw 'Installing backend dependencies failed.' }
    Push-Location backend
    try {
        & $ClinicFlowPython -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }
        & $ClinicFlowPython -m app.seed
        if ($LASTEXITCODE -ne 0) { throw 'Demo seeding failed.' }
    } finally { Pop-Location }
    Push-Location frontend
    try {
        npm ci
        if ($LASTEXITCODE -ne 0) { throw 'Installing frontend dependencies failed.' }
    } finally { Pop-Location }
    Write-Host 'Setup complete. Run ./scripts/dev.ps1 to start the local app.'
} finally { Pop-Location }
