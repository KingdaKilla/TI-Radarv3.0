"""Tests fuer Reciprocal Rank Fusion (Cormack et al. 2009)."""
from __future__ import annotations

from src.fusion import reciprocal_rank_fusion


class TestReciprocalRankFusion:
    def test_single_list_preserves_order(self):
        """Eine einzelne Liste behaelt die Reihenfolge bei."""
        result = reciprocal_rank_fusion([["A", "B", "C"]], k=60)
        ids = [doc_id for doc_id, _ in result]
        assert ids == ["A", "B", "C"]

    def test_two_identical_lists_boost_scores(self):
        """Zwei identische Listen erhoehen Scores, behalten Ordnung."""
        result = reciprocal_rank_fusion([["A", "B", "C"], ["A", "B", "C"]], k=60)
        ids = [doc_id for doc_id, _ in result]
        assert ids == ["A", "B", "C"]
        # Scores should be double compared to single list
        single = reciprocal_rank_fusion([["A", "B", "C"]], k=60)
        for (_, double_score), (_, single_score) in zip(result, single):
            assert abs(double_score - 2 * single_score) < 1e-10

    def test_disjoint_lists_union(self):
        """Disjunkte Listen ergeben Vereinigung, sortiert nach Score."""
        result = reciprocal_rank_fusion([["A", "B"], ["C", "D"]], k=60)
        ids = {doc_id for doc_id, _ in result}
        assert ids == {"A", "B", "C", "D"}
        # First items from each list should score highest (tied)
        assert len(result) == 4

    def test_overlap_boosts_rank(self):
        """Ueberlappende Dokumente werden hoeher gerankt.

        List1: A(idx0)->1/61, B(idx1)->1/62, C(idx2)->1/63
        List2: C(idx0)->1/61, B(idx1)->1/62, D(idx2)->1/63
        Combined:
          A: 1/61              = 0.016393
          B: 1/62 + 1/62      = 0.032258
          C: 1/63 + 1/61      = 0.032265
          D: 1/63             = 0.015873
        C > B > A > D (C wins by a tiny margin over B).
        """
        result = reciprocal_rank_fusion([["A", "B", "C"], ["C", "B", "D"]], k=60)
        ids = [doc_id for doc_id, _ in result]
        # B and C both appear in both lists -> they must be top-2
        assert set(ids[:2]) == {"B", "C"}
        # C has a marginally higher score: 1/63+1/61 > 2/62
        # 1/63+1/61 = (61+63)/(63*61) = 124/3843 ≈ 0.032266
        # 2/62      = 1/31            = 124/3844 ≈ 0.032258 (actually 2/62 = 1/31)
        # Verify: 124/3843 > 124/3844 -> yes, C > B
        assert ids[0] == "C"
        assert ids[1] == "B"
        # A and D come last
        assert set(ids[2:]) == {"A", "D"}
        assert ids[2] == "A"  # A: 1/61 > D: 1/63
        assert ids[3] == "D"

    def test_empty_lists(self):
        """Leere Eingabe ergibt leeres Ergebnis."""
        assert reciprocal_rank_fusion([], k=60) == []
        assert reciprocal_rank_fusion([[]], k=60) == []

    def test_k_parameter_affects_scores(self):
        """k-Parameter beeinflusst Score-Spread."""
        result_k1 = reciprocal_rank_fusion([["A", "B"]], k=1)
        result_k60 = reciprocal_rank_fusion([["A", "B"]], k=60)
        # With k=1: A=1/2=0.5, B=1/3=0.333 -> spread=0.167
        # With k=60: A=1/61=0.0164, B=1/62=0.0161 -> spread=0.0003
        spread_k1 = result_k1[0][1] - result_k1[1][1]
        spread_k60 = result_k60[0][1] - result_k60[1][1]
        assert spread_k1 > spread_k60  # Smaller k = more spread

    def test_top_n_truncation(self):
        """top_n Parameter begrenzt Ergebnisgroesse."""
        result = reciprocal_rank_fusion([["A", "B", "C", "D", "E"]], k=60, top_n=3)
        assert len(result) == 3
        ids = [doc_id for doc_id, _ in result]
        assert ids == ["A", "B", "C"]

    def test_top_n_none_returns_all(self):
        """Ohne top_n werden alle Ergebnisse zurueckgegeben."""
        result = reciprocal_rank_fusion([["A", "B", "C", "D", "E"]], k=60)
        assert len(result) == 5

    def test_top_n_larger_than_results(self):
        """top_n groesser als Ergebnisse gibt alle zurueck."""
        result = reciprocal_rank_fusion([["A", "B"]], k=60, top_n=10)
        assert len(result) == 2

    def test_scores_are_positive(self):
        """Alle RRF-Scores muessen positiv sein."""
        result = reciprocal_rank_fusion([["A", "B", "C"], ["D", "E"]], k=60)
        for _, score in result:
            assert score > 0.0

    def test_scores_descending_order(self):
        """Ergebnisse sind absteigend nach Score sortiert."""
        result = reciprocal_rank_fusion(
            [["A", "B", "C", "D"], ["D", "C", "B", "A"]], k=60
        )
        scores = [score for _, score in result]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]

    def test_three_lists_fusion(self):
        """Fusion ueber drei Listen funktioniert korrekt."""
        result = reciprocal_rank_fusion(
            [["A", "B", "C"], ["B", "C", "A"], ["C", "A", "B"]], k=60
        )
        ids = [doc_id for doc_id, _ in result]
        # Each document appears at ranks 0,1,2 across the three lists
        # A: 1/61 + 1/63 + 1/62, B: 1/62 + 1/61 + 1/63, C: 1/63 + 1/62 + 1/61
        # All three have the same combined score -> order may vary but all present
        assert set(ids) == {"A", "B", "C"}
        # All scores should be equal
        scores = [score for _, score in result]
        assert abs(scores[0] - scores[1]) < 1e-10
        assert abs(scores[1] - scores[2]) < 1e-10

    def test_default_k_is_60(self):
        """Standard-k-Wert ist 60 (Cormack et al. 2009)."""
        result_default = reciprocal_rank_fusion([["A", "B"]])
        result_k60 = reciprocal_rank_fusion([["A", "B"]], k=60)
        assert result_default == result_k60
