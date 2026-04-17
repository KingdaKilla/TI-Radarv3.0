"""Mapper: LandscapeResult -> gRPC Protobuf LandscapeResponse.

Kapselt die gesamte Protobuf-Konstruktionslogik fuer UC1.
Gibt None zurueck, wenn die gRPC-Stubs nicht verfuegbar sind.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

try:
    from shared.generated.python import common_pb2
    from shared.generated.python import uc1_landscape_pb2
except ImportError:
    common_pb2 = None  # type: ignore[assignment]
    uc1_landscape_pb2 = None  # type: ignore[assignment]

from src.use_case import LandscapeResult


def landscape_result_to_proto(
    result: LandscapeResult,
    request_id: str = "",
) -> Any | None:
    """Mappt ein LandscapeResult auf eine Protobuf LandscapeResponse.

    Returns:
        uc1_landscape_pb2.LandscapeResponse oder None, falls Stubs fehlen.
    """
    if uc1_landscape_pb2 is None or common_pb2 is None:
        return None

    # --- Zeitreihe ---
    ts_entries = []
    for entry in result.time_series:
        year = entry["year"]
        ts_entries.append(uc1_landscape_pb2.LandscapeTimeSeriesEntry(
            year=year,
            patent_count=entry.get("patents", 0),
            project_count=entry.get("projects", 0),
            publication_count=entry.get("publications", 0),
            funding_eur=result.funding_by_year.get(year, 0.0),
        ))

    # --- Top Countries ---
    total_activity = sum(int(c.get("total", 0)) for c in result.top_countries) or 1
    country_metrics = []
    for c in result.top_countries:
        count = int(c.get("total", 0))
        country_metrics.append(common_pb2.CountryMetric(
            country_code=str(c["country"]),
            country_name="",  # Frontend kann ISO -> Name mappen
            count=count,
            share=count / total_activity,
        ))

    # --- CAGR ---
    cagr_msg = uc1_landscape_pb2.CagrValues(
        patent_cagr=result.cagr_patents / 100.0,       # Protobuf: Fraction, nicht Prozent
        project_cagr=result.cagr_projects / 100.0,
        publication_cagr=result.cagr_publications / 100.0,
        funding_cagr=result.cagr_funding / 100.0,
        period_years=result.periods,
    )

    # --- Summary ---
    summary = uc1_landscape_pb2.LandscapeSummary(
        total_patents=result.total_patents,
        total_projects=result.total_projects,
        total_publications=result.total_publications,
        total_funding_eur=result.total_funding,
        active_countries=result.active_countries,
        active_actors=0,  # Wird spaeter via Entity Resolution befuellt
    )

    # --- Top CPC Codes ---
    # Bug v3.4.7/C-002: "share" war fälschlicherweise count/total_patents — ergab Werte > 1.0
    # weil Patente mehrere CPC-Codes tragen. Neuer Ansatz:
    #   - share:        normalisiert über die zurückgegebene Top-Liste (Σ = 1.0)
    #   - avg_per_patent: count / total_patents (Multiplizität, kann > 1 sein)
    cpc_entries = []
    cpc_counts_raw = [
        int(cpc.count if hasattr(cpc, "count") else cpc.get("count", 0))
        for cpc in result.top_cpc
    ]
    total_cpc_sum = sum(cpc_counts_raw) or 1  # Vermeidet Division durch 0
    total_patents = result.total_patents or 1
    for cpc, cpc_count in zip(result.top_cpc, cpc_counts_raw):
        cpc_entries.append(uc1_landscape_pb2.CpcCodeCount(
            code=str(cpc.code if hasattr(cpc, "code") else cpc.get("code", "")),
            description=str(cpc.description if hasattr(cpc, "description") else cpc.get("description", "")),
            count=cpc_count,
            share=cpc_count / total_cpc_sum,        # ∈ [0, 1], Σ = 1.0
            avg_per_patent=cpc_count / total_patents,  # Multiplizität, kann > 1 sein
        ))

    # --- Metadata ---
    _severity_map = {
        "LOW": common_pb2.LOW,
        "MEDIUM": common_pb2.MEDIUM,
        "HIGH": common_pb2.HIGH,
    }
    _source_type_map = {
        "PATENT": common_pb2.PATENT,
        "PUBLICATION": common_pb2.PUBLICATION,
        "PROJECT": common_pb2.PROJECT,
        "FUNDING": common_pb2.FUNDING,
    }

    pb_warnings = [
        common_pb2.Warning(
            message=w["message"],
            severity=_severity_map.get(w.get("severity", "LOW"), common_pb2.LOW),
            code=w.get("code", ""),
        )
        for w in result.warnings
    ]

    pb_sources = [
        common_pb2.DataSource(
            name=ds["name"],
            type=_source_type_map.get(ds.get("type", ""), common_pb2.DATA_SOURCE_TYPE_UNSPECIFIED),
            record_count=ds.get("record_count", 0),
        )
        for ds in result.data_sources
    ]

    metadata = common_pb2.ResponseMetadata(
        processing_time_ms=result.processing_time_ms,
        data_sources=pb_sources,
        warnings=pb_warnings,
        request_id=request_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    return uc1_landscape_pb2.LandscapeResponse(
        time_series=ts_entries,
        top_countries=country_metrics,
        cagr_values=cagr_msg,
        summary=summary,
        top_cpc_codes=cpc_entries,
        metadata=metadata,
    )
