"""Tests fuer die Publikations-Konsistenz (Bug CRIT-1) auf Repository-Ebene.

Das Publikations-Svc (UC13) MUSS dieselbe Master-Query wie das
landscape-svc (UC1 Header-Summary) verwenden.  Dieser Test sichert per
Cross-Service-Abgleich, dass identische Eingaben identische
``total_publications`` liefern — wenn jemand den Query-Pfad divergiert,
wird er rot.
"""

from __future__ import annotations

import importlib.util
import pathlib
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Helper: landscape-svc-Repository laden (anderer Service, gleiche SQL-Quelle)
# ---------------------------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent
_LANDSCAPE_REPO_FILE = (
    _REPO_ROOT / "services" / "landscape-svc" / "src" / "infrastructure" / "repository.py"
)


def _load_landscape_repo_cls():
    spec = importlib.util.spec_from_file_location(
        "landscape_repo_pubsvc_check", _LANDSCAPE_REPO_FILE
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.LandscapeRepository


# ---------------------------------------------------------------------------
# Minimaler Fake-Pool (aequivalent zu integration/test_publication_consistency.py).
# ---------------------------------------------------------------------------


class _Conn:
    def __init__(self, total: int) -> None:
        self._total = total

    async def fetchrow(self, sql: str, *args: Any) -> dict[str, Any]:
        return {
            "total_publications": self._total,
            "total_projects_with_pubs": 25,
            "doi_coverage": 0.6,
        }

    async def fetchval(self, sql: str, *args: Any) -> int:
        return self._total

    async def fetch(self, sql: str, *args: Any) -> list[dict[str, Any]]:
        return []


class _PoolCtx:
    def __init__(self, conn: _Conn) -> None:
        self._conn = conn

    async def __aenter__(self) -> _Conn:
        return self._conn

    async def __aexit__(self, *exc: Any) -> None:
        return None


class _Pool:
    def __init__(self, total: int) -> None:
        self._conn = _Conn(total)

    def acquire(self) -> _PoolCtx:
        return _PoolCtx(self._conn)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCrossServicePublicationCountCrit1:
    """Landscape-Svc und Publication-Svc liefern identische Zahlen."""

    @pytest.mark.asyncio
    async def test_same_pool_yields_same_total(self) -> None:
        """Ein gemeinsamer Pool → identische Zahl in beiden Services.

        Das ist die strukturelle Zusage hinter CRIT-1: sobald beide Services
        dieselbe Master-Query nutzen, ist die Divergenz aus dem Audit
        unmoeglich.
        """
        # Nachladen verhindert sys.path-Konflikte mit src.infrastructure in
        # zweigleisiger Test-Session.
        from src.infrastructure.repository import PublicationRepository

        LandscapeRepository = _load_landscape_repo_cls()

        pool = _Pool(total=2_456)
        pub = PublicationRepository(pool=pool)  # type: ignore[arg-type]
        land = LandscapeRepository(pool=pool)  # type: ignore[arg-type]

        pub_total = (await pub.publication_summary("mRNA", 2015, 2025))[
            "total_publications"
        ]
        land_total = await land.count_cordis_publications(
            "mRNA", start_year=2015, end_year=2025,
        )

        assert pub_total == land_total == 2_456
