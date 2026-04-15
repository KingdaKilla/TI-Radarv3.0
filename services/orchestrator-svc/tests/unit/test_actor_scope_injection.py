"""Unit-Test fuer AP3 — Orchestrator injiziert Akteurs-Scope-Label.

Der Orchestrator konvertiert die Protobuf-Responses der UC-Services via
``MessageToDict`` ins Dict. Damit das Frontend UC8/UC9/UC11 als
unterschiedliche Akteurs-Populationen darstellen kann, injiziert der
Orchestrator nach der Konvertierung das kanonische Scope-Label.
"""

from __future__ import annotations

from shared.domain.actor_definitions import ActorScope, canonical_actor_label

from src.actor_scope_injection import UC_ACTOR_SCOPE, inject_actor_scope_label


class TestInjectActorScopeLabel:
    def test_temporal_bekommt_active_in_window(self):
        panel: dict = {"some_field": 1}
        inject_actor_scope_label("temporal", panel)
        assert panel["actor_scope"] == ActorScope.ACTIVE_IN_WINDOW.value
        assert panel["actor_scope_label"] == canonical_actor_label(
            ActorScope.ACTIVE_IN_WINDOW,
        )

    def test_tech_cluster_bekommt_cluster_member(self):
        panel: dict = {}
        inject_actor_scope_label("tech_cluster", panel)
        assert panel["actor_scope"] == ActorScope.CLUSTER_MEMBER.value
        assert panel["actor_scope_label"] == canonical_actor_label(
            ActorScope.CLUSTER_MEMBER,
        )

    def test_actor_type_bekommt_classified(self):
        panel: dict = {}
        inject_actor_scope_label("actor_type", panel)
        assert panel["actor_scope"] == ActorScope.CLASSIFIED.value
        assert panel["actor_scope_label"] == canonical_actor_label(
            ActorScope.CLASSIFIED,
        )

    def test_andere_ucs_unveraendert(self):
        """UC1 (landscape) und andere bekommen kein Scope-Label."""
        panel: dict = {"foo": "bar"}
        inject_actor_scope_label("landscape", panel)
        assert "actor_scope" not in panel
        assert "actor_scope_label" not in panel
        assert panel == {"foo": "bar"}

    def test_vorhandenes_label_wird_nicht_ueberschrieben(self):
        """Wenn der Service bereits ein Label gesetzt hat, bleibt es."""
        panel: dict = {
            "actor_scope": "custom",
            "actor_scope_label": "benutzerdefiniert",
        }
        inject_actor_scope_label("temporal", panel)
        assert panel["actor_scope"] == "custom"
        assert panel["actor_scope_label"] == "benutzerdefiniert"

    def test_drei_eindeutige_mappings(self):
        """UC_ACTOR_SCOPE hat genau drei UCs, jeder mit eigenem Scope."""
        assert set(UC_ACTOR_SCOPE) == {"temporal", "tech_cluster", "actor_type"}
        assert len({scope for scope in UC_ACTOR_SCOPE.values()}) == 3
