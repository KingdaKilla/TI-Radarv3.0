"""Konfiguration fuer den Maturity-Service.

Pydantic Settings laedt Werte aus Umgebungsvariablen und .env-Dateien.
Alle Konfigurationsparameter sind zentral hier definiert.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service-Konfiguration — geladen aus Umgebungsvariablen."""

    # --- PostgreSQL ---
    database_url: str = "postgresql://ti_radar:ti_radar@localhost:5432/ti_radar"
    db_min_connections: int = 2
    db_max_connections: int = 10

    # --- gRPC Server ---
    service_port: int = 50052
    service_host: str = "0.0.0.0"

    # --- Observability ---
    log_level: str = "INFO"
    metrics_port: int = 9092

    # --- Timeouts ---
    db_query_timeout_s: float = 30.0

    # --- S-Curve Konfiguration ---
    min_patents_for_fit: int = 30

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }
