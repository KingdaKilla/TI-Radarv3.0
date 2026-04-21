"""Retrieval-Service Konfiguration."""
from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service-Konfiguration — geladen aus Umgebungsvariablen."""

    # --- Embedding Model (sentence-transformers) ---
    embedding_model: str = "BAAI/bge-large-en-v1.5"
    embedding_dimensions: int = 1024

    # --- Database ---
    database_url: str = "postgresql://ti_radar:ti_radar@localhost:5432/ti_radar"
    db_min_connections: int = 2
    db_max_connections: int = 10

    # --- Embedding Provider (TEI auf dediziertem GPU-Pod) ---
    embedding_provider: str = "local"  # "local" or "remote"
    tei_url: str = ""  # z.B. https://<pod-id>-8000.proxy.runpod.net
    tei_timeout_s: float = 30.0

    # --- Reranker ---
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # --- Retrieval ---
    top_k: int = 10
    similarity_threshold: float = 0.3

    # --- gRPC Server ---
    service_port: int = 50081
    service_host: str = "0.0.0.0"

    # --- Observability ---
    log_level: str = "INFO"
    metrics_port: int = 9101

    # --- Timeouts ---
    db_query_timeout_s: float = 30.0

    model_config = {
        "env_prefix": "RETRIEVAL_",
        "env_file": ".env",
        "case_sensitive": False,
    }
