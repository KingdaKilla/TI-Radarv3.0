"""Tests fuer shared.domain.eu_countries — EU/EEA-Laenderset."""

from __future__ import annotations

from shared.domain.eu_countries import EU_EEA_COUNTRIES, is_european


class TestEuCountries:
    def test_eu27_members(self):
        eu27 = ["AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI",
                "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT",
                "NL", "PL", "PT", "RO", "SE", "SI", "SK"]
        for code in eu27:
            assert code in EU_EEA_COUNTRIES, f"{code} fehlt in EU_EEA_COUNTRIES"

    def test_eea_members(self):
        for code in ["CH", "NO", "IS", "LI"]:
            assert code in EU_EEA_COUNTRIES

    def test_gb_included(self):
        assert "GB" in EU_EEA_COUNTRIES
        assert "UK" in EU_EEA_COUNTRIES

    def test_cordis_alias(self):
        assert "EL" in EU_EEA_COUNTRIES  # CORDIS-Alias fuer GR

    def test_non_european(self):
        for code in ["US", "CN", "JP", "KR", "IN", "BR"]:
            assert code not in EU_EEA_COUNTRIES


class TestIsEuropean:
    def test_german(self):
        assert is_european("DE") is True

    def test_us(self):
        assert is_european("US") is False

    def test_case_insensitive(self):
        assert is_european("de") is True
        assert is_european("De") is True

    def test_whitespace(self):
        assert is_european("  DE  ") is True

    def test_empty(self):
        assert is_european("") is False
