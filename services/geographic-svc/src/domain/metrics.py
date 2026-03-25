"""UC6-spezifische Metriken und Hilfsfunktionen.

Lokaler Fallback fuer shared.domain.metrics und shared.domain.eu_countries,
falls das shared-Package nicht im PYTHONPATH liegt.
"""

from __future__ import annotations

from typing import Any

try:
    from shared.domain.result_types import CountryCount
except ImportError:
    CountryCount = Any  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# EU/EEA-Laender (Fallback fuer shared.domain.eu_countries)
# ---------------------------------------------------------------------------

EU_EEA_COUNTRIES: frozenset[str] = frozenset({
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR",
    "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO",
    "SE", "SI", "SK",
    "CH", "NO", "IS", "LI",
    "GB", "UK", "EL",
})


def is_european(code: str) -> bool:
    """Prueft ob ein Laendercode zum EU/EEA-Raum gehoert."""
    return code.upper().strip() in EU_EEA_COUNTRIES


# ---------------------------------------------------------------------------
# Laender-Zusammenfuehrung
# ---------------------------------------------------------------------------

def merge_country_data(
    patent_countries: list[CountryCount],
    cordis_countries: list[CountryCount],
    *,
    limit: int | None = None,
) -> list[dict[str, str | int]]:
    """Laender-Daten aus Patenten und CORDIS zusammenfuehren.

    Jeder Eintrag: {country, patents, projects, total}, sortiert nach total.
    """
    data: dict[str, dict[str, int]] = {}

    for entry in patent_countries:
        code = str(entry.country)
        if code not in data:
            data[code] = {"patents": 0, "projects": 0}
        data[code]["patents"] = int(entry.count)

    for entry in cordis_countries:
        code = str(entry.country)
        if code not in data:
            data[code] = {"patents": 0, "projects": 0}
        data[code]["projects"] = int(entry.count)

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


def compute_cross_border_share(
    total_projects: int,
    cross_border_projects: int,
) -> float:
    """Cross-Border-Anteil als Fraktion berechnen."""
    if total_projects <= 0:
        return 0.0
    return cross_border_projects / total_projects


def compute_activity_score(
    patent_count: int,
    project_count: int,
    publication_count: int = 0,
) -> float:
    """Gewichteter Activity-Score fuer ein Land.

    Gewichtung: Patente 0.4, Projekte 0.4, Publikationen 0.2
    """
    return patent_count * 0.4 + project_count * 0.4 + publication_count * 0.2
