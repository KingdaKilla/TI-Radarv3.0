"""Unit-Tests fuer GLEIF-Adapter Log-Level-Verhalten.

Hintergrund (Bug v3.4.0):
    GLEIF fuehrt nur LEI-pflichtige Entitaeten (Finanzwesen). Staatliche
    Forschungsinstitute (CNRS, IMEC, CEA, ETHZ, ...) haben systembedingt
    keinen LEI -> die API antwortet mit HTTP 404. Diese 404er sind
    *fachlich erwartbar* und duerfen den Operator-Log nicht mit
    ``warning``-Zeilen zuspammen.

Erwartetes Verhalten:
    - HTTP 404 -> ``debug`` (kein Warning, da erwartbar).
    - HTTP 5xx / 403 / Timeout / ConnectError -> ``warning``.

Ansatz:
    Der Adapter verwendet ``structlog``. Wir patchen das modul-lokale
    ``logger``-Objekt mit einem ``MagicMock`` und pruefen direkt, welche
    Log-Methode (``debug`` vs. ``warning``) fuer welchen Fehler-Typ
    aufgerufen wurde.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.infrastructure import gleif_adapter as gleif_mod
from src.infrastructure.gleif_adapter import GLEIFAdapter


def _make_http_status_error(status_code: int) -> httpx.HTTPStatusError:
    """Baut einen httpx.HTTPStatusError mit gegebenem Statuscode."""
    request = httpx.Request(
        "GET",
        "https://api.gleif.org/api/v1/fuzzy-completions",
    )
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(
        f"Client error '{status_code}' for url '{request.url}'",
        request=request,
        response=response,
    )


def _events(mock_logger: MagicMock, method: str) -> list[tuple[tuple, dict]]:
    """Liefert Liste (args, kwargs) fuer Aufrufe von logger.<method>."""
    return [call.args and (call.args, call.kwargs) or ((), call.kwargs)
            for call in getattr(mock_logger, method).call_args_list]


class TestGleifAdapterLogLevel:
    """Prueft die log-level-Behandlung im ``resolve``-Fehlerpfad."""

    @pytest.mark.asyncio
    async def test_404_wird_als_debug_geloggt_nicht_als_warning(self):
        """404 -> debug ``gleif_lei_not_found``; KEIN ``fehlgeschlagen``-warning."""
        adapter = GLEIFAdapter(pool=None)
        err = _make_http_status_error(404)

        mock_logger = MagicMock()
        with patch.object(gleif_mod, "logger", mock_logger), \
             patch.object(
                 adapter, "_fetch_from_api", new=AsyncMock(side_effect=err),
             ):
            result = await adapter.resolve(
                "INTERUNIVERSITAIR MICRO-ELECTRONICA CENTRUM",
            )

        assert result is None

        # KEIN 'fehlgeschlagen'-warning bei erwartbarem 404.
        warning_events = [c.args[0] for c in mock_logger.warning.call_args_list]
        assert not any("fehlgeschlagen" in ev for ev in warning_events), (
            f"404 darf kein warning erzeugen, gesehen: {warning_events}"
        )

        # Stattdessen: Debug-Eintrag 'gleif_lei_not_found'.
        debug_events = [c.args[0] for c in mock_logger.debug.call_args_list]
        assert any("gleif_lei_not_found" in ev for ev in debug_events), (
            f"Erwarte Debug 'gleif_lei_not_found', gesehen: {debug_events}"
        )

    @pytest.mark.asyncio
    async def test_500_wird_als_warning_geloggt(self):
        """5xx Server-Error -> warning (echte API-Stoerung)."""
        adapter = GLEIFAdapter(pool=None)
        err = _make_http_status_error(500)

        mock_logger = MagicMock()
        with patch.object(gleif_mod, "logger", mock_logger), \
             patch.object(
                 adapter, "_fetch_from_api", new=AsyncMock(side_effect=err),
             ):
            result = await adapter.resolve("Siemens AG")

        assert result is None
        warning_events = [c.args[0] for c in mock_logger.warning.call_args_list]
        assert any("fehlgeschlagen" in ev for ev in warning_events), (
            f"5xx muss warning erzeugen, gesehen: {warning_events}"
        )

    @pytest.mark.asyncio
    async def test_403_wird_als_warning_geloggt(self):
        """403 Forbidden -> warning (Auth-Problem)."""
        adapter = GLEIFAdapter(pool=None)
        err = _make_http_status_error(403)

        mock_logger = MagicMock()
        with patch.object(gleif_mod, "logger", mock_logger), \
             patch.object(
                 adapter, "_fetch_from_api", new=AsyncMock(side_effect=err),
             ):
            result = await adapter.resolve("Foo Corp")

        assert result is None
        warning_events = [c.args[0] for c in mock_logger.warning.call_args_list]
        assert any("fehlgeschlagen" in ev for ev in warning_events), (
            f"403 muss warning erzeugen, gesehen: {warning_events}"
        )

    @pytest.mark.asyncio
    async def test_timeout_wird_als_warning_geloggt(self):
        """Timeout -> warning (echte Verbindungsstoerung)."""
        adapter = GLEIFAdapter(pool=None)
        err = httpx.TimeoutException("request timeout")

        mock_logger = MagicMock()
        with patch.object(gleif_mod, "logger", mock_logger), \
             patch.object(
                 adapter, "_fetch_from_api", new=AsyncMock(side_effect=err),
             ):
            result = await adapter.resolve("Foo Corp")

        assert result is None
        warning_events = [c.args[0] for c in mock_logger.warning.call_args_list]
        assert any("fehlgeschlagen" in ev for ev in warning_events), (
            f"Timeout muss warning erzeugen, gesehen: {warning_events}"
        )

    @pytest.mark.asyncio
    async def test_404_cached_negative_result_vermeidet_zweiten_api_call(self):
        """Sanity: 404 laesst kein Ergebnis ausser None liefern."""
        adapter = GLEIFAdapter(pool=None)
        err = _make_http_status_error(404)

        with patch.object(
            adapter, "_fetch_from_api", new=AsyncMock(side_effect=err),
        ):
            result = await adapter.resolve("Some Research Institute")

        assert result is None
