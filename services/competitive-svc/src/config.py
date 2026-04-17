"""Konfiguration fuer den Competitive-Service.

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
    service_port: int = 50053
    service_host: str = "0.0.0.0"

    # --- Observability ---
    log_level: str = "INFO"
    metrics_port: int = 9093

    # --- Timeouts ---
    # Symmetrisch zum Orchestrator-Timeout (60s). Niedrigerer Wert würde
    # dazu führen, dass die Entity-Resolution-CTE-Query vom asyncpg-Pool
    # abgebrochen wird, bevor der Orchestrator sie cancelt →
    # entity_resolution_fehlgeschlagen mit leerem Error-String.
    db_query_timeout_s: float = 60.0

    # --- Competitive Konfiguration ---
    top_actors_limit: int = 50
    network_max_nodes: int = 40
    network_max_edges: int = 100

    # --- Entity Resolution (optional, TODO 6.4) ---
    # Wenn True, werden Akteure ueber entity.unified_actors dedupliziert.
    # Faellt automatisch auf Raw-Namen zurueck wenn entity-Tabellen leer.
    use_entity_resolution: bool = True

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }
