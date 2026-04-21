"""Deterministische Metriken fuer Technology Intelligence.

Reine Funktionen ohne IO — testbar, auditierbar, reproduzierbar.
"""

from __future__ import annotations

import math
from typing import Any

# Schwellwert, unterhalb dessen ein S-Kurven-Fit als unzuverlaessig gilt
# (Bug MAJ-9). Bei R² < 0.5 wird die Konfidenz zwingend auf 0.0 gesetzt,
# damit nachgelagerte UI-Komponenten keine Scheinsicherheit (z.B. "R²=0 +
# Konfidenz 80 % + Phase: Emerging") mehr erzeugen koennen.
R2_RELIABILITY_THRESHOLD: float = 0.5

# Overfitting-Schwellen fuer 3-Parameter Sigmoid-Fits. R² > 0.98 bei weniger
# als 30 Datenpunkten ist ein klassisches Overfitting-Signal: der Fit hat
# mehr Freiheitsgrade als die Datenbasis erlaubt (Live-Fall Semiconductor
# Laser v3.4.0: R² = 0.9983 bei n = 9 vollstaendigen Jahren).
OVERFIT_R2_THRESHOLD: float = 0.98
OVERFIT_MIN_DATAPOINTS: int = 30


def is_potentially_overfit(r_squared: float | None, n_data_points: int) -> bool:
    """True wenn R² > OVERFIT_R2_THRESHOLD und n < OVERFIT_MIN_DATAPOINTS.

    Ergaenzt die R²-Kopplung (Bug MAJ-9): ``fit_reliability_flag`` fängt den
    Fall "Fit zu schlecht" (R² < 0.5); diese Funktion markiert den umgekehrten
    Fall "Fit verdaechtig gut bei zu wenig Daten".

    Defensiv: ``None``-R² (kein Fit zustande gekommen) ergibt ``False``, damit
    der Fallback-Pfad keine falsche Warnung setzt.

    Args:
        r_squared: R²-Wert des Fits (0..1), oder ``None``.
        n_data_points: Anzahl der Datenpunkte die in den Fit eingingen.

    Returns:
        ``True`` nur wenn R² > OVERFIT_R2_THRESHOLD UND n < OVERFIT_MIN_DATAPOINTS.
    """
    if r_squared is None:
        return False
    return r_squared > OVERFIT_R2_THRESHOLD and n_data_points < OVERFIT_MIN_DATAPOINTS


def cagr(first_value: float, last_value: float, periods: int) -> float:
    """
    Compound Annual Growth Rate.

    Formula: ((V_final / V_initial)^(1/n) - 1) * 100

    Returns percentage (e.g. 12.5 for 12.5% growth).
    Returns 0.0 if inputs are invalid.

    Limitationen:
    - Endpunktsensitivitaet: Nur Anfangs- und Endwert gehen ein; Schwankungen
      dazwischen werden ignoriert. Atypische Start-/Endjahre verzerren das Ergebnis.
    - Glaettungsannahme: CAGR unterstellt konstantes jaehrliches Wachstum und
      bildet keine Strukturbrueche ab (z.B. Programmwechsel FP7 -> H2020 -> Horizon).
    - Null-/Negativwerte: Foerderjahre ohne Daten (funding=0) werden uebersprungen;
      die Funktion gibt 0.0 zurueck, wenn Start- oder Endwert <= 0.
    - Kurze Zeitraeume: Bei wenigen Perioden (n < 3) kann der CAGR statistisch
      nicht belastbar sein.
    """
    if periods <= 0 or first_value <= 0 or last_value <= 0:
        return 0.0
    return (math.pow(last_value / first_value, 1.0 / periods) - 1.0) * 100.0


def hhi_index(shares: list[float]) -> float:
    """
    Herfindahl-Hirschman Index fuer Marktkonzentration.

    Formula: sum(share_i^2) * 10000
    Input: Liste von Marktanteilen (0.0 bis 1.0)
    Output: HHI-Wert (0 bis 10000)

    Interpretation:
    - < 1500: Geringe Konzentration
    - 1500-2500: Moderate Konzentration
    - > 2500: Hohe Konzentration
    """
    if not shares:
        return 0.0
    return sum(s * s for s in shares) * 10_000


def hhi_concentration_level(hhi: float) -> tuple[str, str]:
    """HHI-Wert in Konzentrationsstufe uebersetzen (EN, DE)."""
    if hhi < 1500:
        return "Low", "Gering"
    if hhi < 2500:
        return "Moderate", "Moderat"
    return "High", "Hoch"


def cr4(shares: list[float]) -> float:
    """Concentration Ratio der Top-4 Akteure.

    Summe der 4 groessten Marktanteile. Ergaenzt HHI um eine intuitivere Metrik.
    CR4 > 0.6 gilt als hoch konzentriert, < 0.4 als wettbewerbsintensiv.

    Args:
        shares: Liste der Marktanteile (0-1 Skala)
    Returns:
        CR4-Wert (0-1)
    """
    if not shares:
        return 0.0
    sorted_shares = sorted(shares, reverse=True)
    return sum(sorted_shares[:4])


def s_curve_confidence(
    r_squared: float,
    n_years: int,
    total_patents: int,
) -> float:
    """
    Gewichtete Konfidenz fuer S-Curve-basierte Phasenklassifikation.

    Beruecksichtigt:
    - R² (Guete des Fits): 60% Gewicht
    - Datenabdeckung (Jahre): 20% Gewicht (15+ Jahre = voll)
    - Stichprobengroesse (Patente): 20% Gewicht (200+ Patente = voll)

    R²-Kopplung (Bug MAJ-9): Wenn ``r_squared < R2_RELIABILITY_THRESHOLD`` (0.5),
    gibt die Funktion hart ``0.0`` zurueck. Ein unzuverlaessiger Fit darf nicht
    mit Datenabdeckung/Stichprobengroesse kompensiert werden, sonst entstehen
    Scheinsicherheiten (z.B. R²=0 + 80 % Konfidenz + Phase-Label).

    Args:
        r_squared: R²-Wert des Fits (0..1). ``None`` oder Werte < 0 werden wie 0 behandelt.
        n_years: Anzahl Jahre mit Datenpunkten.
        total_patents: Gesamt-Sample-Groesse (kumulativ am Ende der Reihe).

    Returns:
        Wert in [0.0, 0.95]. Exakt 0.0 wenn R² < R2_RELIABILITY_THRESHOLD;
        sonst min. 0.1 (Floor) bis max. 0.95 (Cap).
    """
    # Kopplung: R² unter Threshold oder fehlend → Konfidenz = 0 (keine Kompensation).
    r_sq = r_squared if r_squared is not None else 0.0
    if r_sq < R2_RELIABILITY_THRESHOLD:
        return 0.0

    data_factor = min(1.0, n_years / 15.0)
    sample_factor = min(1.0, total_patents / 200.0)
    raw = r_sq * 0.6 + data_factor * 0.2 + sample_factor * 0.2
    return round(min(0.95, max(0.1, raw)), 2)


def detect_decline(
    yearly_counts: list[int],
    saturation_pct: float = 90.0,
    consecutive_years: int = 2,
) -> bool:
    """Erkennt Decline-Phase anhand sinkender jaehrlicher Anmelderaten.

    S-Kurve ist monoton steigend (kumulativ) und kann Decline nicht erkennen.
    Diese Funktion prueft die 1. Ableitung (jaehrliche Zahl) auf konsekutive
    Rueckgaenge.

    Args:
        yearly_counts: Jaehrliche Patent-/Projektzahlen (nicht kumulativ)
        saturation_pct: Ab welchem Saettigungsgrad Decline moeglich ist (default 90%)
        consecutive_years: Mindestens N konsekutive negative Jahre (default 2)
    Returns:
        True wenn Decline erkannt
    """
    if len(yearly_counts) < consecutive_years + 1:
        return False
    # Pruefe ob die letzten consecutive_years+1 Werte fallend sind
    recent = yearly_counts[-(consecutive_years + 1):]
    consecutive_declines = 0
    for i in range(1, len(recent)):
        if recent[i] < recent[i - 1]:
            consecutive_declines += 1
        else:
            consecutive_declines = 0
    return consecutive_declines >= consecutive_years


def classify_maturity_phase(
    yearly_counts: list[int],
    maturity_percent: float | None = None,
    r_squared: float | None = None,
) -> tuple[str, str, float]:
    """
    Reifegrad-Phase klassifizieren.

    Wenn maturity_percent gegeben (aus S-Curve-Fit): Schwellwerte nach Gao et al. (2013).
    Sonst: Fallback auf Wachstumsmuster-Heuristik.

    Returns:
        (phase_en, phase_de, confidence)
    """
    # S-Curve-basierte Klassifikation (bevorzugt)
    if maturity_percent is not None:
        confidence = min(0.95, r_squared or 0.5)
        if maturity_percent < 10.0:
            return "Emerging", "Aufkommend", round(confidence, 2)
        if maturity_percent < 50.0:
            return "Growing", "Wachsend", round(confidence, 2)
        if maturity_percent < 90.0:
            return "Mature", "Ausgereift", round(confidence, 2)
        return "Saturation", "Sättigung", round(confidence, 2)

    # Fallback: Wachstumsmuster-Heuristik
    if not yearly_counts or len(yearly_counts) < 3:
        return "Unknown", "Unbekannt", 0.0

    n = len(yearly_counts)

    # Durchschnitte fuer erste und zweite Haelfte
    mid = n // 2
    first_half = yearly_counts[:mid] if mid > 0 else yearly_counts[:1]
    second_half = yearly_counts[mid:]

    avg_first = sum(first_half) / len(first_half) if first_half else 0
    avg_second = sum(second_half) / len(second_half) if second_half else 0

    # Letzte 3 Jahre Trend
    recent = yearly_counts[-3:]
    if len(recent) >= 2 and recent[0] > 0:
        recent_growth = (recent[-1] - recent[0]) / recent[0]
    else:
        recent_growth = 0.0

    # Gesamttrend
    if avg_first > 0:
        overall_growth = (avg_second - avg_first) / avg_first
    else:
        overall_growth = 1.0 if avg_second > 0 else 0.0

    # Varianz in zweiter Haelfte (Stabilitaet)
    if second_half and avg_second > 0:
        variance = sum((x - avg_second) ** 2 for x in second_half) / len(second_half)
        cv = math.sqrt(variance) / avg_second  # Coefficient of Variation
    else:
        cv = 1.0

    # Klassifikation
    total = sum(yearly_counts)
    if total == 0:
        return "Unknown", "Unbekannt", 0.0

    if overall_growth > 0.5 and recent_growth > 0.1:
        phase_en, phase_de = "Emerging", "Aufkommend"
        confidence = min(0.9, 0.5 + overall_growth * 0.3)
    elif overall_growth > 0.1 and recent_growth > -0.1:
        phase_en, phase_de = "Growing", "Wachsend"
        confidence = min(0.9, 0.5 + (1.0 - cv) * 0.3)
    elif abs(overall_growth) <= 0.2 and cv < 0.4:
        phase_en, phase_de = "Mature", "Ausgereift"
        confidence = min(0.9, 0.6 + (1.0 - cv) * 0.3)
    elif overall_growth < -0.1 or recent_growth < -0.2:
        phase_en, phase_de = "Declining", "Rückläufig"
        confidence = min(0.9, 0.5 + abs(overall_growth) * 0.3)
    else:
        phase_en, phase_de = "Growing", "Wachsend"
        confidence = 0.4

    return phase_en, phase_de, round(confidence, 2)


def yoy_growth(current: int, previous: int) -> float | None:
    """Prozentuale Veraenderung zum Vorjahr. None wenn Vorjahr=0."""
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 1)


# Backwards-compat Alias (UC1 nutzt den privaten Namen)
_yoy_growth = yoy_growth


def merge_time_series(
    patent_years: list,
    project_years: list,
    publication_years: list,
    start_year: int,
    end_year: int,
) -> list[dict[str, Any]]:
    """Patent-, Projekt- und Publikations-Zeitreihen mit Wachstumsraten."""

    def _to_map(items: list) -> dict[int, int]:
        if not items:
            return {}
        if hasattr(items[0], "year"):
            return {y.year: y.count for y in items}
        return {y["year"]: y["count"] for y in items}

    patent_map = _to_map(patent_years)
    project_map = _to_map(project_years)
    publication_map = _to_map(publication_years)

    all_years = set(range(start_year, end_year + 1))
    all_years |= set(patent_map.keys())
    all_years |= set(project_map.keys())
    all_years |= set(publication_map.keys())

    sorted_years = sorted(y for y in all_years if start_year <= y <= end_year)

    series: list[dict[str, Any]] = []
    for i, year in enumerate(sorted_years):
        pat = patent_map.get(year, 0)
        proj = project_map.get(year, 0)
        pub = publication_map.get(year, 0)

        entry: dict[str, Any] = {
            "year": year,
            "patents": pat,
            "projects": proj,
            "publications": pub,
        }

        if i > 0:
            prev_year = sorted_years[i - 1]
            entry["patents_growth"] = yoy_growth(
                pat, patent_map.get(prev_year, 0),
            )
            entry["projects_growth"] = yoy_growth(
                proj, project_map.get(prev_year, 0),
            )
            entry["publications_growth"] = yoy_growth(
                pub, publication_map.get(prev_year, 0),
            )

        series.append(entry)

    return series


# Backwards-compat Alias (UC1 nutzt den privaten Namen)
_merge_time_series = merge_time_series


def merge_country_data(
    patent_countries: list,
    cordis_countries: list,
    *,
    limit: int | None = None,
) -> list[dict[str, str | int]]:
    """
    Laender-Daten aus Patenten und CORDIS zusammenfuehren.

    Jeder Eintrag: {country, patents, projects, total}, sortiert nach total.
    Optional: Ergebnis auf `limit` Laender begrenzen.
    Akzeptiert sowohl dict- als auch Attribut-basierte Eintraege (duck typing).
    """

    # Bekannte Aliase auf ISO 3166-1 alpha-2 normalisieren
    country_aliases: dict[str, str] = {
        "UK": "GB",  # CORDIS nutzt UK, EPO nutzt GB
        "EL": "GR",  # CORDIS nutzt EL fuer Griechenland
    }

    def _get(item: Any, key: str) -> Any:
        return getattr(item, key) if hasattr(item, key) else item[key]

    def _normalize(code: str) -> str:
        code = code.strip().upper()
        return country_aliases.get(code, code)

    data: dict[str, dict[str, int]] = {}

    for entry in patent_countries:
        code = _normalize(str(_get(entry, "country")))
        if code not in data:
            data[code] = {"patents": 0, "projects": 0}
        data[code]["patents"] = int(_get(entry, "count"))

    for entry in cordis_countries:
        code = _normalize(str(_get(entry, "country")))
        if code not in data:
            data[code] = {"patents": 0, "projects": 0}
        data[code]["projects"] = int(_get(entry, "count"))

    result: list[dict[str, str | int]] = []
    for code, d in data.items():
        result.append({
            "country": code,
            "patents": d["patents"],
            "projects": d["projects"],
            "total": d["patents"] + d["projects"],
        })

    result.sort(key=lambda x: int(x["total"]), reverse=True)
    return result[:limit] if limit is not None else result
