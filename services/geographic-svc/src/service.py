"""UC6 GeographicServicer — gRPC-Implementierung der Geographic-Analyse.

Empfaengt AnalysisRequest, fuehrt parallele Abfragen gegen PostgreSQL
durch und baut die GeographicResponse mit Laenderverteilung,
Stadtverteilung, Kooperationspaaren und Cross-Border-Anteil.

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

# --- gRPC-Imports (try/except, da Stubs noch nicht generiert) ---
try:
    import grpc
    from grpc import aio as grpc_aio
except ImportError:
    grpc = None  # type: ignore[assignment]
    grpc_aio = None  # type: ignore[assignment]

try:
    from shared.generated.python import common_pb2
    from shared.generated.python import uc6_geographic_pb2
    from shared.generated.python import uc6_geographic_pb2_grpc
except ImportError:
    common_pb2 = None  # type: ignore[assignment]
    uc6_geographic_pb2 = None  # type: ignore[assignment]
    uc6_geographic_pb2_grpc = None  # type: ignore[assignment]

# --- Shared Domain ---
try:
    from shared.domain.eu_countries import EU_EEA_COUNTRIES, is_european
    from shared.domain.metrics import merge_country_data
except ImportError:
    from src.domain.metrics import EU_EEA_COUNTRIES, is_european, merge_country_data

from src.config import Settings
from src.infrastructure.repository import GeographicRepository

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Helper: Basis-Klasse ermitteln (gRPC Servicer oder object)
# ---------------------------------------------------------------------------
def _get_base_class() -> type:
    """Gibt die gRPC-Servicer-Basisklasse zurueck, oder object als Fallback."""
    if uc6_geographic_pb2_grpc is not None:
        return uc6_geographic_pb2_grpc.GeographicServiceServicer  # type: ignore[return-value]
    return object


class GeographicServicer(_get_base_class()):  # type: ignore[misc]
    """gRPC-Servicer fuer UC6 Geographic Analysis.

    Koordiniert parallele Abfragen:
    1. Patent-Laenderverteilung (PostgreSQL)
    2. CORDIS-Laenderverteilung (PostgreSQL)
    3. Stadt-Verteilung (PostgreSQL)
    4. Kooperationspaare (PostgreSQL)
    5. Cross-Border-Anteil (PostgreSQL)
    """

    def __init__(self, pool: asyncpg.Pool, settings: Settings | None = None) -> None:
        self._pool = pool
        self._settings = settings or Settings()
        self._repo = GeographicRepository(pool)

    async def AnalyzeGeographic(
        self,
        request: Any,
        context: Any,
    ) -> Any:
        """UC6: Geografische Verteilung analysieren.

        Args:
            request: tip.common.AnalysisRequest Protobuf-Message
            context: gRPC ServicerContext

        Returns:
            tip.uc6.GeographicResponse Protobuf-Message
        """
        t0 = time.monotonic()

        # --- Request-Parameter extrahieren ---
        technology = request.technology
        request_id = request.request_id or ""
        european_only = request.european_only

        start_year = 2010
        end_year = 2024
        if request.time_range and request.time_range.start_year:
            start_year = request.time_range.start_year
        if request.time_range and request.time_range.end_year:
            end_year = request.time_range.end_year

        top_n = request.top_n or 20

        logger.info(
            "analyse_gestartet",
            technology=technology,
            start_year=start_year,
            end_year=end_year,
            european_only=european_only,
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

        # --- Parallele Datenabfragen ---
        warnings: list[dict[str, str]] = []
        data_sources: list[dict[str, Any]] = []

        patent_countries: list[Any] = []
        cordis_countries: list[Any] = []
        city_data: list[dict[str, Any]] = []
        collab_pairs: list[dict[str, Any]] = []
        cross_border: dict[str, int | float] = {}

        tasks: list[asyncio.Task[Any]] = []

        tasks.append(asyncio.create_task(
            self._repo.patent_country_distribution(
                technology, start_year=start_year, end_year=end_year,
                european_only=european_only, limit=top_n,
            ),
            name="patent_countries",
        ))

        tasks.append(asyncio.create_task(
            self._repo.cordis_country_distribution(
                technology, start_year=start_year, end_year=end_year,
                european_only=european_only, limit=top_n,
            ),
            name="cordis_countries",
        ))

        tasks.append(asyncio.create_task(
            self._repo.city_distribution(
                technology, start_year=start_year, end_year=end_year,
                european_only=european_only, limit=top_n,
            ),
            name="city_distribution",
        ))

        tasks.append(asyncio.create_task(
            self._repo.cooperation_pairs(
                technology, start_year=start_year, end_year=end_year,
                european_only=european_only, limit=top_n,
            ),
            name="cooperation_pairs",
        ))

        tasks.append(asyncio.create_task(
            self._repo.cross_border_share(
                technology, start_year=start_year, end_year=end_year,
                min_countries=2,
            ),
            name="cross_border",
        ))

        # --- Alle Tasks ausfuehren ---
        if tasks:
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

                if name == "patent_countries":
                    patent_countries = list(result)
                elif name == "cordis_countries":
                    cordis_countries = list(result)
                elif name == "city_distribution":
                    city_data = cast(list[dict[str, Any]], result)
                elif name == "cooperation_pairs":
                    collab_pairs = cast(list[dict[str, Any]], result)
                elif name == "cross_border":
                    cross_border = cast(dict[str, int | float], result)

        # --- Laender zusammenfuehren ---
        country_dist = merge_country_data(patent_countries, cordis_countries, limit=top_n)

        # --- Datenquellen ---
        if patent_countries:
            data_sources.append({
                "name": "EPO DOCDB (PostgreSQL)",
                "type": "PATENT",
                "record_count": sum(int(c.count) for c in patent_countries),
            })
        if cordis_countries:
            data_sources.append({
                "name": "CORDIS (PostgreSQL)",
                "type": "PROJECT",
                "record_count": sum(int(c.count) for c in cordis_countries),
            })

        total_countries = len(country_dist)
        total_cities = len(city_data)
        cross_share = float(cross_border.get("cross_border_share", 0.0))

        processing_time_ms = int((time.monotonic() - t0) * 1000)

        logger.info(
            "analyse_abgeschlossen",
            technology=technology,
            laender=total_countries,
            staedte=total_cities,
            kooperationspaare=len(collab_pairs),
            cross_border_anteil=cross_share,
            dauer_ms=processing_time_ms,
        )

        return self._build_response(
            country_dist=country_dist,
            city_data=city_data,
            collab_pairs=collab_pairs,
            cross_border_share=cross_share,
            total_countries=total_countries,
            total_cities=total_cities,
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
        country_dist: list[dict[str, str | int]],
        city_data: list[dict[str, Any]],
        collab_pairs: list[dict[str, Any]],
        cross_border_share: float,
        total_countries: int,
        total_cities: int,
        data_sources: list[dict[str, Any]],
        warnings: list[dict[str, str]],
        request_id: str,
        processing_time_ms: int,
    ) -> Any:
        """GeographicResponse zusammenbauen."""
        if uc6_geographic_pb2 is None or common_pb2 is None:
            return self._build_dict_response(
                country_dist=country_dist,
                city_data=city_data,
                collab_pairs=collab_pairs,
                cross_border_share=cross_border_share,
                total_countries=total_countries,
                total_cities=total_cities,
                data_sources=data_sources,
                warnings=warnings,
                request_id=request_id,
                processing_time_ms=processing_time_ms,
            )

        # --- Protobuf-Messages bauen ---
        total_activity = sum(int(c.get("total", 0)) for c in country_dist) or 1

        pb_countries = [
            uc6_geographic_pb2.CountryDistribution(
                country_code=str(c["country"]),
                patent_count=int(c.get("patents", 0)),
                project_count=int(c.get("projects", 0)),
                activity_score=float(int(c.get("total", 0))),
                share=int(c.get("total", 0)) / total_activity,
            )
            for c in country_dist
        ]

        pb_cities = [
            uc6_geographic_pb2.CityDistribution(
                city=str(c.get("city", "")),
                country_code=str(c.get("country_code", "")),
                actor_count=int(c.get("actor_count", 0)),
                project_count=int(c.get("project_count", 0)),
            )
            for c in city_data
        ]

        pb_pairs = [
            uc6_geographic_pb2.CooperationPair(
                country_a=str(p["country_a"]),
                country_b=str(p["country_b"]),
                co_project_count=int(p.get("co_project_count", 0)),
            )
            for p in collab_pairs
        ]

        _severity_map = {"LOW": common_pb2.LOW, "MEDIUM": common_pb2.MEDIUM, "HIGH": common_pb2.HIGH}
        _source_type_map = {
            "PATENT": common_pb2.PATENT,
            "PROJECT": common_pb2.PROJECT,
        }

        pb_warnings = [
            common_pb2.Warning(
                message=w["message"],
                severity=_severity_map.get(w.get("severity", "LOW"), common_pb2.LOW),
                code=w.get("code", ""),
            )
            for w in warnings
        ]

        pb_sources = [
            common_pb2.DataSource(
                name=ds["name"],
                type=_source_type_map.get(ds.get("type", ""), common_pb2.DATA_SOURCE_TYPE_UNSPECIFIED),
                record_count=ds.get("record_count", 0),
            )
            for ds in data_sources
        ]

        metadata = common_pb2.ResponseMetadata(
            processing_time_ms=processing_time_ms,
            data_sources=pb_sources,
            warnings=pb_warnings,
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        return uc6_geographic_pb2.GeographicResponse(
            country_distribution=pb_countries,
            city_distribution=pb_cities,
            cooperation_pairs=pb_pairs,
            cross_border_share=cross_border_share,
            total_countries=total_countries,
            total_cities=total_cities,
            metadata=metadata,
        )

    def _build_dict_response(
        self,
        *,
        country_dist: list[dict[str, str | int]],
        city_data: list[dict[str, Any]],
        collab_pairs: list[dict[str, Any]],
        cross_border_share: float,
        total_countries: int,
        total_cities: int,
        data_sources: list[dict[str, Any]],
        warnings: list[dict[str, str]],
        request_id: str,
        processing_time_ms: int,
    ) -> dict[str, Any]:
        """Fallback-Response als dict (wenn gRPC-Stubs nicht generiert)."""
        return {
            "country_distribution": country_dist,
            "city_distribution": city_data,
            "cooperation_pairs": collab_pairs,
            "cross_border_share": cross_border_share,
            "total_countries": total_countries,
            "total_cities": total_cities,
            "metadata": {
                "processing_time_ms": processing_time_ms,
                "data_sources": data_sources,
                "warnings": warnings,
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

    def _build_empty_response(self, request_id: str, t0: float) -> Any:
        """Leere Response bei ungueltigem Request."""
        processing_time_ms = int((time.monotonic() - t0) * 1000)
        return self._build_response(
            country_dist=[],
            city_data=[],
            collab_pairs=[],
            cross_border_share=0.0,
            total_countries=0,
            total_cities=0,
            data_sources=[],
            warnings=[],
            request_id=request_id,
            processing_time_ms=processing_time_ms,
        )
