"""UC-C PublicationAnalyticsServicer — gRPC-Implementierung der Publikations-Impact-Chain.

Verknuepft CORDIS-Projekte mit ihren Publikationsoutputs und berechnet
Effizienz-Metriken (Publikationen pro Million EUR, DOI-Abdeckung).
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, cast

import asyncpg
import structlog

try:
    import grpc
except ImportError:
    grpc = None  # type: ignore[assignment]

try:
    from shared.generated.python import common_pb2
    from shared.generated.python import uc_c_publications_pb2
    from shared.generated.python import uc_c_publications_pb2_grpc
except ImportError:
    common_pb2 = None  # type: ignore[assignment]
    uc_c_publications_pb2 = None  # type: ignore[assignment]
    uc_c_publications_pb2_grpc = None  # type: ignore[assignment]

from shared.domain.year_completeness import last_complete_year
from src.config import Settings
from src.domain.metrics import compute_pubs_per_million, compute_pubs_per_project
from src.infrastructure.repository import PublicationRepository

logger = structlog.get_logger(__name__)


def _get_base_class() -> type:
    if uc_c_publications_pb2_grpc is not None:
        return uc_c_publications_pb2_grpc.PublicationAnalyticsServiceServicer  # type: ignore[return-value]
    return object


class PublicationAnalyticsServicer(_get_base_class()):  # type: ignore[misc]
    """gRPC-Servicer fuer UC-C Publication Impact Chain."""

    def __init__(self, pool: asyncpg.Pool, settings: Settings | None = None) -> None:
        self._pool = pool
        self._settings = settings or Settings()
        self._repo = PublicationRepository(pool)

    async def AnalyzePublications(self, request: Any, context: Any) -> Any:
        """UC-C: Publikations-Impact-Chain analysieren."""
        t0 = time.monotonic()

        technology = request.technology
        request_id = request.request_id or ""
        start_year = 2015
        end_year = 2025
        if request.time_range and request.time_range.start_year:
            start_year = request.time_range.start_year
        if request.time_range and request.time_range.end_year:
            end_year = request.time_range.end_year
        top_n = request.top_n or 20

        logger.info("analyse_gestartet", technology=technology, request_id=request_id)

        if not technology or not technology.strip():
            if context is not None and grpc is not None:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Feld 'technology' darf nicht leer sein")
            return self._build_empty_response(request_id, t0)

        warnings: list[dict[str, str]] = []
        data_sources: list[dict[str, Any]] = []

        # 4 parallele Abfragen (gleicher Pattern wie actor-type-svc)
        tasks = [
            asyncio.create_task(
                self._repo.publication_summary(technology, start_year, end_year),
                name="pub_summary",
            ),
            asyncio.create_task(
                self._repo.pub_count_by_year(technology, start_year, end_year),
                name="pub_trend",
            ),
            asyncio.create_task(
                self._repo.top_projects_by_pub_count(technology, start_year, end_year, limit=top_n),
                name="top_projects",
            ),
            asyncio.create_task(
                self._repo.top_publications(technology, start_year, end_year, limit=top_n),
                name="top_pubs",
            ),
        ]

        summary: dict[str, Any] = {}
        trend: list[dict[str, Any]] = []
        top_projects_raw: list[dict[str, Any]] = []
        top_pubs: list[dict[str, Any]] = []

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for task, result in zip(tasks, results, strict=False):
            name = task.get_name()
            if isinstance(result, Exception):
                logger.warning("query_fehlgeschlagen", task=name, fehler=str(result))
                warnings.append({
                    "message": f"Query '{name}' fehlgeschlagen: {result}",
                    "severity": "MEDIUM",
                    "code": f"QUERY_FAILED_{name.upper()}",
                })
                continue
            if name == "pub_summary":
                summary = cast(dict[str, Any], result)
            elif name == "pub_trend":
                trend = cast(list[dict[str, Any]], result)
            elif name == "top_projects":
                top_projects_raw = cast(list[dict[str, Any]], result)
            elif name == "top_pubs":
                top_pubs = cast(list[dict[str, Any]], result)

        # Projekte mit pubs_per_million anreichern
        top_projects: list[dict[str, Any]] = []
        for p in top_projects_raw:
            p["publications_per_million_eur"] = compute_pubs_per_million(
                p.get("ec_contribution_eur", 0), p.get("publication_count", 0),
            )
            top_projects.append(p)

        total_pubs = summary.get("total_publications", 0)
        total_proj = summary.get("total_projects_with_pubs", 0)

        if total_pubs > 0:
            data_sources.append({
                "name": "CORDIS Publications (PostgreSQL)",
                "type": "PUBLICATION",
                "record_count": total_pubs,
            })

        processing_time_ms = int((time.monotonic() - t0) * 1000)
        logger.info(
            "analyse_abgeschlossen",
            technology=technology,
            total_pubs=total_pubs,
            dauer_ms=processing_time_ms,
        )

        return self._build_response(
            total_publications=total_pubs,
            total_projects_with_pubs=total_proj,
            publications_per_project=compute_pubs_per_project(total_pubs, total_proj),
            doi_coverage=summary.get("doi_coverage", 0.0) or 0.0,
            pub_trend=trend,
            top_projects=top_projects,
            top_publications=top_pubs,
            data_sources=data_sources,
            warnings=warnings,
            request_id=request_id,
            processing_time_ms=processing_time_ms,
        )

    def _build_response(self, **kwargs: Any) -> Any:
        if uc_c_publications_pb2 is None or common_pb2 is None:
            # MAJ-7/MAJ-8: ``data_complete_year`` aus dem shared-Helper
            # macht das letzte vollstaendige Kalenderjahr explizit. Das
            # Frontend nutzt den Wert fuer den ReferenceArea-Hinweis
            # "Daten ggf. unvollstaendig" auf dem Pub-Trend-Chart.
            return {
                "total_publications": kwargs["total_publications"],
                "total_projects_with_pubs": kwargs["total_projects_with_pubs"],
                "publications_per_project": kwargs["publications_per_project"],
                "doi_coverage": kwargs["doi_coverage"],
                "pub_trend": kwargs["pub_trend"],
                "top_projects": kwargs["top_projects"],
                "top_publications": kwargs["top_publications"],
                "data_complete_year": last_complete_year(),
                "metadata": {
                    "processing_time_ms": kwargs["processing_time_ms"],
                    "data_sources": kwargs["data_sources"],
                    "warnings": kwargs["warnings"],
                    "request_id": kwargs["request_id"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }

        _severity_map = {"LOW": common_pb2.LOW, "MEDIUM": common_pb2.MEDIUM, "HIGH": common_pb2.HIGH}

        pb_trend = [
            uc_c_publications_pb2.PublicationYearEntry(
                year=int(entry["year"]),
                publication_count=int(entry["publication_count"]),
                project_count=int(entry.get("project_count", 0)),
            )
            for entry in kwargs.get("pub_trend", [])
        ]

        pb_projects = [
            uc_c_publications_pb2.ProjectPublicationLink(
                project_acronym=str(proj.get("project_acronym", "")),
                framework=str(proj.get("framework", "")),
                ec_contribution_eur=float(proj.get("ec_contribution_eur", 0)),
                publication_count=int(proj.get("publication_count", 0)),
                publications_per_million_eur=float(proj.get("publications_per_million_eur", 0)),
            )
            for proj in kwargs.get("top_projects", [])
        ]

        pb_pubs = [
            uc_c_publications_pb2.TopPublication(
                title=str(pub.get("title", "")),
                doi=str(pub.get("doi", "")),
                journal=str(pub.get("journal", "")),
                publication_year=int(pub.get("publication_year", 0)),
                project_acronym=str(pub.get("project_acronym", "")),
            )
            for pub in kwargs.get("top_publications", [])
        ]

        metadata = common_pb2.ResponseMetadata(
            processing_time_ms=kwargs["processing_time_ms"],
            data_sources=[
                common_pb2.DataSource(
                    name=ds["name"],
                    type=common_pb2.PUBLICATION,
                    record_count=ds.get("record_count", 0),
                )
                for ds in kwargs["data_sources"]
            ],
            warnings=[
                common_pb2.Warning(
                    message=w["message"],
                    severity=_severity_map.get(w.get("severity", "LOW"), common_pb2.LOW),
                    code=w.get("code", ""),
                )
                for w in kwargs["warnings"]
            ],
            request_id=kwargs["request_id"],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        return uc_c_publications_pb2.PublicationAnalyticsResponse(
            total_publications=kwargs["total_publications"],
            total_projects_with_pubs=kwargs["total_projects_with_pubs"],
            publications_per_project=kwargs["publications_per_project"],
            doi_coverage=kwargs["doi_coverage"],
            pub_trend=pb_trend,
            top_projects=pb_projects,
            top_publications=pb_pubs,
            metadata=metadata,
        )

    def _build_empty_response(self, request_id: str, t0: float) -> Any:
        processing_time_ms = int((time.monotonic() - t0) * 1000)
        return self._build_response(
            total_publications=0, total_projects_with_pubs=0,
            publications_per_project=0.0, doi_coverage=0.0,
            pub_trend=[], top_projects=[], top_publications=[],
            data_sources=[], warnings=[], request_id=request_id,
            processing_time_ms=processing_time_ms,
        )
