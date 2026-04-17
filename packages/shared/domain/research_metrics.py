"""Reine Berechnungsfunktionen fuer Research Impact (UC7).

Alle Funktionen sind zustandslos und ohne I/O -- testbar und auditierbar.

v3.4.8 (Bundle A): Fix fuer C-012 / M-008 / M-009 / M-010 / C5.2:
* ``_compute_citation_trend`` liefert ``total_citations``, ``publication_count``
  und ``avg_citations`` -- bisher nur ``citations``/``paper_count``. Zusaetzlich
  optionales Padding ueber einen Ziel-Jahresbereich (``start_year``/``end_year``),
  damit das Frontend konsistente Zeitreihen rendern kann.
* ``_compute_venue_distribution`` liefert ``name``, ``publication_count``,
  ``avg_citations``, ``h_index`` und ``share`` -- bisher fehlten
  ``avg_citations`` und ``h_index`` komplett.
* ``_compute_publication_types`` liefert jetzt zusaetzlich ``share`` pro Typ.
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


def _compute_citation_trend(
    papers: list[dict[str, Any]],
    *,
    start_year: int | None = None,
    end_year: int | None = None,
) -> list[dict[str, Any]]:
    """Zitationen und Paper-Anzahl pro Jahr.

    Liefert pro Eintrag ``total_citations``, ``publication_count`` und
    ``avg_citations``. Wenn ``start_year``/``end_year`` gesetzt sind, werden
    fehlende Jahre mit Null-Eintraegen aufgefuellt (Bug C5.2).

    Args:
        papers: Semantic-Scholar Paper-Dicts mit ``year`` und ``citationCount``.
        start_year: Optionales Startjahr fuer Padding (inklusiv).
        end_year: Optionales Endjahr fuer Padding (inklusiv).

    Returns:
        Sortierte Liste (aufsteigend nach Jahr).
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

    # --- Padding ueber Zielbereich ---
    if start_year is not None and end_year is not None and start_year <= end_year:
        for y in range(start_year, end_year + 1):
            by_year.setdefault(y, {"citations": 0, "paper_count": 0})

    result: list[dict[str, Any]] = []
    for y, d in sorted(by_year.items()):
        count = int(d["paper_count"])
        total = int(d["citations"])
        avg = round(total / count, 2) if count > 0 else 0.0
        result.append({
            "year": y,
            "total_citations": total,
            "publication_count": count,
            "avg_citations": avg,
            # Kompat-Felder fuer Alt-Konsumenten:
            "citations": total,
            "paper_count": count,
        })
    return result


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
            "citation_count": p.get("citationCount", 0) or 0,
            "authors": authors_short,
            "authors_short": authors_short,
            "doi": (p.get("externalIds", {}) or {}).get("DOI", "") if p.get("externalIds") else "",
            "is_open_access": bool(p.get("isOpenAccess", False)),
        })
    return result


def _compute_venue_distribution(
    papers: list[dict[str, Any]], top_n: int = 8
) -> list[dict[str, Any]]:
    """Top-Venues nach Anzahl der Paper.

    Berechnet pro Venue:
    * ``publication_count`` -- Anzahl Papers in der Venue.
    * ``avg_citations``     -- durchschnittliche Zitationen pro Paper (M-009).
    * ``h_index``           -- h-Index beschraenkt auf die Paper der Venue (M-010).
    * ``share``             -- Anteil an allen Papers mit Venue.
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
        avg = round(total_cit / count, 2) if count > 0 else 0.0
        h_idx = _compute_h_index(citations_list)
        result.append({
            "name": venue,
            "venue": venue,
            "publication_count": count,
            "count": count,
            "avg_citations": avg,
            "h_index": h_idx,
            "share": round(count / total, 4) if total > 0 else 0.0,
        })
    return result


def _compute_publication_types(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Publikationstypen zaehlen und Anteil berechnen.

    Bug C-012: ``share`` pro Typ = ``count / total_types`` -- bisher fehlte
    das Feld vollstaendig, der Mapper hat es dann auf 0 gesetzt.
    """
    counts: dict[str, int] = {}
    for p in papers:
        types = p.get("publicationTypes") or []
        if isinstance(types, str):
            types = [types]
        for t in types:
            if t:
                counts[t] = counts.get(t, 0) + 1

    total = sum(counts.values())
    return [
        {
            "type": t,
            "count": c,
            "share": round(c / total, 4) if total > 0 else 0.0,
        }
        for t, c in sorted(counts.items(), key=lambda x: x[1], reverse=True)
    ]
