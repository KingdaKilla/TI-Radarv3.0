"""Unit-Tests fuer den OpenAIRE-Adapter.

Fokus: Log-Spam-Unterdrueckung bei ungueltigem Refresh-Token.

Wenn der Refresh-Token-Endpunkt einen 4xx-Fehler liefert (abgelaufener oder
widerrufener Token), setzt der Adapter ein Modul-Level-Flag `_token_invalid`
und senkt nachfolgende `openaire_jahr_fehlgeschlagen`- und
`openaire_teilergebnis`-Logs von `warning` auf `debug` ab. Damit wird die
vorhersehbare 22+ Zeilen-Kaskade (11 Jahre x 2 Log-Zeilen) pro Analyse
vermieden, ohne die fachliche Behandlung (Fallback auf CORDIS) zu aendern.
"""
# ruff: noqa: SIM117

from __future__ import annotations

from typing import Any

import httpx
import pytest

from src.infrastructure import openaire_adapter
from src.infrastructure.openaire_adapter import (
    OpenAIREAdapter,
    _reset_token_invalid_flag,
)


@pytest.fixture(autouse=True)
def _reset_module_state() -> None:
    """Setzt Modul-Level-Singletons zwischen Tests zurueck."""
    _reset_token_invalid_flag()
    openaire_adapter._cached_token = ""
    openaire_adapter._cached_token_exp = 0.0


class _LogSpy:
    """Einfacher Log-Spy: sammelt (level, event, kwargs)-Tupel."""

    def __init__(self) -> None:
        self.records: list[tuple[str, str, dict[str, Any]]] = []

    def _capture(self, level: str):
        def _log(event: str, **kwargs: Any) -> None:
            self.records.append((level, event, kwargs))
        return _log

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(openaire_adapter.logger, "warning", self._capture("warning"))
        monkeypatch.setattr(openaire_adapter.logger, "info", self._capture("info"))
        monkeypatch.setattr(openaire_adapter.logger, "debug", self._capture("debug"))

    def by_level(self, level: str) -> list[tuple[str, dict[str, Any]]]:
        return [(event, kwargs) for lvl, event, kwargs in self.records if lvl == level]

    def events(self) -> list[str]:
        return [event for _, event, _ in self.records]


def _make_status_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://api.openaire.eu/search/publications")
    response = httpx.Response(status, request=request)
    return httpx.HTTPStatusError(f"HTTP {status}", request=request, response=response)


@pytest.mark.asyncio
async def test_403_after_token_invalid_is_logged_as_debug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wenn `_token_invalid=True`, werden 403-Year-Errors auf debug geloggt."""
    spy = _LogSpy()
    spy.install(monkeypatch)

    # Flag direkt setzen (als ob vorher ein 400-Refresh-Fehler aufgetreten waere).
    openaire_adapter._token_invalid = True

    adapter = OpenAIREAdapter(access_token="dummy", refresh_token="")

    # Token-Refresh ueberspringen (ohne Refresh-Token passiert ohnehin nichts).
    async def _noop_ensure(self: OpenAIREAdapter) -> None:
        return None
    monkeypatch.setattr(OpenAIREAdapter, "_ensure_valid_token", _noop_ensure)

    # asyncio.gather simulieren: jedes Jahr liefert einen 403-Fehler.
    error_403 = _make_status_error(403)

    class _FailingClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> _FailingClient:
            return self

        async def __aexit__(self, *args: Any) -> None:
            return None

        async def get(self, *args: Any, **kwargs: Any) -> httpx.Response:
            raise error_403

    monkeypatch.setattr(openaire_adapter.httpx, "AsyncClient", _FailingClient)

    result = await adapter._fetch_from_api("quantum computing", 2015, 2025)

    # Fachlich: leere Liste (Fallback-Verhalten bleibt unveraendert).
    assert result == []

    # Log-Spam-Check: KEINE `openaire_jahr_fehlgeschlagen`- oder
    # `openaire_teilergebnis`-Warnings. Stattdessen auf debug-Level.
    warning_events = [ev for ev, _ in spy.by_level("warning")]
    debug_events = [ev for ev, _ in spy.by_level("debug")]

    assert "openaire_jahr_fehlgeschlagen" not in warning_events, (
        "Bei token_invalid=True duerfen Year-Errors NICHT als warning geloggt werden."
    )
    assert "openaire_teilergebnis" not in warning_events, (
        "Bei token_invalid=True darf kein `openaire_teilergebnis`-Warning entstehen."
    )
    assert "openaire_jahr_fehlgeschlagen" in debug_events, (
        "Year-Errors muessen bei token_invalid=True auf debug-Level geloggt werden."
    )
    assert "openaire_teilergebnis" in debug_events


@pytest.mark.asyncio
async def test_403_without_token_invalid_logs_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regressionsschutz: bei flagfreiem Zustand bleiben Warnings erhalten."""
    spy = _LogSpy()
    spy.install(monkeypatch)

    # Flag explizit zuruecksetzen (wird auch durch Fixture sichergestellt).
    _reset_token_invalid_flag()

    adapter = OpenAIREAdapter(access_token="dummy", refresh_token="")

    async def _noop_ensure(self: OpenAIREAdapter) -> None:
        return None
    monkeypatch.setattr(OpenAIREAdapter, "_ensure_valid_token", _noop_ensure)

    error_403 = _make_status_error(403)

    class _FailingClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> _FailingClient:
            return self

        async def __aexit__(self, *args: Any) -> None:
            return None

        async def get(self, *args: Any, **kwargs: Any) -> httpx.Response:
            raise error_403

    monkeypatch.setattr(openaire_adapter.httpx, "AsyncClient", _FailingClient)

    result = await adapter._fetch_from_api("quantum computing", 2020, 2022)

    assert result == []
    warning_events = [ev for ev, _ in spy.by_level("warning")]
    # Im Normalfall: Year-Errors sind Warnings.
    assert "openaire_jahr_fehlgeschlagen" in warning_events
    assert "openaire_teilergebnis" in warning_events


@pytest.mark.asyncio
async def test_refresh_400_sets_flag_and_logs_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bei 400 auf Refresh-Endpoint: genau eine Warnung + Flag gesetzt."""
    spy = _LogSpy()
    spy.install(monkeypatch)
    _reset_token_invalid_flag()

    error_400 = _make_status_error(400)

    class _RefreshFailingClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> _RefreshFailingClient:
            return self

        async def __aexit__(self, *args: Any) -> None:
            return None

        async def get(self, *args: Any, **kwargs: Any) -> httpx.Response:
            raise error_400

    monkeypatch.setattr(openaire_adapter.httpx, "AsyncClient", _RefreshFailingClient)

    # Abgelaufenes Token erzwingen, damit Refresh ausgeloest wird.
    adapter = OpenAIREAdapter(access_token="", refresh_token="some_refresh_token")
    await adapter._ensure_valid_token()

    assert openaire_adapter._token_invalid is True, (
        "Nach 4xx-Refresh-Fehler muss das Flag gesetzt sein."
    )
    # Genau EINE Warnung beim ersten Fehl-Refresh.
    warning_refresh = [
        (ev, kw) for ev, kw in spy.by_level("warning")
        if ev == "openaire_token_refresh_fehlgeschlagen"
    ]
    assert len(warning_refresh) == 1
    # Klare Konfigurationsfehler-Message enthaelt Hinweis auf DEPLOYMENT.md.
    assert "hinweis" in warning_refresh[0][1]
    assert "OPENAIRE_REFRESH_TOKEN" in warning_refresh[0][1]["hinweis"]

    # Zweiter Refresh-Versuch: KEINE weitere Warnung, Fehler geht auf debug.
    spy.records.clear()
    await adapter._ensure_valid_token()
    warning_refresh_2 = [
        ev for ev, _ in spy.by_level("warning")
        if ev == "openaire_token_refresh_fehlgeschlagen"
    ]
    debug_refresh_2 = [
        ev for ev, _ in spy.by_level("debug")
        if ev == "openaire_token_refresh_fehlgeschlagen"
    ]
    assert warning_refresh_2 == []
    assert debug_refresh_2 == [
        "openaire_token_refresh_fehlgeschlagen"
    ]
