"""Entity Resolution — Normalisierung und Fuzzy-Matching fuer Akteure.

Pipeline zur Vereinheitlichung von Organisationsnamen aus EPO, CORDIS und GLEIF.
Reine Funktionen ohne IO — testbar, auditierbar, reproduzierbar.

Matching-Strategie:
1. Normalisierung (5 Schritte): Gross-/Kleinschreibung, Rechtsformen, Abkuerzungen
2. Blocking: Erstes Zeichen + Laendercode (reduziert Vergleichsraum)
3. Fuzzy Matching: Levenshtein (0.4) + TF-IDF Cosine (0.6) kombiniert
4. Schwellwert: Combined Score > 0.8 fuer Match
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections import defaultdict
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rechtsformen: werden bei Normalisierung entfernt
# ---------------------------------------------------------------------------
# Sortierung nach Laenge absteigend, damit laengere Formen zuerst gematcht werden
# (z.B. "S.A.S." vor "S.A.", "GmbH" vor "G")
LEGAL_FORMS: list[str] = sorted(
    [
        "AG", "GmbH", "Ltd", "S.A.", "B.V.", "Inc.", "Corp.", "S.p.A.",
        "S.r.l.", "AB", "AS", "Oy", "NV", "SE", "plc", "LLC", "Co.",
        "KG", "OHG", "e.V.", "S.L.", "S.A.S.", "GbR", "UG",
        # Zusaetzliche Varianten ohne Punkte
        "SA", "BV", "SPA", "SRL", "SAS", "SL", "eV", "PLC",
        "INC", "CORP", "LTD", "LIMITED", "CORPORATION", "INCORPORATED",
        "GMBH", "GESELLSCHAFT MIT BESCHRAENKTER HAFTUNG",
    ],
    key=len,
    reverse=True,
)

# Regex-Pattern fuer Rechtsformen (Word-Boundary-basiert)
_LEGAL_FORM_PATTERN: re.Pattern[str] = re.compile(
    r"\b(" + "|".join(re.escape(lf) for lf in LEGAL_FORMS) + r")\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Abkuerzungs-Expansion
# ---------------------------------------------------------------------------
ABBREVIATIONS: dict[str, str] = {
    "UNIV": "UNIVERSITY",
    "TECH": "TECHNOLOGY",
    "INST": "INSTITUTE",
    "LAB": "LABORATORY",
    "NATL": "NATIONAL",
    "INTL": "INTERNATIONAL",
    "DEPT": "DEPARTMENT",
    "RES": "RESEARCH",
    "CTR": "CENTER",
    "SCI": "SCIENCE",
    "ENG": "ENGINEERING",
}

# Regex-Pattern fuer Abkuerzungs-Expansion (ganze Woerter)
_ABBREVIATION_PATTERN: re.Pattern[str] = re.compile(
    r"\b(" + "|".join(re.escape(abbr) for abbr in ABBREVIATIONS) + r")\b",
)


# ============================================================================
# Schritt 1-5: Normalisierungspipeline
# ============================================================================


def _strip_accents(text: str) -> str:
    """Unicode-Akzente entfernen (NFD-Zerlegung + Combining-Characters filtern)."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn")


def normalize_actor_name(name: str) -> str:
    """
    5-stufige Normalisierung eines Organisationsnamens.

    1. UPPER(), TRIM()
    2. Rechtsformen entfernen (AG, GmbH, Ltd, etc.)
    3. Abkuerzungen expandieren (Univ -> University, etc.)
    4. Sonderzeichen entfernen (nur alphanumerisch + Leerzeichen)
    5. Mehrfach-Leerzeichen kollabieren

    Args:
        name: Roher Organisationsname

    Returns:
        Normalisierter Name (Grossbuchstaben, bereinigt)
    """
    if not name or not name.strip():
        return ""

    # Schritt 1: Grossbuchstaben + Trim
    result = name.strip().upper()

    # Akzente entfernen (oe -> o, etc.) fuer konsistenten Vergleich
    result = _strip_accents(result)

    # Schritt 2: Rechtsformen entfernen
    result = _LEGAL_FORM_PATTERN.sub("", result)

    # Schritt 3: Abkuerzungen expandieren
    result = _ABBREVIATION_PATTERN.sub(
        lambda m: ABBREVIATIONS[m.group(0)],
        result,
    )

    # Schritt 4: Sonderzeichen entfernen (nur alphanumerisch + Leerzeichen)
    result = re.sub(r"[^A-Z0-9\s]", " ", result)

    # Schritt 5: Mehrfach-Leerzeichen kollabieren + Trim
    result = re.sub(r"\s+", " ", result).strip()

    return result


# ============================================================================
# Blocking: Reduktion des Vergleichsraums
# ============================================================================


def generate_blocking_key(name: str, country: str) -> str:
    """
    Blocking-Key aus erstem Zeichen des normalisierten Namens + Laendercode.

    Reduziert den Vergleichsraum: Nur Akteure im selben Block
    werden paarweise verglichen.

    Args:
        name: Normalisierter Organisationsname
        country: ISO-3166-1 Alpha-2 Laendercode (z.B. "DE")

    Returns:
        Blocking-Key (z.B. "F_DE" fuer Fraunhofer in Deutschland)
    """
    normalized = normalize_actor_name(name) if name else ""
    first_char = normalized[0] if normalized else "_"
    country_code = (country or "XX").upper().strip()[:2]
    return f"{first_char}_{country_code}"


# ============================================================================
# Fuzzy Matching: Levenshtein + TF-IDF Cosine
# ============================================================================


def levenshtein_similarity(a: str, b: str) -> float:
    """
    Normalisierte Levenshtein-Aehnlichkeit (0.0 = voellig verschieden, 1.0 = identisch).

    Formel: 1.0 - (edit_distance / max(len(a), len(b)))

    Versucht rapidfuzz (C-Extension, schneller), faellt auf eigene
    Implementierung zurueck falls nicht installiert.

    Args:
        a: Erster Name (normalisiert)
        b: Zweiter Name (normalisiert)

    Returns:
        Aehnlichkeitswert zwischen 0.0 und 1.0
    """
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0

    # rapidfuzz bevorzugen (C-Extension, deutlich schneller)
    try:
        from rapidfuzz.distance import Levenshtein  # type: ignore[import-untyped]

        dist = Levenshtein.distance(a, b)
        max_len = max(len(a), len(b))
        return 1.0 - (dist / max_len) if max_len > 0 else 1.0
    except ImportError:
        pass

    # Fallback: Dynamic-Programming-Implementierung
    return _levenshtein_dp(a, b)


def _levenshtein_dp(a: str, b: str) -> float:
    """Levenshtein-Aehnlichkeit via Dynamic Programming (Fallback)."""
    n, m = len(a), len(b)
    if n == 0 or m == 0:
        return 0.0

    # Wagner-Fischer Algorithmus (Speicheroptimiert: nur 2 Zeilen)
    prev = list(range(m + 1))
    curr = [0] * (m + 1)

    for i in range(1, n + 1):
        curr[0] = i
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr[j] = min(
                prev[j] + 1,       # Loeschung
                curr[j - 1] + 1,    # Einfuegung
                prev[j - 1] + cost,  # Substitution
            )
        prev, curr = curr, prev

    distance = prev[m]
    max_len = max(n, m)
    return 1.0 - (distance / max_len)


def tfidf_cosine_similarity(names: list[str]) -> np.ndarray:
    """
    TF-IDF Cosine-Aehnlichkeitsmatrix fuer eine Liste von Namen.

    Verwendet Character-N-Gramme (2-4), um auch bei Tippfehlern
    und Wortumstellungen aehnliche Namen zu erkennen.

    Args:
        names: Liste normalisierter Organisationsnamen

    Returns:
        NxN Aehnlichkeitsmatrix (numpy array, dtype float64)

    Raises:
        ImportError: Wenn scikit-learn nicht installiert ist
    """
    if len(names) < 2:
        return np.ones((len(names), len(names)), dtype=np.float64)

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore[import-untyped]
        from sklearn.metrics.pairwise import cosine_similarity  # type: ignore[import-untyped]

        vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 4),
            lowercase=False,  # bereits normalisiert
        )
        tfidf_matrix = vectorizer.fit_transform(names)
        sim_matrix: np.ndarray = cosine_similarity(tfidf_matrix).astype(np.float64)
        return sim_matrix

    except ImportError:
        logger.warning(
            "scikit-learn nicht installiert — TF-IDF deaktiviert, "
            "verwende nur Levenshtein-Distanz"
        )
        # Fallback: Identitaetsmatrix (kein TF-IDF-Beitrag)
        return np.eye(len(names), dtype=np.float64)


# ============================================================================
# Matching-Pipeline
# ============================================================================


def _compute_combined_score(
    lev_score: float,
    tfidf_score: float,
    *,
    lev_weight: float = 0.4,
    tfidf_weight: float = 0.6,
) -> float:
    """Gewichteter Combined Score aus Levenshtein + TF-IDF."""
    return lev_weight * lev_score + tfidf_weight * tfidf_score


def _determine_match_method(lev_score: float, tfidf_score: float) -> str:
    """Bestimmung der dominanten Match-Methode fuer Audit-Zwecke."""
    if lev_score >= 0.95 and tfidf_score >= 0.95:
        return "exact"
    if lev_score > tfidf_score:
        return "levenshtein"
    return "tfidf_cosine"


def find_matches(
    actors: list[dict[str, Any]],
    threshold: float = 0.8,
) -> list[dict[str, Any]]:
    """
    Akteure zu Match-Gruppen zusammenfuehren.

    Pipeline:
    1. Normalisierung aller Namen
    2. Blocking nach erstem Zeichen + Laendercode
    3. Paarweiser Vergleich innerhalb jedes Blocks
    4. Union-Find zur Gruppenbildung
    5. Kanonischen Namen bestimmen (laengster Originalname)

    Args:
        actors: Liste von Dicts mit keys: name, country, source
                Optional: source_id (fuer DB-Mapping)
        threshold: Minimaler Combined Score fuer Match (default: 0.8)

    Returns:
        Liste von Match-Gruppen:
        [{"canonical_name": str,
          "country": str,
          "members": [{"name": str, "source": str, "confidence": float,
                        "match_method": str, "normalized_name": str}]}]
    """
    if not actors:
        return []

    n = len(actors)

    # Normalisierung
    normalized_names = [
        normalize_actor_name(a.get("name", "")) for a in actors
    ]

    # Blocking
    blocks: dict[str, list[int]] = defaultdict(list)
    for i, actor in enumerate(actors):
        key = generate_blocking_key(
            actor.get("name", ""),
            actor.get("country", "XX"),
        )
        blocks[key].append(i)

    logger.info(
        "Entity Resolution: %d Akteure in %d Blocks",
        n, len(blocks),
    )

    # Union-Find Datenstruktur
    parent = list(range(n))
    rank = [0] * n
    best_score = [0.0] * n  # Bester Match-Score pro Akteur

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # Pfadkompression
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx == ry:
            return
        if rank[rx] < rank[ry]:
            rx, ry = ry, rx
        parent[ry] = rx
        if rank[rx] == rank[ry]:
            rank[rx] += 1

    # Match-Scores speichern
    pair_scores: dict[tuple[int, int], tuple[float, str]] = {}

    # Paarweiser Vergleich innerhalb jedes Blocks
    for block_key, indices in blocks.items():
        if len(indices) < 2:
            continue

        # TF-IDF fuer den gesamten Block berechnen
        block_names = [normalized_names[i] for i in indices]
        tfidf_matrix = tfidf_cosine_similarity(block_names)

        for local_i in range(len(indices)):
            for local_j in range(local_i + 1, len(indices)):
                gi, gj = indices[local_i], indices[local_j]
                name_a = normalized_names[gi]
                name_b = normalized_names[gj]

                # Leere Namen ueberspringen
                if not name_a or not name_b:
                    continue

                # Levenshtein
                lev_score = levenshtein_similarity(name_a, name_b)

                # TF-IDF aus vorberechneter Matrix
                tfidf_score = float(tfidf_matrix[local_i, local_j])

                # Combined Score
                combined = _compute_combined_score(lev_score, tfidf_score)

                if combined >= threshold:
                    union(gi, gj)
                    method = _determine_match_method(lev_score, tfidf_score)
                    pair_key = (min(gi, gj), max(gi, gj))
                    pair_scores[pair_key] = (combined, method)

                    # Besten Score tracken
                    best_score[gi] = max(best_score[gi], combined)
                    best_score[gj] = max(best_score[gj], combined)

    # Gruppen bilden
    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)

    # Ergebnis aufbauen
    result: list[dict[str, Any]] = []
    for root, members in groups.items():
        # Kanonischer Name: laengster Originalname (meiste Information)
        canonical_idx = max(members, key=lambda i: len(actors[i].get("name", "")))
        canonical_name = actors[canonical_idx].get("name", "")

        # Laendercode: Modus der Gruppe
        country_counts: dict[str, int] = defaultdict(int)
        for idx in members:
            c = actors[idx].get("country", "")
            if c:
                country_counts[c] += 1
        group_country = (
            max(country_counts, key=country_counts.get)  # type: ignore[arg-type]
            if country_counts
            else ""
        )

        member_list: list[dict[str, Any]] = []
        for idx in members:
            # Confidence: 1.0 fuer Einzelgaenger, sonst bester Paar-Score
            if len(members) == 1:
                confidence = 1.0
                method = "singleton"
            else:
                confidence = best_score[idx] if best_score[idx] > 0 else 1.0
                # Match-Methode aus dem besten Paar
                method = "combined"
                for other in members:
                    if other == idx:
                        continue
                    pair_key = (min(idx, other), max(idx, other))
                    if pair_key in pair_scores:
                        score, m = pair_scores[pair_key]
                        if score == confidence:
                            method = m
                            break

            member_info: dict[str, Any] = {
                "name": actors[idx].get("name", ""),
                "source": actors[idx].get("source", ""),
                "confidence": round(confidence, 4),
                "match_method": method,
                "normalized_name": normalized_names[idx],
            }
            # source_id mituebernehmen falls vorhanden
            if "source_id" in actors[idx]:
                member_info["source_id"] = actors[idx]["source_id"]

            member_list.append(member_info)

        result.append({
            "canonical_name": canonical_name,
            "country": group_country,
            "members": member_list,
        })

    logger.info(
        "Entity Resolution: %d Akteure -> %d Gruppen "
        "(%d Matches, %d Singletons)",
        n,
        len(result),
        sum(1 for g in result if len(g["members"]) > 1),
        sum(1 for g in result if len(g["members"]) == 1),
    )

    return result
