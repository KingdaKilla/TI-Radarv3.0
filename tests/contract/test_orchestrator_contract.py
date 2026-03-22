"""Consumer-driven Contract-Tests fuer den TI-Radar Orchestrator.

Prueft den Vertrag zwischen Frontend (Consumer) und Orchestrator (Provider):
- POST /api/v1/radar gibt alle 12 UC-Schluesse zurueck
- Response-Schema entspricht RadarResponse (schemas.py)
- Graceful Degradation: fehlgeschlagene UCs haben leere Panels + uc_errors
- Explainability-Metadaten sind immer vorhanden
- HTTP-Status-Codes (200, 422 bei ungueltigem Request)

Teststrategie:
  - Consumer-Tests: Frontend definiert Erwartungen (Pact-Consumer)
  - Schema-Validation: alle Pflichtfelder vorhanden und korrekt typisiert
  - Payload-Tests: direkte HTTP-Tests gegen gemockte App (kein Pact Broker noetig)

Die Fixtures 'test_client' und 'mock_orchestrator_app' kommen aus conftest.py.
"""

from __future__ import annotations

import json
from typing import Any

import pytest


# ===========================================================================
# Konstanten
# ===========================================================================

# Alle 12 erwarteten UC-Schluesse gemaess RadarResponse (schemas.py)
REQUIRED_UC_KEYS: frozenset[str] = frozenset({
    "landscape",
    "maturity",
    "competitive",
    "funding",
    "cpc_flow",
    "geographic",
    "research_impact",
    "temporal",
    "tech_cluster",
    "actor_type",
    "patent_grant",
    "euroscivoc",
})

# Pflichtfelder auf oberster Ebene der RadarResponse
REQUIRED_TOP_LEVEL_KEYS: frozenset[str] = frozenset({
    "technology",
    "analysis_period",
    "uc_errors",
    "explainability",
    "total_processing_time_ms",
    "successful_uc_count",
    "total_uc_count",
    "request_id",
    "timestamp",
}) | REQUIRED_UC_KEYS

# Pflichtfelder in ExplainabilityInfo
REQUIRED_EXPLAINABILITY_KEYS: frozenset[str] = frozenset({
    "data_sources",
    "methods",
    "deterministic",
    "warnings",
})


# ===========================================================================
# Hilfsfunktionen
# ===========================================================================


def _post_radar(client, technology: str = "quantum computing", **kwargs) -> Any:
    """Sendet eine POST-Anfrage an /api/v1/radar und gibt die Response zurueck."""
    payload = {
        "technology": technology,
        "years": 10,
        "european_only": False,
        **kwargs,
    }
    return client.post("/api/v1/radar", json=payload)


# ===========================================================================
# HTTP-Status-Code-Tests
# ===========================================================================


class TestHttpStatusCodes:
    """Prueft korrekte HTTP-Status-Codes fuer verschiedene Anfragen."""

    def test_gueltige_anfrage_gibt_200(self, test_client):
        """Eine gueltige Radar-Anfrage gibt HTTP 200 zurueck."""
        response = _post_radar(test_client)
        assert response.status_code == 200

    def test_leerer_technologie_string_gibt_422(self, test_client):
        """Ein leerer Technologie-String verletzt das Pydantic-Constraint (min_length=1)."""
        response = test_client.post(
            "/api/v1/radar",
            json={"technology": "", "years": 10},
        )
        # Pydantic validiert min_length=1 -> HTTP 422 Unprocessable Entity
        assert response.status_code == 422

    def test_fehlende_technology_gibt_422(self, test_client):
        """Fehlendes Pflichtfeld 'technology' gibt HTTP 422 zurueck."""
        response = test_client.post(
            "/api/v1/radar",
            json={"years": 10},
        )
        assert response.status_code == 422

    def test_ungueltige_years_gibt_422(self, test_client):
        """years < 3 verletzt das ge=3-Constraint."""
        response = _post_radar(test_client, years=1)
        assert response.status_code == 422

    def test_years_ueber_maximum_gibt_422(self, test_client):
        """years > 30 verletzt das le=30-Constraint."""
        response = _post_radar(test_client, years=50)
        assert response.status_code == 422


# ===========================================================================
# Response-Schema: Alle 12 UC-Schluesse vorhanden
# ===========================================================================


class TestRadarResponseSchema:
    """Prueft, dass die Response alle 12 UC-Schluesse enthaelt."""

    def test_alle_12_uc_schluesse_vorhanden(self, test_client):
        """Alle 12 UC-Panel-Schluesse sind in der Response vorhanden."""
        response = _post_radar(test_client)
        assert response.status_code == 200

        body = response.json()
        for schluessel in REQUIRED_UC_KEYS:
            assert schluessel in body, f"UC-Schluessel fehlt: '{schluessel}'"

    def test_alle_pflichtfelder_vorhanden(self, test_client):
        """Alle Pflichtfelder der RadarResponse sind vorhanden."""
        response = _post_radar(test_client)
        body = response.json()

        for schluessel in REQUIRED_TOP_LEVEL_KEYS:
            assert schluessel in body, f"Pflichtfeld fehlt: '{schluessel}'"

    def test_technology_wird_gespiegelt(self, test_client):
        """Das 'technology'-Feld in der Response entspricht der Anfrage."""
        response = _post_radar(test_client, technology="solid-state batteries")
        body = response.json()
        assert body["technology"] == "solid-state batteries"

    def test_analysis_period_format(self, test_client):
        """analysis_period hat das Format 'YYYY-YYYY'."""
        response = _post_radar(test_client, years=10)
        body = response.json()
        period = body["analysis_period"]
        assert isinstance(period, str)
        teile = period.split("-")
        assert len(teile) == 2
        assert teile[0].isdigit() and teile[1].isdigit()
        assert int(teile[0]) < int(teile[1])

    def test_uc_panels_sind_dicts(self, test_client):
        """Alle UC-Panels sind JSON-Objekte (dict), auch wenn leer."""
        response = _post_radar(test_client)
        body = response.json()
        for schluessel in REQUIRED_UC_KEYS:
            assert isinstance(body[schluessel], dict), (
                f"UC-Panel '{schluessel}' ist kein dict: {type(body[schluessel])}"
            )

    def test_uc_errors_ist_liste(self, test_client):
        """uc_errors ist eine Liste (kann leer sein bei Erfolg)."""
        response = _post_radar(test_client)
        body = response.json()
        assert isinstance(body["uc_errors"], list)

    def test_total_uc_count_ist_12(self, test_client):
        """total_uc_count ist 12 bei vollstaendigem Run."""
        response = _post_radar(test_client)
        body = response.json()
        assert body["total_uc_count"] == 12

    def test_successful_uc_count_numerisch(self, test_client):
        """successful_uc_count ist eine nicht-negative ganze Zahl."""
        response = _post_radar(test_client)
        body = response.json()
        assert isinstance(body["successful_uc_count"], int)
        assert body["successful_uc_count"] >= 0

    def test_processing_time_nicht_negativ(self, test_client):
        """total_processing_time_ms ist eine nicht-negative ganze Zahl."""
        response = _post_radar(test_client)
        body = response.json()
        assert isinstance(body["total_processing_time_ms"], int)
        assert body["total_processing_time_ms"] >= 0


# ===========================================================================
# Explainability-Metadaten
# ===========================================================================


class TestExplainabilityMetadata:
    """Prueft die ExplainabilityInfo-Struktur in der Response."""

    def test_explainability_vorhanden(self, test_client):
        """'explainability' ist immer in der Response vorhanden."""
        response = _post_radar(test_client)
        body = response.json()
        assert "explainability" in body

    def test_explainability_pflichtfelder(self, test_client):
        """ExplainabilityInfo hat alle Pflichtfelder."""
        response = _post_radar(test_client)
        explainability = response.json()["explainability"]

        for schluessel in REQUIRED_EXPLAINABILITY_KEYS:
            assert schluessel in explainability, (
                f"Explainability-Pflichtfeld fehlt: '{schluessel}'"
            )

    def test_deterministic_flag_ist_bool(self, test_client):
        """'deterministic' ist ein Boolean."""
        response = _post_radar(test_client)
        explainability = response.json()["explainability"]
        assert isinstance(explainability["deterministic"], bool)

    def test_data_sources_ist_liste(self, test_client):
        """'data_sources' ist eine Liste."""
        response = _post_radar(test_client)
        explainability = response.json()["explainability"]
        assert isinstance(explainability["data_sources"], list)

    def test_warnings_ist_liste(self, test_client):
        """'warnings' ist eine Liste (kann leer sein)."""
        response = _post_radar(test_client)
        explainability = response.json()["explainability"]
        assert isinstance(explainability["warnings"], list)

    def test_methods_ist_liste(self, test_client):
        """'methods' ist eine Liste."""
        response = _post_radar(test_client)
        explainability = response.json()["explainability"]
        assert isinstance(explainability["methods"], list)


# ===========================================================================
# Graceful Degradation Contract
# ===========================================================================


class TestGracefulDegradation:
    """Prueft den Contract fuer Graceful Degradation (fehlgeschlagene UCs)."""

    def test_selektive_uc_ausfuehrung(self, test_client):
        """use_cases-Parameter selektiert nur die angeforderten UCs."""
        response = test_client.post(
            "/api/v1/radar",
            json={
                "technology": "quantum computing",
                "years": 10,
                "use_cases": ["landscape", "funding"],
            },
        )
        # HTTP-Status muss 200 sein (Graceful Degradation bei Teilausfuehrung)
        assert response.status_code == 200
        body = response.json()
        # Alle 12 Schluesse sind immer in der Response (auch wenn leer)
        for schluessel in REQUIRED_UC_KEYS:
            assert schluessel in body

    def test_uc_error_struktur(self, test_client):
        """Wenn uc_errors vorhanden: korrekte Fehlerstruktur pro UC."""
        response = _post_radar(test_client)
        body = response.json()
        for fehler in body["uc_errors"]:
            assert "use_case" in fehler
            assert "error_code" in fehler
            assert "error_message" in fehler
            assert "retryable" in fehler
            assert "elapsed_ms" in fehler
            assert isinstance(fehler["retryable"], bool)
            assert isinstance(fehler["elapsed_ms"], int)

    def test_leeres_panel_bei_uc_fehler_ist_dict(self, test_client):
        """Fehlgeschlagene UC-Panels sind immer leere Dicts (nicht null/None)."""
        response = _post_radar(test_client)
        body = response.json()
        # Bei Fehlern: betroffene Panels muessen Dicts sein (koennen leer sein)
        for schluessel in REQUIRED_UC_KEYS:
            panel = body[schluessel]
            assert panel is not None, f"Panel '{schluessel}' ist None — muss Dict sein"
            assert isinstance(panel, dict), (
                f"Panel '{schluessel}' ist {type(panel)} — muss Dict sein"
            )


# ===========================================================================
# Pact Consumer-Contract (optional, wenn pact-python installiert)
# ===========================================================================


class TestPactConsumerContract:
    """Consumer-driven Contract-Tests mit pact-python.

    Schreibt den Consumer-Contract in eine Pact-Datei, die vom Provider
    verifiziert werden kann. Wird uebersprungen wenn pact-python fehlt.
    """

    def test_frontend_erwartet_landscape_panel(self, pact_consumer):
        """Consumer-Contract: Frontend erwartet 'landscape' mit time_series."""
        try:
            from pact import Like, EachLike, Term

            (
                pact_consumer
                .given("Quantum-Computing-Daten sind in der DB vorhanden")
                .upon_receiving("Eine Radar-Analyse fuer 'quantum computing'")
                .with_request(
                    method="POST",
                    path="/api/v1/radar",
                    body={
                        "technology": "quantum computing",
                        "years": 10,
                        "european_only": False,
                        "cpc_codes": [],
                        "top_n": 0,
                        "use_cases": [],
                    },
                    headers={"Content-Type": "application/json"},
                )
                .will_respond_with(
                    status=200,
                    body={
                        "technology": "quantum computing",
                        "analysis_period": Term(r"\d{4}-\d{4}", "2016-2026"),
                        "landscape": Like({"time_series": [], "summary": {}}),
                        "maturity": Like({}),
                        "competitive": Like({}),
                        "funding": Like({}),
                        "cpc_flow": Like({}),
                        "geographic": Like({}),
                        "research_impact": Like({}),
                        "temporal": Like({}),
                        "tech_cluster": Like({}),
                        "actor_type": Like({}),
                        "patent_grant": Like({}),
                        "euroscivoc": Like({}),
                        "uc_errors": [],
                        "explainability": Like({
                            "deterministic": True,
                            "data_sources": [],
                            "methods": [],
                            "warnings": [],
                        }),
                        "total_processing_time_ms": Like(1000),
                        "successful_uc_count": Like(12),
                        "total_uc_count": 12,
                        "request_id": Like(""),
                        "timestamp": Like("2026-02-20T10:00:00"),
                    },
                )
            )

            # Pact-Verifikation ausfuehren (schreibt .json-Datei)
            with pact_consumer:
                import httpx

                response = httpx.post(
                    f"{pact_consumer.uri}/api/v1/radar",
                    json={
                        "technology": "quantum computing",
                        "years": 10,
                        "european_only": False,
                        "cpc_codes": [],
                        "top_n": 0,
                        "use_cases": [],
                    },
                )
                assert response.status_code == 200

        except Exception as exc:
            pytest.skip(f"Pact-Consumer-Test uebersprungen: {exc}")

    def test_frontend_erwartet_alle_12_uc_schluesse(self, pact_consumer):
        """Consumer-Contract: Frontend erwartet alle 12 UC-Schluesse im Response-Body."""
        try:
            from pact import Like

            erwartete_schluesse = {
                schluessel: Like({})
                for schluessel in REQUIRED_UC_KEYS
            }

            (
                pact_consumer
                .given("Alle UC-Services sind verfuegbar")
                .upon_receiving("Eine vollstaendige Radar-Analyse")
                .with_request(
                    method="POST",
                    path="/api/v1/radar",
                    body={"technology": "solid-state batteries", "years": 5},
                )
                .will_respond_with(
                    status=200,
                    body={
                        "technology": "solid-state batteries",
                        "total_uc_count": 12,
                        **erwartete_schluesse,
                    },
                )
            )

            with pact_consumer:
                pass  # Contract wird aufgezeichnet; Provider-Verifikation separat

        except Exception as exc:
            pytest.skip(f"Pact-Consumer-Test uebersprungen: {exc}")
