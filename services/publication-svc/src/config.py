"""Konfiguration fuer den Publication-Analytics-Service."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service-Konfiguration — geladen aus Umgebungsvariablen."""

    database_url: str = "postgresql://ti_radar:ti_radar@localhost:5432/ti_radar"
    db_min_connections: int = 2
    db_max_connections: int = 10

    service_port: int = 50051
    service_host: str = "0.0.0.0"

    log_level: str = "INFO"
    metrics_port: int = 9101

    db_query_timeout_s: float = 30.0

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }
