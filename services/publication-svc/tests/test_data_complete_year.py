"""Tests fuer AP8 — UC13 Response enthaelt ``data_complete_year``.

Bug MAJ-7/MAJ-8: UC13 zeigte CORDIS-Pub-Trends mit Jahren bis 2026. Ohne
``data_complete_year`` im Response kann das Frontend nicht den
„Daten ggf. unvollstaendig"-Hinweis rendern. AP8 fuegt das Feld
hinzu, abgeleitet aus :func:`shared.domain.year_completeness.last_complete_year`.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from shared.domain.year_completeness import last_complete_year

from src import service as service_module
from src.service import PublicationAnalyticsServicer


@pytest.fixture(autouse=True)
def _force_dict_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """Setzt Protobuf-Module auf None, damit Servicer dict-Response liefert."""
    monkeypatch.setattr(service_module, "uc_c_publications_pb2", None)
    monkeypatch.setattr(service_module, "common_pb2", None)


class TestUc13DataCompleteYearMaj7Maj8:
    """UC13-dict-Response MUSS ``data_complete_year`` enthalten."""

    def _build_servicer(self) -> PublicationAnalyticsServicer:
        return PublicationAnalyticsServicer(pool=MagicMock())

    def test_dict_response_enthaelt_data_complete_year(self):
        servicer = self._build_servicer()
        response = servicer._build_response(
            total_publications=0,
            total_projects_with_pubs=0,
            publications_per_project=0.0,
            doi_coverage=0.0,
            pub_trend=[],
            top_projects=[],
            top_publications=[],
            data_sources=[],
            warnings=[],
            request_id="t",
            processing_time_ms=1,
        )

        assert "data_complete_year" in response
        assert response["data_complete_year"] == last_complete_year()

    def test_data_complete_year_at_least_2025(self):
        servicer = self._build_servicer()
        response = servicer._build_response(
            total_publications=0,
            total_projects_with_pubs=0,
            publications_per_project=0.0,
            doi_coverage=0.0,
            pub_trend=[],
            top_projects=[],
            top_publications=[],
            data_sources=[],
            warnings=[],
            request_id="",
            processing_time_ms=0,
        )

        assert response["data_complete_year"] >= 2025
