"""Pytest-Fixtures fuer Pact-Contract-Tests.

Stellt Provider- und Consumer-Konfigurationen bereit:
- ``pact_consumer``: Pact-Consumer-Konfiguration fuer das Frontend
- ``pact_provider``: Pact-Provider-Konfiguration fuer den Orchestrator
- ``mock_orchestrator_app``: FastAPI-Testapp mit gemockten gRPC-Clients
- ``test_client``: httpx.AsyncClient gegen die gemockte App

Pact-Dateien (Consumer-Contracts) werden im Verzeichnis
``tests/contract/pacts/`` abgelegt.

Hinweis: pact-python >= 2.0 wird in der Legacy-API (V2-Kompatibilitaet)
verwendet. Consumer-Tests laufen vollstaendig lokal ohne Pact Broker.
"""

from __future__ import annotations

import os
import pathlib
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# Pfade
_REPO_ROOT = pathlib.Path(__file__).parent.parent.parent
_PACTS_DIR = pathlib.Path(__file__).parent / "pacts"
_PACTS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Pact-Konfiguration
# ---------------------------------------------------------------------------


CONSUMER_NAME = "TI-Radar-Frontend"
PROVIDER_NAME = "TI-Radar-Orchestrator"
GRPC_PROVIDER_NAME = "TI-Radar-UC-Service"


@pytest.fixture(scope="session")
def pact_consumer():
    """Pact-Consumer-Konfiguration fuer das Frontend.

    Konfiguriert den Pact-Mock-Server fuer Consumer-driven Contract-Tests.
    Der Consumer (Frontend) definiert, welche JSON-Struktur er vom
    Provider (Orchestrator) erwartet.

    Yields:
        pact.Pact-Instanz im Kontext des Mock-Servers.
    """
    try:
        from pact import Consumer, Provider

        pact = Consumer(CONSUMER_NAME).has_pact_with(
            Provider(PROVIDER_NAME),
            pact_dir=str(_PACTS_DIR),
            version="2.0.0",
        )
        yield pact
    except ImportError:
        # Fallback: pact-python nicht installiert — Tests werden uebersprungen
        pytest.skip("pact-python nicht installiert — Contract-Tests uebersprungen")


@pytest.fixture(scope="session")
def pact_grpc_provider():
    """Pact-Provider-Konfiguration fuer den gRPC-UC-Service.

    Yields:
        dict mit Provider-Metadaten fuer gRPC-Contract-Validierung.
    """
    return {
        "consumer": CONSUMER_NAME,
        "provider": GRPC_PROVIDER_NAME,
        "pact_dir": str(_PACTS_DIR),
    }


# ---------------------------------------------------------------------------
# Gemockte FastAPI-App fuer Consumer-Tests
# ---------------------------------------------------------------------------


def _build_mock_radar_response() -> dict[str, Any]:
    """Erstellt eine repraesentative Radar-Antwort fuer Contract-Tests.

    Alle 12 UC-Panels sind vorhanden (auch wenn minimal befuellt).
    Diese Struktur definiert den Consumer-Contract.
    """
    return {
        "technology": "quantum computing",
        "analysis_period": "2016-2026",
        "landscape": {
            "time_series": [
                {"year": 2020, "patent_count": 42, "project_count": 3, "publication_count": 15, "funding_eur": 2800000.0},
                {"year": 2021, "patent_count": 58, "project_count": 5, "publication_count": 22, "funding_eur": 4200000.0},
            ],
            "top_countries": [
                {"country_code": "DE", "country_name": "Germany", "count": 45, "share": 0.45},
                {"country_code": "FR", "country_name": "France", "count": 30, "share": 0.30},
            ],
            "cagr_values": {
                "patent_cagr": 12.5,
                "project_cagr": 8.3,
                "publication_cagr": 15.2,
                "funding_cagr": 18.7,
                "period_years": 10,
            },
            "summary": {
                "total_patents": 250,
                "total_projects": 18,
                "total_publications": 145,
                "total_funding_eur": 25000000.0,
                "active_countries": 12,
                "active_actors": 87,
            },
        },
        "maturity": {
            "phase": "Growing",
            "phase_de": "Wachsend",
            "confidence": 0.82,
            "s_curve_data": [],
        },
        "competitive": {
            "hhi_index": 2340.5,
            "concentration_level": "Moderate",
            "top_actors": [
                {"name": "TU Berlin", "share": 0.18, "count": 3, "country": "DE"},
                {"name": "CNRS", "share": 0.12, "count": 2, "country": "FR"},
            ],
            "network_nodes": [],
            "network_edges": [],
        },
        "funding": {
            "total_funding_eur": 25000000.0,
            "by_year": [
                {"year": 2020, "funding": 2800000.0, "count": 2},
                {"year": 2021, "funding": 4200000.0, "count": 3},
            ],
            "by_programme": [
                {"programme": "H2020", "funding": 15000000.0, "count": 8},
                {"programme": "HORIZON", "funding": 10000000.0, "count": 5},
            ],
            "by_instrument": [
                {"funding_scheme": "RIA", "funding": 12000000.0, "count": 6},
                {"funding_scheme": "IA", "funding": 8000000.0, "count": 4},
                {"funding_scheme": "CSA", "funding": 5000000.0, "count": 3},
            ],
        },
        "cpc_flow": {
            "matrix": [],
            "labels": ["G06F", "H04W", "H01M"],
            "jaccard_pairs": [],
        },
        "geographic": {
            "total_countries": 12,
            "patent_countries": [],
            "project_countries": [],
            "collaboration_pairs": [],
        },
        "research_impact": {
            "h_index": 24,
            "total_citations": 1840,
            "top_papers": [],
            "citation_trend": [],
        },
        "temporal": {
            "new_entrant_rate": 0.23,
            "actor_persistence": [],
            "programme_evolution": [],
        },
        "tech_cluster": {
            "eu_patents": 180,
            "global_patents": 420,
            "eu_share": 0.43,
        },
        "actor_type": {
            "breakdown": [
                {"type": "HES", "count": 5, "share": 0.45},
                {"type": "PRC", "count": 4, "share": 0.36},
            ]
        },
        "patent_grant": {
            "grant_rate": 0.72,
            "avg_grant_lag_months": 28.5,
        },
        "euroscivoc": {
            "categories": [],
            "top_category": "Computer science",
        },
        "uc_errors": [],
        "explainability": {
            "data_sources": [
                {"name": "EPO", "type": "patent", "record_count": 250, "last_updated": "2024-01-01"},
                {"name": "CORDIS", "type": "project", "record_count": 18, "last_updated": "2024-01-01"},
            ],
            "methods": ["CAGR", "HHI", "S-Curve"],
            "deterministic": True,
            "warnings": [],
        },
        "total_processing_time_ms": 1234,
        "successful_uc_count": 12,
        "total_uc_count": 12,
        "request_id": "test-req-001",
        "timestamp": "2026-02-20T10:00:00.000000",
    }


@pytest_asyncio.fixture(scope="module")
async def mock_orchestrator_app():
    """Erstellt eine FastAPI-Testinstanz mit vollstaendig gemockten gRPC-Clients.

    Alle gRPC-Calls werden durch einen AsyncMock ersetzt, der die
    vordefinierte Mock-Response zurueckgibt. Dadurch ist kein laufender
    gRPC-Server noetig.

    Yields:
        fastapi.FastAPI-App-Instanz fuer httpx-Tests.
    """
    import sys

    _SVC_PATH = _REPO_ROOT / "services" / "orchestrator-svc"
    if str(_SVC_PATH) not in sys.path:
        sys.path.insert(0, str(_SVC_PATH))

    # Umgebungsvariablen fuer den Orchestrator setzen
    os.environ.setdefault("DATABASE_URL", "postgresql://dummy:dummy@localhost/dummy")
    os.environ.setdefault("LANDSCAPE_SVC_ADDR", "localhost:50051")
    os.environ.setdefault("MATURITY_SVC_ADDR", "localhost:50052")
    os.environ.setdefault("COMPETITIVE_SVC_ADDR", "localhost:50053")
    os.environ.setdefault("FUNDING_SVC_ADDR", "localhost:50054")
    os.environ.setdefault("CPC_FLOW_SVC_ADDR", "localhost:50055")
    os.environ.setdefault("GEOGRAPHIC_SVC_ADDR", "localhost:50056")
    os.environ.setdefault("RESEARCH_IMPACT_SVC_ADDR", "localhost:50057")
    os.environ.setdefault("TEMPORAL_SVC_ADDR", "localhost:50058")

    mock_response = _build_mock_radar_response()

    # GrpcChannelManager vollstaendig mocken
    mock_channel_manager = MagicMock()
    mock_channel_manager.call_uc = AsyncMock(return_value=mock_response)
    mock_channel_manager.get_timeout = MagicMock(return_value=30.0)
    mock_channel_manager.close = AsyncMock()

    try:
        from src.main import create_app

        app = create_app()

        # gRPC-State direkt in die App injizieren (Lifespan ueberspringen)
        app.state.grpc_channels = mock_channel_manager
        app.state.db_pool = None

        yield app

    except ImportError as exc:
        pytest.skip(f"Orchestrator-Modul nicht importierbar: {exc}")


@pytest_asyncio.fixture(scope="module")
async def test_client(mock_orchestrator_app):
    """Erstellt einen httpx.AsyncClient gegen die gemockte Orchestrator-App.

    Yields:
        httpx.AsyncClient fuer HTTP-Anfragen im Test.
    """
    try:
        import httpx
        from fastapi.testclient import TestClient

        client = TestClient(mock_orchestrator_app, raise_server_exceptions=True)
        yield client
    except ImportError:
        pytest.skip("httpx nicht installiert — Contract-Tests uebersprungen")
