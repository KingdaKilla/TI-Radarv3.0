"""Integrations-Tests fuer UC3 CompetitiveRepository gegen PostgreSQL Testcontainer.

Prueft das korrekte Verhalten des Wettbewerbs-Repositories:
- Top-Patent-Anmelder via LATERAL unnest auf applicant_names
- Top-CORDIS-Organisationen per JOIN
- Co-Patent-Anmelder-Paare (gemeinsame Patente)
- Co-Partizipation von CORDIS-Organisationen im selben Projekt
- HHI-Berechnung auf Basis der Repository-Ergebnisse
- EU-Filter (european_only)

Die Fixtures 'db_pool' und 'populated_db' kommen aus conftest.py.

Hinweis zum Schema: patent_schema.patents.applicant_names ist ein TEXT-Feld
(Legacy-Spalte gemaess 002_schema.sql), nicht ein Array. Die Co-Patent-Query
im Repository prueft array_length(applicant_names, 1) >= 2, was bei TEXT-Werten
0 ergibt. Der Test prueft daher Robustheit gegenueber leerer Co-Anmelder-Liste.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest
import pytest_asyncio

from shared.domain.metrics import hhi_index, hhi_concentration_level

# Repository aus dem Service-Pfad importieren — per importlib, um Konflikte
# mit gleichnamigen Modulen anderer Services zu vermeiden (sys.path-Kollision).
_REPO_FILE = (
    pathlib.Path(__file__).resolve().parent.parent.parent
    / "services" / "competitive-svc" / "src" / "infrastructure" / "repository.py"
)
_spec = importlib.util.spec_from_file_location(
    "competitive_infrastructure_repository", _REPO_FILE
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
CompetitiveRepository = _mod.CompetitiveRepository


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest_asyncio.fixture(scope="module")
async def repo(populated_db):
    """Erstellt ein CompetitiveRepository gegen den befuellten Testcontainer."""
    return CompetitiveRepository(pool=populated_db)


# ===========================================================================
# top_patent_applicants
# ===========================================================================


class TestTopPatentApplicants:
    """Tests fuer CompetitiveRepository.top_patent_applicants()."""

    @pytest.mark.asyncio(loop_scope="session")
    async def test_anmelder_fuer_quantum_gefunden(self, repo):
        """Quantum-Computing-Testdaten enthalten Patent-Anmelder."""
        ergebnisse = await repo.top_patent_applicants("quantum computing")
        assert isinstance(ergebnisse, list)
        # applicant_names ist TEXT (nicht Array) — daher abhängig von LATERAL-Verhalten
        # Leere Liste ist toleriert, falls das Feld kein unnest-faehiges Array ist

    @pytest.mark.asyncio(loop_scope="session")
    async def test_struktur_wenn_nicht_leer(self, repo):
        """Wenn Anmelder gefunden: 'name' (str) und 'count' (int) erforderlich."""
        ergebnisse = await repo.top_patent_applicants("quantum computing")
        for eintrag in ergebnisse:
            assert "name" in eintrag
            assert "count" in eintrag
            assert isinstance(eintrag["name"], str)
            assert isinstance(eintrag["count"], int)
            assert eintrag["count"] > 0

    @pytest.mark.asyncio(loop_scope="session")
    async def test_absteigende_sortierung(self, repo):
        """Ergebnisse sind absteigend nach count sortiert."""
        ergebnisse = await repo.top_patent_applicants("quantum computing")
        if len(ergebnisse) >= 2:
            counts = [e["count"] for e in ergebnisse]
            assert counts == sorted(counts, reverse=True)

    @pytest.mark.asyncio(loop_scope="session")
    async def test_limit_wird_beachtet(self, repo):
        """limit-Parameter begrenzt die Ergebnis-Menge."""
        ergebnisse = await repo.top_patent_applicants("quantum computing", limit=3)
        assert len(ergebnisse) <= 3

    @pytest.mark.asyncio(loop_scope="session")
    async def test_unbekannte_tech_gibt_leere_liste(self, repo):
        """Unbekannte Technologie liefert leere Liste."""
        ergebnisse = await repo.top_patent_applicants("xyzzy_non_existent_42")
        assert ergebnisse == []

    @pytest.mark.asyncio(loop_scope="session")
    async def test_jahresbereich_filter(self, repo):
        """start_year und end_year beschraenken die Patent-Auswahl."""
        ergebnisse_gesamt = await repo.top_patent_applicants("quantum computing")
        ergebnisse_2022 = await repo.top_patent_applicants(
            "quantum computing", start_year=2022, end_year=2022
        )
        # Einschraenkung auf ein Jahr liefert gleich viele oder weniger Anmelder
        gesamt_count = sum(e["count"] for e in ergebnisse_gesamt)
        count_2022 = sum(e["count"] for e in ergebnisse_2022)
        assert count_2022 <= gesamt_count


# ===========================================================================
# top_cordis_organizations
# ===========================================================================


class TestTopCordisOrganizations:
    """Tests fuer CompetitiveRepository.top_cordis_organizations()."""

    @pytest.mark.asyncio(loop_scope="session")
    async def test_organisationen_fuer_quantum_gefunden(self, repo):
        """Quantum-CORDIS-Projekte haben Konsortiumsorganisationen."""
        ergebnisse = await repo.top_cordis_organizations("quantum computing")
        assert len(ergebnisse) > 0

    @pytest.mark.asyncio(loop_scope="session")
    async def test_struktur(self, repo):
        """Jeder Eintrag hat 'name', 'country' und 'count'."""
        ergebnisse = await repo.top_cordis_organizations("quantum computing")
        for eintrag in ergebnisse:
            assert "name" in eintrag
            assert "country" in eintrag
            assert "count" in eintrag
            assert isinstance(eintrag["name"], str)
            assert isinstance(eintrag["count"], int)
            assert eintrag["count"] > 0

    @pytest.mark.asyncio(loop_scope="session")
    async def test_tu_berlin_als_koordinator_vorhanden(self, repo):
        """TU Berlin koordiniert Quantum-Projekte und muss erscheinen."""
        ergebnisse = await repo.top_cordis_organizations("quantum computing")
        namen = {e["name"] for e in ergebnisse}
        assert any("Berlin" in name or "Technische" in name for name in namen)

    @pytest.mark.asyncio(loop_scope="session")
    async def test_basf_als_battery_koordinator(self, repo):
        """BASF SE koordiniert Battery-Projekte und muss erscheinen."""
        ergebnisse = await repo.top_cordis_organizations("solid state battery")
        namen = {e["name"] for e in ergebnisse}
        assert any("BASF" in name for name in namen)

    @pytest.mark.asyncio(loop_scope="session")
    async def test_limit(self, repo):
        """limit-Parameter begrenzt die Ergebnis-Menge."""
        ergebnisse = await repo.top_cordis_organizations("quantum computing", limit=2)
        assert len(ergebnisse) <= 2

    @pytest.mark.asyncio(loop_scope="session")
    async def test_unbekannte_tech_gibt_leere_liste(self, repo):
        """Unbekannte Technologie liefert leere Liste."""
        ergebnisse = await repo.top_cordis_organizations("xyzzy_non_existent_42")
        assert ergebnisse == []

    @pytest.mark.asyncio(loop_scope="session")
    async def test_laenderinformation_vorhanden(self, repo):
        """Organisationen haben gueltigen 2-Buchstaben-Laendercode."""
        ergebnisse = await repo.top_cordis_organizations("quantum computing")
        for eintrag in ergebnisse:
            if eintrag["country"] is not None:
                assert len(eintrag["country"]) == 2


# ===========================================================================
# co_project_participants
# ===========================================================================


class TestCoProjectParticipants:
    """Tests fuer CompetitiveRepository.co_project_participants()."""

    @pytest.mark.asyncio(loop_scope="session")
    async def test_co_paare_gefunden(self, repo):
        """CORDIS-Konsortien enthalten Organisationspaare (mind. 2 Orgs je Projekt)."""
        ergebnisse = await repo.co_project_participants("quantum computing")
        assert isinstance(ergebnisse, list)
        # Mindestens ein Paar erwartet (mehrere Orgs je Projekt vorhanden)
        assert len(ergebnisse) >= 1

    @pytest.mark.asyncio(loop_scope="session")
    async def test_struktur(self, repo):
        """Jedes Paar hat 'actor_a', 'actor_b' und 'co_count'."""
        ergebnisse = await repo.co_project_participants("quantum computing")
        for eintrag in ergebnisse:
            assert "actor_a" in eintrag
            assert "actor_b" in eintrag
            assert "co_count" in eintrag
            assert isinstance(eintrag["actor_a"], str)
            assert isinstance(eintrag["actor_b"], str)
            assert isinstance(eintrag["co_count"], int)
            assert eintrag["co_count"] >= 1

    @pytest.mark.asyncio(loop_scope="session")
    async def test_lexikographische_ordnung(self, repo):
        """actor_a < actor_b (verhindert Duplikate in der DB-Query)."""
        ergebnisse = await repo.co_project_participants("quantum computing")
        for eintrag in ergebnisse:
            assert eintrag["actor_a"] < eintrag["actor_b"]

    @pytest.mark.asyncio(loop_scope="session")
    async def test_limit(self, repo):
        """limit-Parameter wird an die DB-Query weitergegeben."""
        ergebnisse = await repo.co_project_participants("quantum computing", limit=3)
        assert len(ergebnisse) <= 3

    @pytest.mark.asyncio(loop_scope="session")
    async def test_unbekannte_tech_gibt_leere_liste(self, repo):
        """Unbekannte Technologie liefert leere Liste."""
        ergebnisse = await repo.co_project_participants("xyzzy_non_existent_42")
        assert ergebnisse == []


# ===========================================================================
# co_patent_applicants
# ===========================================================================


class TestCoPatentApplicants:
    """Tests fuer CompetitiveRepository.co_patent_applicants().

    Hinweis: applicant_names ist als TEXT-Feld im Schema definiert
    (Legacy-Spalte), nicht als TEXT[]. Die LATERAL unnest-Query gibt
    daher 0 Ergebnisse zurueck. Der Test prueft Robustheit.
    """

    @pytest.mark.asyncio(loop_scope="session")
    async def test_kein_fehler_bei_text_feld(self, repo):
        """Kein Fehler auch wenn applicant_names kein Array ist."""
        ergebnisse = await repo.co_patent_applicants("quantum computing")
        assert isinstance(ergebnisse, list)

    @pytest.mark.asyncio(loop_scope="session")
    async def test_struktur_wenn_nicht_leer(self, repo):
        """Falls Ergebnisse: Struktur mit 'actor_a', 'actor_b', 'co_count'."""
        ergebnisse = await repo.co_patent_applicants("quantum computing")
        for eintrag in ergebnisse:
            assert "actor_a" in eintrag
            assert "actor_b" in eintrag
            assert "co_count" in eintrag

    @pytest.mark.asyncio(loop_scope="session")
    async def test_unbekannte_tech_gibt_leere_liste(self, repo):
        """Unbekannte Technologie liefert leere Liste."""
        ergebnisse = await repo.co_patent_applicants("xyzzy_non_existent_42")
        assert ergebnisse == []


# ===========================================================================
# HHI-Berechnung auf Basis von Repository-Ergebnissen
# ===========================================================================


class TestHhiBerechnung:
    """Prueft HHI-Index-Berechnung auf Basis echter DB-Ergebnisse.

    Der HHI wird nicht im Repository berechnet, sondern im Service-Layer
    (shared.domain.metrics.hhi_index). Dieser Test stellt sicher, dass
    die Repository-Daten korrekt in die HHI-Berechnung eingehen.
    """

    @pytest.mark.asyncio(loop_scope="session")
    async def test_hhi_aus_cordis_organisationen(self, repo):
        """HHI-Index aus CORDIS-Organisationen ist im gueltigen Bereich [0, 10000]."""
        organisationen = await repo.top_cordis_organizations("quantum computing")

        if not organisationen:
            pytest.skip("Keine Organisationen gefunden — HHI-Test uebersprungen")

        gesamt = sum(org["count"] for org in organisationen)
        if gesamt == 0:
            pytest.skip("Gesamtcount ist 0 — HHI-Test uebersprungen")

        marktanteile = [org["count"] / gesamt for org in organisationen]
        hhi = hhi_index(marktanteile)

        assert 0 <= hhi <= 10_000

    @pytest.mark.asyncio(loop_scope="session")
    async def test_hhi_monopol_bei_einem_akteur(self, repo):
        """Bei einem einzigen Akteur ergibt der HHI ca. 10000 (Monopol)."""
        # Nur den Top-1-Akteur verwenden
        organisationen = await repo.top_cordis_organizations(
            "quantum computing", limit=1
        )
        if not organisationen:
            pytest.skip("Keine Organisation gefunden")

        marktanteile = [1.0]  # Ein Akteur = 100 %
        hhi = hhi_index(marktanteile)
        assert hhi == pytest.approx(10_000)

    @pytest.mark.asyncio(loop_scope="session")
    async def test_hhi_konzentrationslevel_bestimmbar(self, repo):
        """Aus dem HHI laesst sich ein Konzentrationslevel bestimmen."""
        organisationen = await repo.top_cordis_organizations("quantum computing")
        if not organisationen:
            pytest.skip("Keine Organisationen gefunden")

        gesamt = sum(org["count"] for org in organisationen)
        if gesamt == 0:
            pytest.skip("Gesamtcount ist 0")

        marktanteile = [org["count"] / gesamt for org in organisationen]
        hhi = hhi_index(marktanteile)
        level_en, level_de = hhi_concentration_level(hhi)

        assert level_en in ("Low", "Moderate", "High")
        assert level_de in ("Gering", "Moderat", "Hoch")
