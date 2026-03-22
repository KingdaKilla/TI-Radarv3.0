"""Tests fuer shared.domain.temporal_metrics — Akteur-Dynamik, Technologie-Breite."""

from __future__ import annotations

import pytest

from shared.domain.temporal_metrics import (
    _compute_actor_dynamics,
    _compute_actor_timeline,
    _compute_programme_evolution,
    _compute_technology_breadth,
)


# ============================================================================
# _compute_actor_dynamics()
# ============================================================================


class TestComputeActorDynamics:
    def test_basic(self):
        actors_by_year = {
            2020: {"CompanyA": 5, "CompanyB": 3},
            2021: {"CompanyA": 6, "CompanyC": 2},
            2022: {"CompanyB": 4, "CompanyC": 3, "CompanyD": 1},
        }
        result = _compute_actor_dynamics(actors_by_year)

        assert len(result) == 3
        # Erstes Jahr: alle sind Neulinge
        assert result[0]["year"] == 2020
        assert result[0]["new_entrant_rate"] == 1.0
        assert result[0]["persistence_rate"] == 0.0

        # 2021: CompanyC ist neu, CompanyA bleibt
        assert result[1]["year"] == 2021
        assert result[1]["new_entrant_rate"] == pytest.approx(0.5)  # 1 von 2 neu
        assert result[1]["persistence_rate"] == pytest.approx(0.5)  # 1 von 2 blieb

    def test_empty(self):
        assert _compute_actor_dynamics({}) == []

    def test_single_year(self):
        result = _compute_actor_dynamics({2020: {"A": 1}})
        assert len(result) == 1
        assert result[0]["new_entrant_rate"] == 1.0


# ============================================================================
# _compute_technology_breadth()
# ============================================================================


class TestComputeTechnologyBreadth:
    def test_basic(self):
        cpc_by_year = {
            2020: ["H01L,G06N", "A61K,C07D"],
            2021: ["H01L,G06N,B60L"],
        }
        result = _compute_technology_breadth(cpc_by_year)

        assert len(result) == 2
        assert result[0]["year"] == 2020
        assert result[0]["unique_cpc_sections"] >= 3  # H, G, A, C
        assert result[0]["unique_cpc_subclasses"] >= 4  # H01L, G06N, A61K, C07D

        assert result[1]["year"] == 2021
        assert result[1]["unique_cpc_subclasses"] >= 3

    def test_empty(self):
        assert _compute_technology_breadth({}) == []

    def test_single_section(self):
        cpc_by_year = {2020: ["H01L,H01M,H02J"]}
        result = _compute_technology_breadth(cpc_by_year)
        assert result[0]["unique_cpc_sections"] == 1  # nur "H"
        assert result[0]["unique_cpc_subclasses"] == 3


# ============================================================================
# _compute_actor_timeline()
# ============================================================================


class TestComputeActorTimeline:
    def test_basic(self):
        actors_by_year = {
            2020: {"CompanyA": 10, "CompanyB": 5},
            2021: {"CompanyA": 8, "CompanyC": 3},
            2022: {"CompanyA": 12},
        }
        result = _compute_actor_timeline(actors_by_year, top_n=2)

        assert len(result) == 2
        # CompanyA hat die meisten (30 total)
        assert result[0]["name"] == "CompanyA"
        assert result[0]["total_count"] == 30
        assert sorted(result[0]["years_active"]) == [2020, 2021, 2022]

    def test_empty(self):
        assert _compute_actor_timeline({}) == []

    def test_top_n_limit(self):
        actors_by_year = {2020: {f"C{i}": i for i in range(20)}}
        result = _compute_actor_timeline(actors_by_year, top_n=5)
        assert len(result) == 5


# ============================================================================
# _compute_programme_evolution()
# ============================================================================


class TestComputeProgrammeEvolution:
    def test_basic(self):
        data = [
            {"year": 2020, "scheme": "RIA", "count": 10},
            {"year": 2020, "scheme": "CSA", "count": 5},
            {"year": 2021, "scheme": "RIA", "count": 15},
        ]
        result = _compute_programme_evolution(data)

        assert len(result) == 2
        assert result[0]["year"] == 2020
        assert result[0]["RIA"] == 10
        assert result[0]["CSA"] == 5
        assert result[1]["year"] == 2021
        assert result[1]["RIA"] == 15

    def test_empty(self):
        assert _compute_programme_evolution([]) == []

    def test_sorted_by_year(self):
        data = [
            {"year": 2022, "scheme": "A", "count": 1},
            {"year": 2020, "scheme": "A", "count": 1},
            {"year": 2021, "scheme": "A", "count": 1},
        ]
        result = _compute_programme_evolution(data)
        years = [r["year"] for r in result]
        assert years == sorted(years)
