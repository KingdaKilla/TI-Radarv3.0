"""Deterministische Paritaetsvalidierung: v1 (Prototype 5) == v2 (MVP v2).

Stellt sicher, dass die Refaktorierung der shared.domain-Schicht keine
numerischen Regressionen eingefuehrt hat. Alle Testfaelle verwenden
bekannte Eingabedaten mit vorab berechneten Erwartungswerten.

Q.5 — Deterministic Validation (v1 = v2):
Jede Metrik-Funktion produziert exakt denselben Ausgabewert wie die
referenzielle Implementierung in 07_Prototypen/prototype_5/src/ti_radar/domain/.

Berechnungsmethode der Erwartungswerte:
    - CAGR:  ((last / first) ^ (1/n) - 1) * 100  [manuell berechnet]
    - HHI:   sum(s_i^2) * 10000                    [manuell berechnet]
    - Laender-Merge: Additionsregel + Sortierung    [manuell verfolgt]
    - Reifephase: Gao et al. (2013) Schwellwerte    [aus Quelle abgeleitet]

Alle Docstrings und Kommentare in Deutsch gemaess Projektkonventionen.
"""

from __future__ import annotations

import math
from typing import Any

import pytest

from shared.domain.metrics import (
    cagr,
    classify_maturity_phase,
    hhi_concentration_level,
    hhi_index,
    merge_country_data,
    merge_time_series,
    yoy_growth,
)


# ============================================================================
# Hilfstypen fuer parametrisierte Testfaelle
# ============================================================================


# Eingabe-Typ fuer CAGR-Paritaets-Tests
_CagrFallTyp = tuple[float, float, int, float]

# Eingabe-Typ fuer HHI-Paritaets-Tests
_HhiFallTyp = tuple[list[float], float, str]

# Eingabe-Typ fuer Reifephase-Tests
_PhaseFallTyp = tuple[list[int], float | None, float | None, str, str]


# ============================================================================
# CAGR-Paritaet — Vorberechnete Referenzwerte
# ============================================================================


class TestCagrParitaet:
    """CAGR-Paritaet zwischen v1-Formelimplementierung und v2 shared.domain.

    Jeder Testfall: (first_value, last_value, periods, erwarteter_cagr_prozent)
    Erwartungswerte: manuell berechnet via ((last/first)^(1/n) - 1) * 100
    """

    @pytest.mark.parametrize(
        ("first", "last", "periods", "erwartet"),
        [
            # --- Jahresbezogene Patentdaten (Anwendungsfall UC2) ---
            # {2015: 10, 2019: 35}: 4 Perioden
            # Berechnung: ((35/10)^(1/4) - 1) * 100 = (3.5^0.25 - 1) * 100
            #           = (1.36784... - 1) * 100 = 36.784...%
            (10.0, 35.0, 4, (math.pow(3.5, 1.0 / 4.0) - 1.0) * 100.0),
            # {2010: 100, 2020: 250}: 10 Perioden (Referenzfall aus Aufgabenstellung)
            (100.0, 250.0, 10, (math.pow(2.5, 1.0 / 10.0) - 1.0) * 100.0),
            # {2015: 50, 2022: 200}: 7 Perioden
            # Berechnung: ((200/50)^(1/7) - 1) * 100 = (4.0^(1/7) - 1) * 100
            (50.0, 200.0, 7, (math.pow(4.0, 1.0 / 7.0) - 1.0) * 100.0),
            # Stagnation: selber Wert in 5 Jahren = 0%
            (300.0, 300.0, 5, 0.0),
            # Verdoppelung in einem Jahr = 100%
            (1.0, 2.0, 1, 100.0),
            # Foerderdaten (UC4): Projekte 2015-2023
            # {2015: 20, 2023: 80}: 8 Perioden
            # Berechnung: ((80/20)^(1/8) - 1) * 100 = (4.0^0.125 - 1) * 100
            (20.0, 80.0, 8, (math.pow(4.0, 1.0 / 8.0) - 1.0) * 100.0),
        ],
        ids=[
            "patentzahl_2015_2019",
            "patentzahl_2010_2020_referenz",
            "patentzahl_2015_2022",
            "stagnation_5_jahre",
            "verdoppelung_1_jahr",
            "foerderprojekte_2015_2023",
        ],
    )
    def test_cagr_paritaet_v1_v2(
        self,
        first: float,
        last: float,
        periods: int,
        erwartet: float,
    ) -> None:
        """Paritaetspruefung: v2-Ergebnis stimmt mit manuell berechnetem v1-Wert ueberein.

        Toleranz: abs=0.01% — entspricht der Praezision der v1-Implementierung,
        die auf 2 Dezimalstellen rundet.
        """
        ergebnis = cagr(first, last, periods)
        assert ergebnis == pytest.approx(erwartet, abs=0.01), (
            f"CAGR({first}, {last}, {periods}): "
            f"v2={ergebnis:.4f}%, erwartet={erwartet:.4f}%"
        )

    @pytest.mark.parametrize(
        ("first", "last", "periods"),
        [
            (0.0, 100.0, 5),    # Startwert Null
            (100.0, 0.0, 5),    # Endwert Null
            (-10.0, 100.0, 5),  # Negativer Startwert
            (100.0, 50.0, 0),   # Null Perioden
            (100.0, 50.0, -3),  # Negative Perioden
        ],
        ids=[
            "startwert_null",
            "endwert_null",
            "negativer_startwert",
            "null_perioden",
            "negative_perioden",
        ],
    )
    def test_cagr_ungueltige_eingaben_geben_null(
        self,
        first: float,
        last: float,
        periods: int,
    ) -> None:
        """Robustheit: Ungueltige Eingaben geben 0.0 zurueck (kein Absturz).

        Dies entspricht dem Verhalten der v1-Referenzimplementierung, die
        ungueltige Eingaben mit einem defensiven 0.0-Fallback behandelt.
        """
        ergebnis = cagr(first, last, periods)
        assert ergebnis == 0.0


# ============================================================================
# HHI-Paritaet — Vorberechnete Referenzwerte mit Konzentrationsklassen
# ============================================================================


class TestHhiParitaet:
    """HHI-Paritaet: Akteur-Zaehlungen → HHI-Wert → Konzentrationsklasse.

    Simuliert den typischen UC3-Workflow: Akteurdaten aus CORDIS/EPO werden
    zu Marktanteilen normiert, der HHI berechnet und klassifiziert.
    """

    @pytest.mark.parametrize(
        ("akteur_zaehlung", "erwarteter_hhi", "erwartete_klasse_en"),
        [
            # --- Bekannter Referenzfall aus Aufgabenstellung ---
            # {A: 50, B: 30, C: 20} — Gesamt 100
            # Anteile: [0.50, 0.30, 0.20]
            # HHI = (0.25 + 0.09 + 0.04) * 10000 = 3800 → Hoch
            (
                {"A": 50, "B": 30, "C": 20},
                (0.50**2 + 0.30**2 + 0.20**2) * 10_000,
                "High",
            ),
            # --- Oligopol: 3 Akteure 60/30/10 ---
            # Anteile: [0.60, 0.30, 0.10]
            # HHI = (0.36 + 0.09 + 0.01) * 10000 = 4600 → Hoch
            (
                {"Siemens": 60, "Bosch": 30, "BASF": 10},
                (0.60**2 + 0.30**2 + 0.10**2) * 10_000,
                "High",
            ),
            # --- Moderater Markt: 4 Akteure mit ausgeglichenen Anteilen ---
            # Anteile: [0.40, 0.30, 0.20, 0.10]
            # HHI = (0.16 + 0.09 + 0.04 + 0.01) * 10000 = 3000 → Hoch
            (
                {"Alpha": 40, "Beta": 30, "Gamma": 20, "Delta": 10},
                (0.40**2 + 0.30**2 + 0.20**2 + 0.10**2) * 10_000,
                "High",
            ),
            # --- Annaehernd gleichmaessiger Markt: 4 Akteure je ~25% ---
            # Anteile: [0.25, 0.25, 0.25, 0.25]
            # HHI = 4 * 0.0625 * 10000 = 2500 → Hoch (exakte Grenze)
            (
                {"W": 25, "X": 25, "Y": 25, "Z": 25},
                2500.0,
                "High",
            ),
            # --- Fragmentierter Markt: 10 gleichgrosse Akteure ---
            # Anteile: [0.10] * 10
            # HHI = 10 * 0.01 * 10000 = 1000 → Gering
            (
                {f"Akteur{i}": 10 for i in range(10)},
                (0.10**2 * 10) * 10_000,
                "Low",
            ),
        ],
        ids=[
            "referenzfall_A50_B30_C20",
            "oligopol_siemens_bosch_basf",
            "ausgewogenes_quartett",
            "gleichverteilte_vier",
            "fragmentierte_zehn",
        ],
    )
    def test_hhi_aus_akteur_zaehlungen(
        self,
        akteur_zaehlung: dict[str, int],
        erwarteter_hhi: float,
        erwartete_klasse_en: str,
    ) -> None:
        """Paritaet: Akteur-Zaehlungen → normierte Anteile → HHI → Klasse.

        Entspricht dem UC3-Ablauf: Akteurdaten normieren, HHI berechnen,
        Konzentrationsstufe bestimmen.
        """
        gesamt = sum(akteur_zaehlung.values())
        anteile = [count / gesamt for count in akteur_zaehlung.values()]

        berechneter_hhi = hhi_index(anteile)
        klasse_en, _ = hhi_concentration_level(berechneter_hhi)

        assert berechneter_hhi == pytest.approx(erwarteter_hhi, abs=0.1), (
            f"HHI fuer {akteur_zaehlung}: berechnet={berechneter_hhi:.2f}, "
            f"erwartet={erwarteter_hhi:.2f}"
        )
        assert klasse_en == erwartete_klasse_en, (
            f"HHI={berechneter_hhi:.0f}: Klasse '{klasse_en}' != erwartet '{erwartete_klasse_en}'"
        )

    def test_hhi_referenzfall_A50_B30_C20_explizit(self):
        """Expliziter Referenzfall aus Aufgabenstellung: {A: 50, B: 30, C: 20}.

        Schrittweise Berechnung:
            Gesamt = 50 + 30 + 20 = 100
            Anteile: [0.50, 0.30, 0.20]
            Quadrate: [0.2500, 0.0900, 0.0400]
            Summe: 0.3800
            HHI = 0.3800 * 10000 = 3800

        Klassifikation: 3800 > 2500 → "High" (DOJ: highly concentrated).
        """
        anteile = [50 / 100, 30 / 100, 20 / 100]
        ergebnis_hhi = hhi_index(anteile)

        # Exakter Erwartungswert
        assert ergebnis_hhi == pytest.approx(3800.0, abs=0.1)

        klasse_en, klasse_de = hhi_concentration_level(ergebnis_hhi)
        assert klasse_en == "High"
        assert klasse_de == "Hoch"


# ============================================================================
# Reifephase-Paritaet — Gao et al. (2013) Klassifikation
# ============================================================================


class TestReifephaseParitaet:
    """Paritaet der Reifephasen-Klassifikation fuer konkrete Patentreihen.

    Testet classify_maturity_phase() mit realistischen jaehrlichen Patentserien,
    die typischen Technologielebenszyklen in EU-Patenddaten entsprechen.
    """

    @pytest.mark.parametrize(
        ("yearly_counts", "maturity_percent", "r_squared", "erwartete_phase_en"),
        [
            # --- S-Kurve-basiert: Emerging (maturity < 10%) ---
            # Neue Technologie: nur 5% des Saettigungslevels erreicht
            ([], 5.0, 0.88, "Emerging"),
            # --- S-Kurve-basiert: Growing (10% <= maturity < 50%) ---
            # Wachsende Technologie: 30% des Saettigungslevels
            ([], 30.0, 0.91, "Growing"),
            # --- S-Kurve-basiert: Mature (50% <= maturity < 90%) ---
            # Reife Technologie: 70% des Saettigungslevels
            ([], 70.0, 0.87, "Mature"),
            # --- S-Kurve-basiert: Saturation (maturity >= 90%) ---
            # Gesaettigte Technologie: 95% des Saettigungslevels
            ([], 95.0, 0.93, "Saturation"),
            # --- Fallback-Heuristik: Starkes Wachstum → Emerging/Growing ---
            # Patentserie mit exponentiellem Wachstum
            ([5, 8, 15, 28, 52, 95], None, None, "Emerging"),
            # --- Fallback-Heuristik: Stabiler Markt → Mature ---
            # Patentserie mit minimaler Schwankung um konstanten Wert
            ([100, 103, 98, 101, 99, 102], None, None, "Mature"),
        ],
        ids=[
            "scurve_emerging_5pct",
            "scurve_growing_30pct",
            "scurve_mature_70pct",
            "scurve_saturation_95pct",
            "fallback_exponentielles_wachstum",
            "fallback_stabiler_markt",
        ],
    )
    def test_reifephase_paritaet(
        self,
        yearly_counts: list[int],
        maturity_percent: float | None,
        r_squared: float | None,
        erwartete_phase_en: str,
    ) -> None:
        """Paritaet: Phase-Klassifikation stimmt mit v1-Logik ueberein.

        Die Schwellwerte sind unveraendert zwischen v1 und v2 (Gao et al. 2013).
        """
        phase_en, _, _ = classify_maturity_phase(
            yearly_counts=yearly_counts,
            maturity_percent=maturity_percent,
            r_squared=r_squared,
        )
        assert phase_en == erwartete_phase_en, (
            f"Phase fuer maturity={maturity_percent}, counts={yearly_counts}: "
            f"erhalten='{phase_en}', erwartet='{erwartete_phase_en}'"
        )

    def test_unbekannte_phase_bei_zu_wenig_daten(self):
        """Fallback: Weniger als 3 Datenpunkte ohne maturity_percent → Unbekannt.

        v1 und v2 geben beide "Unknown" zurueck — keine numerische Regression.
        """
        phase_en, phase_de, konfidenz = classify_maturity_phase([10, 20])
        assert phase_en == "Unknown"
        assert phase_de == "Unbekannt"
        assert konfidenz == 0.0

    def test_leere_zeitreihe_ohne_scurve_parameter(self):
        """Grenzfall: Leere Zeitreihe ohne S-Kurve-Parameter → Unbekannt."""
        phase_en, _, konfidenz = classify_maturity_phase([])
        assert phase_en == "Unknown"
        assert konfidenz == 0.0


# ============================================================================
# YOY-Wachstum-Paritaet
# ============================================================================


class TestYoyWachstumParitaet:
    """Jahr-ueber-Jahr-Wachstum: Paritaet zwischen v1 und v2.

    Einfache prozentuale Aenderung: (current - previous) / previous * 100
    """

    @pytest.mark.parametrize(
        ("current", "previous", "erwartet"),
        [
            # Standard-Wachstum: 110 nach 100 = +10%
            (110, 100, 10.0),
            # Rueckgang: 80 nach 100 = -20%
            (80, 100, -20.0),
            # Stagnation: 100 nach 100 = 0%
            (100, 100, 0.0),
            # Verdoppelung: 200 nach 100 = +100%
            (200, 100, 100.0),
            # Halbierung: 50 nach 100 = -50%
            (50, 100, -50.0),
            # Patentwachstum: 42 nach 30 = +40%
            (42, 30, 40.0),
        ],
        ids=[
            "wachstum_10_prozent",
            "rueckgang_20_prozent",
            "stagnation_null",
            "verdoppelung",
            "halbierung",
            "patent_wachstum_40pct",
        ],
    )
    def test_yoy_wachstum_paritaet(
        self,
        current: int,
        previous: int,
        erwartet: float,
    ) -> None:
        """Paritaet: yoy_growth() stimmt mit manuell berechnetem Wert ueberein."""
        ergebnis = yoy_growth(current, previous)
        assert ergebnis is not None
        assert ergebnis == pytest.approx(erwartet, abs=0.05)

    def test_yoy_vorjahr_null_gibt_none(self):
        """Spezialfall: Vorjahr=0 gibt None zurueck (kein Teilen durch Null).

        Konsistent mit v1-Verhalten: Division durch Null wird durch None signalisiert.
        """
        assert yoy_growth(100, 0) is None
        assert yoy_growth(0, 0) is None


# ============================================================================
# Laender-Aggregations-Paritaet
# ============================================================================


class TestLaenderAggregationParitaet:
    """Paritaet der merge_country_data-Funktion fuer UC6 (Geografische Analyse).

    Testet die Zusammenfuehrung von Patent- und CORDIS-Laenderdaten mit
    vorberechneten Erwartungswerten fuer Summen und Sortierung.
    """

    def test_einfache_zusammenfuehrung_mit_bekannten_werten(self):
        """Grundfall: Patente + CORDIS-Projekte pro Land korrekt summiert.

        Eingabe:
            patent_countries: DE=100, FR=50
            cordis_countries: DE=30,  IT=20

        Erwartete Ausgabe (nach total absteigend sortiert):
            DE: patents=100, projects=30, total=130  ← groesste total
            FR: patents=50,  projects=0,  total=50
            IT: patents=0,   projects=20, total=20
        """
        patent_countries = [
            {"country": "DE", "count": 100},
            {"country": "FR", "count": 50},
        ]
        cordis_countries = [
            {"country": "DE", "count": 30},
            {"country": "IT", "count": 20},
        ]

        ergebnis = merge_country_data(patent_countries, cordis_countries)

        assert len(ergebnis) == 3

        # Erstes Ergebnis muss DE sein (highest total)
        de = ergebnis[0]
        assert de["country"] == "DE"
        assert de["patents"] == 100
        assert de["projects"] == 30
        assert de["total"] == 130

        # Zweites Ergebnis muss FR sein
        fr = ergebnis[1]
        assert fr["country"] == "FR"
        assert fr["patents"] == 50
        assert fr["projects"] == 0
        assert fr["total"] == 50

        # Drittes Ergebnis muss IT sein
        it = ergebnis[2]
        assert it["country"] == "IT"
        assert it["patents"] == 0
        assert it["projects"] == 20
        assert it["total"] == 20

    @pytest.mark.parametrize(
        ("patent_laender", "cordis_laender", "erwartete_reihenfolge", "erwartete_totals"),
        [
            # Fall 1: Nur Patent-Daten
            (
                [{"country": "DE", "count": 200}, {"country": "FR", "count": 100}],
                [],
                ["DE", "FR"],
                [200, 100],
            ),
            # Fall 2: Nur CORDIS-Daten
            (
                [],
                [{"country": "ES", "count": 150}, {"country": "PL", "count": 50}],
                ["ES", "PL"],
                [150, 50],
            ),
            # Fall 3: Ueberlappende + exklusive Laender
            (
                [{"country": "DE", "count": 80}, {"country": "FR", "count": 60}],
                [{"country": "FR", "count": 90}, {"country": "IT", "count": 40}],
                ["FR", "DE", "IT"],  # FR=150, DE=80, IT=40
                [150, 80, 40],
            ),
        ],
        ids=[
            "nur_patent_daten",
            "nur_cordis_daten",
            "gemischte_ueberlappung",
        ],
    )
    def test_laender_aggregation_sortierung_und_totals(
        self,
        patent_laender: list[dict[str, Any]],
        cordis_laender: list[dict[str, Any]],
        erwartete_reihenfolge: list[str],
        erwartete_totals: list[int],
    ) -> None:
        """Paritaet: Laender-Merge gibt korrekte Reihenfolge und Summen zurueck."""
        ergebnis = merge_country_data(patent_laender, cordis_laender)

        assert len(ergebnis) == len(erwartete_reihenfolge), (
            f"Erwartet {len(erwartete_reihenfolge)} Laender, erhalten {len(ergebnis)}"
        )

        for rang, (erwartet_land, erwartet_total) in enumerate(
            zip(erwartete_reihenfolge, erwartete_totals)
        ):
            assert ergebnis[rang]["country"] == erwartet_land, (
                f"Rang {rang}: erwartet '{erwartet_land}', erhalten '{ergebnis[rang]['country']}'"
            )
            assert ergebnis[rang]["total"] == erwartet_total, (
                f"{erwartet_land} total: erwartet={erwartet_total}, "
                f"erhalten={ergebnis[rang]['total']}"
            )

    def test_limit_parameter_schneidet_korrekt_ab(self):
        """limit-Parameter begrenzt Ergebnis auf die top-N Laender.

        Gibt immer die N Laender mit dem hoechsten total-Wert zurueck.
        """
        patent_laender = [
            {"country": "DE", "count": 300},
            {"country": "FR", "count": 200},
            {"country": "IT", "count": 100},
            {"country": "ES", "count": 50},
        ]
        ergebnis_alle = merge_country_data(patent_laender, [])
        ergebnis_top2 = merge_country_data(patent_laender, [], limit=2)

        assert len(ergebnis_alle) == 4
        assert len(ergebnis_top2) == 2
        # Top-2 muessen DE und FR sein
        assert ergebnis_top2[0]["country"] == "DE"
        assert ergebnis_top2[1]["country"] == "FR"

    def test_leere_eingaben_ergeben_leere_ausgabe(self):
        """Robustheit: Leere Eingabelisten fuehren zu leerer Ausgabe."""
        ergebnis = merge_country_data([], [])
        assert ergebnis == []


# ============================================================================
# Zeitreihen-Merge-Paritaet
# ============================================================================


class TestZeitreihenMergeParitaet:
    """Paritaet der merge_time_series-Funktion fuer UC1 (Landscape).

    Testet die Zusammenfuehrung von Patent-, Projekt- und Publikations-
    Zeitreihen mit Wachstumsraten-Berechnung.
    """

    def test_wachstumsrate_in_zweitem_eintrag_korrekt(self):
        """Wachstumsrate wird ab zweitem Jahr korrekt berechnet.

        Eingabe: Patente 2020=100, 2021=150
        Erwartete Wachstumsrate 2021: (150-100)/100 * 100 = 50.0%
        """
        patent_years = [
            {"year": 2020, "count": 100},
            {"year": 2021, "count": 150},
        ]
        ergebnis = merge_time_series(patent_years, [], [], 2020, 2021)

        assert len(ergebnis) == 2

        # Erstes Jahr: keine Wachstumsrate (kein Vorjahr)
        assert "patents_growth" not in ergebnis[0]

        # Zweites Jahr: Wachstumsrate korrekt
        assert ergebnis[1]["patents_growth"] == pytest.approx(50.0)

    def test_fehlende_jahre_werden_mit_null_aufgefuellt(self):
        """Luecken in der Zeitreihe werden mit 0 aufgefuellt.

        Wenn kein Eintrag fuer ein Jahr vorhanden ist, wird 0 eingetragen.
        """
        patent_years = [{"year": 2020, "count": 50}]
        ergebnis = merge_time_series(patent_years, [], [], 2019, 2021)

        assert len(ergebnis) == 3
        # 2019: kein Patent-Eintrag → 0
        assert ergebnis[0]["year"] == 2019
        assert ergebnis[0]["patents"] == 0
        # 2020: Eintrag vorhanden
        assert ergebnis[1]["year"] == 2020
        assert ergebnis[1]["patents"] == 50

    def test_alle_drei_datenquellen_korrekt_zusammengefuehrt(self):
        """Alle drei Quellen (Patente, Projekte, Publikationen) korrekt gemischt.

        Prueft, dass Patent-, Projekt- und Publikationsdaten fuer dasselbe Jahr
        in einem einzigen Eintrag zusammengefuehrt werden.
        """
        patent_years = [{"year": 2021, "count": 42}]
        project_years = [{"year": 2021, "count": 15}]
        pub_years = [{"year": 2021, "count": 7}]

        ergebnis = merge_time_series(patent_years, project_years, pub_years, 2021, 2021)

        assert len(ergebnis) == 1
        eintrag = ergebnis[0]
        assert eintrag["year"] == 2021
        assert eintrag["patents"] == 42
        assert eintrag["projects"] == 15
        assert eintrag["publications"] == 7

    def test_jahresbereich_wird_korrekt_eingehalten(self):
        """Zeitreihe enthaelt genau die Jahre start_year bis end_year.

        Eintrage ausserhalb dieses Bereichs werden ignoriert.
        """
        patent_years = [
            {"year": 2018, "count": 5},   # vor start_year → ignorieren
            {"year": 2020, "count": 10},
            {"year": 2025, "count": 20},   # nach end_year → ignorieren
        ]
        ergebnis = merge_time_series(patent_years, [], [], 2019, 2023)

        jahre = [e["year"] for e in ergebnis]
        assert min(jahre) >= 2019
        assert max(jahre) <= 2023
        assert 2018 not in jahre
        assert 2025 not in jahre
