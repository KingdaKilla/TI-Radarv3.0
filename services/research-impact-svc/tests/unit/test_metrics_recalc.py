"""Unit-Tests fuer Bundle A Bug-Fixes in UC7 Research Impact Metriken.

Deckt die Bugs C-012, M-008, M-009, M-010 und das Zeitraum-Padding C5.2 ab.
Es werden sowohl die shared-Metriken (``shared.domain.research_metrics``)
als auch die lokalen Fallback-Metriken (``src.domain.metrics``) getestet,
damit der Service-Code unabhaengig von der Import-Reihenfolge robust ist.
"""

from __future__ import annotations

from typing import Any

import pytest

# shared-Domain (primaer im service.py importiert)
from shared.domain.research_metrics import (
    _compute_citation_trend as shared_citation_trend,
    _compute_publication_types as shared_publication_types,
    _compute_venue_distribution as shared_venue_distribution,
)

# lokaler Fallback
from src.domain.metrics import (
    compute_citation_trend,
    compute_publication_types,
    compute_venue_distribution,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _paper(
    *,
    year: int,
    citations: int,
    venue: str = "",
    types: list[str] | None = None,
) -> dict[str, Any]:
    """Erstellt ein Paper-Dict im Semantic-Scholar Format."""
    return {
        "year": year,
        "citationCount": citations,
        "venue": venue,
        "publicationTypes": types or [],
    }


# ---------------------------------------------------------------------------
# C-012: publication_types[*].share
# ---------------------------------------------------------------------------

class TestPublicationTypesShare:
    """Bug C-012: ``share`` muss gesetzt sein, nicht 0 bei count > 0."""

    def test_publication_types_share_sum_to_one_shared(self) -> None:
        papers = [
            _paper(year=2020, citations=5, types=["JournalArticle"]),
            _paper(year=2020, citations=5, types=["JournalArticle"]),
            _paper(year=2021, citations=3, types=["Conference"]),
            _paper(year=2022, citations=1, types=["Review"]),
        ]
        result = shared_publication_types(papers)
        assert result, "publication_types duerfen nicht leer sein"
        total_share = sum(entry["share"] for entry in result)
        assert total_share == pytest.approx(1.0, abs=1e-3)
        # Jeder Eintrag mit count > 0 muss share > 0 haben (C-012)
        for entry in result:
            assert entry["count"] > 0
            assert entry["share"] > 0.0

    def test_publication_types_share_sum_to_one_local(self) -> None:
        papers = [
            _paper(year=2020, citations=5, types=["JournalArticle"]),
            _paper(year=2020, citations=5, types=["JournalArticle"]),
            _paper(year=2021, citations=3, types=["Conference"]),
        ]
        result = compute_publication_types(papers)
        total_share = sum(entry["share"] for entry in result)
        assert total_share == pytest.approx(1.0, abs=1e-3)
        for entry in result:
            assert entry["share"] > 0.0


# ---------------------------------------------------------------------------
# M-008: citation_trend[*].avg_citations
# ---------------------------------------------------------------------------

class TestCitationTrendAvg:
    """Bug M-008: ``avg_citations`` MUSS aus total/count berechnet werden."""

    def test_citation_trend_avg_citations_computed_shared(self) -> None:
        # 10 Papers im Jahr 2020, je 10 Zitationen -> total=100, avg=10.0
        papers = [_paper(year=2020, citations=10) for _ in range(10)]
        trend = shared_citation_trend(papers)
        assert len(trend) == 1
        entry = trend[0]
        assert entry["year"] == 2020
        assert entry["total_citations"] == 100
        assert entry["publication_count"] == 10
        assert entry["avg_citations"] == pytest.approx(10.0)

    def test_citation_trend_avg_citations_computed_local(self) -> None:
        papers = [
            _paper(year=2019, citations=4),
            _paper(year=2019, citations=6),
        ]
        trend = compute_citation_trend(papers)
        entry = next(e for e in trend if e["year"] == 2019)
        assert entry["total_citations"] == 10
        assert entry["publication_count"] == 2
        assert entry["avg_citations"] == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# M-009 / M-010: top_venues avg_citations + h_index
# ---------------------------------------------------------------------------

class TestTopVenues:
    """Bug M-009 (avg_citations) + M-010 (h_index) pro Venue."""

    def test_top_venues_avg_citations_shared(self) -> None:
        papers = [
            _paper(year=2020, citations=10, venue="Nature"),
            _paper(year=2021, citations=20, venue="Nature"),
            _paper(year=2022, citations=30, venue="Nature"),
            _paper(year=2022, citations=5, venue="Science"),
        ]
        venues = shared_venue_distribution(papers, top_n=8)
        nature = next(v for v in venues if v["name"] == "Nature")
        assert nature["publication_count"] == 3
        assert nature["avg_citations"] == pytest.approx(20.0)  # 60/3

    def test_top_venues_h_index_from_papers_shared(self) -> None:
        # Venue "A" mit Zitationen [5, 5, 5, 5, 5] -> h_index = 5
        # Venue "B" mit Zitationen [10, 8, 5, 4, 3] -> h_index = 4
        papers_a = [_paper(year=2020, citations=5, venue="A") for _ in range(5)]
        papers_b = [
            _paper(year=2020, citations=10, venue="B"),
            _paper(year=2020, citations=8, venue="B"),
            _paper(year=2020, citations=5, venue="B"),
            _paper(year=2020, citations=4, venue="B"),
            _paper(year=2020, citations=3, venue="B"),
        ]
        venues = shared_venue_distribution(papers_a + papers_b, top_n=8)
        by_name = {v["name"]: v for v in venues}
        assert by_name["A"]["h_index"] == 5
        assert by_name["B"]["h_index"] == 4

    def test_top_venues_h_index_from_papers_local(self) -> None:
        papers = [
            _paper(year=2020, citations=100, venue="IEEE TNN"),
            _paper(year=2021, citations=80, venue="IEEE TNN"),
            _paper(year=2022, citations=3, venue="IEEE TNN"),
            _paper(year=2022, citations=2, venue="IEEE TNN"),
        ]
        venues = compute_venue_distribution(papers, top_n=8)
        v = venues[0]
        # Zitationen sortiert: [100, 80, 3, 2] -> h_index = 3 (3 Paper >= 3)
        assert v["h_index"] == 3
        assert v["avg_citations"] == pytest.approx(46.25)


# ---------------------------------------------------------------------------
# C5.2: Zeitraum-Padding
# ---------------------------------------------------------------------------

class TestCitationTrendPadding:
    """Bug C5.2: fehlende Jahre zwischen start_year/end_year mit 0 auffuellen."""

    def test_citation_trend_padded_for_missing_years_shared(self) -> None:
        # Daten nur fuer 2018-2022, Bereich aber 2016-2024
        papers = [
            _paper(year=2018, citations=5),
            _paper(year=2020, citations=10),
            _paper(year=2022, citations=15),
        ]
        trend = shared_citation_trend(papers, start_year=2016, end_year=2024)
        years = [e["year"] for e in trend]
        # ALLE Jahre 2016..2024 muessen enthalten sein
        assert years == list(range(2016, 2025))
        # 2016 und 2017 muessen 0-Werte haben
        by_year = {e["year"]: e for e in trend}
        assert by_year[2016]["publication_count"] == 0
        assert by_year[2016]["total_citations"] == 0
        assert by_year[2016]["avg_citations"] == 0.0
        assert by_year[2017]["publication_count"] == 0
        # Vorhandene Daten bleiben unveraendert
        assert by_year[2018]["total_citations"] == 5
        assert by_year[2020]["publication_count"] == 1
        # 2023 + 2024 sind ebenfalls gepadded
        assert by_year[2023]["publication_count"] == 0
        assert by_year[2024]["publication_count"] == 0

    def test_citation_trend_padded_for_missing_years_local(self) -> None:
        papers = [_paper(year=2019, citations=7)]
        trend = compute_citation_trend(papers, start_year=2017, end_year=2021)
        years = [e["year"] for e in trend]
        assert years == [2017, 2018, 2019, 2020, 2021]
        by_year = {e["year"]: e for e in trend}
        assert by_year[2017]["total_citations"] == 0
        assert by_year[2019]["total_citations"] == 7
        assert by_year[2021]["total_citations"] == 0

    def test_citation_trend_no_padding_without_range_shared(self) -> None:
        """Ohne start_year/end_year darf nichts auto-gepadded werden."""
        papers = [_paper(year=2020, citations=3)]
        trend = shared_citation_trend(papers)
        assert len(trend) == 1
        assert trend[0]["year"] == 2020
