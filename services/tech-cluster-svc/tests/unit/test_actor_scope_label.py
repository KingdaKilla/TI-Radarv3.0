"""Unit-Test fuer AP3 — UC9 Response enthaelt kanonisches Scope-Label.

Bug CRIT-3: UC9 zaehlt *Cluster-Mitglieder* (Akteure, die via CPC-Co-
Occurrence einem Tech-Cluster zugeordnet sind). Das Label muss
``Cluster-Mitglieder`` (``ActorScope.CLUSTER_MEMBER``) sein.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from shared.domain.actor_definitions import ActorScope, canonical_actor_label


class TestUc9ActorScopeLabel:
    """Prueft, dass der UC9-dict-Response das Scope-Label enthaelt.

    Wir erzwingen den Dict-Pfad, indem wir die pb2-Imports auf ``None``
    setzen. Das dict-Response wird in der REST/JSON-Auslieferung genutzt.
    """

    def _servicer_and_response(self, **kwargs):
        from src import service as service_mod

        with patch.object(service_mod, "uc9_tech_cluster_pb2", None), \
             patch.object(service_mod, "common_pb2", None):
            servicer = service_mod.TechClusterServicer(pool=MagicMock())
            defaults = dict(
                clusters=[], actor_cpc_links=[],
                total_actors=0, total_cpc_codes=0,
                data_sources=[], warnings=[], request_id="test",
                processing_time_ms=1,
            )
            defaults.update(kwargs)
            return servicer._build_response(**defaults)

    def test_dict_response_enthaelt_actor_scope_label(self):
        response = self._servicer_and_response()
        assert isinstance(response, dict)
        assert "actor_scope" in response
        assert response["actor_scope"] == ActorScope.CLUSTER_MEMBER.value
        assert "actor_scope_label" in response
        assert response["actor_scope_label"] == canonical_actor_label(
            ActorScope.CLUSTER_MEMBER,
        )

    def test_label_ist_deutsch_und_spezifisch(self):
        response = self._servicer_and_response(request_id="")
        assert "cluster" in response["actor_scope_label"].lower()
