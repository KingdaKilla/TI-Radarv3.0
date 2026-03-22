"""Deterministische, jahresstratifizierte Stichprobenziehung fuer Patent-Analysen.

Statistische Methode: Proportionale Allokation mit systematischer Auswahl
==========================================================================

Die Stichprobenziehung erfolgt in drei Schritten:

1. **Schichtung (Stratifikation)**: Die Grundgesamtheit wird nach Publikationsjahr
   in disjunkte Schichten (Strata) partitioniert. Jedes Patent gehoert exakt einer
   Schicht an.

2. **Proportionale Allokation**: Jede Schicht erhaelt einen Anteil an der
   Stichprobe, der ihrem Anteil an der Grundgesamtheit entspricht:

       n_h = round(n * N_h / N)

   wobei n = Stichprobengroesse, N_h = Schichtgroesse, N = Grundgesamtheit.

   Kleine Schichten (N_h <= Minimum) werden vollstaendig uebernommen
   (Census-Strata). Die ueberzaehligen Einheiten werden proportional von
   den grossen Schichten abgezogen.

3. **Systematische Auswahl (Midpoint-Regel)**: Innerhalb jeder Schicht wird
   systematisch mit festem Startoffset ausgewaehlt:

       Schritt k = N_h / n_h
       Start   s = floor(k / 2)
       Indices = [floor(s + i * k) for i in range(n_h)]

   Die Midpoint-Regel (s = k/2) vermeidet Randeffekte und ist voellig
   deterministisch — es wird kein Zufallszahlengenerator benoetigt.
   Die Elemente jeder Schicht werden vorab sortiert (standardmaessig nach
   ihrem Index in der Eingabeliste), sodass bei identischer Eingabe
   stets dasselbe Ergebnis entsteht.

Eigenschaften:
- Deterministisch: identischer Input -> identischer Output, ohne Seed
- Proportional: Jahresanteile in der Stichprobe = Jahresanteile in der Population
- Census-Strata: Jahre mit wenigen Patenten werden vollstaendig uebernommen
- Laufzeit: O(N) fuer Gruppierung + O(n) fuer Auswahl

Referenzen:
- Cochran, W. G. (1977). Sampling Techniques. 3rd ed. Wiley.
  Kapitel 5 (Stratified Random Sampling), Kapitel 7 (Systematic Sampling).
- Madow, W. G. & Madow, L. H. (1944). On the Theory of Systematic Sampling.
  Annals of Mathematical Statistics, 15(1), 1-24.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

DEFAULT_SAMPLE_SIZE: int = 10_000
"""Standard-Stichprobengroesse fuer CPC-Co-Klassifikation."""

CENSUS_THRESHOLD: int = 5
"""Schichten mit hoechstens so vielen Elementen werden vollstaendig uebernommen."""


# ---------------------------------------------------------------------------
# Ergebnis-Datenklasse
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SamplingResult:
    """Ergebnis der stratifizierten Stichprobenziehung.

    Attributes:
        sampled_data: Die ausgewaehlten Elemente in ihrer urspruenglichen
            Schicht-Reihenfolge (sortiert nach Jahr, dann Original-Index).
        population_size: Groesse der Grundgesamtheit (N).
        sample_size: Groesse der gezogenen Stichprobe (n).
        sampling_fraction: Auswahlsatz f = n / N.
        strata_info: Pro Schicht (Jahr): Populationsgroesse N_h,
            Stichprobengroesse n_h, und ob Census-Stratum.
        was_sampled: True wenn tatsaechlich eine Reduktion stattfand.
    """

    sampled_data: list[tuple[set[str], int]]
    population_size: int
    sample_size: int
    sampling_fraction: float
    strata_info: dict[int, StratumInfo]
    was_sampled: bool


@dataclass(frozen=True, slots=True)
class StratumInfo:
    """Informationen ueber eine einzelne Schicht (Jahrgang)."""

    population_count: int
    sample_count: int
    is_census: bool


# ---------------------------------------------------------------------------
# Kern-Algorithmus
# ---------------------------------------------------------------------------


def stratified_sample(
    patent_data: list[tuple[set[str], int]],
    *,
    target_size: int = DEFAULT_SAMPLE_SIZE,
    census_threshold: int = CENSUS_THRESHOLD,
) -> SamplingResult:
    """Proportionale jahresstratifizierte Stichprobe aus Patent-Daten ziehen.

    Args:
        patent_data: Liste von (cpc_code_set, year) Tupeln. Nur Patente mit
            mindestens 2 CPC-Codes (bereits gefiltert).
        target_size: Ziel-Stichprobengroesse. Standard: 10.000.
        census_threshold: Schichten mit <= dieser Groesse werden vollstaendig
            uebernommen. Standard: 5.

    Returns:
        SamplingResult mit der gezogenen Stichprobe und Metadaten.

    Raises:
        ValueError: Wenn target_size < 1.

    Performance:
        O(N) fuer Gruppierung, O(n) fuer systematische Auswahl.
        Bei N=100.000 und n=10.000 typischerweise < 10ms in CPython 3.12.

    Beispiel::

        data = [({\"H01L\", \"G06N\"}, 2020), ({\"B01D\", \"C07C\"}, 2021), ...]
        result = stratified_sample(data, target_size=1000)
        print(f\"{result.sample_size} von {result.population_size} ausgewaehlt\")
        # Downstream: build_cooccurrence_with_years(result.sampled_data)
    """
    if target_size < 1:
        msg = f"target_size muss >= 1 sein, erhalten: {target_size}"
        raise ValueError(msg)

    population_size = len(patent_data)

    # --- Trivialfall: Population passt komplett in Stichprobe ---
    if population_size <= target_size:
        trivial_strata = _group_by_year(patent_data)
        trivial_info = {
            year: StratumInfo(
                population_count=len(indices),
                sample_count=len(indices),
                is_census=True,
            )
            for year, indices in trivial_strata.items()
        }
        return SamplingResult(
            sampled_data=list(patent_data),
            population_size=population_size,
            sample_size=population_size,
            sampling_fraction=1.0,
            strata_info=trivial_info,
            was_sampled=False,
        )

    # --- Schritt 1: Nach Jahr gruppieren ---
    strata = _group_by_year(patent_data)

    # --- Schritt 2: Proportionale Allokation mit Census-Strata ---
    allocation = _allocate_proportional(
        strata_sizes={year: len(indices) for year, indices in strata.items()},
        target_size=target_size,
        census_threshold=census_threshold,
    )

    # --- Schritt 3: Systematische Auswahl pro Schicht ---
    selected_indices: list[int] = []
    strata_info: dict[int, StratumInfo] = {}

    for year in sorted(strata.keys()):
        indices = strata[year]
        n_h = allocation[year]
        is_census = n_h >= len(indices)

        strata_info[year] = StratumInfo(
            population_count=len(indices),
            sample_count=n_h,
            is_census=is_census,
        )

        if is_census:
            selected_indices.extend(indices)
        else:
            selected_indices.extend(
                _systematic_select(indices, n_h)
            )

    # Stichprobe zusammenstellen (Reihenfolge: sortiert nach Jahr, dann Index)
    sampled_data = [patent_data[i] for i in selected_indices]
    actual_size = len(sampled_data)

    return SamplingResult(
        sampled_data=sampled_data,
        population_size=population_size,
        sample_size=actual_size,
        sampling_fraction=actual_size / population_size,
        strata_info=strata_info,
        was_sampled=True,
    )


# ---------------------------------------------------------------------------
# Hilfs-Funktionen
# ---------------------------------------------------------------------------


def _group_by_year(
    patent_data: list[tuple[set[str], int]],
) -> dict[int, list[int]]:
    """Patent-Indizes nach Publikationsjahr gruppieren.

    Returns:
        Dict {year: [index_in_patent_data, ...]} mit sortierten Indizes.
    """
    groups: dict[int, list[int]] = defaultdict(list)
    for idx, (_, year) in enumerate(patent_data):
        groups[year].append(idx)
    return dict(groups)


def _allocate_proportional(
    strata_sizes: dict[int, int],
    target_size: int,
    census_threshold: int,
) -> dict[int, int]:
    """Proportionale Allokation mit Census-Strata-Korrektur.

    Algorithmus:
    1. Identifiziere Census-Strata (N_h <= census_threshold).
    2. Reserviere deren volle Groesse.
    3. Verteile die verbleibende Stichprobengroesse proportional auf die
       uebrigen Schichten.
    4. Korrigiere Rundungsfehler durch Largest-Remainder-Methode (Hare-Quota),
       damit die Summe exakt target_size ergibt.

    Args:
        strata_sizes: {year: N_h} fuer jede Schicht.
        target_size: Gewuenschte Gesamt-Stichprobengroesse n.
        census_threshold: Schichten <= dieser Groesse werden voll uebernommen.

    Returns:
        {year: n_h} Allokation pro Schicht.
    """
    census_years: set[int] = set()
    census_total = 0

    for year, size in strata_sizes.items():
        if size <= census_threshold:
            census_years.add(year)
            census_total += size

    remaining_target = target_size - census_total
    non_census_total = sum(
        size for year, size in strata_sizes.items() if year not in census_years
    )

    # Falls Census-Strata bereits die gesamte Stichprobe ausfuellen
    if remaining_target <= 0 or non_census_total == 0:
        result: dict[int, int] = {}
        for year, size in strata_sizes.items():
            if year in census_years:
                result[year] = size
            else:
                # Mindestens 1 pro nicht-leerer Schicht, um Repraesentativitaet
                # zu wahren (falls ueberhaupt Platz)
                result[year] = min(1, size) if remaining_target > 0 else 0
        return result

    # Proportionale Verteilung mit Largest-Remainder-Korrektur
    allocation: dict[int, int] = {}
    remainders: list[tuple[int, float]] = []

    for year, size in strata_sizes.items():
        if year in census_years:
            allocation[year] = size
            continue

        exact = remaining_target * size / non_census_total
        floored = math.floor(exact)
        # Sicherheitsgrenze: nicht mehr als N_h
        floored = min(floored, size)
        allocation[year] = floored
        remainders.append((year, exact - floored))

    # Rundungsdifferenz verteilen (Largest-Remainder / Hare-Quota)
    current_sum = sum(allocation.values())
    deficit = target_size - current_sum

    # Sortiere nach groesstem Remainder (absteigend)
    remainders.sort(key=lambda x: x[1], reverse=True)

    for year, _ in remainders:
        if deficit <= 0:
            break
        # Nicht ueber N_h hinaus allokieren
        if allocation[year] < strata_sizes[year]:
            allocation[year] += 1
            deficit -= 1

    return allocation


def _systematic_select(indices: list[int], n: int) -> list[int]:
    """Systematische Auswahl mit Midpoint-Start aus einer sortierten Index-Liste.

    Waehlt n Elemente aus indices mittels gleichmaessiger Schrittweite.
    Der Startpunkt liegt bei floor(step/2) (Midpoint-Regel).

    Args:
        indices: Sortierte Liste von Indizes (aufsteigend).
        n: Anzahl zu waehlender Elemente.

    Returns:
        Liste von n ausgewaehlten Indizes.
    """
    total = len(indices)
    if n >= total:
        return list(indices)
    if n == 0:
        return []

    step = total / n
    start = step / 2.0
    return [indices[int(start + i * step)] for i in range(n)]


# ---------------------------------------------------------------------------
# Stichprobenfehler / Konfidenz
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class JaccardConfidence:
    """Konfidenzschaetzung fuer einen Jaccard-Index aus stratifizierter Stichprobe.

    Attributes:
        jaccard: Punkt-Schaetzung des Jaccard-Index.
        standard_error: Geschaetzter Standardfehler (mit FPC).
        margin_of_error_95: Halbe Breite des 95%-Konfidenzintervalls.
        ci_lower: Untere Grenze des 95%-Konfidenzintervalls (geclippt auf [0, 1]).
        ci_upper: Obere Grenze des 95%-Konfidenzintervalls (geclippt auf [0, 1]).
        effective_n: Effektive Stichprobengroesse (Vereinigungsmenge).
    """

    jaccard: float
    standard_error: float
    margin_of_error_95: float
    ci_lower: float
    ci_upper: float
    effective_n: int


def estimate_jaccard_confidence(
    intersection_count: int,
    union_count: int,
    sample_size: int,
    population_size: int,
) -> JaccardConfidence:
    """Konfidenzintervall fuer einen geschaetzten Jaccard-Index berechnen.

    Der Jaccard-Index J = |A intersect B| / |A union B| kann als Proportion
    p der Patente in der Vereinigungsmenge betrachtet werden, die beide
    CPC-Codes tragen.

    Fuer Proportionen aus endlichen Populationen gilt:

        SE(p) = sqrt(p * (1-p) / (n-1)) * sqrt(1 - n/N)

    wobei:
    - p = intersection_count / union_count (Punkt-Schaetzung)
    - n = union_count in der Stichprobe (effektive Stichprobengroesse)
    - N = union_count * (population_size / sample_size) (geschaetzte
      Vereinigungsgroesse in der Population)
    - sqrt(1 - n/N) = Finite Population Correction (FPC)

    Bei sample_size == population_size (keine Stichprobe) ist SE = 0.

    Args:
        intersection_count: |A intersect B| in der Stichprobe.
        union_count: |A union B| in der Stichprobe.
        sample_size: Stichprobengroesse n.
        population_size: Populationsgroesse N.

    Returns:
        JaccardConfidence mit Punkt-Schaetzung und 95%-KI.
    """
    if union_count == 0:
        return JaccardConfidence(
            jaccard=0.0,
            standard_error=0.0,
            margin_of_error_95=0.0,
            ci_lower=0.0,
            ci_upper=0.0,
            effective_n=0,
        )

    p = intersection_count / union_count

    # Keine Stichprobe (Vollerhebung) oder exakter Wert
    if sample_size >= population_size or union_count <= 1:
        return JaccardConfidence(
            jaccard=round(p, 6),
            standard_error=0.0,
            margin_of_error_95=0.0,
            ci_lower=round(p, 6),
            ci_upper=round(p, 6),
            effective_n=union_count,
        )

    # Geschaetzte Vereinigungsgroesse in der Population
    scaling = population_size / sample_size
    estimated_union_pop = union_count * scaling

    # Finite Population Correction (FPC)
    fpc = math.sqrt(max(0.0, 1.0 - union_count / estimated_union_pop))

    # Standardfehler der Proportion
    variance = p * (1.0 - p) / (union_count - 1)
    se = math.sqrt(variance) * fpc

    # 95%-KI (z = 1.96)
    z = 1.96
    moe = z * se

    return JaccardConfidence(
        jaccard=round(p, 6),
        standard_error=round(se, 6),
        margin_of_error_95=round(moe, 6),
        ci_lower=round(max(0.0, p - moe), 6),
        ci_upper=round(min(1.0, p + moe), 6),
        effective_n=union_count,
    )
