"""UC7-spezifische Metriken und Hilfsfunktionen.

Lokaler Fallback fuer shared.domain.research_metrics,
falls das shared-Package nicht im PYTHONPATH liegt.

v3.4.8 (Bundle A): Parity mit shared.domain.research_metrics --
``avg_citations``/``share``/``h_index`` werden jetzt konsistent gesetzt
und ``compute_citation_trend`` unterstuetzt Jahr-Padding.
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


def compute_citation_trend(
    papers: list[dict[str, Any]],
    *,
    start_year: int | None = None,
    end_year: int | None = None,
) -> list[dict[str, Any]]:
    """Zitationen und Paper-Anzahl pro Jahr mit optionalem Jahr-Padding.

    Fuellt fehlende Jahre zwischen ``start_year`` und ``end_year`` mit
    Null-Eintraegen auf (Bug C5.2), damit das Frontend konsistente
    Zeitreihen rendern kann.
    """
    by_year: dict[int, dict[str, int]] = {}
    for p in papers:
        year = p.get("year")
        if not year:
            continue
        try:
            year_int = int(year)
        except (TypeError, ValueError):
            continue
        bucket = by_year.setdefault(year_int, {"citations": 0, "paper_count": 0})
        bucket["citations"] += int(p.get("citationCount", 0) or 0)
        bucket["paper_count"] += 1

    if start_year is not None and end_year is not None and start_year <= end_year:
        for y in range(start_year, end_year + 1):
            by_year.setdefault(y, {"citations": 0, "paper_count": 0})

    return [
        {
            "year": y,
            "total_citations": d["citations"],
            "publication_count": d["paper_count"],
            "avg_citations": (
                round(d["citations"] / d["paper_count"], 2)
                if d["paper_count"] > 0 else 0.0
            ),
            "citations": d["citations"],
            "paper_count": d["paper_count"],
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
    """Top-Venues inklusive ``avg_citations``, ``h_index`` und ``share``.

    * M-009: ``avg_citations`` = total_citations / publication_count
    * M-010: ``h_index`` -- h-Index beschraenkt auf Paper der Venue
    """
    buckets: dict[str, dict[str, Any]] = {}
    for p in papers:
        venue = p.get("venue") or ""
        if not venue:
            continue
        bucket = buckets.setdefault(
            venue, {"count": 0, "total_citations": 0, "citations_list": []},
        )
        citation_count = int(p.get("citationCount", 0) or 0)
        bucket["count"] = int(bucket["count"]) + 1
        bucket["total_citations"] = int(bucket["total_citations"]) + citation_count
        bucket["citations_list"].append(citation_count)

    total = sum(int(b["count"]) for b in buckets.values())
    sorted_venues = sorted(buckets.items(), key=lambda x: int(x[1]["count"]), reverse=True)

    result: list[dict[str, Any]] = []
    for venue, bucket in sorted_venues[:top_n]:
        count = int(bucket["count"])
        total_cit = int(bucket["total_citations"])
        citations_list: list[int] = bucket["citations_list"]
        result.append({
            "name": venue,
            "venue": venue,
            "publication_count": count,
            "count": count,
            "avg_citations": round(total_cit / count, 2) if count > 0 else 0.0,
            "h_index": compute_h_index(citations_list),
            "share": round(count / total, 4) if total > 0 else 0.0,
        })
    return result


def compute_publication_types(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Publikationstypen zaehlen und Anteil pro Typ berechnen (Bug C-012)."""
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
