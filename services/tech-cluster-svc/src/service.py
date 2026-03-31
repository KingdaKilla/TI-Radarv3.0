"""UC9 TechClusterServicer — gRPC-Implementierung der Cluster-Analyse.

Empfaengt AnalysisRequest, baut Akteur-CPC-Co-Occurrence-Matrix,
fuehrt Clustering durch und berechnet Dimension-Scores.
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
    from shared.generated.python import uc9_tech_cluster_pb2
    from shared.generated.python import uc9_tech_cluster_pb2_grpc
except ImportError:
    common_pb2 = None  # type: ignore[assignment]
    uc9_tech_cluster_pb2 = None  # type: ignore[assignment]
    uc9_tech_cluster_pb2_grpc = None  # type: ignore[assignment]

from shared.domain.eu_countries import EU_EEA_COUNTRIES, is_european
from shared.domain.metrics import cagr
from src.config import Settings
from src.domain.metrics import compute_cluster_coherence
from src.infrastructure.repository import TechClusterRepository

logger = structlog.get_logger(__name__)


def _get_base_class() -> type:
    if uc9_tech_cluster_pb2_grpc is not None:
        return uc9_tech_cluster_pb2_grpc.TechClusterServiceServicer  # type: ignore[return-value]
    return object


class TechClusterServicer(_get_base_class()):  # type: ignore[misc]
    """gRPC-Servicer fuer UC9 Technology Cluster.

    Koordiniert:
    1. Akteur-CPC-Matrix (PostgreSQL)
    2. CPC-Co-Occurrence (PostgreSQL)
    3. Cluster-Zuweisung (Community Detection)
    4. Dimension-Score-Berechnung
    """

    def __init__(self, pool: asyncpg.Pool, settings: Settings | None = None) -> None:
        self._pool = pool
        self._settings = settings or Settings()
        self._repo = TechClusterRepository(pool)

    async def AnalyzeTechCluster(
        self,
        request: Any,
        context: Any,
    ) -> Any:
        """UC9: Technologie-Cluster analysieren."""
        t0 = time.monotonic()

        technology = request.technology
        request_id = request.request_id or ""
        european_only = request.european_only

        start_year = 2010
        end_year = 2024
        if request.time_range and request.time_range.start_year:
            start_year = request.time_range.start_year
        if request.time_range and request.time_range.end_year:
            end_year = request.time_range.end_year

        logger.info("analyse_gestartet", technology=technology, request_id=request_id)

        if not technology or not technology.strip():
            if context is not None and grpc is not None:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Feld 'technology' darf nicht leer sein")
            return self._build_empty_response(request_id, t0)

        warnings: list[dict[str, str]] = []
        data_sources: list[dict[str, Any]] = []

        # --- Parallele Abfragen ---
        tasks = [
            asyncio.create_task(
                self._repo.actor_cpc_matrix(technology, start_year=start_year, end_year=end_year, european_only=european_only),
                name="actor_cpc",
            ),
            asyncio.create_task(
                self._repo.cpc_co_occurrence(technology, start_year=start_year, end_year=end_year),
                name="cpc_co_occurrence",
            ),
            asyncio.create_task(
                self._repo.patent_counts_by_cpc_year(technology, start_year=start_year, end_year=end_year),
                name="cpc_year_counts",
            ),
        ]

        actor_cpc_data: list[dict[str, Any]] = []
        co_occurrence_data: list[dict[str, Any]] = []
        cpc_year_data: list[dict[str, Any]] = []

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for task, result in zip(tasks, results, strict=False):
            name = task.get_name()
            if isinstance(result, Exception):
                logger.warning("query_fehlgeschlagen", task=name, fehler=str(result))
                warnings.append({"message": f"Query '{name}' fehlgeschlagen: {result}", "severity": "MEDIUM", "code": f"QUERY_FAILED_{name.upper()}"})
                continue
            if name == "actor_cpc":
                actor_cpc_data = cast(list[dict[str, Any]], result)
            elif name == "cpc_co_occurrence":
                co_occurrence_data = cast(list[dict[str, Any]], result)
            elif name == "cpc_year_counts":
                cpc_year_data = cast(list[dict[str, Any]], result)

        # --- Co-Occurrence-Lookup fuer Coherence-Berechnung ---
        cpc_co_map: dict[tuple[str, str], int] = {}
        for entry in co_occurrence_data:
            a, b = str(entry["cpc_a"]), str(entry["cpc_b"])
            key = (min(a, b), max(a, b))
            cpc_co_map[key] = int(entry["co_count"])

        # --- Patent-Counts pro CPC-Section und Jahr fuer CAGR ---
        section_year_counts: dict[str, dict[int, int]] = {}
        for entry in cpc_year_data:
            cpc = str(entry["cpc_code"])
            section = cpc[:1] if cpc else "X"
            year = int(entry["year"])
            count = int(entry["count"])
            if section not in section_year_counts:
                section_year_counts[section] = {}
            section_year_counts[section][year] = section_year_counts[section].get(year, 0) + count

        # --- Einfaches Clustering via CPC-Gruppierung ---
        cpc_groups: dict[str, list[str]] = {}
        for entry in actor_cpc_data:
            cpc = str(entry["cpc_code"])
            section = cpc[:1] if cpc else "X"
            if section not in cpc_groups:
                cpc_groups[section] = []
            if cpc not in cpc_groups[section]:
                cpc_groups[section].append(cpc)

        clusters: list[dict[str, Any]] = []
        for idx, (section, cpcs) in enumerate(sorted(cpc_groups.items())):
            actors_in_cluster = {str(e["actor"]) for e in actor_cpc_data if str(e["cpc_code"])[:1] == section}
            patents_in_cluster = sum(int(e["count"]) for e in actor_cpc_data if str(e["cpc_code"])[:1] == section)

            # Coherence: average Jaccard via co-occurrence density
            coherence_val = compute_cluster_coherence(cpc_co_map, cpcs)

            # Density: edges / possible_edges (same as coherence for co-occurrence)
            density_val = coherence_val

            # CAGR per cluster from yearly patent counts
            cagr_val = 0.0
            yearly = section_year_counts.get(section, {})
            if yearly:
                sorted_years = sorted(y for y in yearly.keys() if y <= 2024)
                if len(sorted_years) >= 2:
                    first_val = float(yearly[sorted_years[0]])
                    last_val = float(yearly[sorted_years[-1]])
                    n_periods = sorted_years[-1] - sorted_years[0]
                    # cagr() returns percentage (e.g. 12.5 for 12.5%);
                    # frontend expects fraction (0.125), so divide by 100
                    cagr_val = cagr(first_val, last_val, n_periods) / 100.0

            clusters.append({
                "cluster_id": idx,
                "label": f"CPC Section {section}",
                "cpc_codes": cpcs[:10],
                "actor_count": len(actors_in_cluster),
                "patent_count": patents_in_cluster,
                "density": round(density_val, 4),
                "coherence": round(coherence_val, 4),
                "cagr": round(cagr_val, 4),
            })

        total_actors = len({str(e["actor"]) for e in actor_cpc_data})
        total_cpc = len({str(e["cpc_code"]) for e in actor_cpc_data})

        if actor_cpc_data:
            data_sources.append({"name": "EPO DOCDB (PostgreSQL)", "type": "PATENT", "record_count": len(actor_cpc_data)})

        processing_time_ms = int((time.monotonic() - t0) * 1000)
        logger.info("analyse_abgeschlossen", technology=technology, clusters=len(clusters), dauer_ms=processing_time_ms)

        return self._build_response(
            clusters=clusters, actor_cpc_links=actor_cpc_data[:100],
            total_actors=total_actors, total_cpc_codes=total_cpc,
            data_sources=data_sources, warnings=warnings,
            request_id=request_id, processing_time_ms=processing_time_ms,
        )

    def _build_response(self, *, clusters: list[dict[str, Any]], actor_cpc_links: list[dict[str, Any]],
                         total_actors: int, total_cpc_codes: int, data_sources: list[dict[str, Any]],
                         warnings: list[dict[str, str]], request_id: str, processing_time_ms: int) -> Any:
        if uc9_tech_cluster_pb2 is None or common_pb2 is None:
            return {
                "clusters": clusters, "actor_cpc_links": actor_cpc_links,
                "total_actors": total_actors, "total_cpc_codes": total_cpc_codes,
                "metadata": {"processing_time_ms": processing_time_ms, "data_sources": data_sources,
                             "warnings": warnings, "request_id": request_id,
                             "timestamp": datetime.now(timezone.utc).isoformat()},
            }

        pb_clusters = [
            uc9_tech_cluster_pb2.TechnologyCluster(
                cluster_id=c["cluster_id"], label=c["label"],
                cpc_codes=c["cpc_codes"], actor_count=c["actor_count"],
                patent_count=c["patent_count"], density=c.get("density", 0.0),
                coherence=c.get("coherence", 0.0), cagr=c.get("cagr", 0.0),
            )
            for c in clusters
        ]
        pb_links = [
            uc9_tech_cluster_pb2.ActorCpcLink(
                actor=str(l["actor"]), cpc_code=str(l["cpc_code"]), count=int(l["count"]),
            )
            for l in actor_cpc_links
        ]

        _severity_map = {"LOW": common_pb2.LOW, "MEDIUM": common_pb2.MEDIUM, "HIGH": common_pb2.HIGH}
        metadata = common_pb2.ResponseMetadata(
            processing_time_ms=processing_time_ms,
            data_sources=[common_pb2.DataSource(name=ds["name"], type=common_pb2.PATENT, record_count=ds.get("record_count", 0)) for ds in data_sources],
            warnings=[common_pb2.Warning(message=w["message"], severity=_severity_map.get(w.get("severity", "LOW"), common_pb2.LOW), code=w.get("code", "")) for w in warnings],
            request_id=request_id, timestamp=datetime.now(timezone.utc).isoformat(),
        )

        return uc9_tech_cluster_pb2.TechClusterResponse(
            clusters=pb_clusters, actor_cpc_links=pb_links,
            total_actors=total_actors, total_cpc_codes=total_cpc_codes, metadata=metadata,
        )

    def _build_empty_response(self, request_id: str, t0: float) -> Any:
        processing_time_ms = int((time.monotonic() - t0) * 1000)
        return self._build_response(
            clusters=[], actor_cpc_links=[], total_actors=0, total_cpc_codes=0,
            data_sources=[], warnings=[], request_id=request_id, processing_time_ms=processing_time_ms,
        )
