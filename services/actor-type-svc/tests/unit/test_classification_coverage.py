"""Unit-Tests fuer compute_classification_coverage + Service-Integration.

Bug-Fix (Bundle B):
    Die UC11 ActorType-Response hat ``classification_coverage`` als Feld
    im Proto (uc11_actor_type.proto:193), aber der Service hat es nie
    gesetzt. Dadurch war ``classification_coverage == 0`` bei
    ``unclassified_actors == 0`` und ``total_classified_actors > 0`` --
    ein logisch unmoeglicher Zustand.

    Hier werden die neue Berechnungslogik (``compute_classification_coverage``)
    und die Durchreichung durch den Servicer (``_build_response``,
    ``_build_empty_response``) validiert.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.domain.metrics import compute_classification_coverage


class TestComputeClassificationCoverage:
    """Tests fuer die reine Domain-Funktion."""

    def test_leere_daten_geben_1_0(self):
        # 0/0 -> 1.0 ("alle bekannten Akteure klassifiziert", leere Basis)
        assert compute_classification_coverage(0, 0) == 1.0

    def test_alle_klassifiziert_ohne_unclassified(self):
        # 10 klassifiziert, 0 unclassified -> 1.0 (Bug-Kernfall)
        assert compute_classification_coverage(10, 0) == 1.0

    def test_teilweise_klassifiziert(self):
        # 5 klassifiziert, 10 unclassified -> 5/15 == 0.3333
        assert compute_classification_coverage(5, 10) == pytest.approx(0.3333, abs=1e-4)

    def test_haelfte_klassifiziert(self):
        assert compute_classification_coverage(50, 50) == pytest.approx(0.5)

    def test_nichts_klassifiziert(self):
        # 0 klassifiziert, 10 unclassified -> 0.0
        assert compute_classification_coverage(0, 10) == 0.0

    def test_ergebnis_immer_in_0_1(self):
        result = compute_classification_coverage(1234, 5678)
        assert 0.0 <= result <= 1.0

    def test_negative_werte_werden_geklammert(self):
        # Defensiv: Negative Inputs -> als 0 behandeln.
        # classified<0, unclassified<0 -> denom == 0 -> 1.0 (leer)
        assert compute_classification_coverage(-5, -5) == 1.0
        # classified<0 (->0), unclassified=10 -> 0/10 -> 0.0
        assert compute_classification_coverage(-5, 10) == 0.0

    def test_float_inputs_werden_akzeptiert(self):
        # Robustheit: float -> int Konvertierung
        assert compute_classification_coverage(10.0, 0.0) == 1.0  # type: ignore[arg-type]


class TestServiceIntegration:
    """Stellt sicher, dass der Servicer die neuen Felder setzt."""

    def _build_dict_response(self, **overrides):
        """Baut ein dict-Response via ``_build_response`` mit gemockten pb2."""
        from src import service as service_mod

        with patch.object(service_mod, "uc11_actor_type_pb2", None), \
             patch.object(service_mod, "common_pb2", None):
            servicer = service_mod.ActorTypeServicer(pool=MagicMock())
            defaults = dict(
                type_breakdown=[], type_trend=[], top_actors=[],
                total_classified=0, unclassified_actors=0,
                classification_coverage=1.0,
                sme_share=0.0,
                data_sources=[], warnings=[], request_id="t",
                processing_time_ms=0,
            )
            defaults.update(overrides)
            return servicer._build_response(**defaults)

    def test_dict_response_enthaelt_classification_coverage(self):
        resp = self._build_dict_response(classification_coverage=0.85)
        assert "classification_coverage" in resp
        assert resp["classification_coverage"] == pytest.approx(0.85)

    def test_dict_response_enthaelt_unclassified_actors(self):
        resp = self._build_dict_response(unclassified_actors=7)
        assert "unclassified_actors" in resp
        assert resp["unclassified_actors"] == 7

    def test_bug_fix_coverage_nicht_null_bei_unclassified_null(self):
        """Kern des Bug-Fix: coverage == 1.0 wenn unclassified == 0
        und total_classified > 0 — *nicht* 0."""
        resp = self._build_dict_response(
            total_classified=100,
            unclassified_actors=0,
            classification_coverage=compute_classification_coverage(100, 0),
        )
        assert resp["total_classified_actors"] == 100
        assert resp["unclassified_actors"] == 0
        assert resp["classification_coverage"] == pytest.approx(1.0)

    def test_empty_response_hat_sinnvolle_defaults(self):
        """``_build_empty_response`` muss die neuen Felder setzen."""
        from src import service as service_mod

        with patch.object(service_mod, "uc11_actor_type_pb2", None), \
             patch.object(service_mod, "common_pb2", None):
            servicer = service_mod.ActorTypeServicer(pool=MagicMock())
            resp = servicer._build_empty_response(request_id="x", t0=0.0)
            assert resp["unclassified_actors"] == 0
            assert resp["classification_coverage"] == pytest.approx(1.0)
            assert resp["total_classified_actors"] == 0
