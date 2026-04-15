"""Tests fuer AP8 — UC12 Response enthaelt ``data_complete_year``.

Bug MAJ-7/MAJ-8: UC12 zeigte Anmeldungen/Erteilungen/Quote bis 2026 —
2025/2026 sind aber wegen EPO-Bulk-Verzoegerung nur teilweise vorhanden.
``data_complete_year`` aus dem shared-Helper macht den Cutoff explizit.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from shared.domain.year_completeness import last_complete_year

from src import service as service_module
from src.service import PatentGrantServicer


@pytest.fixture(autouse=True)
def _force_dict_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """Setzt Protobuf-Module auf None, damit Servicer dict-Response liefert."""
    monkeypatch.setattr(service_module, "uc12_patent_grant_pb2", None)
    monkeypatch.setattr(service_module, "common_pb2", None)


class TestUc12DataCompleteYearMaj7Maj8:
    """UC12-dict-Response MUSS ``data_complete_year`` enthalten."""

    def _build_servicer(self) -> PatentGrantServicer:
        return PatentGrantServicer(pool=MagicMock())

    def _empty_dict_response(self) -> dict:
        servicer = self._build_servicer()
        return servicer._build_response(
            summary={
                "total_applications": 0,
                "total_grants": 0,
                "grant_rate": 0.0,
                "avg_time_to_grant_months": 0.0,
                "median_time_to_grant_months": 0.0,
            },
            year_trend=[],
            kind_codes=[],
            country_rates=[],
            cpc_rates=[],
            data_sources=[],
            warnings=[],
            request_id="t",
            processing_time_ms=1,
        )

    def test_dict_response_enthaelt_data_complete_year(self):
        response = self._empty_dict_response()
        assert "data_complete_year" in response
        assert response["data_complete_year"] == last_complete_year()

    def test_data_complete_year_at_least_2025(self):
        response = self._empty_dict_response()
        assert response["data_complete_year"] >= 2025
