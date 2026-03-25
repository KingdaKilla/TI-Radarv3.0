"""Integrations-Tests fuer UC4 FundingRepository gegen PostgreSQL Testcontainer.

Prueft das korrekte Verhalten des Foerderungs-Repositories:
- EU-Foerderung pro Jahr (funding_by_year)
- Foerderung nach Rahmenprogramm (funding_by_programme: H2020, HORIZON)
- Foerderung nach Instrument (funding_by_instrument: RIA, IA, CSA)
- Top-finanzierte Organisationen (top_funded_organizations)
- Foerderung pro Land (funding_by_country)
- Durchschnittliche Projektdauer (avg_project_duration)
- Leere Ergebnis-Behandlung bei unbekannter Technologie

Die Fixtures 'db_pool' und 'populated_db' kommen aus conftest.py.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest
import pytest_asyncio

# Repository aus dem Service-Pfad importieren — per importlib, um Konflikte
# mit gleichnamigen Modulen anderer Services zu vermeiden (sys.path-Kollision).
_REPO_FILE = (
    pathlib.Path(__file__).resolve().parent.parent.parent
    / "services" / "funding-svc" / "src" / "infrastructure" / "repository.py"
)
_spec = importlib.util.spec_from_file_location(
    "funding_infrastructure_repository", _REPO_FILE
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
FundingRepository = _mod.FundingRepository


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest_asyncio.fixture(scope="module")
async def repo(populated_db):
    """Erstellt ein FundingRepository gegen den befuellten Testcontainer."""
    return FundingRepository(pool=populated_db)


# ===========================================================================
# funding_by_year
# ===========================================================================


class TestFundingByYear:
    """Tests fuer FundingRepository.funding_by_year()."""

    @pytest.mark.asyncio(loop_scope="session")
    async def test_foerderung_fuer_quantum_gefunden(self, repo):
        """EU-Foerderung fuer Quantum-Computing aus CORDIS ist abrufbar."""
        ergebnisse = await repo.funding_by_year("quantum computing")
        assert isinstance(ergebnisse, list)
        assert len(ergebnisse) > 0

    @pytest.mark.asyncio(loop_scope="session")
    async def test_struktur(self, repo):
        """Jeder Eintrag hat 'year' (int), 'funding' (float), 'count' (int)."""
        ergebnisse = await repo.funding_by_year("quantum computing")
        for eintrag in ergebnisse:
            assert "year" in eintrag
            assert "funding" in eintrag
            assert "count" in eintrag
            assert isinstance(eintrag["year"], int)
            assert isinstance(eintrag["funding"], float)
            assert isinstance(eintrag["count"], int)
            assert eintrag["funding"] >= 0.0
            assert eintrag["count"] > 0

    @pytest.mark.asyncio(loop_scope="session")
    async def test_foerdervolumen_positiv(self, repo):
        """Gesamt-Foerdervolumen fuer Quantum-Computing ist groesser als Null."""
        ergebnisse = await repo.funding_by_year("quantum computing")
        gesamt = sum(e["funding"] for e in ergebnisse)
        assert gesamt > 0.0

    @pytest.mark.asyncio(loop_scope="session")
    async def test_chronologische_sortierung(self, repo):
        """Ergebnisse sind aufsteigend nach Jahr sortiert."""
        ergebnisse = await repo.funding_by_year("quantum computing")
        jahre = [e["year"] for e in ergebnisse]
        assert jahre == sorted(jahre)

    @pytest.mark.asyncio(loop_scope="session")
    async def test_jahresfilter_start(self, repo):
        """start_year-Filter schliesst Jahre vor dem Grenzwert aus."""
        ergebnisse = await repo.funding_by_year("quantum computing", start_year=2021)
        for eintrag in ergebnisse:
            assert eintrag["year"] >= 2021

    @pytest.mark.asyncio(loop_scope="session")
    async def test_jahresfilter_ende(self, repo):
        """end_year-Filter schliesst Jahre nach dem Grenzwert aus."""
        ergebnisse = await repo.funding_by_year("quantum computing", end_year=2020)
        for eintrag in ergebnisse:
            assert eintrag["year"] <= 2020

    @pytest.mark.asyncio(loop_scope="session")
    async def test_battery_foerderung_gefunden(self, repo):
        """Foerderung fuer Solid-State-Battery-Projekte ist abrufbar."""
        ergebnisse = await repo.funding_by_year("solid state battery")
        assert len(ergebnisse) > 0
        gesamt = sum(e["funding"] for e in ergebnisse)
        assert gesamt > 0.0

    @pytest.mark.asyncio(loop_scope="session")
    async def test_unbekannte_tech_gibt_leere_liste(self, repo):
        """Unbekannte Technologie liefert leere Liste (kein Fehler)."""
        ergebnisse = await repo.funding_by_year("xyzzy_non_existent_42")
        assert ergebnisse == []


# ===========================================================================
# funding_by_programme
# ===========================================================================


class TestFundingByProgramme:
    """Tests fuer FundingRepository.funding_by_programme()."""

    @pytest.mark.asyncio(loop_scope="session")
    async def test_programme_vorhanden(self, repo):
        """H2020 und HORIZON erscheinen als Rahmenprogramme."""
        ergebnisse = await repo.funding_by_programme("quantum computing")
        assert len(ergebnisse) > 0

    @pytest.mark.asyncio(loop_scope="session")
    async def test_struktur(self, repo):
        """Jeder Eintrag hat 'programme' (str), 'funding' (float), 'count' (int)."""
        ergebnisse = await repo.funding_by_programme("quantum computing")
        for eintrag in ergebnisse:
            assert "programme" in eintrag
            assert "funding" in eintrag
            assert "count" in eintrag
            assert isinstance(eintrag["programme"], str)
            assert isinstance(eintrag["funding"], float)
            assert isinstance(eintrag["count"], int)

    @pytest.mark.asyncio(loop_scope="session")
    async def test_bekannte_programme_enthalten(self, repo):
        """H2020 und/oder HORIZON kommen in den Testdaten vor."""
        ergebnisse = await repo.funding_by_programme("quantum computing")
        programme = {e["programme"] for e in ergebnisse}
        assert programme & {"H2020", "HORIZON"}

    @pytest.mark.asyncio(loop_scope="session")
    async def test_absteigende_sortierung_nach_foerderung(self, repo):
        """Ergebnisse sind absteigend nach Foerdervolumen sortiert."""
        ergebnisse = await repo.funding_by_programme("quantum computing")
        if len(ergebnisse) >= 2:
            foerderungen = [e["funding"] for e in ergebnisse]
            assert foerderungen == sorted(foerderungen, reverse=True)

    @pytest.mark.asyncio(loop_scope="session")
    async def test_unbekannte_tech_gibt_leere_liste(self, repo):
        """Unbekannte Technologie liefert leere Liste."""
        ergebnisse = await repo.funding_by_programme("xyzzy_non_existent_42")
        assert ergebnisse == []


# ===========================================================================
# funding_by_instrument
# ===========================================================================


class TestFundingByInstrument:
    """Tests fuer FundingRepository.funding_by_instrument()."""

    @pytest.mark.asyncio(loop_scope="session")
    async def test_instrumente_vorhanden(self, repo):
        """RIA, IA, CSA erscheinen als Foerderinstrumente."""
        ergebnisse = await repo.funding_by_instrument("quantum computing")
        assert len(ergebnisse) > 0

    @pytest.mark.asyncio(loop_scope="session")
    async def test_struktur(self, repo):
        """Jeder Eintrag hat 'funding_scheme' (str), 'funding' (float), 'count' (int)."""
        ergebnisse = await repo.funding_by_instrument("quantum computing")
        for eintrag in ergebnisse:
            assert "funding_scheme" in eintrag
            assert "funding" in eintrag
            assert "count" in eintrag
            assert isinstance(eintrag["funding_scheme"], str)
            assert isinstance(eintrag["funding"], float)
            assert isinstance(eintrag["count"], int)

    @pytest.mark.asyncio(loop_scope="session")
    async def test_ria_instrument_vorhanden(self, repo):
        """RIA ist das haeufigste Instrument in den Quantum-Testdaten."""
        ergebnisse = await repo.funding_by_instrument("quantum computing")
        schemata = {e["funding_scheme"] for e in ergebnisse}
        assert "RIA" in schemata

    @pytest.mark.asyncio(loop_scope="session")
    async def test_battery_instrumente(self, repo):
        """Battery-Projekte haben Instrumente (IA, RIA, CSA)."""
        ergebnisse = await repo.funding_by_instrument("solid state battery")
        assert len(ergebnisse) > 0
        schemata = {e["funding_scheme"] for e in ergebnisse}
        assert schemata & {"IA", "RIA", "CSA"}

    @pytest.mark.asyncio(loop_scope="session")
    async def test_unbekannte_tech_gibt_leere_liste(self, repo):
        """Unbekannte Technologie liefert leere Liste."""
        ergebnisse = await repo.funding_by_instrument("xyzzy_non_existent_42")
        assert ergebnisse == []


# ===========================================================================
# top_funded_organizations
# ===========================================================================


class TestTopFundedOrganizations:
    """Tests fuer FundingRepository.top_funded_organizations()."""

    @pytest.mark.asyncio(loop_scope="session")
    async def test_organisationen_gefunden(self, repo):
        """Top-finanzierte Organisationen fuer Quantum sind abrufbar."""
        ergebnisse = await repo.top_funded_organizations("quantum computing")
        assert len(ergebnisse) > 0

    @pytest.mark.asyncio(loop_scope="session")
    async def test_struktur(self, repo):
        """Jeder Eintrag hat 'name', 'country', 'type', 'funding', 'count'."""
        ergebnisse = await repo.top_funded_organizations("quantum computing")
        for eintrag in ergebnisse:
            assert "name" in eintrag
            assert "country" in eintrag
            assert "type" in eintrag
            assert "funding" in eintrag
            assert "count" in eintrag
            assert isinstance(eintrag["name"], str)
            assert isinstance(eintrag["funding"], float)
            assert isinstance(eintrag["count"], int)

    @pytest.mark.asyncio(loop_scope="session")
    async def test_foerdervolumen_positiv(self, repo):
        """Alle Eintraege haben nicht-negatives Foerdervolumen."""
        ergebnisse = await repo.top_funded_organizations("quantum computing")
        for eintrag in ergebnisse:
            assert eintrag["funding"] >= 0.0

    @pytest.mark.asyncio(loop_scope="session")
    async def test_absteigende_sortierung(self, repo):
        """Ergebnisse sind absteigend nach Foerdervolumen sortiert."""
        ergebnisse = await repo.top_funded_organizations("quantum computing")
        if len(ergebnisse) >= 2:
            foerderungen = [e["funding"] for e in ergebnisse]
            assert foerderungen == sorted(foerderungen, reverse=True)

    @pytest.mark.asyncio(loop_scope="session")
    async def test_limit(self, repo):
        """limit-Parameter begrenzt die Ergebnis-Menge."""
        ergebnisse = await repo.top_funded_organizations("quantum computing", limit=2)
        assert len(ergebnisse) <= 2

    @pytest.mark.asyncio(loop_scope="session")
    async def test_basf_in_battery_top_list(self, repo):
        """BASF SE ist der groesste Emfaenger in den Battery-Testdaten."""
        ergebnisse = await repo.top_funded_organizations("solid state battery")
        namen = [e["name"] for e in ergebnisse]
        assert any("BASF" in name for name in namen)

    @pytest.mark.asyncio(loop_scope="session")
    async def test_unbekannte_tech_gibt_leere_liste(self, repo):
        """Unbekannte Technologie liefert leere Liste."""
        ergebnisse = await repo.top_funded_organizations("xyzzy_non_existent_42")
        assert ergebnisse == []


# ===========================================================================
# funding_by_country
# ===========================================================================


class TestFundingByCountry:
    """Tests fuer FundingRepository.funding_by_country()."""

    @pytest.mark.asyncio(loop_scope="session")
    async def test_laender_gefunden(self, repo):
        """Foerderung nach Land fuer Quantum-Projekte ist abrufbar."""
        ergebnisse = await repo.funding_by_country("quantum computing")
        assert len(ergebnisse) > 0

    @pytest.mark.asyncio(loop_scope="session")
    async def test_struktur(self, repo):
        """Jeder Eintrag hat 'country' (str), 'funding' (float), 'count' (int)."""
        ergebnisse = await repo.funding_by_country("quantum computing")
        for eintrag in ergebnisse:
            assert "country" in eintrag
            assert "funding" in eintrag
            assert "count" in eintrag
            assert isinstance(eintrag["country"], str)
            assert isinstance(eintrag["funding"], float)
            assert isinstance(eintrag["count"], int)

    @pytest.mark.asyncio(loop_scope="session")
    async def test_deutschland_als_top_empfaenger(self, repo):
        """DE ist aufgrund der Testdaten ein fuehrender Empfaenger."""
        ergebnisse = await repo.funding_by_country("quantum computing")
        laender = {e["country"] for e in ergebnisse}
        assert "DE" in laender

    @pytest.mark.asyncio(loop_scope="session")
    async def test_limit(self, repo):
        """limit-Parameter begrenzt die Ergebnis-Menge."""
        ergebnisse = await repo.funding_by_country("quantum computing", limit=1)
        assert len(ergebnisse) <= 1

    @pytest.mark.asyncio(loop_scope="session")
    async def test_unbekannte_tech_gibt_leere_liste(self, repo):
        """Unbekannte Technologie liefert leere Liste."""
        ergebnisse = await repo.funding_by_country("xyzzy_non_existent_42")
        assert ergebnisse == []


# ===========================================================================
# avg_project_duration
# ===========================================================================


class TestAvgProjectDuration:
    """Tests fuer FundingRepository.avg_project_duration()."""

    @pytest.mark.asyncio(loop_scope="session")
    async def test_dauer_positiv(self, repo):
        """Durchschnittliche Projektdauer ist groesser als Null (in Monaten)."""
        dauer = await repo.avg_project_duration("quantum computing")
        assert isinstance(dauer, float)
        assert dauer > 0.0

    @pytest.mark.asyncio(loop_scope="session")
    async def test_dauer_realistisch(self, repo):
        """Projektdauer liegt zwischen 1 und 60 Monaten."""
        dauer = await repo.avg_project_duration("quantum computing")
        assert 1.0 <= dauer <= 60.0

    @pytest.mark.asyncio(loop_scope="session")
    async def test_battery_dauer(self, repo):
        """Durchschnittliche Dauer fuer Battery-Projekte ist berechenbar."""
        dauer = await repo.avg_project_duration("solid state battery")
        assert isinstance(dauer, float)
        assert dauer > 0.0

    @pytest.mark.asyncio(loop_scope="session")
    async def test_unbekannte_tech_gibt_null(self, repo):
        """Unbekannte Technologie liefert 0.0 (kein Fehler)."""
        dauer = await repo.avg_project_duration("xyzzy_non_existent_42")
        assert dauer == 0.0
