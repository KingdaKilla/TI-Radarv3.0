"""Reciprocal Rank Fusion (Cormack et al. 2009).

Kombiniert mehrere Ranking-Listen zu einem einzigen Fused-Ranking.
RRF-Score fuer Dokument d: SUM(1 / (k + rank(d))) ueber alle Listen,
wobei rank 1-basiert ist (erstes Element hat rank=1).
"""
from __future__ import annotations


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]],
    k: int = 60,
    top_n: int | None = None,
) -> list[tuple[str, float]]:
    """Fusioniert mehrere gerankte Listen via RRF.

    Args:
        ranked_lists: Liste von geordneten Doc-ID-Listen (hoechster Rang zuerst).
        k: RRF-Daempfungsparameter (Standard: 60, nach Cormack et al. 2009).
        top_n: Optionale Begrenzung der Ergebnisgroesse.

    Returns:
        Sortierte Liste von (doc_id, rrf_score) Tupeln, absteigend nach Score.
    """
    scores: dict[str, float] = {}

    for ranked_list in ranked_lists:
        for rank_zero_based, doc_id in enumerate(ranked_list):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank_zero_based + 1)

    result = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    if top_n is not None:
        result = result[:top_n]

    return result
