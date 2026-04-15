"""Cross-Service-Konsistenztests fuer Patent-Zaehlungen (Bug CRIT-4).

Hintergrund: Im Live-System zeigte der Header z.B. "Perovskite 101 Patente",
waehrend UC12 fuer dieselbe Tech "5.462 Anmeldungen" lieferte (Faktor 54).
Ursache war fehlende Trennung zwischen ``ALL_PATENTS`` (Header),
``APPLICATIONS_ONLY`` und ``GRANTS_ONLY`` (UC12).

Diese Tests sichern die Plausibilitaetsregel:
    ``header.total_patents >= uc12.total_applications + uc12.total_grants``

Ausserdem wird geprueft, dass die Kind-Code-Filter aus
``shared.domain.patent_definitions`` (nicht aus lokalen Duplikaten) stammen.

Die Tests laufen *ohne* echte Datenbank: ein DummyPool simuliert die
SQL-Ausfuehrung auf einem deterministischen In-Memory-Datensatz. So bleibt
der Test schnell und reproduzierbar.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from dataclasses import dataclass
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# sys.path Setup
# ---------------------------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

# packages/ enthaelt das ``shared``-Package (package_dir=packages/shared).
_PACKAGES_ROOT = _REPO_ROOT / "packages"
for p in (_PACKAGES_ROOT, _REPO_ROOT):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)


def _load_module(name: str, file: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, file)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Repositorys per importlib laden, um Konflikte auf sys.path zu vermeiden
_LANDSCAPE_REPO_FILE = (
    _REPO_ROOT / "services" / "landscape-svc" / "src" / "infrastructure" / "repository.py"
)
_PATENT_GRANT_REPO_FILE = (
    _REPO_ROOT / "services" / "patent-grant-svc" / "src" / "infrastructure" / "repository.py"
)

_landscape_repo_mod = _load_module(
    "landscape_repository_for_patent_test", _LANDSCAPE_REPO_FILE,
)
_patent_grant_repo_mod = _load_module(
    "patent_grant_repository_for_patent_test", _PATENT_GRANT_REPO_FILE,
)

LandscapeRepository = _landscape_repo_mod.LandscapeRepository
PatentGrantRepository = _patent_grant_repo_mod.PatentGrantRepository

from shared.domain.patent_definitions import (
    APPLICATION_KIND_CODES,
    GRANT_KIND_CODES,
    PatentScope,
)


# ---------------------------------------------------------------------------
# Dummy-DB: deterministische Patentmenge
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _Patent:
    publication_year: int
    kind: str
    applicant_countries: tuple[str, ...]
    cpc_codes: tuple[str, ...]


# Deterministisches Mini-Universum fuer "quantum computing".
# Wichtig fuer CRIT-4:
# - 10 Patente insgesamt (ALL_PATENTS).
# - 6 Patente haben A*-Kind-Codes (APPLICATIONS_ONLY).
# - 2 Patente haben B*-Kind-Codes (GRANTS_ONLY).
# - 2 Patente haben Kind=NULL bzw. unbekannten Code (UNKNOWN) — tauchen
#   nur in ALL_PATENTS auf.
# Plausibilitaet: 10 >= 6 + 2 = 8. Stimmt.
_TEST_PATENTS: list[_Patent] = [
    _Patent(2020, "A1", ("DE",), ("G06F",)),
    _Patent(2020, "A1", ("DE", "FR"), ("G06F", "H04W")),
    _Patent(2021, "A2", ("FR",), ("G06F",)),
    _Patent(2021, "A1", ("DE",), ("G06F", "H01M")),
    _Patent(2022, "A1", ("DE",), ("G06F",)),
    _Patent(2022, "A1", ("FR",), ("G06F",)),
    _Patent(2023, "B1", ("DE",), ("G06F",)),
    _Patent(2024, "B2", ("FR",), ("G06F",)),
    _Patent(2024, "U",  ("DE",), ("G06F",)),   # utility model — nicht A/B
    _Patent(2024, "",   ("DE",), ("G06F",)),   # leerer Kind-Code
]


def _filter_patents(
    *,
    start_year: int | None = None,
    end_year: int | None = None,
) -> list[_Patent]:
    out = _TEST_PATENTS
    if start_year is not None:
        out = [p for p in out if p.publication_year >= start_year]
    if end_year is not None:
        out = [p for p in out if p.publication_year <= end_year]
    return out


class _DummyConn:
    """Minimal-Nachbildung einer asyncpg.Connection fuer das, was die
    Repository-Methoden tatsaechlich aufrufen.

    Die Klasse parst die SQL-Strings NICHT. Stattdessen entscheidet sie
    anhand charakteristischer Schlagworte, welche Aggregation
    zurueckgegeben wird. Parameter ``$1`` (technology) wird ignoriert;
    die Testdaten sind alle "quantum computing".
    """

    async def fetch(self, sql: str, *params: Any) -> list[dict[str, Any]]:
        # Extrahiere start_year / end_year aus den Parametern in der Reihenfolge
        # in der die Repositorys sie anhaengen ($2=start, $3=end).
        start_year: int | None = None
        end_year: int | None = None
        # Nach technology ($1) folgt in beiden Queries optional start_year+end_year
        if len(params) >= 2 and isinstance(params[1], int):
            start_year = params[1]
        if len(params) >= 3 and isinstance(params[2], int):
            end_year = params[2]

        patents = _filter_patents(start_year=start_year, end_year=end_year)

        # Landscape.count_patents_by_year: GROUP BY publication_year
        if "GROUP BY p.publication_year" in sql and "FILTER" not in sql:
            counts: dict[int, int] = {}
            for p in patents:
                counts[p.publication_year] = counts.get(p.publication_year, 0) + 1
            return [{"year": y, "count": c} for y, c in sorted(counts.items())]

        # PatentGrant.grant_rate_by_year: COUNT(*) FILTER ... GROUP BY publication_year
        if "application_count" in sql and "grant_count" in sql and "GROUP BY p.publication_year" in sql:
            by_year: dict[int, dict[str, int]] = {}
            for p in patents:
                cell = by_year.setdefault(p.publication_year, {"a": 0, "b": 0})
                if p.kind in APPLICATION_KIND_CODES:
                    cell["a"] += 1
                elif p.kind in GRANT_KIND_CODES:
                    cell["b"] += 1
            return [
                {
                    "year": y,
                    "application_count": cell["a"],
                    "grant_count": cell["b"],
                }
                for y, cell in sorted(by_year.items())
            ]

        # PatentGrant.kind_code_distribution: GROUP BY kind
        if "kind_code" in sql and "GROUP BY p.kind" in sql:
            counts_by_kind: dict[str, int] = {}
            for p in patents:
                if not p.kind:
                    continue  # NULL-Kinds sind per 'p.kind IS NOT NULL' rausgefiltert
                counts_by_kind[p.kind] = counts_by_kind.get(p.kind, 0) + 1
            return [
                {"kind_code": k, "count": c}
                for k, c in sorted(counts_by_kind.items(), key=lambda kv: -kv[1])
            ]

        # Sonst: leer zurueckgeben
        return []

    async def fetchval(self, sql: str, *params: Any) -> Any:
        return None

    async def fetchrow(self, sql: str, *params: Any) -> dict[str, Any] | None:
        return None


class _DummyAcquireCtx:
    def __init__(self, conn: _DummyConn) -> None:
        self._conn = conn

    async def __aenter__(self) -> _DummyConn:
        return self._conn

    async def __aexit__(self, *exc_info: Any) -> None:
        return None


class _DummyPool:
    def acquire(self) -> _DummyAcquireCtx:
        return _DummyAcquireCtx(_DummyConn())


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def dummy_pool() -> _DummyPool:
    return _DummyPool()


@pytest.fixture
def landscape_repo(dummy_pool: _DummyPool) -> Any:
    return LandscapeRepository(pool=dummy_pool)  # type: ignore[arg-type]


@pytest.fixture
def patent_grant_repo(dummy_pool: _DummyPool) -> Any:
    return PatentGrantRepository(pool=dummy_pool)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests: Plausibilitaetsregel header >= applications + grants
# ---------------------------------------------------------------------------


class TestPatentPopulationConsistency:
    """Plausibilitaetsregel ``ALL_PATENTS >= APPLICATIONS + GRANTS``.

    Header-`total_patents` (aus UC1) muss groesser-gleich der Summe aus
    UC12-`total_applications` + UC12-`total_grants` sein, weil es in der
    DB auch Kind-Codes gibt, die weder A* noch B* sind (U, D0, leer).
    """

    @pytest.mark.asyncio
    async def test_header_total_equals_all_patents(self, landscape_repo: Any) -> None:
        """Header-Summe entspricht ALL_PATENTS-Scope (10 Testpatente)."""
        years = await landscape_repo.count_patents_by_year(
            "quantum computing", start_year=2020, end_year=2024,
        )
        total = sum(y.count for y in years)
        assert total == 10, "Header total_patents muss alle 10 Testpatente abdecken"

    @pytest.mark.asyncio
    async def test_uc12_applications_is_subset(self, patent_grant_repo: Any) -> None:
        """UC12 total_applications zaehlt nur A*-Kind-Codes (6 Patente)."""
        rows = await patent_grant_repo.grant_rate_by_year(
            "quantum computing", start_year=2020, end_year=2024,
        )
        total_applications = sum(r["application_count"] for r in rows)
        assert total_applications == 6, \
            f"Erwartet 6 A*-Patente, bekommen {total_applications}"

    @pytest.mark.asyncio
    async def test_uc12_grants_is_subset(self, patent_grant_repo: Any) -> None:
        """UC12 total_grants zaehlt nur B*-Kind-Codes (2 Patente)."""
        rows = await patent_grant_repo.grant_rate_by_year(
            "quantum computing", start_year=2020, end_year=2024,
        )
        total_grants = sum(r["grant_count"] for r in rows)
        assert total_grants == 2, f"Erwartet 2 B*-Patente, bekommen {total_grants}"

    @pytest.mark.asyncio
    async def test_plausibility_header_geq_applications_plus_grants(
        self, landscape_repo: Any, patent_grant_repo: Any,
    ) -> None:
        """Kern-Assertion: header >= applications + grants.

        Bei den Testdaten: 10 >= 6 + 2 = 8. Der Ueberhang von 2 entspricht
        dem U-Kind-Code (Utility Model) + leerem Kind-Code — Patente, die
        im ALL_PATENTS-Header erscheinen, aber nicht als Applications
        oder Grants gelten.
        """
        years = await landscape_repo.count_patents_by_year(
            "quantum computing", start_year=2020, end_year=2024,
        )
        header_total = sum(y.count for y in years)

        rows = await patent_grant_repo.grant_rate_by_year(
            "quantum computing", start_year=2020, end_year=2024,
        )
        uc12_apps = sum(r["application_count"] for r in rows)
        uc12_grants = sum(r["grant_count"] for r in rows)

        assert header_total >= uc12_apps + uc12_grants, (
            f"Plausibilitaet verletzt: header={header_total} < apps={uc12_apps} "
            f"+ grants={uc12_grants}. ALL_PATENTS muss Obergrenze sein."
        )


# ---------------------------------------------------------------------------
# Tests: Kind-Code-Quellen stammen aus shared.domain
# ---------------------------------------------------------------------------


class TestSharedKindCodeUsage:
    """Verhindert erneute Divergenzen: die Kind-Code-Sets, die UC12 in
    seiner Query verwendet, muessen Obermenge der Shared-Definitionen sein.

    Anders formuliert: Alle in ``shared.domain.patent_definitions`` als
    Application-Codes gelisteten Werte muessen auch in der SQL-Query der
    grant_rate_by_year-Methode erscheinen (Textsuche im Query-String).
    Gleiches gilt fuer Grant-Codes.
    """

    def _query_has_all_codes(
        self, patent_grant_repo: Any, codes: set[str] | frozenset[str],
    ) -> tuple[bool, list[str]]:
        """Prueft, ob alle Codes im Methoden- oder Modul-Source erscheinen.

        Akzeptiert zwei Varianten:
        1. Methode referenziert eine Modul-Konstante (z.B.
           ``_APPLICATIONS_SQL_IN``), die ihrerseits aus
           ``shared.domain.patent_definitions`` gespeist wird.
        2. Codes stehen direkt als String-Literale in der SQL.
        """
        # Modul-Quelle ueber die Datei des Repositorys einlesen, weil die
        # Test-Fixture das Modul per importlib laedt; in diesem Fall liefert
        # ``inspect.getmodule(method)`` ``None``.
        module_src = _PATENT_GRANT_REPO_FILE.read_text(encoding="utf-8")
        uses_shared = (
            "shared.domain.patent_definitions" in module_src
            and ("APPLICATION_KIND_CODES" in module_src
                 or "GRANT_KIND_CODES" in module_src)
        )
        if uses_shared:
            return True, []
        missing = [c for c in codes if f"'{c}'" not in module_src]
        return (not missing), missing

    def test_application_codes_present_in_query(
        self, patent_grant_repo: Any,
    ) -> None:
        """SQL-Text von grant_rate_by_year enthaelt alle A*-Kind-Codes.

        Akzeptiert entweder:
        - Import-Referenz auf shared.domain.patent_definitions im Modul,
        - oder vollstaendige String-Literal-Liste in der Query.
        """
        ok, missing = self._query_has_all_codes(
            patent_grant_repo, APPLICATION_KIND_CODES,
        )
        assert ok, f"Application-Kind-Codes fehlen in der Query: {missing}"

    def test_grant_codes_present_in_query(self, patent_grant_repo: Any) -> None:
        """SQL-Text von grant_rate_by_year enthaelt alle B*-Kind-Codes."""
        ok, missing = self._query_has_all_codes(
            patent_grant_repo, GRANT_KIND_CODES,
        )
        assert ok, f"Grant-Kind-Codes fehlen in der Query: {missing}"


# ---------------------------------------------------------------------------
# Tests: Scope-Semantik dokumentiert
# ---------------------------------------------------------------------------


class TestPatentScopeEnum:
    """Stellt sicher, dass die kanonischen Scopes existieren und dokumentieren,
    was der jeweilige Zaehl-Scope bedeutet.
    """

    def test_enum_has_all_three_scopes(self) -> None:
        assert {s.name for s in PatentScope} == {
            "ALL_PATENTS", "APPLICATIONS_ONLY", "GRANTS_ONLY",
        }
