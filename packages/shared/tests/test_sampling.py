"""Tests fuer shared.domain.sampling — Stratifizierte Stichprobenziehung."""

from __future__ import annotations

import pytest

from shared.domain.sampling import (
    SamplingResult,
    StratumInfo,
    estimate_jaccard_confidence,
    stratified_sample,
)


# ============================================================================
# stratified_sample()
# ============================================================================


class TestStratifiedSample:
    def test_trivial_case_no_sampling(self):
        """Population < target_size: keine Stichprobe noetig."""
        data = [
            ({"A01", "B02"}, 2020),
            ({"C03", "D04"}, 2021),
        ]
        result = stratified_sample(data, target_size=100)
        assert result.was_sampled is False
        assert result.sample_size == 2
        assert result.population_size == 2
        assert result.sampling_fraction == 1.0

    def test_exact_target_size(self):
        """Population == target_size: keine Stichprobe."""
        data = [({"A", "B"}, 2020)] * 10
        result = stratified_sample(data, target_size=10)
        assert result.was_sampled is False
        assert result.sample_size == 10

    def test_actual_sampling(self):
        """Population > target_size: Stichprobe wird gezogen."""
        # 100 Patente ueber 5 Jahre (20 pro Jahr)
        data = []
        for year in range(2020, 2025):
            for _ in range(20):
                data.append(({"H01L", "G06N"}, year))

        result = stratified_sample(data, target_size=50)

        assert result.was_sampled is True
        assert result.sample_size == 50
        assert result.population_size == 100
        assert result.sampling_fraction == pytest.approx(0.5)

    def test_proportional_allocation(self):
        """Stichprobe wahrt Jahresanteile proportional."""
        data = []
        # 2020: 80 Patente, 2021: 20 Patente
        for _ in range(80):
            data.append(({"A", "B"}, 2020))
        for _ in range(20):
            data.append(({"C", "D"}, 2021))

        result = stratified_sample(data, target_size=50)

        assert result.was_sampled is True
        # 2020 sollte ca. 80% der Stichprobe haben
        info_2020 = result.strata_info[2020]
        info_2021 = result.strata_info[2021]
        assert info_2020.sample_count > info_2021.sample_count

    def test_census_threshold(self):
        """Kleine Schichten werden vollstaendig uebernommen."""
        data = []
        for _ in range(100):
            data.append(({"A", "B"}, 2020))
        for _ in range(3):
            data.append(({"C", "D"}, 2021))

        result = stratified_sample(data, target_size=50, census_threshold=5)

        # 2021 hat nur 3 Elemente -> Census-Stratum
        assert result.strata_info[2021].is_census is True
        assert result.strata_info[2021].sample_count == 3

    def test_deterministic(self):
        """Identischer Input -> identischer Output."""
        data = [({"A", "B"}, y) for y in range(2015, 2025) for _ in range(10)]
        r1 = stratified_sample(data, target_size=50)
        r2 = stratified_sample(data, target_size=50)
        assert r1.sampled_data == r2.sampled_data
        assert r1.sample_size == r2.sample_size

    def test_invalid_target_size(self):
        with pytest.raises(ValueError):
            stratified_sample([], target_size=0)
        with pytest.raises(ValueError):
            stratified_sample([], target_size=-1)

    def test_empty_input(self):
        result = stratified_sample([], target_size=10)
        assert result.was_sampled is False
        assert result.sample_size == 0

    def test_strata_info_structure(self):
        data = [({"A", "B"}, 2020)] * 30 + [({"C", "D"}, 2021)] * 20
        result = stratified_sample(data, target_size=25)
        assert 2020 in result.strata_info
        assert 2021 in result.strata_info
        for year, info in result.strata_info.items():
            assert isinstance(info, StratumInfo)
            assert info.population_count > 0
            assert info.sample_count > 0
            assert info.sample_count <= info.population_count


# ============================================================================
# estimate_jaccard_confidence()
# ============================================================================


class TestEstimateJaccardConfidence:
    def test_zero_union(self):
        result = estimate_jaccard_confidence(0, 0, 100, 1000)
        assert result.jaccard == 0.0
        assert result.standard_error == 0.0

    def test_full_census(self):
        """Vollerhebung: kein Sampling Error."""
        result = estimate_jaccard_confidence(50, 100, 1000, 1000)
        assert result.jaccard == pytest.approx(0.5)
        assert result.standard_error == 0.0
        assert result.ci_lower == result.ci_upper == result.jaccard

    def test_sampled_population(self):
        """Stichprobe: Konfidenzintervall existiert."""
        result = estimate_jaccard_confidence(30, 100, 500, 10000)
        assert result.jaccard == pytest.approx(0.3)
        assert result.standard_error > 0
        assert result.ci_lower < result.jaccard
        assert result.ci_upper > result.jaccard
        assert result.ci_lower >= 0.0
        assert result.ci_upper <= 1.0

    def test_confidence_interval_width(self):
        """Groessere Stichprobe -> kleineres KI."""
        small = estimate_jaccard_confidence(50, 100, 100, 10000)
        large = estimate_jaccard_confidence(500, 1000, 1000, 10000)
        assert small.margin_of_error_95 > large.margin_of_error_95

    def test_perfect_overlap(self):
        result = estimate_jaccard_confidence(100, 100, 100, 100)
        assert result.jaccard == pytest.approx(1.0)

    def test_no_overlap(self):
        result = estimate_jaccard_confidence(0, 100, 100, 100)
        assert result.jaccard == pytest.approx(0.0)
