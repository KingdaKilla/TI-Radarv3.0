"""Tests fuer UC7 Publikations-Scope-Label (Bug CRIT-1).

UC7 (research-impact-svc) liefert ``total_publications`` aus Semantic
Scholar — also nicht identisch mit UC1 Header (CORDIS_LINKED) oder UC13.
Das Modul muss auf den Scope ``SEMANTIC_SCHOLAR_TOP`` verweisen, damit
das UI korrekt "Top-Autor-Publikationen" rendert.
"""

from __future__ import annotations

import pytest

from shared.domain.publication_definitions import (
    PublicationScope,
    canonical_publication_label,
)
from src.infrastructure.repository import (
    UC7_PUBLICATION_LABEL,
    UC7_PUBLICATION_SCOPE,
)


class TestUc7PublicationScopeCrit1:
    """Bug CRIT-1 Teil-Assertion fuer UC7."""

    def test_scope_is_semantic_scholar_top(self) -> None:
        """UC7 verwendet explizit den SEMANTIC_SCHOLAR_TOP-Scope."""
        assert UC7_PUBLICATION_SCOPE is PublicationScope.SEMANTIC_SCHOLAR_TOP

    def test_label_is_top_author_publications(self) -> None:
        """Das Label wird aus dem kanonischen Mapping abgeleitet."""
        assert UC7_PUBLICATION_LABEL == "Top-Autor-Publikationen"

    def test_label_matches_canonical_label(self) -> None:
        """Das Label ist **identisch** zum Return von canonical_publication_label.

        Jede Divergenz waere ein Indikator fuer eine stille Re-Definition.
        """
        assert UC7_PUBLICATION_LABEL == canonical_publication_label(
            PublicationScope.SEMANTIC_SCHOLAR_TOP,
        )

    def test_label_differs_from_cordis_linked(self) -> None:
        """UC7 darf NICHT das CORDIS_LINKED-Label tragen — sonst Verwechslung."""
        cordis_label = canonical_publication_label(PublicationScope.CORDIS_LINKED)
        assert UC7_PUBLICATION_LABEL != cordis_label
