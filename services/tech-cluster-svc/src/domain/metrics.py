"""UC9-spezifische Metriken: Clustering und EU vs Global Vergleich.

Re-exportiert cagr aus shared.domain.metrics.
UC9-spezifisch: compute_cluster_coherence, compute_silhouette_simple.
"""

from __future__ import annotations

from typing import Any

from shared.domain.metrics import cagr  # noqa: F401


def compute_cluster_coherence(
    cpc_co_occurrence: dict[tuple[str, str], int],
    cluster_cpcs: list[str],
) -> float:
    """Cluster-Kohaerenz: Ratio tatsaechlicher zu moeglichen Kanten."""
    if len(cluster_cpcs) < 2:
        return 1.0

    possible_edges = len(cluster_cpcs) * (len(cluster_cpcs) - 1) / 2
    actual_edges = 0
    total_weight = 0

    for i, a in enumerate(cluster_cpcs):
        for b in cluster_cpcs[i + 1:]:
            key = (min(a, b), max(a, b))
            if key in cpc_co_occurrence:
                actual_edges += 1
                total_weight += cpc_co_occurrence[key]

    density = actual_edges / possible_edges if possible_edges > 0 else 0.0
    return round(density, 4)


def compute_silhouette_simple(
    assignments: list[int],
    distances: list[list[float]],
) -> float:
    """Vereinfachter Silhouette-Score.

    Approximation fuer Faelle wo sklearn nicht verfuegbar ist.
    """
    if len(assignments) < 2:
        return 0.0

    n = len(assignments)
    silhouettes: list[float] = []

    for i in range(n):
        cluster_i = assignments[i]

        # Intra-Cluster-Distanz
        same_cluster = [j for j in range(n) if assignments[j] == cluster_i and j != i]
        if not same_cluster:
            silhouettes.append(0.0)
            continue
        a_i = sum(distances[i][j] for j in same_cluster) / len(same_cluster)

        # Naechster Nachbar-Cluster
        other_clusters = set(assignments) - {cluster_i}
        if not other_clusters:
            silhouettes.append(0.0)
            continue

        b_i = float("inf")
        for c in other_clusters:
            c_members = [j for j in range(n) if assignments[j] == c]
            if c_members:
                avg_d = sum(distances[i][j] for j in c_members) / len(c_members)
                b_i = min(b_i, avg_d)

        s_i = (b_i - a_i) / max(a_i, b_i) if max(a_i, b_i) > 0 else 0.0
        silhouettes.append(s_i)

    return round(sum(silhouettes) / len(silhouettes), 4) if silhouettes else 0.0
