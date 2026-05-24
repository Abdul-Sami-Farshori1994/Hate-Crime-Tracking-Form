# From project root: starts Postgres (Docker) then runs Alembic migrations.
# Requires Docker Desktop running on Windows.
# Full app in Docker (Postgres + API + web UI): from project root run `docker compose up -d --build` then open http://localhost:8080
# Without Docker DB: optional SQLite in backend/.env (see backend/.env.example).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Starting PostgreSQL (docker compose)..." -ForegroundColor Cyan
docker compose up -d

Write-Host "Waiting for database to accept connections..." -ForegroundColor Cyan
$ready = $false
for ($i = 0; $i -lt 40; $i++) {
    docker compose exec -T db pg_isready -U postgres -d hatecrime 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    Start-Sleep -Seconds 1
}
if (-not $ready) {
    Write-Warning "Database did not become ready in time. Check: docker compose logs db"
}

Set-Location backend
Write-Host "Running alembic upgrade head..." -ForegroundColor Cyan
& ..\.venv\Scripts\alembic.exe upgrade head
Write-Host "Done." -ForegroundColor Green
