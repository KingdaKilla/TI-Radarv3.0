"""Zentrale Konfiguration via Pydantic Settings.

Alle UC-Service-Adressen, Timeouts und infrastrukturelle Parameter
werden ueber Umgebungsvariablen oder .env-Datei geladen.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class UCServiceConfig:
    """Konfiguration eines einzelnen UC-Service (Adresse + Timeout)."""

    __slots__ = ("address", "timeout")

    def __init__(self, address: str, timeout: float) -> None:
        self.address = address
        self.timeout = timeout

    def __repr__(self) -> str:
        return f"UCServiceConfig(address={self.address!r}, timeout={self.timeout})"


class Settings(BaseSettings):
    """Anwendungskonfiguration — geladen aus Umgebungsvariablen / .env.

    Jeder UC-Service hat eine separate Adresse und einen individuellen
    Timeout (in Sekunden). Die Werte koennen per Umgebungsvariable
    ueberschrieben werden (z.B. UC_LANDSCAPE_ADDRESS=landscape-svc:50051).
    """

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"

    # --- CORS ---
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- Datenbank (fuer Suggestions-Endpoint via asyncpg) ---
    database_url: str = Field(
        default="postgresql://tip:tip@postgres:5432/tip",
        description="PostgreSQL Connection-String fuer asyncpg",
    )

    # --- gRPC: UC-Service-Adressen (host:port) ---
    uc_landscape_address: str = "landscape-svc:50051"
    uc_maturity_address: str = "maturity-svc:50051"
    uc_competitive_address: str = "competitive-svc:50051"
    uc_funding_address: str = "funding-svc:50051"
    uc_cpc_flow_address: str = "cpc-flow-svc:50051"
    uc_geographic_address: str = "geographic-svc:50051"
    uc_research_impact_address: str = "research-impact-svc:50051"
    uc_temporal_address: str = "temporal-svc:50051"
    uc_tech_cluster_address: str = "tech-cluster-svc:50051"
    uc_actor_type_address: str = "actor-type-svc:50051"
    uc_patent_grant_address: str = "patent-grant-svc:50051"
    uc_euroscivoc_address: str = "euroscivoc-svc:50051"
    uc_publication_address: str = "publication-svc:50051"

    # --- LLM-Service (v3.5.0) ---
    # gRPC-Adresse des llm-svc. Der analyze-panel Endpoint forwardet Requests
    # per gRPC dorthin. Bei leerem Default bzw. gesetzter ENV `LLM_ADDRESS`
    # wird der Service aktiv; sonst liefert der Endpoint leeres Ergebnis.
    llm_address: str = "llm-svc:50070"
    llm_timeout_s: float = 30.0

    # --- gRPC: Per-UC Timeouts (Sekunden) ---
    uc_landscape_timeout: float = 60.0     # bei parallelen Requests DB-Pool-Contention
    uc_maturity_timeout: float = 60.0      # COUNT(DISTINCT family_id) auf grossen Datasets langsam
    uc_competitive_timeout: float = 60.0   # Entity Resolution + Netzwerk-Berechnung
    uc_funding_timeout: float = 30.0
    uc_cpc_flow_timeout: float = 60.0       # CPC-Jaccard auf patent_cpc ist rechenintensiv
    uc_geographic_timeout: float = 30.0
    uc_research_impact_timeout: float = 30.0  # Externe API (OpenAlex)
    uc_temporal_timeout: float = 60.0      # bei parallelen Requests DB-Pool-Contention
    uc_tech_cluster_timeout: float = 60.0   # Community-Detection ist rechenintensiv
    uc_actor_type_timeout: float = 30.0
    uc_patent_grant_timeout: float = 30.0
    uc_euroscivoc_timeout: float = 30.0
    uc_publication_timeout: float = 60.0   # bei parallelen Requests DB-Pool-Contention

    # --- gRPC: Globale Einstellungen ---
    grpc_max_message_size: int = Field(
        default=50 * 1024 * 1024,  # 50 MB
        description="Maximale gRPC-Nachrichtengroesse in Bytes",
    )

    # --- Prometheus ---
    metrics_enabled: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # -----------------------------------------------------------------
    # Hilfsmethoden: UC-Service-Konfigurationen als strukturierte Objekte
    # -----------------------------------------------------------------

    def get_uc_configs(self) -> dict[str, UCServiceConfig]:
        """Gibt alle 13 UC-Service-Konfigurationen als Dict zurueck.

        Keys entsprechen den Panel-Namen im RadarResponse.
        """
        return {
            "landscape": UCServiceConfig(
                self.uc_landscape_address, self.uc_landscape_timeout,
            ),
            "maturity": UCServiceConfig(
                self.uc_maturity_address, self.uc_maturity_timeout,
            ),
            "competitive": UCServiceConfig(
                self.uc_competitive_address, self.uc_competitive_timeout,
            ),
            "funding": UCServiceConfig(
                self.uc_funding_address, self.uc_funding_timeout,
            ),
            "cpc_flow": UCServiceConfig(
                self.uc_cpc_flow_address, self.uc_cpc_flow_timeout,
            ),
            "geographic": UCServiceConfig(
                self.uc_geographic_address, self.uc_geographic_timeout,
            ),
            "research_impact": UCServiceConfig(
                self.uc_research_impact_address, self.uc_research_impact_timeout,
            ),
            "temporal": UCServiceConfig(
                self.uc_temporal_address, self.uc_temporal_timeout,
            ),
            "tech_cluster": UCServiceConfig(
                self.uc_tech_cluster_address, self.uc_tech_cluster_timeout,
            ),
            "actor_type": UCServiceConfig(
                self.uc_actor_type_address, self.uc_actor_type_timeout,
            ),
            "patent_grant": UCServiceConfig(
                self.uc_patent_grant_address, self.uc_patent_grant_timeout,
            ),
            "euroscivoc": UCServiceConfig(
                self.uc_euroscivoc_address, self.uc_euroscivoc_timeout,
            ),
            "publication": UCServiceConfig(
                self.uc_publication_address, self.uc_publication_timeout,
            ),
        }

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS-Origins als Liste (aus kommasepariertem String)."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
