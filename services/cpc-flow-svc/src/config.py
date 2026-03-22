"""Konfiguration fuer den CPC-Flow-Service.

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
    service_port: int = 50055
    service_host: str = "0.0.0.0"

    # --- Observability ---
    log_level: str = "INFO"
    metrics_port: int = 9095

    # --- Timeouts ---
    db_query_timeout_s: float = 60.0  # CPC-Jaccard kann laenger dauern

    # --- CPC-Flow Konfiguration ---
    cpc_level: int = 4
    top_n_codes: int = 15
    sample_size: int = 10_000
    similarity_threshold: float = 0.01

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }
