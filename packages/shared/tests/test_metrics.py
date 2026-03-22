"""Tests fuer shared.domain.metrics — CAGR, HHI, S-Curve-Konfidenz, Phasenklassifikation."""

from __future__ import annotations

import math

import pytest

from shared.domain.metrics import (
    cagr,
    classify_maturity_phase,
    cr4,
    detect_decline,
    hhi_concentration_level,
    hhi_index,
    merge_country_data,
    merge_time_series,
    s_curve_confidence,
    yoy_growth,
)


# ============================================================================
# cagr()
# ============================================================================


class TestCagr:
    def test_positive_growth(self):
        # 100 -> 200 ueber 5 Jahre = ca. 14.87%
        result = cagr(100.0, 200.0, 5)
        assert result == pytest.approx(14.87, abs=0.1)

    def test_no_growth(self):
        result = cagr(100.0, 100.0, 10)
        assert result == pytest.approx(0.0)

    def test_negative_growth(self):
        result = cagr(200.0, 100.0, 5)
        assert result < 0

    def test_one_period(self):
        result = cagr(100.0, 150.0, 1)
        assert result == pytest.approx(50.0)

    def test_zero_periods(self):
        assert cagr(100.0, 200.0, 0) == 0.0

    def test_negative_periods(self):
        assert cagr(100.0, 200.0, -1) == 0.0

    def test_zero_first_value(self):
        assert cagr(0.0, 200.0, 5) == 0.0

    def test_zero_last_value(self):
        assert cagr(100.0, 0.0, 5) == 0.0

    def test_negative_first_value(self):
        assert cagr(-10.0, 200.0, 5) == 0.0

    def test_large_values(self):
        result = cagr(1_000_000, 10_000_000, 10)
        assert result > 0


# ============================================================================
# hhi_index()
# ============================================================================


class TestHhiIndex:
    def test_monopoly(self):
        # Ein Akteur mit 100% Marktanteil
        assert hhi_index([1.0]) == pytest.approx(10_000)

    def test_duopoly_equal(self):
        # Zwei Akteure mit je 50%
        assert hhi_index([0.5, 0.5]) == pytest.approx(5_000)

    def test_fragmented_market(self):
        # 10 Akteure mit je 10%
        shares = [0.1] * 10
        assert hhi_index(shares) == pytest.approx(1_000)

    def test_empty(self):
        assert hhi_index([]) == 0.0

    def test_three_actors(self):
        shares = [0.6, 0.3, 0.1]
        expected = (0.36 + 0.09 + 0.01) * 10_000
        assert hhi_index(shares) == pytest.approx(expected)

    def test_single_small_share(self):
        assert hhi_index([0.01]) == pytest.approx(1.0)


# ============================================================================
# hhi_concentration_level()
# ============================================================================


class TestHhiConcentrationLevel:
    def test_low(self):
        assert hhi_concentration_level(500) == ("Low", "Gering")

    def test_moderate(self):
        assert hhi_concentration_level(2000) == ("Moderate", "Moderat")

    def test_high(self):
        assert hhi_concentration_level(5000) == ("High", "Hoch")

    def test_boundary_1500(self):
        assert hhi_concentration_level(1500) == ("Moderate", "Moderat")

    def test_boundary_2500(self):
        assert hhi_concentration_level(2500) == ("High", "Hoch")

    def test_zero(self):
        assert hhi_concentration_level(0) == ("Low", "Gering")


# ============================================================================
# cr4()
# ============================================================================


class TestCR4:
    def test_empty_list(self):
        """Leere Liste ergibt 0.0."""
        assert cr4([]) == 0.0

    def test_single_actor(self):
        """Ein Akteur: CR4 = dessen Anteil."""
        assert cr4([0.75]) == pytest.approx(0.75)

    def test_four_equal(self):
        """Vier gleiche Akteure mit je 25% ergeben CR4 = 1.0."""
        assert cr4([0.25, 0.25, 0.25, 0.25]) == pytest.approx(1.0)

    def test_more_than_four(self):
        """Nur die Top-4 Anteile werden summiert."""
        shares = [0.3, 0.2, 0.15, 0.1, 0.1, 0.05, 0.05, 0.05]
        expected = 0.3 + 0.2 + 0.15 + 0.1  # = 0.75
        assert cr4(shares) == pytest.approx(expected)

    def test_monopoly(self):
        """Monopol: Ein Akteur mit 100% ergibt CR4 = 1.0."""
        assert cr4([1.0]) == pytest.approx(1.0)

    def test_fragmented_market(self):
        """Stark fragmentierter Markt: 10 Akteure mit je 10%."""
        shares = [0.1] * 10
        assert cr4(shares) == pytest.approx(0.4)

    def test_unsorted_input(self):
        """Ungeordnete Eingabe wird korrekt sortiert."""
        shares = [0.05, 0.3, 0.1, 0.2, 0.15, 0.1, 0.05, 0.05]
        expected = 0.3 + 0.2 + 0.15 + 0.1  # = 0.75
        assert cr4(shares) == pytest.approx(expected)


# ============================================================================
# s_curve_confidence()
# ============================================================================


class TestSCurveConfidence:
    def test_perfect_data(self):
        result = s_curve_confidence(0.99, 20, 500)
        assert result == pytest.approx(0.95)

    def test_minimal_data(self):
        result = s_curve_confidence(0.3, 3, 10)
        assert 0.1 <= result <= 0.95

    def test_floor_at_0_1(self):
        result = s_curve_confidence(0.0, 0, 0)
        assert result >= 0.1

    def test_cap_at_0_95(self):
        result = s_curve_confidence(1.0, 100, 10_000)
        assert result <= 0.95

    def test_r_squared_weight(self):
        high = s_curve_confidence(0.9, 10, 100)
        low = s_curve_confidence(0.1, 10, 100)
        assert high > low


# ============================================================================
# detect_decline()
# ============================================================================


class TestDetectDecline:
    def test_no_decline_growing(self):
        """Wachsende Reihe ergibt kein Decline."""
        assert detect_decline([10, 20, 30, 40]) is False

    def test_decline_detected(self):
        """Zwei konsekutive Rueckgaenge erkennen Decline."""
        assert detect_decline([100, 90, 80]) is True

    def test_single_dip_not_decline(self):
        """Ein einzelner Rueckgang gefolgt von Erholung ist kein Decline."""
        assert detect_decline([100, 90, 95]) is False

    def test_insufficient_data(self):
        """Zu wenige Datenpunkte: kein Decline erkennbar."""
        assert detect_decline([100]) is False

    def test_plateau_not_decline(self):
        """Gleichbleibende Werte sind kein Decline."""
        assert detect_decline([100, 100, 100]) is False

    def test_three_consecutive_declines(self):
        """Drei konsekutive Rueckgaenge mit consecutive_years=3."""
        assert detect_decline([100, 90, 80, 70], consecutive_years=3) is True

    def test_two_values_insufficient(self):
        """Zwei Werte reichen nicht fuer consecutive_years=2."""
        assert detect_decline([100, 90]) is False

    def test_decline_at_end_only(self):
        """Decline wird nur an den letzten Werten geprueft."""
        # Wachstum gefolgt von Decline am Ende
        assert detect_decline([10, 20, 30, 25, 20]) is True

    def test_custom_consecutive_years(self):
        """Benutzerdefinierte Anzahl konsekutiver Jahre."""
        # 2 Rueckgaenge reichen nicht bei consecutive_years=3
        assert detect_decline([100, 90, 80], consecutive_years=3) is False


# ============================================================================
# classify_maturity_phase()
# ============================================================================


class TestClassifyMaturityPhase:
    def test_scurve_emerging(self):
        phase_en, phase_de, conf = classify_maturity_phase([], maturity_percent=5.0, r_squared=0.8)
        assert phase_en == "Emerging"
        assert phase_de == "Aufkommend"

    def test_scurve_growing(self):
        phase_en, phase_de, _ = classify_maturity_phase([], maturity_percent=30.0, r_squared=0.9)
        assert phase_en == "Growing"
        assert phase_de == "Wachsend"

    def test_scurve_mature(self):
        phase_en, phase_de, _ = classify_maturity_phase([], maturity_percent=70.0, r_squared=0.85)
        assert phase_en == "Mature"
        assert phase_de == "Ausgereift"

    def test_scurve_saturation(self):
        phase_en, phase_de, _ = classify_maturity_phase([], maturity_percent=95.0, r_squared=0.9)
        assert phase_en == "Saturation"

    def test_fallback_insufficient_data(self):
        phase_en, _, conf = classify_maturity_phase([1, 2])
        assert phase_en == "Unknown"
        assert conf == 0.0

    def test_fallback_empty(self):
        phase_en, _, _ = classify_maturity_phase([])
        assert phase_en == "Unknown"

    def test_fallback_all_zeros(self):
        phase_en, _, _ = classify_maturity_phase([0, 0, 0, 0])
        assert phase_en == "Unknown"

    def test_fallback_strong_growth(self):
        counts = [10, 20, 30, 50, 80, 120]
        phase_en, _, _ = classify_maturity_phase(counts)
        assert phase_en in ("Emerging", "Growing")

    def test_fallback_stable(self):
        counts = [100, 102, 98, 101, 99, 100]
        phase_en, _, _ = classify_maturity_phase(counts)
        assert phase_en in ("Mature", "Growing")

    def test_confidence_capped(self):
        _, _, conf = classify_maturity_phase([], maturity_percent=50.0, r_squared=1.0)
        assert conf <= 0.95


# ============================================================================
# yoy_growth()
# ============================================================================


class TestYoyGrowth:
    def test_positive_growth(self):
        assert yoy_growth(110, 100) == pytest.approx(10.0)

    def test_negative_growth(self):
        assert yoy_growth(80, 100) == pytest.approx(-20.0)

    def test_zero_growth(self):
        assert yoy_growth(100, 100) == pytest.approx(0.0)

    def test_zero_previous(self):
        assert yoy_growth(100, 0) is None

    def test_double(self):
        assert yoy_growth(200, 100) == pytest.approx(100.0)


# ============================================================================
# merge_time_series()
# ============================================================================


class TestMergeTimeSeries:
    def test_basic_merge(self):
        patent_years = [{"year": 2020, "count": 10}, {"year": 2021, "count": 20}]
        project_years = [{"year": 2020, "count": 5}]
        pub_years = [{"year": 2021, "count": 3}]

        result = merge_time_series(patent_years, project_years, pub_years, 2020, 2021)

        assert len(result) == 2
        assert result[0]["year"] == 2020
        assert result[0]["patents"] == 10
        assert result[0]["projects"] == 5
        assert result[0]["publications"] == 0

        assert result[1]["year"] == 2021
        assert result[1]["patents"] == 20
        assert result[1]["publications"] == 3

    def test_empty_lists(self):
        result = merge_time_series([], [], [], 2020, 2022)
        assert len(result) == 3
        for entry in result:
            assert entry["patents"] == 0

    def test_growth_rates_in_second_entry(self):
        patent_years = [{"year": 2020, "count": 100}, {"year": 2021, "count": 150}]
        result = merge_time_series(patent_years, [], [], 2020, 2021)
        assert "patents_growth" not in result[0]
        assert result[1]["patents_growth"] == pytest.approx(50.0)


# ============================================================================
# merge_country_data()
# ============================================================================


class TestMergeCountryData:
    def test_basic_merge(self):
        patents = [{"country": "DE", "count": 100}, {"country": "FR", "count": 50}]
        projects = [{"country": "DE", "count": 30}, {"country": "IT", "count": 20}]

        result = merge_country_data(patents, projects)

        assert result[0]["country"] == "DE"
        assert result[0]["total"] == 130
        assert result[0]["patents"] == 100
        assert result[0]["projects"] == 30

    def test_sorted_by_total(self):
        patents = [{"country": "FR", "count": 200}]
        projects = [{"country": "DE", "count": 300}]

        result = merge_country_data(patents, projects)
        assert result[0]["country"] == "DE"

    def test_limit(self):
        patents = [
            {"country": "DE", "count": 100},
            {"country": "FR", "count": 50},
            {"country": "IT", "count": 25},
        ]
        result = merge_country_data(patents, [], limit=2)
        assert len(result) == 2

    def test_empty(self):
        result = merge_country_data([], [])
        assert result == []
