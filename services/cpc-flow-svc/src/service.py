"""UC5 CpcFlowServicer — gRPC-Implementierung der CPC-Co-Klassifikations-Analyse.

Empfaengt AnalysisRequest, berechnet Jaccard-Similarity-Matrix auf
CPC-Code-Co-Klassifikationen und identifiziert Technologie-Konvergenz.

Zwei Pfade:
1. SQL-nativ: patent_cpc Tabelle (alle Patente, keine Stichprobe)
2. Python-Pfad: Sampling + lokale Jaccard-Berechnung (Fallback)

Migration von MVP v1.0:
- SQLite FTS5 MATCH -> PostgreSQL tsvector @@ plainto_tsquery
- aiosqlite -> asyncpg Connection Pool
- FastAPI Response -> gRPC Protobuf Messages
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
    from shared.generated.python import uc5_cpc_flow_pb2
    from shared.generated.python import uc5_cpc_flow_pb2_grpc
except ImportError:
    common_pb2 = None  # type: ignore[assignment]
    uc5_cpc_flow_pb2 = None  # type: ignore[assignment]
    uc5_cpc_flow_pb2_grpc = None  # type: ignore[assignment]

# --- Shared Domain Funktionen ---
try:
    from shared.domain.cpc_flow import (
        assign_colors,
        build_cooccurrence_with_years,
        build_jaccard_from_sql,
        build_year_data_from_aggregates,
        compute_whitespace_opportunities,
        extract_cpc_sets_with_years,
    )
    from shared.domain.cpc_descriptions import get_cpc_description
except ImportError:
    from src.domain.metrics import (  # type: ignore[attr-defined]
        assign_colors,
        build_cooccurrence_with_years,
        build_jaccard_from_sql,
        build_year_data_from_aggregates,
        compute_whitespace_opportunities,
        extract_cpc_sets_with_years,
    )
    get_cpc_description = lambda code: ""  # type: ignore[assignment]  # noqa: E731

try:
    from shared.domain.sampling import stratified_sample
except ImportError:
    stratified_sample = None  # type: ignore[assignment]

from src.config import Settings
from src.infrastructure.repository import CpcFlowRepository

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Helper: Basis-Klasse ermitteln (gRPC Servicer oder object)
# ---------------------------------------------------------------------------
def _get_base_class() -> type:
    """Gibt die gRPC-Servicer-Basisklasse zurueck, oder object als Fallback."""
    if uc5_cpc_flow_pb2_grpc is not None:
        return uc5_cpc_flow_pb2_grpc.CpcFlowServiceServicer  # type: ignore[return-value]
    return object


class CpcFlowServicer(_get_base_class()):  # type: ignore[misc]
    """gRPC-Servicer fuer UC5 CPC Technology Flow.

    Berechnet Jaccard-Co-Klassifikations-Matrix:
    1. SQL-nativer Pfad: Direkte Aggregation in patent_cpc (bevorzugt)
    2. Python-Pfad: Rohdaten laden, ggf. Sampling, lokale Berechnung
    """

    def __init__(self, pool: asyncpg.Pool, settings: Settings | None = None) -> None:
        self._pool = pool
        self._settings = settings or Settings()
        self._repo = CpcFlowRepository(pool)

    async def AnalyzeCpcFlow(
        self,
        request: Any,
        context: Any,
    ) -> Any:
        """UC5: CPC-Technologiefluss analysieren.

        Args:
            request: tip.common.AnalysisRequest Protobuf-Message
            context: gRPC ServicerContext

        Returns:
            tip.uc5.CpcFlowResponse Protobuf-Message
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

        cpc_level = self._settings.cpc_level
        top_n = request.top_n or self._settings.top_n_codes

        logger.info(
            "cpc_flow_analyse_gestartet",
            technology=technology,
            start_year=start_year,
            end_year=end_year,
            cpc_level=cpc_level,
            top_n=top_n,
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

        # --- Analyse ausfuehren ---
        warnings: list[dict[str, str]] = []
        data_sources: list[dict[str, Any]] = []

        try:
            # Pruefen ob patent_cpc Tabelle existiert
            has_cpc_table = await self._repo.has_cpc_table()

            if has_cpc_table:
                result = await self._analyze_sql_path(
                    technology, start_year, end_year,
                    cpc_level=cpc_level, top_n=top_n,
                    warnings=warnings, data_sources=data_sources,
                )
            else:
                logger.info("patent_cpc_nicht_vorhanden", fallback="python_pfad")
                result = await self._analyze_python_path(
                    technology, start_year, end_year,
                    cpc_level=cpc_level, top_n=top_n,
                    warnings=warnings, data_sources=data_sources,
                )
        except Exception as exc:
            logger.warning("cpc_flow_fehlgeschlagen", fehler=str(exc))
            warnings.append({
                "message": f"CPC-Abfrage fehlgeschlagen: {exc}",
                "severity": "HIGH",
                "code": "QUERY_FAILED_CPC",
            })
            result = None

        if result is None:
            processing_time_ms = int((time.monotonic() - t0) * 1000)
            return self._build_response(
                labels=[], matrix=[], total_connections=0,
                total_patents=0, cpc_codes_info=[], top_pairs=[],
                year_data_entries=[], chord_data=[],
                similarity_threshold=self._settings.similarity_threshold,
                data_sources=data_sources, warnings=warnings,
                request_id=request_id, processing_time_ms=processing_time_ms,
            )

        processing_time_ms = int((time.monotonic() - t0) * 1000)

        logger.info(
            "cpc_flow_analyse_abgeschlossen",
            technology=technology,
            codes=len(result["labels"]),
            connections=result["total_connections"],
            total_patents=result["total_patents"],
            dauer_ms=processing_time_ms,
        )

        return self._build_response(
            labels=result["labels"],
            matrix=result["matrix"],
            total_connections=result["total_connections"],
            total_patents=result["total_patents"],
            cpc_codes_info=result.get("cpc_codes_info", []),
            top_pairs=result.get("top_pairs", []),
            year_data_entries=result.get("year_data_entries", []),
            chord_data=result.get("chord_data", []),
            pair_co_counts=result.get("pair_co_counts", {}),
            code_counts=result.get("code_counts", {}),
            similarity_threshold=self._settings.similarity_threshold,
            data_sources=data_sources,
            warnings=warnings,
            request_id=request_id,
            processing_time_ms=processing_time_ms,
        )

    # -----------------------------------------------------------------------
    # SQL-nativer Pfad
    # -----------------------------------------------------------------------

    async def _analyze_sql_path(
        self,
        technology: str,
        start_year: int,
        end_year: int,
        *,
        cpc_level: int,
        top_n: int,
        warnings: list[dict[str, str]],
        data_sources: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """SQL-native Jaccard-Berechnung via patent_cpc Tabelle."""
        result = await self._repo.compute_cpc_jaccard(
            technology, start_year=start_year, end_year=end_year,
            top_n=top_n, cpc_level=cpc_level,
        )

        labels = result["labels"]
        if not labels or len(labels) < 2:
            warnings.append({
                "message": "Zu wenige CPC-Codes fuer Fluss-Analyse",
                "severity": "MEDIUM",
                "code": "INSUFFICIENT_CPC_CODES",
            })
            return None

        data_sources.append({
            "name": "EPO DOCDB (PostgreSQL)",
            "type": "PATENT",
            "record_count": result["total_patents"],
        })

        # CPC Code-Counts + Co-Occurrence aus Repo (Bug 2 Fix)
        cc = result.get("code_counts", {})
        pair_co_counts = result.get("pair_co_counts", {})

        # Top-Paare extrahieren — mit echter co_occurrence_count
        top_pairs = _extract_top_pairs(
            labels, result["matrix"], top_n=10,
            pair_co_counts=pair_co_counts, code_counts=cc,
        )

        # Chord-Data aus Matrix ableiten
        chord_data = _build_chord_data(labels, result["matrix"])

        # CPC Codes Info — patent_count + Beschreibung durchreichen
        cpc_codes_info = [
            {"code": label, "description": get_cpc_description(label), "patent_count": cc.get(label, 0), "section": label[0] if label else ""}
            for label in labels
        ]

        # Whitespace-Analyse
        whitespace = compute_whitespace_opportunities(
            labels, result["matrix"], cc, top_n=10,
        )

        # Year-Data aus SQL-Aggregaten (Bug 1 Fix)
        year_data_entries: list[dict[str, Any]] = []
        try:
            cpc_year_rows = await self._repo.cpc_year_counts(
                technology, labels,
                start_year=start_year, end_year=end_year, cpc_level=cpc_level,
            )
            pair_year_rows = await self._repo.cpc_pair_year_counts(
                technology, labels,
                start_year=start_year, end_year=end_year, cpc_level=cpc_level,
            )
            year_data_entries = _build_year_data_entries(
                top_codes=labels,
                cpc_year_counts=cpc_year_rows,
                pair_year_counts=pair_year_rows,
            )
        except Exception as exc:
            logger.warning("year_data_aggregation_fehlgeschlagen", fehler=str(exc))
            warnings.append({
                "message": f"Year-Data-Aggregation fehlgeschlagen: {exc}",
                "severity": "LOW",
                "code": "YEAR_DATA_FAILED",
            })

        return {
            "labels": labels,
            "matrix": result["matrix"],
            "total_connections": result["total_connections"],
            "total_patents": result["total_patents"],
            "cpc_codes_info": cpc_codes_info,
            "top_pairs": top_pairs,
            "year_data_entries": year_data_entries,
            "chord_data": chord_data,
            "whitespace_opportunities": whitespace,
            "pair_co_counts": pair_co_counts,
            "code_counts": cc,
        }

    # -----------------------------------------------------------------------
    # Python-Pfad (Fallback)
    # -----------------------------------------------------------------------

    async def _analyze_python_path(
        self,
        technology: str,
        start_year: int,
        end_year: int,
        *,
        cpc_level: int,
        top_n: int,
        warnings: list[dict[str, str]],
        data_sources: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Python-basierte Berechnung mit optionalem Sampling."""
        patent_rows = await self._repo.get_cpc_codes_raw(
            technology, start_year=start_year, end_year=end_year,
        )

        if not patent_rows:
            warnings.append({
                "message": "Keine CPC-Codes fuer diese Technologie gefunden",
                "severity": "MEDIUM",
                "code": "NO_CPC_DATA",
            })
            return None

        data_sources.append({
            "name": "EPO DOCDB (PostgreSQL)",
            "type": "PATENT",
            "record_count": len(patent_rows),
        })

        # CPC-Code-Sets + Jahr pro Patent extrahieren
        patent_data = extract_cpc_sets_with_years(patent_rows, level=cpc_level)

        if len(patent_data) < 2:
            warnings.append({
                "message": "Zu wenige Patente mit mehreren CPC-Codes",
                "severity": "MEDIUM",
                "code": "INSUFFICIENT_CPC_PATENTS",
            })
            return None

        # Optional: Stratifizierte Stichprobe
        sample_size = self._settings.sample_size
        if stratified_sample is not None and len(patent_data) > sample_size:
            sample_result = stratified_sample(patent_data, target_size=sample_size)
            patent_data = sample_result.sampled_data
            warnings.append({
                "message": (
                    f"Stichprobe: {sample_result.sample_size} von "
                    f"{sample_result.population_size} Patenten "
                    f"(f={sample_result.sampling_fraction:.2%})"
                ),
                "severity": "LOW",
                "code": "SAMPLING_APPLIED",
            })

        # Co-Occurrence + Jaccard berechnen
        labels, matrix, total_connections, year_data = build_cooccurrence_with_years(
            patent_data, top_n=top_n,
        )

        if not labels or len(labels) < 2:
            warnings.append({
                "message": "Zu wenige CPC-Codes nach Filterung",
                "severity": "MEDIUM",
                "code": "INSUFFICIENT_CPC_CODES_FILTERED",
            })
            return None

        # CPC-Counts aus patent_data rekonstruieren (fuer union_count)
        local_code_counts: dict[str, int] = {}
        for codes, _year in patent_data:
            for code in codes:
                if code in labels:
                    local_code_counts[code] = local_code_counts.get(code, 0) + 1

        # Exakte Co-Occurrence fuer Top-Pairs
        local_pair_counts: dict[tuple[str, str], int] = {}
        for codes, _year in patent_data:
            relevant = sorted(c for c in codes if c in labels)
            for i in range(len(relevant)):
                for j in range(i + 1, len(relevant)):
                    key = (relevant[i], relevant[j])
                    local_pair_counts[key] = local_pair_counts.get(key, 0) + 1

        top_pairs = _extract_top_pairs(
            labels, matrix, top_n=10,
            pair_co_counts=local_pair_counts, code_counts=local_code_counts,
        )
        chord_data = _build_chord_data(labels, matrix)
        cpc_codes_info = [
            {"code": label, "description": "", "patent_count": local_code_counts.get(label, 0), "section": label[0] if label else ""}
            for label in labels
        ]

        # Year-Data aus year_data-Dict ableiten (Bug 1 Fix)
        year_data_entries: list[dict[str, Any]] = []
        cpc_counts_by_year = year_data.get("cpc_counts", {})
        pair_counts_by_year = year_data.get("pair_counts", {})
        for year_str in sorted(cpc_counts_by_year.keys()):
            year_code_counts = cpc_counts_by_year.get(year_str, {})
            year_pair_counts = pair_counts_by_year.get(year_str, {})
            active = len(year_code_counts)
            total_patents_y = sum(year_code_counts.values())

            sims: list[float] = []
            for pair_key, co in year_pair_counts.items():
                if "|" not in pair_key:
                    continue
                ca, cb = pair_key.split("|", 1)
                count_a = year_code_counts.get(ca, 0)
                count_b = year_code_counts.get(cb, 0)
                union = count_a + count_b - co
                if union > 0 and co > 0:
                    sims.append(co / union)

            avg_sim = sum(sims) / len(sims) if sims else 0.0
            max_sim = max(sims) if sims else 0.0
            year_data_entries.append({
                "year": int(year_str),
                "active_codes": active,
                "avg_similarity": round(avg_sim, 4),
                "max_similarity": round(max_sim, 4),
                "patent_count": total_patents_y,
            })

        return {
            "labels": labels,
            "matrix": matrix,
            "total_connections": total_connections,
            "total_patents": len(patent_data),
            "cpc_codes_info": cpc_codes_info,
            "top_pairs": top_pairs,
            "year_data_entries": year_data_entries,
            "chord_data": chord_data,
            "pair_co_counts": local_pair_counts,
            "code_counts": local_code_counts,
        }

    # -----------------------------------------------------------------------
    # Response Builder
    # -----------------------------------------------------------------------

    def _build_response(
        self,
        *,
        labels: list[str],
        matrix: list[list[float]],
        total_connections: int,
        total_patents: int,
        cpc_codes_info: list[dict[str, Any]],
        top_pairs: list[dict[str, Any]],
        year_data_entries: list[dict[str, Any]],
        chord_data: list[dict[str, Any]],
        similarity_threshold: float,
        data_sources: list[dict[str, Any]],
        warnings: list[dict[str, str]],
        request_id: str,
        processing_time_ms: int,
        pair_co_counts: dict[tuple[str, str], int] | None = None,
        code_counts: dict[str, int] | None = None,
    ) -> Any:
        """CpcFlowResponse aus berechneten Daten zusammenbauen."""
        pair_co_counts = pair_co_counts or {}
        code_counts = code_counts or {}

        if uc5_cpc_flow_pb2 is None or common_pb2 is None:
            return self._build_dict_response(
                labels=labels, matrix=matrix,
                total_connections=total_connections, total_patents=total_patents,
                cpc_codes_info=cpc_codes_info, top_pairs=top_pairs,
                year_data_entries=year_data_entries, chord_data=chord_data,
                similarity_threshold=similarity_threshold,
                data_sources=data_sources, warnings=warnings,
                request_id=request_id, processing_time_ms=processing_time_ms,
            )

        # --- Protobuf-Messages bauen ---

        # Jaccard Matrix (upper triangle, filtered by threshold)
        pb_jaccard = []
        n = len(labels)
        for i in range(n):
            for j in range(i + 1, n):
                sim = matrix[i][j] if i < len(matrix) and j < len(matrix[i]) else 0.0
                if sim >= similarity_threshold:
                    code_a = labels[i]
                    code_b = labels[j]
                    key = (code_a, code_b) if code_a < code_b else (code_b, code_a)
                    co = pair_co_counts.get(key, 0)
                    if co == 0 and sim > 0:
                        # aus Jaccard zurueckrechnen als Fallback
                        ca = code_counts.get(code_a, 0)
                        cb = code_counts.get(code_b, 0)
                        if ca + cb > 0:
                            co = int(round(sim * (ca + cb) / (1.0 + sim)))
                    union = max(0, code_counts.get(code_a, 0)
                                   + code_counts.get(code_b, 0)
                                   - co)
                    pb_jaccard.append(uc5_cpc_flow_pb2.JaccardMatrixEntry(
                        code_a=code_a,
                        code_b=code_b,
                        similarity=sim,
                        co_occurrence_count=co,
                        union_count=union,
                    ))

        # Top Pairs — co_occurrence_count aus dem bereits berechneten Feld (Bug 2 Fix)
        pb_top_pairs = [
            uc5_cpc_flow_pb2.TopCpcPair(
                code_a=p["code_a"],
                description_a="",
                code_b=p["code_b"],
                description_b="",
                similarity=p["similarity"],
                co_occurrence_count=p.get("co_occurrence_count", 0),
            )
            for p in top_pairs
        ]

        # Year Data
        pb_year_data = [
            uc5_cpc_flow_pb2.CpcYearData(
                year=yd.get("year", 0),
                active_codes=yd.get("active_codes", 0),
                avg_similarity=yd.get("avg_similarity", 0.0),
                max_similarity=yd.get("max_similarity", 0.0),
                patent_count=yd.get("patent_count", 0),
            )
            for yd in year_data_entries
        ]

        # Chord Data
        pb_chord = [
            uc5_cpc_flow_pb2.ChordDataEntry(
                source=cd["source"],
                target=cd["target"],
                value=cd.get("value", 0),
                source_label=cd.get("source_label", ""),
                target_label=cd.get("target_label", ""),
            )
            for cd in chord_data
        ]

        # CPC Codes Info
        pb_cpc_codes = [
            uc5_cpc_flow_pb2.CpcCodeInfo(
                code=ci["code"],
                description=ci.get("description", ""),
                patent_count=ci.get("patent_count", 0),
                section=ci.get("section", ""),
            )
            for ci in cpc_codes_info
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
                type=common_pb2.PATENT,
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

        return uc5_cpc_flow_pb2.CpcFlowResponse(
            jaccard_matrix=pb_jaccard,
            top_pairs=pb_top_pairs,
            year_data=pb_year_data,
            chord_data=pb_chord,
            cpc_codes=pb_cpc_codes,
            similarity_threshold=similarity_threshold,
            total_pairs_analyzed=total_connections,
            metadata=metadata,
        )

    def _build_dict_response(
        self,
        *,
        labels: list[str],
        matrix: list[list[float]],
        total_connections: int,
        total_patents: int,
        cpc_codes_info: list[dict[str, Any]],
        top_pairs: list[dict[str, Any]],
        year_data_entries: list[dict[str, Any]],
        chord_data: list[dict[str, Any]],
        similarity_threshold: float,
        data_sources: list[dict[str, Any]],
        warnings: list[dict[str, str]],
        request_id: str,
        processing_time_ms: int,
    ) -> dict[str, Any]:
        """Fallback-Response als dict (wenn gRPC-Stubs nicht generiert)."""
        return {
            "labels": labels,
            "matrix": matrix,
            "total_connections": total_connections,
            "total_patents": total_patents,
            "cpc_codes_info": cpc_codes_info,
            "top_pairs": top_pairs,
            "year_data_entries": year_data_entries,
            "chord_data": chord_data,
            "similarity_threshold": similarity_threshold,
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
            labels=[], matrix=[], total_connections=0, total_patents=0,
            cpc_codes_info=[], top_pairs=[], year_data_entries=[],
            chord_data=[], similarity_threshold=self._settings.similarity_threshold,
            data_sources=[], warnings=[], request_id=request_id,
            processing_time_ms=processing_time_ms,
        )


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _extract_top_pairs(
    labels: list[str],
    matrix: list[list[float]],
    *,
    top_n: int = 10,
    pair_co_counts: dict[tuple[str, str], int] | None = None,
    code_counts: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Top CPC-Paare nach Jaccard-Similarity extrahieren.

    Args:
        labels: CPC-Code-Labels.
        matrix: Jaccard-Similarity-Matrix.
        top_n: Anzahl zurueckgegebener Paare.
        pair_co_counts: Optional Lookup {(code_a, code_b): co_count}
            fuer exakte Intersection-Groessen (Bug 2 Fix).
        code_counts: Optional Lookup {code: patent_count} fuer union_count.
    """
    pair_co_counts = pair_co_counts or {}
    code_counts = code_counts or {}

    pairs: list[dict[str, Any]] = []
    n = len(labels)
    for i in range(n):
        for j in range(i + 1, n):
            sim = matrix[i][j] if i < len(matrix) and j < len(matrix[i]) else 0.0
            if sim > 0:
                code_a = labels[i]
                code_b = labels[j]
                key = (code_a, code_b) if code_a < code_b else (code_b, code_a)
                co_count = pair_co_counts.get(key, 0)

                # Wenn co_count nicht bekannt, aus Jaccard zurueckrechnen:
                # jaccard = co / (a + b - co)  -->  co = jaccard*(a+b) / (1+jaccard)
                if co_count == 0 and code_counts:
                    count_a = code_counts.get(code_a, 0)
                    count_b = code_counts.get(code_b, 0)
                    if sim > 0 and (count_a + count_b) > 0:
                        co_count = int(round(sim * (count_a + count_b) / (1.0 + sim)))

                count_a = code_counts.get(code_a, 0)
                count_b = code_counts.get(code_b, 0)
                union_count = max(0, count_a + count_b - co_count)

                pairs.append({
                    "code_a": code_a,
                    "code_b": code_b,
                    "similarity": sim,
                    "co_occurrence_count": co_count,
                    "union_count": union_count,
                })
    pairs.sort(key=lambda p: p["similarity"], reverse=True)
    return pairs[:top_n]


def _build_year_data_entries(
    *,
    top_codes: list[str],
    cpc_year_counts: list[dict[str, Any]],
    pair_year_counts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Year-Data aus Aggregaten bauen (Bug 1 Fix).

    Aggregiert pro Jahr:
    - active_codes: Anzahl distinkter CPC-Codes
    - patent_count: Summe Patent-Counts
    - avg_similarity / max_similarity: Jaccard ueber Paare des Jahres.
    """
    codes_by_year: dict[int, dict[str, int]] = {}
    for row in cpc_year_counts:
        year = int(row["year"])
        code = row["code"]
        count = int(row["patent_count"])
        codes_by_year.setdefault(year, {})[code] = count

    pairs_by_year: dict[int, list[tuple[str, str, int]]] = {}
    for row in pair_year_counts:
        year = int(row["year"])
        pairs_by_year.setdefault(year, []).append(
            (row["code_a"], row["code_b"], int(row["co_count"])),
        )

    entries: list[dict[str, Any]] = []
    for year in sorted(codes_by_year.keys()):
        code_counts = codes_by_year[year]
        active = len(code_counts)
        total_patents_y = sum(code_counts.values())

        sims: list[float] = []
        for code_a, code_b, co in pairs_by_year.get(year, []):
            ca = code_counts.get(code_a, 0)
            cb = code_counts.get(code_b, 0)
            union = ca + cb - co
            if union > 0 and co > 0:
                sims.append(co / union)

        avg_sim = sum(sims) / len(sims) if sims else 0.0
        max_sim = max(sims) if sims else 0.0

        entries.append({
            "year": year,
            "active_codes": active,
            "avg_similarity": round(avg_sim, 4),
            "max_similarity": round(max_sim, 4),
            "patent_count": total_patents_y,
        })
    return entries


def _build_chord_data(
    labels: list[str],
    matrix: list[list[float]],
) -> list[dict[str, Any]]:
    """Chord-Diagramm-Daten aus Jaccard-Matrix ableiten."""
    chord: list[dict[str, Any]] = []
    n = len(labels)
    for i in range(n):
        for j in range(i + 1, n):
            sim = matrix[i][j] if i < len(matrix) and j < len(matrix[i]) else 0.0
            if sim > 0:
                # Wert als Integer-Gewicht (Skalierung fuer Visualisierung)
                value = max(1, int(sim * 1000))
                chord.append({
                    "source": labels[i],
                    "target": labels[j],
                    "value": value,
                    "source_label": labels[i],
                    "target_label": labels[j],
                })
    return chord
