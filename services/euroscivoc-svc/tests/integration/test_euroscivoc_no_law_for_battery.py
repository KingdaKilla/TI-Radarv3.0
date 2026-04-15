"""Integrationstest fuer AP4 · CRIT-2: Query-Relevanz-Filter.

Stellt sicher, dass die SQL-Query der discipline_distribution einen
ts_rank_cd-Threshold enthaelt. Das soll ausschliessen, dass bei einer
Mehrwort-Query wie "solid state battery" Projekte als relevant zaehlen,
die nur einzelne Tokens matchen (z. B. "battery law").

Der Test ueberprueft die SQL-String-Struktur, da ohne Postgres keine
echte Query gegen die Produktion laufen kann.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from src.infrastructure.repository import EuroSciVocRepository


class _FakePool:
    """Poolsimulator, der die SQL-String aufzeichnet, die an conn.fetch
    uebergeben wird, ohne sie tatsaechlich auszufuehren."""

    def __init__(self, captured_rows: list[dict[str, Any]] | None = None) -> None:
        self.captured_sql: str | None = None
        self.captured_params: tuple[Any, ...] = ()
        self._rows = captured_rows or []

    def acquire(self) -> "_FakeConn":  # noqa: D401
        return _FakeConn(self)


class _FakeConn:
    def __init__(self, pool: _FakePool) -> None:
        self._pool = pool

    async def __aenter__(self) -> "_FakeConn":
        return self

    async def __aexit__(self, *_: Any) -> None:
        return None

    async def fetch(self, sql: str, *params: Any) -> list[dict[str, Any]]:
        self._pool.captured_sql = sql
        self._pool.captured_params = params
        return self._pool._rows

    async def fetchval(self, sql: str, *params: Any) -> Any:  # pragma: no cover
        self._pool.captured_sql = sql
        self._pool.captured_params = params
        return 0


def test_discipline_distribution_uses_ts_rank_threshold() -> None:
    """Die Query muss ts_rank_cd fuer Score-Filtering enthalten."""
    pool = _FakePool()
    repo = EuroSciVocRepository(pool)  # type: ignore[arg-type]

    asyncio.run(repo.discipline_distribution("solid state battery"))

    assert pool.captured_sql is not None
    sql = pool.captured_sql.lower()

    # Muss ts_rank_cd mit Threshold enthalten, um Token-Split-Matches zu
    # eliminieren (z. B. "battery law" bei Suche nach "solid state battery").
    assert "ts_rank_cd" in sql, (
        "SQL muss ts_rank_cd fuer Relevanz-Filter verwenden, um fachliche "
        "Fehlzuordnungen wie 'law' -> 'solid state battery' zu vermeiden."
    )

    # Prueft, dass ein numerischer Schwellenwert verwendet wird (>= 0.x).
    # Die innere Parameter-Liste von ts_rank_cd darf selbst Klammern
    # (z. B. plainto_tsquery(...)) enthalten, daher nicht greedy und keine
    # Zeichen-Klassen-basierte Nicht-Klammer-Match-Heuristik.
    threshold_match = re.search(
        r"ts_rank_cd\(.+?\)\)\s*>=\s*([0-9.]+)", sql, re.DOTALL
    )
    assert threshold_match is not None, (
        f"Die Query muss einen Schwellenwert-Vergleich (ts_rank_cd(...) >= X) "
        f"haben. SQL war:\n{sql}"
    )
    threshold = float(threshold_match.group(1))
    assert threshold > 0.0, "Threshold muss groesser als 0 sein."


def test_total_mapped_projects_also_uses_rank_threshold() -> None:
    """Auch die Hilfsquery fuer Gesamtzahlen muss konsistent rank-gefiltert sein,
    sonst divergieren total_mapped und discipline_distribution.

    Das verhindert, dass 'Coverage' als Quotient zweier unterschiedlich
    gefilterter Populationen berechnet wird.
    """
    pool = _FakePool()
    repo = EuroSciVocRepository(pool)  # type: ignore[arg-type]

    asyncio.run(repo.total_mapped_projects("solid state battery"))

    assert pool.captured_sql is not None
    sql = pool.captured_sql.lower()
    assert "ts_rank_cd" in sql
