"""UC7-spezifische Metriken und Hilfsfunktionen.

Lokaler Fallback fuer shared.domain.research_metrics,
falls das shared-Package nicht im PYTHONPATH liegt.
"""

from __future__ import annotations

from typing import Any


def compute_h_index(citations: list[int]) -> int:
    """h-Index: groesster Wert h so dass h Paper >= h Zitationen haben (Hirsch 2005)."""
    sorted_c = sorted(citations, reverse=True)
    h = 0
    for i, c in enumerate(sorted_c):
        if c >= i + 1:
            h = i + 1
        else:
            break
    return h


def compute_i10_index(citations: list[int]) -> int:
    """i10-Index: Anzahl Publikationen mit >= 10 Zitationen."""
    return sum(1 for c in citations if c >= 10)


def compute_citation_trend(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
        {
            "year": y,
            "total_citations": d["citations"],
            "publication_count": d["paper_count"],
            "avg_citations": round(d["citations"] / d["paper_count"], 2) if d["paper_count"] > 0 else 0.0,
        }
        for y, d in sorted(by_year.items())
    ]


def compute_top_papers(
    papers: list[dict[str, Any]], top_n: int = 10,
) -> list[dict[str, Any]]:
    """Top-N Paper nach Zitationen sortiert."""
    sorted_papers = sorted(papers, key=lambda p: p.get("citationCount", 0) or 0, reverse=True)
    result: list[dict[str, Any]] = []
    for p in sorted_papers[:top_n]:
        authors = p.get("authors", []) or []
        authors_short = ", ".join(a.get("name", "") for a in authors[:5])
        if len(authors) > 5:
            authors_short += " et al."
        result.append({
            "title": p.get("title", ""),
            "authors": authors_short,
            "venue": p.get("venue", ""),
            "year": p.get("year", 0),
            "citation_count": p.get("citationCount", 0) or 0,
            "doi": p.get("externalIds", {}).get("DOI", "") if p.get("externalIds") else "",
            "is_open_access": p.get("isOpenAccess", False),
        })
    return result


def compute_venue_distribution(
    papers: list[dict[str, Any]], top_n: int = 8,
) -> list[dict[str, Any]]:
    """Top-Venues nach Anzahl der Paper."""
    counts: dict[str, dict[str, int | float]] = {}
    for p in papers:
        venue = p.get("venue") or ""
        if not venue:
            continue
        if venue not in counts:
            counts[venue] = {"count": 0, "total_citations": 0}
        counts[venue]["count"] = int(counts[venue]["count"]) + 1
        counts[venue]["total_citations"] = int(counts[venue]["total_citations"]) + (p.get("citationCount", 0) or 0)

    total = sum(int(v["count"]) for v in counts.values())
    sorted_venues = sorted(counts.items(), key=lambda x: int(x[1]["count"]), reverse=True)

    return [
        {
            "name": v,
            "publication_count": int(d["count"]),
            "avg_citations": round(int(d["total_citations"]) / int(d["count"]), 2) if int(d["count"]) > 0 else 0.0,
            "share": round(int(d["count"]) / total, 4) if total > 0 else 0.0,
        }
        for v, d in sorted_venues[:top_n]
    ]


def compute_publication_types(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Publikationstypen zaehlen."""
    counts: dict[str, int] = {}
    for p in papers:
        pub_type = p.get("publicationTypes") or p.get("type") or ""
        if isinstance(pub_type, list):
            for t in pub_type:
                if t:
                    counts[t] = counts.get(t, 0) + 1
        elif pub_type:
            counts[str(pub_type)] = counts.get(str(pub_type), 0) + 1

    total = sum(counts.values())
    return [
        {
            "type": t,
            "count": c,
            "share": round(c / total, 4) if total > 0 else 0.0,
        }
        for t, c in sorted(counts.items(), key=lambda x: x[1], reverse=True)
    ]
