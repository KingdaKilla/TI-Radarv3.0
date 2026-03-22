"""Typisierte Domain-Ergebnisobjekte.

Slotted, frozen Dataclasses fuer Abfrageergebnisse.
Vorteile gegenueber dict[str, Any]:
- ~40% weniger Speicher (kein __dict__ pro Instanz)
- Schnellerer Attributzugriff (C-Level Slot Lookup)
- Statische Typpruefung moeglich
- frozen=True garantiert Unveraenderlichkeit
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class YearCount:
    """Anzahl pro Jahr (Patent-/Projekt-/Publikationszeitreihe)."""
    year: int
    count: int


@dataclass(slots=True, frozen=True)
class CountryCount:
    """Anzahl pro Land (ISO-2 Laendercode)."""
    country: str
    count: int


@dataclass(slots=True, frozen=True)
class CpcCount:
    """Anzahl pro CPC-Code mit Beschreibung."""
    code: str
    description: str
    count: int


@dataclass(slots=True, frozen=True)
class FundingYear:
    """Foerdervolumen pro Jahr."""
    year: int
    funding: float
    count: int


@dataclass(slots=True, frozen=True)
class TimeSeriesEntry:
    """Zusammengefuehrter Zeitreihenpunkt (Patent + Projekt + Publikation)."""
    year: int
    patents: int = 0
    projects: int = 0
    publications: int = 0
    funding_eur: float = 0.0


@dataclass(slots=True, frozen=True)
class ActorScore:
    """Akteur mit Aktivitaets-Scores."""
    name: str
    country_code: str
    patent_count: int
    project_count: int
    share: float

    @property
    def total(self) -> int:
        return self.patent_count + self.project_count
