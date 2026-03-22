"""Zentrale Konfiguration via Pydantic Settings fuer den Export-Service.

Alle infrastrukturellen Parameter werden ueber Umgebungsvariablen
oder eine .env-Datei geladen. Enthalt Verbindungsdaten zur Datenbank,
Orchestrator-URL und Export-spezifische Limits.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Anwendungskonfiguration — geladen aus Umgebungsvariablen / .env.

    Der Export-Service benoetigt Zugriff auf:
    - PostgreSQL (export_schema fuer Cache und Export-Log)
    - Orchestrator-Service (fuer frische Analyseergebnisse)
    """

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8020
    debug: bool = False
    log_level: str = "INFO"

    # --- Datenbank (PostgreSQL via asyncpg) ---
    database_url: str = Field(
        default="postgresql://tip:tip@postgres:5432/tip",
        description="PostgreSQL Connection-String fuer asyncpg (export_schema)",
    )

    # --- Orchestrator-Service ---
    orchestrator_url: str = Field(
        default="http://orchestrator-svc:8000",
        description="Base-URL des Orchestrator-Service fuer /api/v1/radar Aufrufe",
    )

    # --- Export-spezifische Limits ---
    cache_ttl_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Lebensdauer von gecachten Analyseergebnissen in Stunden",
    )
    max_rows_csv: int = Field(
        default=100_000,
        ge=1000,
        le=1_000_000,
        description="Maximale Zeilenanzahl pro CSV-Export",
    )

    # --- CORS ---
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS-Origins als Liste (aus kommasepariertem String)."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
