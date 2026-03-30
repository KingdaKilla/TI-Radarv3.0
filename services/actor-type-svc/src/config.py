"""Konfiguration fuer den Actor-Type-Service."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service-Konfiguration — geladen aus Umgebungsvariablen."""

    database_url: str = "postgresql://ti_radar:ti_radar@localhost:5432/ti_radar"
    db_min_connections: int = 2
    db_max_connections: int = 10

    service_port: int = 50061
    service_host: str = "0.0.0.0"

    log_level: str = "INFO"
    metrics_port: int = 9101

    db_query_timeout_s: float = 30.0

    # GLEIF LEI Lookup
    gleif_enabled: bool = True
    gleif_timeout_s: float = 10.0
    gleif_rate_limit_rpm: int = 55

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }
