"""Tests fuer shared.domain.patent_definitions — Master-Scope fuer Patente.

Hintergrund: Bug CRIT-4 — `total_patents` im Header vs. `total_applications`
in UC12 wurden inkonsistent gezaehlt. Zentrale Scope-Enum + Kind-Code-Listen
machen die Trennung verbindlich.
"""

from __future__ import annotations

from enum import Enum

import pytest

from shared.domain.patent_definitions import (
    APPLICATION_KIND_CODES,
    GRANT_KIND_CODES,
    PatentScope,
    canonical_patent_label,
)


class TestPatentScope:
    def test_is_enum(self):
        assert issubclass(PatentScope, Enum)

    def test_all_patents_present(self):
        assert PatentScope.ALL_PATENTS is not None

    def test_applications_only_present(self):
        assert PatentScope.APPLICATIONS_ONLY is not None

    def test_grants_only_present(self):
        assert PatentScope.GRANTS_ONLY is not None

    def test_exactly_three_scopes(self):
        assert len(list(PatentScope)) == 3


class TestKindCodes:
    def test_a1_in_application_codes(self):
        """A1 ist ein Standard-EPO-Application-Kind-Code."""
        assert "A1" in APPLICATION_KIND_CODES

    def test_b1_in_grant_codes(self):
        """B1 ist ein Standard-EPO-Grant-Kind-Code."""
        assert "B1" in GRANT_KIND_CODES

    def test_application_codes_complete(self):
        """Alle gaengigen Application-Codes sind enthalten."""
        expected = {"A", "A1", "A2", "A3", "A4", "A8", "A9"}
        assert expected <= APPLICATION_KIND_CODES

    def test_grant_codes_complete(self):
        """Alle gaengigen Grant-Codes sind enthalten."""
        expected = {"B", "B1", "B2", "B3", "B4", "B8", "B9"}
        assert expected <= GRANT_KIND_CODES

    def test_no_overlap_between_applications_and_grants(self):
        """Application- und Grant-Codes sind disjunkt."""
        assert APPLICATION_KIND_CODES.isdisjoint(GRANT_KIND_CODES)

    def test_codes_are_sets(self):
        """Kind-Codes sind frozensets/sets (O(1)-Lookup)."""
        assert isinstance(APPLICATION_KIND_CODES, (set, frozenset))
        assert isinstance(GRANT_KIND_CODES, (set, frozenset))


class TestCanonicalPatentLabel:
    def test_all_patents_label(self):
        label = canonical_patent_label(PatentScope.ALL_PATENTS)
        assert isinstance(label, str) and len(label) > 0

    def test_applications_only_label(self):
        label = canonical_patent_label(PatentScope.APPLICATIONS_ONLY)
        assert isinstance(label, str) and len(label) > 0

    def test_grants_only_label(self):
        label = canonical_patent_label(PatentScope.GRANTS_ONLY)
        assert isinstance(label, str) and len(label) > 0

    def test_labels_distinct(self):
        """Jeder Scope hat ein eigenes Label."""
        labels = {canonical_patent_label(s) for s in PatentScope}
        assert len(labels) == 3

    def test_invalid_type_raises(self):
        with pytest.raises((TypeError, ValueError, AttributeError)):
            canonical_patent_label("not a scope")  # type: ignore[arg-type]
