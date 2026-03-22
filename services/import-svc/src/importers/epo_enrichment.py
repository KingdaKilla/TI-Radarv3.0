"""EPO Enrichment — CPC-Codes und Applicant-Countries fuer bestehende Patente nachladen.

Liest die gleichen DOCDB-XML-Archive wie der Importer, extrahiert aber nur:
  - publication_number + publication_year (fuer den JOIN)
  - cpc_codes (TEXT[])
  - applicant_countries (TEXT[])

und aktualisiert die bestehenden Zeilen in patent_schema.patents per
Batch-UPDATE ueber eine Staging-Tabelle.

Aufruf:
    docker compose exec import-svc python -m import_svc.cli enrich-epo
"""

from __future__ import annotations

import io
import time
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, Generator

import structlog
from lxml import etree

if TYPE_CHECKING:
    import asyncpg

logger = structlog.get_logger(__name__)

EXCH_NS = "http://www.epo.org/exchange"


def _text(element: etree._Element | None) -> str:
    if element is None:
        return ""
    return (element.text or "").strip()


def _parse_date(date_str: str) -> date | None:
    """Datum aus YYYYMMDD- oder YYYY-MM-DD-Format parsen."""
    if not date_str:
        return None
    try:
        if len(date_str) == 8 and date_str.isdigit():
            return datetime.strptime(date_str, "%Y%m%d").date()
        if len(date_str) == 10 and "-" in date_str:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        pass
    return None


@dataclass
class EnrichmentResult:
    """Ergebnis eines Enrichment-Vorgangs."""
    source: str = "EPO-Enrichment"
    files_processed: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


def _parse_enrichment_data(doc: etree._Element) -> dict | None:
    """Nur CPC-Codes und Laender aus einem Patent-Dokument extrahieren."""
    try:
        country = doc.get("country", "")
        doc_number = doc.get("doc-number", "")
        kind = doc.get("kind", "")
        pub_date_str = doc.get("date-publ", "")

        if not doc_number:
            return None

        publication_number = f"{country}{doc_number}{kind}".strip()

        # publication_year berechnen
        pub_year = None
        if pub_date_str and len(pub_date_str) >= 4:
            try:
                pub_year = int(pub_date_str[:4])
            except ValueError:
                pass
        if pub_year is None or pub_year < 1900 or pub_year > 2100:
            return None

        # CPC-Codes aus <classification-symbol>
        cpc_codes: list[str] = []
        cpc_elems = doc.findall(f".//{{{EXCH_NS}}}patent-classification")
        if not cpc_elems:
            cpc_elems = doc.findall(".//patent-classification")
        for cpc in cpc_elems:
            scheme_elem = cpc.find(f"{{{EXCH_NS}}}classification-scheme")
            if scheme_elem is None:
                scheme_elem = cpc.find("classification-scheme")
            scheme = ""
            if scheme_elem is not None:
                scheme = scheme_elem.get("scheme", "") or _text(scheme_elem)
            if scheme.upper() not in ("CPC", "CPCI", "CPCA", ""):
                continue

            sym_elem = cpc.find(f"{{{EXCH_NS}}}classification-symbol")
            if sym_elem is None:
                sym_elem = cpc.find("classification-symbol")
            if sym_elem is not None and _text(sym_elem):
                raw = _text(sym_elem).replace(" ", "")
                if raw:
                    cpc_codes.append(raw)

        # Applicant-Countries aus <residence>/<country>
        applicant_countries: list[str] = []
        applicants_elem = doc.find(f".//{{{EXCH_NS}}}applicants")
        if applicants_elem is None:
            applicants_elem = doc.find(".//applicants")
        if applicants_elem is not None:
            for applicant in applicants_elem:
                data_format = applicant.get("data-format", "")
                if data_format != "docdb":
                    continue
                res_elem = applicant.find(f".//{{{EXCH_NS}}}residence")
                if res_elem is None:
                    res_elem = applicant.find(".//residence")
                if res_elem is not None:
                    c_elem = res_elem.find(f"{{{EXCH_NS}}}country")
                    if c_elem is None:
                        c_elem = res_elem.find("country")
                    ctry = _text(c_elem)
                    if ctry:
                        applicant_countries.append(ctry)

        # Filing-Date (Anmeldedatum) extrahieren fuer UC12 Time-to-Grant
        filing_date = None
        app_ref = doc.find(f".//{{{EXCH_NS}}}application-reference")
        if app_ref is None:
            app_ref = doc.find(".//application-reference")
        if app_ref is not None:
            date_elem = app_ref.find(f".//{{{EXCH_NS}}}date")
            if date_elem is None:
                date_elem = app_ref.find(".//date")
            filing_date = _parse_date(_text(date_elem))

        # Nur zurueckgeben wenn Daten vorhanden
        if not cpc_codes and not applicant_countries and filing_date is None:
            return None

        return {
            "publication_number": publication_number,
            "publication_year": pub_year,
            "cpc_codes": cpc_codes or None,
            "applicant_countries": applicant_countries or None,
            "filing_date": filing_date,
        }
    except Exception as exc:
        logger.warning("enrichment_parse_fehler", error=str(exc))
        return None


def _iterparse_enrichment(
    source: str | BinaryIO,
    source_label: str = "<stream>",
) -> Generator[dict, None, None]:
    """Enrichment-Daten aus einem XML-Stream per iterparse yielden."""
    tags = (
        f"{{{EXCH_NS}}}exchange-document",
        "exchange-document",
    )
    try:
        context = etree.iterparse(source, events=("end",), tag=tags, recover=True)
        for _event, elem in context:
            data = _parse_enrichment_data(elem)
            if data:
                yield data
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
    except etree.XMLSyntaxError as exc:
        logger.warning("xml_syntax_fehler", source=source_label, error=str(exc))
    except Exception as exc:
        logger.error("xml_parse_fehler", source=source_label, error=str(exc))


def _iter_enrichment_from_zip(
    zip_path: Path,
) -> Generator[dict, None, None]:
    """Enrichment-Daten aus verschachtelten ZIP-Archiven streamen."""
    try:
        with zipfile.ZipFile(zip_path, "r") as outer_zf:
            inner_zips = sorted(
                entry for entry in outer_zf.namelist()
                if entry.startswith("Root/DOC/") and entry.lower().endswith(".zip")
            )

            if not inner_zips:
                xml_entries = sorted(
                    entry for entry in outer_zf.namelist()
                    if entry.lower().endswith(".xml")
                    and "index" not in entry.lower()
                    and not entry.startswith("__MACOSX")
                )
                for entry_name in xml_entries:
                    with outer_zf.open(entry_name) as xml_stream:
                        yield from _iterparse_enrichment(
                            xml_stream,
                            source_label=f"{zip_path.name}/{entry_name}",
                        )
                return

            for inner_idx, inner_name in enumerate(inner_zips):
                try:
                    inner_data = outer_zf.read(inner_name)
                    inner_zf = zipfile.ZipFile(io.BytesIO(inner_data))
                    xml_entries = [e for e in inner_zf.namelist() if e.lower().endswith(".xml")]

                    for xml_entry in xml_entries:
                        source_label = f"{zip_path.name}/{inner_name}/{xml_entry}"
                        if (inner_idx + 1) % 10 == 0 or inner_idx == 0:
                            logger.info(
                                "enrichment_inner_zip",
                                zip=zip_path.name,
                                inner=inner_name.split("/")[-1],
                                progress=f"{inner_idx + 1}/{len(inner_zips)}",
                            )
                        with inner_zf.open(xml_entry) as xml_stream:
                            yield from _iterparse_enrichment(xml_stream, source_label)

                    inner_zf.close()
                    del inner_data
                except Exception as exc:
                    logger.error(
                        "enrichment_inner_zip_fehler",
                        zip=zip_path.name,
                        inner=inner_name,
                        error=str(exc),
                    )
    except Exception as exc:
        logger.error("enrichment_zip_fehler", zip=zip_path.name, error=str(exc))


async def _update_enrichment_batch(
    pool: asyncpg.Pool,
    batch: list[dict],
) -> int:
    """Batch von Enrichment-Daten per Staging-Tabelle in die DB schreiben."""
    if not batch:
        return 0

    records = [
        (
            rec["publication_number"],
            rec["publication_year"],
            rec["cpc_codes"],
            rec["applicant_countries"],
            rec.get("filing_date"),
        )
        for rec in batch
    ]

    updated = 0
    async with pool.acquire() as conn:
        async with conn.transaction():
            try:
                await conn.execute("""
                    CREATE TEMP TABLE _staging_enrichment (
                        publication_number TEXT,
                        publication_year   SMALLINT,
                        cpc_codes          TEXT[],
                        applicant_countries TEXT[],
                        filing_date        DATE
                    ) ON COMMIT DROP
                """)

                await conn.copy_records_to_table(
                    "_staging_enrichment",
                    records=records,
                    columns=["publication_number", "publication_year", "cpc_codes", "applicant_countries", "filing_date"],
                )

                result = await conn.execute("""
                    UPDATE patent_schema.patents p
                    SET
                        cpc_codes = COALESCE(s.cpc_codes, p.cpc_codes),
                        applicant_countries = COALESCE(s.applicant_countries, p.applicant_countries),
                        filing_date = COALESCE(s.filing_date, p.filing_date)
                    FROM _staging_enrichment s
                    WHERE p.publication_number = s.publication_number
                      AND p.publication_year = s.publication_year
                      AND (p.cpc_codes IS NULL OR p.applicant_countries IS NULL OR p.filing_date IS NULL)
                """)

                count_str = result.split()[-1] if result else "0"
                updated = int(count_str) if count_str.isdigit() else 0

            except Exception as exc:
                logger.error("enrichment_batch_fehler", error=str(exc), batch_size=len(batch))
                raise

    return updated


async def _ensure_progress_table(pool: asyncpg.Pool) -> None:
    """Fortschritts-Tabelle fuer ZIP-Tracking anlegen (idempotent)."""
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS patent_schema.enrichment_progress (
                zip_name   TEXT PRIMARY KEY,
                updated_count INTEGER NOT NULL DEFAULT 0,
                completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)


async def _get_completed_zips(pool: asyncpg.Pool) -> set[str]:
    """Bereits verarbeitete ZIP-Dateinamen laden."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT zip_name FROM patent_schema.enrichment_progress"
        )
    return {row["zip_name"] for row in rows}


async def _mark_zip_completed(
    pool: asyncpg.Pool, zip_name: str, updated_count: int,
) -> None:
    """ZIP als verarbeitet markieren."""
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO patent_schema.enrichment_progress (zip_name, updated_count)
               VALUES ($1, $2)
               ON CONFLICT (zip_name) DO UPDATE
                 SET updated_count = EXCLUDED.updated_count,
                     completed_at = NOW()""",
            zip_name,
            updated_count,
        )


async def enrich_epo_patents(
    pool: asyncpg.Pool,
    data_dir: str,
    batch_size: int = 10_000,
    progress_cb: Any = None,
) -> EnrichmentResult:
    """CPC-Codes und Applicant-Countries fuer bestehende Patente nachladen.

    Liest die gleichen ZIP-Archive wie der Importer, extrahiert nur die
    fehlenden Felder und aktualisiert die bestehenden Zeilen.

    **Resume-Faehig**: Bereits verarbeitete ZIPs werden uebersprungen
    (Fortschritt in patent_schema.enrichment_progress gespeichert).
    """
    result = EnrichmentResult()
    start_time = time.monotonic()

    epo_dir = Path(data_dir) / "EPO"
    if not epo_dir.exists():
        result.errors.append(f"EPO-Verzeichnis nicht gefunden: {epo_dir}")
        return result

    zip_files = sorted(epo_dir.glob("*.zip"))
    if not zip_files:
        result.errors.append(f"Keine ZIP-Dateien in {epo_dir}")
        return result

    # Fortschritts-Tabelle + bereits erledigte ZIPs laden
    await _ensure_progress_table(pool)
    completed_zips = await _get_completed_zips(pool)
    skipped = len([z for z in zip_files if z.name in completed_zips])

    logger.info(
        "enrichment_gestartet",
        verzeichnis=str(epo_dir),
        anzahl_zip=len(zip_files),
        bereits_erledigt=skipped,
        verbleibend=len(zip_files) - skipped,
        batch_size=batch_size,
    )

    batch: list[dict] = []
    total_updated = 0

    async def _flush() -> None:
        nonlocal batch, total_updated
        if not batch:
            return
        try:
            updated = await _update_enrichment_batch(pool, batch)
            total_updated += updated
        except Exception as exc:
            result.errors.append(f"Enrichment-Batch fehlgeschlagen: {exc}")
        batch = []

    for zip_idx, zip_file in enumerate(zip_files):
        # Bereits verarbeitete ZIPs ueberspringen
        if zip_file.name in completed_zips:
            result.files_processed += 1
            result.records_skipped += 1
            continue

        logger.info(
            "enrichment_zip",
            zip=zip_file.name,
            size_mb=round(zip_file.stat().st_size / (1024 * 1024), 1),
            progress=f"{zip_idx + 1}/{len(zip_files)}",
            uebersprungen=skipped,
        )

        zip_updated_before = total_updated
        try:
            for enrichment_data in _iter_enrichment_from_zip(zip_file):
                batch.append(enrichment_data)
                if len(batch) >= batch_size:
                    await _flush()
                    total = total_updated
                    if total % 100_000 < batch_size:
                        logger.info(
                            "enrichment_fortschritt",
                            aktualisiert=total_updated,
                            aktuelle_zip=zip_file.name,
                        )

            # Restlichen Batch der ZIP flushen
            await _flush()

            # ZIP als erledigt markieren
            zip_updated = total_updated - zip_updated_before
            await _mark_zip_completed(pool, zip_file.name, zip_updated)

            result.files_processed += 1
            if progress_cb:
                progress_cb(result.files_processed, total_updated, zip_file.name)

        except Exception as exc:
            result.errors.append(f"Fehler bei ZIP {zip_file.name}: {exc}")

    result.records_updated = total_updated
    result.duration_seconds = round(time.monotonic() - start_time, 2)

    logger.info(
        "enrichment_abgeschlossen",
        dateien=result.files_processed,
        aktualisiert=result.records_updated,
        uebersprungen=skipped,
        dauer_sekunden=result.duration_seconds,
    )

    return result
