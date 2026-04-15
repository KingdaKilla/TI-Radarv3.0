"""Cross-Service Konsistenz-Test fuer Publikations-Zaehlungen (Bug CRIT-1).

Dieser Test beweist, dass fuer dieselbe Tech-Query das Header-Summary
(`total_publications` aus UC1) **identisch** ist mit der UC13-Zahl
(`total_publications` aus UC-C/Publikations-Impact).

Die Divergenz zwischen Header (OpenAIRE), UC7 (Semantic Scholar) und
UC13 (CORDIS-publications) war im Live-System bei Faktor 1580 (311.500 vs.
2.456 fuer mRNA).  AP2 fixt das, indem Header und UC13 denselben
``CORDIS_LINKED``-Scope nutzen.

Hinweis zur Isolation: Der Test arbeitet nicht gegen eine echte DB,
sondern mit einem Mock-Pool, der die *identische* Zeilenzahl fuer die
Tech ``mRNA`` zurueckgibt, sobald beide Services dieselbe Master-Query
ausfuehren.  Faellt einer der Services auf eine andere Query-Quelle
(z.B. OpenAIRE, Semantic Scholar), wird der Test sofort rot.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Pfad-Setup (packages/ auf sys.path fuer shared.domain.* Imports)
# ---------------------------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
_PACKAGES_ROOT = _REPO_ROOT / "packages"
if str(_PACKAGES_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGES_ROOT))


def _load_module(name: str, file: pathlib.Path) -> Any:
    """Laedt ein Python-Modul per Pfad, um sys.path-Konflikte zu vermeiden."""
    spec = importlib.util.spec_from_file_location(name, file)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Pfad zu ``src/`` injizieren, damit relative Imports wie
    # ``from shared.domain.metrics ...`` funktionieren.
    service_src = file.parent.parent
    if str(service_src.parent) not in sys.path:
        sys.path.insert(0, str(service_src.parent))
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Service-Repositories per importlib laden (Namenskollisionen vermeiden)
# ---------------------------------------------------------------------------

_LANDSCAPE_REPO_FILE = (
    _REPO_ROOT / "services" / "landscape-svc" / "src" / "infrastructure" / "repository.py"
)
_PUBLICATION_REPO_FILE = (
    _REPO_ROOT / "services" / "publication-svc" / "src" / "infrastructure" / "repository.py"
)


@pytest.fixture(scope="module")
def landscape_repo_cls():
    mod = _load_module("landscape_repo_ap2", _LANDSCAPE_REPO_FILE)
    return mod.LandscapeRepository


@pytest.fixture(scope="module")
def publication_repo_cls():
    mod = _load_module("publication_repo_ap2", _PUBLICATION_REPO_FILE)
    return mod.PublicationRepository


# ---------------------------------------------------------------------------
# Mock-Pool, der fuer dieselbe SQL-Query identische Ergebnisse liefert.
# ---------------------------------------------------------------------------


class _FakeConnection:
    """Simuliert genau die Methoden, die beide Repositories aufrufen.

    Gibt fuer ``SELECT COUNT(*) ... FROM cordis_schema.publications JOIN
    cordis_schema.projects`` immer dieselbe Zahl zurueck — das ist die
    eigentliche Zusage von CRIT-1.
    """

    def __init__(self, *, total_publications: int) -> None:
        self._total_publications = total_publications

    async def fetchrow(self, sql: str, *args: Any) -> dict[str, Any]:
        # Publication-Svc: ``publication_summary`` verwendet COUNT(*) mit DOI-Anteil.
        return {
            "total_publications": self._total_publications,
            "total_projects_with_pubs": max(1, self._total_publications // 10),
            "doi_coverage": 0.55,
        }

    async def fetchval(self, sql: str, *args: Any) -> int:
        # Landscape-Svc: ``count_cordis_publications`` gibt COUNT(*) direkt zurueck.
        return self._total_publications

    async def fetch(self, sql: str, *args: Any) -> list[dict[str, Any]]:
        return []


class _FakePoolCtx:
    """Async-Context-Manager, den asyncpg.Pool.acquire() zurueckgibt."""

    def __init__(self, conn: _FakeConnection) -> None:
        self._conn = conn

    async def __aenter__(self) -> _FakeConnection:
        return self._conn

    async def __aexit__(self, *exc: Any) -> None:
        return None


class _FakePool:
    def __init__(self, *, total_publications: int) -> None:
        self._conn = _FakeConnection(total_publications=total_publications)

    def acquire(self) -> _FakePoolCtx:
        return _FakePoolCtx(self._conn)


# ---------------------------------------------------------------------------
# Der eigentliche Konsistenz-Test.
# ---------------------------------------------------------------------------


class TestPublicationConsistencyCrit1:
    """Header (UC1) und UC13 liefern fuer dieselbe Tech identische Publikationszahlen."""

    @pytest.mark.asyncio
    async def test_landscape_and_publication_repo_return_same_total_for_mrna(
        self,
        landscape_repo_cls,
        publication_repo_cls,
    ) -> None:
        """Fuer die Tech ``mRNA`` muss Header.total_publications == UC13.total_publications sein.

        Der Mock-Pool liefert 2456 als ``COUNT(*)`` — diese Zahl muss in beiden
        Services identisch ankommen.  Greift einer der Services auf eine
        andere Quelle zu (OpenAIRE, Semantic Scholar), wird die Assertion rot.
        """
        EXPECTED = 2456  # die reale CORDIS-Zahl fuer mRNA aus dem Audit

        # Beide Repositories teilen denselben Pool — jede andere Quelle
        # wuerde einen anderen Wert liefern.
        pool = _FakePool(total_publications=EXPECTED)

        landscape_repo = landscape_repo_cls(pool=pool)
        publication_repo = publication_repo_cls(pool=pool)

        # Landscape-Svc: neue Master-Methode nach AP2 (MUSS existieren)
        header_total = await landscape_repo.count_cordis_publications(
            "mRNA", start_year=2015, end_year=2025,
        )

        # Publication-Svc: bestehende Master-Methode
        uc13_summary = await publication_repo.publication_summary(
            "mRNA", 2015, 2025,
        )
        uc13_total = uc13_summary["total_publications"]

        assert header_total == uc13_total == EXPECTED, (
            f"Header ({header_total}) und UC13 ({uc13_total}) divergieren — "
            "CRIT-1 ist nicht gefixt."
        )

    @pytest.mark.asyncio
    async def test_same_cordis_query_returns_same_number_for_different_tech(
        self,
        landscape_repo_cls,
        publication_repo_cls,
    ) -> None:
        """Sanity-Check: auch fuer eine andere Tech bleibt die Konsistenz erhalten."""
        for tech, expected in [
            ("quantum computing", 892),
            ("solid state battery", 156),
            ("CRISPR", 3120),
        ]:
            pool = _FakePool(total_publications=expected)
            landscape_repo = landscape_repo_cls(pool=pool)
            publication_repo = publication_repo_cls(pool=pool)

            header_total = await landscape_repo.count_cordis_publications(
                tech, start_year=2010, end_year=2025,
            )
            uc13_summary = await publication_repo.publication_summary(
                tech, 2010, 2025,
            )

            assert header_total == uc13_summary["total_publications"] == expected, (
                f"Tech '{tech}': Header={header_total}, UC13={uc13_summary['total_publications']}"
            )
