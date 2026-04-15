"""Jahres-Vollstaendigkeit — Helfer fuer CAGR/S-Fit/Zeitreihen.

Bug MAJ-7 und MAJ-8 entstanden, weil Services das laufende (unvollstaendige)
Kalenderjahr in CAGR- und S-Kurven-Berechnungen einbezogen haben. Ein Jahr `Y`
gilt genau dann als vollstaendig abgeschlossen, wenn `today >= date(Y + 1, 1, 1)`.

Diese Helfer liefern eine einheitliche Definition, auf die alle Panels (Landscape,
Maturity, Publication, Research-Impact, Temporal) verweisen koennen.
"""

from __future__ import annotations

from datetime import date


def last_complete_year(today: date | None = None) -> int:
    """Letztes vollstaendig abgeschlossenes Kalenderjahr.

    Args:
        today: Referenzdatum; wenn ``None``, wird ``date.today()`` genutzt.

    Returns:
        Das Vorjahr von ``today`` (z.B. 2026-04-14 → 2025).

    Beispiel:
        >>> last_complete_year(date(2026, 4, 14))
        2025
        >>> last_complete_year(date(2027, 1, 1))
        2026
    """
    ref = today if today is not None else date.today()
    return ref.year - 1


def is_year_complete(year: int, today: date | None = None) -> bool:
    """Prueft, ob ``year`` zum Stichtag ``today`` vollstaendig abgeschlossen ist.

    Ein Jahr ``Y`` ist genau dann abgeschlossen, wenn ``today >= date(Y + 1, 1, 1)``.
    Das laufende Jahr ist nie abgeschlossen (auch am 31.12. nicht).

    Args:
        year: Zu pruefendes Kalenderjahr.
        today: Referenzdatum; wenn ``None``, wird ``date.today()`` genutzt.

    Returns:
        ``True`` wenn ``year`` < ``today.year`` (i.e. streng kleiner).
    """
    ref = today if today is not None else date.today()
    return ref >= date(year + 1, 1, 1)


def clip_to_complete_years(
    years: list[int],
    today: date | None = None,
) -> list[int]:
    """Entfernt unvollstaendige Jahre aus der Liste, Reihenfolge bleibt erhalten.

    Zukunftsjahre und das laufende Jahr werden verworfen. Duplikate werden
    nicht dedupliziert (falls bewusst in der Eingabe).

    Args:
        years: Liste von Jahreszahlen (kann unsortiert sein).
        today: Referenzdatum; wenn ``None``, wird ``date.today()`` genutzt.

    Returns:
        Neue Liste mit nur vollstaendigen Jahren, Reihenfolge wie Eingabe.
    """
    ref = today if today is not None else date.today()
    return [y for y in years if is_year_complete(y, ref)]


__all__ = [
    "clip_to_complete_years",
    "is_year_complete",
    "last_complete_year",
]
