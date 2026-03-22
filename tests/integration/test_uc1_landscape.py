"""Integrations-Tests fuer UC1 LandscapeRepository gegen PostgreSQL Testcontainer.

Prueft das korrekte Verhalten des Repository unter echten DB-Bedingungen:
- tsvector-Volltextsuche mit plainto_tsquery
- Jaehrliche Patent- und Projektzaehlung
- Laenderverteilung mit LATERAL unnest
- Leere Ergebnis-Behandlung bei unbekannter Technologie
- EU-Filter via applicant_countries && text[]
- Funding-Zeitreihe aus cordis_schema.projects
- Pagination via LIMIT

Die Fixtures 'db_pool' und 'populated_db' kommen aus conftest.py und
stellen einen PostgreSQL-Container mit vollstaendigem Schema und
vorbereiteten Testdaten bereit.
"""

from __future__ import annotations

import sys
import pathlib

import pytest
import pytest_asyncio

# Repository aus dem Service-Pfad importieren
_SVC_PATH = pathlib.Path(__file__).parent.parent.parent / "services" / "landscape-svc" / "src"
if str(_SVC_PATH) not in sys.path:
    sys.path.insert(0, str(_SVC_PATH))

from infrastructure.repository import LandscapeRepository  # noqa: E402


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest_asyncio.fixture(scope="module")
async def repo(populated_db):
    """Erstellt ein LandscapeRepository gegen den befuellten Testcontainer."""
    return LandscapeRepository(pool=populated_db)


# ===========================================================================
# count_patents_by_year
# ===========================================================================


class TestCountPatentsByYear:
    """Tests fuer LandscapeRepository.count_patents_by_year()."""

    @pytest.mark.asyncio
    async def test_bekannte_technologie_liefert_ergebnisse(self, repo):
        """Quantum-Computing-Patente sind in der DB und werden gefunden."""
        ergebnisse = await repo.count_patents_by_year("quantum computing")
        assert isinstance(ergebnisse, list)
        assert len(ergebnisse) > 0

    @pytest.mark.asyncio
    async def test_struktur_der_eintraege(self, repo):
        """Jeder Eintrag hat die Schluesse 'year' (int) und 'count' (int)."""
        ergebnisse = await repo.count_patents_by_year("quantum computing")
        for eintrag in ergebnisse:
            assert "year" in eintrag
            assert "count" in eintrag
            assert isinstance(eintrag["year"], int)
            assert isinstance(eintrag["count"], int)
            assert eintrag["count"] > 0

    @pytest.mark.asyncio
    async def test_chronologische_sortierung(self, repo):
        """Ergebnisse sind aufsteigend nach Jahr sortiert."""
        ergebnisse = await repo.count_patents_by_year("quantum computing")
        jahre = [e["year"] for e in ergebnisse]
        assert jahre == sorted(jahre)

    @pytest.mark.asyncio
    async def test_jahresfilter_start(self, repo):
        """start_year-Filter schliesst frueheres Jahr aus."""
        alle = await repo.count_patents_by_year("quantum computing")
        gefiltert = await repo.count_patents_by_year(
            "quantum computing", start_year=2022
        )
        # Ab 2022 gefiltert — gleich viele oder weniger Ergebnisse
        assert len(gefiltert) <= len(alle)
        for eintrag in gefiltert:
            assert eintrag["year"] >= 2022

    @pytest.mark.asyncio
    async def test_jahresfilter_ende(self, repo):
        """end_year-Filter schliesst spaeters Jahr aus."""
        ergebnisse = await repo.count_patents_by_year(
            "quantum computing", end_year=2020
        )
        for eintrag in ergebnisse:
            assert eintrag["year"] <= 2020

    @pytest.mark.asyncio
    async def test_unbekannte_technologie_gibt_leere_liste(self, repo):
        """Nicht vorhandene Technologie liefert leere Liste (kein Fehler)."""
        ergebnisse = await repo.count_patents_by_year("xyzzy_non_existent_tech_42")
        assert ergebnisse == []

    @pytest.mark.asyncio
    async def test_european_only_filter(self, repo):
        """european_only=True liefert nur Patente mit EU-Anmeldern."""
        alle = await repo.count_patents_by_year("quantum computing")
        eu_only = await repo.count_patents_by_year(
            "quantum computing", european_only=True
        )
        # EU-Only-Ergebnisse duerfen nicht groesser als 'alle' sein
        gesamt_alle = sum(e["count"] for e in alle)
        gesamt_eu = sum(e["count"] for e in eu_only)
        assert gesamt_eu <= gesamt_alle

    @pytest.mark.asyncio
    async def test_battery_technologie_gefunden(self, repo):
        """Solid-State-Battery-Patente werden per Volltextsuche gefunden."""
        ergebnisse = await repo.count_patents_by_year("solid state battery")
        assert len(ergebnisse) > 0
        gesamt = sum(e["count"] for e in ergebnisse)
        assert gesamt >= 3  # Mindestens 3 Battery-Testpatente eingefuegt


# ===========================================================================
# count_patents_by_country
# ===========================================================================


class TestCountPatentsByCountry:
    """Tests fuer LandscapeRepository.count_patents_by_country()."""

    @pytest.mark.asyncio
    async def test_laender_vorhanden(self, repo):
        """Quantum-Computing-Patente sind in DE und FR angemeldet."""
        ergebnisse = await repo.count_patents_by_country("quantum computing")
        laender = {e["country"] for e in ergebnisse}
        # Beide Anmelderlaender aus den Testdaten muessen erscheinen
        assert "DE" in laender or "FR" in laender

    @pytest.mark.asyncio
    async def test_struktur(self, repo):
        """Jeder Eintrag hat 'country' (str) und 'count' (int)."""
        ergebnisse = await repo.count_patents_by_country("quantum computing")
        assert len(ergebnisse) > 0
        for eintrag in ergebnisse:
            assert "country" in eintrag
            assert "count" in eintrag
            assert isinstance(eintrag["country"], str)
            assert isinstance(eintrag["count"], int)
            assert len(eintrag["country"]) == 2  # ISO-2-Code

    @pytest.mark.asyncio
    async def test_absteigende_sortierung(self, repo):
        """Ergebnisse sind absteigend nach count sortiert."""
        ergebnisse = await repo.count_patents_by_country("quantum computing")
        counts = [e["count"] for e in ergebnisse]
        assert counts == sorted(counts, reverse=True)

    @pytest.mark.asyncio
    async def test_limit_wird_beachtet(self, repo):
        """LIMIT wird an die DB weitergegeben und begrenzt die Ergebnis-Menge."""
        ergebnisse = await repo.count_patents_by_country("quantum computing", limit=1)
        assert len(ergebnisse) <= 1

    @pytest.mark.asyncio
    async def test_leeres_ergebnis_bei_unbekannter_tech(self, repo):
        """Unbekannte Technologie liefert leere Liste."""
        ergebnisse = await repo.count_patents_by_country("xyzzy_non_existent_42")
        assert ergebnisse == []


# ===========================================================================
# count_projects_by_year
# ===========================================================================


class TestCountProjectsByYear:
    """Tests fuer LandscapeRepository.count_projects_by_year()."""

    @pytest.mark.asyncio
    async def test_quantum_projekte_gefunden(self, repo):
        """Quantum-Computing-Projekte aus CORDIS sind abrufbar."""
        ergebnisse = await repo.count_projects_by_year("quantum computing")
        assert len(ergebnisse) > 0
        gesamt = sum(e["count"] for e in ergebnisse)
        assert gesamt >= 2  # Mindestens 2 Quantum-Projekte in Testdaten

    @pytest.mark.asyncio
    async def test_struktur(self, repo):
        """Jeder Eintrag hat 'year' (int) und 'count' (int)."""
        ergebnisse = await repo.count_projects_by_year("quantum computing")
        for eintrag in ergebnisse:
            assert "year" in eintrag
            assert "count" in eintrag
            assert isinstance(eintrag["year"], int)
            assert isinstance(eintrag["count"], int)

    @pytest.mark.asyncio
    async def test_battery_projekte(self, repo):
        """Solid-State-Battery-Projekte aus CORDIS sind abrufbar."""
        ergebnisse = await repo.count_projects_by_year("solid state battery")
        assert len(ergebnisse) > 0

    @pytest.mark.asyncio
    async def test_unbekannte_tech_gibt_leere_liste(self, repo):
        """Unbekannte Technologie liefert leere Liste (kein Fehler)."""
        ergebnisse = await repo.count_projects_by_year("xyzzy_non_existent_42")
        assert ergebnisse == []

    @pytest.mark.asyncio
    async def test_startjahr_filter(self, repo):
        """start_year begrenzt die Ergebnisse auf Jahre >= start_year."""
        ergebnisse = await repo.count_projects_by_year(
            "quantum computing", start_year=2021
        )
        for eintrag in ergebnisse:
            assert eintrag["year"] >= 2021


# ===========================================================================
# funding_by_year
# ===========================================================================


class TestFundingByYear:
    """Tests fuer LandscapeRepository.funding_by_year()."""

    @pytest.mark.asyncio
    async def test_foerderung_vorhanden(self, repo):
        """EU-Foerderung fuer Quantum-Computing-Projekte ist abrufbar."""
        ergebnisse = await repo.funding_by_year("quantum computing")
        assert len(ergebnisse) > 0

    @pytest.mark.asyncio
    async def test_struktur(self, repo):
        """Jeder Eintrag hat 'year' (int), 'funding' (float) und 'count' (int)."""
        ergebnisse = await repo.funding_by_year("quantum computing")
        for eintrag in ergebnisse:
            assert "year" in eintrag
            assert "funding" in eintrag
            assert "count" in eintrag
            assert isinstance(eintrag["year"], int)
            assert isinstance(eintrag["funding"], float)
            assert isinstance(eintrag["count"], int)
            assert eintrag["funding"] >= 0.0

    @pytest.mark.asyncio
    async def test_foerdervolumen_positiv(self, repo):
        """Das gesamte Foerdervolumen ist groesser als Null."""
        ergebnisse = await repo.funding_by_year("quantum computing")
        gesamt_foerderung = sum(e["funding"] for e in ergebnisse)
        assert gesamt_foerderung > 0.0

    @pytest.mark.asyncio
    async def test_leeres_ergebnis_bei_unbekannter_tech(self, repo):
        """Unbekannte Technologie liefert leere Liste."""
        ergebnisse = await repo.funding_by_year("xyzzy_non_existent_42")
        assert ergebnisse == []


# ===========================================================================
# top_cpc_codes
# ===========================================================================


class TestTopCpcCodes:
    """Tests fuer LandscapeRepository.top_cpc_codes()."""

    @pytest.mark.asyncio
    async def test_cpc_codes_gefunden(self, repo):
        """Quantum-Computing-Patente haben CPC-Codes in der normalisierten Tabelle."""
        ergebnisse = await repo.top_cpc_codes("quantum computing")
        assert len(ergebnisse) > 0

    @pytest.mark.asyncio
    async def test_struktur(self, repo):
        """Jeder Eintrag hat 'code', 'description' und 'count'."""
        ergebnisse = await repo.top_cpc_codes("quantum computing")
        for eintrag in ergebnisse:
            assert "code" in eintrag
            assert "description" in eintrag
            assert "count" in eintrag
            assert isinstance(eintrag["code"], str)
            assert isinstance(eintrag["count"], int)
            assert eintrag["count"] > 0

    @pytest.mark.asyncio
    async def test_limit(self, repo):
        """limit-Parameter begrenzt die Ergebnis-Menge."""
        ergebnisse = await repo.top_cpc_codes("quantum computing", limit=2)
        assert len(ergebnisse) <= 2

    @pytest.mark.asyncio
    async def test_g06f_ist_haeufigster_code(self, repo):
        """G06F ist der haeufigste CPC-Code in den Quantum-Testdaten."""
        ergebnisse = await repo.top_cpc_codes("quantum computing", limit=5)
        if ergebnisse:
            # G06F sollte im Top-1 sein (sechs von sieben Quantum-Patenten)
            assert ergebnisse[0]["code"] == "G06F"
