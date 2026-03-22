"""UC12 PatentGrantServicer — gRPC-Implementierung der Patent-Grant-Rate-Analyse.

Neu in v2 — keine v1.0-Referenz. Analysiert die Erteilungsrate von
Patentanmeldungen basierend auf EPO Kind-Codes (A1/A2 vs B1/B2).
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
    from shared.generated.python import uc12_patent_grant_pb2
    from shared.generated.python import uc12_patent_grant_pb2_grpc
except ImportError:
    common_pb2 = None  # type: ignore[assignment]
    uc12_patent_grant_pb2 = None  # type: ignore[assignment]
    uc12_patent_grant_pb2_grpc = None  # type: ignore[assignment]

from src.config import Settings
from src.domain.metrics import KIND_CODE_DESCRIPTIONS, compute_grant_rate, compute_grant_rate_summary
from src.infrastructure.repository import PatentGrantRepository

logger = structlog.get_logger(__name__)


def _get_base_class() -> type:
    if uc12_patent_grant_pb2_grpc is not None:
        return uc12_patent_grant_pb2_grpc.PatentGrantServiceServicer  # type: ignore[return-value]
    return object


class PatentGrantServicer(_get_base_class()):  # type: ignore[misc]
    """gRPC-Servicer fuer UC12 Patent Grant Rate Analysis.

    Koordiniert:
    1. Kind-Code-Verteilung (PostgreSQL)
    2. Grant-Rate pro Jahr (PostgreSQL)
    3. Grant-Rate pro Land (PostgreSQL)
    4. Grant-Rate pro CPC-Code (PostgreSQL)
    """

    def __init__(self, pool: asyncpg.Pool, settings: Settings | None = None) -> None:
        self._pool = pool
        self._settings = settings or Settings()
        self._repo = PatentGrantRepository(pool)

    async def AnalyzePatentGrant(self, request: Any, context: Any) -> Any:
        """UC12: Patent-Erteilungsrate analysieren."""
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

        tasks = [
            asyncio.create_task(self._repo.kind_code_distribution(technology, start_year=start_year, end_year=end_year), name="kind_codes"),
            asyncio.create_task(self._repo.grant_rate_by_year(technology, start_year=start_year, end_year=end_year), name="year_trend"),
            asyncio.create_task(self._repo.grant_rate_by_country(technology, start_year=start_year, end_year=end_year, european_only=european_only), name="country_rates"),
            asyncio.create_task(self._repo.grant_rate_by_cpc(technology, start_year=start_year, end_year=end_year), name="cpc_rates"),
            asyncio.create_task(self._repo.avg_time_to_grant(technology, start_year=start_year, end_year=end_year), name="time_to_grant"),
        ]

        kind_codes: list[dict[str, Any]] = []
        year_trend: list[dict[str, Any]] = []
        country_rates: list[dict[str, Any]] = []
        cpc_rates: list[dict[str, Any]] = []
        time_to_grant: dict[str, float] = {"avg_months": 0.0, "median_months": 0.0}

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for task, result in zip(tasks, results, strict=False):
            name = task.get_name()
            if isinstance(result, Exception):
                logger.warning("query_fehlgeschlagen", task=name, fehler=str(result))
                warnings.append({"message": f"Query '{name}' fehlgeschlagen: {result}", "severity": "MEDIUM", "code": f"QUERY_FAILED_{name.upper()}"})
                continue
            if name == "kind_codes":
                kind_codes = cast(list[dict[str, Any]], result)
            elif name == "year_trend":
                year_trend = cast(list[dict[str, Any]], result)
            elif name == "country_rates":
                country_rates = cast(list[dict[str, Any]], result)
            elif name == "cpc_rates":
                cpc_rates = cast(list[dict[str, Any]], result)
            elif name == "time_to_grant":
                time_to_grant = cast(dict[str, float], result)

        # --- Summary berechnen ---
        total_applications = sum(int(y.get("application_count", 0)) for y in year_trend)
        total_grants = sum(int(y.get("grant_count", 0)) for y in year_trend)
        summary = compute_grant_rate_summary(
            total_applications,
            total_grants,
            avg_time_to_grant_months=time_to_grant.get("avg_months", 0.0),
            median_time_to_grant_months=time_to_grant.get("median_months", 0.0),
        )

        # Kind-Code Beschreibungen hinzufuegen
        for kc in kind_codes:
            kc["description"] = KIND_CODE_DESCRIPTIONS.get(str(kc["kind_code"]), "")

        if kind_codes:
            total_patents = sum(int(kc["count"]) for kc in kind_codes)
            data_sources.append({"name": "EPO DOCDB (PostgreSQL)", "type": "PATENT", "record_count": total_patents})

        processing_time_ms = int((time.monotonic() - t0) * 1000)
        logger.info(
            "analyse_abgeschlossen", technology=technology,
            applications=total_applications, grants=total_grants,
            grant_rate=summary["grant_rate"], dauer_ms=processing_time_ms,
        )

        return self._build_response(
            summary=summary, year_trend=year_trend, kind_codes=kind_codes,
            country_rates=country_rates, cpc_rates=cpc_rates,
            data_sources=data_sources, warnings=warnings,
            request_id=request_id, processing_time_ms=processing_time_ms,
        )

    def _build_response(self, **kwargs: Any) -> Any:
        if uc12_patent_grant_pb2 is None or common_pb2 is None:
            return {
                "summary": kwargs["summary"],
                "year_trend": kwargs["year_trend"],
                "kind_code_distribution": kwargs["kind_codes"],
                "country_grant_rates": kwargs["country_rates"],
                "cpc_grant_rates": kwargs["cpc_rates"],
                "metadata": {
                    "processing_time_ms": kwargs["processing_time_ms"],
                    "data_sources": kwargs["data_sources"],
                    "warnings": kwargs["warnings"],
                    "request_id": kwargs["request_id"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }

        pb_summary = uc12_patent_grant_pb2.GrantRateSummary(
            total_applications=kwargs["summary"]["total_applications"],
            total_grants=kwargs["summary"]["total_grants"],
            grant_rate=kwargs["summary"]["grant_rate"],
            avg_time_to_grant_months=kwargs["summary"]["avg_time_to_grant_months"],
            median_time_to_grant_months=kwargs["summary"]["median_time_to_grant_months"],
        )

        pb_years = [
            uc12_patent_grant_pb2.GrantRateYearEntry(
                year=int(y["year"]), application_count=int(y.get("application_count", 0)),
                grant_count=int(y.get("grant_count", 0)),
                grant_rate=float(y.get("grant_rate", 0.0)),
            )
            for y in kwargs["year_trend"]
        ]

        pb_kinds = [
            uc12_patent_grant_pb2.KindCodeDistribution(
                kind_code=str(k["kind_code"]),
                description=str(k.get("description", "")),
                count=int(k["count"]),
                share=float(k.get("share", 0.0)),
            )
            for k in kwargs["kind_codes"]
        ]

        pb_countries = [
            uc12_patent_grant_pb2.CountryGrantRate(
                country_code=str(c["country_code"]),
                application_count=int(c.get("application_count", 0)),
                grant_count=int(c.get("grant_count", 0)),
                grant_rate=float(c.get("grant_rate", 0.0)),
            )
            for c in kwargs["country_rates"]
        ]

        pb_cpc = [
            uc12_patent_grant_pb2.CpcGrantRate(
                cpc_code=str(c["cpc_code"]),
                description=str(c.get("description", "")),
                application_count=int(c.get("application_count", 0)),
                grant_count=int(c.get("grant_count", 0)),
                grant_rate=float(c.get("grant_rate", 0.0)),
            )
            for c in kwargs["cpc_rates"]
        ]

        _severity_map = {"LOW": common_pb2.LOW, "MEDIUM": common_pb2.MEDIUM, "HIGH": common_pb2.HIGH}
        metadata = common_pb2.ResponseMetadata(
            processing_time_ms=kwargs["processing_time_ms"],
            data_sources=[common_pb2.DataSource(name=ds["name"], type=common_pb2.PATENT, record_count=ds.get("record_count", 0)) for ds in kwargs["data_sources"]],
            warnings=[common_pb2.Warning(message=w["message"], severity=_severity_map.get(w.get("severity", "LOW"), common_pb2.LOW), code=w.get("code", "")) for w in kwargs["warnings"]],
            request_id=kwargs["request_id"], timestamp=datetime.now(timezone.utc).isoformat(),
        )

        return uc12_patent_grant_pb2.PatentGrantResponse(
            summary=pb_summary, year_trend=pb_years,
            kind_code_distribution=pb_kinds,
            country_grant_rates=pb_countries,
            cpc_grant_rates=pb_cpc, metadata=metadata,
        )

    def _build_empty_response(self, request_id: str, t0: float) -> Any:
        processing_time_ms = int((time.monotonic() - t0) * 1000)
        return self._build_response(
            summary={"total_applications": 0, "total_grants": 0, "grant_rate": 0.0,
                     "avg_time_to_grant_months": 0.0, "median_time_to_grant_months": 0.0},
            year_trend=[], kind_codes=[], country_rates=[], cpc_rates=[],
            data_sources=[], warnings=[], request_id=request_id,
            processing_time_ms=processing_time_ms,
        )
