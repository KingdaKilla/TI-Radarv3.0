"""Tests fuer UC-C Domain-Metriken: compute_pubs_per_million, compute_pubs_per_project."""

import pytest

from src.domain.metrics import compute_pubs_per_million, compute_pubs_per_project


# ===================================================================
# compute_pubs_per_million
# ===================================================================


class TestPubsPerMillion:
    """Tests fuer Publikationen-pro-Million-EUR-Berechnung."""

    def test_normal_case(self) -> None:
        """2M EUR Foerderung, 50 Publikationen -> 25.0 pro Million."""
        assert compute_pubs_per_million(2_000_000, 50) == 25.0

    def test_one_million(self) -> None:
        """1M EUR, 10 Publikationen -> 10.0."""
        assert compute_pubs_per_million(1_000_000, 10) == 10.0

    def test_small_funding(self) -> None:
        """500k EUR, 5 Publikationen -> 10.0."""
        assert compute_pubs_per_million(500_000, 5) == 10.0

    def test_zero_funding(self) -> None:
        """Keine Foerderung -> 0.0 (Division durch Null vermeiden)."""
        assert compute_pubs_per_million(0, 50) == 0.0

    def test_negative_funding(self) -> None:
        """Negative Foerderung -> 0.0 (Schutz vor unsinnigen Werten)."""
        assert compute_pubs_per_million(-100_000, 5) == 0.0

    def test_zero_publications(self) -> None:
        """Keine Publikationen -> 0.0."""
        assert compute_pubs_per_million(1_000_000, 0) == 0.0

    def test_rounding(self) -> None:
        """Ergebnis wird auf 2 Dezimalstellen gerundet."""
        # 3M EUR, 7 Pubs -> 7/3 = 2.333... -> 2.33
        assert compute_pubs_per_million(3_000_000, 7) == 2.33

    def test_large_values(self) -> None:
        """Grosse Foerderung mit vielen Publikationen."""
        assert compute_pubs_per_million(50_000_000, 500) == 10.0


# ===================================================================
# compute_pubs_per_project
# ===================================================================


class TestPubsPerProject:
    """Tests fuer Durchschnittliche-Publikationen-pro-Projekt-Berechnung."""

    def test_normal_case(self) -> None:
        """100 Pubs, 20 Projekte -> 5.0."""
        assert compute_pubs_per_project(100, 20) == 5.0

    def test_zero_projects(self) -> None:
        """Keine Projekte -> 0.0 (Division durch Null vermeiden)."""
        assert compute_pubs_per_project(100, 0) == 0.0

    def test_zero_publications(self) -> None:
        """Keine Publikationen -> 0.0."""
        assert compute_pubs_per_project(0, 10) == 0.0

    def test_both_zero(self) -> None:
        """Beides Null -> 0.0."""
        assert compute_pubs_per_project(0, 0) == 0.0

    def test_negative_projects(self) -> None:
        """Negative Projektzahl -> 0.0 (Schutz)."""
        assert compute_pubs_per_project(50, -1) == 0.0

    def test_rounding(self) -> None:
        """Ergebnis wird auf 1 Dezimalstelle gerundet."""
        # 7 Pubs / 3 Projekte = 2.333... -> 2.3
        assert compute_pubs_per_project(7, 3) == 2.3

    def test_one_project(self) -> None:
        """Ein Projekt mit vielen Publikationen."""
        assert compute_pubs_per_project(42, 1) == 42.0

    def test_equal_counts(self) -> None:
        """Gleich viele Pubs wie Projekte -> 1.0."""
        assert compute_pubs_per_project(15, 15) == 1.0
