# One-shot local setup for Windows PowerShell: scripts\bootstrap.ps1
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    $secret = python -c "import secrets; print(secrets.token_urlsafe(48))"
    (Get-Content ".env") -replace "SECRET_KEY=generate-a-random-value-before-running", "SECRET_KEY=$secret" |
        Set-Content ".env"
    Write-Host "[bootstrap] wrote .env with a generated SECRET_KEY"
}

Write-Host "[bootstrap] backend"
Set-Location "$root\backend"
if (-not (Test-Path ".venv")) { python -m venv .venv }
$py = "$root\backend\.venv\Scripts\python.exe"

& $py -m pip install --upgrade pip | Out-Null
& $py -m pip install -e ".[dev]"

$env:DATABASE_URL = "sqlite:///./devflow.db"
if (-not $env:SECRET_KEY) { $env:SECRET_KEY = "local-dev-secret" }
& $py -m alembic upgrade head
& $py -m app.db.seed

Write-Host "[bootstrap] frontend"
Set-Location "$root\frontend"
npm install

Write-Host ""
Write-Host "Done. Two terminals:"
Write-Host "  cd backend;  .venv\Scripts\uvicorn.exe app.main:app --reload"
Write-Host "  cd frontend; npm run dev"
Write-Host ""
Write-Host "Then open http://localhost:5173 and sign in with demo@devflow.dev / demo12345"
