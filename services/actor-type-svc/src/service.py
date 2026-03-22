"""UC11 ActorTypeServicer — gRPC-Implementierung der Actor-Type-Analyse.

Neu in v2 — keine v1.0-Referenz. Analysiert die Verteilung von
Organisationstypen (HES, PRC, REC, OTH, PUB) aus CORDIS-Projektpartnern.
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
    from shared.generated.python import uc11_actor_type_pb2
    from shared.generated.python import uc11_actor_type_pb2_grpc
except ImportError:
    common_pb2 = None  # type: ignore[assignment]
    uc11_actor_type_pb2 = None  # type: ignore[assignment]
    uc11_actor_type_pb2_grpc = None  # type: ignore[assignment]

from src.config import Settings
from src.domain.metrics import compute_sme_share, compute_type_breakdown
from src.infrastructure.repository import ActorTypeRepository

logger = structlog.get_logger(__name__)


def _get_base_class() -> type:
    if uc11_actor_type_pb2_grpc is not None:
        return uc11_actor_type_pb2_grpc.ActorTypeServiceServicer  # type: ignore[return-value]
    return object


class ActorTypeServicer(_get_base_class()):  # type: ignore[misc]
    """gRPC-Servicer fuer UC11 Actor Type Distribution."""

    def __init__(self, pool: asyncpg.Pool, settings: Settings | None = None) -> None:
        self._pool = pool
        self._settings = settings or Settings()
        self._repo = ActorTypeRepository(pool)

    async def AnalyzeActorTypes(self, request: Any, context: Any) -> Any:
        """UC11: Akteur-Typ-Verteilung analysieren."""
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

        logger.info("analyse_gestartet", technology=technology, request_id=request_id)

        if not technology or not technology.strip():
            if context is not None and grpc is not None:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Feld 'technology' darf nicht leer sein")
            return self._build_empty_response(request_id, t0)

        warnings: list[dict[str, str]] = []
        data_sources: list[dict[str, Any]] = []

        tasks = [
            asyncio.create_task(self._repo.type_breakdown(technology, start_year=start_year, end_year=end_year), name="breakdown"),
            asyncio.create_task(self._repo.type_trend(technology, start_year=start_year, end_year=end_year), name="trend"),
            asyncio.create_task(self._repo.top_actors_by_type(technology, start_year=start_year, end_year=end_year, limit=top_n), name="top_actors"),
            asyncio.create_task(self._repo.sme_count(technology), name="sme"),
        ]

        breakdown_raw: list[dict[str, Any]] = []
        trend_raw: list[dict[str, Any]] = []
        top_actors: list[dict[str, Any]] = []
        sme_data: dict[str, int] = {"sme_count": 0, "total_prc": 0}

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for task, result in zip(tasks, results, strict=False):
            name = task.get_name()
            if isinstance(result, Exception):
                logger.warning("query_fehlgeschlagen", task=name, fehler=str(result))
                warnings.append({"message": f"Query '{name}' fehlgeschlagen: {result}", "severity": "MEDIUM", "code": f"QUERY_FAILED_{name.upper()}"})
                continue
            if name == "breakdown":
                breakdown_raw = cast(list[dict[str, Any]], result)
            elif name == "trend":
                trend_raw = cast(list[dict[str, Any]], result)
            elif name == "top_actors":
                top_actors = cast(list[dict[str, Any]], result)
            elif name == "sme":
                sme_data = cast(dict[str, int], result)

        type_breakdown = compute_type_breakdown(breakdown_raw)
        sme_share = compute_sme_share(sme_data["sme_count"], sme_data["total_prc"])

        # Trend zu Year-Entries aggregieren
        year_entries: list[dict[str, Any]] = []
        trend_by_year: dict[int, dict[str, int]] = {}
        for row in trend_raw:
            year = int(row["year"])
            atype = str(row["activity_type"])
            if year not in trend_by_year:
                trend_by_year[year] = {}
            trend_by_year[year][atype] = int(row["count"])
        for year in sorted(trend_by_year.keys()):
            entry = {"year": year}
            total = 0
            for t in ("HES", "PRC", "REC", "OTH", "PUB"):
                entry[f"{t.lower()}_count"] = trend_by_year[year].get(t, 0)
                total += trend_by_year[year].get(t, 0)
            entry["total"] = total
            year_entries.append(entry)

        total_classified = sum(int(b.get("actor_count", 0)) for b in type_breakdown)

        if breakdown_raw:
            data_sources.append({"name": "CORDIS (PostgreSQL)", "type": "PROJECT", "record_count": total_classified})

        processing_time_ms = int((time.monotonic() - t0) * 1000)
        logger.info("analyse_abgeschlossen", technology=technology, typen=len(type_breakdown), dauer_ms=processing_time_ms)

        return self._build_response(
            type_breakdown=type_breakdown, type_trend=year_entries,
            top_actors=top_actors, total_classified=total_classified,
            sme_share=sme_share, data_sources=data_sources, warnings=warnings,
            request_id=request_id, processing_time_ms=processing_time_ms,
        )

    def _build_response(self, **kwargs: Any) -> Any:
        if uc11_actor_type_pb2 is None or common_pb2 is None:
            return {
                "type_breakdown": kwargs["type_breakdown"],
                "type_trend": kwargs["type_trend"],
                "top_actors_by_type": kwargs["top_actors"],
                "total_classified_actors": kwargs["total_classified"],
                "sme_share": kwargs["sme_share"],
                "metadata": {
                    "processing_time_ms": kwargs["processing_time_ms"],
                    "data_sources": kwargs["data_sources"],
                    "warnings": kwargs["warnings"],
                    "request_id": kwargs["request_id"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }

        _type_map = {"HES": 1, "PRC": 2, "REC": 3, "OTH": 4, "PUB": 5}
        _severity_map = {"LOW": common_pb2.LOW, "MEDIUM": common_pb2.MEDIUM, "HIGH": common_pb2.HIGH}

        pb_breakdown = [
            uc11_actor_type_pb2.ActorTypeBreakdown(
                type=_type_map.get(b["type"], 0), label=str(b["label"]),
                actor_count=int(b["actor_count"]), project_count=int(b["project_count"]),
                funding_eur=float(b.get("funding_eur", 0.0)),
                actor_share=float(b.get("actor_share", 0.0)),
                activity_share=float(b.get("activity_share", 0.0)),
            )
            for b in kwargs["type_breakdown"]
        ]

        pb_trend = [
            uc11_actor_type_pb2.ActorTypeYearEntry(
                year=int(e["year"]),
                hes_count=int(e.get("hes_count", 0)), prc_count=int(e.get("prc_count", 0)),
                rec_count=int(e.get("rec_count", 0)), oth_count=int(e.get("oth_count", 0)),
                pub_count=int(e.get("pub_count", 0)), total=int(e.get("total", 0)),
            )
            for e in kwargs["type_trend"]
        ]

        pb_actors = [
            uc11_actor_type_pb2.TypedActor(
                name=str(a["name"]), type=_type_map.get(str(a.get("type", "")), 0),
                country_code=str(a.get("country_code", "")),
                project_count=int(a.get("project_count", 0)),
                is_sme=bool(a.get("is_sme", False)),
            )
            for a in kwargs["top_actors"]
        ]

        metadata = common_pb2.ResponseMetadata(
            processing_time_ms=kwargs["processing_time_ms"],
            data_sources=[common_pb2.DataSource(name=ds["name"], type=common_pb2.PROJECT, record_count=ds.get("record_count", 0)) for ds in kwargs["data_sources"]],
            warnings=[common_pb2.Warning(message=w["message"], severity=_severity_map.get(w.get("severity", "LOW"), common_pb2.LOW), code=w.get("code", "")) for w in kwargs["warnings"]],
            request_id=kwargs["request_id"], timestamp=datetime.now(timezone.utc).isoformat(),
        )

        return uc11_actor_type_pb2.ActorTypeResponse(
            type_breakdown=pb_breakdown, type_trend=pb_trend,
            top_actors_by_type=pb_actors,
            total_classified_actors=kwargs["total_classified"],
            sme_share=kwargs["sme_share"], metadata=metadata,
        )

    def _build_empty_response(self, request_id: str, t0: float) -> Any:
        processing_time_ms = int((time.monotonic() - t0) * 1000)
        return self._build_response(
            type_breakdown=[], type_trend=[], top_actors=[],
            total_classified=0, sme_share=0.0, data_sources=[], warnings=[],
            request_id=request_id, processing_time_ms=processing_time_ms,
        )
