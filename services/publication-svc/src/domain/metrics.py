"""UC-C-spezifische Metriken: Publikations-Impact-Chain.

Reine Funktionen fuer die Berechnung von Publikations-Effizienz-Metriken
aus CORDIS-Projektdaten. Keine Seiteneffekte, keine I/O.
"""

from __future__ import annotations


def compute_pubs_per_million(ec_contribution: float, pub_count: int) -> float:
    """Publikationen pro Million EUR Foerderung.

    Args:
        ec_contribution: EU-Foerderbeitrag in EUR.
        pub_count: Anzahl der Publikationen.

    Returns:
        Publikationen pro Million EUR, gerundet auf 2 Dezimalstellen.
        0.0 wenn ec_contribution <= 0.
    """
    if ec_contribution <= 0:
        return 0.0
    return round(pub_count / (ec_contribution / 1_000_000), 2)


def compute_pubs_per_project(total_pubs: int, total_projects: int) -> float:
    """Durchschnittliche Publikationen pro Projekt.

    Args:
        total_pubs: Gesamtanzahl der Publikationen.
        total_projects: Gesamtanzahl der Projekte mit Publikationen.

    Returns:
        Durchschnittliche Publikationen pro Projekt, gerundet auf 1 Dezimalstelle.
        0.0 wenn total_projects <= 0.
    """
    if total_projects <= 0:
        return 0.0
    return round(total_pubs / total_projects, 1)
