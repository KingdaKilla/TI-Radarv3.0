"""UC8-spezifische Metriken und Hilfsfunktionen.

Lokaler Fallback fuer shared.domain.temporal_metrics,
falls das shared-Package nicht im PYTHONPATH liegt.
"""

from __future__ import annotations

import math
from typing import Any


def compute_actor_dynamics(
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
            new_entrants = len(current_actors)
            persistent = 0
            exited = 0
            churn_rate = 0.0
            persistence_ratio = 0.0
        else:
            new_set = current_actors - prev_actors
            persist_set = current_actors & prev_actors
            exit_set = prev_actors - current_actors
            new_entrants = len(new_set)
            persistent = len(persist_set)
            exited = len(exit_set)
            churn_rate = exited / len(prev_actors) if prev_actors else 0.0
            persistence_ratio = persistent / len(current_actors) if current_actors else 0.0

        result.append({
            "year": year,
            "new_entrants": new_entrants,
            "persistent_actors": persistent,
            "exited_actors": exited,
            "total_active": len(current_actors),
            "churn_rate": round(churn_rate, 4),
            "persistence_ratio": round(persistence_ratio, 4),
        })

        prev_actors = current_actors

    return result


def compute_technology_breadth(
    cpc_by_year: dict[int, list[str]],
) -> list[dict[str, Any]]:
    """Technologie-Breite pro Jahr (Shannon-Index, Herfindahl).

    Zwei Granularitaeten:
    - unique_cpc_codes: CPC-Subklassen (Level 4, z.B. H01L)
    - shannon_index: Shannon-Diversitaetsindex
    - herfindahl_index: Herfindahl-Konzentration
    """
    result: list[dict[str, Any]] = []
    seen_codes: set[str] = set()

    for year in sorted(cpc_by_year.keys()):
        code_counts: dict[str, int] = {}
        for cpc_str in cpc_by_year[year]:
            for code in cpc_str.split(","):
                code = code.strip()
                if code and len(code) >= 4:
                    sub = code[:4]
                    code_counts[sub] = code_counts.get(sub, 0) + 1

        total = sum(code_counts.values())
        unique = len(code_counts)

        # Shannon-Index
        shannon = 0.0
        if total > 0:
            for count in code_counts.values():
                p = count / total
                if p > 0:
                    shannon -= p * math.log2(p)

        # Herfindahl
        herfindahl = 0.0
        if total > 0:
            for count in code_counts.values():
                p = count / total
                herfindahl += p * p

        # Neue Codes
        current_codes = set(code_counts.keys())
        new_codes = len(current_codes - seen_codes)
        seen_codes |= current_codes

        result.append({
            "year": year,
            "unique_cpc_codes": unique,
            "shannon_index": round(shannon, 4),
            "herfindahl_index": round(herfindahl, 4),
            "new_codes": new_codes,
        })

    return result


def compute_actor_timeline(
    actors_by_year: dict[int, dict[str, int]], top_n: int = 10,
) -> list[dict[str, Any]]:
    """Top-N Akteure mit ihren aktiven Jahren und Persistenz-Typ."""
    total_counts: dict[str, int] = {}
    actor_years: dict[str, list[int]] = {}

    for year, actors in actors_by_year.items():
        for name, count in actors.items():
            total_counts[name] = total_counts.get(name, 0) + count
            if name not in actor_years:
                actor_years[name] = []
            actor_years[name].append(year)

    top_actors = sorted(total_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]

    result: list[dict[str, Any]] = []
    for name, count in top_actors:
        years = sorted(actor_years.get(name, []))
        active_count = len(years)

        # Persistenz-Typ bestimmen
        if active_count == 1:
            persistence = "ONE_TIMER"
        elif active_count <= 4:
            persistence = "OCCASIONAL"
        else:
            persistence = "PERSISTENT"

        result.append({
            "actor_name": name,
            "persistence_type": persistence,
            "first_active_year": years[0] if years else 0,
            "last_active_year": years[-1] if years else 0,
            "active_years_count": active_count,
            "total_count": count,
        })

    return result


def compute_programme_evolution(
    instrument_data: list[dict[str, str | int | float]],
) -> list[dict[str, Any]]:
    """Programm-Verteilung pro Jahr (fuer Stacked Area Chart)."""
    by_year: dict[int, dict[str, dict[str, float]]] = {}
    for row in instrument_data:
        year = int(row.get("year", 0))
        programme = str(row.get("scheme", row.get("programme", "")))
        count = int(row.get("count", 0))
        funding = float(row.get("funding", 0.0))
        if year not in by_year:
            by_year[year] = {}
        if programme not in by_year[year]:
            by_year[year][programme] = {"count": 0, "funding": 0.0}
        by_year[year][programme]["count"] += count
        by_year[year][programme]["funding"] += funding

    result: list[dict[str, Any]] = []
    for year in sorted(by_year.keys()):
        for programme, data in by_year[year].items():
            result.append({
                "year": year,
                "programme": programme,
                "project_count": int(data["count"]),
                "funding_eur": data["funding"],
            })
    return result


def compute_dynamics_summary(
    actors_by_year: dict[int, dict[str, int]],
) -> dict[str, Any]:
    """Zusammenfassung der Akteur-Dynamik."""
    all_actors: dict[str, list[int]] = {}
    for year, actors in actors_by_year.items():
        for name in actors:
            if name not in all_actors:
                all_actors[name] = []
            all_actors[name].append(year)

    total = len(all_actors)
    lifespans = [max(years) - min(years) + 1 for years in all_actors.values()] if all_actors else []
    persistent = sum(1 for ls in lifespans if ls >= 5)
    one_timers = sum(1 for ls in lifespans if ls == 1)
    avg_lifespan = sum(lifespans) / len(lifespans) if lifespans else 0.0

    sorted_ls = sorted(lifespans)
    mid = len(sorted_ls) // 2
    if len(sorted_ls) % 2 == 0 and len(sorted_ls) >= 2:
        median_lifespan = (sorted_ls[mid - 1] + sorted_ls[mid]) / 2.0
    elif sorted_ls:
        median_lifespan = float(sorted_ls[mid])
    else:
        median_lifespan = 0.0

    # --- Aufkommende / Abnehmende Themen (Akteur-basiert) ---
    # Akteure, die erst in den letzten 2 Jahren aufgetaucht sind => "emerging"
    # Akteure, die in den letzten 2 Jahren verschwunden sind => "declining"
    emerging: list[str] = []
    declining: list[str] = []
    if sorted_years := sorted(actors_by_year.keys()):
        recent_cutoff = sorted_years[-1] - 1  # last 2 years
        early_cutoff = sorted_years[-1] - 2   # years before that

        for actor_name, years_list in all_actors.items():
            min_y = min(years_list)
            max_y = max(years_list)
            if min_y >= recent_cutoff and len(years_list) >= 1:
                # Actor appeared only recently
                emerging.append(actor_name)
            elif max_y <= early_cutoff and len(years_list) >= 2:
                # Actor was active before but disappeared
                declining.append(actor_name)

        # Sort by activity count descending, keep top 10
        emerging_set = set(emerging)
        declining_set = set(declining)
        emerging_counts = {a: sum(actors_by_year.get(y, {}).get(a, 0) for y in yrs)
                          for a, yrs in all_actors.items() if a in emerging_set}
        declining_counts = {a: sum(actors_by_year.get(y, {}).get(a, 0) for y in yrs)
                           for a, yrs in all_actors.items() if a in declining_set}
        emerging = sorted(emerging, key=lambda a: emerging_counts.get(a, 0), reverse=True)[:10]
        declining = sorted(declining, key=lambda a: declining_counts.get(a, 0), reverse=True)[:10]

    return {
        "total_actors": total,
        "persistent_count": persistent,
        "one_timer_count": one_timers,
        "avg_lifespan_years": round(avg_lifespan, 2),
        "median_lifespan_years": round(median_lifespan, 2),
        "emerging": emerging,
        "declining": declining,
    }
