"""Unit-Tests fuer den bipartiten Jaccard cooperation_score (UC6).

Der Score normalisiert absolute Kooperationszahlen auf die Gesamtaktivitaet
der beiden Laender: (2 * co_projects) / (projects_a + projects_b).

Diese Tests decken die Formel selbst sowie Edge-Cases ab (0 co-projects,
Division-by-Zero-Schutz, Clamping, Symmetrie).
"""

from __future__ import annotations

import math

import pytest

from src.service import _bipartite_jaccard


# ---------------------------------------------------------------------------
# Formel-Basis
# ---------------------------------------------------------------------------


class TestBipartiteJaccardFormula:
    """Prueft die grundlegende Formel (2 * co) / (a + b)."""

    def test_hoher_score_bei_starker_kooperation(self) -> None:
        """(2*396) / (400+400) = 0.99 — DE/FR-aehnliches Szenario."""
        score = _bipartite_jaccard(co_projects=396, projects_a=400, projects_b=400)
        assert math.isclose(score, 0.99, rel_tol=1e-9)

    def test_niedriger_score_bei_geringer_kooperation(self) -> None:
        """(2*10) / (100+100) = 0.1 — nur 10 % der Aktivitaet gemeinsam."""
        score = _bipartite_jaccard(co_projects=10, projects_a=100, projects_b=100)
        assert math.isclose(score, 0.1, rel_tol=1e-9)

    def test_perfekte_kooperation_gibt_eins(self) -> None:
        """co == a == b -> Score = 1.0 (voellig deckungsgleich)."""
        score = _bipartite_jaccard(co_projects=50, projects_a=50, projects_b=50)
        assert math.isclose(score, 1.0, rel_tol=1e-9)

    def test_asymmetrische_groessen(self) -> None:
        """Grosses Land + kleines Land: (2*5) / (1000+5) ~ 0.00995."""
        score = _bipartite_jaccard(co_projects=5, projects_a=1000, projects_b=5)
        assert math.isclose(score, 10.0 / 1005.0, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# Edge-Cases
# ---------------------------------------------------------------------------


class TestBipartiteJaccardEdgeCases:
    """Defensive Branches: leere Zaehler/Nenner sollen nicht crashen."""

    def test_null_coprojects_gibt_null_score(self) -> None:
        """0 co-projects -> 0 score, unabhaengig von Totals."""
        assert _bipartite_jaccard(co_projects=0, projects_a=100, projects_b=100) == 0.0

    def test_negativer_coprojects_gibt_null(self) -> None:
        """Defensiv: negative Werte fuehren zu 0 (keine Exception)."""
        assert _bipartite_jaccard(co_projects=-5, projects_a=100, projects_b=100) == 0.0

    def test_nenner_null_gibt_null_score(self) -> None:
        """Wenn beide Laender-Totals 0 sind, Rueckgabe 0.0 statt ZeroDivisionError."""
        assert _bipartite_jaccard(co_projects=5, projects_a=0, projects_b=0) == 0.0

    def test_negativer_nenner_gibt_null(self) -> None:
        """Defensive Pruefung auf <= 0 auch bei absurden Eingaben."""
        assert _bipartite_jaccard(co_projects=5, projects_a=-10, projects_b=5) == 0.0

    def test_score_ist_in_null_bis_eins(self) -> None:
        """Clamping: Score liegt immer in [0, 1]."""
        score = _bipartite_jaccard(co_projects=600, projects_a=500, projects_b=500)
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# Eigenschaften (Property-artig, ohne Hypothesis-Dependency)
# ---------------------------------------------------------------------------


class TestBipartiteJaccardProperties:
    """Strukturelle Eigenschaften der Formel."""

    def test_symmetrie_a_b_vertauschen(self) -> None:
        """Score(a, b) == Score(b, a)."""
        s1 = _bipartite_jaccard(co_projects=20, projects_a=150, projects_b=80)
        s2 = _bipartite_jaccard(co_projects=20, projects_a=80, projects_b=150)
        assert math.isclose(s1, s2, rel_tol=1e-12)

    @pytest.mark.parametrize(
        ("co", "a", "b", "expected"),
        [
            (1, 10, 10, 0.1),
            (5, 10, 10, 0.5),
            (10, 10, 10, 1.0),
            (0, 10, 10, 0.0),
            (50, 100, 100, 0.5),
        ],
    )
    def test_parametrische_werte(self, co: int, a: int, b: int, expected: float) -> None:
        """Tabellarische Gegenprobe fuer typische Input-Kombinationen."""
        assert math.isclose(
            _bipartite_jaccard(co_projects=co, projects_a=a, projects_b=b),
            expected,
            rel_tol=1e-9,
        )


# ---------------------------------------------------------------------------
# Integration-Light: collab_pairs + Jaccard zusammen
# ---------------------------------------------------------------------------


class TestCooperationPairsHaveNonzeroScore:
    """Verifiziert, dass realistische Repository-Outputs Nicht-Null-Scores erzeugen."""

    def test_pairs_have_nonzero_score(self) -> None:
        """Simuliert typischen Repository-Output und prueft, dass jeder Pair
        mit co_project_count > 0 auch einen cooperation_score > 0 bekommt."""
        collab_pairs = [
            {
                "country_a": "DE",
                "country_b": "FR",
                "co_project_count": 120,
                "projects_a": 400,
                "projects_b": 350,
            },
            {
                "country_a": "DE",
                "country_b": "NL",
                "co_project_count": 45,
                "projects_a": 400,
                "projects_b": 120,
            },
            {
                "country_a": "ES",
                "country_b": "IT",
                "co_project_count": 60,
                "projects_a": 200,
                "projects_b": 220,
            },
        ]

        scored = [
            {
                **p,
                "cooperation_score": _bipartite_jaccard(
                    co_projects=p["co_project_count"],
                    projects_a=p["projects_a"],
                    projects_b=p["projects_b"],
                ),
            }
            for p in collab_pairs
        ]

        assert all(p["cooperation_score"] > 0.0 for p in scored)
        assert all(0.0 <= p["cooperation_score"] <= 1.0 for p in scored)

    def test_pair_without_totals_fallbacks_to_zero(self) -> None:
        """Wenn projects_a/projects_b fehlen (Legacy-Repo), bleibt Score 0."""
        p = {
            "country_a": "DE",
            "country_b": "FR",
            "co_project_count": 120,
            # keine projects_a/projects_b
        }
        score = _bipartite_jaccard(
            co_projects=int(p["co_project_count"]),
            projects_a=int(p.get("projects_a", 0)),
            projects_b=int(p.get("projects_b", 0)),
        )
        assert score == 0.0
