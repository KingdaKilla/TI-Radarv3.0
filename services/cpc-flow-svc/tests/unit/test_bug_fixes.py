"""Unit-Tests fuer Bundle-D Bug-Fixes.

Testet:
- Bug 1: year_data_entries darf nicht leer sein, wenn CPC-Daten vorhanden sind.
- Bug 2: top_pairs mit similarity > 0 muessen co_occurrence_count > 0 haben
         (Jaccard ohne Co-Occurrence ist mathematisch unmoeglich).
"""

from __future__ import annotations

from typing import Any

import pytest

from src.service import (
    _build_year_data_entries,
    _extract_top_pairs,
)


# ---------------------------------------------------------------------------
# Bug 2: co_occurrence_count
# ---------------------------------------------------------------------------

class TestCoOccurrenceCountNonZero:
    """Wenn similarity > 0, muss co_occurrence_count > 0 sein."""

    def test_top_pairs_have_co_occurrence_count_field(self) -> None:
        """Jedes Top-Pair enthaelt ein co_occurrence_count-Feld."""
        labels = ["H04W", "G06N"]
        matrix = [[1.0, 0.25], [0.25, 1.0]]
        pair_co_counts = {("G06N", "H04W"): 50}
        code_counts = {"H04W": 120, "G06N": 130}

        pairs = _extract_top_pairs(
            labels, matrix, top_n=10,
            pair_co_counts=pair_co_counts, code_counts=code_counts,
        )

        assert len(pairs) == 1
        assert "co_occurrence_count" in pairs[0]
        assert "union_count" in pairs[0]

    def test_co_occurrence_count_from_pair_counts(self) -> None:
        """co_occurrence_count entspricht dem SQL-Ergebnis wenn vorhanden."""
        labels = ["A01B", "B02C"]
        matrix = [[1.0, 0.2], [0.2, 1.0]]
        pair_co_counts = {("A01B", "B02C"): 42}
        code_counts = {"A01B": 100, "B02C": 110}

        pairs = _extract_top_pairs(
            labels, matrix, top_n=10,
            pair_co_counts=pair_co_counts, code_counts=code_counts,
        )

        assert pairs[0]["co_occurrence_count"] == 42

    def test_top_pairs_with_similarity_gt_zero_have_co_count_gt_zero(self) -> None:
        """Kernpruefung (Bug 2): similarity > 0 impliziert co_occurrence_count > 0."""
        labels = ["X01A", "Y02B", "Z03C"]
        matrix = [
            [1.0, 0.3, 0.1],
            [0.3, 1.0, 0.0],
            [0.1, 0.0, 1.0],
        ]
        pair_co_counts = {
            ("X01A", "Y02B"): 15,
            ("X01A", "Z03C"): 5,
        }
        code_counts = {"X01A": 100, "Y02B": 60, "Z03C": 70}

        pairs = _extract_top_pairs(
            labels, matrix, top_n=10,
            pair_co_counts=pair_co_counts, code_counts=code_counts,
        )

        for pair in pairs:
            if pair["similarity"] > 0:
                assert pair["co_occurrence_count"] > 0, (
                    f"Jaccard {pair['similarity']} bei co_occurrence_count=0 "
                    f"ist mathematisch unmoeglich: {pair}"
                )

    def test_co_count_fallback_reconstructed_from_jaccard(self) -> None:
        """Fehlt pair_co_counts, wird co_count aus Jaccard zurueckgerechnet."""
        labels = ["A01B", "C02D"]
        # Jaccard = 0.25 mit Counts (100, 100) -> co = 0.25*200/1.25 = 40
        matrix = [[1.0, 0.25], [0.25, 1.0]]
        code_counts = {"A01B": 100, "C02D": 100}

        pairs = _extract_top_pairs(
            labels, matrix, top_n=10,
            pair_co_counts={}, code_counts=code_counts,
        )

        assert len(pairs) == 1
        assert pairs[0]["co_occurrence_count"] > 0
        # Toleranz wegen Rundung
        assert 35 <= pairs[0]["co_occurrence_count"] <= 45

    def test_union_count_matches_inclusion_exclusion(self) -> None:
        """union_count = count_a + count_b - co_count (Inclusion-Exclusion)."""
        labels = ["H04W", "G06N"]
        matrix = [[1.0, 0.5], [0.5, 1.0]]
        pair_co_counts = {("G06N", "H04W"): 50}
        code_counts = {"H04W": 100, "G06N": 80}

        pairs = _extract_top_pairs(
            labels, matrix, top_n=10,
            pair_co_counts=pair_co_counts, code_counts=code_counts,
        )

        # union = 100 + 80 - 50 = 130
        assert pairs[0]["union_count"] == 130

    def test_no_pair_when_similarity_zero(self) -> None:
        """Paare mit similarity=0 werden nicht aufgenommen."""
        labels = ["A01B", "B02C"]
        matrix = [[1.0, 0.0], [0.0, 1.0]]
        pairs = _extract_top_pairs(
            labels, matrix, top_n=10,
            pair_co_counts={}, code_counts={"A01B": 10, "B02C": 10},
        )
        assert pairs == []


# ---------------------------------------------------------------------------
# Bug 1: year_data_entries
# ---------------------------------------------------------------------------

class TestYearDataPopulated:
    """year_data_entries darf nicht leer sein wenn CPC-Codes pro Jahr vorhanden sind."""

    def test_year_data_populated_when_cpc_data_exists(self) -> None:
        """Kernpruefung (Bug 1): year_data muss bei vorhandenen CPC-Daten befuellt sein."""
        cpc_year_counts = [
            {"year": 2020, "code": "H04W", "patent_count": 100},
            {"year": 2020, "code": "G06N", "patent_count": 80},
            {"year": 2021, "code": "H04W", "patent_count": 120},
            {"year": 2021, "code": "G06N", "patent_count": 110},
        ]
        pair_year_counts = [
            {"year": 2020, "code_a": "G06N", "code_b": "H04W", "co_count": 20},
            {"year": 2021, "code_a": "G06N", "code_b": "H04W", "co_count": 40},
        ]

        entries = _build_year_data_entries(
            top_codes=["H04W", "G06N"],
            cpc_year_counts=cpc_year_counts,
            pair_year_counts=pair_year_counts,
        )

        assert len(entries) == 2, "Es muessen 2 Jahres-Eintraege vorhanden sein"
        assert entries[0]["year"] == 2020
        assert entries[1]["year"] == 2021

    def test_year_entry_schema(self) -> None:
        """Jeder Year-Eintrag enthaelt die Pflicht-Felder."""
        entries = _build_year_data_entries(
            top_codes=["H04W"],
            cpc_year_counts=[{"year": 2020, "code": "H04W", "patent_count": 50}],
            pair_year_counts=[],
        )

        assert len(entries) == 1
        entry = entries[0]
        for field in ("year", "active_codes", "avg_similarity",
                      "max_similarity", "patent_count"):
            assert field in entry, f"Feld {field} fehlt in year-entry"

    def test_active_codes_counts_distinct_cpc(self) -> None:
        """active_codes zaehlt die Anzahl unterschiedlicher CPC-Codes pro Jahr."""
        cpc_year_counts = [
            {"year": 2022, "code": "A01B", "patent_count": 10},
            {"year": 2022, "code": "B02C", "patent_count": 20},
            {"year": 2022, "code": "C03D", "patent_count": 30},
        ]

        entries = _build_year_data_entries(
            top_codes=["A01B", "B02C", "C03D"],
            cpc_year_counts=cpc_year_counts,
            pair_year_counts=[],
        )

        assert entries[0]["active_codes"] == 3

    def test_patent_count_sums_per_year(self) -> None:
        """patent_count aggregiert alle Code-Counts des Jahres."""
        cpc_year_counts = [
            {"year": 2023, "code": "A01B", "patent_count": 10},
            {"year": 2023, "code": "B02C", "patent_count": 20},
        ]
        entries = _build_year_data_entries(
            top_codes=["A01B", "B02C"],
            cpc_year_counts=cpc_year_counts,
            pair_year_counts=[],
        )
        assert entries[0]["patent_count"] == 30

    def test_avg_and_max_similarity_from_jaccard(self) -> None:
        """avg/max_similarity werden aus pair_year_counts via Jaccard berechnet."""
        cpc_year_counts = [
            {"year": 2024, "code": "X", "patent_count": 100},
            {"year": 2024, "code": "Y", "patent_count": 100},
            {"year": 2024, "code": "Z", "patent_count": 100},
        ]
        # Erzwinge unterschiedliche Jaccard-Werte
        pair_year_counts = [
            {"year": 2024, "code_a": "X", "code_b": "Y", "co_count": 50},  # J=0.333
            {"year": 2024, "code_a": "Y", "code_b": "Z", "co_count": 10},  # J=0.0526
        ]
        entries = _build_year_data_entries(
            top_codes=["X", "Y", "Z"],
            cpc_year_counts=cpc_year_counts,
            pair_year_counts=pair_year_counts,
        )

        entry = entries[0]
        assert entry["max_similarity"] > entry["avg_similarity"]
        assert entry["max_similarity"] == pytest.approx(0.3333, abs=0.001)

    def test_empty_inputs_yield_empty_year_data(self) -> None:
        """Keine CPC-Daten -> keine Year-Entries."""
        entries = _build_year_data_entries(
            top_codes=[],
            cpc_year_counts=[],
            pair_year_counts=[],
        )
        assert entries == []

    def test_entries_are_sorted_by_year(self) -> None:
        """Year-Entries sind chronologisch sortiert."""
        cpc_year_counts = [
            {"year": 2022, "code": "A", "patent_count": 10},
            {"year": 2020, "code": "A", "patent_count": 5},
            {"year": 2023, "code": "A", "patent_count": 30},
            {"year": 2021, "code": "A", "patent_count": 15},
        ]
        entries = _build_year_data_entries(
            top_codes=["A"],
            cpc_year_counts=cpc_year_counts,
            pair_year_counts=[],
        )
        years = [e["year"] for e in entries]
        assert years == sorted(years)


# ---------------------------------------------------------------------------
# Integrations-Check: Kombi aus beiden Fixes
# ---------------------------------------------------------------------------

class TestCombinedConsistency:
    """Konsistenz zwischen Top-Pairs und Year-Data."""

    def test_similarity_implies_nonzero_co_occurrence_in_all_pairs(self) -> None:
        """KEIN Paar darf similarity > 0 und co_occurrence_count == 0 haben."""
        labels = ["A", "B", "C"]
        matrix = [
            [1.0, 0.3, 0.15],
            [0.3, 1.0, 0.05],
            [0.15, 0.05, 1.0],
        ]
        pair_co_counts = {
            ("A", "B"): 30,
            ("A", "C"): 15,
            ("B", "C"): 5,
        }
        code_counts = {"A": 100, "B": 100, "C": 100}

        pairs = _extract_top_pairs(
            labels, matrix, top_n=20,
            pair_co_counts=pair_co_counts, code_counts=code_counts,
        )

        invalid = [p for p in pairs if p["similarity"] > 0 and p["co_occurrence_count"] <= 0]
        assert invalid == [], f"Invalide Paare (Jaccard > 0, co_count == 0): {invalid}"
