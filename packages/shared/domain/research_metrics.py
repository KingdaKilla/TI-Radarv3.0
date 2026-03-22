"""Reine Berechnungsfunktionen fuer Research Impact (UC7).

Alle Funktionen sind zustandslos und ohne I/O — testbar und auditierbar.
"""

from __future__ import annotations

from typing import Any


def _compute_h_index(citations: list[int]) -> int:
    """h-Index: groesster Wert h so dass h Paper >= h Zitationen haben."""
    sorted_c = sorted(citations, reverse=True)
    h = 0
    for i, c in enumerate(sorted_c):
        if c >= i + 1:
            h = i + 1
        else:
            break
    return h


def _compute_citation_trend(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Zitationen und Paper-Anzahl pro Jahr."""
    by_year: dict[int, dict[str, int]] = {}
    for p in papers:
        year = p.get("year")
        if not year:
            continue
        if year not in by_year:
            by_year[year] = {"citations": 0, "paper_count": 0}
        by_year[year]["citations"] += p.get("citationCount", 0) or 0
        by_year[year]["paper_count"] += 1

    return [
        {"year": y, "citations": d["citations"], "paper_count": d["paper_count"]}
        for y, d in sorted(by_year.items())
    ]


def _compute_top_papers(
    papers: list[dict[str, Any]], top_n: int = 10
) -> list[dict[str, Any]]:
    """Top-N Paper nach Zitationen sortiert."""
    sorted_papers = sorted(papers, key=lambda p: p.get("citationCount", 0) or 0, reverse=True)
    result: list[dict[str, Any]] = []
    for p in sorted_papers[:top_n]:
        authors = p.get("authors", []) or []
        authors_short = ", ".join(a.get("name", "") for a in authors[:3])
        if len(authors) > 3:
            authors_short += " et al."
        result.append({
            "title": p.get("title", ""),
            "venue": p.get("venue", ""),
            "year": p.get("year", 0),
            "citations": p.get("citationCount", 0) or 0,
            "authors_short": authors_short,
        })
    return result


def _compute_venue_distribution(
    papers: list[dict[str, Any]], top_n: int = 8
) -> list[dict[str, Any]]:
    """Top-Venues nach Anzahl der Paper."""
    counts: dict[str, int] = {}
    for p in papers:
        venue = p.get("venue") or ""
        if venue:
            counts[venue] = counts.get(venue, 0) + 1

    total = sum(counts.values())
    sorted_venues = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [
        {
            "venue": v,
            "count": c,
            "share": round(c / total, 4) if total > 0 else 0.0,
        }
        for v, c in sorted_venues[:top_n]
    ]


def _compute_publication_types(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Publikationstypen zaehlen."""
    counts: dict[str, int] = {}
    for p in papers:
        types = p.get("publicationTypes") or []
        for t in types:
            if t:
                counts[t] = counts.get(t, 0) + 1

    return [
        {"type": t, "count": c}
        for t, c in sorted(counts.items(), key=lambda x: x[1], reverse=True)
    ]
