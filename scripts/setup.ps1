# TI-Radar Setup Script (Windows)
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "=== TI-Radar Setup ===" -ForegroundColor Cyan

# 1. Docker prüfen
try {
    $dockerVersion = docker --version
    Write-Host "[OK] Docker gefunden: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "FEHLER: Docker ist nicht installiert." -ForegroundColor Red
    Write-Host "Download: https://www.docker.com/products/docker-desktop"
    exit 1
}

try {
    docker compose version | Out-Null
} catch {
    Write-Host "FEHLER: Docker Compose Plugin nicht gefunden." -ForegroundColor Red
    exit 1
}

# 2. .env erstellen falls nicht vorhanden
$envFile = Join-Path $ProjectRoot ".env"
$envExample = Join-Path $ProjectRoot ".env.example"

if (-not (Test-Path $envFile)) {
    Copy-Item $envExample $envFile
    Write-Host "[INFO] .env aus .env.example erstellt. Bitte Werte eintragen!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Mindestens folgende Werte müssen gesetzt werden:"
    Write-Host "  - POSTGRES_PASSWORD"
    Write-Host "  - TI_RADAR_DB_PATH (z.B. D:/ti-radar-db)"
    Write-Host ""
    $answer = Read-Host "Möchten Sie die .env jetzt bearbeiten? [j/N]"
    if ($answer -match "^[jJyY]$") {
        notepad $envFile
        Write-Host "Bitte nach dem Bearbeiten Enter drücken..."
        Read-Host
    }
}

# 3. TI_RADAR_DB_PATH prüfen
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
    Write-Host "FEHLER: TI_RADAR_DB_PATH ist nicht gesetzt in .env" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $dbPath)) {
    Write-Host "[INFO] Erstelle Datenbank-Verzeichnis: $dbPath" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $dbPath -Force | Out-Null
}
Write-Host "[OK] Datenbank-Verzeichnis: $dbPath" -ForegroundColor Green

# 4. Docker-Images bauen
Write-Host "[...] Baue Docker-Images (kann beim ersten Mal mehrere Minuten dauern)..." -ForegroundColor Yellow
Push-Location $ProjectRoot
docker compose --env-file .env -f deploy/docker-compose.yml build
Pop-Location

Write-Host ""
Write-Host "=== Setup abgeschlossen ===" -ForegroundColor Cyan
Write-Host "Starten mit: .\scripts\start.ps1"
