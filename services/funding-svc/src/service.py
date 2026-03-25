"""UC4 FundingServicer — gRPC-Implementierung der EU-Foerderungs-Analyse.

Empfaengt AnalysisRequest, fuehrt parallele Abfragen gegen CORDIS-Daten
in PostgreSQL durch, berechnet CAGR und baut FundingResponse mit
Programmverteilung, Instrumenten-Aufschluesselung und Zeitreihen.

Migration von MVP v1.0:
- SQLite FTS5 MATCH -> PostgreSQL tsvector @@ plainto_tsquery
- aiosqlite -> asyncpg Connection Pool
- FastAPI Response -> gRPC Protobuf Messages
"""

from __future__ import annotations

import asyncio
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
    from shared.generated.python import uc4_funding_pb2
    from shared.generated.python import uc4_funding_pb2_grpc
except ImportError:
    common_pb2 = None  # type: ignore[assignment]
    uc4_funding_pb2 = None  # type: ignore[assignment]
    uc4_funding_pb2_grpc = None  # type: ignore[assignment]

# --- Shared Domain Metriken ---
from shared.domain.metrics import cagr

from src.config import Settings
from src.infrastructure.repository import FundingRepository

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Helper: Basis-Klasse ermitteln (gRPC Servicer oder object)
# ---------------------------------------------------------------------------
def _get_base_class() -> type:
    """Gibt die gRPC-Servicer-Basisklasse zurueck, oder object als Fallback."""
    if uc4_funding_pb2_grpc is not None:
        return uc4_funding_pb2_grpc.FundingServiceServicer  # type: ignore[return-value]
    return object


class FundingServicer(_get_base_class()):  # type: ignore[misc]
    """gRPC-Servicer fuer UC4 Funding Radar.

    Koordiniert parallele Abfragen gegen CORDIS-Daten:
    1. Foerderung pro Jahr (Zeitreihe)
    2. Foerderung pro Programm (FP7, H2020, Horizon Europe)
    3. Foerderung pro Instrument (RIA, IA, CSA)
    4. Top-Organisationen
    5. Laenderverteilung

    Berechnet CAGR und Durchschnittswerte.
    """

    def __init__(self, pool: asyncpg.Pool, settings: Settings | None = None) -> None:
        self._pool = pool
        self._settings = settings or Settings()
        self._repo = FundingRepository(pool)

    async def AnalyzeFunding(
        self,
        request: Any,
        context: Any,
    ) -> Any:
        """UC4: EU-Foerderung analysieren.

        Args:
            request: tip.common.AnalysisRequest Protobuf-Message
            context: gRPC ServicerContext

        Returns:
            tip.uc4.FundingResponse Protobuf-Message
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

        top_n = request.top_n or 20

        logger.info(
            "funding_analyse_gestartet",
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

        # --- Parallele Datenabfragen ---
        warnings: list[dict[str, str]] = []
        data_sources: list[dict[str, Any]] = []

        funding_years: list[dict[str, Any]] = []
        programme_data: list[dict[str, Any]] = []
        instrument_data: list[dict[str, Any]] = []
        top_orgs: list[dict[str, Any]] = []
        country_data: list[dict[str, Any]] = []

        tasks = [
            asyncio.create_task(
                self._repo.funding_by_year(
                    technology, start_year=start_year, end_year=end_year,
                ),
                name="funding_years",
            ),
            asyncio.create_task(
                self._repo.funding_by_programme(
                    technology, start_year=start_year, end_year=end_year,
                ),
                name="programme",
            ),
            asyncio.create_task(
                self._repo.funding_by_instrument(
                    technology, start_year=start_year, end_year=end_year,
                ),
                name="instrument",
            ),
            asyncio.create_task(
                self._repo.top_funded_organizations(
                    technology, start_year=start_year, end_year=end_year,
                    limit=top_n,
                ),
                name="top_orgs",
            ),
            asyncio.create_task(
                self._repo.funding_by_country(
                    technology, start_year=start_year, end_year=end_year,
                    limit=top_n,
                ),
                name="country",
            ),
        ]

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

            if name == "funding_years":
                funding_years = result
            elif name == "programme":
                programme_data = result
            elif name == "instrument":
                instrument_data = result
            elif name == "top_orgs":
                top_orgs = result
            elif name == "country":
                country_data = result

        if funding_years:
            data_sources.append({
                "name": "CORDIS (PostgreSQL)",
                "type": "FUNDING",
                "record_count": sum(int(f.count) for f in funding_years),
            })

        # --- Aggregationen berechnen ---
        total_funding = sum(float(f.funding) for f in funding_years)
        total_projects = sum(int(f.count) for f in funding_years)
        avg_size = total_funding / total_projects if total_projects > 0 else 0.0

        # Durchschnittliche Projektdauer (Monate) — muss extra abgefragt werden
        avg_duration = 0.0
        try:
            avg_duration = await self._repo.avg_project_duration(
                technology, start_year=start_year, end_year=end_year,
            )
        except Exception as e:
            logger.warning("avg_duration_fehlgeschlagen", fehler=str(e))

        # --- CAGR berechnen ---
        funding_cagr = 0.0
        non_zero = [
            f for f in funding_years
            if float(f.funding) > 0
        ]
        if len(non_zero) >= 2:
            first = float(non_zero[0].funding)
            last = float(non_zero[-1].funding)
            first_year = int(non_zero[0].year)
            last_year = int(non_zero[-1].year)
            year_span = last_year - first_year
            if year_span > 0:
                funding_cagr = cagr(first, last, year_span)

        # --- Verarbeitungszeit ---
        processing_time_ms = int((time.monotonic() - t0) * 1000)

        logger.info(
            "funding_analyse_abgeschlossen",
            technology=technology,
            total_funding=round(total_funding, 2),
            total_projects=total_projects,
            cagr=round(funding_cagr, 2),
            dauer_ms=processing_time_ms,
        )

        return self._build_response(
            total_funding=total_funding,
            total_projects=total_projects,
            funding_cagr=funding_cagr,
            funding_years=funding_years,
            programme_data=programme_data,
            instrument_data=instrument_data,
            top_orgs=top_orgs,
            country_data=country_data,
            avg_duration=avg_duration,
            avg_size=avg_size,
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
        total_funding: float,
        total_projects: int,
        funding_cagr: float,
        funding_years: list[dict[str, Any]],
        programme_data: list[dict[str, Any]],
        instrument_data: list[dict[str, Any]],
        top_orgs: list[dict[str, Any]],
        country_data: list[dict[str, Any]],
        avg_duration: float,
        avg_size: float,
        data_sources: list[dict[str, Any]],
        warnings: list[dict[str, str]],
        request_id: str,
        processing_time_ms: int,
    ) -> Any:
        """FundingResponse aus berechneten Daten zusammenbauen."""
        if uc4_funding_pb2 is None or common_pb2 is None:
            return self._build_dict_response(
                total_funding=total_funding, total_projects=total_projects,
                funding_cagr=funding_cagr, funding_years=funding_years,
                programme_data=programme_data, instrument_data=instrument_data,
                top_orgs=top_orgs, country_data=country_data,
                avg_duration=avg_duration, avg_size=avg_size,
                data_sources=data_sources, warnings=warnings,
                request_id=request_id, processing_time_ms=processing_time_ms,
            )

        # --- Protobuf-Messages bauen ---

        # Programme Breakdown
        pb_programmes = []
        for p in programme_data:
            funding = float(p.get("funding", 0) or 0)
            count = int(p.get("count", 0) or 0)
            share = funding / total_funding if total_funding > 0 else 0.0
            avg_proj = funding / count if count > 0 else 0.0
            pb_programmes.append(uc4_funding_pb2.ProgrammeBreakdown(
                programme=str(p.get("programme", "UNKNOWN")),
                funding_eur=funding,
                project_count=count,
                share=share,
                avg_project_size=avg_proj,
            ))

        # Instrument Breakdown
        pb_instruments = []
        for inst in instrument_data:
            funding = float(inst.get("funding", 0) or 0)
            count = int(inst.get("count", 0) or 0)
            share = funding / total_funding if total_funding > 0 else 0.0
            pb_instruments.append(uc4_funding_pb2.InstrumentBreakdown(
                instrument=str(inst.get("funding_scheme", "UNKNOWN")),
                instrument_name="",
                funding_eur=funding,
                project_count=count,
                share=share,
            ))

        # Time Series
        pb_time_series = []
        for f in funding_years:
            funding = float(f.funding)
            count = int(f.count)
            avg_proj = funding / count if count > 0 else 0.0
            pb_time_series.append(uc4_funding_pb2.FundingTimeSeriesEntry(
                year=int(f.year),
                funding_eur=funding,
                project_count=count,
                avg_project_size=avg_proj,
                participant_count=0,
            ))

        # Top Organisations
        pb_orgs = [
            uc4_funding_pb2.FundedOrganisation(
                name=str(o["name"]),
                country_code=str(o.get("country", "")),
                funding_eur=float(o.get("funding", 0) or 0),
                project_count=int(o.get("count", 0) or 0),
                organisation_type=str(o.get("type", "")),
            )
            for o in top_orgs
        ]

        # Country Distribution
        total_country_funding = sum(float(c.get("funding", 0) or 0) for c in country_data) or 1.0
        pb_countries = [
            uc4_funding_pb2.CountryFunding(
                country_code=str(c["country"]),
                country_name="",
                funding_eur=float(c.get("funding", 0) or 0),
                participation_count=int(c.get("count", 0) or 0),
                share=float(c.get("funding", 0) or 0) / total_country_funding,
            )
            for c in country_data
        ]

        # Metadata
        _severity_map = {
            "LOW": common_pb2.LOW,
            "MEDIUM": common_pb2.MEDIUM,
            "HIGH": common_pb2.HIGH,
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
                type=common_pb2.FUNDING,
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

        return uc4_funding_pb2.FundingResponse(
            total_funding_eur=total_funding,
            project_count=total_projects,
            cagr=funding_cagr / 100.0,  # Protobuf: Fraction
            programme_breakdown=pb_programmes,
            instrument_breakdown=pb_instruments,
            time_series=pb_time_series,
            top_organisations=pb_orgs,
            country_distribution=pb_countries,
            avg_duration_months=avg_duration,
            avg_funding_per_project=avg_size,
            metadata=metadata,
        )

    def _build_dict_response(
        self,
        *,
        total_funding: float,
        total_projects: int,
        funding_cagr: float,
        funding_years: list[dict[str, Any]],
        programme_data: list[dict[str, Any]],
        instrument_data: list[dict[str, Any]],
        top_orgs: list[dict[str, Any]],
        country_data: list[dict[str, Any]],
        avg_duration: float,
        avg_size: float,
        data_sources: list[dict[str, Any]],
        warnings: list[dict[str, str]],
        request_id: str,
        processing_time_ms: int,
    ) -> dict[str, Any]:
        """Fallback-Response als dict (wenn gRPC-Stubs nicht generiert)."""
        return {
            "total_funding_eur": round(total_funding, 2),
            "project_count": total_projects,
            "cagr": funding_cagr / 100.0,
            "programme_breakdown": programme_data,
            "instrument_breakdown": instrument_data,
            "time_series": [
                {"year": f.year, "funding": f.funding, "count": f.count}
                for f in funding_years
            ],
            "top_organisations": top_orgs,
            "country_distribution": country_data,
            "avg_duration_months": avg_duration,
            "avg_funding_per_project": round(avg_size, 2),
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
            total_funding=0.0, total_projects=0, funding_cagr=0.0,
            funding_years=[], programme_data=[], instrument_data=[],
            top_orgs=[], country_data=[], avg_duration=0.0, avg_size=0.0,
            data_sources=[], warnings=[], request_id=request_id,
            processing_time_ms=processing_time_ms,
        )
