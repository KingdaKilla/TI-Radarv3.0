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
from shared.domain.publication_definitions import (
    PublicationScope,
    canonical_publication_label,
)
from shared.domain.year_completeness import last_complete_year

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

    # MAJ-7/MAJ-8: Letztes vollstaendig abgeschlossenes Kalenderjahr.
    # Frontend nutzt es als ReferenceArea-Cutoff fuer den Hinweis
    # "Daten ggf. unvollstaendig". Quelle: ``last_complete_year()``.
    data_complete_year: int = 0

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

        # MAJ-7/MAJ-8: Datenvollstaendigkeits-Cutoff aus shared-Helper.
        # Wenn der User ein Endjahr nach dem letzten vollstaendigen Jahr
        # anfragt, wird CAGR bis dorthin gerechnet, aber das Frontend
        # bekommt einen Hinweis (Warning + ``data_complete_year``-Feld).
        data_complete_year = last_complete_year()
        if end_year > data_complete_year:
            result.warnings.append({
                "message": (
                    f"Endjahr {end_year} > letztes vollstaendiges Jahr "
                    f"{data_complete_year} — CAGR wird auf vollstaendige "
                    "Jahre beschraenkt; Trend ggf. unvollstaendig."
                ),
                "severity": "MEDIUM",
                "code": "DATA_INCOMPLETE_RECENT_YEARS",
            })

        # --- Parallele Datenabfragen ---
        patent_years: list = []
        patent_countries: list = []
        project_years: list = []
        project_countries: list = []
        publication_years: list = []
        top_cpc: list = []
        total_funding: float = 0.0
        funding_by_year: dict[int, float] = {}

        # CRIT-1: kanonische CORDIS-Publikationszahl (Header-Summary-Quelle).
        total_publications_cordis: int = 0

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

        # CRIT-1: Header-Summary ``total_publications`` aus CORDIS_LINKED-Scope.
        # Diese Zahl MUSS mit publication-svc (UC13) identisch sein.
        tasks.append(asyncio.create_task(
            self._repo.count_cordis_publications(
                technology, start_year=start_year, end_year=end_year,
            ),
            name="cordis_publications_total",
        ))

        # OpenAIRE Publikationen (extern, optional) — liefert nur die
        # Zeitreihen-Trendkurve, *nicht* die Header-Gesamtzahl (CRIT-1).
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
                elif name == "cordis_publications_total":
                    total_publications_cordis = int(task_result or 0)

        # --- Datenquellen dokumentieren ---
        total_patents = sum(y.count for y in patent_years)
        total_projects = sum(y.count for y in project_years)
        # CRIT-1: Header-Publikationen MUSS aus CORDIS_LINKED-Scope kommen —
        # identisch zur Query in publication-svc.publication_summary().
        # OpenAIRE liefert nur die Trendkurve fuer die Zeitreihe.
        total_publications = total_publications_cordis
        openaire_publications = _sum_counts(publication_years)

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
            # CRIT-1: kanonisches Label aus shared.domain.publication_definitions.
            data_sources.append({
                "name": (
                    f"CORDIS Publications — {canonical_publication_label(PublicationScope.CORDIS_LINKED)}"
                ),
                "type": "PUBLICATION",
                "record_count": total_publications,
            })
        if openaire_publications > 0:
            data_sources.append({
                "name": "OpenAIRE (API) — Zeitreihen-Trend",
                "type": "PUBLICATION",
                "record_count": openaire_publications,
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
        # MAJ-7/MAJ-8: ``data_complete_year`` schneidet das laufende Jahr ab,
        # damit der Endwert nicht durch ein Teiljahr verzerrt wird.
        periods = end_year - start_year
        cagr_patents = _safe_cagr(patent_years, periods, data_complete_year=data_complete_year)
        cagr_projects = _safe_cagr(project_years, periods, data_complete_year=data_complete_year)
        cagr_publications = _safe_cagr(publication_years, periods, data_complete_year=data_complete_year)
        cagr_funding = _compute_funding_cagr(
            funding_by_year, start_year, end_year, data_complete_year=data_complete_year,
        )

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
        result.data_complete_year = data_complete_year
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
    data_complete_year: int | None = None,
) -> float:
    """CAGR sicher berechnen — gibt 0.0 bei unzureichenden Daten zurueck.

    Nimmt den ersten und letzten Datenpunkt (nicht den Zeitraum-Anfang/Ende),
    um CAGR nur ueber tatsaechlich vorhandene Daten zu berechnen.
    Unterstuetzt sowohl dict- als auch Attribut-basierte Eintraege.

    Daten nach data_complete_year werden ignoriert, da unvollstaendige
    Jahrgaenge die CAGR-Berechnung nach unten verzerren wuerden. Wenn
    nicht angegeben, wird ``last_complete_year()`` verwendet (Bug
    MAJ-7/MAJ-8 — kein Hardcoding mehr).
    """
    if not yearly_data or periods <= 0:
        return 0.0

    if data_complete_year is None:
        data_complete_year = last_complete_year()

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
    data_complete_year: int | None = None,
) -> float:
    """CAGR fuer Foerdervolumen berechnen.

    Ueberspringt Jahre ohne Foerderung am Anfang/Ende.
    Daten nach data_complete_year werden ignoriert (unvollstaendig). Wenn
    nicht angegeben, wird ``last_complete_year()`` verwendet (Bug
    MAJ-7/MAJ-8).
    """
    if not funding_by_year:
        return 0.0

    if data_complete_year is None:
        data_complete_year = last_complete_year()

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
