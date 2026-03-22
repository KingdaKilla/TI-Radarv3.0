"""UC8 TemporalServicer — gRPC-Implementierung der Temporal-Analyse.

Empfaengt AnalysisRequest, fuehrt parallele Abfragen gegen PostgreSQL
durch und berechnet Akteur-Persistenz, Programmevolution und Technologiebreite.

Migration von MVP v1.0:
- SQLite FTS5 MATCH -> PostgreSQL tsvector @@ plainto_tsquery
- aiosqlite -> asyncpg Connection Pool
- FastAPI Response -> gRPC Protobuf Messages
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
    from grpc import aio as grpc_aio
except ImportError:
    grpc = None  # type: ignore[assignment]
    grpc_aio = None  # type: ignore[assignment]

try:
    from shared.generated.python import common_pb2
    from shared.generated.python import uc8_temporal_pb2
    from shared.generated.python import uc8_temporal_pb2_grpc
except ImportError:
    common_pb2 = None  # type: ignore[assignment]
    uc8_temporal_pb2 = None  # type: ignore[assignment]
    uc8_temporal_pb2_grpc = None  # type: ignore[assignment]

# --- Shared Domain Metriken ---
try:
    from shared.domain.temporal_metrics import (
        _compute_actor_dynamics,
        _compute_actor_timeline,
        _compute_programme_evolution,
        _compute_technology_breadth,
    )
except ImportError:
    _compute_actor_dynamics = None  # type: ignore[assignment]
    _compute_actor_timeline = None  # type: ignore[assignment]
    _compute_programme_evolution = None  # type: ignore[assignment]
    _compute_technology_breadth = None  # type: ignore[assignment]

from src.config import Settings
from src.domain.metrics import (
    compute_actor_dynamics,
    compute_actor_timeline,
    compute_dynamics_summary,
    compute_programme_evolution,
    compute_technology_breadth,
)
from src.infrastructure.repository import TemporalRepository

logger = structlog.get_logger(__name__)


def _get_base_class() -> type:
    """Gibt die gRPC-Servicer-Basisklasse zurueck, oder object als Fallback."""
    if uc8_temporal_pb2_grpc is not None:
        return uc8_temporal_pb2_grpc.TemporalServiceServicer  # type: ignore[return-value]
    return object


class TemporalServicer(_get_base_class()):  # type: ignore[misc]
    """gRPC-Servicer fuer UC8 Temporal Dynamics.

    Koordiniert parallele Abfragen:
    1. Patent-Akteure pro Jahr (PostgreSQL)
    2. CORDIS-Akteure pro Jahr (PostgreSQL)
    3. CPC-Codes pro Jahr (PostgreSQL)
    4. Instrument/Programm-Daten (PostgreSQL)
    """

    def __init__(self, pool: asyncpg.Pool, settings: Settings | None = None) -> None:
        self._pool = pool
        self._settings = settings or Settings()
        self._repo = TemporalRepository(pool)

    async def AnalyzeTemporal(
        self,
        request: Any,
        context: Any,
    ) -> Any:
        """UC8: Temporale Dynamik analysieren.

        Args:
            request: tip.common.AnalysisRequest Protobuf-Message
            context: gRPC ServicerContext

        Returns:
            tip.uc8.TemporalResponse Protobuf-Message
        """
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

        logger.info(
            "analyse_gestartet",
            technology=technology,
            start_year=start_year,
            end_year=end_year,
            european_only=european_only,
            request_id=request_id,
        )

        if not technology or not technology.strip():
            if context is not None and grpc is not None:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "Feld 'technology' darf nicht leer sein",
                )
            return self._build_empty_response(request_id, t0)

        # --- Parallele Datenabfragen ---
        warnings: list[dict[str, str]] = []
        data_sources: list[dict[str, Any]] = []

        tasks: list[asyncio.Task[Any]] = []

        tasks.append(asyncio.create_task(
            self._repo.patent_actors_by_year(
                technology, start_year=start_year, end_year=end_year,
                european_only=european_only,
            ),
            name="patent_actors",
        ))

        tasks.append(asyncio.create_task(
            self._repo.cordis_actors_by_year(
                technology, start_year=start_year, end_year=end_year,
                european_only=european_only,
            ),
            name="cordis_actors",
        ))

        tasks.append(asyncio.create_task(
            self._repo.cpc_codes_by_year(
                technology, start_year=start_year, end_year=end_year,
                european_only=european_only,
            ),
            name="cpc_codes",
        ))

        tasks.append(asyncio.create_task(
            self._repo.funding_by_instrument(
                technology, start_year=start_year, end_year=end_year,
            ),
            name="funding_instruments",
        ))

        # --- Ergebnisse sammeln ---
        patent_actors_raw: list[dict[str, Any]] = []
        cordis_actors_raw: list[dict[str, Any]] = []
        cpc_codes_raw: list[dict[str, Any]] = []
        instrument_data: list[dict[str, Any]] = []

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

            if name == "patent_actors":
                patent_actors_raw = cast(list[dict[str, Any]], result)
            elif name == "cordis_actors":
                cordis_actors_raw = cast(list[dict[str, Any]], result)
            elif name == "cpc_codes":
                cpc_codes_raw = cast(list[dict[str, Any]], result)
            elif name == "funding_instruments":
                instrument_data = cast(list[dict[str, Any]], result)

        # --- Akteure zusammenfuehren ---
        actors_by_year: dict[int, dict[str, int]] = {}
        for row in patent_actors_raw:
            year = int(row["year"])
            name = str(row["name"]).upper().strip()
            if year not in actors_by_year:
                actors_by_year[year] = {}
            actors_by_year[year][name] = actors_by_year[year].get(name, 0) + int(row["count"])

        for row in cordis_actors_raw:
            year = int(row["year"])
            name = str(row["name"]).upper().strip()
            if year not in actors_by_year:
                actors_by_year[year] = {}
            actors_by_year[year][name] = actors_by_year[year].get(name, 0) + int(row["count"])

        # --- CPC-Codes pro Jahr ---
        cpc_by_year: dict[int, list[str]] = {}
        for row in cpc_codes_raw:
            year = int(row["year"])
            if year not in cpc_by_year:
                cpc_by_year[year] = []
            cpc_by_year[year].append(str(row["cpc_codes"]))

        # --- Metriken berechnen ---
        entrant_persistence = compute_actor_dynamics(actors_by_year)
        tech_breadth = compute_technology_breadth(cpc_by_year)
        actor_timeline = compute_actor_timeline(actors_by_year, top_n=10)
        programme_evo = compute_programme_evolution(instrument_data)
        dynamics_summary = compute_dynamics_summary(actors_by_year)

        # --- Datenquellen ---
        if patent_actors_raw:
            data_sources.append({
                "name": "EPO DOCDB (PostgreSQL)",
                "type": "PATENT",
                "record_count": len(patent_actors_raw),
            })
        if cordis_actors_raw:
            data_sources.append({
                "name": "CORDIS (PostgreSQL)",
                "type": "PROJECT",
                "record_count": len(cordis_actors_raw),
            })

        processing_time_ms = int((time.monotonic() - t0) * 1000)

        logger.info(
            "analyse_abgeschlossen",
            technology=technology,
            akteure_gesamt=dynamics_summary["total_actors"],
            persistente=dynamics_summary["persistent_count"],
            dauer_ms=processing_time_ms,
        )

        return self._build_response(
            entrant_persistence=entrant_persistence,
            actor_timeline=actor_timeline,
            programme_evo=programme_evo,
            tech_breadth=tech_breadth,
            dynamics_summary=dynamics_summary,
            data_sources=data_sources,
            warnings=warnings,
            request_id=request_id,
            processing_time_ms=processing_time_ms,
        )

    # -----------------------------------------------------------------------
    # Response Builder
    # -----------------------------------------------------------------------

    def _build_response(
        self,
        *,
        entrant_persistence: list[dict[str, Any]],
        actor_timeline: list[dict[str, Any]],
        programme_evo: list[dict[str, Any]],
        tech_breadth: list[dict[str, Any]],
        dynamics_summary: dict[str, Any],
        data_sources: list[dict[str, Any]],
        warnings: list[dict[str, str]],
        request_id: str,
        processing_time_ms: int,
    ) -> Any:
        """TemporalResponse zusammenbauen."""
        if uc8_temporal_pb2 is None or common_pb2 is None:
            return self._build_dict_response(
                entrant_persistence=entrant_persistence,
                actor_timeline=actor_timeline,
                programme_evo=programme_evo,
                tech_breadth=tech_breadth,
                dynamics_summary=dynamics_summary,
                data_sources=data_sources,
                warnings=warnings,
                request_id=request_id,
                processing_time_ms=processing_time_ms,
            )

        pb_trend = [
            uc8_temporal_pb2.EntrantPersistenceTrend(
                year=int(e["year"]),
                new_entrants=int(e.get("new_entrants", 0)),
                persistent_actors=int(e.get("persistent_actors", 0)),
                exited_actors=int(e.get("exited_actors", 0)),
                total_active=int(e.get("total_active", 0)),
                churn_rate=float(e.get("churn_rate", 0.0)),
                persistence_ratio=float(e.get("persistence_ratio", 0.0)),
            )
            for e in entrant_persistence
        ]

        pb_timeline = [
            uc8_temporal_pb2.ActorTimeline(
                actor_name=str(a.get("actor_name", "")),
                persistence_type=_map_persistence_type(a.get("persistence_type", "")),
                first_active_year=int(a.get("first_active_year", 0)),
                last_active_year=int(a.get("last_active_year", 0)),
                active_years_count=int(a.get("active_years_count", 0)),
            )
            for a in actor_timeline
        ]

        pb_programmes = [
            uc8_temporal_pb2.ProgrammeEvolution(
                year=int(p.get("year", 0)),
                programme=str(p.get("programme", "")),
                project_count=int(p.get("project_count", 0)),
                funding_eur=float(p.get("funding_eur", 0.0)),
            )
            for p in programme_evo
        ]

        pb_breadth = [
            uc8_temporal_pb2.TechnologyBreadthEntry(
                year=int(b["year"]),
                unique_cpc_codes=int(b.get("unique_cpc_codes", 0)),
                shannon_index=float(b.get("shannon_index", 0.0)),
                herfindahl_index=float(b.get("herfindahl_index", 0.0)),
                new_codes=int(b.get("new_codes", 0)),
            )
            for b in tech_breadth
        ]

        pb_summary = uc8_temporal_pb2.ActorDynamicsSummary(
            total_actors=int(dynamics_summary.get("total_actors", 0)),
            persistent_count=int(dynamics_summary.get("persistent_count", 0)),
            one_timer_count=int(dynamics_summary.get("one_timer_count", 0)),
            avg_lifespan_years=float(dynamics_summary.get("avg_lifespan_years", 0.0)),
            median_lifespan_years=float(dynamics_summary.get("median_lifespan_years", 0.0)),
        )

        _severity_map = {"LOW": common_pb2.LOW, "MEDIUM": common_pb2.MEDIUM, "HIGH": common_pb2.HIGH}
        _source_type_map = {"PATENT": common_pb2.PATENT, "PROJECT": common_pb2.PROJECT}

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

        return uc8_temporal_pb2.TemporalResponse(
            entrant_persistence_trend=pb_trend,
            actor_timeline=pb_timeline,
            programme_evolution=pb_programmes,
            technology_breadth=pb_breadth,
            dynamics_summary=pb_summary,
            metadata=metadata,
        )

    def _build_dict_response(self, **kwargs: Any) -> dict[str, Any]:
        """Fallback-Response als dict."""
        return {
            "entrant_persistence_trend": kwargs["entrant_persistence"],
            "actor_timeline": kwargs["actor_timeline"],
            "programme_evolution": kwargs["programme_evo"],
            "technology_breadth": kwargs["tech_breadth"],
            "dynamics_summary": kwargs["dynamics_summary"],
            "metadata": {
                "processing_time_ms": kwargs["processing_time_ms"],
                "data_sources": kwargs["data_sources"],
                "warnings": kwargs["warnings"],
                "request_id": kwargs["request_id"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

    def _build_empty_response(self, request_id: str, t0: float) -> Any:
        """Leere Response bei ungueltigem Request."""
        processing_time_ms = int((time.monotonic() - t0) * 1000)
        return self._build_response(
            entrant_persistence=[], actor_timeline=[], programme_evo=[],
            tech_breadth=[], dynamics_summary={"total_actors": 0, "persistent_count": 0,
            "one_timer_count": 0, "avg_lifespan_years": 0.0, "median_lifespan_years": 0.0},
            data_sources=[], warnings=[], request_id=request_id,
            processing_time_ms=processing_time_ms,
        )


def _map_persistence_type(ptype: str) -> int:
    """Persistence-Typ-String auf Protobuf-Enum-Wert mappen."""
    if uc8_temporal_pb2 is None:
        return 0
    mapping = {
        "ONE_TIMER": 1,
        "OCCASIONAL": 2,
        "PERSISTENT": 3,
        "NEW_ENTRANT": 4,
        "EXITED": 5,
    }
    return mapping.get(ptype, 0)
