"""GET /api/v1/suggestions — Autocomplete-Vorschlaege fuer das Suchfeld.

Liefert Technologie-Vorschlaege basierend auf Patent- und Projekt-Titeln
aus der PostgreSQL-Datenbank (via asyncpg). Bei leerem Suchbegriff
werden kuratierte Default-Vorschlaege zurueckgegeben.

Migriert aus v1.0 (SQLite + FTS5) auf PostgreSQL + pg_trgm/tsvector.
"""

from __future__ import annotations

import re
from collections import Counter

import structlog
from fastapi import APIRouter, Query, Request

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Suggestions"])


# ---------------------------------------------------------------------------
# Kuratierte Technologie-Liste (alphabetisch sortiert)
# Dient gleichzeitig als Default-Vorschlag und als Whitelist fuer die
# Frontend-Validierung (Pool-Endpoint /api/v1/suggestions/pool).
# ---------------------------------------------------------------------------
_DEFAULT_SUGGESTIONS: list[str] = [
    # AI & Computing
    "3D Printing",
    "5G",
    "6G",
    "Additive Manufacturing",
    "Artificial Intelligence",
    "Augmented Reality",
    "Autonomous Drones",
    "Autonomous Vehicles",
    # Batteries & Storage
    "Battery Technology",
    "Bioinformatics",
    "Biomaterials",
    "Bioprinting",
    "Blockchain",
    "Brain-Computer Interface",
    # Energy & Climate
    "Carbon Capture",
    "Chip Design",
    "Circular Economy",
    "Collaborative Robotics",
    "Composite Materials",
    "Computer Vision",
    "CRISPR",
    "Cybersecurity",
    "Data Center",
    "Deep Learning",
    "Digital Health",
    "Digital Twins",
    "Direct Air Capture",
    # Transportation
    "Edge Computing",
    "Electric Vehicles",
    "Extended Reality",
    "Federated Learning",
    "Fuel Cells",
    # Biotech & Medical
    "Gene Therapy",
    "Generative AI",
    "Geothermal Energy",
    "Graphene",
    "Green Hydrogen",
    "Grid Energy Storage",
    "Humanoid Robots",
    "Hydrogen Energy",
    "Hydrogen Vehicles",
    "Hyperloop",
    # Manufacturing & Industrial
    "Industrial IoT",
    "Internet of Things",
    "Large Language Models",
    "Laser Technology",
    "Lithium-Ion Batteries",
    # Materials
    "Machine Learning",
    "Metamaterials",
    "mRNA Technology",
    "Nanomaterials",
    "Nanotechnology",
    "Natural Language Processing",
    "Neuromorphic Computing",
    "Neuroprosthetics",
    "Nuclear Fusion",
    "Offshore Wind",
    "Perovskite Solar",
    "Photonic Computing",
    "Photovoltaic",
    "Post-Quantum Cryptography",
    "Precision Agriculture",
    "Precision Medicine",
    "Privacy Enhancing Technologies",
    # Quantum & Computing Infrastructure
    "Quantum Communication",
    "Quantum Computing",
    "Quantum Sensing",
    "Redox Flow Batteries",
    "Regenerative Medicine",
    "Reinforcement Learning",
    "Reusable Rockets",
    # Robotics & Automation
    "Robotics",
    "Satellite Internet",
    "Satellite Technology",
    "Semiconductor",
    "Small Modular Reactors",
    "Smart Factories",
    "Smart Grid",
    "Smart Materials",
    "Sodium-Ion Batteries",
    "Solar Energy",
    "Solid-State Batteries",
    # Space & Infrastructure
    "Space Technology",
    "Superconductor",
    "Sustainable Aviation Fuel",
    "Synthetic Biology",
    "Tidal Energy",
    "Urban Air Mobility",
    "Vertical Farming",
    "Virtual Reality",
    "Wearable Health",
    "Wind Energy",
    "Zero Trust Security",
]


# Stopwords fuer Ngram-Filterung (Patent-/Projekttitel enthalten viele
# generische Woerter die keine Technologiebegriffe sind)
_STOPWORDS = frozenset({
    # Englisch
    "a", "an", "the", "of", "for", "and", "or", "in", "on", "to", "with",
    "by", "from", "at", "its", "is", "are", "was", "were", "be", "been",
    "has", "have", "had", "do", "does", "did", "not", "no", "nor",
    "but", "if", "than", "that", "this", "these", "those", "such", "as",
    "based", "method", "methods", "using", "use", "used", "system", "systems",
    "device", "devices", "apparatus", "process", "processes", "comprising",
    "related", "new", "novel", "improved", "thereof", "therein", "wherein",
    "means", "including", "particularly", "especially", "via",
    # Deutsch
    "und", "fuer", "der", "die", "das", "ein", "eine", "von", "mit",
    "zur", "zum", "auf", "aus", "bei", "nach", "ueber",
    # Franzoesisch
    "le", "la", "les", "de", "du", "des", "un", "une", "et", "en",
    "au", "aux", "pour", "par", "sur", "dans", "avec",
    # Einzelbuchstaben
    *list("abcdefghijklmnopqrstuvwxyz"),
})


# ---------------------------------------------------------------------------
# Ngram-Extraktion aus Titeln (migriert aus v1.0 data.py)
# ---------------------------------------------------------------------------

_WORD_PATTERN = re.compile(r"[a-zA-Z0-9\u00e4\u00f6\u00fc\u00c4\u00d6\u00dc\u00df-]+")


def _extract_terms(
    titles: list[str],
    prefix: str,
    ngram_sizes: tuple[int, ...] = (2, 3),
) -> list[str]:
    """Haeufigste Ngrams aus Titeln extrahieren, die den Suchbegriff enthalten.

    Behaelt die Original-Gross-/Kleinschreibung bei (haeufigste Variante gewinnt).
    Filtert Stopword-lastige Ngrams und dedupliziert aehnliche Begriffe.
    """
    prefix_lower = prefix.lower()
    norm_to_forms: dict[str, Counter[str]] = {}

    for title in titles:
        words = _WORD_PATTERN.findall(title)
        for n in ngram_sizes:
            for i in range(len(words) - n + 1):
                ngram = " ".join(words[i : i + n])
                ngram_lower = ngram.lower()
                if prefix_lower not in ngram_lower:
                    continue
                # Stopword-Check: Technologiebegriffe beginnen/enden
                # nicht mit Stopwords ("a quantum", "using laser" etc.)
                ngram_words = ngram_lower.split()
                if ngram_words[0] in _STOPWORDS or ngram_words[-1] in _STOPWORDS:
                    continue
                if ngram_lower not in norm_to_forms:
                    norm_to_forms[ngram_lower] = Counter()
                norm_to_forms[ngram_lower][ngram] += 1

    # Pro normalisiertem Begriff: Gesamtcount + intelligente Schreibweise
    scored: list[tuple[str, int]] = []
    for _norm, forms in norm_to_forms.items():
        total = sum(forms.values())
        best_form = forms.most_common(1)[0][0]
        scored.append((_normalize_case(best_form), total))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [term for term, _ in scored[:30]]


def _normalize_case(term: str) -> str:
    """Intelligente Gross-/Kleinschreibung fuer Technologiebegriffe.

    - ALL CAPS oder all lowercase -> Title Case
    - Kurze ALL-CAPS-Woerter (<=4 Zeichen) bleiben gross (Akronyme: LED, AI, CPC)
    - Gemischte Schreibweise (Quantum Computing) bleibt erhalten
    """
    if not term.isupper() and not term.islower():
        return term

    words = term.split()
    result: list[str] = []
    for word in words:
        is_acronym = word.isupper() and len(word) <= 4 and not word.isdigit()
        if is_acronym and word.lower() not in _STOPWORDS:
            result.append(word)
        else:
            result.append(word.capitalize())
    return " ".join(result)


# ---------------------------------------------------------------------------
# Endpoint: GET /api/v1/suggestions
# ---------------------------------------------------------------------------


@router.get("/suggestions/pool")
async def suggestion_pool() -> list[str]:
    """Liefert die komplette kuratierte Technologie-Whitelist.

    Frontend nutzt diesen Pool, um Nutzer-Eingaben vor Submit zu validieren
    (nur Technologien aus dem Pool zulaessig, verhindert unsinnige Eingaben
    die Backend-Fehler provozieren wuerden).
    """
    return _DEFAULT_SUGGESTIONS


@router.get("/suggestions")
async def suggest_technologies(
    request: Request,
    q: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=8, ge=1, le=20),
) -> list[str]:
    """Technologie-Vorschlaege fuer die Suchfeld-Autocomplete.

    Bei leerem q werden kuratierte Default-Vorschlaege zurueckgegeben.
    Bei Eingabe >= 2 Zeichen werden Patent- und Projekt-Titel per
    PostgreSQL-Prefix-Suche abgefragt und Ngrams extrahiert.
    """
    # Leeres Suchfeld: kuratierte alphabetische Liste
    if not q or len(q.strip()) < 2:
        return _DEFAULT_SUGGESTIONS[:limit]

    q = q.strip()
    db_pool = getattr(request.app.state, "db_pool", None)

    if db_pool is None:
        logger.warning("suggestions_keine_db_verbindung")
        # Fallback: Default-Vorschlaege filtern
        return [
            s for s in _DEFAULT_SUGGESTIONS
            if q.lower() in s.lower()
        ][:limit]

    all_titles: list[str] = []

    try:
        async with db_pool.acquire() as conn:
            # Patent-Titel per Prefix-Suche (pg_trgm oder ILIKE)
            patent_rows = await conn.fetch(
                """
                SELECT title FROM patent_schema.patents
                WHERE title ILIKE $1
                LIMIT 500
                """,
                f"%{q}%",
            )
            all_titles.extend(row["title"] for row in patent_rows if row["title"])

            # Projekt-Titel per Prefix-Suche
            project_rows = await conn.fetch(
                """
                SELECT title FROM cordis_schema.projects
                WHERE title ILIKE $1
                LIMIT 200
                """,
                f"%{q}%",
            )
            all_titles.extend(row["title"] for row in project_rows if row["title"])

    except Exception as exc:
        logger.warning("suggestions_db_fehler", error=str(exc))
        # Fallback: Default-Vorschlaege filtern
        return [
            s for s in _DEFAULT_SUGGESTIONS
            if q.lower() in s.lower()
        ][:limit]

    if not all_titles:
        return []

    terms = _extract_terms(all_titles, q)
    return terms[:limit]
