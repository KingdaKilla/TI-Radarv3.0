"""CORDIS Bulk-Importer — JSON-ZIP- und CSV-Dateien in cordis_schema laden.

Liest CORDIS-Bulk-Downloads (JSON-ZIP-Archive oder CSV-Fallback),
parst die Daten und schreibt sie batchweise in PostgreSQL.

Primaerer Pfad (JSON-ZIP):
    /data/bulk/CORDIS/
        cordis-fp7projects-json.zip
        cordis-h2020projects-json.zip
        cordis-HORIZONprojects-json.zip
        cordis-h2020projectPublications-json.zip
        cordis-HORIZONprojectPublications-json.zip

    Jedes ZIP enthaelt project.json / organization.json als JSON-Arrays.

Fallback (CSV):
    /data/bulk/CORDIS/
        *project*.csv    (Projekte-Daten)
        *organization*.csv  (Organisationen-Daten)

Ziel-Tabellen:
    cordis_schema.projects        — EU-Forschungsprojekte
    cordis_schema.organizations   — Beteiligte Organisationen
    cordis_schema.publications    — Projekt-Publikationen
"""

from __future__ import annotations

import csv
import json
import time
import zipfile
from collections.abc import Generator
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    import asyncpg

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Import-Tracking: Inkrementelle Imports via cross_schema.import_log
# ---------------------------------------------------------------------------


async def _is_already_imported(pool: asyncpg.Pool, source: str, filename: str) -> bool:
    """Pruefen ob eine Datei bereits erfolgreich importiert wurde.

    Args:
        pool: asyncpg Connection-Pool.
        source: Datenquelle ('epo', 'cordis', 'euroscivoc').
        filename: Name der zu pruefenden Datei.

    Returns:
        True wenn die Datei bereits importiert wurde, sonst False.
    """
    row = await pool.fetchrow(
        "SELECT 1 FROM cross_schema.import_log "
        "WHERE source=$1 AND filename=$2 AND status='completed'",
        source, filename,
    )
    return row is not None


async def _log_import(
    pool: asyncpg.Pool,
    source: str,
    filename: str,
    record_count: int,
    duration_seconds: float,
) -> None:
    """Erfolgreichen Import in cross_schema.import_log protokollieren.

    Bei erneutem Import derselben Datei wird der bestehende Eintrag
    aktualisiert (UPSERT via ON CONFLICT).

    Args:
        pool: asyncpg Connection-Pool.
        source: Datenquelle ('epo', 'cordis', 'euroscivoc').
        filename: Name der importierten Datei.
        record_count: Anzahl importierter Datensaetze.
        duration_seconds: Import-Dauer in Sekunden.
    """
    await pool.execute(
        """INSERT INTO cross_schema.import_log
               (source, filename, record_count, duration_seconds, status)
           VALUES ($1, $2, $3, $4, 'completed')
           ON CONFLICT (source, filename) DO UPDATE SET
               record_count = EXCLUDED.record_count,
               duration_seconds = EXCLUDED.duration_seconds,
               imported_at = NOW(),
               status = 'completed'""",
        source, filename, record_count, duration_seconds,
    )


# ---------------------------------------------------------------------------
# Ergebnis-Datenklasse
# ---------------------------------------------------------------------------


@dataclass
class ImportResult:
    """Ergebnis eines Bulk-Import-Vorgangs.

    Attribute:
        source: Datenquelle (z.B. "EPO", "CORDIS").
        files_processed: Anzahl verarbeiteter Dateien.
        records_imported: Anzahl erfolgreich importierter Datensaetze.
        records_skipped: Anzahl uebersprungener Datensaetze (Duplikate, Fehler).
        errors: Liste von Fehlermeldungen.
        duration_seconds: Laufzeit in Sekunden.
        details: Zusaetzliche Details (z.B. Projekte vs. Organisationen).
    """

    source: str = "CORDIS"
    files_processed: int = 0
    records_imported: int = 0
    records_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    details: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Gemeinsame Hilfsfunktionen
# ---------------------------------------------------------------------------


def _parse_date(date_str: str | None) -> date | None:
    """Datum aus verschiedenen CORDIS-Formaten parsen.

    Unterstuetzte Formate:
        YYYY-MM-DD, DD/MM/YYYY, YYYY-MM-DDTHH:MM:SS
    """
    if not date_str or (isinstance(date_str, str) and not date_str.strip()):
        return None
    date_str = str(date_str).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def _parse_decimal(value: Any) -> Decimal | None:
    """Dezimalwert sicher parsen (Komma und Punkt als Trennzeichen)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        # Komma als Dezimaltrennzeichen ersetzen (europaeisches Format)
        cleaned = value.strip().replace(",", ".")
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def _parse_bool(value: Any) -> bool:
    """Boolean-Wert aus CORDIS-Daten parsen.

    Akzeptiert: True/False (bool), YES/true/1 (str), etc.
    """
    if isinstance(value, bool):
        return value
    if not value:
        return False
    return str(value).strip().upper() in ("YES", "TRUE", "1", "Y", "JA")


def _detect_framework(filename: str) -> str:
    """Framework-Programm aus Dateiname erkennen."""
    lower = filename.lower()
    if "fp7" in lower:
        return "FP7"
    if "h2020" in lower:
        return "H2020"
    if "horizon" in lower:
        return "HORIZON"
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# JSON-ZIP-Verarbeitung
# ---------------------------------------------------------------------------


def _stream_json_from_zip(
    zip_path: Path,
    json_filename: str,
) -> Generator[dict[str, Any], None, None]:
    """JSON-Array aus ZIP-Datei streamen (In-Memory, kein Entpacken auf Disk).

    Args:
        zip_path: Pfad zur ZIP-Datei.
        json_filename: Name der JSON-Datei innerhalb des ZIP-Archivs.

    Yields:
        Einzelne JSON-Objekte aus dem Array.
    """
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            if json_filename not in zf.namelist():
                logger.debug(
                    "json_nicht_in_zip",
                    zip_datei=zip_path.name,
                    json_datei=json_filename,
                )
                return

            with zf.open(json_filename) as f:
                content = f.read().decode("utf-8")
                try:
                    data = json.loads(content)
                    if isinstance(data, list):
                        yield from data
                    elif isinstance(data, dict):
                        # Manche CORDIS-Dateien wrappen das Array in einem Objekt
                        # z.B. {"projects": [...]}
                        for _key, val in data.items():
                            if isinstance(val, list):
                                yield from val
                                break
                        else:
                            yield data
                    else:
                        logger.warning(
                            "unerwartetes_json_format",
                            zip_datei=zip_path.name,
                            json_datei=json_filename,
                            typ=type(data).__name__,
                        )
                except json.JSONDecodeError as exc:
                    logger.error(
                        "json_decode_fehler",
                        zip_datei=zip_path.name,
                        json_datei=json_filename,
                        error=str(exc),
                    )
    except zipfile.BadZipFile as exc:
        logger.error(
            "ungueltige_zip_datei",
            zip_datei=zip_path.name,
            error=str(exc),
        )
    except Exception as exc:
        logger.error(
            "zip_lese_fehler",
            zip_datei=zip_path.name,
            error=str(exc),
        )


def _find_json_files_in_zip(zip_path: Path) -> list[str]:
    """Alle JSON-Dateinamen innerhalb eines ZIP-Archivs auflisten."""
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            return [n for n in zf.namelist() if n.endswith(".json")]
    except (zipfile.BadZipFile, Exception) as exc:
        logger.error("zip_auflisten_fehler", zip_datei=zip_path.name, error=str(exc))
        return []


# ---------------------------------------------------------------------------
# Projekte: JSON-Parsing
# ---------------------------------------------------------------------------


def _parse_project_json(record: dict[str, Any], framework: str) -> dict | None:
    """Einzelnes Projekt-Objekt aus CORDIS-JSON parsen.

    CORDIS JSON-Felder:
        id, rcn, acronym, title, objective, keywords, startDate, endDate,
        status, totalCost, ecMaxContribution, fundingScheme, topics,
        legalBasis, contentUpdateDate
    """
    try:
        project_id = record.get("id")
        if project_id is None:
            return None

        # id muss ein Integer sein
        try:
            project_id = int(project_id)
        except (ValueError, TypeError):
            return None

        return {
            "id": project_id,
            "rcn": _safe_int(record.get("rcn")),
            "framework": framework,
            "acronym": _safe_str(record.get("acronym"), max_len=50),
            "title": _safe_str(record.get("title"), max_len=2000) or "",
            "objective": _safe_str(record.get("objective")),
            "keywords": _safe_str(record.get("keywords")),
            "start_date": _parse_date(record.get("startDate")),
            "end_date": _parse_date(record.get("endDate")),
            "status": _safe_str(record.get("status"), max_len=20),
            "total_cost": _parse_decimal(record.get("totalCost")),
            "ec_max_contribution": _parse_decimal(record.get("ecMaxContribution")),
            "funding_scheme": _safe_str(record.get("fundingScheme"), max_len=50),
            "topics": _safe_str(record.get("topics")),
            "legal_basis": _safe_str(record.get("legalBasis")),
        }
    except Exception as exc:
        logger.warning("projekt_json_parse_fehler", error=str(exc))
        return None


def _safe_str(value: Any, max_len: int | None = None) -> str | None:
    """Sicherer String-Zugriff mit optionaler Laengenbegrenzung."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if max_len is not None:
        s = s[:max_len]
    return s


def _safe_int(value: Any) -> int | None:
    """Sicher einen Integer parsen."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Organisationen: JSON-Parsing
# ---------------------------------------------------------------------------


def _parse_organization_json(record: dict[str, Any]) -> dict | None:
    """Einzelnes Organisations-Objekt aus CORDIS-JSON parsen.

    CORDIS JSON-Felder:
        organisationID, projectID, name, shortName, country, city,
        role, activityType, SME, ecContribution, totalCost
    """
    try:
        project_id = record.get("projectID") or record.get("projectId")
        name = record.get("name") or record.get("legalName") or ""
        name = name.strip()

        if not project_id or not name:
            return None

        try:
            project_id = int(project_id)
        except (ValueError, TypeError):
            return None

        # Rolle normalisieren (CORDIS liefert teilweise Grossbuchstaben)
        role = _safe_str(record.get("role"), max_len=20)
        if role:
            role = role.lower()

        # activityType normalisieren (HES, PRC, REC, OTH, PUB)
        activity_type = _safe_str(record.get("activityType"), max_len=5)
        if activity_type:
            activity_type = activity_type.upper()

        return {
            "organisation_id": _safe_int(record.get("organisationID")),
            "project_id": project_id,
            "name": name[:500],
            "short_name": _safe_str(record.get("shortName"), max_len=50),
            "country": _safe_str(record.get("country"), max_len=2),
            "city": _safe_str(record.get("city"), max_len=200),
            "role": role,
            "activity_type": activity_type,
            "sme": _parse_bool(record.get("SME") or record.get("sme")),
            "ec_contribution": _parse_decimal(record.get("ecContribution")),
            "total_cost": _parse_decimal(record.get("totalCost")),
        }
    except Exception as exc:
        logger.warning("organisation_json_parse_fehler", error=str(exc))
        return None


# ---------------------------------------------------------------------------
# Publikationen: JSON-Parsing
# ---------------------------------------------------------------------------


def _parse_publication_json(record: dict[str, Any]) -> dict | None:
    """Einzelnes Publikations-Objekt aus CORDIS-JSON parsen.

    CORDIS JSON-Felder:
        projectID, title, authors, journalTitle, publicationDate,
        doi, openAccess
    """
    try:
        project_id = record.get("projectID") or record.get("projectId")
        title = _safe_str(record.get("title"))

        if not project_id:
            return None

        try:
            project_id = int(project_id)
        except (ValueError, TypeError):
            return None

        doi = _safe_str(record.get("doi"))

        return {
            "project_id": project_id,
            "title": title,
            "authors": _safe_str(record.get("authors")),
            "journal": _safe_str(record.get("journalTitle") or record.get("journal")),
            "publication_date": _parse_date(record.get("publicationDate")),
            "doi": doi,
            "open_access": _parse_bool(record.get("openAccess")),
        }
    except Exception as exc:
        logger.warning("publikation_json_parse_fehler", error=str(exc))
        return None


# ---------------------------------------------------------------------------
# Batch-Insert: Projekte
# ---------------------------------------------------------------------------


async def _insert_project_batch(
    pool: asyncpg.Pool,
    batch: list[dict],
) -> tuple[int, int]:
    """Batch von Projekten via executemany in cordis_schema.projects einfuegen.

    ON CONFLICT DO NOTHING fuer idempotente Re-Imports.
    Erweitert gegenueber CSV-Version: rcn, keywords, status, topics,
    legal_basis werden jetzt auch importiert (JSON liefert mehr Felder).

    Returns:
        Tuple (importiert, uebersprungen).
    """
    if not batch:
        return 0, 0

    valid_records = [p for p in batch if p["id"] is not None]
    invalid = len(batch) - len(valid_records)

    if not valid_records:
        return 0, invalid

    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO cordis_schema.projects (
                id, rcn, framework, acronym, title, objective,
                keywords, start_date, end_date, status,
                total_cost, ec_max_contribution, funding_scheme,
                topics, legal_basis
            ) VALUES (
                $1, $2, $3, $4, $5, $6,
                $7, $8, $9, $10,
                $11, $12, $13,
                $14, $15
            )
            ON CONFLICT (id) DO NOTHING
            """,
            [
                (
                    p["id"],
                    p.get("rcn"),
                    p.get("framework", "UNKNOWN"),
                    p.get("acronym"),
                    p.get("title", ""),
                    p.get("objective"),
                    p.get("keywords"),
                    p.get("start_date"),
                    p.get("end_date"),
                    p.get("status"),
                    p.get("total_cost"),
                    p.get("ec_max_contribution"),
                    p.get("funding_scheme"),
                    p.get("topics"),
                    p.get("legal_basis"),
                )
                for p in valid_records
            ],
        )

    return len(valid_records), invalid


# ---------------------------------------------------------------------------
# Batch-Insert: Organisationen
# ---------------------------------------------------------------------------


async def _insert_organization_batch(
    pool: asyncpg.Pool,
    batch: list[dict],
) -> tuple[int, int]:
    """Batch von Organisationen via executemany in cordis_schema.organizations einfuegen.

    ON CONFLICT DO NOTHING fuer idempotente Re-Imports.
    Erweitert: organisation_id, short_name, total_cost werden jetzt importiert.

    Returns:
        Tuple (importiert, uebersprungen).
    """
    if not batch:
        return 0, 0

    valid_records = [o for o in batch if o["project_id"] is not None]
    invalid = len(batch) - len(valid_records)

    if not valid_records:
        return 0, invalid

    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO cordis_schema.organizations (
                organisation_id, project_id, name, short_name,
                country, city, role, activity_type,
                sme, ec_contribution, total_cost
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (project_id, name) DO NOTHING
            """,
            [
                (
                    o.get("organisation_id"),
                    o["project_id"],
                    o["name"],
                    o.get("short_name"),
                    o.get("country"),
                    o.get("city"),
                    o.get("role"),
                    o.get("activity_type"),
                    o.get("sme"),
                    o.get("ec_contribution"),
                    o.get("total_cost"),
                )
                for o in valid_records
            ],
        )

    return len(valid_records), invalid


# ---------------------------------------------------------------------------
# Batch-Insert: Publikationen
# ---------------------------------------------------------------------------


async def _insert_publication_batch(
    pool: asyncpg.Pool,
    batch: list[dict],
) -> tuple[int, int]:
    """Batch von Publikationen via executemany in cordis_schema.publications einfuegen.

    ON CONFLICT (doi) DO NOTHING fuer Deduplikation.

    Returns:
        Tuple (importiert, uebersprungen).
    """
    if not batch:
        return 0, 0

    valid_records = [p for p in batch if p["project_id"] is not None]
    invalid = len(batch) - len(valid_records)

    if not valid_records:
        return 0, invalid

    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO cordis_schema.publications (
                project_id, title, authors, journal,
                publication_date, doi, open_access
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (doi) DO NOTHING
            """,
            [
                (
                    p["project_id"],
                    p.get("title"),
                    p.get("authors"),
                    p.get("journal"),
                    p.get("publication_date"),
                    p.get("doi"),
                    p.get("open_access"),
                )
                for p in valid_records
            ],
        )

    return len(valid_records), invalid


# ---------------------------------------------------------------------------
# JSON-ZIP-Verarbeitung: generisch mit Batch-Logik
# ---------------------------------------------------------------------------


async def _process_json_records(
    pool: asyncpg.Pool,
    records: Generator[dict[str, Any], None, None],
    record_parser: callable,
    batch_inserter: callable,
    batch_size: int,
    entity_name: str,
    source_name: str,
    *,
    parser_extra_args: tuple = (),
) -> tuple[int, int, list[str]]:
    """Generische JSON-Record-Verarbeitung: Parsen und batchweise einfuegen.

    Args:
        pool: asyncpg Connection-Pool.
        records: Generator der JSON-Objekte.
        record_parser: Funktion zum Parsen eines JSON-Objekts.
        batch_inserter: Async-Funktion zum Batch-Insert.
        batch_size: Anzahl Datensaetze pro Batch.
        entity_name: Name der Entitaet (fuer Logging).
        source_name: Name der Quelldatei (fuer Fehlermeldungen).
        parser_extra_args: Zusaetzliche Argumente fuer den Parser.

    Returns:
        Tuple (importiert, uebersprungen, fehler).
    """
    imported = 0
    skipped = 0
    errors: list[str] = []
    batch: list[dict] = []

    for idx, record in enumerate(records):
        parsed = record_parser(record, *parser_extra_args)
        if parsed:
            batch.append(parsed)
        else:
            skipped += 1

        # Batch-Groesse erreicht -> in DB schreiben
        if len(batch) >= batch_size:
            try:
                batch_imported, batch_skipped = await batch_inserter(pool, batch)
                imported += batch_imported
                skipped += batch_skipped
            except Exception as exc:
                error_msg = (
                    f"Batch-Insert fehlgeschlagen bei {entity_name} "
                    f"Eintrag {idx} ({source_name}): {exc}"
                )
                errors.append(error_msg)
                logger.error(
                    f"{entity_name}_batch_fehler",
                    error=str(exc),
                    eintrag=idx,
                    quelle=source_name,
                )
            batch = []

            # Fortschritt loggen
            if (imported + skipped) % 10_000 == 0:
                logger.info(
                    f"{entity_name}_import_fortschritt",
                    importiert=imported,
                    uebersprungen=skipped,
                    quelle=source_name,
                )

    # Restlichen Batch verarbeiten
    if batch:
        try:
            batch_imported, batch_skipped = await batch_inserter(pool, batch)
            imported += batch_imported
            skipped += batch_skipped
        except Exception as exc:
            error_msg = f"Letzter Batch fehlgeschlagen ({source_name}): {exc}"
            errors.append(error_msg)
            logger.error(
                f"{entity_name}_letzter_batch_fehler",
                error=str(exc),
                quelle=source_name,
            )

    return imported, skipped, errors


# ---------------------------------------------------------------------------
# CSV-Parsing (Fallback-Pfad)
# ---------------------------------------------------------------------------


def _detect_encoding(file_path: Path) -> str:
    """Encoding einer CSV-Datei erkennen (UTF-8 oder Latin-1 Fallback)."""
    try:
        with open(file_path, encoding="utf-8") as f:
            f.read(4096)
        return "utf-8"
    except UnicodeDecodeError:
        return "latin-1"


def _parse_project_row(row: dict[str, str]) -> dict | None:
    """Einzelne Projektzeile aus CORDIS-CSV parsen (Fallback-Pfad).

    Erwartete Spalten (case-insensitive Mapping):
        id, acronym, title, objective, startDate, endDate,
        totalCost, ecMaxContribution, fundingScheme, frameworkProgramme
    """
    try:
        project_id = (
            row.get("id", "")
            or row.get("projectID", "")
            or row.get("project_id", "")
        ).strip()

        if not project_id:
            return None

        framework = (
            row.get("frameworkProgramme", "")
            or row.get("framework", "")
            or row.get("programme", "")
        ).strip()

        return {
            "id": int(project_id) if project_id.isdigit() else None,
            "rcn": _safe_int(row.get("rcn", "")),
            "framework": framework or "UNKNOWN",
            "acronym": _safe_str(row.get("acronym", ""), max_len=50),
            "title": _safe_str(row.get("title", ""), max_len=2000) or "",
            "objective": _safe_str(row.get("objective", "")),
            "keywords": _safe_str(row.get("keywords", "")),
            "start_date": _parse_date(
                row.get("startDate", "") or row.get("start_date", "")
            ),
            "end_date": _parse_date(
                row.get("endDate", "") or row.get("end_date", "")
            ),
            "status": _safe_str(row.get("status", ""), max_len=20),
            "total_cost": _parse_decimal(
                row.get("totalCost", "") or row.get("total_cost", "")
            ),
            "ec_max_contribution": _parse_decimal(
                row.get("ecMaxContribution", "")
                or row.get("ec_max_contribution", "")
            ),
            "funding_scheme": _safe_str(
                row.get("fundingScheme", "") or row.get("funding_scheme", ""),
                max_len=50,
            ),
            "topics": _safe_str(row.get("topics", "")),
            "legal_basis": _safe_str(row.get("legalBasis", "")),
        }
    except (ValueError, KeyError) as exc:
        logger.warning("projekt_csv_parse_fehler", error=str(exc))
        return None


def _parse_organization_row(row: dict[str, str]) -> dict | None:
    """Einzelne Organisationszeile aus CORDIS-CSV parsen (Fallback-Pfad).

    Erwartete Spalten:
        projectID, name, country, city, role,
        activityType, sme, ecContribution
    """
    try:
        project_id = (
            row.get("projectID", "")
            or row.get("project_id", "")
            or row.get("projectId", "")
        ).strip()

        name = (row.get("name", "") or row.get("organisationName", "")).strip()

        if not project_id or not name:
            return None

        role = _safe_str(
            row.get("role", "") or row.get("participantRole", ""),
            max_len=20,
        )
        if role:
            role = role.lower()

        activity_type = _safe_str(
            row.get("activityType", "") or row.get("activity_type", ""),
            max_len=5,
        )
        if activity_type:
            activity_type = activity_type.upper()

        return {
            "organisation_id": _safe_int(row.get("organisationID", "")),
            "project_id": int(project_id) if project_id.isdigit() else None,
            "name": name[:500],
            "short_name": _safe_str(row.get("shortName", ""), max_len=50),
            "country": _safe_str(
                row.get("country", "") or row.get("countryCode", ""),
                max_len=2,
            ),
            "city": _safe_str(row.get("city", ""), max_len=200),
            "role": role,
            "activity_type": activity_type,
            "sme": _parse_bool(
                row.get("sme", "") or row.get("SME", "")
            ),
            "ec_contribution": _parse_decimal(
                row.get("ecContribution", "")
                or row.get("ec_contribution", "")
                or ""
            ),
            "total_cost": _parse_decimal(
                row.get("totalCost", "") or row.get("total_cost", "") or ""
            ),
        }
    except (ValueError, KeyError) as exc:
        logger.warning("organisation_csv_parse_fehler", error=str(exc))
        return None


async def _process_csv_file(
    pool: asyncpg.Pool,
    file_path: Path,
    row_parser: callable,
    batch_inserter: callable,
    batch_size: int,
    entity_name: str,
) -> tuple[int, int, list[str]]:
    """Generische CSV-Verarbeitung: Zeilen parsen und batchweise einfuegen.

    Args:
        pool: asyncpg Connection-Pool.
        file_path: Pfad zur CSV-Datei.
        row_parser: Funktion zum Parsen einer CSV-Zeile.
        batch_inserter: Async-Funktion zum Batch-Insert.
        batch_size: Anzahl Zeilen pro Batch.
        entity_name: Name der Entitaet (fuer Logging).

    Returns:
        Tuple (importiert, uebersprungen, fehler).
    """
    encoding = _detect_encoding(file_path)
    imported = 0
    skipped = 0
    errors: list[str] = []
    batch: list[dict] = []

    logger.info(
        f"{entity_name}_csv_lesen",
        datei=file_path.name,
        encoding=encoding,
    )

    try:
        with open(file_path, encoding=encoding, newline="") as f:
            # Semikolon als Trennzeichen (CORDIS-Standard) oder Komma
            sample = f.read(4096)
            f.seek(0)
            delimiter = ";" if sample.count(";") > sample.count(",") else ","

            reader = csv.DictReader(f, delimiter=delimiter)

            for row_idx, row in enumerate(reader):
                parsed = row_parser(row)
                if parsed:
                    batch.append(parsed)
                else:
                    skipped += 1

                # Batch-Groesse erreicht -> in DB schreiben
                if len(batch) >= batch_size:
                    try:
                        batch_imported, batch_skipped = await batch_inserter(
                            pool, batch
                        )
                        imported += batch_imported
                        skipped += batch_skipped
                    except Exception as exc:
                        error_msg = f"Batch-Insert fehlgeschlagen bei Zeile {row_idx}: {exc}"
                        errors.append(error_msg)
                        logger.error(
                            f"{entity_name}_batch_fehler",
                            error=str(exc),
                            zeile=row_idx,
                        )
                    batch = []

                    # Fortschritt loggen
                    if (imported + skipped) % 10_000 == 0:
                        logger.info(
                            f"{entity_name}_import_fortschritt",
                            importiert=imported,
                            uebersprungen=skipped,
                        )

        # Restlichen Batch verarbeiten
        if batch:
            try:
                batch_imported, batch_skipped = await batch_inserter(pool, batch)
                imported += batch_imported
                skipped += batch_skipped
            except Exception as exc:
                error_msg = f"Letzter Batch fehlgeschlagen: {exc}"
                errors.append(error_msg)
                logger.error(f"{entity_name}_letzter_batch_fehler", error=str(exc))

    except Exception as exc:
        error_msg = f"CSV-Lesefehler {file_path.name}: {exc}"
        errors.append(error_msg)
        logger.error(f"{entity_name}_csv_fehler", datei=file_path.name, error=str(exc))

    return imported, skipped, errors


# ---------------------------------------------------------------------------
# JSON-ZIP Import-Logik
# ---------------------------------------------------------------------------


async def _import_from_zip_files(
    pool: asyncpg.Pool,
    cordis_dir: Path,
    zip_files: list[Path],
    batch_size: int,
    result: ImportResult,
) -> None:
    """Projekte, Organisationen und Publikationen aus ZIP-Dateien importieren.

    Klassifiziert ZIP-Dateien nach Typ:
      - *projects*.zip  -> project.json + organization.json
      - *Publications*.zip -> publications JSON
    """
    # ZIP-Dateien nach Typ klassifizieren
    project_zips = sorted(
        f for f in zip_files
        if "project" in f.name.lower() and "publication" not in f.name.lower()
    )
    publication_zips = sorted(
        f for f in zip_files
        if "publication" in f.name.lower()
    )

    logger.info(
        "cordis_zip_klassifizierung",
        projekt_zips=len(project_zips),
        publikation_zips=len(publication_zips),
    )

    # --- Projekte und Organisationen aus Projekt-ZIPs ---
    projects_imported = 0
    projects_skipped = 0
    orgs_imported = 0
    orgs_skipped = 0

    for zip_path in project_zips:
        # Inkrementeller Import: bereits importierte Dateien ueberspringen
        if await _is_already_imported(pool, "cordis", zip_path.name):
            logger.info(
                "ueberspringe_bereits_importierte_datei",
                datei=zip_path.name,
                quelle="cordis",
            )
            result.files_processed += 1
            continue

        zip_start_time = time.monotonic()
        framework = _detect_framework(zip_path.name)

        logger.info(
            "cordis_zip_verarbeitung",
            datei=zip_path.name,
            framework=framework,
        )

        # Projekte importieren
        project_records = _stream_json_from_zip(zip_path, "project.json")
        imported, skipped, errors = await _process_json_records(
            pool=pool,
            records=project_records,
            record_parser=_parse_project_json,
            batch_inserter=_insert_project_batch,
            batch_size=batch_size,
            entity_name="projekt",
            source_name=zip_path.name,
            parser_extra_args=(framework,),
        )
        projects_imported += imported
        projects_skipped += skipped
        result.errors.extend(errors)

        # Organisationen aus derselben ZIP importieren
        org_records = _stream_json_from_zip(zip_path, "organization.json")
        org_imported, org_skipped, org_errors = await _process_json_records(
            pool=pool,
            records=org_records,
            record_parser=_parse_organization_json,
            batch_inserter=_insert_organization_batch,
            batch_size=batch_size,
            entity_name="organisation",
            source_name=zip_path.name,
        )
        orgs_imported += org_imported
        orgs_skipped += org_skipped
        result.errors.extend(org_errors)

        result.files_processed += 1

        # Import in cross_schema.import_log protokollieren
        zip_record_count = imported + org_imported
        zip_duration = round(time.monotonic() - zip_start_time, 2)
        await _log_import(
            pool, "cordis", zip_path.name, zip_record_count, zip_duration,
        )

    result.details["projects_imported"] = projects_imported
    result.details["projects_skipped"] = projects_skipped
    result.details["organizations_imported"] = orgs_imported
    result.details["organizations_skipped"] = orgs_skipped

    # --- Publikationen aus Publikations-ZIPs ---
    pubs_imported = 0
    pubs_skipped = 0

    for zip_path in publication_zips:
        # Inkrementeller Import: bereits importierte Dateien ueberspringen
        if await _is_already_imported(pool, "cordis", zip_path.name):
            logger.info(
                "ueberspringe_bereits_importierte_datei",
                datei=zip_path.name,
                quelle="cordis",
            )
            result.files_processed += 1
            continue

        pub_start_time = time.monotonic()

        logger.info(
            "cordis_publikationen_zip_verarbeitung",
            datei=zip_path.name,
        )

        # JSON-Dateiname innerhalb des ZIP finden
        json_files = _find_json_files_in_zip(zip_path)
        if not json_files:
            logger.warning(
                "keine_json_in_pub_zip",
                datei=zip_path.name,
            )
            continue

        # Erste JSON-Datei verwenden (typisch: publication.json o.Ae.)
        pub_json_name = json_files[0]
        pub_records = _stream_json_from_zip(zip_path, pub_json_name)
        imported, skipped, errors = await _process_json_records(
            pool=pool,
            records=pub_records,
            record_parser=_parse_publication_json,
            batch_inserter=_insert_publication_batch,
            batch_size=batch_size,
            entity_name="publikation",
            source_name=zip_path.name,
        )
        pubs_imported += imported
        pubs_skipped += skipped
        result.errors.extend(errors)

        result.files_processed += 1

        # Import in cross_schema.import_log protokollieren
        pub_duration = round(time.monotonic() - pub_start_time, 2)
        await _log_import(
            pool, "cordis", zip_path.name, imported, pub_duration,
        )

    result.details["publications_imported"] = pubs_imported
    result.details["publications_skipped"] = pubs_skipped

    # Gesamtstatistiken
    result.records_imported = projects_imported + orgs_imported + pubs_imported
    result.records_skipped = projects_skipped + orgs_skipped + pubs_skipped


# ---------------------------------------------------------------------------
# CSV Import-Logik (Fallback)
# ---------------------------------------------------------------------------


async def _import_from_csv_files(
    pool: asyncpg.Pool,
    cordis_dir: Path,
    batch_size: int,
    result: ImportResult,
) -> None:
    """Projekte und Organisationen aus CSV-Dateien importieren (Fallback)."""
    project_files = sorted(
        f for f in cordis_dir.glob("*.csv")
        if "project" in f.name.lower()
    )
    org_files = sorted(
        f for f in cordis_dir.glob("*.csv")
        if "organ" in f.name.lower() or "participant" in f.name.lower()
    )

    if not project_files and not org_files:
        result.errors.append(f"Keine CSV-Dateien in {cordis_dir} gefunden")
        logger.warning("keine_csv_dateien", path=str(cordis_dir))
        return

    logger.info(
        "cordis_csv_fallback",
        projekt_dateien=len(project_files),
        org_dateien=len(org_files),
    )

    # --- Projekte importieren ---
    projects_imported = 0
    projects_skipped = 0

    for file_path in project_files:
        # Inkrementeller Import: bereits importierte Dateien ueberspringen
        if await _is_already_imported(pool, "cordis", file_path.name):
            logger.info(
                "ueberspringe_bereits_importierte_datei",
                datei=file_path.name,
                quelle="cordis",
            )
            result.files_processed += 1
            continue

        csv_start_time = time.monotonic()

        imported, skipped, errors = await _process_csv_file(
            pool=pool,
            file_path=file_path,
            row_parser=_parse_project_row,
            batch_inserter=_insert_project_batch,
            batch_size=batch_size,
            entity_name="projekt",
        )
        projects_imported += imported
        projects_skipped += skipped
        result.errors.extend(errors)
        result.files_processed += 1

        # Import in cross_schema.import_log protokollieren
        csv_duration = round(time.monotonic() - csv_start_time, 2)
        await _log_import(
            pool, "cordis", file_path.name, imported, csv_duration,
        )

    result.details["projects_imported"] = projects_imported
    result.details["projects_skipped"] = projects_skipped

    # --- Organisationen importieren ---
    orgs_imported = 0
    orgs_skipped = 0

    for file_path in org_files:
        # Inkrementeller Import: bereits importierte Dateien ueberspringen
        if await _is_already_imported(pool, "cordis", file_path.name):
            logger.info(
                "ueberspringe_bereits_importierte_datei",
                datei=file_path.name,
                quelle="cordis",
            )
            result.files_processed += 1
            continue

        org_csv_start_time = time.monotonic()

        imported, skipped, errors = await _process_csv_file(
            pool=pool,
            file_path=file_path,
            row_parser=_parse_organization_row,
            batch_inserter=_insert_organization_batch,
            batch_size=batch_size,
            entity_name="organisation",
        )
        orgs_imported += imported
        orgs_skipped += skipped
        result.errors.extend(errors)
        result.files_processed += 1

        # Import in cross_schema.import_log protokollieren
        org_csv_duration = round(time.monotonic() - org_csv_start_time, 2)
        await _log_import(
            pool, "cordis", file_path.name, imported, org_csv_duration,
        )

    result.details["organizations_imported"] = orgs_imported
    result.details["organizations_skipped"] = orgs_skipped

    # Gesamtstatistiken
    result.records_imported = projects_imported + orgs_imported
    result.records_skipped = projects_skipped + orgs_skipped


# ---------------------------------------------------------------------------
# Haupt-Import-Funktion
# ---------------------------------------------------------------------------


async def import_cordis_bulk(
    pool: asyncpg.Pool,
    data_dir: str,
    batch_size: int = 10_000,
) -> ImportResult:
    """CORDIS-Bulk-Import: ZIP- oder CSV-Dateien lesen, parsen, in PostgreSQL laden.

    Primaerer Pfad: JSON-ZIP-Archive (cordis-*projects-json.zip)
    Fallback-Pfad:  CSV-Dateien (*project*.csv, *organ*.csv)

    Die Entscheidung zwischen ZIP und CSV erfolgt automatisch:
    - Wenn *.zip-Dateien vorhanden sind -> JSON-ZIP-Pfad
    - Sonst -> CSV-Fallback

    Args:
        pool: asyncpg Connection-Pool.
        data_dir: Basisverzeichnis fuer Bulk-Daten.
        batch_size: Anzahl Datensaetze pro Batch-Insert.

    Returns:
        ImportResult mit Statistiken zum Import-Vorgang.
    """
    result = ImportResult(source="CORDIS")
    start_time = time.monotonic()

    cordis_dir = Path(data_dir) / "CORDIS"
    if not cordis_dir.exists():
        result.errors.append(f"CORDIS-Verzeichnis nicht gefunden: {cordis_dir}")
        logger.error("cordis_verzeichnis_fehlt", path=str(cordis_dir))
        return result

    # ZIP-Dateien suchen (primaerer Pfad)
    zip_files = sorted(cordis_dir.glob("*.zip"))

    if zip_files:
        # --- JSON-ZIP-Pfad (primaer) ---
        logger.info(
            "cordis_import_gestartet",
            modus="JSON-ZIP",
            verzeichnis=str(cordis_dir),
            zip_dateien=len(zip_files),
            batch_size=batch_size,
        )

        await _import_from_zip_files(
            pool=pool,
            cordis_dir=cordis_dir,
            zip_files=zip_files,
            batch_size=batch_size,
            result=result,
        )
    else:
        # --- CSV-Fallback ---
        logger.info(
            "cordis_import_gestartet",
            modus="CSV-Fallback",
            verzeichnis=str(cordis_dir),
            batch_size=batch_size,
        )

        await _import_from_csv_files(
            pool=pool,
            cordis_dir=cordis_dir,
            batch_size=batch_size,
            result=result,
        )

    result.duration_seconds = round(time.monotonic() - start_time, 2)

    logger.info(
        "cordis_import_abgeschlossen",
        dateien_verarbeitet=result.files_processed,
        datensaetze_importiert=result.records_imported,
        datensaetze_uebersprungen=result.records_skipped,
        fehler=len(result.errors),
        dauer_sekunden=result.duration_seconds,
        details=result.details,
    )

    return result
