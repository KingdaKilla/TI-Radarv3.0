"""UC3 CompetitiveServicer — gRPC-Implementierung der Wettbewerbs-Analyse.

Empfaengt AnalysisRequest, ermittelt Top-Akteure aus Patent-Anmeldern
und CORDIS-Organisationen, berechnet HHI-Konzentration und baut
Netzwerk-Graph fuer Co-Patenting/Co-Partizipation.

Entity Resolution (TODO 6.4):
- Optional: Nutzt entity.unified_actors fuer deduplizierte Akteur-Namen.
- Graceful Degradation: Faellt auf Raw-Namen zurueck wenn entity-Tabellen
  nicht verfuegbar oder leer sind.
- Steuerbar via Settings.use_entity_resolution (Default: True).

Migration von MVP v1.0:
- SQLite FTS5 MATCH -> PostgreSQL tsvector @@ plainto_tsquery
- aiosqlite -> asyncpg Connection Pool
- FastAPI Response -> gRPC Protobuf Messages
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from itertools import combinations
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
    from shared.generated.python import uc3_competitive_pb2
    from shared.generated.python import uc3_competitive_pb2_grpc
except ImportError:
    common_pb2 = None  # type: ignore[assignment]
    uc3_competitive_pb2 = None  # type: ignore[assignment]
    uc3_competitive_pb2_grpc = None  # type: ignore[assignment]

# --- Shared Domain Metriken ---
from shared.domain.metrics import cr4, hhi_concentration_level, hhi_index

from src.config import Settings
from src.infrastructure.repository import CompetitiveRepository

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Helper: Basis-Klasse ermitteln (gRPC Servicer oder object)
# ---------------------------------------------------------------------------
def _get_base_class() -> type:
    """Gibt die gRPC-Servicer-Basisklasse zurueck, oder object als Fallback."""
    if uc3_competitive_pb2_grpc is not None:
        return uc3_competitive_pb2_grpc.CompetitiveServiceServicer  # type: ignore[return-value]
    return object


class CompetitiveServicer(_get_base_class()):  # type: ignore[misc]
    """gRPC-Servicer fuer UC3 Competitive Intelligence.

    Koordiniert parallele Abfragen:
    1. Patent-Anmelder (PostgreSQL, tsvector-Suche)
    2. CORDIS-Organisationen (PostgreSQL, tsvector-Suche)
    3. Co-Patent-Kanten (Netzwerk)
    4. Co-Partizipation-Kanten (Netzwerk)

    Berechnet HHI, Marktanteile und baut Netzwerk-Graph.
    """

    def __init__(self, pool: asyncpg.Pool, settings: Settings | None = None) -> None:
        self._pool = pool
        self._settings = settings or Settings()
        self._repo = CompetitiveRepository(pool)

    async def AnalyzeCompetitive(
        self,
        request: Any,
        context: Any,
    ) -> Any:
        """UC3: Wettbewerbslandschaft analysieren.

        Args:
            request: tip.common.AnalysisRequest Protobuf-Message
            context: gRPC ServicerContext

        Returns:
            tip.uc3.CompetitiveResponse Protobuf-Message
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

        top_n = request.top_n or 20

        logger.info(
            "competitive_analyse_gestartet",
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

        patent_actors: dict[str, int] = {}
        cordis_actors: dict[str, int] = {}
        cordis_countries: dict[str, str] = {}

        limit = self._settings.top_actors_limit

        # --- Entity Resolution: Unified Actors (optional, TODO 6.4) ---
        # Wenn aktiviert, zuerst deduplizierte Akteure abfragen.
        # Graceful Fallback: Bei leerer Antwort auf Raw-Queries zurueckfallen.
        unified_actors_used = False
        unified_actor_list: list[dict[str, Any]] = []

        if self._settings.use_entity_resolution:
            try:
                unified_actor_list = await self._repo.top_unified_actors(
                    technology,
                    start_year=start_year,
                    end_year=end_year,
                    european_only=european_only,
                    limit=limit,
                )
                if unified_actor_list:
                    unified_actors_used = True
                    logger.info(
                        "entity_resolution_aktiv",
                        technology=technology,
                        unified_actors=len(unified_actor_list),
                    )
                    data_sources.append({
                        "name": "Entity Resolution (unified_actors)",
                        "type": "PATENT",
                        "record_count": sum(
                            a.get("total_count", 0) for a in unified_actor_list
                        ),
                    })
            except Exception as exc:
                logger.warning(
                    "entity_resolution_uebersprungen",
                    error=str(exc),
                )
                warnings.append({
                    "message": f"Entity Resolution fehlgeschlagen, Fallback auf Raw-Namen: {exc}",
                    "severity": "LOW",
                    "code": "ENTITY_RESOLUTION_FAILED",
                })

        # --- Fallback: Raw-Queries (Patent-Anmelder + CORDIS-Organisationen) ---
        if not unified_actors_used:
            # Parallele Abfragen fuer Patent-Anmelder und CORDIS-Organisationen
            tasks = [
                asyncio.create_task(
                    self._repo.top_patent_applicants(
                        technology, start_year=start_year, end_year=end_year,
                        european_only=european_only, limit=limit,
                    ),
                    name="patent_applicants",
                ),
                asyncio.create_task(
                    self._repo.top_cordis_organizations(
                        technology, start_year=start_year, end_year=end_year,
                        limit=limit,
                    ),
                    name="cordis_organizations",
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

                if name == "patent_applicants":
                    for a in result:
                        actor_name = str(a["name"]).upper().strip()
                        if actor_name:
                            patent_actors[actor_name] = patent_actors.get(actor_name, 0) + int(a["count"])
                    if result:
                        data_sources.append({
                            "name": "EPO DOCDB (PostgreSQL)",
                            "type": "PATENT",
                            "record_count": sum(int(a["count"]) for a in result),
                        })

                elif name == "cordis_organizations":
                    for o in result:
                        actor_name = str(o["name"]).upper().strip()
                        if actor_name:
                            cordis_actors[actor_name] = cordis_actors.get(actor_name, 0) + int(o["count"])
                            if o.get("country"):
                                cordis_countries[actor_name] = str(o["country"])
                    if result:
                        data_sources.append({
                            "name": "CORDIS (PostgreSQL)",
                            "type": "PROJECT",
                            "record_count": sum(int(o["count"]) for o in result),
                        })

        # --- Akteure zusammenfuehren ---
        actor_counts: dict[str, int] = {}

        if unified_actors_used:
            # Entity Resolution: Akteure bereits dedupliziert
            for ua in unified_actor_list:
                actor_name = str(ua["name"]).upper().strip()
                if actor_name:
                    total = ua.get("total_count", 0)
                    actor_counts[actor_name] = total
                    patent_actors[actor_name] = ua.get("patent_count", 0)
                    cordis_actors[actor_name] = ua.get("project_count", 0)
                    if ua.get("country_code"):
                        cordis_countries[actor_name] = str(ua["country_code"])
        else:
            # Raw-Merge: Patent + CORDIS Counts addieren
            for name, count in patent_actors.items():
                actor_counts[name] = actor_counts.get(name, 0) + count
            for name, count in cordis_actors.items():
                actor_counts[name] = actor_counts.get(name, 0) + count

        if not actor_counts:
            return self._build_empty_response(request_id, t0)

        sorted_actors = sorted(actor_counts.items(), key=lambda x: x[1], reverse=True)
        total_activity = sum(c for _, c in sorted_actors)

        # --- Top-Akteure mit Marktanteilen ---
        top_actors: list[dict[str, Any]] = []
        for name, count in sorted_actors[:top_n]:
            share = count / total_activity if total_activity > 0 else 0.0
            top_actors.append({
                "name": name,
                "country_code": cordis_countries.get(name, ""),
                "patent_count": patent_actors.get(name, 0),
                "project_count": cordis_actors.get(name, 0),
                "share": round(share, 4),
            })

        # --- HHI und CR4 berechnen ---
        shares = [c / total_activity for _, c in sorted_actors] if total_activity > 0 else []
        hhi = hhi_index(shares)
        level_en, _level_de = hhi_concentration_level(hhi)
        cr4_value = cr4(shares)

        # Top-3 / Top-10 Anteil
        top_3_count = sum(c for _, c in sorted_actors[:3])
        top_3_share = top_3_count / total_activity if total_activity > 0 else 0.0
        top_10_count = sum(c for _, c in sorted_actors[:10])
        top_10_share = top_10_count / total_activity if total_activity > 0 else 0.0

        # --- Netzwerk-Graph ---
        network_nodes, network_edges = await self._build_network(
            technology, start_year, end_year, european_only,
            actor_counts, patent_actors, cordis_actors, warnings,
        )

        # --- Verarbeitungszeit ---
        processing_time_ms = int((time.monotonic() - t0) * 1000)

        logger.info(
            "competitive_analyse_abgeschlossen",
            technology=technology,
            hhi=round(hhi, 1),
            cr4=round(cr4_value, 4),
            level=level_en,
            total_actors=len(actor_counts),
            dauer_ms=processing_time_ms,
        )

        return self._build_response(
            hhi=hhi,
            level_en=level_en,
            cr4_share=cr4_value,
            top_actors=top_actors,
            network_nodes=network_nodes,
            network_edges=network_edges,
            top_3_share=top_3_share,
            top_10_share=top_10_share,
            total_actors=len(actor_counts),
            data_sources=data_sources,
            warnings=warnings,
            request_id=request_id,
            processing_time_ms=processing_time_ms,
        )

    # -----------------------------------------------------------------------
    # Netzwerk-Graph
    # -----------------------------------------------------------------------

    async def _build_network(
        self,
        technology: str,
        start_year: int,
        end_year: int,
        european_only: bool,
        actor_counts: dict[str, int],
        patent_actors: dict[str, int],
        cordis_actors: dict[str, int],
        warnings: list[dict[str, str]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Netzwerk-Graph: Knoten + Kanten aus Co-Applicants und Co-Partizipation."""
        all_edges: dict[tuple[str, str], int] = {}
        patent_actor_set: set[str] = set(patent_actors.keys())
        cordis_actor_set: set[str] = set(cordis_actors.keys())

        # Parallele Abfrage fuer Kanten
        tasks = [
            asyncio.create_task(
                self._repo.co_patent_applicants(
                    technology, start_year=start_year, end_year=end_year,
                    european_only=european_only, limit=200,
                ),
                name="co_patents",
            ),
            asyncio.create_task(
                self._repo.co_project_participants(
                    technology, start_year=start_year, end_year=end_year,
                    limit=200,
                ),
                name="co_projects",
            ),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for task, result in zip(tasks, results, strict=False):
            name = task.get_name()
            if isinstance(result, Exception):
                logger.warning("netzwerk_query_fehlgeschlagen", task=name, fehler=str(result))
                warnings.append({
                    "message": f"Netzwerk '{name}' fehlgeschlagen: {result}",
                    "severity": "LOW",
                    "code": f"NETWORK_FAILED_{name.upper()}",
                })
                continue

            for edge in result:
                a = str(edge["actor_a"]).upper().strip()
                b = str(edge["actor_b"]).upper().strip()
                if name == "co_patents":
                    patent_actor_set.add(a)
                    patent_actor_set.add(b)
                else:
                    cordis_actor_set.add(a)
                    cordis_actor_set.add(b)
                key = (min(a, b), max(a, b))
                all_edges[key] = all_edges.get(key, 0) + int(edge["co_count"])

        if not all_edges:
            return [], []

        # Top-Akteure filtern
        max_nodes = self._settings.network_max_nodes
        max_edges = self._settings.network_max_edges

        top_actor_names = sorted(
            actor_counts.keys(), key=lambda n: actor_counts[n], reverse=True,
        )[:max_nodes]
        top_set = set(top_actor_names)

        filtered_edges = [
            (a, b, w) for (a, b), w in all_edges.items()
            if a in top_set and b in top_set
        ]
        filtered_edges.sort(key=lambda x: x[2], reverse=True)
        filtered_edges = filtered_edges[:max_edges]

        connected: set[str] = set()
        for a, b, _ in filtered_edges:
            connected.add(a)
            connected.add(b)

        nodes: list[dict[str, Any]] = []
        for name in connected:
            nodes.append({
                "id": name,
                "label": name,
                "size": float(actor_counts.get(name, 0)),
                "community": 0,
                "country_code": "",
            })

        edges: list[dict[str, Any]] = [
            {"source": a, "target": b, "weight": w, "collaboration_type": "MIXED"}
            for a, b, w in filtered_edges
        ]

        return nodes, edges

    # -----------------------------------------------------------------------
    # Response Builder
    # -----------------------------------------------------------------------

    def _build_response(
        self,
        *,
        hhi: float,
        level_en: str,
        cr4_share: float = 0.0,
        top_actors: list[dict[str, Any]],
        network_nodes: list[dict[str, Any]],
        network_edges: list[dict[str, Any]],
        top_3_share: float,
        top_10_share: float,
        total_actors: int,
        data_sources: list[dict[str, Any]],
        warnings: list[dict[str, str]],
        request_id: str,
        processing_time_ms: int,
    ) -> Any:
        """CompetitiveResponse aus berechneten Daten zusammenbauen."""
        if uc3_competitive_pb2 is None or common_pb2 is None:
            return self._build_dict_response(
                hhi=hhi, level_en=level_en, cr4_share=cr4_share,
                top_actors=top_actors,
                network_nodes=network_nodes, network_edges=network_edges,
                top_3_share=top_3_share, top_10_share=top_10_share,
                total_actors=total_actors, data_sources=data_sources,
                warnings=warnings, request_id=request_id,
                processing_time_ms=processing_time_ms,
            )

        # --- Protobuf-Messages bauen ---
        # Concentration Level Enum mappen
        level_map = {
            "Low": uc3_competitive_pb2.LOW,
            "Moderate": uc3_competitive_pb2.MODERATE,
            "High": uc3_competitive_pb2.HIGH,
        }
        hhi_level = level_map.get(level_en, uc3_competitive_pb2.CONCENTRATION_LEVEL_UNSPECIFIED)

        # Top Actors
        pb_actors = [
            uc3_competitive_pb2.Actor(
                name=a["name"],
                country_code=a.get("country_code", ""),
                country_name="",
                patent_count=a.get("patent_count", 0),
                project_count=a.get("project_count", 0),
                publication_count=0,
                share=a["share"],
                actor_type=uc3_competitive_pb2.ACTOR_TYPE_UNSPECIFIED,
            )
            for a in top_actors
        ]

        # Network Edges
        collab_map = {
            "CO_PATENT": uc3_competitive_pb2.CO_PATENT,
            "CO_PROJECT": uc3_competitive_pb2.CO_PROJECT,
            "MIXED": uc3_competitive_pb2.MIXED,
        }
        pb_edges = [
            uc3_competitive_pb2.NetworkEdge(
                source=e["source"],
                target=e["target"],
                weight=e["weight"],
                collaboration_type=collab_map.get(
                    e.get("collaboration_type", "MIXED"),
                    uc3_competitive_pb2.COLLABORATION_TYPE_UNSPECIFIED,
                ),
            )
            for e in network_edges
        ]

        # Network Nodes
        pb_nodes = [
            uc3_competitive_pb2.NetworkNode(
                id=n["id"],
                label=n["label"],
                size=n["size"],
                community=n.get("community", 0),
                country_code=n.get("country_code", ""),
            )
            for n in network_nodes
        ]

        # Metadata
        _severity_map = {
            "LOW": common_pb2.LOW,
            "MEDIUM": common_pb2.MEDIUM,
            "HIGH": common_pb2.HIGH,
        }
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

        return uc3_competitive_pb2.CompetitiveResponse(
            hhi_index=hhi,
            hhi_level=hhi_level,
            top_actors=pb_actors,
            network_edges=pb_edges,
            network_nodes=pb_nodes,
            top3_share=top_3_share,
            top10_share=top_10_share,
            total_actors=total_actors,
            metadata=metadata,
            cr4_share=cr4_share,
        )

    def _build_dict_response(
        self,
        *,
        hhi: float,
        level_en: str,
        cr4_share: float = 0.0,
        top_actors: list[dict[str, Any]],
        network_nodes: list[dict[str, Any]],
        network_edges: list[dict[str, Any]],
        top_3_share: float,
        top_10_share: float,
        total_actors: int,
        data_sources: list[dict[str, Any]],
        warnings: list[dict[str, str]],
        request_id: str,
        processing_time_ms: int,
    ) -> dict[str, Any]:
        """Fallback-Response als dict (wenn gRPC-Stubs nicht generiert)."""
        return {
            "hhi_index": round(hhi, 1),
            "hhi_level": level_en,
            "cr4_share": round(cr4_share, 4),
            "top_actors": top_actors,
            "network_edges": network_edges,
            "network_nodes": network_nodes,
            "top3_share": round(top_3_share, 4),
            "top10_share": round(top_10_share, 4),
            "total_actors": total_actors,
            "metadata": {
                "processing_time_ms": processing_time_ms,
                "data_sources": data_sources,
                "warnings": warnings,
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

    def _build_empty_response(self, request_id: str, t0: float) -> Any:
        """Leere Response bei ungueltigem Request oder keinen Daten."""
        processing_time_ms = int((time.monotonic() - t0) * 1000)
        return self._build_response(
            hhi=0.0, level_en="Low", top_actors=[],
            network_nodes=[], network_edges=[],
            top_3_share=0.0, top_10_share=0.0,
            total_actors=0, data_sources=[], warnings=[],
            request_id=request_id, processing_time_ms=processing_time_ms,
        )
