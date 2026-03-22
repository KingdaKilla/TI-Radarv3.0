"""Tests fuer shared.domain.cpc_flow — CPC Co-Klassifikation und Jaccard-Index."""

from __future__ import annotations

import pytest

from shared.domain.cpc_flow import (
    assign_colors,
    build_cooccurrence,
    build_cooccurrence_with_years,
    build_jaccard_from_sql,
    build_year_data_from_aggregates,
    extract_cpc_sets,
    extract_cpc_sets_with_years,
    normalize_cpc,
)


# ============================================================================
# normalize_cpc()
# ============================================================================


class TestNormalizeCpc:
    def test_standard_code(self):
        assert normalize_cpc("H01L 33/00") == "H01L"

    def test_short_code(self):
        assert normalize_cpc("G06") == "G06"

    def test_level_3(self):
        assert normalize_cpc("H01L 33/00", level=3) == "H01"

    def test_whitespace(self):
        assert normalize_cpc("  H01M  ") == "H01M"

    def test_empty(self):
        assert normalize_cpc("") == ""

    def test_spaces_in_code(self):
        assert normalize_cpc("B 60 L") == "B60L"


# ============================================================================
# extract_cpc_sets()
# ============================================================================


class TestExtractCpcSets:
    def test_basic(self):
        result = extract_cpc_sets(["H01L,G06N,B60L"])
        assert len(result) == 1
        assert "H01L" in result[0]
        assert "G06N" in result[0]
        assert "B60L" in result[0]

    def test_single_code_filtered_out(self):
        """Patente mit nur 1 CPC-Code werden gefiltert (braucht mind. 2)."""
        result = extract_cpc_sets(["H01L"])
        assert len(result) == 0

    def test_empty_strings(self):
        result = extract_cpc_sets(["", "  ", None])
        assert len(result) == 0

    def test_multiple_patents(self):
        result = extract_cpc_sets(["A01B,C07K", "G06F,H04L"])
        assert len(result) == 2


# ============================================================================
# extract_cpc_sets_with_years()
# ============================================================================


class TestExtractCpcSetsWithYears:
    def test_basic(self):
        rows = [
            {"cpc_codes": "H01L,G06N", "year": 2020},
            {"cpc_codes": "A61K,C07D", "year": 2021},
        ]
        result = extract_cpc_sets_with_years(rows)
        assert len(result) == 2
        codes, year = result[0]
        assert year == 2020
        assert "H01L" in codes

    def test_missing_year(self):
        rows = [{"cpc_codes": "H01L,G06N", "year": 0}]
        result = extract_cpc_sets_with_years(rows)
        assert len(result) == 0


# ============================================================================
# build_cooccurrence()
# ============================================================================


class TestBuildCooccurrence:
    def test_basic_matrix(self):
        patent_sets = [
            {"H01L", "G06N"},
            {"H01L", "G06N"},
            {"H01L", "B60L"},
        ]
        labels, matrix, total_connections = build_cooccurrence(patent_sets, top_n=3)
        assert len(labels) >= 2
        assert len(matrix) == len(labels)
        assert total_connections > 0

    def test_single_patent(self):
        labels, matrix, total = build_cooccurrence([{"H01L", "G06N"}], top_n=5)
        assert len(labels) == 2
        assert total == 1

    def test_too_few_codes(self):
        labels, matrix, total = build_cooccurrence([{"H01L"}], top_n=5)
        assert len(labels) <= 1

    def test_jaccard_symmetry(self):
        patent_sets = [
            {"A", "B", "C"},
            {"A", "B"},
            {"B", "C"},
        ]
        labels, matrix, _ = build_cooccurrence(patent_sets, top_n=3)
        n = len(labels)
        for i in range(n):
            for j in range(n):
                assert matrix[i][j] == matrix[j][i]


# ============================================================================
# build_cooccurrence_with_years()
# ============================================================================


class TestBuildCooccurrenceWithYears:
    def test_year_data_structure(self):
        data = [
            ({"H01L", "G06N"}, 2020),
            ({"H01L", "B60L"}, 2021),
            ({"G06N", "B60L"}, 2021),
        ]
        labels, matrix, total_conn, year_data = build_cooccurrence_with_years(data, top_n=5)
        assert "min_year" in year_data
        assert "max_year" in year_data
        assert year_data["min_year"] == 2020
        assert year_data["max_year"] == 2021
        assert "pair_counts" in year_data
        assert "cpc_counts" in year_data

    def test_too_few_codes(self):
        data = [({"H01L"}, 2020)]
        labels, matrix, total, year_data = build_cooccurrence_with_years(data, top_n=5)
        assert len(labels) <= 1


# ============================================================================
# build_jaccard_from_sql()
# ============================================================================


class TestBuildJaccardFromSql:
    def test_basic(self):
        top_codes = ["H01L", "G06N", "B60L"]
        code_counts = {"H01L": 100, "G06N": 80, "B60L": 50}
        pair_counts = [("H01L", "G06N", 40)]

        matrix, total = build_jaccard_from_sql(top_codes, code_counts, pair_counts)

        assert len(matrix) == 3
        assert total == 1
        # Jaccard: 40 / (100 + 80 - 40) = 40/140
        expected_j = 40 / 140
        idx_h01l = 0
        idx_g06n = 1
        assert matrix[idx_h01l][idx_g06n] == pytest.approx(expected_j, abs=0.001)
        assert matrix[idx_g06n][idx_h01l] == pytest.approx(expected_j, abs=0.001)

    def test_empty(self):
        matrix, total = build_jaccard_from_sql([], {}, [])
        assert matrix == []
        assert total == 0

    def test_one_code(self):
        matrix, total = build_jaccard_from_sql(["H01L"], {"H01L": 10}, [])
        assert matrix == []


# ============================================================================
# build_year_data_from_aggregates()
# ============================================================================


class TestBuildYearDataFromAggregates:
    def test_basic(self):
        all_codes = ["H01L", "G06N"]
        cpc_year = [("H01L", 2020, 50), ("G06N", 2020, 30), ("H01L", 2021, 60)]
        pair_year = [("G06N", "H01L", 2020, 20)]

        result = build_year_data_from_aggregates(all_codes, cpc_year, pair_year)

        assert result["min_year"] == 2020
        assert result["max_year"] == 2021
        assert "2020" in result["cpc_counts"]
        assert result["cpc_counts"]["2020"]["H01L"] == 50

    def test_empty(self):
        result = build_year_data_from_aggregates([], [], [])
        assert result["min_year"] == 0
        assert result["max_year"] == 0


# ============================================================================
# assign_colors()
# ============================================================================


class TestAssignColors:
    def test_known_sections(self):
        labels = ["A01B", "H01L", "G06N"]
        colors = assign_colors(labels)
        assert len(colors) == 3
        assert colors[0] == "#ef4444"  # A -> rot
        assert colors[1] == "#ec4899"  # H -> pink
        assert colors[2] == "#8b5cf6"  # G -> violett

    def test_unknown_section(self):
        colors = assign_colors(["Z99"])
        assert colors[0] == "#9ca3af"  # Fallback grau

    def test_empty(self):
        assert assign_colors([]) == []
