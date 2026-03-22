"""Mapper: LandscapeResult -> dict-basierte Response.

Fallback-Format fuer Tests und Entwicklung ohne generierte gRPC-Stubs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.use_case import LandscapeResult


def landscape_result_to_dict(
    result: LandscapeResult,
    request_id: str = "",
) -> dict[str, Any]:
    """Mappt ein LandscapeResult auf ein Response-dict.

    Nuetzlich fuer Unit-Tests und lokale Entwicklung ohne Protobuf-Stubs.
    """
    return {
        "time_series": [
            {
                "year": entry["year"],
                "patent_count": entry.get("patents", 0),
                "project_count": entry.get("projects", 0),
                "publication_count": entry.get("publications", 0),
                "funding_eur": result.funding_by_year.get(entry["year"], 0.0),
            }
            for entry in result.time_series
        ],
        "top_countries": result.top_countries,
        "cagr_values": {
            "patent_cagr": result.cagr_patents / 100.0,
            "project_cagr": result.cagr_projects / 100.0,
            "publication_cagr": result.cagr_publications / 100.0,
            "funding_cagr": result.cagr_funding / 100.0,
            "period_years": result.periods,
        },
        "summary": {
            "total_patents": result.total_patents,
            "total_projects": result.total_projects,
            "total_publications": result.total_publications,
            "total_funding_eur": result.total_funding,
            "active_countries": result.active_countries,
            "active_actors": 0,
        },
        "top_cpc_codes": result.top_cpc,
        "metadata": {
            "processing_time_ms": result.processing_time_ms,
            "data_sources": result.data_sources,
            "warnings": result.warnings,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
