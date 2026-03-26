"""UC1 LandscapeServicer — duenner gRPC-Adapter.

Extrahiert Request-Parameter aus Protobuf, delegiert Geschaeftslogik
an den AnalyzeLandscape Use Case und mappt das LandscapeResult
zurueck auf gRPC-/dict-Responses.

Migration von MVP v1.0:
- SQLite FTS5 MATCH -> PostgreSQL tsvector @@ plainto_tsquery
- aiosqlite -> asyncpg Connection Pool
- FastAPI Response -> gRPC Protobuf Messages
"""

from __future__ import annotations

import time
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
    from shared.generated.python import uc1_landscape_pb2_grpc
except ImportError:
    uc1_landscape_pb2_grpc = None  # type: ignore[assignment]

from src.config import Settings
from src.infrastructure.openaire_adapter import OpenAIREAdapter
from src.infrastructure.repository import LandscapeRepository
from src.mappers.dict_response import landscape_result_to_dict
from src.mappers.protobuf import landscape_result_to_proto
from src.use_case import AnalyzeLandscape, LandscapeResult

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Helper: Basis-Klasse ermitteln (gRPC Servicer oder object)
# ---------------------------------------------------------------------------
def _get_base_class() -> type:
    """Gibt die gRPC-Servicer-Basisklasse zurueck, oder object als Fallback."""
    if uc1_landscape_pb2_grpc is not None:
        return uc1_landscape_pb2_grpc.LandscapeServiceServicer  # type: ignore[return-value]
    return object


class LandscapeServicer(_get_base_class()):  # type: ignore[misc]
    """gRPC-Servicer fuer UC1 Technology Landscape.

    Duenner Adapter: extrahiert Parameter, delegiert an Use Case,
    mappt Ergebnis auf gRPC-Response.
    """

    def __init__(self, pool: asyncpg.Pool, settings: Settings | None = None) -> None:
        self._pool = pool
        self._settings = settings or Settings()
        repo = LandscapeRepository(pool)
        openaire = OpenAIREAdapter(
            access_token=self._settings.openaire_access_token,
            refresh_token=self._settings.openaire_refresh_token,
            timeout=self._settings.openaire_timeout_s,
            pool=pool,
        )
        self._use_case = AnalyzeLandscape(repo=repo, openaire=openaire)

    async def AnalyzeLandscape(
        self,
        request: Any,
        context: Any,
    ) -> Any:
        """UC1: Technologie-Landschaft analysieren.

        Empfaengt einen AnalysisRequest mit technology, time_range, european_only.
        Delegiert Geschaeftslogik an den Use Case.

        Args:
            request: tip.common.AnalysisRequest Protobuf-Message
            context: gRPC ServicerContext (fuer Fehlerbehandlung)

        Returns:
            tip.uc1.LandscapeResponse Protobuf-Message
        """
        t0 = time.monotonic()

        # --- Request-Parameter extrahieren ---
        technology = request.technology
        request_id = request.request_id or ""
        european_only = request.european_only

        # Zeitraum: Default 2010-2024 wenn nicht angegeben
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
            return self._build_empty_response(request_id)

        # --- Use Case ausfuehren ---
        result = await self._use_case.execute(
            technology=technology,
            start_year=start_year,
            end_year=end_year,
            european_only=european_only,
            top_n=top_n,
        )

        # --- Response bauen (Protobuf oder dict-Fallback) ---
        pb = landscape_result_to_proto(result, request_id)
        return pb if pb is not None else landscape_result_to_dict(result, request_id)

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _build_empty_response(request_id: str = "") -> Any:
        """Leere Response fuer Validierungsfehler."""
        pb = landscape_result_to_proto(LandscapeResult(), request_id)
        return pb if pb is not None else landscape_result_to_dict(LandscapeResult(), request_id)
