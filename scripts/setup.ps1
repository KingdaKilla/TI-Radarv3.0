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
    Write-Host "Mindestens folgenden Wert setzen:"
    Write-Host "  - POSTGRES_PASSWORD (sicheres Passwort wählen)"
    Write-Host ""
    $answer = Read-Host "Möchten Sie die .env jetzt bearbeiten? [j/N]"
    if ($answer -match "^[jJyY]$") {
        notepad $envFile
        Write-Host "Bitte nach dem Bearbeiten Enter drücken..."
        Read-Host
    }
}

# 3. POSTGRES_PASSWORD prüfen
$envContent = Get-Content $envFile | Where-Object { $_ -notmatch "^\s*#" -and $_ -match "=" }
$envVars = @{}
foreach ($line in $envContent) {
    $parts = $line -split "=", 2
    if ($parts.Count -eq 2) {
        $envVars[$parts[0].Trim()] = $parts[1].Trim()
    }
}

$pgPassword = $envVars["POSTGRES_PASSWORD"]
if ([string]::IsNullOrWhiteSpace($pgPassword)) {
    Write-Host "FEHLER: POSTGRES_PASSWORD ist nicht gesetzt in .env" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Datenbank-Passwort gesetzt" -ForegroundColor Green

# 4. Docker-Images bauen
Write-Host "[...] Baue Docker-Images (kann beim ersten Mal mehrere Minuten dauern)..." -ForegroundColor Yellow
Push-Location $ProjectRoot
docker compose --env-file .env -f deploy/docker-compose.yml build
Pop-Location

Write-Host ""
Write-Host "=== Setup abgeschlossen ===" -ForegroundColor Cyan
Write-Host "Starten mit: .\scripts\start.ps1"
