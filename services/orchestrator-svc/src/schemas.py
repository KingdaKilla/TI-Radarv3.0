"""Pydantic Request/Response-Modelle fuer die REST-API.

Die Modelle bilden die gRPC-Protobuf-Nachrichten auf JSON-kompatible
Pydantic-Strukturen ab. Das Frontend erhaelt ausschliesslich diese
JSON-Modelle — Protobuf-Details sind intern.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

import re

from pydantic import BaseModel, Field, field_validator

# =============================================================================
# Allowlists / Validation constants
# =============================================================================

_VALID_UC_NAMES: frozenset[str] = frozenset({
    "landscape", "maturity", "competitive", "funding", "cpc_flow",
    "geographic", "research_impact", "temporal", "tech_cluster",
    "actor_type", "patent_grant", "euroscivoc", "publication",
})

_CPC_CODE_RE: re.Pattern[str] = re.compile(
    r"^[A-H]\d{2}[A-Z]?\d{0,4}(/\d{1,6})?$"
)

_MAX_CPC_CODES = 50


# =============================================================================
# Request-Modelle
# =============================================================================


class RadarRequest(BaseModel):
    """Anfrage fuer eine Technology-Radar-Analyse.

    Entspricht der RadarRequest-Protobuf-Nachricht in radar.proto.
    """

    technology: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Technologie-Suchbegriff (z.B. 'solid-state batteries', 'CRISPR')",
    )
    years: int = Field(
        default=10,
        ge=3,
        le=30,
        description="Analysezeitraum in Jahren (rueckblickend ab heute)",
    )
    european_only: bool = Field(
        default=False,
        description="Nur EU-27 + assoziierte Laender beruecksichtigen",
    )
    cpc_codes: list[str] = Field(
        default_factory=list,
        description="Optionale CPC-Codes zur Einschraenkung der Patent-Suche",
    )
    top_n: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Maximale Anzahl Top-N-Eintraege (0 = Service-Default)",
    )
    use_cases: list[str] = Field(
        default_factory=list,
        description="Selektive UC-Ausfuehrung (leer = alle 13 UCs)",
    )

    @field_validator("use_cases")
    @classmethod
    def validate_use_cases(cls, v: list[str]) -> list[str]:
        invalid = [uc for uc in v if uc not in _VALID_UC_NAMES]
        if invalid:
            raise ValueError(
                f"Unknown use_cases: {invalid}. "
                f"Allowed: {sorted(_VALID_UC_NAMES)}"
            )
        return v

    @field_validator("cpc_codes")
    @classmethod
    def validate_cpc_codes(cls, v: list[str]) -> list[str]:
        if len(v) > _MAX_CPC_CODES:
            raise ValueError(
                f"Too many CPC codes: {len(v)} (max {_MAX_CPC_CODES})"
            )
        for code in v:
            if not _CPC_CODE_RE.match(code):
                raise ValueError(
                    f"Invalid CPC code format: '{code}'. "
                    f"Expected pattern: [A-H]<digits>[<letter>][<digits>][/<digits>]"
                )
        return v


# =============================================================================
# Response: Warnungen und Metadaten
# =============================================================================


class WarningSeverity(StrEnum):
    """Schweregrad einer Warnung."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class WarningItem(BaseModel):
    """Nicht-fatale Warnung aus einem UC-Service."""

    message: str
    severity: WarningSeverity = WarningSeverity.LOW
    code: str = ""


class DataSourceInfo(BaseModel):
    """Metadaten einer genutzten Datenquelle."""

    name: str
    type: str = "mixed"
    record_count: int = 0
    last_updated: str = ""


class UseCaseError(BaseModel):
    """Fehlerbericht eines einzelnen UC-Service (Graceful Degradation)."""

    use_case: str
    error_code: str
    error_message: str
    retryable: bool = True
    elapsed_ms: int = 0


class ExplainabilityInfo(BaseModel):
    """Transparenz-Metadaten aggregiert ueber alle UC-Services."""

    data_sources: list[DataSourceInfo] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)
    deterministic: bool = True
    warnings: list[WarningItem] = Field(default_factory=list)


# =============================================================================
# Response: Haupt-Radar-Antwort
# =============================================================================


class UCPanelMetadata(BaseModel):
    """Metadaten eines einzelnen UC-Panel-Ergebnisses."""

    processing_time_ms: int = 0
    data_sources: list[DataSourceInfo] = Field(default_factory=list)
    warnings: list[WarningItem] = Field(default_factory=list)
    request_id: str = ""
    timestamp: str = ""


class UCPanel(BaseModel):
    """Typisiertes UC-Panel mit Discriminator-Feld.

    Das ``use_case``-Feld identifiziert den konkreten Panel-Typ (analog zu
    TMF630 @type). ``data`` enthaelt die panel-spezifischen Ergebnisse aus
    der Protobuf-Konvertierung. ``metadata`` liefert Panel-Metadaten.

    Bei Graceful Degradation: data = {}, metadata bleibt leer.
    """

    use_case: str = Field(description="Panel-Typ / Discriminator (z.B. 'landscape', 'maturity')")
    data: dict[str, Any] = Field(default_factory=dict, description="Panel-spezifische Ergebnisdaten")
    metadata: UCPanelMetadata = Field(default_factory=UCPanelMetadata)


class HATEOASLinks(BaseModel):
    """Navigierbare Links zu verwandten Ressourcen (HATEOAS-Prinzip)."""

    self: str = ""
    export_csv: str = ""
    export_json: str = ""
    export_xlsx: str = ""
    export_pdf: str = ""
    suggestions: str = ""


class RadarResponse(BaseModel):
    """Komplette Radar-Antwort mit allen UC-Panels.

    Jedes Panel ist als typisiertes ``UCPanel``-Objekt modelliert, wobei
    das ``use_case``-Feld als Discriminator dient (analog zu TMF630 @type).
    Zusaetzlich bleiben die UC-Panels als flache Felder erhalten fuer
    Abwaertskompatibilitaet.

    Bei Graceful Degradation enthaelt ein fehlgeschlagenes Panel ein
    leeres ``data: {}`` und der Fehler wird in ``uc_errors`` gemeldet.
    """

    technology: str
    analysis_period: str

    # Typisierte UC-Panels als Liste (neues Format mit Discriminator)
    panels: list[UCPanel] = Field(default_factory=list, description="Alle UC-Panel-Ergebnisse als typisierte Liste")

    # 12 UC-Panels als flache Felder (Abwaertskompatibilitaet)
    landscape: dict[str, Any] = Field(default_factory=dict)
    maturity: dict[str, Any] = Field(default_factory=dict)
    competitive: dict[str, Any] = Field(default_factory=dict)
    funding: dict[str, Any] = Field(default_factory=dict)
    cpc_flow: dict[str, Any] = Field(default_factory=dict)
    geographic: dict[str, Any] = Field(default_factory=dict)
    research_impact: dict[str, Any] = Field(default_factory=dict)
    temporal: dict[str, Any] = Field(default_factory=dict)
    tech_cluster: dict[str, Any] = Field(default_factory=dict)
    actor_type: dict[str, Any] = Field(default_factory=dict)
    patent_grant: dict[str, Any] = Field(default_factory=dict)
    euroscivoc: dict[str, Any] = Field(default_factory=dict)
    publication: dict[str, Any] = Field(default_factory=dict)

    # HATEOAS-Links
    links: HATEOASLinks = Field(default_factory=HATEOASLinks, alias="_links")

    # Orchestrator-Metadaten
    uc_errors: list[UseCaseError] = Field(default_factory=list)
    explainability: ExplainabilityInfo = Field(default_factory=ExplainabilityInfo)
    total_processing_time_ms: int = 0
    successful_uc_count: int = 0
    total_uc_count: int = 13
    request_id: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


# =============================================================================
# Health-Response
# =============================================================================


class ServiceHealthStatus(BaseModel):
    """Zustand eines einzelnen Downstream-Service."""

    service_name: str
    use_case: str
    healthy: bool
    latency_ms: int = 0
    error: str = ""
    version: str = ""


class HealthResponse(BaseModel):
    """Aggregierte Health-Antwort des Orchestrators."""

    healthy: bool
    services: list[ServiceHealthStatus] = Field(default_factory=list)
    version: str = "3.0.0"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    database_healthy: bool = False


# =============================================================================
# Suggestions-Response
# =============================================================================


class SuggestionResponse(BaseModel):
    """Autocomplete-Vorschlaege fuer das Suchfeld."""

    suggestions: list[str] = Field(default_factory=list)
    source: str = "database"
    query: str = ""
