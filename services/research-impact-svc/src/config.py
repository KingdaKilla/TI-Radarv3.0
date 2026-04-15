"""Konfiguration fuer den Research-Impact-Service.

Pydantic Settings laedt Werte aus Umgebungsvariablen und .env-Dateien.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service-Konfiguration — geladen aus Umgebungsvariablen."""

    # --- PostgreSQL (fuer zukuenftige lokale Paper-Daten) ---
    database_url: str = "postgresql://ti_radar:ti_radar@localhost:5432/ti_radar"
    db_min_connections: int = 2
    db_max_connections: int = 10

    # --- Semantic Scholar API ---
    semantic_scholar_api_key: str = ""
    semantic_scholar_timeout_s: float = 15.0
    semantic_scholar_max_results: int = 200

    # --- gRPC Server ---
    service_port: int = 50057
    service_host: str = "0.0.0.0"

    # --- Observability ---
    log_level: str = "INFO"
    metrics_port: int = 9097

    # --- Timeouts ---
    db_query_timeout_s: float = 30.0

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }
