# TI-Radar Start Script (Windows)
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "=== TI-Radar Start ===" -ForegroundColor Cyan

# .env prüfen
$envFile = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "FEHLER: .env nicht gefunden. Bitte zuerst setup.ps1 ausführen." -ForegroundColor Red
    exit 1
}

# Services starten
Push-Location $ProjectRoot
docker compose --env-file .env -f deploy/docker-compose.yml up -d
Pop-Location

Write-Host ""
Write-Host "=== Services gestartet ===" -ForegroundColor Cyan
Write-Host "Frontend:    http://localhost:3000"
Write-Host "API:         http://localhost:8000"
Write-Host "API Docs:    http://localhost:8000/docs"
Write-Host ""
Write-Host "Logs:   docker compose --env-file .env -f deploy/docker-compose.yml logs -f"
Write-Host "Stop:   docker compose --env-file .env -f deploy/docker-compose.yml down"
