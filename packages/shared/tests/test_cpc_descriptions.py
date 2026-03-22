"""Tests fuer shared.domain.cpc_descriptions — CPC-Code-Beschreibungen."""

from __future__ import annotations

from shared.domain.cpc_descriptions import (
    CPC_CLASS_DESCRIPTIONS,
    CPC_SECTION_DESCRIPTIONS,
    CPC_SUBCLASS_DESCRIPTIONS,
    describe_cpc,
)


class TestCpcDescriptions:
    def test_all_sections_present(self):
        expected = {"A", "B", "C", "D", "E", "F", "G", "H", "Y"}
        assert set(CPC_SECTION_DESCRIPTIONS.keys()) == expected

    def test_class_descriptions_non_empty(self):
        assert len(CPC_CLASS_DESCRIPTIONS) > 50
        for key, value in CPC_CLASS_DESCRIPTIONS.items():
            assert len(key) == 3, f"Klasse {key} hat falsche Laenge"
            assert value, f"Klasse {key} hat leere Beschreibung"

    def test_subclass_descriptions_non_empty(self):
        assert len(CPC_SUBCLASS_DESCRIPTIONS) > 100
        for key, value in CPC_SUBCLASS_DESCRIPTIONS.items():
            assert len(key) == 4, f"Subklasse {key} hat falsche Laenge"
            assert value, f"Subklasse {key} hat leere Beschreibung"


class TestDescribeCpc:
    def test_subclass_lookup(self):
        desc = describe_cpc("G06N")
        assert "Computing" in desc or "Computational" in desc

    def test_class_fallback(self):
        desc = describe_cpc("G06")
        assert "Computing" in desc

    def test_section_fallback(self):
        desc = describe_cpc("G")
        assert "Physics" in desc

    def test_long_code_uses_subclass(self):
        desc = describe_cpc("H01L 33/00")
        assert "Semiconductor" in desc

    def test_unknown_code(self):
        assert describe_cpc("Z99X") == ""

    def test_empty(self):
        assert describe_cpc("") == ""

    def test_common_codes(self):
        assert describe_cpc("H01M") != ""  # Batteries
        assert describe_cpc("A61K") != ""  # Pharma
        assert describe_cpc("B60L") != ""  # Electric vehicles
        assert describe_cpc("Y02E") != ""  # Climate/Energy
