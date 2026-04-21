"""Embedding-Service Konfiguration."""
from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service-Konfiguration — geladen aus Umgebungsvariablen."""

    # --- Embedding Model (sentence-transformers) ---
    embedding_model: str = "BAAI/bge-large-en-v1.5"
    embedding_dimensions: int = 1024
    batch_size: int = 2048

    # --- Database ---
    database_url: str = "postgresql://ti_radar:ti_radar@localhost:5432/ti_radar"
    db_min_connections: int = 2
    db_max_connections: int = 10

    # --- gRPC Server ---
    service_port: int = 50080
    service_host: str = "0.0.0.0"

    # --- Observability ---
    log_level: str = "INFO"
    metrics_port: int = 9100

    # --- Device ---
    device: str = "cuda"  # "cuda" or "cpu"

    # --- Remote Embedding (TEI auf dediziertem GPU-Pod) ---
    embedding_provider: str = "local"  # "local" or "remote"
    tei_url: str = ""  # z.B. https://<pod-id>-8000.proxy.runpod.net
    tei_batch_size: int = 500  # Texte pro TEI-Request
    tei_timeout_s: float = 120.0

    # --- Retry ---
    retry_max_attempts: int = 5
    retry_base_delay: float = 1.0

    # --- Timeouts ---
    db_query_timeout_s: float = 30.0

    model_config = {
        "env_prefix": "EMBEDDING_",
        "env_file": ".env",
        "case_sensitive": False,
    }
