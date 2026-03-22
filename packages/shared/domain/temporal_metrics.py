"""Reine Berechnungsfunktionen fuer Temporale Dynamik (UC8).

Alle Funktionen sind zustandslos und ohne I/O — testbar und auditierbar.
"""

from __future__ import annotations

from typing import Any


def _compute_actor_dynamics(
    actors_by_year: dict[int, dict[str, int]],
) -> list[dict[str, Any]]:
    """New Entrant Rate und Persistence Rate pro Jahr."""
    sorted_years = sorted(actors_by_year.keys())
    if not sorted_years:
        return []

    result: list[dict[str, Any]] = []
    prev_actors: set[str] = set()

    for year in sorted_years:
        current_actors = set(actors_by_year[year].keys())

        if not prev_actors:
            new_entrant_rate = 1.0
            persistence_rate = 0.0
        else:
            new_entrants = current_actors - prev_actors
            persisting = current_actors & prev_actors
            new_entrant_rate = len(new_entrants) / len(current_actors) if current_actors else 0.0
            persistence_rate = len(persisting) / len(prev_actors) if prev_actors else 0.0

        result.append({
            "year": year,
            "new_entrant_rate": round(new_entrant_rate, 4),
            "persistence_rate": round(persistence_rate, 4),
            "total_actors": len(current_actors),
        })

        prev_actors = current_actors

    return result


def _compute_technology_breadth(
    cpc_by_year: dict[int, list[str]],
) -> list[dict[str, Any]]:
    """Technologie-Breite pro Jahr (Leydesdorff et al. 2015).

    Zwei Granularitaeten:
    - unique_cpc_sections: CPC-Sektionen (A-H, grob, max 9)
    - unique_cpc_subclasses: CPC-Subklassen (Level 4, z.B. H01L, feinkoernig)
    """
    result: list[dict[str, Any]] = []

    for year in sorted(cpc_by_year.keys()):
        sections: set[str] = set()
        subclasses: set[str] = set()
        for cpc_str in cpc_by_year[year]:
            for code in cpc_str.split(","):
                code = code.strip()
                if code:
                    sections.add(code[0])
                    if len(code) >= 4:
                        subclasses.add(code[:4])

        result.append({
            "year": year,
            "unique_cpc_sections": len(sections),
            "unique_cpc_subclasses": len(subclasses),
        })

    return result


def _compute_actor_timeline(
    actors_by_year: dict[int, dict[str, int]], top_n: int = 10
) -> list[dict[str, Any]]:
    """Top-N Akteure mit ihren aktiven Jahren."""
    total_counts: dict[str, int] = {}
    actor_years: dict[str, list[int]] = {}

    for year, actors in actors_by_year.items():
        for name, count in actors.items():
            total_counts[name] = total_counts.get(name, 0) + count
            if name not in actor_years:
                actor_years[name] = []
            actor_years[name].append(year)

    top_actors = sorted(total_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]

    return [
        {
            "name": name,
            "years_active": sorted(actor_years.get(name, [])),
            "total_count": count,
        }
        for name, count in top_actors
    ]


def _compute_programme_evolution(
    instrument_data: list[dict[str, str | int | float]],
) -> list[dict[str, Any]]:
    """Programm-Verteilung pro Jahr (fuer Stacked Area Chart)."""
    by_year: dict[int, dict[str, int]] = {}
    for row in instrument_data:
        year = int(row.get("year", 0))
        scheme = str(row.get("scheme", ""))
        count = int(row.get("count", 0))
        if year not in by_year:
            by_year[year] = {}
        by_year[year][scheme] = by_year[year].get(scheme, 0) + count

    return [
        {"year": year, **counts}
        for year, counts in sorted(by_year.items())
    ]
