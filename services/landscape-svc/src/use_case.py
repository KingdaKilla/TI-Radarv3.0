"""UC1 AnalyzeLandscape Use Case — transportunabhaengige Geschaeftslogik.

Enthaelt die gesamte Orchestrierung der Landscape-Analyse:
- Parallele Datenabfragen (Repository + OpenAIRE)
- CAGR-Berechnungen
- Zeitreihen- und Laender-Zusammenfuehrung
- Datenquellen-Dokumentation

Keine Abhaengigkeit zu gRPC, Protobuf oder HTTP.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from shared.domain.metrics import cagr, merge_country_data, merge_time_series

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Result Dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class LandscapeResult:
    """Ergebnis einer Landscape-Analyse (UC1).

    Mutable waehrend der Konstruktion (NOT frozen), da Felder
    schrittweise aus parallelen Queries befuellt werden.
    """

    time_series: list[dict[str, Any]] = field(default_factory=list)
    funding_by_year: dict[int, float] = field(default_factory=dict)
    top_countries: list[dict[str, str | int]] = field(default_factory=list)
    top_cpc: list[dict[str, Any]] = field(default_factory=list)

    total_patents: int = 0
    total_projects: int = 0
    total_publications: int = 0
    total_funding: float = 0.0
    active_countries: int = 0

    cagr_patents: float = 0.0
    cagr_projects: float = 0.0
    cagr_publications: float = 0.0
    cagr_funding: float = 0.0
    periods: int = 0

    data_sources: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, str]] = field(default_factory=list)

    processing_time_ms: int = 0


# ---------------------------------------------------------------------------
# Use Case
# ---------------------------------------------------------------------------

class AnalyzeLandscape:
    """Orchestriert die UC1 Landscape-Analyse.

    Transportunabhaengig: nimmt primitive Parameter, gibt LandscapeResult zurueck.
    Keine Abhaengigkeit zu gRPC, Protobuf oder HTTP.

    Args:
        repo: LandscapeRepository (oder beliebiges Objekt mit denselben async-Methoden).
        openaire: OpenAIREAdapter (oder None, wenn keine Publikationsdaten gewuenscht).
    """

    def __init__(self, *, repo: Any, openaire: Any | None = None) -> None:
        self._repo = repo
        self._openaire = openaire

    async def execute(
        self,
        technology: str,
        start_year: int = 2010,
        end_year: int = 2024,
        european_only: bool = False,
        top_n: int = 20,
    ) -> LandscapeResult:
        """Landscape-Analyse ausfuehren.

        Args:
            technology: Suchbegriff fuer Volltextsuche.
            start_year: Erstes Jahr (inklusiv).
            end_year: Letztes Jahr (inklusiv).
            european_only: Nur EU/EEA-Laender beruecksichtigen.
            top_n: Maximale Anzahl Laender/CPC-Codes im Ergebnis.

        Returns:
            LandscapeResult mit allen berechneten Metriken.
        """
        t0 = time.monotonic()
        result = LandscapeResult()

        # --- Parallele Datenabfragen ---
        patent_years: list = []
        patent_countries: list = []
        project_years: list = []
        project_countries: list = []
        publication_years: list = []
        top_cpc: list = []
        total_funding: float = 0.0
        funding_by_year: dict[int, float] = {}

        tasks: list[asyncio.Task[Any]] = []

        # Patent-Daten
        tasks.append(asyncio.create_task(
            self._repo.count_patents_by_year(
                technology, start_year=start_year, end_year=end_year,
                european_only=european_only,
            ),
            name="patent_years",
        ))
        tasks.append(asyncio.create_task(
            self._repo.count_patents_by_country(
                technology, start_year=start_year, end_year=end_year,
                european_only=european_only, limit=top_n,
            ),
            name="patent_countries",
        ))

        # CORDIS Projekt-Daten
        tasks.append(asyncio.create_task(
            self._repo.count_projects_by_year(
                technology, start_year=start_year, end_year=end_year,
            ),
            name="project_years",
        ))
        tasks.append(asyncio.create_task(
            self._repo.count_projects_by_country(
                technology, start_year=start_year, end_year=end_year,
                european_only=european_only, limit=top_n,
            ),
            name="project_countries",
        ))

        # Top CPC-Codes
        tasks.append(asyncio.create_task(
            self._repo.top_cpc_codes(
                technology, start_year=start_year, end_year=end_year,
                limit=min(top_n, 15),
            ),
            name="top_cpc",
        ))

        # Foerderung pro Jahr
        tasks.append(asyncio.create_task(
            self._repo.funding_by_year(
                technology, start_year=start_year, end_year=end_year,
            ),
            name="funding_by_year",
        ))

        # OpenAIRE Publikationen (extern, optional)
        if self._openaire is not None:
            tasks.append(asyncio.create_task(
                self._openaire.count_by_year(technology, start_year, end_year),
                name="publication_years",
            ))

        # --- Alle Tasks ausfuehren ---
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for task, task_result in zip(tasks, results, strict=False):
                name = task.get_name()
                if isinstance(task_result, Exception):
                    logger.warning(
                        "query_fehlgeschlagen", task=name, fehler=str(task_result),
                    )
                    result.warnings.append({
                        "message": f"Query '{name}' fehlgeschlagen: {task_result}",
                        "severity": "MEDIUM",
                        "code": f"QUERY_FAILED_{name.upper()}",
                    })
                    continue

                if name == "patent_years":
                    patent_years = task_result
                elif name == "patent_countries":
                    patent_countries = task_result
                elif name == "project_years":
                    project_years = task_result
                elif name == "project_countries":
                    project_countries = task_result
                elif name == "publication_years":
                    publication_years = task_result
                elif name == "top_cpc":
                    top_cpc = task_result
                elif name == "funding_by_year":
                    for entry in task_result:
                        funding_by_year[entry.year] = entry.funding
                    total_funding = sum(funding_by_year.values())

        # --- Datenquellen dokumentieren ---
        total_patents = sum(y.count for y in patent_years)
        total_projects = sum(y.count for y in project_years)
        total_publications = _sum_counts(publication_years)

        data_sources: list[dict[str, Any]] = []
        if total_patents > 0:
            data_sources.append({
                "name": "EPO DOCDB (PostgreSQL)",
                "type": "PATENT",
                "record_count": total_patents,
            })
        if total_projects > 0:
            data_sources.append({
                "name": "CORDIS (PostgreSQL)",
                "type": "PROJECT",
                "record_count": total_projects,
            })
        if total_publications > 0:
            data_sources.append({
                "name": "OpenAIRE (API)",
                "type": "PUBLICATION",
                "record_count": total_publications,
            })

        # --- Zeitreihen zusammenfuehren ---
        time_series = merge_time_series(
            patent_years, project_years, publication_years, start_year, end_year,
        )

        # --- Laender zusammenfuehren ---
        top_countries = merge_country_data(
            patent_countries, project_countries, limit=top_n,
        )

        # --- CAGR berechnen ---
        periods = end_year - start_year
        cagr_patents = _safe_cagr(patent_years, periods)
        cagr_projects = _safe_cagr(project_years, periods)
        cagr_publications = _safe_cagr(publication_years, periods)
        cagr_funding = _compute_funding_cagr(funding_by_year, start_year, end_year)

        # --- Distinct Countries zaehlen ---
        active_countries = len({str(c["country"]) for c in top_countries})

        # --- Verarbeitungszeit ---
        processing_time_ms = int((time.monotonic() - t0) * 1000)

        logger.info(
            "analyse_abgeschlossen",
            technology=technology,
            patente=total_patents,
            projekte=total_projects,
            publikationen=total_publications,
            laender=active_countries,
            dauer_ms=processing_time_ms,
        )

        # --- Result befuellen ---
        result.time_series = time_series
        result.funding_by_year = funding_by_year
        result.top_countries = top_countries
        result.top_cpc = top_cpc
        result.total_patents = total_patents
        result.total_projects = total_projects
        result.total_publications = total_publications
        result.total_funding = total_funding
        result.active_countries = active_countries
        result.cagr_patents = cagr_patents
        result.cagr_projects = cagr_projects
        result.cagr_publications = cagr_publications
        result.cagr_funding = cagr_funding
        result.periods = periods
        result.data_sources = data_sources
        result.processing_time_ms = processing_time_ms

        return result


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _sum_counts(items: list) -> int:
    """Summe der count-Werte — unterstuetzt sowohl dict als auch Attribut-Zugriff.

    OpenAIRE gibt list[dict] zurueck, Repository gibt list[YearCount] zurueck.
    """
    if not items:
        return 0
    if hasattr(items[0], "count"):
        return sum(item.count for item in items)
    return sum(item["count"] for item in items)


def _get(item: Any, key: str) -> Any:
    """Attribut- oder dict-Zugriff (duck typing fuer OpenAIRE-Dicts vs. typed results)."""
    return getattr(item, key) if hasattr(item, key) else item[key]


def _safe_cagr(
    yearly_data: list,
    periods: int,
    data_complete_year: int = 2025,
) -> float:
    """CAGR sicher berechnen — gibt 0.0 bei unzureichenden Daten zurueck.

    Nimmt den ersten und letzten Datenpunkt (nicht den Zeitraum-Anfang/Ende),
    um CAGR nur ueber tatsaechlich vorhandene Daten zu berechnen.
    Unterstuetzt sowohl dict- als auch Attribut-basierte Eintraege.

    Daten nach data_complete_year werden ignoriert, da unvollstaendige
    Jahrgaenge die CAGR-Berechnung nach unten verzerren wuerden.
    """
    if not yearly_data or periods <= 0:
        return 0.0

    # Nur vollstaendige Jahre beruecksichtigen
    filtered = [x for x in yearly_data if _get(x, "year") <= data_complete_year]
    if not filtered:
        return 0.0

    sorted_data = sorted(filtered, key=lambda x: _get(x, "year"))
    first_val = _get(sorted_data[0], "count")
    last_val = _get(sorted_data[-1], "count")
    actual_periods = _get(sorted_data[-1], "year") - _get(sorted_data[0], "year")

    if actual_periods <= 0:
        return 0.0

    return cagr(float(first_val), float(last_val), actual_periods)


def _compute_funding_cagr(
    funding_by_year: dict[int, float],
    start_year: int,
    end_year: int,
    data_complete_year: int = 2025,
) -> float:
    """CAGR fuer Foerdervolumen berechnen.

    Ueberspringt Jahre ohne Foerderung am Anfang/Ende.
    Daten nach data_complete_year werden ignoriert (unvollstaendig).
    """
    if not funding_by_year:
        return 0.0

    sorted_years = sorted(
        y for y, v in funding_by_year.items()
        if v > 0 and y <= data_complete_year
    )
    if len(sorted_years) < 2:
        return 0.0

    first_year = sorted_years[0]
    last_year = sorted_years[-1]
    periods = last_year - first_year

    if periods <= 0:
        return 0.0

    return cagr(funding_by_year[first_year], funding_by_year[last_year], periods)
