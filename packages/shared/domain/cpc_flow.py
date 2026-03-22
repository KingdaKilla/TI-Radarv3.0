"""CPC-Technologiefluss: Co-Klassifikations-Analyse via Jaccard-Index."""

from __future__ import annotations

import math
from collections import Counter
from itertools import combinations
from typing import Any


def normalize_cpc(code: str, level: int = 4) -> str:
    """CPC-Code auf ein bestimmtes Hierarchie-Level kuerzen.

    Level 4 = Subklasse (z.B. 'H01L'), Level 3 = Klasse (z.B. 'H01').
    """
    clean = code.strip().replace(" ", "")
    return clean[:level] if len(clean) >= level else clean


def extract_cpc_sets(
    cpc_strings: list[str], level: int = 4
) -> list[set[str]]:
    """Aus kommaseparierten CPC-Strings pro Patent eine Menge normalisierter Codes erzeugen."""
    result: list[set[str]] = []
    for raw in cpc_strings:
        if not raw:
            continue
        codes = {normalize_cpc(c, level) for c in raw.split(",") if c.strip()}
        if len(codes) >= 2:
            result.append(codes)
    return result


def extract_cpc_sets_with_years(
    patent_rows: list[dict[str, str | int]], level: int = 4
) -> list[tuple[set[str], int]]:
    """CPC-Sets + Jahr aus patent_rows extrahieren."""
    result: list[tuple[set[str], int]] = []
    for row in patent_rows:
        raw = str(row.get("cpc_codes", ""))
        year = int(row.get("year", 0))
        if not raw or year == 0:
            continue
        codes = {normalize_cpc(c, level) for c in raw.split(",") if c.strip()}
        if len(codes) >= 2:
            result.append((codes, year))
    return result


def build_cooccurrence(
    patent_sets: list[set[str]], top_n: int = 15
) -> tuple[list[str], list[list[float]], int]:
    """Co-Occurrence-Matrix und Jaccard-Normalisierung berechnen.

    Returns:
        (labels, jaccard_matrix, total_connections)
    """
    # Haeufigste CPC-Codes ermitteln
    code_counter: Counter[str] = Counter()
    for codes in patent_sets:
        for code in codes:
            code_counter[code] += 1

    top_codes = [code for code, _ in code_counter.most_common(top_n)]
    if len(top_codes) < 2:
        return top_codes, [], 0

    n = len(top_codes)
    code_index = {code: i for i, code in enumerate(top_codes)}

    # Co-Occurrence zaehlen
    pair_counts: Counter[tuple[int, int]] = Counter()
    code_patent_sets: dict[int, set[int]] = {i: set() for i in range(n)}

    for patent_id, codes in enumerate(patent_sets):
        relevant = [code_index[c] for c in codes if c in code_index]
        for idx in relevant:
            code_patent_sets[idx].add(patent_id)
        for a, b in combinations(sorted(relevant), 2):
            pair_counts[(a, b)] += 1

    # Jaccard-Matrix berechnen
    matrix: list[list[float]] = [[0.0] * n for _ in range(n)]
    total_connections = 0

    for (a, b), count in pair_counts.items():
        if count < 1:
            continue
        union_size = len(code_patent_sets[a] | code_patent_sets[b])
        jaccard = count / union_size if union_size > 0 else 0.0
        matrix[a][b] = round(jaccard, 4)
        matrix[b][a] = round(jaccard, 4)
        total_connections += 1

    return top_codes, matrix, total_connections


def build_cooccurrence_with_years(
    patent_data: list[tuple[set[str], int]], top_n: int = 15
) -> tuple[list[str], list[list[float]], int, dict[str, Any]]:
    """Co-Occurrence mit Jahr-Tracking fuer Frontend-seitige Neuberechnung.

    Returns:
        (labels, jaccard_matrix, total_connections, year_data)
    """
    # Alle CPC-Sets (ohne Jahr) fuer Gesamt-Matrix
    patent_sets = [codes for codes, _ in patent_data]

    # Haeufigste CPC-Codes ermitteln
    code_counter: Counter[str] = Counter()
    for codes in patent_sets:
        for code in codes:
            code_counter[code] += 1

    # Alle CPC-Codes sortiert nach Haeufigkeit (fuer year_data)
    all_codes = [code for code, _ in code_counter.most_common()]
    top_codes = all_codes[:top_n]
    if len(top_codes) < 2:
        return top_codes, [], 0, {}

    n = len(top_codes)
    code_index = {code: i for i, code in enumerate(top_codes)}

    # Co-Occurrence zaehlen (Gesamt + pro Jahr)
    pair_counts: Counter[tuple[int, int]] = Counter()
    code_patent_sets: dict[int, set[int]] = {i: set() for i in range(n)}

    # Year-level tracking (alle Codes, nicht nur top_n)
    all_code_set = set(all_codes)
    pair_counts_by_year: dict[int, dict[str, int]] = {}
    cpc_counts_by_year: dict[int, dict[str, int]] = {}
    years_seen: set[int] = set()

    for patent_id, (codes, year) in enumerate(patent_data):
        years_seen.add(year)

        # Year-level CPC counts (alle Codes)
        if year not in cpc_counts_by_year:
            cpc_counts_by_year[year] = {}
        for code in codes:
            if code in all_code_set:
                cpc_counts_by_year[year][code] = cpc_counts_by_year[year].get(code, 0) + 1

        # Year-level pair counts (alle Codes)
        if year not in pair_counts_by_year:
            pair_counts_by_year[year] = {}
        relevant_all = sorted(c for c in codes if c in all_code_set)
        for ca, cb in combinations(relevant_all, 2):
            key = f"{ca}|{cb}"
            pair_counts_by_year[year][key] = pair_counts_by_year[year].get(key, 0) + 1

        # Gesamt-Matrix (nur top_n)
        relevant = [code_index[c] for c in codes if c in code_index]
        for idx in relevant:
            code_patent_sets[idx].add(patent_id)
        for ia, ib in combinations(sorted(relevant), 2):
            pair_counts[(ia, ib)] += 1

    # Jaccard-Matrix berechnen (Gesamt)
    matrix: list[list[float]] = [[0.0] * n for _ in range(n)]
    total_connections = 0

    for (ia, ib), count in pair_counts.items():
        if count < 1:
            continue
        union_size = len(code_patent_sets[ia] | code_patent_sets[ib])
        jaccard = count / union_size if union_size > 0 else 0.0
        matrix[ia][ib] = round(jaccard, 4)
        matrix[ib][ia] = round(jaccard, 4)
        total_connections += 1

    sorted_years = sorted(years_seen)
    year_data: dict[str, Any] = {
        "min_year": sorted_years[0] if sorted_years else 0,
        "max_year": sorted_years[-1] if sorted_years else 0,
        "all_labels": all_codes,
        "pair_counts": {
            str(y): pair_counts_by_year.get(y, {}) for y in sorted_years
        },
        "cpc_counts": {
            str(y): cpc_counts_by_year.get(y, {}) for y in sorted_years
        },
    }

    return top_codes, matrix, total_connections, year_data


def build_jaccard_from_sql(
    top_codes: list[str],
    code_counts: dict[str, int],
    pair_counts: list[tuple[str, str, int]],
) -> tuple[list[list[float]], int]:
    """Jaccard-Matrix aus SQL-Aggregaten berechnen.

    Args:
        top_codes: Sortierte CPC-Codes (Top-N).
        code_counts: {cpc_code: patent_count} fuer jeden Top-Code.
        pair_counts: [(code_a, code_b, co_count), ...] Co-Occurrence-Paare.

    Returns:
        (jaccard_matrix, total_connections)
    """
    n = len(top_codes)
    if n < 2:
        return [], 0

    code_index = {code: i for i, code in enumerate(top_codes)}
    matrix: list[list[float]] = [[0.0] * n for _ in range(n)]
    total_connections = 0

    for code_a, code_b, co_count in pair_counts:
        if co_count < 1:
            continue
        ia = code_index.get(code_a)
        ib = code_index.get(code_b)
        if ia is None or ib is None:
            continue
        count_a = code_counts.get(code_a, 0)
        count_b = code_counts.get(code_b, 0)
        union = count_a + count_b - co_count
        jaccard = co_count / union if union > 0 else 0.0
        rounded = round(jaccard, 4)
        matrix[ia][ib] = rounded
        matrix[ib][ia] = rounded
        total_connections += 1

    return matrix, total_connections


def build_year_data_from_aggregates(
    all_codes: list[str],
    cpc_year_counts: list[tuple[str, int, int]],
    pair_year_counts: list[tuple[str, str, int, int]],
) -> dict[str, Any]:
    """Year-Data-Struktur aus SQL-Aggregaten aufbauen.

    Konvertiert die SQL-Ergebnisse in das Format das das Frontend erwartet
    (identisch zu build_cooccurrence_with_years).

    Args:
        all_codes: Alle CPC-Codes sortiert nach Haeufigkeit.
        cpc_year_counts: [(cpc_code, pub_year, count), ...] pro Code und Jahr.
        pair_year_counts: [(code_a, code_b, pub_year, co_count), ...] pro Paar und Jahr.

    Returns:
        dict mit min_year, max_year, all_labels, pair_counts, cpc_counts.
    """
    years_seen: set[int] = set()
    cpc_counts_by_year: dict[int, dict[str, int]] = {}
    pair_counts_by_year: dict[int, dict[str, int]] = {}

    for code, year, count in cpc_year_counts:
        years_seen.add(year)
        if year not in cpc_counts_by_year:
            cpc_counts_by_year[year] = {}
        cpc_counts_by_year[year][code] = count

    for code_a, code_b, year, co_count in pair_year_counts:
        years_seen.add(year)
        if year not in pair_counts_by_year:
            pair_counts_by_year[year] = {}
        key = f"{code_a}|{code_b}" if code_a < code_b else f"{code_b}|{code_a}"
        pair_counts_by_year[year][key] = co_count

    sorted_years = sorted(years_seen)
    return {
        "min_year": sorted_years[0] if sorted_years else 0,
        "max_year": sorted_years[-1] if sorted_years else 0,
        "all_labels": all_codes,
        "pair_counts": {
            str(y): pair_counts_by_year.get(y, {}) for y in sorted_years
        },
        "cpc_counts": {
            str(y): cpc_counts_by_year.get(y, {}) for y in sorted_years
        },
    }


def compute_whitespace_opportunities(
    labels: list[str],
    matrix: list[list[float]],
    code_counts: dict[str, int],
    *,
    min_activity_percentile: float = 0.25,
    jaccard_threshold: float = 0.05,
    top_n: int = 10,
) -> list[dict[str, Any]]:
    """Whitespace-Analyse: Innovationsluecken in CPC-Ko-Klassifikation identifizieren.

    Findet CPC-Code-Paare mit hoher Einzelaktivitaet aber geringer Ko-Klassifikation.
    Basiert auf Yoon & Park (2005) 'Patent Vacuums' und Kim, Cho & Kim (2019)
    'Recombinant Search'.

    Args:
        labels: CPC-Code-Labels (z.B. ['H01L', 'C01B', ...]).
        matrix: Jaccard-Similarity-Matrix (NxN, symmetrisch).
        code_counts: {cpc_code: patent_count} fuer Aktivitaetsfilter.
        min_activity_percentile: Mindest-Perzentil fuer Einzelaktivitaet.
        jaccard_threshold: Maximaler Jaccard fuer Whitespace-Kandidaten.
        top_n: Anzahl zurueckgegebener Whitespace-Opportunitaeten.

    Returns:
        Sortierte Liste der Top-Whitespace-Paare:
        [{"code_a", "code_b", "jaccard", "freq_a", "freq_b", "opportunity_score"}, ...]
    """
    n = len(labels)
    if n < 2 or not code_counts:
        return []

    counts = sorted(code_counts.get(label, 0) for label in labels)
    threshold_idx = max(0, int(len(counts) * min_activity_percentile))
    min_count = counts[threshold_idx] if counts else 0
    max_count = max(counts) if counts else 1

    opportunities: list[dict[str, Any]] = []

    for i in range(n):
        freq_i = code_counts.get(labels[i], 0)
        if freq_i < min_count:
            continue
        for j in range(i + 1, n):
            freq_j = code_counts.get(labels[j], 0)
            if freq_j < min_count:
                continue

            jaccard = matrix[i][j] if i < len(matrix) and j < len(matrix[i]) else 0.0
            if jaccard > jaccard_threshold:
                continue

            activity = math.sqrt(freq_i * freq_j) / max_count if max_count > 0 else 0
            score = round((1.0 - jaccard) * activity, 4)

            opportunities.append({
                "code_a": labels[i],
                "code_b": labels[j],
                "jaccard": round(jaccard, 4),
                "freq_a": freq_i,
                "freq_b": freq_j,
                "opportunity_score": score,
            })

    opportunities.sort(key=lambda o: o["opportunity_score"], reverse=True)
    return opportunities[:top_n]


# Farben fuer CPC-Sektionen (A-H + Y)
CPC_COLORS: dict[str, str] = {
    "A": "#ef4444",  # rot
    "B": "#f97316",  # orange
    "C": "#eab308",  # gelb
    "D": "#22c55e",  # gruen
    "E": "#06b6d4",  # cyan
    "F": "#3b82f6",  # blau
    "G": "#8b5cf6",  # violett
    "H": "#ec4899",  # pink
    "Y": "#6b7280",  # grau
}


def assign_colors(labels: list[str]) -> list[str]:
    """Farben basierend auf CPC-Sektion (erster Buchstabe) zuweisen."""
    return [CPC_COLORS.get(label[0], "#9ca3af") if label else "#9ca3af" for label in labels]
