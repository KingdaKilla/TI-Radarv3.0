"""UC10-spezifische Metriken: Interdisziplinaritaet und Taxonomie.

Shannon-Index, Simpson-Index und Rao-Stirling-Diversitaet
fuer die EuroSciVoc-Disziplin-Verteilung.
"""

from __future__ import annotations

import math
from typing import Any


def compute_shannon_index(counts: dict[str, int]) -> float:
    """Shannon-Diversitaetsindex fuer Disziplin-Verteilung."""
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    shannon = 0.0
    for count in counts.values():
        if count > 0:
            p = count / total
            shannon -= p * math.log2(p)
    return round(shannon, 4)


def compute_simpson_index(counts: dict[str, int]) -> float:
    """Simpson-Diversitaetsindex (1 - D)."""
    total = sum(counts.values())
    if total <= 1:
        return 0.0
    d = sum(c * (c - 1) for c in counts.values()) / (total * (total - 1))
    return round(1.0 - d, 4)


def compute_jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Jaccard-Aehnlichkeit zweier Disziplin-Sets."""
    if not set_a and not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def build_discipline_tree(
    nodes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Hierarchischen Baum aus flacher EuroSciVoc-Knotenliste bauen.

    Erwartet Eintraege mit: id, label, parent_id, level, count.
    Gibt Wurzel-Knoten mit verschachtelten children zurueck.
    """
    node_map: dict[str, dict[str, Any]] = {}
    for n in nodes:
        node_id = str(n["id"])
        node_map[node_id] = {
            "id": node_id,
            "label": str(n.get("label", "")),
            "value": float(n.get("count", n.get("project_count", 0))),
            "share": float(n.get("share", 0.0)),
            "level": str(n.get("level", "")),
            "children": [],
        }

    roots: list[dict[str, Any]] = []
    for n in nodes:
        node_id = str(n["id"])
        parent_id = str(n.get("parent_id", ""))
        if parent_id and parent_id in node_map:
            node_map[parent_id]["children"].append(node_map[node_id])
        else:
            roots.append(node_map[node_id])

    return roots


def classify_interdisciplinarity(
    shannon: float,
    active_fields: int,
) -> bool:
    """Prueft ob die Technologie als interdisziplinaer gilt.

    Schwellenwert: Shannon > 2.0 ODER aktive Felder >= 3.
    """
    return shannon > 2.0 or active_fields >= 3
