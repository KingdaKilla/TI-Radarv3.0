"""Unit-Test fuer AP3 — UC11 Response enthaelt kanonisches Scope-Label.

Bug CRIT-3: UC11 zaehlt *klassifizierte Organisationen* (alle CORDIS-Orgs
mit aktivem ``activity_type``). Das Label muss
``klassifizierte Organisationen`` (``ActorScope.CLASSIFIED``) sein.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from shared.domain.actor_definitions import ActorScope, canonical_actor_label


class TestUc11ActorScopeLabel:
    """Prueft, dass der UC11-dict-Response das Scope-Label enthaelt.

    Das dict-Response wird durch die REST/JSON-Auslieferung genutzt, wenn
    Protobuf-Imports fehlen. Wir erzwingen diesen Pfad, indem wir die
    pb2-Imports des Servicer-Moduls auf ``None`` setzen — so wird der
    Dict-Pfad im ``_build_response`` aktiv.
    """

    def _servicer_and_response(self, **kwargs):
        # Servicer-Modul lazy importieren, damit Monkeypatch greift.
        from src import service as service_mod

        with patch.object(service_mod, "uc11_actor_type_pb2", None), \
             patch.object(service_mod, "common_pb2", None):
            servicer = service_mod.ActorTypeServicer(pool=MagicMock())
            defaults = dict(
                type_breakdown=[], type_trend=[], top_actors=[],
                total_classified=0, sme_share=0.0,
                data_sources=[], warnings=[], request_id="test",
                processing_time_ms=1,
            )
            defaults.update(kwargs)
            return servicer._build_response(**defaults)

    def test_dict_response_enthaelt_actor_scope_label(self):
        response = self._servicer_and_response()
        assert isinstance(response, dict)
        assert "actor_scope" in response
        assert response["actor_scope"] == ActorScope.CLASSIFIED.value
        assert "actor_scope_label" in response
        assert response["actor_scope_label"] == canonical_actor_label(
            ActorScope.CLASSIFIED,
        )

    def test_label_ist_deutsch_und_spezifisch(self):
        response = self._servicer_and_response(request_id="")
        assert "klassifiziert" in response["actor_scope_label"].lower()
