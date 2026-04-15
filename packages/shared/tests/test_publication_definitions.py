"""Tests fuer shared.domain.publication_definitions — Master-Scope fuer Publikationen.

Hintergrund: Bug CRIT-1 — Header, UC7 und UC13 lieferten drei unterschiedliche
Publikationszahlen (Faktor bis 1580). Zentrale Scope-Enum zwingt Services zu
einer eindeutigen Semantik.
"""

from __future__ import annotations

from enum import Enum

import pytest

from shared.domain.publication_definitions import (
    PublicationScope,
    canonical_publication_label,
)


class TestPublicationScope:
    def test_is_enum(self):
        """PublicationScope ist ein Enum."""
        assert issubclass(PublicationScope, Enum)

    def test_cordis_linked_present(self):
        """Scope CORDIS_LINKED existiert (Publikationen direkt aus CORDIS-Projekten)."""
        assert PublicationScope.CORDIS_LINKED is not None

    def test_openaire_matched_present(self):
        """Scope OPENAIRE_MATCHED existiert (Publikationen aus OpenAIRE-Abgleich)."""
        assert PublicationScope.OPENAIRE_MATCHED is not None

    def test_semantic_scholar_top_present(self):
        """Scope SEMANTIC_SCHOLAR_TOP existiert (Top-Autor-Publikationen)."""
        assert PublicationScope.SEMANTIC_SCHOLAR_TOP is not None

    def test_exactly_three_scopes(self):
        """Genau drei Scopes — keine stillen Ergaenzungen."""
        assert len(list(PublicationScope)) == 3


class TestCanonicalPublicationLabel:
    def test_cordis_linked_label(self):
        label = canonical_publication_label(PublicationScope.CORDIS_LINKED)
        assert label == "CORDIS-Projekt-Publikationen"

    def test_openaire_matched_label(self):
        label = canonical_publication_label(PublicationScope.OPENAIRE_MATCHED)
        assert label == "OpenAIRE Tech-Treffer"

    def test_semantic_scholar_top_label(self):
        label = canonical_publication_label(PublicationScope.SEMANTIC_SCHOLAR_TOP)
        assert label == "Top-Autor-Publikationen"

    def test_labels_are_non_empty_strings(self):
        for scope in PublicationScope:
            label = canonical_publication_label(scope)
            assert isinstance(label, str)
            assert len(label) > 0

    def test_invalid_type_raises(self):
        """Nicht-Scope-Input wird abgelehnt."""
        with pytest.raises((TypeError, ValueError, AttributeError)):
            canonical_publication_label("not a scope")  # type: ignore[arg-type]
