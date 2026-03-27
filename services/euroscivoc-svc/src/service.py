"""UC10 EuroSciVocServicer — gRPC-Implementierung der EuroSciVoc-Analyse.

Neu in v2 — keine v1.0-Referenz. Analysiert die Zuordnung von
Technologien zu wissenschaftlichen Disziplinen via EuroSciVoc-Taxonomie
aus CORDIS-Projekten.
"""

from __future__ import annotations

import asyncio
import math
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
    from shared.generated.python import uc10_euroscivoc_pb2
    from shared.generated.python import uc10_euroscivoc_pb2_grpc
except ImportError:
    common_pb2 = None  # type: ignore[assignment]
    uc10_euroscivoc_pb2 = None  # type: ignore[assignment]
    uc10_euroscivoc_pb2_grpc = None  # type: ignore[assignment]

from src.config import Settings
from src.domain.metrics import (
    build_discipline_tree,
    classify_interdisciplinarity,
    compute_shannon_index,
    compute_simpson_index,
)
from src.infrastructure.repository import EuroSciVocRepository

logger = structlog.get_logger(__name__)


def _get_base_class() -> type:
    if uc10_euroscivoc_pb2_grpc is not None:
        return uc10_euroscivoc_pb2_grpc.EuroSciVocServiceServicer  # type: ignore[return-value]
    return object


class EuroSciVocServicer(_get_base_class()):  # type: ignore[misc]
    """gRPC-Servicer fuer UC10 EuroSciVoc Discipline Mapping.

    Koordiniert:
    1. Disziplin-Verteilung (PostgreSQL)
    2. Disziplin-Trend (PostgreSQL)
    3. Cross-Disciplinary-Links (PostgreSQL)
    4. Interdisziplinaritaets-Metriken (berechnet)
    """

    def __init__(self, pool: asyncpg.Pool, settings: Settings | None = None) -> None:
        self._pool = pool
        self._settings = settings or Settings()
        self._repo = EuroSciVocRepository(pool)

    async def AnalyzeEuroSciVoc(self, request: Any, context: Any) -> Any:
        """UC10: EuroSciVoc-Taxonomie analysieren."""
        t0 = time.monotonic()

        technology = request.technology
        request_id = request.request_id or ""
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
            asyncio.create_task(self._repo.discipline_distribution(technology, start_year=start_year, end_year=end_year), name="disciplines"),
            asyncio.create_task(self._repo.discipline_trend(technology, start_year=start_year, end_year=end_year), name="trend"),
            asyncio.create_task(self._repo.cross_disciplinary_links(technology, start_year=start_year, end_year=end_year), name="links"),
            asyncio.create_task(self._repo.total_mapped_projects(technology), name="total_mapped"),
        ]

        disciplines: list[dict[str, Any]] = []
        trend: list[dict[str, Any]] = []
        links: list[dict[str, Any]] = []
        total_mapped: int = 0

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for task, result in zip(tasks, results, strict=False):
            name = task.get_name()
            if isinstance(result, Exception):
                logger.warning("query_fehlgeschlagen", task=name, fehler=str(result))
                warnings.append({"message": f"Query '{name}' fehlgeschlagen: {result}", "severity": "MEDIUM", "code": f"QUERY_FAILED_{name.upper()}"})
                continue
            if name == "disciplines":
                disciplines = cast(list[dict[str, Any]], result)
            elif name == "trend":
                trend = cast(list[dict[str, Any]], result)
            elif name == "links":
                links = cast(list[dict[str, Any]], result)
            elif name == "total_mapped":
                total_mapped = int(result)

        # --- Metriken berechnen ---
        disc_counts = {str(d["label"]): int(d["project_count"]) for d in disciplines}
        shannon = compute_shannon_index(disc_counts)
        simpson = compute_simpson_index(disc_counts)

        # Felder zaehlen (Level = FIELD)
        fields = [d for d in disciplines if str(d.get("level", "")).upper() in ("FIELD", "1")]
        active_fields = len(fields)
        active_disciplines = len(disciplines)
        is_interdisciplinary = classify_interdisciplinarity(shannon, active_fields)

        # Baum bauen
        tree_roots = build_discipline_tree(disciplines)

        # --- CAGR pro Feld aus Trenddaten berechnen ---
        # Aggregiere Trenddaten: pro discipline_id -> {year: count}
        disc_year_counts: dict[str, dict[int, int]] = {}
        for t in trend:
            did = str(t.get("discipline_id", ""))
            if not did:
                continue
            yr = int(t["year"])
            cnt = int(t.get("publication_count", 0))
            if did not in disc_year_counts:
                disc_year_counts[did] = {}
            disc_year_counts[did][yr] = disc_year_counts[did].get(yr, 0) + cnt

        # Fuer FIELD-level: Aufsummiere alle Kinder-Disziplinen
        # Disziplinen mit parent_id == field_id gehoeren zum Feld
        field_ids = {str(f["id"]) for f in fields}
        field_year_counts: dict[str, dict[int, int]] = {fid: {} for fid in field_ids}

        for d in disciplines:
            did = str(d["id"])
            parent = str(d.get("parent_id", ""))
            # Direkte Treffer (Feld selbst)
            if did in field_ids and did in disc_year_counts:
                for yr, cnt in disc_year_counts[did].items():
                    field_year_counts[did][yr] = field_year_counts[did].get(yr, 0) + cnt
            # Kinder zuordnen (parent_id zeigt auf ein Feld)
            if parent in field_ids and did in disc_year_counts:
                for yr, cnt in disc_year_counts[did].items():
                    field_year_counts[parent][yr] = field_year_counts[parent].get(yr, 0) + cnt

        def _compute_field_cagr(yearly: dict[int, int]) -> float:
            """CAGR fuer ein Feld aus jaehrlichen Projektzahlen."""
            if len(yearly) < 2:
                return 0.0
            sorted_years = sorted(yearly.keys())
            # Nur vollstaendige Datenjahre (<=2024)
            sorted_years = [y for y in sorted_years if y <= 2024]
            if len(sorted_years) < 2:
                return 0.0
            first_val = float(yearly[sorted_years[0]])
            last_val = float(yearly[sorted_years[-1]])
            n_periods = sorted_years[-1] - sorted_years[0]
            if n_periods <= 0 or first_val <= 0 or last_val <= 0:
                return 0.0
            return (math.pow(last_val / first_val, 1.0 / n_periods) - 1.0)

        # CAGR pro Feld berechnen und an fields anhaengen
        for f in fields:
            fid = str(f["id"])
            yearly = field_year_counts.get(fid, {})
            f["cagr"] = _compute_field_cagr(yearly)

        if disciplines:
            data_sources.append({"name": "CORDIS EuroSciVoc (PostgreSQL)", "type": "PROJECT", "record_count": total_mapped})

        processing_time_ms = int((time.monotonic() - t0) * 1000)
        logger.info("analyse_abgeschlossen", technology=technology, disziplinen=active_disciplines, dauer_ms=processing_time_ms)

        return self._build_response(
            disciplines=disciplines, tree_roots=tree_roots, fields=fields,
            links=links, trend=trend, shannon=shannon, simpson=simpson,
            active_disciplines=active_disciplines, active_fields=active_fields,
            is_interdisciplinary=is_interdisciplinary, total_mapped=total_mapped,
            data_sources=data_sources, warnings=warnings, request_id=request_id,
            processing_time_ms=processing_time_ms,
        )

    def _build_response(self, **kwargs: Any) -> Any:
        if uc10_euroscivoc_pb2 is None or common_pb2 is None:
            # Fuer jedes FIELD-level Disziplin zaehle Unterdisziplinen
            field_ids = {str(f["id"]) for f in kwargs["fields"]}
            sub_field_counts: dict[str, int] = {fid: 0 for fid in field_ids}
            for d in kwargs["disciplines"]:
                parent = str(d.get("parent_id", ""))
                if parent in sub_field_counts:
                    sub_field_counts[parent] += 1

            fields_of_science = [
                {
                    "id": str(f["id"]),
                    "label": str(f.get("label", "")),
                    "total_publications": 0,
                    "total_projects": int(f.get("project_count", 0)),
                    "share": float(f.get("share", 0.0)),
                    "active_sub_fields": sub_field_counts.get(str(f["id"]), 0),
                    "cagr": float(f.get("cagr", 0.0)),
                }
                for f in kwargs["fields"]
            ]

            return {
                "disciplines": kwargs["disciplines"],
                "fields_of_science": fields_of_science,
                "disciplinary_links": kwargs["links"],
                "discipline_trend": kwargs["trend"],
                "interdisciplinarity": {
                    "shannon_index": kwargs["shannon"],
                    "simpson_index": kwargs["simpson"],
                    "active_disciplines": kwargs["active_disciplines"],
                    "active_fields": kwargs["active_fields"],
                    "is_interdisciplinary": kwargs["is_interdisciplinary"],
                },
                "total_mapped_publications": kwargs["total_mapped"],
                "metadata": {
                    "processing_time_ms": kwargs["processing_time_ms"],
                    "data_sources": kwargs["data_sources"],
                    "warnings": kwargs["warnings"],
                    "request_id": kwargs["request_id"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }

        _severity_map = {"LOW": common_pb2.LOW, "MEDIUM": common_pb2.MEDIUM, "HIGH": common_pb2.HIGH}
        metadata = common_pb2.ResponseMetadata(
            processing_time_ms=kwargs["processing_time_ms"],
            data_sources=[common_pb2.DataSource(name=ds["name"], type=common_pb2.PROJECT, record_count=ds.get("record_count", 0)) for ds in kwargs["data_sources"]],
            warnings=[common_pb2.Warning(message=w["message"], severity=_severity_map.get(w.get("severity", "LOW"), common_pb2.LOW), code=w.get("code", "")) for w in kwargs["warnings"]],
            request_id=kwargs["request_id"], timestamp=datetime.now(timezone.utc).isoformat(),
        )

        pb_disciplines = [
            uc10_euroscivoc_pb2.EuroSciVocNode(
                id=str(d["id"]), label=str(d.get("label", "")),
                parent_id=str(d.get("parent_id", "")),
                project_count=int(d.get("project_count", 0)),
                share=float(d.get("share", 0.0)),
            )
            for d in kwargs["disciplines"]
        ]

        pb_links = [
            uc10_euroscivoc_pb2.DisciplinaryLink(
                discipline_a_id=str(l["discipline_a_id"]),
                discipline_a_label=str(l["discipline_a_label"]),
                discipline_b_id=str(l["discipline_b_id"]),
                discipline_b_label=str(l["discipline_b_label"]),
                co_occurrence_count=int(l["co_occurrence_count"]),
            )
            for l in kwargs["links"]
        ]

        pb_trend = [
            uc10_euroscivoc_pb2.DisciplineYearEntry(
                year=int(t["year"]), discipline=str(t["discipline"]),
                discipline_id=str(t.get("discipline_id", "")),
                publication_count=int(t.get("publication_count", 0)),
            )
            for t in kwargs["trend"]
        ]

        pb_interdisciplinarity = uc10_euroscivoc_pb2.InterdisciplinarityMetrics(
            shannon_index=kwargs["shannon"], simpson_index=kwargs["simpson"],
            active_disciplines=kwargs["active_disciplines"],
            active_fields=kwargs["active_fields"],
            is_interdisciplinary=kwargs["is_interdisciplinary"],
        )

        # --- FieldOfScience mit CAGR ---
        # Fuer jedes FIELD-level Disziplin zaehle Unterdisziplinen
        field_ids = {str(f["id"]) for f in kwargs["fields"]}
        sub_field_counts: dict[str, int] = {fid: 0 for fid in field_ids}
        for d in kwargs["disciplines"]:
            parent = str(d.get("parent_id", ""))
            if parent in sub_field_counts:
                sub_field_counts[parent] += 1

        pb_fields = [
            uc10_euroscivoc_pb2.FieldOfScience(
                id=str(f["id"]),
                label=str(f.get("label", "")),
                total_publications=0,
                total_projects=int(f.get("project_count", 0)),
                share=float(f.get("share", 0.0)),
                active_sub_fields=sub_field_counts.get(str(f["id"]), 0),
                cagr=float(f.get("cagr", 0.0)),
            )
            for f in kwargs["fields"]
        ]

        return uc10_euroscivoc_pb2.EuroSciVocResponse(
            disciplines=pb_disciplines, disciplinary_links=pb_links,
            discipline_trend=pb_trend, interdisciplinarity=pb_interdisciplinarity,
            fields_of_science=pb_fields,
            total_mapped_publications=kwargs["total_mapped"], metadata=metadata,
        )

    def _build_empty_response(self, request_id: str, t0: float) -> Any:
        processing_time_ms = int((time.monotonic() - t0) * 1000)
        return self._build_response(
            disciplines=[], tree_roots=[], fields=[], links=[], trend=[],
            shannon=0.0, simpson=0.0, active_disciplines=0, active_fields=0,
            is_interdisciplinary=False, total_mapped=0, data_sources=[], warnings=[],
            request_id=request_id, processing_time_ms=processing_time_ms,
        )
