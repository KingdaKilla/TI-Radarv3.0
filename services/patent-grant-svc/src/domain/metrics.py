"""UC12-spezifische Metriken: Patent Grant Rate.

EPO Kind-Code Klassifikation:
- A1: Published application with search report
- A2: Published application without search report
- A3: Separate search report publication
- B1: Granted patent specification
- B2: Amended after opposition
- B3: Limited after post-grant limitation

Grant Rate = B-Codes / A-Codes (Erteilungsquote).
"""

from __future__ import annotations

from typing import Any

# Single-source-of-truth fuer Kind-Code-Mengen (Bug CRIT-4):
# Die lokalen APPLICATION_CODES / GRANT_CODES wurden durch zentrale Shared-
# Definitionen ersetzt. Alte Namen bleiben als Alias bestehen, damit
# Legacy-Importe weiter funktionieren.
from shared.domain.patent_definitions import (
    APPLICATION_KIND_CODES as APPLICATION_CODES,
    GRANT_KIND_CODES as GRANT_CODES,
)


# Kind-Code Beschreibungen
# EPO-Daten enthalten sowohl vollstaendige Codes (A1, B2) als auch
# Kurzformen (A, B) aus verschiedenen Patentaemtern.
KIND_CODE_DESCRIPTIONS: dict[str, str] = {
    "A": "Patent application (generic)",
    "A1": "Application published with search report",
    "A2": "Application published without search report",
    "A3": "Separate publication of search report",
    "A4": "Supplementary search report",
    "A8": "Corrected title page of A document",
    "A9": "Complete reprint of A document",
    "B": "Patent granted (generic)",
    "B1": "Patent granted (no prior A with claims)",
    "B2": "Patent amended after opposition",
    "B3": "Patent limited after post-grant limitation",
    "B4": "Patent granted (European, amended)",
    "B8": "Corrected title page of B document",
    "B9": "Complete reprint of B document",
    "U": "Utility model",
    "D0": "INPADOC reference",
}


def compute_grant_rate(applications: int, grants: int) -> float:
    """Grant Rate als Fraktion [0, 1] berechnen."""
    if applications <= 0:
        return 0.0
    return round(grants / applications, 4)


def classify_kind_code(kind_code: str) -> str:
    """Kind-Code in Kategorie einordnen: APPLICATION, GRANT oder OTHER."""
    code = kind_code.strip().upper()
    if code in APPLICATION_CODES:
        return "APPLICATION"
    if code in GRANT_CODES:
        return "GRANT"
    return "OTHER"


def compute_grant_rate_summary(
    total_applications: int,
    total_grants: int,
    avg_time_to_grant_months: float = 0.0,
    median_time_to_grant_months: float = 0.0,
) -> dict[str, Any]:
    """Zusammenfassung der Grant-Rate-Statistiken."""
    return {
        "total_applications": total_applications,
        "total_grants": total_grants,
        "grant_rate": compute_grant_rate(total_applications, total_grants),
        "avg_time_to_grant_months": round(avg_time_to_grant_months, 1),
        "median_time_to_grant_months": round(median_time_to_grant_months, 1),
    }
