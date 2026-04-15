"""
UC11-spezifische Metriken: Akteur-Typ-Verteilung.

CORDIS activity_type Codes:
- HES: Higher Education Establishment
- PRC: Private for-profit (Company/SME)
- REC: Research Organisation
- OTH: Other
- PUB: Public Body
"""

from __future__ import annotations

from typing import Any

# Menschenlesbare Labels fuer Organisationstypen
ACTIVITY_TYPE_LABELS: dict[str, str] = {
    "HES": "Higher Education",
    "PRC": "KMU / Unternehmen",
    "REC": "Research Organisation",
    "OTH": "Other",
    "PUB": "Public Body",
}


def compute_type_breakdown(
    raw_counts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Organisationstypen aggregieren mit Anteilen.

    Erwartet Eintraege: {activity_type, actor_count, project_count, funding}.
    """
    total_actors = sum(int(r.get("actor_count", 0)) for r in raw_counts)
    total_activity = sum(
        int(r.get("actor_count", 0)) + int(r.get("project_count", 0))
        for r in raw_counts
    )

    result: list[dict[str, Any]] = []
    for r in raw_counts:
        atype = str(r.get("activity_type", "OTH"))
        actor_count = int(r.get("actor_count", 0))
        project_count = int(r.get("project_count", 0))
        activity = actor_count + project_count

        result.append({
            "type": atype,
            "label": ACTIVITY_TYPE_LABELS.get(atype, atype),
            "actor_count": actor_count,
            "project_count": project_count,
            "funding_eur": float(r.get("funding", 0.0)),
            "actor_share": round(actor_count / total_actors, 4) if total_actors > 0 else 0.0,
            "activity_share": round(activity / total_activity, 4) if total_activity > 0 else 0.0,
        })

    result.sort(key=lambda x: x["actor_count"], reverse=True)
    return result


def compute_sme_share(
    sme_count: int,
    total_prc: int,
) -> float:
    """SME-Anteil unter PRC-Akteuren."""
    if total_prc <= 0:
        return 0.0
    return round(sme_count / total_prc, 4)
