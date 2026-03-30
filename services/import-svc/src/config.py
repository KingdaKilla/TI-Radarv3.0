"""Konfiguration fuer den Import Service via Pydantic Settings.

Alle Einstellungen koennen ueber Umgebungsvariablen gesetzt werden.
Prefix: kein Prefix (flache Struktur, Docker-freundlich).
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Import-Service-Konfiguration.

    Attribute:
        database_url: PostgreSQL-Verbindungs-URL (asyncpg-kompatibel).
        bulk_data_dir: Basisverzeichnis fuer Bulk-Dateien (EPO/, CORDIS/).
        batch_size: Anzahl Datensaetze pro Batch-Insert (COPY).
        max_workers: Maximale Anzahl paralleler Worker fuer Dateiverarbeitung.
        log_level: Logging-Level (DEBUG, INFO, WARNING, ERROR).
        debug: Debug-Modus aktivieren (farbiges Logging, auto-reload).
        cors_origins: Kommagetrennte CORS-Origins.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Datenbank
    database_url: str = "postgresql://ti_radar:ti_radar@localhost:5432/ti_radar"

    # Bulk-Datenverzeichnis
    bulk_data_dir: str = "/data/bulk"

    # Import-Parameter
    batch_size: int = 10_000
    max_workers: int = 4

    # Logging
    log_level: str = "INFO"
    debug: bool = False

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Scheduler (woechentlicher Bulk-Import)
    import_schedule: str = "0 2 * * 0"  # Cron: Sonntag 02:00 UTC
    scheduler_enabled: bool = True
    scheduler_timezone: str = "UTC"

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS-Origins als Liste aufsplitten."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
