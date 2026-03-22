"""Port-Interfaces (ABCs) fuer Repository- und Adapter-Abstraktionen.

Definiert die Vertraege, die Infrastructure-Adapter implementieren muessen.
Use Cases haengen nur von diesen Ports ab, nicht von konkreten Implementierungen.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from shared.domain.result_types import CountryCount, CpcCount, FundingYear, YearCount


class PatentQueryPort(ABC):
    """Port: Patent-Datenabfragen."""

    @abstractmethod
    async def count_patents_by_year(
        self, technology: str, *, start_year: int, end_year: int,
        european_only: bool = False,
    ) -> list[YearCount]: ...

    @abstractmethod
    async def count_patents_by_country(
        self, technology: str, *, start_year: int, end_year: int,
        european_only: bool = False, limit: int = 20,
    ) -> list[CountryCount]: ...

    @abstractmethod
    async def top_cpc_codes(
        self, technology: str, *, start_year: int, end_year: int, limit: int = 15,
    ) -> list[CpcCount]: ...


class ProjectQueryPort(ABC):
    """Port: CORDIS-Projekt-Datenabfragen."""

    @abstractmethod
    async def count_projects_by_year(
        self, technology: str, *, start_year: int, end_year: int,
    ) -> list[YearCount]: ...

    @abstractmethod
    async def count_projects_by_country(
        self, technology: str, *, start_year: int, end_year: int,
        european_only: bool = False, limit: int = 20,
    ) -> list[CountryCount]: ...

    @abstractmethod
    async def funding_by_year(
        self, technology: str, *, start_year: int, end_year: int,
    ) -> list[FundingYear]: ...


class PublicationQueryPort(ABC):
    """Port: Externe Publikations-API."""

    @abstractmethod
    async def count_by_year(
        self, technology: str, start_year: int, end_year: int,
    ) -> list[YearCount]: ...
