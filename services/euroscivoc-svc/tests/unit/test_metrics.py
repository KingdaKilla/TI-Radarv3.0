"""Unit-Tests fuer euroscivoc-svc domain.metrics.

AP4 · CRIT-2: Shannon-Index mathematisch korrekt auch bei <2 Kategorien.

Der Shannon-Index ist definiert als:

    H = -Sigma(p_i * log(p_i))

Bei genau einer Kategorie mit p=1 gilt: -1 * log(1) = 0.

Defensive Implementierungen muessen zusaetzlich sicherstellen, dass:
- leere Eingaben -> 0.0
- Eingaben mit einer einzigen Kategorie -> 0.0 (nicht rauschen durch Float-Ungenauigkeit)
- Eingaben mit k Kategorien gleich verteilt -> log2(k) (bzw. ln(k) je nach Basis)
"""

from __future__ import annotations

import math

import pytest

from src.domain.metrics import (
    classify_interdisciplinarity,
    compute_shannon_index,
    compute_simpson_index,
)


# ---------------------------------------------------------------------------
# Shannon-Index: Defensive Edge-Cases
# ---------------------------------------------------------------------------


class TestShannonEdgeCases:
    """Shannon-Index muss bei <2 Kategorien garantiert 0.0 zurueckliefern."""

    def test_shannon_empty_dict_is_zero(self) -> None:
        assert compute_shannon_index({}) == 0.0

    def test_shannon_single_category_is_zero(self) -> None:
        """-1*log(1) = 0, mathematisch exakt 0."""
        assert compute_shannon_index({"A": 5}) == 0.0

    def test_shannon_single_category_large_count(self) -> None:
        assert compute_shannon_index({"solid_state_battery": 10_000}) == 0.0

    def test_shannon_single_category_float_value(self) -> None:
        """Auch ein einzelner Float-Wert muss exakt 0 ergeben."""
        assert compute_shannon_index({"A": 1}) == 0.0

    def test_shannon_zero_count_treated_safely(self) -> None:
        assert compute_shannon_index({"A": 0}) == 0.0

    def test_shannon_all_zero_counts(self) -> None:
        assert compute_shannon_index({"A": 0, "B": 0}) == 0.0


# ---------------------------------------------------------------------------
# Shannon-Index: Mathematisch korrekte Werte
# ---------------------------------------------------------------------------


class TestShannonMath:
    """Shannon-Index bei bekannten Verteilungen."""

    def test_shannon_uniform_two_categories_is_log2_2(self) -> None:
        """Zwei gleichverteilte Kategorien -> log2(2) = 1.0."""
        result = compute_shannon_index({"A": 10, "B": 10})
        assert result == pytest.approx(1.0, rel=1e-3)

    def test_shannon_uniform_four_categories_is_log2_4(self) -> None:
        """Vier gleichverteilte Kategorien -> log2(4) = 2.0."""
        result = compute_shannon_index({"A": 1, "B": 1, "C": 1, "D": 1})
        assert result == pytest.approx(2.0, rel=1e-3)

    def test_shannon_skewed_distribution(self) -> None:
        """Sehr ungleiche Verteilung -> Wert nahe 0, aber > 0."""
        result = compute_shannon_index({"A": 100, "B": 1})
        assert 0.0 < result < 0.2


# ---------------------------------------------------------------------------
# Simpson-Index
# ---------------------------------------------------------------------------


class TestSimpsonIndex:
    def test_simpson_empty(self) -> None:
        assert compute_simpson_index({}) == 0.0

    def test_simpson_single_category(self) -> None:
        assert compute_simpson_index({"A": 10}) == 0.0


# ---------------------------------------------------------------------------
# Interdisziplinaritaet-Klassifikation
# ---------------------------------------------------------------------------


class TestClassifyInterdisciplinarity:
    def test_single_field_not_interdisciplinary(self) -> None:
        """Bei 1 Feld darf die Klassifikation nicht interdisziplinaer sein,
        unabhaengig vom (korrekt 0) Shannon-Wert.
        """
        assert classify_interdisciplinarity(shannon=0.0, active_fields=1) is False

    def test_three_fields_is_interdisciplinary(self) -> None:
        assert classify_interdisciplinarity(shannon=1.5, active_fields=3) is True

    def test_high_shannon_is_interdisciplinary(self) -> None:
        assert classify_interdisciplinarity(shannon=2.5, active_fields=2) is True
