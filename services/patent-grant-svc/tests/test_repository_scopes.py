"""Unit-Tests fuer PatentGrantRepository: Scope-Trennung (Bug CRIT-4).

Prueft, dass die Kind-Code-Listen aus ``shared.domain.patent_definitions``
stammen, nicht aus lokalen Duplikaten, und dass die Plausibilitaetsregel
``ALL_PATENTS >= APPLICATIONS_ONLY + GRANTS_ONLY`` durch die Query-Logik
garantiert wird.
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
from src.infrastructure.repository import PatentGrantRepository


# ---------------------------------------------------------------------------
# Dummy-Pool fuer Unit-Level-Tests
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Patent:
    publication_year: int
    kind: str


_MINI_DB: list[_Patent] = [
    _Patent(2020, "A1"),
    _Patent(2020, "A1"),
    _Patent(2021, "A2"),
    _Patent(2021, "A1"),
    _Patent(2022, "A1"),
    _Patent(2022, "A1"),
    _Patent(2023, "B1"),
    _Patent(2024, "B2"),
    _Patent(2024, "U"),
    _Patent(2024, ""),
]


class _DummyConn:
    async def fetch(self, sql: str, *params: Any) -> list[dict[str, Any]]:
        start_year = params[1] if len(params) >= 2 and isinstance(params[1], int) else None
        end_year = params[2] if len(params) >= 3 and isinstance(params[2], int) else None

        pool = [
            p for p in _MINI_DB
            if (start_year is None or p.publication_year >= start_year)
            and (end_year is None or p.publication_year <= end_year)
        ]

        # grant_rate_by_year
        if "application_count" in sql and "grant_count" in sql and "GROUP BY p.publication_year" in sql:
            by_year: dict[int, dict[str, int]] = {}
            for p in pool:
                cell = by_year.setdefault(p.publication_year, {"a": 0, "b": 0})
                if p.kind in APPLICATION_KIND_CODES:
                    cell["a"] += 1
                elif p.kind in GRANT_KIND_CODES:
                    cell["b"] += 1
            return [
                {"year": y, "application_count": c["a"], "grant_count": c["b"]}
                for y, c in sorted(by_year.items())
            ]

        # total_patent_counts (neue Methode) — erwartet Summary-Row zurueck.
        if "total_applications" in sql and "total_grants" in sql and "total_all" in sql:
            total_all = len(pool)
            apps = sum(1 for p in pool if p.kind in APPLICATION_KIND_CODES)
            grants = sum(1 for p in pool if p.kind in GRANT_KIND_CODES)
            return [{
                "total_all": total_all,
                "total_applications": apps,
                "total_grants": grants,
            }]

        return []

    async def fetchval(self, sql: str, *params: Any) -> Any:
        return None

    async def fetchrow(self, sql: str, *params: Any) -> dict[str, Any] | None:
        rows = await self.fetch(sql, *params)
        return rows[0] if rows else None


class _Ctx:
    def __init__(self, conn: _DummyConn) -> None:
        self._conn = conn

    async def __aenter__(self) -> _DummyConn:
        return self._conn

    async def __aexit__(self, *a: Any) -> None:
        return None


class _DummyPool:
    def acquire(self) -> _Ctx:
        return _Ctx(_DummyConn())


@pytest.fixture
def repo() -> PatentGrantRepository:
    return PatentGrantRepository(pool=_DummyPool())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestKindCodeSource:
    """Prueft, dass Kind-Code-Listen aus shared.domain kommen, nicht lokal."""

    def test_query_references_shared_constants(self, repo: PatentGrantRepository) -> None:
        """``grant_rate_by_year`` soll Shared-Konstanten verwenden.

        Akzeptanzkriterium: entweder enthaelt der Source-Code einen Import von
        ``APPLICATION_KIND_CODES`` / ``GRANT_KIND_CODES`` aus
        ``shared.domain.patent_definitions``, oder die SQL-Query enthaelt
        vollstaendig dieselben Codes wie die Shared-Definition.
        """
        module = inspect.getmodule(repo.grant_rate_by_year)
        assert module is not None
        module_src = inspect.getsource(module)

        uses_shared_import = (
            "shared.domain.patent_definitions" in module_src
            and (
                "APPLICATION_KIND_CODES" in module_src
                or "GRANT_KIND_CODES" in module_src
            )
        )
        if uses_shared_import:
            return

        # Fallback: alle Codes muessen explizit in der Query stehen
        method_src = inspect.getsource(repo.grant_rate_by_year)
        missing_apps = [c for c in APPLICATION_KIND_CODES if f"'{c}'" not in method_src]
        missing_grants = [c for c in GRANT_KIND_CODES if f"'{c}'" not in method_src]
        assert not missing_apps, f"Application-Codes fehlen in Query: {missing_apps}"
        assert not missing_grants, f"Grant-Codes fehlen in Query: {missing_grants}"


class TestGrantRateByYearAggregation:
    """Prueft die Semantik der Aggregation gegen den Mini-Datensatz."""

    @pytest.mark.asyncio
    async def test_applications_count_matches_a_codes(
        self, repo: PatentGrantRepository,
    ) -> None:
        rows = await repo.grant_rate_by_year(
            "quantum", start_year=2020, end_year=2024,
        )
        total_apps = sum(r["application_count"] for r in rows)
        assert total_apps == 6  # sechs A*-Patente im Mini-Datensatz

    @pytest.mark.asyncio
    async def test_grants_count_matches_b_codes(
        self, repo: PatentGrantRepository,
    ) -> None:
        rows = await repo.grant_rate_by_year(
            "quantum", start_year=2020, end_year=2024,
        )
        total_grants = sum(r["grant_count"] for r in rows)
        assert total_grants == 2  # B1 + B2

    @pytest.mark.asyncio
    async def test_unknown_kind_not_counted(
        self, repo: PatentGrantRepository,
    ) -> None:
        """U-Codes und leere Kind-Codes duerfen weder als App noch als Grant zaehlen."""
        rows = await repo.grant_rate_by_year(
            "quantum", start_year=2020, end_year=2024,
        )
        total = sum(r["application_count"] + r["grant_count"] for r in rows)
        assert total == 8  # 6 + 2, NICHT 10


class TestTotalPatentCounts:
    """Prueft die neue Methode ``total_patent_counts`` (alle drei Scopes)."""

    @pytest.mark.asyncio
    async def test_method_exists(self, repo: PatentGrantRepository) -> None:
        assert hasattr(repo, "total_patent_counts"), (
            "PatentGrantRepository muss eine Methode total_patent_counts(...)"
            " bereitstellen, die alle drei Scopes (ALL, APPLICATIONS, GRANTS)"
            " in einer einzigen Query liefert."
        )

    @pytest.mark.asyncio
    async def test_returns_all_three_scopes(self, repo: PatentGrantRepository) -> None:
        result = await repo.total_patent_counts(  # type: ignore[attr-defined]
            "quantum", start_year=2020, end_year=2024,
        )
        assert isinstance(result, dict)
        assert set(result.keys()) >= {
            PatentScope.ALL_PATENTS.value,
            PatentScope.APPLICATIONS_ONLY.value,
            PatentScope.GRANTS_ONLY.value,
        }

    @pytest.mark.asyncio
    async def test_plausibility_all_geq_apps_plus_grants(
        self, repo: PatentGrantRepository,
    ) -> None:
        result = await repo.total_patent_counts(  # type: ignore[attr-defined]
            "quantum", start_year=2020, end_year=2024,
        )
        total_all = result[PatentScope.ALL_PATENTS.value]
        apps = result[PatentScope.APPLICATIONS_ONLY.value]
        grants = result[PatentScope.GRANTS_ONLY.value]
        assert total_all >= apps + grants, (
            f"Plausibilitaet verletzt: all={total_all}, apps={apps}, grants={grants}"
        )

    @pytest.mark.asyncio
    async def test_matches_expected_values(self, repo: PatentGrantRepository) -> None:
        result = await repo.total_patent_counts(  # type: ignore[attr-defined]
            "quantum", start_year=2020, end_year=2024,
        )
        assert result[PatentScope.ALL_PATENTS.value] == 10
        assert result[PatentScope.APPLICATIONS_ONLY.value] == 6
        assert result[PatentScope.GRANTS_ONLY.value] == 2
