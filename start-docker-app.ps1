# Build and run Postgres + API + web UI. Requires Docker Desktop (Linux containers) running.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

docker info 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Docker Engine is not available. On Windows:" -ForegroundColor Yellow
    Write-Host "  1. Open Docker Desktop from the Start menu." -ForegroundColor Yellow
    Write-Host "  2. Wait until it shows 'Engine running'." -ForegroundColor Yellow
    Write-Host "  3. Run this script again: .\start-docker-app.ps1" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host "Building and starting containers..." -ForegroundColor Cyan
docker compose up -d --build

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "  Web app:  http://localhost:8080" -ForegroundColor Green
Write-Host "  API docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "  Postgres: localhost:5433 (user/pass postgres/postgres, DB hatecrime)" -ForegroundColor Green
Write-Host ""
Write-Host "Local dev (uvicorn on your PC): keep DATABASE_URL=...@127.0.0.1:5433 in backend/.env" -ForegroundColor DarkGray
