"""Unit-Tests fuer LandscapeRepository: Patent-Zaehlung mit ALL_PATENTS-Scope.

Hintergrund (Bug CRIT-4): Der Header zeigt ``total_patents`` und muss
die ``ALL_PATENTS``-Semantik aus ``shared.domain.patent_definitions``
verwenden (alle Patente ungefiltert nach Kind-Code).
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any

import pytest

from shared.domain.patent_definitions import (
    APPLICATION_KIND_CODES,
    GRANT_KIND_CODES,
    PatentScope,
)
from src.infrastructure.repository import LandscapeRepository


# ---------------------------------------------------------------------------
# Mini-DB
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _P:
    year: int
    kind: str


# Gleich wie im Integrationstest: 10 Patente, 6 A*, 2 B*, 2 sonstige.
_DB: list[_P] = [
    _P(2020, "A1"), _P(2020, "A1"),
    _P(2021, "A2"), _P(2021, "A1"),
    _P(2022, "A1"), _P(2022, "A1"),
    _P(2023, "B1"), _P(2024, "B2"),
    _P(2024, "U"),  _P(2024, ""),
]


class _Conn:
    async def fetch(self, sql: str, *params: Any) -> list[dict[str, Any]]:
        start_year = params[1] if len(params) >= 2 and isinstance(params[1], int) else None
        end_year = params[2] if len(params) >= 3 and isinstance(params[2], int) else None
        pool = [p for p in _DB
                if (start_year is None or p.year >= start_year)
                and (end_year is None or p.year <= end_year)]

        if "GROUP BY p.publication_year" in sql and "FILTER" not in sql:
            counts: dict[int, int] = {}
            for p in pool:
                counts[p.year] = counts.get(p.year, 0) + 1
            return [{"year": y, "count": c} for y, c in sorted(counts.items())]
        return []

    async def fetchval(self, sql: str, *params: Any) -> Any:
        return None


class _Ctx:
    def __init__(self, c: _Conn) -> None:
        self._c = c

    async def __aenter__(self) -> _Conn:
        return self._c

    async def __aexit__(self, *a: Any) -> None:
        return None


class _Pool:
    def acquire(self) -> _Ctx:
        return _Ctx(_Conn())


@pytest.fixture
def repo() -> LandscapeRepository:
    return LandscapeRepository(pool=_Pool())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAllPatentsScope:
    """Header-`total_patents` muss ALL_PATENTS-Semantik haben."""

    @pytest.mark.asyncio
    async def test_counts_all_patents_including_unknown_kinds(
        self, repo: LandscapeRepository,
    ) -> None:
        """Die Query darf NICHT nach Kind-Code filtern."""
        rows = await repo.count_patents_by_year(
            "quantum computing", start_year=2020, end_year=2024,
        )
        total = sum(r.count for r in rows)
        assert total == 10, (
            f"Erwartet 10 (alle Patente inkl. U-Code und leerem Kind), "
            f"bekommen {total}. Der Header-Scope ALL_PATENTS darf nicht "
            f"auf A*/B* eingeschraenkt werden."
        )

    def test_query_has_no_kind_code_filter(self, repo: LandscapeRepository) -> None:
        """Statisch: die Query enthaelt kein ``p.kind IN (...)`` oder FILTER."""
        src = inspect.getsource(repo.count_patents_by_year)
        assert "p.kind IN" not in src and "p.kind = ANY" not in src, (
            "count_patents_by_year darf keinen Kind-Code-Filter haben "
            "(Scope ALL_PATENTS)."
        )
        assert "FILTER (WHERE p.kind" not in src, (
            "count_patents_by_year darf keinen COUNT(*) FILTER auf p.kind haben."
        )

    def test_docstring_documents_all_patents_scope(
        self, repo: LandscapeRepository,
    ) -> None:
        """Der Docstring sollte den Scope ALL_PATENTS explizit dokumentieren,
        damit bei zukuenftigen Aenderungen die Semantik nicht versehentlich
        geaendert wird.
        """
        doc = (repo.count_patents_by_year.__doc__ or "") + "\n"
        # Modul-Docstring ebenfalls heranziehen (fuer Sammel-Dokumentation)
        module = inspect.getmodule(repo.count_patents_by_year)
        mod_src = inspect.getsource(module) if module else ""
        has_hint = (
            "ALL_PATENTS" in doc
            or "ALL_PATENTS" in mod_src
            or "PatentScope" in mod_src
        )
        assert has_hint, (
            "count_patents_by_year muss in seiner Docstring (oder im Modul) "
            "auf PatentScope.ALL_PATENTS verweisen."
        )


class TestPlausibilityAgainstUc12:
    """Cross-Check-Regel (Integration, aber lokal simuliert):
    Header >= UC12.apps + UC12.grants.
    """

    @pytest.mark.asyncio
    async def test_header_is_upper_bound(self, repo: LandscapeRepository) -> None:
        rows = await repo.count_patents_by_year(
            "quantum computing", start_year=2020, end_year=2024,
        )
        header_total = sum(r.count for r in rows)

        expected_apps = sum(1 for p in _DB if p.kind in APPLICATION_KIND_CODES)
        expected_grants = sum(1 for p in _DB if p.kind in GRANT_KIND_CODES)

        assert header_total >= expected_apps + expected_grants
