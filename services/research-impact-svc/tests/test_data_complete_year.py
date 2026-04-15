"""Tests fuer AP8 — UC7 Response enthaelt ``data_complete_year``.

Bug MAJ-7/MAJ-8: UC7 (Forschungsimpact) reichte nur bis 2024 — ohne
expliziten ``data_complete_year`` weiss das Frontend aber nicht, ab
welchem Jahr Werte unvollstaendig sind. Nach AP8 wird das Feld via
:func:`shared.domain.year_completeness.last_complete_year` gesetzt.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from shared.domain.year_completeness import last_complete_year

from src.service import ResearchImpactServicer


class TestUc7DataCompleteYearMaj7Maj8:
    """UC7-dict-Response MUSS ``data_complete_year`` enthalten."""

    def _build_servicer(self) -> ResearchImpactServicer:
        return ResearchImpactServicer(pool=MagicMock())

    def _empty_dict_response(self) -> dict:
        servicer = self._build_servicer()
        return servicer._build_dict_response(
            h_index=0,
            avg_citations=0.0,
            median_citations=0.0,
            total_citations=0,
            total_publications=0,
            citation_trend=[],
            top_papers=[],
            top_venues=[],
            publication_types=[],
            open_access_share=0.0,
            i10_index=0,
            top_institutions=[],
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
