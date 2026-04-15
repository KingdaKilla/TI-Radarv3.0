"""Unit-Tests fuer AnalyzeLandscape Use Case.

Alle externen Abhaengigkeiten (Repository, OpenAIRE) werden durch
AsyncMock-Objekte ersetzt. Kein IO, kein gRPC, kein Protobuf.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from shared.domain.result_types import CountryCount, CpcCount, FundingYear, YearCount
from shared.domain.year_completeness import last_complete_year
from src.use_case import AnalyzeLandscape, LandscapeResult, _compute_funding_cagr, _safe_cagr


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_repo(**overrides: object) -> AsyncMock:
    """Erstellt ein Mock-Repository mit sinnvollen Standardwerten."""
    repo = AsyncMock()

    repo.count_patents_by_year.return_value = overrides.get(
        "patent_years",
        [YearCount(year=2020, count=100), YearCount(year=2024, count=200)],
    )
    repo.count_patents_by_country.return_value = overrides.get(
        "patent_countries",
        [CountryCount(country="DE", count=80), CountryCount(country="FR", count=60)],
    )
    repo.count_projects_by_year.return_value = overrides.get(
        "project_years",
        [YearCount(year=2020, count=10), YearCount(year=2024, count=20)],
    )
    repo.count_projects_by_country.return_value = overrides.get(
        "project_countries",
        [CountryCount(country="DE", count=5), CountryCount(country="NL", count=3)],
    )
    repo.top_cpc_codes.return_value = overrides.get(
        "top_cpc",
        [CpcCount(code="H04W", description="Wireless", count=50)],
    )
    repo.funding_by_year.return_value = overrides.get(
        "funding_by_year",
        [FundingYear(year=2020, funding=1_000_000.0, count=5),
         FundingYear(year=2024, funding=2_000_000.0, count=8)],
    )
    # AP2 CRIT-1: Header-Summary muss ``total_publications`` aus dem
    # CORDIS_LINKED-Scope beziehen.  Das Repository liefert die Zahl direkt.
    repo.count_cordis_publications.return_value = overrides.get(
        "cordis_publications_total", 2_456,
    )

    return repo


def _make_openaire(**overrides: object) -> AsyncMock:
    """Erstellt einen Mock-OpenAIRE-Adapter."""
    openaire = AsyncMock()
    openaire.count_by_year.return_value = overrides.get(
        "publication_years",
        [{"year": 2020, "count": 50}, {"year": 2024, "count": 80}],
    )
    return openaire


# ---------------------------------------------------------------------------
# Tests: Normaler Ablauf
# ---------------------------------------------------------------------------

class TestAnalyzeLandscapeNormal:
    """Testet den normalen Ausfuehrungspfad mit gueltigem Input."""

    async def test_returns_landscape_result(self):
        repo = _make_repo()
        openaire = _make_openaire()
        uc = AnalyzeLandscape(repo=repo, openaire=openaire)

        result = await uc.execute("quantum computing", start_year=2020, end_year=2024)

        assert isinstance(result, LandscapeResult)

    async def test_correct_totals(self):
        repo = _make_repo()
        openaire = _make_openaire()
        uc = AnalyzeLandscape(repo=repo, openaire=openaire)

        result = await uc.execute("quantum computing", start_year=2020, end_year=2024)

        assert result.total_patents == 300  # 100 + 200
        assert result.total_projects == 30  # 10 + 20
        # CRIT-1: Header.total_publications kommt aus Repo (CORDIS_LINKED-Scope),
        # nicht mehr aus OpenAIRE.  Default im Fixture: 2_456.
        assert result.total_publications == 2_456
        assert result.total_funding == 3_000_000.0  # 1M + 2M

    async def test_periods_calculated(self):
        repo = _make_repo()
        uc = AnalyzeLandscape(repo=repo, openaire=None)

        result = await uc.execute("ai", start_year=2015, end_year=2024)

        assert result.periods == 9  # 2024 - 2015

    async def test_active_countries(self):
        repo = _make_repo()
        uc = AnalyzeLandscape(repo=repo, openaire=None)

        result = await uc.execute("robotics", start_year=2020, end_year=2024)

        # DE from patents + projects, FR from patents, NL from projects = 3
        assert result.active_countries == 3

    async def test_time_series_populated(self):
        repo = _make_repo()
        openaire = _make_openaire()
        uc = AnalyzeLandscape(repo=repo, openaire=openaire)

        result = await uc.execute("blockchain", start_year=2020, end_year=2024)

        assert len(result.time_series) > 0
        years = [entry["year"] for entry in result.time_series]
        assert 2020 in years
        assert 2024 in years

    async def test_data_sources_populated(self):
        repo = _make_repo()
        openaire = _make_openaire()
        uc = AnalyzeLandscape(repo=repo, openaire=openaire)

        result = await uc.execute("iot", start_year=2020, end_year=2024)

        source_types = [ds["type"] for ds in result.data_sources]
        assert "PATENT" in source_types
        assert "PROJECT" in source_types
        assert "PUBLICATION" in source_types

    async def test_cagr_values_nonzero(self):
        repo = _make_repo()
        openaire = _make_openaire()
        uc = AnalyzeLandscape(repo=repo, openaire=openaire)

        result = await uc.execute("5g", start_year=2020, end_year=2024)

        # Patent CAGR: 100 -> 200 ueber 4 Jahre (2020-2024)
        assert result.cagr_patents > 0.0
        assert result.cagr_projects > 0.0
        assert result.cagr_funding > 0.0

    async def test_without_openaire(self):
        """Ohne OpenAIRE-Adapter gibt es nur CORDIS-Publikationen (keine Trendkurve).

        CRIT-1: Die Header-Zahl kommt weiterhin aus dem Repo — OpenAIRE liefert
        nur die *optionale* Zeitreihe.
        """
        repo = _make_repo()
        uc = AnalyzeLandscape(repo=repo, openaire=None)

        result = await uc.execute("quantum", start_year=2020, end_year=2024)

        # total_publications kommt vom Repo (Default 2_456).
        assert result.total_publications == 2_456
        # Die PUBLICATION-Datenquelle kommt jetzt aus CORDIS (nicht OpenAIRE).
        pub_sources = [ds for ds in result.data_sources if ds.get("type") == "PUBLICATION"]
        assert len(pub_sources) == 1
        assert "CORDIS" in pub_sources[0]["name"]

    async def test_processing_time_positive(self):
        repo = _make_repo()
        uc = AnalyzeLandscape(repo=repo, openaire=None)

        result = await uc.execute("ai", start_year=2020, end_year=2024)

        assert result.processing_time_ms >= 0

    async def test_top_cpc_passed_through(self):
        expected_cpc = [CpcCount(code="G06N", description="AI", count=120)]
        repo = _make_repo(top_cpc=expected_cpc)
        uc = AnalyzeLandscape(repo=repo, openaire=None)

        result = await uc.execute("ai", start_year=2020, end_year=2024)

        assert result.top_cpc == expected_cpc


# ---------------------------------------------------------------------------
# Tests: Leere / fehlende Daten
# ---------------------------------------------------------------------------

class TestAnalyzeLandscapeEmpty:
    """Testet Verhalten bei leeren oder fehlenden Daten."""

    async def test_empty_results_from_repo(self):
        """Leere Ergebnisse fuehren zu Null-Totals (kein Fehler)."""
        repo = _make_repo(
            patent_years=[],
            patent_countries=[],
            project_years=[],
            project_countries=[],
            top_cpc=[],
            funding_by_year=[],
            cordis_publications_total=0,
        )
        uc = AnalyzeLandscape(repo=repo, openaire=None)

        result = await uc.execute("nonexistent_tech", start_year=2020, end_year=2024)

        assert result.total_patents == 0
        assert result.total_projects == 0
        assert result.total_publications == 0
        assert result.total_funding == 0.0
        assert result.active_countries == 0
        assert result.cagr_patents == 0.0
        assert result.data_sources == []
        assert result.warnings == []


# ---------------------------------------------------------------------------
# Tests: Fehlerbehandlung
# ---------------------------------------------------------------------------

class TestAnalyzeLandscapeErrors:
    """Testet Graceful Degradation bei fehlgeschlagenen Queries."""

    async def test_failed_query_adds_warning(self):
        """Fehlgeschlagene Query wird als Warning dokumentiert, nicht als Exception."""
        repo = _make_repo()
        # patent_years Query schlaegt fehl
        repo.count_patents_by_year.side_effect = RuntimeError("DB connection lost")
        uc = AnalyzeLandscape(repo=repo, openaire=None)

        result = await uc.execute("ai", start_year=2020, end_year=2024)

        assert len(result.warnings) >= 1
        warning_msgs = [w["message"] for w in result.warnings]
        assert any("patent_years" in msg for msg in warning_msgs)
        assert any("MEDIUM" == w["severity"] for w in result.warnings)

    async def test_failed_query_does_not_crash(self):
        """Einzelne fehlgeschlagene Query laesst andere Queries durchlaufen."""
        repo = _make_repo()
        repo.count_patents_by_year.side_effect = RuntimeError("timeout")
        uc = AnalyzeLandscape(repo=repo, openaire=None)

        result = await uc.execute("ai", start_year=2020, end_year=2024)

        # Patent total ist 0 (Query fehlgeschlagen), aber Projekte funktionieren
        assert result.total_patents == 0
        assert result.total_projects == 30  # 10 + 20

    async def test_failed_openaire_adds_warning(self):
        """Fehlgeschlagene OpenAIRE-Query erzeugt Warning — Header bleibt aus CORDIS.

        CRIT-1: OpenAIRE liefert nur die Zeitreihen-Trendkurve.  Wenn sie
        ausfaellt, bleibt ``total_publications`` dennoch aus dem Repo gefuellt.
        """
        repo = _make_repo(cordis_publications_total=789)
        openaire = _make_openaire()
        openaire.count_by_year.side_effect = ConnectionError("OpenAIRE down")
        uc = AnalyzeLandscape(repo=repo, openaire=openaire)

        result = await uc.execute("ai", start_year=2020, end_year=2024)

        assert result.total_publications == 789  # Header unveraendert aus CORDIS
        warning_codes = [w["code"] for w in result.warnings]
        assert any("PUBLICATION_YEARS" in code for code in warning_codes)

    async def test_multiple_failed_queries(self):
        """Mehrere fehlgeschlagene Queries erzeugen mehrere Warnings."""
        repo = _make_repo()
        repo.count_patents_by_year.side_effect = RuntimeError("err1")
        repo.count_projects_by_year.side_effect = RuntimeError("err2")
        repo.top_cpc_codes.side_effect = RuntimeError("err3")
        uc = AnalyzeLandscape(repo=repo, openaire=None)

        result = await uc.execute("ai", start_year=2020, end_year=2024)

        assert len(result.warnings) >= 3


# ---------------------------------------------------------------------------
# Tests: Hilfsfunktionen
# ---------------------------------------------------------------------------

class TestSafeCagr:
    """Testet _safe_cagr Hilfsfunktion."""

    def test_normal_growth(self):
        data = [YearCount(year=2020, count=100), YearCount(year=2024, count=200)]
        result = _safe_cagr(data, 4)
        assert result > 0.0

    def test_empty_data(self):
        assert _safe_cagr([], 5) == 0.0

    def test_zero_periods(self):
        data = [YearCount(year=2020, count=100)]
        assert _safe_cagr(data, 0) == 0.0

    def test_single_year(self):
        data = [YearCount(year=2020, count=100)]
        assert _safe_cagr(data, 5) == 0.0


class TestComputeFundingCagr:
    """Testet _compute_funding_cagr Hilfsfunktion."""

    def test_normal_growth(self):
        funding = {2020: 1_000_000.0, 2024: 2_000_000.0}
        result = _compute_funding_cagr(funding, 2020, 2024)
        assert result > 0.0

    def test_empty_funding(self):
        assert _compute_funding_cagr({}, 2020, 2024) == 0.0

    def test_single_year_funding(self):
        funding = {2022: 500_000.0}
        assert _compute_funding_cagr(funding, 2020, 2024) == 0.0

    def test_skips_zero_values(self):
        funding = {2020: 0.0, 2021: 100_000.0, 2023: 200_000.0, 2024: 0.0}
        result = _compute_funding_cagr(funding, 2020, 2024)
        # Should compute CAGR from 2021 to 2023 (skipping zeros)
        assert result > 0.0


# ---------------------------------------------------------------------------
# Tests: LandscapeResult Dataclass
# ---------------------------------------------------------------------------

class TestLandscapeResult:
    """Testet LandscapeResult Dataclass."""

    def test_default_values(self):
        result = LandscapeResult()
        assert result.total_patents == 0
        assert result.total_projects == 0
        assert result.total_publications == 0
        assert result.total_funding == 0.0
        assert result.active_countries == 0
        assert result.time_series == []
        assert result.warnings == []

    def test_mutable(self):
        """LandscapeResult ist mutable (NOT frozen)."""
        result = LandscapeResult()
        result.total_patents = 500
        assert result.total_patents == 500

    def test_slots(self):
        """LandscapeResult nutzt __slots__ fuer Speichereffizienz."""
        result = LandscapeResult()
        assert not hasattr(result, "__dict__")


# ---------------------------------------------------------------------------
# Tests: CRIT-1 — Publikations-Triplet
# ---------------------------------------------------------------------------

class TestAnalyzeLandscapePublicationScopeCrit1:
    """Header ``total_publications`` MUSS aus CORDIS-Scope kommen (Bug CRIT-1).

    Vor AP2: Header bezog ``total_publications`` aus OpenAIRE (Faktor 1580
    abweichend von UC13 bei mRNA).  Ab AP2: derselbe CORDIS_LINKED-Query
    wie in publication-svc — Konsistenz strukturell erzwungen.
    """

    async def test_total_publications_comes_from_repo_not_openaire(self):
        """Selbst wenn OpenAIRE divergierende Zahlen liefert, gewinnt das Repo."""
        repo = _make_repo(cordis_publications_total=2_456)
        openaire = _make_openaire(
            # OpenAIRE liefert *fiktive* 311.500 (der CRIT-1-Worst-Case),
            # der Use-Case darf diese NICHT als Header-Total verwenden.
            publication_years=[{"year": 2020, "count": 150_000},
                               {"year": 2024, "count": 161_500}],
        )
        uc = AnalyzeLandscape(repo=repo, openaire=openaire)

        result = await uc.execute("mRNA", start_year=2015, end_year=2025)

        assert result.total_publications == 2_456, (
            "Header.total_publications muss aus CORDIS-Repo kommen, nicht OpenAIRE."
        )

    async def test_repo_method_count_cordis_publications_is_called(self):
        """Der Use-Case ruft die neue Master-Methode auf."""
        repo = _make_repo(cordis_publications_total=1_000)
        uc = AnalyzeLandscape(repo=repo, openaire=None)

        await uc.execute("quantum computing", start_year=2020, end_year=2024)

        repo.count_cordis_publications.assert_called_once()

    async def test_without_openaire_still_has_publications_from_repo(self):
        """Ohne OpenAIRE-Adapter liefert das Repo weiterhin Publikationen."""
        repo = _make_repo(cordis_publications_total=789)
        uc = AnalyzeLandscape(repo=repo, openaire=None)

        result = await uc.execute("ai", start_year=2020, end_year=2024)

        assert result.total_publications == 789

    async def test_publication_scope_label_cordis_linked(self):
        """Die Data-Source-Liste enthaelt das kanonische Label aus shared.domain."""
        from shared.domain.publication_definitions import (
            PublicationScope,
            canonical_publication_label,
        )
        repo = _make_repo(cordis_publications_total=42)
        uc = AnalyzeLandscape(repo=repo, openaire=None)

        result = await uc.execute("5g", start_year=2020, end_year=2024)

        cordis_label = canonical_publication_label(PublicationScope.CORDIS_LINKED)
        pub_sources = [ds for ds in result.data_sources if ds.get("type") == "PUBLICATION"]
        # Mindestens eine PUBLICATION-Datenquelle MUSS das CORDIS-Label tragen.
        assert any(cordis_label in ds.get("name", "") for ds in pub_sources), (
            f"Erwartet '{cordis_label}' in data_sources, gefunden: {pub_sources}"
        )


# ---------------------------------------------------------------------------
# Tests: AP8 — data_complete_year aus shared-Helper, kein Hardcoding
# ---------------------------------------------------------------------------


class TestAnalyzeLandscapeDataCompleteYearMaj7Maj8:
    """LandscapeResult MUSS ``data_complete_year`` ausweisen.

    Bug MAJ-7/MAJ-8: Header zeigte CAGR auf Basis unvollstaendiger Jahre,
    Frontend hatte keinen Hinweis, ob das Endjahr vollstaendig ist. Nach
    AP8 wird ``data_complete_year`` aus
    :func:`shared.domain.year_completeness.last_complete_year` abgeleitet
    und im Result mitgegeben.
    """

    async def test_data_complete_year_field_present(self):
        repo = _make_repo()
        uc = AnalyzeLandscape(repo=repo, openaire=None)

        result = await uc.execute("ai", start_year=2020, end_year=2024)

        assert hasattr(result, "data_complete_year")

    async def test_data_complete_year_uses_helper(self):
        """Default-Wert kommt aus ``last_complete_year()`` (heute 2025)."""
        repo = _make_repo()
        uc = AnalyzeLandscape(repo=repo, openaire=None)

        result = await uc.execute("ai", start_year=2020, end_year=2026)

        # Helper liefert 2025 bei heute 2026-04-14, aktuell mind. 2024.
        assert result.data_complete_year == last_complete_year()
        assert result.data_complete_year >= 2024

    async def test_cagr_clipped_to_complete_years(self):
        """CAGR ignoriert Daten nach ``data_complete_year``.

        Selbst wenn das Repo Jahre bis 2026 liefert, darf CAGR nur ueber
        Jahre bis ``last_complete_year()`` berechnet werden. ``cagr()``
        gibt Prozentwerte zurueck.
        """
        # Repo liefert 2020 -> 100, 2026 -> 1_000_000 (kuenstlich hoher Spike
        # im laufenden Jahr).  CAGR muss diesen Spike ignorieren.
        repo = _make_repo(
            patent_years=[
                YearCount(year=2020, count=100),
                YearCount(year=2025, count=200),
                YearCount(year=2026, count=1_000_000),
            ],
        )
        uc = AnalyzeLandscape(repo=repo, openaire=None)

        result = await uc.execute("ai", start_year=2020, end_year=2026)

        # Mit dem Spike (1_000_000): CAGR wuerde > 300% sein.
        # Geclippt (100 → 200, 5 Jahre): ca. 14.87%.
        assert 0.0 < result.cagr_patents < 50.0, (
            f"CAGR {result.cagr_patents:.2f}% deutet auf nicht-geclipptes "
            "Spike-Jahr 2026 hin."
        )

    async def test_warning_when_end_year_after_data_complete_year(self):
        """Wenn das User-Endjahr > ``last_complete_year()`` ist, MUSS
        eine Warning mit Code ``DATA_INCOMPLETE_RECENT_YEARS`` gesetzt werden.
        """
        repo = _make_repo()
        uc = AnalyzeLandscape(repo=repo, openaire=None)

        result = await uc.execute("ai", start_year=2020, end_year=2026)

        codes = [w["code"] for w in result.warnings]
        assert "DATA_INCOMPLETE_RECENT_YEARS" in codes


class TestSafeCagrUsesYearHelper:
    """``_safe_cagr`` MUSS standardmaessig ``last_complete_year()`` nutzen.

    Vorher hardcoded 2024 — das laeuft ab 2026 in eine zu kurze Reihe.
    Nach AP8 ist der Default dynamisch.
    """

    def test_safe_cagr_default_clip_dynamic(self):
        # Daten von 2020-2026, ohne explizites data_complete_year-Argument.
        data = [
            YearCount(year=2020, count=100),
            YearCount(year=2025, count=200),
            YearCount(year=2026, count=999_999),
        ]
        result = _safe_cagr(data, periods=6)
        # Heute = 2026: last_complete_year() = 2025 ⇒ Spike (2026) ist raus.
        # Erwartet: moderate CAGR von 100 → 200 ueber 5 Jahre ≈ 14.87 (Prozent).
        # ``cagr()`` gibt Prozentwerte zurueck; ohne Clip waere CAGR > 300%.
        assert 0.0 < result < 50.0
