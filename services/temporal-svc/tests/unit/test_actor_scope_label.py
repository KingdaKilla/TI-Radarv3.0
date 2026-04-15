"""Unit-Test fuer AP3 — UC8 Response enthaelt kanonisches Scope-Label.

Bug CRIT-3: UC8 zaehlt *Patent-Anmelder im Zeitfenster*. Das Label muss
``aktive Akteure im Zeitfenster`` (``ActorScope.ACTIVE_IN_WINDOW``) sein.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from shared.domain.actor_definitions import ActorScope, canonical_actor_label

from src.service import TemporalServicer


class TestUc8ActorScopeLabel:
    """Prueft, dass der UC8-dict-Response das Scope-Label enthaelt.

    Das dict-Response wird in der REST/JSON-Auslieferung genutzt und ist
    die fuer das Frontend sichtbare Repraesentation. Wir testen hier den
    ``_build_dict_response``-Pfad direkt.
    """

    def _build_servicer(self) -> TemporalServicer:
        pool = MagicMock()
        return TemporalServicer(pool=pool)

    def _default_response(self, **overrides):
        servicer = self._build_servicer()
        defaults = dict(
            entrant_persistence=[],
            actor_timeline=[],
            programme_evo=[],
            tech_breadth=[],
            dynamics_summary={
                "total_actors": 0, "persistent_count": 0,
                "one_timer_count": 0, "avg_lifespan_years": 0.0,
                "median_lifespan_years": 0.0,
            },
            data_sources=[],
            warnings=[],
            request_id="test",
            processing_time_ms=1,
        )
        defaults.update(overrides)
        return servicer._build_dict_response(**defaults)

    def test_dict_response_enthaelt_actor_scope_label(self):
        response = self._default_response()
        assert "actor_scope" in response
        assert response["actor_scope"] == ActorScope.ACTIVE_IN_WINDOW.value
        assert "actor_scope_label" in response
        assert response["actor_scope_label"] == canonical_actor_label(
            ActorScope.ACTIVE_IN_WINDOW,
        )

    def test_label_ist_deutsch_und_spezifisch(self):
        response = self._default_response(request_id="")
        assert "Zeitfenster" in response["actor_scope_label"]


class TestUc8DataCompleteYearMaj7Maj8:
    """UC8-Response MUSS ``data_complete_year`` enthalten.

    Bug MAJ-7/MAJ-8: UC8 zeigt eine Akteurs-Timeline bis 2026 — das
    Frontend kann nur den ReferenceArea-Hinweis „Daten ggf. unvollstaendig"
    rendern, wenn das Backend einen Cutoff liefert. Quelle: shared-Helper
    ``last_complete_year()``.
    """

    def _build_servicer(self) -> TemporalServicer:
        pool = MagicMock()
        return TemporalServicer(pool=pool)

    def test_dict_response_enthaelt_data_complete_year(self):
        from shared.domain.year_completeness import last_complete_year

        servicer = self._build_servicer()
        response = servicer._build_dict_response(
            entrant_persistence=[],
            actor_timeline=[],
            programme_evo=[],
            tech_breadth=[],
            dynamics_summary={
                "total_actors": 0, "persistent_count": 0,
                "one_timer_count": 0, "avg_lifespan_years": 0.0,
                "median_lifespan_years": 0.0,
            },
            data_sources=[],
            warnings=[],
            request_id="t",
            processing_time_ms=1,
        )

        assert "data_complete_year" in response
        assert response["data_complete_year"] == last_complete_year()
