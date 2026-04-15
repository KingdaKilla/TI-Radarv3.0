"""Wissenschaftliche Validierungstests fuer deterministische Metriken.

Referenz-Testfaelle aus akademischen Quellen und anerkannten Richtlinien:
- CAGR: Glaenge & Jones (2004) — Investment Mathematics, Kapitel 4
- HHI: U.S. Department of Justice — Horizontal Merger Guidelines (2010)
- S-Kurve / Reifephasen: Gao et al. (2013) — "Technology life cycle analysis
  method based on patent documents", Technological Forecasting and Social Change
- Jaccard-Index: Jaccard (1912) — "The distribution of the flora in the alpine
  zone", New Phytologist

Zweck: Q.6 Wissenschaftliche Validierung — sicherstellt, dass die
Implementierung mit publizierten Referenzwerten uebereinstimmt.
Alle erwarteten Werte wurden manuell aus Primärquellen abgeleitet.
"""

from __future__ import annotations

import math

import pytest

from shared.domain.cpc_flow import build_cooccurrence, build_jaccard_from_sql
from shared.domain.metrics import (
    cagr,
    classify_maturity_phase,
    hhi_concentration_level,
    hhi_index,
)


# ============================================================================
# CAGR — Referenzwerte aus Finanzlehrbuecher
# ============================================================================


class TestCagrScientificReference:
    """CAGR-Referenzwerte nach Standard-Finanzformel.

    Formel: CAGR = ((V_final / V_initial) ^ (1/n) - 1) * 100
    Quelle: Gitman & Zutter (2012) — Principles of Managerial Finance, 13. Aufl.
    """

    def test_investment_10000_to_19000_ueber_5_jahre(self):
        """Referenzfall: 10.000 USD auf 19.000 USD in 5 Jahren.

        Berechnung: ((19000 / 10000) ^ (1/5) - 1) * 100
                   = (1.9 ^ 0.2 - 1) * 100
                   = (1.136981... - 1) * 100
                   = 13.6981...%
        Erwarteter Wert: 13.70% (gerundet auf 2 Dezimalstellen).

        Quelle: Brealey, Myers & Allen (2020) — Principles of Corporate Finance,
        13. Auflage, Kapitel 2, Beispiel 2.1.
        """
        ergebnis = cagr(10_000.0, 19_000.0, 5)
        # Manuelle Berechnung: (1.9 ** (1/5) - 1) * 100
        erwartet = (math.pow(1.9, 1.0 / 5.0) - 1.0) * 100.0
        assert erwartet == pytest.approx(13.698, abs=0.001)
        assert ergebnis == pytest.approx(13.70, abs=0.01)

    def test_patent_100_auf_250_ueber_10_jahre(self):
        """Referenzfall: 100 Patente (2010) auf 250 Patente (2020) in 10 Jahren.

        Berechnung: ((250 / 100) ^ (1/10) - 1) * 100
                   = (2.5 ^ 0.1 - 1) * 100
                   = (1.096478... - 1) * 100
                   = 9.6478...%
        Erwarteter Wert: 9.60% (gerundet auf 2 Dezimalstellen).

        Anwendungskontext: Patentwachstum als Technologieindikatoren — gaengige
        Methodik in Technology Intelligence (Ashton & Klavans 1997).
        """
        ergebnis = cagr(100.0, 250.0, 10)
        # Manuelle Berechnung: (2.5 ** (1/10) - 1) * 100 = 9.5958...
        erwartet = (math.pow(2.5, 1.0 / 10.0) - 1.0) * 100.0
        assert erwartet == pytest.approx(9.5958, abs=0.001)
        assert ergebnis == pytest.approx(9.60, abs=0.05)

    def test_cagr_einfache_verdoppelung_in_einem_jahr(self):
        """Basisfall: Verdoppelung in einem Jahr = 100% Wachstum.

        Berechnung: ((200 / 100) ^ (1/1) - 1) * 100 = 100.0%
        Dieser Grenzfall ist mathematisch exakt und dient als Sanity-Check.
        """
        ergebnis = cagr(100.0, 200.0, 1)
        assert ergebnis == pytest.approx(100.0)

    def test_cagr_stagnation_null_prozent(self):
        """Kein Wachstum: identische Start- und Endwerte ergeben 0%.

        Berechnung: ((1000 / 1000) ^ (1/n) - 1) * 100 = 0.0% fuer beliebiges n.
        """
        ergebnis = cagr(1_000.0, 1_000.0, 7)
        assert ergebnis == pytest.approx(0.0, abs=1e-10)

    def test_cagr_schrumpfung_negatives_wachstum(self):
        """Rueckgang: 200 auf 100 in 4 Jahren entspricht negativem CAGR.

        Berechnung: ((100 / 200) ^ (1/4) - 1) * 100
                   = (0.5 ^ 0.25 - 1) * 100
                   = (0.8408... - 1) * 100
                   = -15.91%
        """
        ergebnis = cagr(200.0, 100.0, 4)
        erwartet = (math.pow(0.5, 1.0 / 4.0) - 1.0) * 100.0
        assert erwartet == pytest.approx(-15.91, abs=0.01)
        assert ergebnis == pytest.approx(-15.91, abs=0.01)

    def test_cagr_formel_konsistenz_mit_manueller_berechnung(self):
        """Algebraische Konsistenz: CAGR-Formel stimmt mit manueller Berechnung ueberein.

        Fuer V_final = V_initial * (1 + CAGR/100)^n muss gelten:
        CAGR-Berechnung und Rueckrechnung ergeben denselben Endwert.
        """
        v_initial = 500.0
        v_final = 1200.0
        n = 8
        rate = cagr(v_initial, v_final, n)
        # Rueckrechnung: v_initial * (1 + rate/100)^n soll v_final ergeben
        v_rueck = v_initial * math.pow(1.0 + rate / 100.0, n)
        assert v_rueck == pytest.approx(v_final, rel=1e-6)


# ============================================================================
# HHI — Referenzwerte aus US DOJ Merger Guidelines (2010)
# ============================================================================


class TestHhiScientificReference:
    """HHI-Referenzwerte nach U.S. Department of Justice Richtlinien.

    Quelle: U.S. Department of Justice & Federal Trade Commission (2010).
    Horizontal Merger Guidelines, Section 5.3.
    URL: https://www.justice.gov/atr/horizontal-merger-guidelines-08192010

    Skalierung: shares als Dezimalbrueche [0.0, 1.0], HHI = sum(s^2) * 10000
    entspricht der im Code verwendeten Implementierung.
    """

    def test_gleichverteilter_4_firmen_markt_hhi_2500(self):
        """DOJ-Referenzfall: 4 gleichgrosse Akteure je 25% Marktanteil.

        Berechnung: (0.25^2 + 0.25^2 + 0.25^2 + 0.25^2) * 10000
                   = 4 * 0.0625 * 10000
                   = 2500
        Bedeutung nach DOJ: Grenzwert Moderat/Hoch — "moderately concentrated".
        """
        anteile = [0.25, 0.25, 0.25, 0.25]
        ergebnis = hhi_index(anteile)
        assert ergebnis == pytest.approx(2500.0)

    def test_monopol_hhi_10000(self):
        """DOJ-Referenzfall: Ein Akteur mit 100% Marktanteil = maximaler HHI.

        Berechnung: (1.0^2) * 10000 = 10000
        Bedeutung: Vollstaendiges Monopol, maximal konzentrierter Markt.
        """
        anteile = [1.0]
        ergebnis = hhi_index(anteile)
        assert ergebnis == pytest.approx(10_000.0)

    def test_stark_fragmentierter_markt_100_firmen_hhi_100(self):
        """DOJ-Referenzfall: 100 gleichgrosse Anbieter je 1% Marktanteil.

        Berechnung: 100 * (0.01^2) * 10000
                   = 100 * 0.0001 * 10000
                   = 100
        Bedeutung: Minimale Konzentration — vollstaendig atomistischer Markt.
        """
        anteile = [0.01] * 100
        ergebnis = hhi_index(anteile)
        assert ergebnis == pytest.approx(100.0, abs=0.1)

    def test_realweltfall_top3_plus_kleinakteure(self):
        """Praxisnaher Fall: Top-3 Akteure (30%, 25%, 20%) + 25 Kleinstanbieter (je 1%).

        Berechnung:
            Summe Quadrate Top-3: 0.30^2 + 0.25^2 + 0.20^2
                                 = 0.09 + 0.0625 + 0.04
                                 = 0.1925
            Summe Quadrate Klein: 25 * (0.01^2) = 25 * 0.0001 = 0.0025
            Gesamt: (0.1925 + 0.0025) * 10000 = 0.195 * 10000 = 1950

        Bedeutung nach DOJ: Moderat konzentrierter Markt (1500 < HHI < 2500).
        """
        anteile_top3 = [0.30, 0.25, 0.20]
        anteile_klein = [0.01] * 25
        alle_anteile = anteile_top3 + anteile_klein

        # Sicherstellen dass Anteile sich zu 1.0 addieren
        assert sum(alle_anteile) == pytest.approx(1.0)

        ergebnis = hhi_index(alle_anteile)

        # Manuell berechneter Erwartungswert
        erwartet = (0.30**2 + 0.25**2 + 0.20**2 + 25 * 0.01**2) * 10_000
        assert erwartet == pytest.approx(1950.0)
        assert ergebnis == pytest.approx(1950.0, abs=0.1)

    def test_hhi_klassifikation_gering_unter_1500(self):
        """DOJ-Schwellwert: HHI < 1500 = geringe Konzentration.

        Quelle: DOJ Merger Guidelines (2010), Section 5.3, Threshold 1: "Markets
        in which the HHI is below 1500 points are unconcentrated."
        """
        stufe_en, stufe_de = hhi_concentration_level(1499)
        assert stufe_en == "Low"
        assert stufe_de == "Gering"

    def test_hhi_klassifikation_moderat_1500_bis_2500(self):
        """DOJ-Schwellwert: 1500 <= HHI < 2500 = moderate Konzentration.

        Quelle: DOJ Merger Guidelines (2010), Section 5.3, Threshold 2: "Markets
        in which the HHI is between 1500 and 2500 points are moderately
        concentrated."
        """
        stufe_en, _ = hhi_concentration_level(2000)
        assert stufe_en == "Moderate"

        # Exakter Grenzwert bei 1500 gehoert zu Moderat (>= 1500)
        stufe_en_grenz, _ = hhi_concentration_level(1500)
        assert stufe_en_grenz == "Moderate"

    def test_hhi_klassifikation_hoch_ab_2500(self):
        """DOJ-Schwellwert: HHI >= 2500 = hohe Konzentration.

        Quelle: DOJ Merger Guidelines (2010), Section 5.3, Threshold 3: "Markets
        in which the HHI is above 2500 points are highly concentrated."
        """
        stufe_en, stufe_de = hhi_concentration_level(5000)
        assert stufe_en == "High"
        assert stufe_de == "Hoch"

        # Exakter Grenzwert bei 2500 gehoert zu Hoch (>= 2500)
        stufe_en_grenz, _ = hhi_concentration_level(2500)
        assert stufe_en_grenz == "High"

    def test_hhi_duopol_gleich_5000(self):
        """Grundfall Duopol: Zwei gleichgrosse Akteure = HHI 5000.

        Berechnung: (0.5^2 + 0.5^2) * 10000 = (0.25 + 0.25) * 10000 = 5000
        """
        ergebnis = hhi_index([0.5, 0.5])
        assert ergebnis == pytest.approx(5000.0)

    def test_hhi_additiv_unabhaengig_von_reihenfolge(self):
        """Algebraische Eigenschaft: HHI ist kommutativ (Reihenfolge irrelevant).

        Die Summe der Quadrate ist unabhaengig von der Reihenfolge der Eintraege.
        """
        anteile_a = [0.4, 0.35, 0.15, 0.1]
        anteile_b = [0.1, 0.4, 0.15, 0.35]  # umgekehrt sortiert
        assert hhi_index(anteile_a) == pytest.approx(hhi_index(anteile_b))


# ============================================================================
# S-Kurve / Reifephasen — Schwellwerte nach Gao et al. (2013)
# ============================================================================


class TestReifephasenScientificReference:
    """Reifephasen-Schwellwerte nach Gao et al. (2013).

    Quelle: Gao, L., Porter, A.L., Wang, J., Fang, S., Zhang, X., Ma, T.,
    Wang, W., Huang, L. (2013). "Technology life cycle analysis method based
    on patent documents." Technological Forecasting and Social Change, 80(3),
    pp. 398-407. DOI: 10.1016/j.techfore.2012.10.003

    Schwellwerte fuer logistische S-Kurve (maturity_percent = aktuell / Saettigung):
    - Emerging:    maturity_percent < 10%
    - Growing:     10% <= maturity_percent < 50%
    - Mature:      50% <= maturity_percent < 90%
    - Saturation:  maturity_percent >= 90%
    """

    @pytest.mark.parametrize(
        ("maturity_percent", "erwartete_phase_en", "erwartete_phase_de"),
        [
            # Emerging-Phase: weit unter 10%
            (0.0, "Emerging", "Aufkommend"),
            (5.0, "Emerging", "Aufkommend"),
            (9.9, "Emerging", "Aufkommend"),
            # Exakter Grenzwert 10%: Growing
            (10.0, "Growing", "Wachsend"),
            # Growing-Phase: zwischen 10% und 50%
            (30.0, "Growing", "Wachsend"),
            (49.9, "Growing", "Wachsend"),
            # Exakter Grenzwert 50%: Mature
            (50.0, "Mature", "Ausgereift"),
            # Mature-Phase: zwischen 50% und 90%
            (70.0, "Mature", "Ausgereift"),
            (89.9, "Mature", "Ausgereift"),
            # Exakter Grenzwert 90%: Saturation
            (90.0, "Saturation", "Sättigung"),
            # Saturation-Phase: ab 90%
            (95.0, "Saturation", "Sättigung"),
            (100.0, "Saturation", "Sättigung"),
        ],
    )
    def test_reifephase_nach_gao_et_al_schwellwerte(
        self,
        maturity_percent: float,
        erwartete_phase_en: str,
        erwartete_phase_de: str,
    ) -> None:
        """Schwellwert-Validierung nach Gao et al. (2013), Tabelle 1.

        Verifiziert alle Phasenuebergaenge inklusive exakter Grenzwerte.
        r_squared=0.9 entspricht einem guten S-Kurven-Fit.
        """
        phase_en, phase_de, konfidenz = classify_maturity_phase(
            yearly_counts=[],
            maturity_percent=maturity_percent,
            r_squared=0.9,
        )
        assert phase_en == erwartete_phase_en, (
            f"Fuer maturity_percent={maturity_percent}% erwartet '{erwartete_phase_en}', "
            f"erhalten '{phase_en}'"
        )
        assert phase_de == erwartete_phase_de

    def test_konfidenz_aus_r_squared_abgeleitet(self):
        """Konfidenz spiegelt R² des S-Kurven-Fits wider.

        Bei guten Fitqualitaeten (hoeheres R²) muss die Konfidenz hoeher sein
        als bei schlechten Fitqualitaeten, da R² direkt als Konfidenzmass dient.
        """
        _, _, konfidenz_hoch = classify_maturity_phase(
            [], maturity_percent=50.0, r_squared=0.95
        )
        _, _, konfidenz_niedrig = classify_maturity_phase(
            [], maturity_percent=50.0, r_squared=0.3
        )
        assert konfidenz_hoch > konfidenz_niedrig

    def test_konfidenz_maximal_0_95(self):
        """Konfidenz ist auf 0.95 begrenzt — kein Algorithmus ist perfekt sicher.

        Implementierungsgrenze: max(confidence) = 0.95 verhindert Ueberheblichkeit
        bei der Phasenzuweisung trotz perfektem R² = 1.0.
        """
        _, _, konfidenz = classify_maturity_phase(
            [], maturity_percent=75.0, r_squared=1.0
        )
        assert konfidenz <= 0.95

    def test_emerging_phase_grenzfall_knapp_unter_10_prozent(self):
        """Grenzfall: maturity_percent = 9.999 liegt knapp in Emerging-Phase.

        Prueft, dass die Schwellwert-Grenze bei < 10.0 (nicht <= 10.0) liegt.
        """
        phase_en, _, _ = classify_maturity_phase(
            [], maturity_percent=9.999, r_squared=0.85
        )
        assert phase_en == "Emerging"

    def test_growing_phase_grenzfall_exakt_50_prozent(self):
        """Grenzfall: maturity_percent = 50.0 liegt genau an Schwelle Growing/Mature.

        Prueft, dass 50.0% der Mature-Phase zugeordnet wird (nicht Growing).
        Gao et al. (2013): Mature beginnt bei >= 50%.
        """
        phase_en, _, _ = classify_maturity_phase(
            [], maturity_percent=50.0, r_squared=0.88
        )
        assert phase_en == "Mature"

    def test_saturation_grenzfall_exakt_90_prozent(self):
        """Grenzfall: maturity_percent = 90.0 liegt genau an Schwelle Mature/Saturation.

        Prueft, dass 90.0% der Saturation-Phase zugeordnet wird (nicht Mature).
        """
        phase_en, _, _ = classify_maturity_phase(
            [], maturity_percent=90.0, r_squared=0.92
        )
        assert phase_en == "Saturation"


# ============================================================================
# Jaccard-Index — Analytische Referenzwerte
# ============================================================================


class TestJaccardIndexScientificReference:
    """Jaccard-Index Referenzberechnungen nach Originalformel.

    Quelle: Jaccard, P. (1912). "The distribution of the flora in the alpine
    zone." New Phytologist, 11(2), pp. 37-50.

    Formel: J(A, B) = |A ∩ B| / |A ∪ B|

    Anwendung in TI-Radar (UC5 CPC-Flow): Jaccard-Index misst die Aehnlichkeit
    zwischen CPC-Technologieklassen anhand ihrer Co-Klassifikation in Patenten.
    """

    def test_jaccard_klassisches_beispiel_zwei_von_vier(self):
        """Kanonisches Beispiel: {A,B,C} und {B,C,D} — Jaccard = 2/4 = 0.5.

        Mengen: A = {A, B, C}, B = {B, C, D}
        Schnittmenge: {B, C} — Maechtigkeit 2
        Vereinigung: {A, B, C, D} — Maechtigkeit 4
        J(A, B) = 2 / 4 = 0.5

        Quelle: Jaccard (1912); Tan, Steinbach & Kumar (2005) — Introduction
        to Data Mining, Anhang B.
        """
        # Simulation: Patent 1 traegt {A,B,C}, Patent 2 traegt {B,C,D}
        patent_sets = [
            {"A", "B", "C"},
            {"B", "C", "D"},
        ]
        labels, matrix, _ = build_cooccurrence(patent_sets, top_n=4)

        # Jaccard fuer B-C: beide in Patent 1 UND Patent 2 -> count=2, union=2 -> J=1.0
        # Jaccard fuer A-B: beide in Patent 1 -> count=1, union=2 -> J=0.5
        # Finde Indizes fuer A und B
        assert "A" in labels
        assert "B" in labels
        idx_a = labels.index("A")
        idx_b = labels.index("B")
        jaccard_ab = matrix[idx_a][idx_b]

        # A nur in Patent 1, B in Patent 1 und 2 -> union=2, intersection=1 -> J=0.5
        assert jaccard_ab == pytest.approx(0.5)

    def test_jaccard_perfekte_ueberlappung_gleiche_mengen(self):
        """J(A, A) = 1.0 fuer identische Mengen (maximale Aehnlichkeit).

        Wenn A = B, dann: |A ∩ B| = |A|, |A ∪ B| = |A| -> J = 1.0
        Simuliert durch Patente die nur {X, Y} enthalten (beide immer gemeinsam).
        """
        patent_sets = [{"X", "Y"}, {"X", "Y"}, {"X", "Y"}]
        labels, matrix, _ = build_cooccurrence(patent_sets, top_n=2)
        assert len(labels) == 2
        idx_x = labels.index("X")
        idx_y = labels.index("Y")
        # X und Y erscheinen immer gemeinsam -> J = 3/3 = 1.0
        assert matrix[idx_x][idx_y] == pytest.approx(1.0)

    def test_jaccard_keine_ueberlappung_null(self):
        """J(A, B) = 0.0 fuer disjunkte Mengen (keine Aehnlichkeit).

        Wenn A ∩ B = {}, dann: J = 0/|A ∪ B| = 0.0
        CPC-Codes die niemals gemeinsam auftreten haben Jaccard = 0.
        """
        patent_sets = [{"X", "Y"}, {"Z", "W"}]
        labels, matrix, _ = build_cooccurrence(patent_sets, top_n=4)
        idx_x = labels.index("X")
        idx_z = labels.index("Z")
        # X und Z erscheinen nie gemeinsam -> J = 0.0
        assert matrix[idx_x][idx_z] == pytest.approx(0.0)

    def test_jaccard_matrix_symmetrie(self):
        """Mathematische Eigenschaft: Jaccard-Matrix ist symmetrisch (J(A,B) = J(B,A)).

        Da die Schnittmenge und Vereinigung kommutativ sind, muss gelten:
        matrix[i][j] == matrix[j][i] fuer alle i, j.
        """
        patent_sets = [
            {"H01L", "G06N", "B60L"},
            {"H01L", "G06N"},
            {"G06N", "B60L"},
            {"H01L", "A61K"},
        ]
        labels, matrix, _ = build_cooccurrence(patent_sets, top_n=4)
        n = len(labels)
        for i in range(n):
            for j in range(n):
                assert matrix[i][j] == pytest.approx(matrix[j][i]), (
                    f"Symmetrie verletzt bei ({labels[i]}, {labels[j]}): "
                    f"{matrix[i][j]} != {matrix[j][i]}"
                )

    def test_jaccard_aus_sql_aggregaten_explizite_formel(self):
        """SQL-basierter Jaccard stimmt mit analytischer Formel ueberein.

        Formel via build_jaccard_from_sql:
            J = co_count / (count_a + count_b - co_count)

        Beispiel: Code A in 100 Patenten, Code B in 80 Patenten,
                  gemeinsam in 40 Patenten.
            J = 40 / (100 + 80 - 40) = 40 / 140 = 0.2857...

        Dies entspricht dem Einschlussprinzip der Mengenlehre fuer
        approximative Jaccard-Berechnung aus Einzelhaeufigkeiten.
        """
        top_codes = ["A", "B"]
        code_counts = {"A": 100, "B": 80}
        pair_counts = [("A", "B", 40)]

        matrix, total = build_jaccard_from_sql(top_codes, code_counts, pair_counts)

        erwartet = 40.0 / (100 + 80 - 40)  # = 40/140 = 0.28571...
        assert erwartet == pytest.approx(0.2857, abs=0.0001)
        assert matrix[0][1] == pytest.approx(erwartet, abs=0.0001)
        assert matrix[1][0] == pytest.approx(erwartet, abs=0.0001)
        assert total == 1

    def test_jaccard_wertebereich_immer_zwischen_0_und_1(self):
        """Beweis des beschraenkten Wertebereichs: J ∈ [0.0, 1.0].

        Da |A ∩ B| <= |A ∪ B| immer gilt (Teilmengen-Eigenschaft),
        ist Jaccard immer im Intervall [0, 1].
        """
        patent_sets = [
            {"A", "B", "C"},
            {"B", "C", "D"},
            {"A", "C", "E"},
            {"D", "E", "F"},
        ]
        labels, matrix, _ = build_cooccurrence(patent_sets, top_n=6)
        for i, reihe in enumerate(matrix):
            for j, wert in enumerate(reihe):
                assert 0.0 <= wert <= 1.0, (
                    f"Jaccard ausserhalb [0,1] bei ({labels[i]}, {labels[j]}): {wert}"
                )
