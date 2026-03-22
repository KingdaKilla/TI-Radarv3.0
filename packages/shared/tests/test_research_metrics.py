"""Tests fuer shared.domain.research_metrics — h-Index, Zitationstrend, Top-Papers."""

from __future__ import annotations

import pytest

from shared.domain.research_metrics import (
    _compute_citation_trend,
    _compute_h_index,
    _compute_publication_types,
    _compute_top_papers,
    _compute_venue_distribution,
)


# ============================================================================
# _compute_h_index()
# ============================================================================


class TestComputeHIndex:
    def test_classic_example(self):
        # 5 Paper mit [10, 8, 5, 4, 3] Zitationen -> h=4
        assert _compute_h_index([10, 8, 5, 4, 3]) == 4

    def test_all_equal(self):
        assert _compute_h_index([5, 5, 5, 5, 5]) == 5

    def test_one_paper_many_citations(self):
        assert _compute_h_index([100]) == 1

    def test_empty(self):
        assert _compute_h_index([]) == 0

    def test_all_zeros(self):
        assert _compute_h_index([0, 0, 0]) == 0

    def test_descending(self):
        assert _compute_h_index([6, 5, 3, 1, 0]) == 3

    def test_hirsch_example(self):
        # Hirsch (2005) Beispiel: h=10 wenn 10 Paper je >= 10 Zitationen
        citations = [15, 14, 13, 12, 11, 10, 10, 10, 10, 10, 5, 3, 1]
        assert _compute_h_index(citations) == 10


# ============================================================================
# _compute_citation_trend()
# ============================================================================


class TestComputeCitationTrend:
    def test_basic(self):
        papers = [
            {"year": 2020, "citationCount": 10},
            {"year": 2020, "citationCount": 5},
            {"year": 2021, "citationCount": 20},
        ]
        result = _compute_citation_trend(papers)
        assert len(result) == 2
        assert result[0]["year"] == 2020
        assert result[0]["citations"] == 15
        assert result[0]["paper_count"] == 2
        assert result[1]["year"] == 2021
        assert result[1]["citations"] == 20

    def test_empty(self):
        assert _compute_citation_trend([]) == []

    def test_missing_year(self):
        papers = [{"citationCount": 10}]
        assert _compute_citation_trend(papers) == []

    def test_none_citations(self):
        papers = [{"year": 2020, "citationCount": None}]
        result = _compute_citation_trend(papers)
        assert result[0]["citations"] == 0

    def test_sorted_by_year(self):
        papers = [
            {"year": 2022, "citationCount": 5},
            {"year": 2020, "citationCount": 10},
            {"year": 2021, "citationCount": 3},
        ]
        result = _compute_citation_trend(papers)
        years = [r["year"] for r in result]
        assert years == sorted(years)


# ============================================================================
# _compute_top_papers()
# ============================================================================


class TestComputeTopPapers:
    def test_basic(self):
        papers = [
            {"title": "A", "venue": "Nature", "year": 2020, "citationCount": 100, "authors": []},
            {"title": "B", "venue": "Science", "year": 2021, "citationCount": 50, "authors": []},
            {"title": "C", "venue": "ArXiv", "year": 2022, "citationCount": 200, "authors": []},
        ]
        result = _compute_top_papers(papers, top_n=2)
        assert len(result) == 2
        assert result[0]["title"] == "C"
        assert result[0]["citations"] == 200

    def test_authors_truncation(self):
        papers = [{
            "title": "X",
            "venue": "V",
            "year": 2020,
            "citationCount": 10,
            "authors": [
                {"name": "Alice"},
                {"name": "Bob"},
                {"name": "Charlie"},
                {"name": "Diana"},
            ],
        }]
        result = _compute_top_papers(papers)
        assert "et al." in result[0]["authors_short"]

    def test_empty(self):
        assert _compute_top_papers([]) == []


# ============================================================================
# _compute_venue_distribution()
# ============================================================================


class TestComputeVenueDistribution:
    def test_basic(self):
        papers = [
            {"venue": "Nature"},
            {"venue": "Nature"},
            {"venue": "Science"},
        ]
        result = _compute_venue_distribution(papers)
        assert result[0]["venue"] == "Nature"
        assert result[0]["count"] == 2
        assert result[0]["share"] == pytest.approx(2 / 3, abs=0.01)

    def test_empty_venues_filtered(self):
        papers = [{"venue": ""}, {"venue": None}]
        result = _compute_venue_distribution(papers)
        assert result == []

    def test_top_n_limit(self):
        papers = [{"venue": f"V{i}"} for i in range(20)]
        result = _compute_venue_distribution(papers, top_n=5)
        assert len(result) == 5


# ============================================================================
# _compute_publication_types()
# ============================================================================


class TestComputePublicationTypes:
    def test_basic(self):
        papers = [
            {"publicationTypes": ["JournalArticle"]},
            {"publicationTypes": ["JournalArticle", "Review"]},
            {"publicationTypes": ["Conference"]},
        ]
        result = _compute_publication_types(papers)
        types = {r["type"]: r["count"] for r in result}
        assert types["JournalArticle"] == 2
        assert types["Review"] == 1
        assert types["Conference"] == 1

    def test_empty(self):
        assert _compute_publication_types([]) == []

    def test_none_types(self):
        papers = [{"publicationTypes": None}]
        assert _compute_publication_types(papers) == []
