# Daily Postgres backup (run on host with docker compose dev overlay or internal access).
# Example: .\scripts\backup-db.ps1 -OutDir .\backups

param(
    [string]$OutDir = ".\backups",
    [string]$Container = "hatecrime-db-1",
    [string]$DbName = "hatecrime",
    [string]$DbUser = "postgres"
)

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$stamp = Get-Date -Format "yyyy-MM-dd_HHmm"
$outFile = Join-Path $OutDir "hatecrime-$stamp.sql.gz"

docker exec $Container pg_dump -U $DbUser $DbName | gzip > $outFile
Write-Host "Backup written to $outFile"
