"""UC7 ResearchImpactServicer — gRPC-Implementierung der Research-Impact-Analyse.

Empfaengt AnalysisRequest, ruft Semantic Scholar API auf,
berechnet h-Index, Zitationstrends, Top-Papers und Venues.

Migration von MVP v1.0:
- FastAPI Response -> gRPC Protobuf Messages
- Semantic Scholar Adapter bleibt httpx-basiert
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import asyncpg
import structlog

# --- gRPC-Imports (try/except, da Stubs noch nicht generiert) ---
try:
    import grpc
    from grpc import aio as grpc_aio
except ImportError:
    grpc = None  # type: ignore[assignment]
    grpc_aio = None  # type: ignore[assignment]

try:
    from shared.generated.python import common_pb2
    from shared.generated.python import uc7_research_impact_pb2
    from shared.generated.python import uc7_research_impact_pb2_grpc
except ImportError:
    common_pb2 = None  # type: ignore[assignment]
    uc7_research_impact_pb2 = None  # type: ignore[assignment]
    uc7_research_impact_pb2_grpc = None  # type: ignore[assignment]

# --- Shared Domain Metriken ---
try:
    from shared.domain.research_metrics import (
        _compute_citation_trend,
        _compute_h_index,
        _compute_publication_types,
        _compute_top_papers,
        _compute_venue_distribution,
    )
except ImportError:
    from src.domain.metrics import (
        compute_citation_trend as _compute_citation_trend,
        compute_h_index as _compute_h_index,
        compute_publication_types as _compute_publication_types,
        compute_top_papers as _compute_top_papers,
        compute_venue_distribution as _compute_venue_distribution,
    )

from shared.domain.year_completeness import last_complete_year
from src.config import Settings
from src.domain.metrics import compute_i10_index
from src.infrastructure.repository import ResearchImpactRepository
from src.infrastructure.semantic_scholar_adapter import SemanticScholarAdapter

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Helper: Basis-Klasse ermitteln
# ---------------------------------------------------------------------------
def _get_base_class() -> type:
    """Gibt die gRPC-Servicer-Basisklasse zurueck, oder object als Fallback."""
    if uc7_research_impact_pb2_grpc is not None:
        return uc7_research_impact_pb2_grpc.ResearchImpactServiceServicer  # type: ignore[return-value]
    return object


class ResearchImpactServicer(_get_base_class()):  # type: ignore[misc]
    """gRPC-Servicer fuer UC7 Research Impact.

    Ruft Semantic Scholar API auf und berechnet:
    1. h-Index (Hirsch 2005)
    2. Zitationstrend pro Jahr
    3. Top-Papers nach Zitationen
    4. Top-Venues nach Publikationsvolumen
    5. Publikationstypen-Verteilung
    """

    def __init__(self, pool: asyncpg.Pool, settings: Settings | None = None) -> None:
        self._pool = pool
        self._settings = settings or Settings()
        self._repo = ResearchImpactRepository(pool)
        self._semantic_scholar = SemanticScholarAdapter(
            api_key=self._settings.semantic_scholar_api_key,
            timeout=self._settings.semantic_scholar_timeout_s,
            max_results=self._settings.semantic_scholar_max_results,
            pool=pool,
        )

    async def AnalyzeResearchImpact(
        self,
        request: Any,
        context: Any,
    ) -> Any:
        """UC7: Forschungswirkung analysieren.

        Args:
            request: tip.common.AnalysisRequest Protobuf-Message
            context: gRPC ServicerContext

        Returns:
            tip.uc7.ResearchImpactResponse Protobuf-Message
        """
        t0 = time.monotonic()

        technology = request.technology
        request_id = request.request_id or ""

        start_year = 2010
        end_year = 2024
        if request.time_range and request.time_range.start_year:
            start_year = request.time_range.start_year
        if request.time_range and request.time_range.end_year:
            end_year = request.time_range.end_year

        top_n = request.top_n or 10

        logger.info(
            "analyse_gestartet",
            technology=technology,
            start_year=start_year,
            end_year=end_year,
            request_id=request_id,
        )

        # --- Validierung ---
        if not technology or not technology.strip():
            if context is not None and grpc is not None:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "Feld 'technology' darf nicht leer sein",
                )
            return self._build_empty_response(request_id, t0)

        # --- Semantic Scholar Abfrage ---
        warnings: list[dict[str, str]] = []
        data_sources: list[dict[str, Any]] = []
        papers: list[dict[str, Any]] = []

        try:
            papers = await self._semantic_scholar.search_papers(
                technology, year_start=start_year, year_end=end_year,
            )
            if papers:
                # CRIT-1: Scope-Label aus shared.domain anhaengen, damit das
                # Frontend (Panel + Detail) "Top-Autor-Publikationen" statt
                # generisch "Publikationen" rendern kann.
                from src.infrastructure.repository import UC7_PUBLICATION_LABEL
                data_sources.append({
                    "name": (
                        f"Semantic Scholar Academic Graph API — "
                        f"{UC7_PUBLICATION_LABEL}"
                    ),
                    "type": "PUBLICATION",
                    "record_count": len(papers),
                })
        except Exception as exc:
            logger.warning("semantic_scholar_fehlgeschlagen", fehler=str(exc))
            warnings.append({
                "message": f"Semantic Scholar Abfrage fehlgeschlagen: {exc}",
                "severity": "HIGH",
                "code": "SEMANTIC_SCHOLAR_FAILED",
            })

        # --- CORDIS Institutionen (Supplement) ---
        top_institutions: list[dict[str, Any]] = []
        try:
            top_institutions = await self._repo.get_top_institutions(
                technology, limit=15,
            )
            if top_institutions:
                data_sources.append({
                    "name": "CORDIS EU Research Projects",
                    "type": "PUBLICATION",
                    "record_count": len(top_institutions),
                })
                logger.info(
                    "cordis_institutionen_geladen",
                    technology=technology,
                    anzahl=len(top_institutions),
                )
        except Exception as exc:
            logger.warning("cordis_institutionen_fehlgeschlagen", fehler=str(exc))
            warnings.append({
                "message": f"CORDIS-Institutionsabfrage fehlgeschlagen: {exc}",
                "severity": "LOW",
                "code": "CORDIS_INSTITUTIONS_FAILED",
            })

        if not papers:
            processing_time_ms = int((time.monotonic() - t0) * 1000)
            return self._build_response(
                h_index=0, avg_citations=0.0, median_citations=0.0,
                total_citations=0, total_publications=0,
                citation_trend=[], top_papers=[], top_venues=[],
                publication_types=[], open_access_share=0.0, i10_index=0,
                top_institutions=top_institutions,
                data_sources=data_sources, warnings=warnings,
                request_id=request_id, processing_time_ms=processing_time_ms,
            )

        # --- Metriken berechnen ---
        citations = [p.get("citationCount", 0) or 0 for p in papers]
        h_index = _compute_h_index(citations)
        i10_index = compute_i10_index(citations)
        total_citations = sum(citations)
        total_publications = len(papers)
        avg_citations = total_citations / total_publications if total_publications > 0 else 0.0

        sorted_citations = sorted(citations)
        mid = len(sorted_citations) // 2
        if len(sorted_citations) % 2 == 0 and len(sorted_citations) >= 2:
            median_citations = (sorted_citations[mid - 1] + sorted_citations[mid]) / 2.0
        elif sorted_citations:
            median_citations = float(sorted_citations[mid])
        else:
            median_citations = 0.0

        citation_trend = _compute_citation_trend(papers)
        top_papers = _compute_top_papers(papers, top_n)
        top_venues = _compute_venue_distribution(papers, 8)
        publication_types = _compute_publication_types(papers)

        open_access_count = sum(1 for p in papers if p.get("isOpenAccess"))
        open_access_share = open_access_count / total_publications if total_publications > 0 else 0.0

        if total_publications >= self._settings.semantic_scholar_max_results:
            warnings.append({
                "message": (
                    f"h-Index basiert auf Top-{total_publications} relevantesten Papers "
                    "— Approximation, kein vollstaendiger Korpus (Banks 2006)"
                ),
                "severity": "LOW",
                "code": "SAMPLE_SIZE_LIMIT",
            })

        processing_time_ms = int((time.monotonic() - t0) * 1000)

        logger.info(
            "analyse_abgeschlossen",
            technology=technology,
            papers=total_publications,
            h_index=h_index,
            total_citations=total_citations,
            dauer_ms=processing_time_ms,
        )

        return self._build_response(
            h_index=h_index, avg_citations=avg_citations,
            median_citations=median_citations, total_citations=total_citations,
            total_publications=total_publications,
            citation_trend=citation_trend, top_papers=top_papers,
            top_venues=top_venues, publication_types=publication_types,
            open_access_share=open_access_share, i10_index=i10_index,
            top_institutions=top_institutions,
            data_sources=data_sources, warnings=warnings,
            request_id=request_id, processing_time_ms=processing_time_ms,
        )

    # -----------------------------------------------------------------------
    # Response Builder
    # -----------------------------------------------------------------------

    def _build_response(
        self,
        *,
        h_index: int,
        avg_citations: float,
        median_citations: float,
        total_citations: int,
        total_publications: int,
        citation_trend: list[dict[str, Any]],
        top_papers: list[dict[str, Any]],
        top_venues: list[dict[str, Any]],
        publication_types: list[dict[str, Any]],
        open_access_share: float,
        i10_index: int,
        top_institutions: list[dict[str, Any]] | None = None,
        data_sources: list[dict[str, Any]] | None = None,
        warnings: list[dict[str, str]] | None = None,
        request_id: str = "",
        processing_time_ms: int = 0,
    ) -> Any:
        """ResearchImpactResponse zusammenbauen."""
        if top_institutions is None:
            top_institutions = []
        if data_sources is None:
            data_sources = []
        if warnings is None:
            warnings = []

        if uc7_research_impact_pb2 is None or common_pb2 is None:
            return self._build_dict_response(
                h_index=h_index, avg_citations=avg_citations,
                median_citations=median_citations, total_citations=total_citations,
                total_publications=total_publications,
                citation_trend=citation_trend, top_papers=top_papers,
                top_venues=top_venues, publication_types=publication_types,
                open_access_share=open_access_share, i10_index=i10_index,
                top_institutions=top_institutions,
                data_sources=data_sources, warnings=warnings,
                request_id=request_id, processing_time_ms=processing_time_ms,
            )

        # --- Protobuf ---
        pb_trend = [
            uc7_research_impact_pb2.CitationTrendEntry(
                year=int(e.get("year", 0)),
                total_citations=int(e.get("total_citations", e.get("citations", 0))),
                publication_count=int(e.get("publication_count", e.get("paper_count", 0))),
                avg_citations=float(e.get("avg_citations", 0.0)),
            )
            for e in citation_trend
        ]

        pb_papers = [
            uc7_research_impact_pb2.TopPaper(
                title=str(p.get("title", "")),
                authors=str(p.get("authors", p.get("authors_short", ""))),
                year=int(p.get("year", 0)),
                venue=str(p.get("venue", "")),
                citation_count=int(p.get("citation_count", p.get("citations", 0))),
                doi=str(p.get("doi", "")),
                is_open_access=bool(p.get("is_open_access", False)),
            )
            for p in top_papers
        ]

        pb_venues = [
            uc7_research_impact_pb2.TopVenue(
                name=str(v.get("name", v.get("venue", ""))),
                publication_count=int(v.get("publication_count", v.get("count", 0))),
                avg_citations=float(v.get("avg_citations", 0.0)),
                share=float(v.get("share", 0.0)),
            )
            for v in top_venues
        ]

        pb_types = [
            uc7_research_impact_pb2.PublicationType(
                type=str(t.get("type", "")),
                count=int(t.get("count", 0)),
                share=float(t.get("share", 0.0)),
            )
            for t in publication_types
        ]

        pb_institutions = [
            uc7_research_impact_pb2.TopInstitution(
                name=str(inst.get("name", "")),
                project_count=int(inst.get("project_count", 0)),
                country=str(inst.get("country", "")),
                activity_type=str(inst.get("activity_type", "")),
            )
            for inst in top_institutions
        ]

        _severity_map = {"LOW": common_pb2.LOW, "MEDIUM": common_pb2.MEDIUM, "HIGH": common_pb2.HIGH}
        _source_type_map = {"PUBLICATION": common_pb2.PUBLICATION}

        metadata = common_pb2.ResponseMetadata(
            processing_time_ms=processing_time_ms,
            data_sources=[
                common_pb2.DataSource(
                    name=ds["name"],
                    type=_source_type_map.get(ds.get("type", ""), common_pb2.DATA_SOURCE_TYPE_UNSPECIFIED),
                    record_count=ds.get("record_count", 0),
                )
                for ds in data_sources
            ],
            warnings=[
                common_pb2.Warning(
                    message=w["message"],
                    severity=_severity_map.get(w.get("severity", "LOW"), common_pb2.LOW),
                    code=w.get("code", ""),
                )
                for w in warnings
            ],
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        return uc7_research_impact_pb2.ResearchImpactResponse(
            h_index=h_index,
            avg_citations=avg_citations,
            median_citations=median_citations,
            total_citations=total_citations,
            total_publications=total_publications,
            citation_trend=pb_trend,
            top_papers=pb_papers,
            top_venues=pb_venues,
            publication_types=pb_types,
            open_access_share=open_access_share,
            i10_index=i10_index,
            metadata=metadata,
            top_institutions=pb_institutions,
        )

    def _build_dict_response(
        self,
        *,
        h_index: int,
        avg_citations: float,
        median_citations: float,
        total_citations: int,
        total_publications: int,
        citation_trend: list[dict[str, Any]],
        top_papers: list[dict[str, Any]],
        top_venues: list[dict[str, Any]],
        publication_types: list[dict[str, Any]],
        open_access_share: float,
        i10_index: int,
        top_institutions: list[dict[str, Any]] | None = None,
        data_sources: list[dict[str, Any]] | None = None,
        warnings: list[dict[str, str]] | None = None,
        request_id: str = "",
        processing_time_ms: int = 0,
    ) -> dict[str, Any]:
        """Fallback-Response als dict.

        Bug MAJ-7/MAJ-8: ``data_complete_year`` aus dem shared-Helper
        macht den Cutoff explizit, damit das Frontend bei Citation-Trend-
        Daten bis 2026 den Hinweis "Daten ggf. unvollstaendig" rendert.
        """
        return {
            "h_index": h_index,
            "avg_citations": avg_citations,
            "median_citations": median_citations,
            "total_citations": total_citations,
            "total_publications": total_publications,
            "citation_trend": citation_trend,
            "top_papers": top_papers,
            "top_venues": top_venues,
            "publication_types": publication_types,
            "open_access_share": open_access_share,
            "i10_index": i10_index,
            "top_institutions": top_institutions or [],
            "data_complete_year": last_complete_year(),
            "metadata": {
                "processing_time_ms": processing_time_ms,
                "data_sources": data_sources or [],
                "warnings": warnings or [],
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

    def _build_empty_response(self, request_id: str, t0: float) -> Any:
        """Leere Response bei ungueltigem Request."""
        processing_time_ms = int((time.monotonic() - t0) * 1000)
        return self._build_response(
            h_index=0, avg_citations=0.0, median_citations=0.0,
            total_citations=0, total_publications=0,
            citation_trend=[], top_papers=[], top_venues=[],
            publication_types=[], open_access_share=0.0, i10_index=0,
            top_institutions=[],
            data_sources=[], warnings=[], request_id=request_id,
            processing_time_ms=processing_time_ms,
        )
