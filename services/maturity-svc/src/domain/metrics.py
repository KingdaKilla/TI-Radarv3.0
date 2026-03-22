"""UC2-spezifische Metriken und Hilfsfunktionen.

Re-exportiert Kernfunktionen aus shared.domain.metrics und shared.domain.scurve.
UC2-spezifisch: fit_best_model (Stub-Fallback fuer shared.domain.scurve).
"""

from __future__ import annotations

from typing import Any

from shared.domain.metrics import (  # noqa: F401
    cagr,
    classify_maturity_phase,
    detect_decline,
    s_curve_confidence,
)


def fit_best_model(
    years: list[int],
    cumulative: list[int],
) -> dict[str, Any] | None:
    """Fallback S-Curve-Fit (verwendet shared.domain.scurve wenn verfuegbar).

    Diese lokale Version gibt None zurueck — der eigentliche Fit
    kommt aus shared.domain.scurve.fit_best_model.
    """
    # Dieser Fallback wird nur erreicht wenn weder shared noch scipy verfuegbar
    return None
