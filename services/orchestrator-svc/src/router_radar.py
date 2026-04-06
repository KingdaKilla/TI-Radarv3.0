"""POST /api/v1/radar — Zentraler Radar-Endpoint.

Empfaengt eine Technologie-Anfrage vom Frontend, erzeugt einen
Protobuf-AnalysisRequest und verteilt ihn parallel an alle 12
UC-Services via gRPC. Implementiert:

- Async Fan-Out via asyncio.gather mit return_exceptions=True
- Per-UC Timeout-Konfiguration
- Graceful Degradation: fehlgeschlagene UCs liefern leere Panels + Warnungen
- Protobuf-zu-JSON Konvertierung der Responses
- Prometheus-Metriken pro UC-Aufruf
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any

import grpc
import structlog
from fastapi import APIRouter, Depends, Request

from src.auth import verify_api_key
from src.grpc_clients import GrpcChannelManager
from src.middleware import record_grpc_call, record_radar_request
from src.schemas import (
    DataSourceInfo,
    ExplainabilityInfo,
    HATEOASLinks,
    RadarRequest,
    RadarResponse,
    UCPanel,
    UCPanelMetadata,
    UseCaseError,
    WarningItem,
    WarningSeverity,
)

# Protobuf-Importe (Placeholder bis Kompilierung)
try:
    from google.protobuf.json_format import MessageToDict

    from shared.generated.python import common_pb2
except ImportError:
    common_pb2 = None  # type: ignore[assignment]
    MessageToDict = None  # type: ignore[assignment]

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Radar"])

# ---------------------------------------------------------------------------
# Mapping: UC-Name -> radar.proto UseCase Enum-Wert
# ---------------------------------------------------------------------------
UC_NAME_TO_ENUM: dict[str, str] = {
    "landscape": "UC1_LANDSCAPE",
    "maturity": "UC2_MATURITY",
    "competitive": "UC3_COMPETITIVE",
    "funding": "UC4_FUNDING",
    "cpc_flow": "UC5_CPC_FLOW",
    "geographic": "UC6_GEOGRAPHIC",
    "research_impact": "UC7_RESEARCH_IMPACT",
    "temporal": "UC8_TEMPORAL",
    "tech_cluster": "UC9_TECH_CLUSTER",
    "actor_type": "UC_11_ACTOR_TYPE",
    "patent_grant": "UC_12_PATENT_GRANT",
    "euroscivoc": "UC_10_EUROSCIVOC",
    "publication": "UC_C_PUBLICATION",
}

# Lesbare UC-Bezeichnungen fuer Fehlermeldungen
UC_DISPLAY_NAMES: dict[str, str] = {
    "landscape": "UC1 Landscape",
    "maturity": "UC2 Maturity",
    "competitive": "UC3 Competitive",
    "funding": "UC4 Funding",
    "cpc_flow": "UC5 CPC-Flow",
    "geographic": "UC6 Geographic",
    "research_impact": "UC7 Research-Impact",
    "temporal": "UC8 Temporal",
    "tech_cluster": "UC9 Tech-Cluster",
    "actor_type": "UC11 Actor-Type",
    "patent_grant": "UC12 Patent-Grant",
    "euroscivoc": "UC10 EuroSciVoc",
    "publication": "UC-C Publication Impact Chain",
}


# ---------------------------------------------------------------------------
# Protobuf-Hilfsfunktionen
# ---------------------------------------------------------------------------


def _build_analysis_request(
    request: RadarRequest,
    request_id: str,
    start_year: int,
    end_year: int,
) -> Any:
    """Erzeugt einen Protobuf AnalysisRequest aus dem REST-Request.

    Falls die Protobuf-Stubs noch nicht generiert sind, wird ein
    Dummy-Objekt zurueckgegeben (fuer Entwicklung/Testing).
    """
    if common_pb2 is None:
        # Fallback: Dict-basierter Dummy-Request fuer Entwicklungsmodus
        return {
            "technology": request.technology,
            "time_range": {"start_year": start_year, "end_year": end_year},
            "european_only": request.european_only,
            "cpc_codes": request.cpc_codes,
            "top_n": request.top_n,
            "request_id": request_id,
        }

    # Protobuf-AnalysisRequest aufbauen
    time_range = common_pb2.TimeRange(
        start_year=start_year,
        end_year=end_year,
    )
    return common_pb2.AnalysisRequest(
        technology=request.technology,
        time_range=time_range,
        european_only=request.european_only,
        cpc_codes=request.cpc_codes,
        top_n=request.top_n,
        request_id=request_id,
    )


def _proto_to_dict(proto_response: Any) -> dict[str, Any]:
    """Konvertiert eine Protobuf-Response in ein JSON-kompatibles Dict.

    Verwendet google.protobuf.json_format.MessageToDict mit
    preserve_proto_field_name=True, damit die snake_case-Feldnamen
    erhalten bleiben (konsistent mit dem Frontend).
    """
    if MessageToDict is not None and hasattr(proto_response, "DESCRIPTOR"):
        return MessageToDict(
            proto_response,
            preserving_proto_field_name=True,
            always_print_fields_with_no_presence=True,
            float_precision=6,
        )
    # Fallback: Response ist bereits ein Dict (Entwicklungsmodus)
    if isinstance(proto_response, dict):
        return proto_response
    return {}


def _classify_grpc_error(exc: grpc.RpcError) -> tuple[str, bool]:
    """Klassifiziert einen gRPC-Fehler fuer die Fehlerberichterstattung.

    Returns:
        Tuple (error_code, retryable).
    """
    code = exc.code() if hasattr(exc, "code") else None
    match code:
        case grpc.StatusCode.DEADLINE_EXCEEDED:
            return "TIMEOUT", True
        case grpc.StatusCode.UNAVAILABLE:
            return "UNAVAILABLE", True
        case grpc.StatusCode.INTERNAL:
            return "INTERNAL", False
        case grpc.StatusCode.NOT_FOUND:
            return "NOT_FOUND", False
        case grpc.StatusCode.RESOURCE_EXHAUSTED:
            return "RESOURCE_EXHAUSTED", True
        case grpc.StatusCode.UNIMPLEMENTED:
            return "UNIMPLEMENTED", False
        case _:
            return "UNKNOWN", True


# ---------------------------------------------------------------------------
# Einzelner UC-Aufruf mit Timeout und Fehlerbehandlung
# ---------------------------------------------------------------------------


async def _call_single_uc(
    channel_manager: GrpcChannelManager,
    uc_name: str,
    analysis_request: Any,
    timeout: float,
) -> tuple[str, dict[str, Any] | None, UseCaseError | None, float]:
    """Ruft einen einzelnen UC-Service auf mit Timeout und Fehlerbehandlung.

    Returns:
        Tuple (uc_name, panel_data, error, duration_seconds).
        Bei Erfolg: panel_data ist ein Dict, error ist None.
        Bei Fehler: panel_data ist None, error enthaelt den Fehlerbericht.
    """
    t0 = time.monotonic()

    try:
        # gRPC-Aufruf mit asyncio.wait_for fuer scharfen Timeout
        response = await asyncio.wait_for(
            channel_manager.call_uc(uc_name, analysis_request, timeout=timeout),
            timeout=timeout,
        )

        duration = time.monotonic() - t0
        panel_data = _proto_to_dict(response)

        # Metrik: erfolgreicher Aufruf
        record_grpc_call(uc_name, "success", duration)

        logger.info(
            "uc_aufruf_erfolgreich",
            uc=uc_name,
            duration_ms=int(duration * 1000),
        )

        return uc_name, panel_data, None, duration

    except asyncio.TimeoutError:
        duration = time.monotonic() - t0
        record_grpc_call(uc_name, "timeout", duration)

        error = UseCaseError(
            use_case=uc_name,
            error_code="TIMEOUT",
            error_message=(
                f"{UC_DISPLAY_NAMES.get(uc_name, uc_name)}: "
                f"Timeout nach {timeout:.0f}s"
            ),
            retryable=True,
            elapsed_ms=int(duration * 1000),
        )
        logger.warning(
            "uc_aufruf_timeout",
            uc=uc_name,
            timeout=timeout,
            duration_ms=int(duration * 1000),
        )
        return uc_name, None, error, duration

    except grpc.RpcError as exc:
        duration = time.monotonic() - t0
        error_code, retryable = _classify_grpc_error(exc)
        record_grpc_call(uc_name, error_code.lower(), duration)

        details = exc.details() if hasattr(exc, "details") else str(exc)
        error = UseCaseError(
            use_case=uc_name,
            error_code=error_code,
            error_message=(
                f"{UC_DISPLAY_NAMES.get(uc_name, uc_name)}: "
                f"{error_code} — {details}"
            ),
            retryable=retryable,
            elapsed_ms=int(duration * 1000),
        )
        logger.warning(
            "uc_aufruf_grpc_fehler",
            uc=uc_name,
            error_code=error_code,
            details=details,
            duration_ms=int(duration * 1000),
        )
        return uc_name, None, error, duration

    except RuntimeError as exc:
        # Stubs nicht verfuegbar (Entwicklungsmodus)
        duration = time.monotonic() - t0
        record_grpc_call(uc_name, "unavailable", duration)

        error = UseCaseError(
            use_case=uc_name,
            error_code="STUBS_UNAVAILABLE",
            error_message=(
                f"{UC_DISPLAY_NAMES.get(uc_name, uc_name)}: "
                f"gRPC-Stubs nicht verfuegbar — {exc}"
            ),
            retryable=False,
            elapsed_ms=int(duration * 1000),
        )
        logger.warning("uc_stubs_nicht_verfuegbar", uc=uc_name, error=str(exc))
        return uc_name, None, error, duration

    except Exception as exc:
        duration = time.monotonic() - t0
        record_grpc_call(uc_name, "error", duration)

        error = UseCaseError(
            use_case=uc_name,
            error_code="INTERNAL",
            error_message=(
                f"{UC_DISPLAY_NAMES.get(uc_name, uc_name)}: "
                f"INTERNAL — Unerwarteter Fehler. Siehe Server-Logs."
            ),
            retryable=False,
            elapsed_ms=int(duration * 1000),
        )
        logger.error(
            "uc_aufruf_unerwarteter_fehler",
            uc=uc_name,
            error=str(exc),
            exc_info=True,
        )
        return uc_name, None, error, duration


# ---------------------------------------------------------------------------
# Metadata-Aggregation aus UC-Responses
# ---------------------------------------------------------------------------


def _aggregate_metadata(
    panel_results: dict[str, dict[str, Any]],
) -> ExplainabilityInfo:
    """Aggregiert Metadaten (Quellen, Methoden, Warnungen) aus allen UC-Panels."""
    all_sources: list[DataSourceInfo] = []
    all_methods: list[str] = []
    all_warnings: list[WarningItem] = []
    seen_source_names: set[str] = set()
    seen_methods: set[str] = set()

    for _uc_name, panel_data in panel_results.items():
        metadata = panel_data.get("metadata", {})

        # Datenquellen deduplizieren
        for source in metadata.get("data_sources", []):
            name = source.get("name", "")
            if name and name not in seen_source_names:
                seen_source_names.add(name)
                all_sources.append(DataSourceInfo(
                    name=name,
                    type=source.get("type", "mixed"),
                    record_count=source.get("record_count", 0),
                    last_updated=source.get("last_updated", ""),
                ))

        # Methoden deduplizieren
        # (Methoden-Feld kann in custom response fields sein, nicht in metadata)

        # Warnungen sammeln
        for warning in metadata.get("warnings", []):
            severity_str = warning.get("severity", "LOW")
            try:
                severity = WarningSeverity(severity_str.lower())
            except ValueError:
                severity = WarningSeverity.LOW
            all_warnings.append(WarningItem(
                message=warning.get("message", ""),
                severity=severity,
                code=warning.get("code", ""),
            ))

    return ExplainabilityInfo(
        data_sources=all_sources,
        methods=list(seen_methods) if seen_methods else all_methods,
        deterministic=True,
        warnings=all_warnings,
    )


# ---------------------------------------------------------------------------
# Haupt-Endpoint: POST /api/v1/radar
# ---------------------------------------------------------------------------


@router.post("/radar", response_model=RadarResponse, dependencies=[Depends(verify_api_key)])
async def analyze_technology(
    request: RadarRequest,
    http_request: Request,
) -> RadarResponse:
    """Technology Radar: Alle 13 UC-Services parallel per gRPC aufrufen.

    Gibt ein komplettes Dashboard-Objekt zurueck mit:
    - 12 UC-Panels (Landscape, Maturity, Competitive, Funding, CPC-Flow,
      Geographic, Research-Impact, Temporal, Tech-Cluster, Actor-Type,
      Patent-Grant, EuroSciVoc)
    - Fehlerliste fuer ausgefallene UCs (Graceful Degradation)
    - Aggregierte Explainability-Metadaten (Quellen, Methoden, Warnungen)
    - Gesamtverarbeitungszeit und Erfolgsstatistiken
    """
    t0 = time.monotonic()
    request_id: str = getattr(http_request.state, "request_id", "")

    # Analysezeitraum berechnen
    current_year = datetime.now().year
    start_year = current_year - request.years

    # gRPC Channel-Manager aus App-State holen
    channel_manager: GrpcChannelManager = http_request.app.state.grpc_channels

    # Protobuf-AnalysisRequest erzeugen
    analysis_request = _build_analysis_request(
        request, request_id, start_year, current_year,
    )

    # UC-Auswahl bestimmen (leer = alle 13 UCs)
    all_uc_names = list(UC_NAME_TO_ENUM.keys())
    if request.use_cases:
        # Nur angeforderte UCs ausfuehren
        selected = set(request.use_cases)
        uc_names = [name for name in all_uc_names if name in selected]
    else:
        uc_names = all_uc_names

    total_uc_count = len(uc_names)

    logger.info(
        "radar_analyse_start",
        technology=request.technology,
        years=request.years,
        start_year=start_year,
        end_year=current_year,
        uc_count=total_uc_count,
        european_only=request.european_only,
    )

    # --- Paralleler Fan-Out an alle UC-Services ---
    tasks = [
        _call_single_uc(
            channel_manager=channel_manager,
            uc_name=uc_name,
            analysis_request=analysis_request,
            timeout=channel_manager.get_timeout(uc_name),
        )
        for uc_name in uc_names
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # --- Ergebnisse aggregieren (Graceful Degradation) ---
    panel_data: dict[str, dict[str, Any]] = {}
    uc_errors: list[UseCaseError] = []

    for result in results:
        if isinstance(result, BaseException):
            # Unerwarteter Fehler im gather selbst (sollte nicht vorkommen)
            logger.error("gather_unerwarteter_fehler", error=str(result))
            continue

        uc_name, data, error, _duration = result

        if error is not None:
            uc_errors.append(error)
            panel_data[uc_name] = {}  # Leeres Panel bei Fehler
        elif data is not None:
            panel_data[uc_name] = data
        else:
            panel_data[uc_name] = {}

    # --- Warnungen fuer degradierte UCs hinzufuegen ---
    explainability = _aggregate_metadata(panel_data)
    for uc_error in uc_errors:
        explainability.warnings.append(WarningItem(
            message=uc_error.error_message,
            severity=WarningSeverity.HIGH,
            code=uc_error.error_code,
        ))

    # --- Statistiken ---
    successful_count = total_uc_count - len(uc_errors)
    elapsed_ms = int((time.monotonic() - t0) * 1000)

    # Metrik: Radar-Request-Ergebnis
    if len(uc_errors) == 0:
        record_radar_request("success")
    elif successful_count > 0:
        record_radar_request("partial")
    else:
        record_radar_request("failure")

    logger.info(
        "radar_analyse_abgeschlossen",
        technology=request.technology,
        duration_ms=elapsed_ms,
        successful=successful_count,
        failed=len(uc_errors),
        total=total_uc_count,
    )

    # --- Typisierte UC-Panels aufbauen ---
    panels: list[UCPanel] = []
    for uc_name, data in panel_data.items():
        panel_meta = UCPanelMetadata()
        if data and "metadata" in data:
            raw_meta = data["metadata"]
            panel_meta = UCPanelMetadata(
                processing_time_ms=int(raw_meta.get("processing_time_ms", 0)),
                request_id=raw_meta.get("request_id", ""),
                timestamp=raw_meta.get("timestamp", ""),
            )
        panels.append(UCPanel(use_case=uc_name, data=data, metadata=panel_meta))

    # --- HATEOAS-Links ---
    tech_encoded = request.technology.replace(" ", "%20")
    links = HATEOASLinks(
        self="/api/v1/radar",
        export_csv="/api/v1/export/csv",
        export_json="/api/v1/export/json",
        export_xlsx="/api/v1/export/xlsx",
        export_pdf="/api/v1/export/pdf",
        suggestions=f"/api/v1/suggestions?q={tech_encoded}",
    )

    # --- Response zusammenbauen ---
    return RadarResponse(
        technology=request.technology,
        analysis_period=f"{start_year}-{current_year}",
        panels=panels,
        landscape=panel_data.get("landscape", {}),
        maturity=panel_data.get("maturity", {}),
        competitive=panel_data.get("competitive", {}),
        funding=panel_data.get("funding", {}),
        cpc_flow=panel_data.get("cpc_flow", {}),
        geographic=panel_data.get("geographic", {}),
        research_impact=panel_data.get("research_impact", {}),
        temporal=panel_data.get("temporal", {}),
        tech_cluster=panel_data.get("tech_cluster", {}),
        actor_type=panel_data.get("actor_type", {}),
        patent_grant=panel_data.get("patent_grant", {}),
        euroscivoc=panel_data.get("euroscivoc", {}),
        publication=panel_data.get("publication", {}),
        **{"_links": links},
        uc_errors=uc_errors,
        explainability=explainability,
        total_processing_time_ms=elapsed_ms,
        successful_uc_count=successful_count,
        total_uc_count=total_uc_count,
        request_id=request_id,
        timestamp=datetime.now().isoformat(),
    )
