"""Unit-Tests fuer EuroSciVocServicer (AP4 · CRIT-2).

Testet die Service-Ebene mit einem gemockten Repository:
- Shannon-Index wird nur ueber FIELD-Level-Kategorien berechnet.
- Bei 1 Projekt mit 3 Sub-Disziplinen unter 1 Feld muss active_fields = 1
  UND shannon_index = 0 sein.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from src.service import EuroSciVocServicer


# ---------------------------------------------------------------------------
# Fake-Repository
# ---------------------------------------------------------------------------


class _FakeRepo:
    """Stellt deterministische Antworten fuer die 5 Repository-Queries bereit."""

    def __init__(
        self,
        *,
        disciplines: list[dict[str, Any]],
        trend: list[dict[str, Any]] | None = None,
        links: list[dict[str, Any]] | None = None,
        total_mapped: int = 0,
        total_projects: int = 0,
    ) -> None:
        self._disciplines = disciplines
        self._trend = trend or []
        self._links = links or []
        self._total_mapped = total_mapped
        self._total_projects = total_projects
        # Aufzeichnung der kwargs fuer Konsistenz-Asserts (MIN-10).
        self.total_mapped_calls: list[dict[str, Any]] = []
        self.total_projects_calls: list[dict[str, Any]] = []
        self.discipline_distribution_calls: list[dict[str, Any]] = []

    async def discipline_distribution(self, technology: str, **kwargs: Any) -> list[dict[str, Any]]:
        self.discipline_distribution_calls.append({"technology": technology, **kwargs})
        return self._disciplines

    async def discipline_trend(self, technology: str, **_: Any) -> list[dict[str, Any]]:
        return self._trend

    async def cross_disciplinary_links(self, technology: str, **_: Any) -> list[dict[str, Any]]:
        return self._links

    async def total_mapped_projects(self, technology: str, **kwargs: Any) -> int:
        self.total_mapped_calls.append({"technology": technology, **kwargs})
        return self._total_mapped

    async def total_projects(self, technology: str, **kwargs: Any) -> int:
        self.total_projects_calls.append({"technology": technology, **kwargs})
        return self._total_projects


def _make_servicer(repo: _FakeRepo) -> EuroSciVocServicer:
    """Erstellt einen EuroSciVocServicer und ersetzt sein Repo durch `repo`.

    Umgeht die asyncpg.Pool-Konstruktor-Signatur.
    """
    servicer = EuroSciVocServicer.__new__(EuroSciVocServicer)  # type: ignore[call-arg]
    servicer._pool = None  # type: ignore[attr-defined]
    servicer._settings = SimpleNamespace()  # type: ignore[attr-defined]
    servicer._repo = repo  # type: ignore[attr-defined]
    return servicer


def _build_request(technology: str) -> SimpleNamespace:
    return SimpleNamespace(
        technology=technology,
        request_id="test-001",
        time_range=SimpleNamespace(start_year=2020, end_year=2024),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestShannonBasedOnFieldLevelOnly:
    """Shannon-Index darf nur ueber FIELD-Level-Kategorien berechnet werden,
    damit er konsistent mit `active_fields` ist.
    """

    @pytest.mark.asyncio
    async def test_one_field_with_three_subdisciplines_shannon_zero(self) -> None:
        """CRIT-2: Ein Feld mit 3 Sub-Disziplinen darf nicht Shannon > 0 liefern."""
        disciplines = [
            # 1 FIELD, dazu 3 Sub-Disziplinen (Level 2 / SUBFIELD)
            {"id": "f1", "label": "natural sciences", "level": "FIELD", "parent_id": "", "project_count": 1, "share": 1.0},
            {"id": "s1", "label": "chemistry", "level": "SUBFIELD", "parent_id": "f1", "project_count": 1, "share": 1.0},
            {"id": "s2", "label": "physics", "level": "SUBFIELD", "parent_id": "f1", "project_count": 1, "share": 1.0},
            {"id": "s3", "label": "mathematics", "level": "SUBFIELD", "parent_id": "f1", "project_count": 1, "share": 1.0},
        ]
        repo = _FakeRepo(disciplines=disciplines, total_mapped=1, total_projects=1)
        servicer = _make_servicer(repo)

        response = await servicer.AnalyzeEuroSciVoc(_build_request("mrna"), context=None)

        inter = response["interdisciplinarity"]
        assert inter["active_fields"] == 1
        assert inter["shannon_index"] == 0.0, (
            f"Shannon bei 1 Feld muss 0 sein, ist aber {inter['shannon_index']}"
        )
        assert inter["is_interdisciplinary"] is False

    @pytest.mark.asyncio
    async def test_two_fields_shannon_positive(self) -> None:
        """Zwei Felder mit gleicher Verteilung -> Shannon > 0."""
        disciplines = [
            {"id": "f1", "label": "natural sciences", "level": "FIELD", "parent_id": "", "project_count": 5, "share": 0.5},
            {"id": "f2", "label": "engineering", "level": "FIELD", "parent_id": "", "project_count": 5, "share": 0.5},
        ]
        repo = _FakeRepo(disciplines=disciplines, total_mapped=10, total_projects=10)
        servicer = _make_servicer(repo)

        response = await servicer.AnalyzeEuroSciVoc(_build_request("pqc"), context=None)

        inter = response["interdisciplinarity"]
        assert inter["active_fields"] == 2
        assert inter["shannon_index"] > 0.9  # log2(2) = 1.0
        assert inter["shannon_index"] <= 1.0 + 1e-6

    @pytest.mark.asyncio
    async def test_empty_disciplines_shannon_zero(self) -> None:
        repo = _FakeRepo(disciplines=[], total_mapped=0, total_projects=0)
        servicer = _make_servicer(repo)

        response = await servicer.AnalyzeEuroSciVoc(_build_request("unknown tech"), context=None)

        inter = response["interdisciplinarity"]
        assert inter["active_fields"] == 0
        assert inter["shannon_index"] == 0.0

    @pytest.mark.asyncio
    async def test_level_1_is_treated_as_field(self) -> None:
        """Level '1' ist synonym zu 'FIELD' (manche Datensaetze nutzen numerische Level)."""
        disciplines = [
            {"id": "f1", "label": "natural sciences", "level": "1", "parent_id": "", "project_count": 3, "share": 1.0},
            {"id": "s1", "label": "chemistry", "level": "2", "parent_id": "f1", "project_count": 3, "share": 1.0},
        ]
        repo = _FakeRepo(disciplines=disciplines, total_mapped=3, total_projects=3)
        servicer = _make_servicer(repo)

        response = await servicer.AnalyzeEuroSciVoc(_build_request("x"), context=None)

        inter = response["interdisciplinarity"]
        assert inter["active_fields"] == 1
        assert inter["shannon_index"] == 0.0


class TestTotalProjectsIsDistinctCount:
    """MIN-10: `total_mapped_publications` muss die Anzahl *distinkter* Projekte
    sein und darf nicht versehentlich ueber Felder summiert werden.

    Live-Beobachtung: UC10 zeigte 387 Projekte, waehrend der Header (selbe Tech,
    selbes Zeitfenster) nur 307 zaehlte. Ursache war die Aggregation per Feld
    (Doppelzaehlung von Projekten mit mehreren EuroSciVoc-Tags) plus eine
    fehlende Zeitfenster-Filterung in `total_mapped_projects()`.
    """

    @pytest.mark.asyncio
    async def test_total_mapped_publications_equals_distinct_project_count(self) -> None:
        """10 Projekte, 2 Felder, jedes Projekt in beiden Feldern -> total = 10, nicht 20."""
        # Disziplin-Verteilung: 2 Felder, jedes mit 10 Projekten (Doppelzaehlung).
        # Wuerde man `SUM(project_count GROUP BY field)` rechnen, kaeme 20 raus.
        disciplines = [
            {"id": "f1", "label": "natural sciences", "level": "FIELD", "parent_id": "", "project_count": 10, "share": 0.5},
            {"id": "f2", "label": "engineering", "level": "FIELD", "parent_id": "", "project_count": 10, "share": 0.5},
        ]
        # Repo liefert distinct project count = 10.
        repo = _FakeRepo(disciplines=disciplines, total_mapped=10, total_projects=10)
        servicer = _make_servicer(repo)

        response = await servicer.AnalyzeEuroSciVoc(_build_request("mrna"), context=None)

        assert response["total_mapped_publications"] == 10, (
            "total_mapped_publications muss COUNT(DISTINCT project) sein, "
            f"nicht SUM-ueber-Felder. Wert war {response['total_mapped_publications']}."
        )
        # Sanity: Summe ueber Felder waere 20 — darf NICHT der Wert sein.
        sum_over_fields = sum(int(d["project_count"]) for d in disciplines)
        assert response["total_mapped_publications"] != sum_over_fields

    @pytest.mark.asyncio
    async def test_total_mapped_uses_same_year_window_as_distribution(self) -> None:
        """`total_mapped_projects` muss mit demselben Zeitfenster wie
        `discipline_distribution` aufgerufen werden, sonst entstehen
        Header/UC10-Divergenzen (Header 307 vs. UC10 387 in Live-Daten).
        """
        repo = _FakeRepo(disciplines=[], total_mapped=0, total_projects=0)
        servicer = _make_servicer(repo)

        await servicer.AnalyzeEuroSciVoc(_build_request("mrna"), context=None)

        # Ein Aufruf an total_mapped_projects mit start_year/end_year = 2020/2024.
        assert len(repo.total_mapped_calls) == 1
        call = repo.total_mapped_calls[0]
        assert call.get("start_year") == 2020, (
            f"total_mapped_projects muss start_year=2020 erhalten, kwargs waren: {call}"
        )
        assert call.get("end_year") == 2024, (
            f"total_mapped_projects muss end_year=2024 erhalten, kwargs waren: {call}"
        )

        # discipline_distribution muss dasselbe Fenster nutzen.
        dist = repo.discipline_distribution_calls[0]
        assert dist.get("start_year") == call.get("start_year")
        assert dist.get("end_year") == call.get("end_year")
