"""Master-Definitionen fuer Patent-Zaehlungen (Bug CRIT-4).

Hintergrund: `total_patents` im Header und `total_applications` in UC12 wurden
im Live-System nicht konsistent getrennt. Dieses Modul definiert drei kanonische
Scopes und die EPO/USPTO-Kind-Code-Listen, die Applications von Grants trennen.

Kind-Code-Referenz (EPO/USPTO/WO):
    A, A1, A2, A3, A4, A8, A9 → Application (Offenlegungsschrift / vor Erteilung).
    B, B1, B2, B3, B4, B8, B9 → Grant (erteiltes Patent / Correction nach Erteilung).

Scope-Mapping (dokumentarisch):
    ALL_PATENTS        → ``patent_schema.patents`` ohne Kind-Code-Filter.
                         Genutzt vom Header (`total_patents`).
    APPLICATIONS_ONLY  → ``patent_schema.patents`` WHERE kind IN APPLICATION_KIND_CODES.
                         Genutzt von UC12 (`total_applications`).
    GRANTS_ONLY        → ``patent_schema.patents`` WHERE kind IN GRANT_KIND_CODES.
                         Genutzt von UC12 (`total_grants`).

Plausibilitaet: ``ALL_PATENTS >= APPLICATIONS_ONLY + GRANTS_ONLY`` (Rest sind
unbekannte/nicht-klassifizierte Kind-Codes).
"""

from __future__ import annotations

from enum import Enum


class PatentScope(Enum):
    """Kanonischer Scope fuer Patent-Zaehlungen."""

    ALL_PATENTS = "all_patents"
    APPLICATIONS_ONLY = "applications_only"
    GRANTS_ONLY = "grants_only"


APPLICATION_KIND_CODES: frozenset[str] = frozenset({
    "A", "A1", "A2", "A3", "A4", "A8", "A9",
})
"""EPO/USPTO Kind-Codes fuer Applications (Offenlegungsschrift)."""

GRANT_KIND_CODES: frozenset[str] = frozenset({
    "B", "B1", "B2", "B3", "B4", "B8", "B9",
})
"""EPO/USPTO Kind-Codes fuer Grants (erteiltes Patent)."""


_LABELS: dict[PatentScope, str] = {
    PatentScope.ALL_PATENTS: "Patente (alle)",
    PatentScope.APPLICATIONS_ONLY: "Patent-Anmeldungen",
    PatentScope.GRANTS_ONLY: "Erteilte Patente",
}


def canonical_patent_label(scope: PatentScope) -> str:
    """Kurzes deutsches Label fuer UI/Logs.

    Args:
        scope: Element des ``PatentScope``-Enums.

    Returns:
        Lesbares Label (z.B. "Patent-Anmeldungen").

    Raises:
        TypeError: wenn ``scope`` kein ``PatentScope`` ist.
    """
    if not isinstance(scope, PatentScope):
        raise TypeError(
            f"scope muss PatentScope sein, nicht {type(scope).__name__}"
        )
    return _LABELS[scope]


__all__ = [
    "APPLICATION_KIND_CODES",
    "GRANT_KIND_CODES",
    "PatentScope",
    "canonical_patent_label",
]
