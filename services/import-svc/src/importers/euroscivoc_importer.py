"""EuroSciVoc Bulk-Importer — JSON aus CORDIS-ZIPs in cordis_schema laden.

Liest EuroSciVoc-Taxonomie-Daten aus den CORDIS-Bulk-Downloads
(euroSciVoc.json in den Projekt-ZIPs) und importiert:
  1. Hierarchische Taxonomie (cordis_schema.euroscivoc)
  2. Projekt-Zuordnungen (cordis_schema.project_euroscivoc)

Erwartete Verzeichnisstruktur:
    /data/bulk/CORDIS/
        cordis-HORIZONprojects-json.zip   (enthaelt euroSciVoc.json)
        cordis-h2020projects-json.zip     (enthaelt euroSciVoc.json)
        cordis-fp7projects-json.zip       (enthaelt euroSciVoc.json)

JSON-Format pro Eintrag:
    {
      "euroSciVocCode": "/29/97/67681549/64785222",
      "euroSciVocPath": "/social sciences/political sciences/...",
      "projectID": 101084160,
      "euroSciVocTitle": "revolutions",
      "euroSciVocDescription": ""
    }

Ziel-Tabellen:
    cordis_schema.euroscivoc            — Hierarchische Taxonomie
    cordis_schema.project_euroscivoc    — Junction Projekt <-> EuroSciVoc
"""

from __future__ import annotations

import json
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    import asyncpg

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Ergebnis-Datenklasse
# ---------------------------------------------------------------------------


@dataclass
class ImportResult:
    """Ergebnis eines Bulk-Import-Vorgangs."""

    source: str = "EUROSCIVOC"
    files_processed: int = 0
    records_imported: int = 0
    records_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    details: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Taxonomie-Baum aus JSON-Pfaden ableiten
# ---------------------------------------------------------------------------


def _build_taxonomy_from_entries(
    entries: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Taxonomie-Baum aus EuroSciVoc-JSON-Eintraegen aufbauen.

    Jeder Eintrag hat euroSciVocCode und euroSciVocPath.
    Aus dem Pfad werden alle Ebenen der Hierarchie abgeleitet.

    Returns:
        Dict code -> {code, label_en, parent_code, level}
    """
    taxonomy: dict[str, dict[str, Any]] = {}

    for entry in entries:
        code = (entry.get("euroSciVocCode") or "").strip()
        path = (entry.get("euroSciVocPath") or "").strip()

        if not code or not path:
            continue

        # Pfad-Segmente: "/social sciences/political sciences/..."
        path_parts = [p for p in path.split("/") if p.strip()]
        code_parts = [p for p in code.split("/") if p.strip()]

        if not path_parts or not code_parts:
            continue

        # Alle Hierarchie-Ebenen registrieren
        for depth in range(len(path_parts)):
            # Code bis zu dieser Tiefe
            partial_code = "/" + "/".join(code_parts[: depth + 1])
            label = path_parts[depth].strip()

            if partial_code in taxonomy:
                continue

            parent_code = None
            if depth > 0:
                parent_code = "/" + "/".join(code_parts[:depth])

            taxonomy[partial_code] = {
                "code": partial_code,
                "label_en": label,
                "label_de": None,
                "parent_code": parent_code,
                "level": depth,
            }

    return taxonomy


# ---------------------------------------------------------------------------
# JSON aus ZIP-Dateien lesen
# ---------------------------------------------------------------------------


def _read_euroscivoc_from_zip(zip_path: Path) -> list[dict[str, Any]]:
    """euroSciVoc.json aus einem CORDIS-Projekt-ZIP lesen."""
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            if "euroSciVoc.json" not in zf.namelist():
                logger.debug(
                    "euroscivoc_json_nicht_gefunden",
                    zip_datei=zip_path.name,
                )
                return []
            with zf.open("euroSciVoc.json") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return []
    except (zipfile.BadZipFile, json.JSONDecodeError, KeyError) as exc:
        logger.error(
            "euroscivoc_zip_lesefehler",
            zip_datei=zip_path.name,
            error=str(exc),
        )
        return []


# ---------------------------------------------------------------------------
# Batch-Insert: Taxonomie
# ---------------------------------------------------------------------------


async def _insert_taxonomy_batch(
    pool: asyncpg.Pool,
    records: list[dict[str, Any]],
) -> tuple[int, int]:
    """Taxonomie-Eintraege batchweise einfuegen.

    ON CONFLICT (code) DO UPDATE fuer Upsert-Verhalten.
    DEFERRABLE INITIALLY DEFERRED fuer self-referencing FK.
    """
    if not records:
        return 0, 0

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SET CONSTRAINTS ALL DEFERRED")
            await conn.executemany(
                """
                INSERT INTO cordis_schema.euroscivoc (
                    code, label_en, label_de, parent_code, level
                ) VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (code) DO UPDATE SET
                    label_en    = EXCLUDED.label_en,
                    label_de    = COALESCE(EXCLUDED.label_de, cordis_schema.euroscivoc.label_de),
                    parent_code = COALESCE(EXCLUDED.parent_code, cordis_schema.euroscivoc.parent_code),
                    level       = EXCLUDED.level
                """,
                [
                    (
                        r["code"],
                        r["label_en"],
                        r["label_de"],
                        r["parent_code"],
                        r["level"],
                    )
                    for r in records
                ],
            )

    return len(records), 0


# ---------------------------------------------------------------------------
# Batch-Insert: Projekt-Zuordnungen
# ---------------------------------------------------------------------------


async def _insert_junction_batch(
    pool: asyncpg.Pool,
    batch: list[tuple[int, str]],
) -> tuple[int, int]:
    """Projekt-EuroSciVoc-Zuordnungen batchweise einfuegen.

    Nutzt Staging-Tabelle fuer effizienten JOIN.
    """
    if not batch:
        return 0, 0

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("""
                CREATE TEMP TABLE _staging_pe (
                    project_id      INTEGER,
                    euroscivoc_code TEXT
                ) ON COMMIT DROP
            """)

            await conn.copy_records_to_table(
                "_staging_pe",
                records=batch,
                columns=["project_id", "euroscivoc_code"],
            )

            result = await conn.execute("""
                INSERT INTO cordis_schema.project_euroscivoc (project_id, euroscivoc_id)
                SELECT s.project_id, e.id
                FROM _staging_pe s
                JOIN cordis_schema.euroscivoc e ON e.code = s.euroscivoc_code
                JOIN cordis_schema.projects p ON p.id = s.project_id
                ON CONFLICT (project_id, euroscivoc_id) DO NOTHING
            """)

            count_str = result.split()[-1] if result else "0"
            imported = int(count_str) if count_str.isdigit() else 0

    return imported, len(batch) - imported


# ---------------------------------------------------------------------------
# Haupt-Import-Funktion
# ---------------------------------------------------------------------------


async def import_euroscivoc_bulk(
    pool: asyncpg.Pool,
    data_dir: str,
    batch_size: int = 5_000,
    progress_cb: Any = None,
) -> ImportResult:
    """EuroSciVoc-Bulk-Import aus CORDIS-JSON-ZIPs.

    Schritt 1: euroSciVoc.json aus allen Projekt-ZIPs lesen.
    Schritt 2: Taxonomie-Baum aufbauen und in DB einfuegen.
    Schritt 3: Projekt-Zuordnungen (Junction) einfuegen.
    """
    result = ImportResult(source="EUROSCIVOC")
    start_time = time.monotonic()

    cordis_dir = Path(data_dir) / "CORDIS"
    if not cordis_dir.exists():
        result.errors.append(f"CORDIS-Verzeichnis nicht gefunden: {cordis_dir}")
        logger.error("euroscivoc_verzeichnis_fehlt", path=str(cordis_dir))
        return result

    # Projekt-ZIPs finden
    zip_files = sorted(
        f for f in cordis_dir.glob("cordis-*projects-json.zip")
    )

    if not zip_files:
        result.errors.append(f"Keine CORDIS-Projekt-ZIPs in {cordis_dir}")
        logger.warning("keine_cordis_zips", path=str(cordis_dir))
        return result

    logger.info(
        "euroscivoc_import_gestartet",
        verzeichnis=str(cordis_dir),
        zip_dateien=len(zip_files),
    )

    # -------------------------------------------------------------------
    # Schritt 1: Alle Eintraege aus den ZIPs lesen
    # -------------------------------------------------------------------
    all_entries: list[dict[str, Any]] = []

    for zip_path in zip_files:
        entries = _read_euroscivoc_from_zip(zip_path)
        logger.info(
            "euroscivoc_zip_gelesen",
            zip_datei=zip_path.name,
            eintraege=len(entries),
        )
        all_entries.extend(entries)
        result.files_processed += 1

    logger.info("euroscivoc_gesamt_eintraege", total=len(all_entries))

    if not all_entries:
        result.errors.append("Keine EuroSciVoc-Eintraege in den ZIPs gefunden")
        return result

    # -------------------------------------------------------------------
    # Schritt 2: Taxonomie aufbauen und einfuegen
    # -------------------------------------------------------------------
    taxonomy = _build_taxonomy_from_entries(all_entries)
    logger.info("euroscivoc_taxonomie_aufgebaut", codes=len(taxonomy))

    # Nach Level sortiert einfuegen (Eltern zuerst)
    sorted_taxonomy = sorted(taxonomy.values(), key=lambda r: r["level"])

    taxonomy_imported = 0
    for i in range(0, len(sorted_taxonomy), batch_size):
        batch = sorted_taxonomy[i: i + batch_size]
        imported, skipped = await _insert_taxonomy_batch(pool, batch)
        taxonomy_imported += imported
        logger.info(
            "euroscivoc_taxonomie_batch",
            importiert=taxonomy_imported,
            total=len(sorted_taxonomy),
        )

    result.details["taxonomy_imported"] = taxonomy_imported

    # -------------------------------------------------------------------
    # Schritt 3: Projekt-Zuordnungen einfuegen
    # -------------------------------------------------------------------
    junction_imported = 0
    junction_skipped = 0

    # Eintraege mit projectID sammeln
    junction_pairs: list[tuple[int, str]] = []
    for entry in all_entries:
        project_id = entry.get("projectID")
        code = (entry.get("euroSciVocCode") or "").strip()
        if project_id and code:
            junction_pairs.append((int(project_id), code))

    logger.info("euroscivoc_junction_paare", total=len(junction_pairs))

    for i in range(0, len(junction_pairs), batch_size):
        batch = junction_pairs[i: i + batch_size]
        try:
            imported, skipped = await _insert_junction_batch(pool, batch)
            junction_imported += imported
            junction_skipped += skipped
        except Exception as exc:
            error_msg = f"Junction-Batch fehlgeschlagen bei Offset {i}: {exc}"
            result.errors.append(error_msg)
            logger.error("euroscivoc_junction_fehler", error=str(exc), offset=i)

        if (i + batch_size) % 20_000 == 0:
            logger.info(
                "euroscivoc_junction_fortschritt",
                importiert=junction_imported,
                uebersprungen=junction_skipped,
                total=len(junction_pairs),
            )

    result.details["junction_imported"] = junction_imported
    result.details["junction_skipped"] = junction_skipped

    # Gesamtstatistiken
    result.records_imported = taxonomy_imported + junction_imported
    result.records_skipped = junction_skipped
    result.duration_seconds = round(time.monotonic() - start_time, 2)

    logger.info(
        "euroscivoc_import_abgeschlossen",
        dateien_verarbeitet=result.files_processed,
        taxonomie_importiert=taxonomy_imported,
        zuordnungen_importiert=junction_imported,
        uebersprungen=junction_skipped,
        fehler=len(result.errors),
        dauer_sekunden=result.duration_seconds,
    )

    return result
