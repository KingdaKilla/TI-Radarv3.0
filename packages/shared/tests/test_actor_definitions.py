"""Tests fuer shared.domain.actor_definitions — Master-Scope fuer Akteure.

Hintergrund: Bug CRIT-3 — UC8, UC9 und UC11 lieferten drei unterschiedliche
Akteurs-Zahlen (Faktor bis 100). Zentrale Scope-Enum trennt die Semantik
eindeutig.
"""

from __future__ import annotations

from enum import Enum

import pytest

from shared.domain.actor_definitions import (
    ActorScope,
    canonical_actor_label,
)


class TestActorScope:
    def test_is_enum(self):
        """ActorScope ist ein Enum."""
        assert issubclass(ActorScope, Enum)

    def test_active_in_window_present(self):
        """Scope ACTIVE_IN_WINDOW (UC8 — aktiv im Zeitfenster)."""
        assert ActorScope.ACTIVE_IN_WINDOW is not None

    def test_cluster_member_present(self):
        """Scope CLUSTER_MEMBER (UC9 — Akteur in einem Tech-Cluster)."""
        assert ActorScope.CLUSTER_MEMBER is not None

    def test_classified_present(self):
        """Scope CLASSIFIED (UC11 — klassifizierte Organisation)."""
        assert ActorScope.CLASSIFIED is not None

    def test_exactly_three_scopes(self):
        """Genau drei Scopes."""
        assert len(list(ActorScope)) == 3


class TestCanonicalActorLabel:
    def test_active_in_window_label(self):
        assert canonical_actor_label(ActorScope.ACTIVE_IN_WINDOW) == "aktive Akteure im Zeitfenster"

    def test_cluster_member_label(self):
        assert canonical_actor_label(ActorScope.CLUSTER_MEMBER) == "Cluster-Mitglieder"

    def test_classified_label(self):
        assert canonical_actor_label(ActorScope.CLASSIFIED) == "klassifizierte Organisationen"

    def test_labels_are_non_empty_strings(self):
        for scope in ActorScope:
            label = canonical_actor_label(scope)
            assert isinstance(label, str)
            assert len(label) > 0

    def test_invalid_type_raises(self):
        with pytest.raises((TypeError, ValueError, AttributeError)):
            canonical_actor_label("not a scope")  # type: ignore[arg-type]
