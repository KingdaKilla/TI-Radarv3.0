# TI-Radar Start Script (Windows)
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "=== TI-Radar Start ===" -ForegroundColor Cyan

# .env pruefen
$envFile = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "FEHLER: .env nicht gefunden. Bitte zuerst setup.ps1 ausfuehren." -ForegroundColor Red
    exit 1
}

# TI_RADAR_DB_PATH pruefen
$envContent = Get-Content $envFile | Where-Object { $_ -notmatch "^\s*#" -and $_ -match "=" }
$envVars = @{}
foreach ($line in $envContent) {
    $parts = $line -split "=", 2
    if ($parts.Count -eq 2) {
        $envVars[$parts[0].Trim()] = $parts[1].Trim()
    }
}

$dbPath = $envVars["TI_RADAR_DB_PATH"]
if ([string]::IsNullOrWhiteSpace($dbPath)) {
    Write-Host "FEHLER: TI_RADAR_DB_PATH nicht gesetzt in .env" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $dbPath)) {
    Write-Host "FEHLER: Datenbank-Verzeichnis nicht gefunden: $dbPath" -ForegroundColor Red
    Write-Host "Ist das externe Laufwerk angeschlossen?"
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
