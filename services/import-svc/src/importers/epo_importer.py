"""EPO Bulk-Importer — DOCDB-XML aus verschachtelten ZIP-Archiven in patent_schema.patents laden.

Liest EPO-Bulk-Downloads im DOCDB-XML-Format. Die EPO-Daten liegen als
verschachtelte ZIP-Archive vor:

    /data/bulk/EPO/
        docdb_xml_bck_202534_001_A.zip          (aeusseres ZIP, ~1.4 GB)
            Root/DOC/DOCDB-202534-001-CA-0521.zip   (inneres ZIP)
                DOCDB-202534-001-CA-0521.xml         (DOCDB-XML, ~90 MB)

Jedes aeussere ZIP wird geoeffnet, die inneren ZIPs in Root/DOC/ werden
in den Speicher geladen und deren XML-Eintraege per lxml iterparse
speichereffizient geparst.

Ziel-Tabellen:
    patent_schema.patents        — Stammdaten je Patent
    patent_schema.patent_cpc     — Junction-Tabelle Patent <-> CPC-Codes
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

# DOCDB-XML Namespace
EXCH_NS = "http://www.epo.org/exchange"
NSMAP = {"exch": EXCH_NS}


# ---------------------------------------------------------------------------
# Ergebnis-Datenklasse
# ---------------------------------------------------------------------------


@dataclass
class ImportResult:
    """Ergebnis eines Bulk-Import-Vorgangs."""

    source: str = "EPO"
    files_processed: int = 0
    records_imported: int = 0
    records_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


# ---------------------------------------------------------------------------
# XML-Parsing-Hilfsfunktionen
# ---------------------------------------------------------------------------


def _text(element: etree._Element | None) -> str:
    """Sicherer Textzugriff auf ein XML-Element (leerer String bei None)."""
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


def _parse_patent_document(doc: etree._Element) -> dict | None:
    """Einzelnes Patent-Dokument aus DOCDB-XML extrahieren.

    Unterstuetzt sowohl Namespace-qualifizierte (exch:) als auch
    unqualifizierte Elementnamen.
    """
    try:
        # Attribute direkt vom exchange-document Element
        country = doc.get("country", "")
        doc_number = doc.get("doc-number", "")
        kind = doc.get("kind", "")
        family_id = doc.get("family-id", "")

        if not doc_number:
            return None

        publication_number = f"{country}{doc_number}{kind}".strip()

        # Publikationsdatum aus dem Attribut
        pub_date_str = doc.get("date-publ", "")
        publication_date = _parse_date(pub_date_str)

        # Titel extrahieren — mit und ohne Namespace
        title = ""
        # Versuche mit Namespace
        title_elems = doc.findall(f".//{{{EXCH_NS}}}invention-title")
        if not title_elems:
            title_elems = doc.findall(".//invention-title")
        for title_elem in title_elems:
            lang = title_elem.get("lang", "").lower()
            text = _text(title_elem)
            if lang == "en" and text:
                title = text
                break
            if not title and text:
                title = text

        # CPC-Codes extrahieren
        cpc_codes: list[str] = []
        # Mit Namespace
        cpc_elems = doc.findall(f".//{{{EXCH_NS}}}patent-classification")
        if not cpc_elems:
            cpc_elems = doc.findall(".//patent-classification")
        for cpc in cpc_elems:
            # classification-scheme pruefen
            scheme_elem = cpc.find(f"{{{EXCH_NS}}}classification-scheme")
            if scheme_elem is None:
                scheme_elem = cpc.find("classification-scheme")
            scheme = ""
            if scheme_elem is not None:
                scheme = scheme_elem.get("scheme", "") or _text(scheme_elem)
            if scheme.upper() not in ("CPC", "CPCI", "CPCA", ""):
                continue

            # Primaer: <classification-symbol> (DOCDB-XML Standardformat)
            sym_elem = cpc.find(f"{{{EXCH_NS}}}classification-symbol")
            if sym_elem is None:
                sym_elem = cpc.find("classification-symbol")
            if sym_elem is not None and _text(sym_elem):
                # Symbol normalisieren: Leerzeichen entfernen, z.B. "H04N   7/152" -> "H04N7/152"
                raw = _text(sym_elem).replace(" ", "")
                if raw:
                    cpc_codes.append(raw)
                    continue

            # Fallback: Einzelne Felder (aeltere XML-Formate)
            section = _text(cpc.find(f"{{{EXCH_NS}}}section") or cpc.find("section"))
            cls = _text(cpc.find(f"{{{EXCH_NS}}}class") or cpc.find("class"))
            subclass = _text(cpc.find(f"{{{EXCH_NS}}}subclass") or cpc.find("subclass"))
            main_group = _text(cpc.find(f"{{{EXCH_NS}}}main-group") or cpc.find("main-group"))
            subgroup = _text(cpc.find(f"{{{EXCH_NS}}}subgroup") or cpc.find("subgroup"))
            code = f"{section}{cls}{subclass}{main_group}/{subgroup}".strip()
            if code and code != "/":
                cpc_codes.append(code)

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

        # Anmelder extrahieren — bevorzugt data-format="docdb" (mit Land)
        # und "docdba" (bereinigter Name). Wir sammeln beide und mergen.
        applicant_names: list[str] = []
        applicant_countries: list[str] = []
        applicants_elem = doc.find(f".//{{{EXCH_NS}}}applicants")
        if applicants_elem is None:
            applicants_elem = doc.find(".//applicants")
        if applicants_elem is not None:
            # Erst docdb-Format sammeln (hat Laenderinfo in <residence>/<country>)
            docdb_entries: list[tuple[str, str]] = []
            docdba_names: list[str] = []

            for applicant in applicants_elem:
                data_format = applicant.get("data-format", "")
                name_elem = applicant.find(f".//{{{EXCH_NS}}}name")
                if name_elem is None:
                    name_elem = applicant.find(".//name")
                name = _text(name_elem)
                if not name:
                    continue

                if data_format == "docdb":
                    # Land aus <residence>/<country> extrahieren
                    country_code = ""
                    res_elem = applicant.find(f".//{{{EXCH_NS}}}residence")
                    if res_elem is None:
                        res_elem = applicant.find(".//residence")
                    if res_elem is not None:
                        c_elem = res_elem.find(f"{{{EXCH_NS}}}country")
                        if c_elem is None:
                            c_elem = res_elem.find("country")
                        country_code = _text(c_elem)
                    docdb_entries.append((name, country_code))
                elif data_format == "docdba":
                    docdba_names.append(name)

            # Bevorzugt docdba-Namen (bereinigt), mit Laendern aus docdb
            if docdba_names:
                for i, name in enumerate(docdba_names):
                    applicant_names.append(name)
                    # Laendercode aus docdb zuordnen (gleicher Index)
                    if i < len(docdb_entries):
                        applicant_countries.append(docdb_entries[i][1])
                    else:
                        applicant_countries.append("")
            elif docdb_entries:
                for name, ctry in docdb_entries:
                    applicant_names.append(name)
                    applicant_countries.append(ctry)

        # TODO 9.17: Patent-Zitations-Extraktion (UC-F)
        # EPO DOCDB XML enthaelt <references-cited> mit <citation> Kindern:
        #   <exch:references-cited>
        #     <exch:citation ct="patcit">
        #       <exch:patcit dnum-type="epodoc">
        #         <document-id>
        #           <country>EP</country>
        #           <doc-number>1234567</doc-number>
        #           <kind>A1</kind>
        #         </document-id>
        #       </exch:patcit>
        #       <category>X</category>
        #       <cited-phase>search</cited-phase>
        #     </exch:citation>
        #   </exch:references-cited>
        #
        # Extraktion in patent_schema.patent_citations Tabelle:
        #   citing_patent  = publication_number (aktuelles Dokument)
        #   cited_patent   = "{country}{doc_number}{kind}" aus <patcit>
        #   citation_category = <category> Text (X, Y, A, D, ...)
        #   cited_phase    = <cited-phase> Text (search, examination, opposition)
        #   citing_year    = publication_date.year
        #
        # Implementierung: references-cited parsen, Liste von dicts zurueckgeben,
        # Batch-Insert analog zu _insert_patent_batch in separater Funktion.

        return {
            "publication_number": publication_number,
            "country": country,
            "doc_number": doc_number,
            "kind": kind,
            "title": title[:2000] if title else "",
            "publication_date": publication_date,
            "filing_date": filing_date,
            "family_id": family_id,
            "cpc_codes": cpc_codes,
            "applicant_names": applicant_names,
            "applicant_countries": applicant_countries,
        }
    except Exception as exc:
        logger.warning("patent_parse_fehler", error=str(exc))
        return None


def _iterparse_xml_stream(
    source: str | BinaryIO,
    source_label: str = "<stream>",
) -> Generator[dict, None, None]:
    """Patent-Dokumente aus einem XML-Stream per iterparse yielden.

    Verwendet den Namespace-qualifizierten Tag fuer DOCDB-XML.
    """
    # Tags mit und ohne Namespace
    tags = (
        f"{{{EXCH_NS}}}exchange-document",
        "exchange-document",
    )

    try:
        context = etree.iterparse(
            source,
            events=("end",),
            tag=tags,
            recover=True,
        )
        for _event, elem in context:
            patent = _parse_patent_document(elem)
            if patent:
                yield patent
            # Speicher freigeben
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]

    except etree.XMLSyntaxError as exc:
        logger.warning("xml_syntax_fehler", source=source_label, error=str(exc))
    except Exception as exc:
        logger.error("xml_parse_fehler", source=source_label, error=str(exc))


# ---------------------------------------------------------------------------
# ZIP-Verarbeitung (verschachtelt: aeusseres ZIP -> innere ZIPs -> XML)
# ---------------------------------------------------------------------------


def _iter_patents_from_zip(
    zip_path: Path,
) -> Generator[dict, None, None]:
    """Patent-Dokumente aus einem verschachtelten ZIP-Archiv streamen.

    EPO-Bulk-Downloads haben folgende Struktur:
        aeusseres.zip/
            Root/DOC/DOCDB-*.zip   (innere ZIPs)
                DOCDB-*.xml        (DOCDB-XML mit Patenten)
            Root/index.xml         (Index, wird ignoriert)

    Jedes innere ZIP wird in den Speicher geladen (typisch 8-10 MB),
    das enthaltene XML per iterparse geparst.
    """
    try:
        with zipfile.ZipFile(zip_path, "r") as outer_zf:
            # Innere ZIPs in Root/DOC/ finden
            inner_zips = sorted(
                entry
                for entry in outer_zf.namelist()
                if entry.startswith("Root/DOC/")
                and entry.lower().endswith(".zip")
            )

            if not inner_zips:
                # Fallback: Direkte XML-Eintraege (falls kein verschachteltes Format)
                xml_entries = sorted(
                    entry
                    for entry in outer_zf.namelist()
                    if entry.lower().endswith(".xml")
                    and "index" not in entry.lower()
                    and not entry.startswith("__MACOSX")
                )
                if xml_entries:
                    logger.info(
                        "zip_direkte_xml",
                        zip_datei=zip_path.name,
                        anzahl=len(xml_entries),
                    )
                    for entry_name in xml_entries:
                        with outer_zf.open(entry_name) as xml_stream:
                            yield from _iterparse_xml_stream(
                                xml_stream,
                                source_label=f"{zip_path.name}/{entry_name}",
                            )
                else:
                    logger.warning(
                        "zip_keine_eintraege",
                        zip_datei=zip_path.name,
                    )
                return

            logger.info(
                "zip_innere_zips_gefunden",
                zip_datei=zip_path.name,
                anzahl_inner=len(inner_zips),
            )

            for inner_idx, inner_name in enumerate(inner_zips):
                try:
                    # Inneres ZIP in den Speicher laden
                    inner_data = outer_zf.read(inner_name)
                    inner_zf = zipfile.ZipFile(io.BytesIO(inner_data))

                    # XML-Eintraege im inneren ZIP finden
                    xml_entries = [
                        e for e in inner_zf.namelist()
                        if e.lower().endswith(".xml")
                    ]

                    for xml_entry in xml_entries:
                        source_label = f"{zip_path.name}/{inner_name}/{xml_entry}"
                        if (inner_idx + 1) % 5 == 0 or inner_idx == 0:
                            logger.info(
                                "inner_zip_verarbeitung",
                                aeusseres_zip=zip_path.name,
                                inneres_zip=inner_name.split("/")[-1],
                                fortschritt=f"{inner_idx + 1}/{len(inner_zips)}",
                            )

                        with inner_zf.open(xml_entry) as xml_stream:
                            yield from _iterparse_xml_stream(
                                xml_stream,
                                source_label=source_label,
                            )

                    inner_zf.close()
                    # Speicher freigeben
                    del inner_data

                except Exception as exc:
                    logger.error(
                        "inner_zip_fehler",
                        aeusseres_zip=zip_path.name,
                        inneres_zip=inner_name,
                        error=str(exc),
                    )

    except zipfile.BadZipFile as exc:
        logger.error("zip_beschaedigt", zip_datei=zip_path.name, error=str(exc))
    except Exception as exc:
        logger.error("zip_oeffnen_fehler", zip_datei=zip_path.name, error=str(exc))


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
# Batch-Insert via COPY-Protokoll
# ---------------------------------------------------------------------------


async def _insert_patent_batch(
    pool: asyncpg.Pool,
    batch: list[dict],
) -> tuple[int, int]:
    """Batch von Patenten via COPY in patent_schema.patents einfuegen.

    Passt die Daten an das tatsaechliche Schema an:
    - applicant_names: text (komma-getrennt, nicht Array)
    - applicant_countries: text[]
    - cpc_codes: text[] (volles CPC-Format)
    - publication_year: smallint (aus publication_date berechnet)
    - country: char(2) Check-Constraint
    - kind: varchar(4) Check-Constraint '^[A-Z][0-9]?$'
    """
    if not batch:
        return 0, 0

    patent_records: list[tuple] = []

    for patent in batch:
        # publication_year aus publication_date berechnen
        pub_date = patent["publication_date"]
        if pub_date is not None:
            pub_year = pub_date.year
        else:
            # Ohne Datum kein gueltiger Eintrag (publication_year NOT NULL)
            continue

        # Check-Constraint: publication_year >= 1900 AND <= 2100
        if pub_year < 1900 or pub_year > 2100:
            continue

        # country muss genau 2 Grossbuchstaben sein
        country = patent["country"][:2].upper()
        if len(country) != 2 or not country.isalpha():
            continue

        # kind: Pruefe Check-Constraint '^[A-Z][0-9]?$'
        kind = patent["kind"]
        if kind:
            # Nur 1-2 Zeichen: Ein Buchstabe + optionale Ziffer
            kind = kind[:2]
            if not (len(kind) >= 1 and kind[0].isalpha() and kind[0].isupper()):
                kind = None

        # applicant_names als komma-getrennter Text (Spalte ist TEXT, nicht TEXT[])
        applicant_text = "; ".join(patent["applicant_names"]) if patent["applicant_names"] else ""

        # applicant_countries: leere Strings entfernen
        app_countries = [c for c in patent["applicant_countries"] if c] if patent["applicant_countries"] else None

        patent_records.append((
            patent["publication_number"],
            country,
            patent["doc_number"],
            kind or None,
            patent["title"],
            pub_date,
            pub_year,
            patent["family_id"],
            applicant_text,
            app_countries or None,
            patent["cpc_codes"] or None,
            patent.get("filing_date"),
        ))

    if not patent_records:
        return 0, 0

    imported = 0
    skipped = 0

    async with pool.acquire() as conn:
        async with conn.transaction():
            try:
                await conn.execute("""
                    CREATE TEMP TABLE _staging_patents (
                        publication_number TEXT,
                        country            TEXT,
                        doc_number         TEXT,
                        kind               TEXT,
                        title              TEXT,
                        publication_date   DATE,
                        publication_year   SMALLINT,
                        family_id          TEXT,
                        applicant_names    TEXT,
                        applicant_countries TEXT[],
                        cpc_codes          TEXT[],
                        filing_date        DATE
                    ) ON COMMIT DROP
                """)

                await conn.copy_records_to_table(
                    "_staging_patents",
                    records=patent_records,
                    columns=[
                        "publication_number", "country", "doc_number", "kind",
                        "title", "publication_date", "publication_year",
                        "family_id", "applicant_names", "applicant_countries",
                        "cpc_codes", "filing_date",
                    ],
                )

                result = await conn.execute("""
                    INSERT INTO patent_schema.patents (
                        publication_number, country, doc_number, kind,
                        title, publication_date, publication_year,
                        family_id, applicant_names, applicant_countries,
                        cpc_codes, filing_date
                    )
                    SELECT
                        publication_number, country, doc_number, kind,
                        title, publication_date, publication_year,
                        family_id, applicant_names, applicant_countries,
                        cpc_codes, filing_date
                    FROM _staging_patents
                    ON CONFLICT (publication_number, publication_year) DO NOTHING
                """)

                count_str = result.split()[-1] if result else "0"
                imported = int(count_str) if count_str.isdigit() else len(patent_records)
                skipped = len(patent_records) - imported

            except Exception as exc:
                logger.error(
                    "batch_insert_fehler",
                    error=str(exc),
                    batch_size=len(patent_records),
                )
                raise

    return imported, skipped


# ---------------------------------------------------------------------------
# Haupt-Import-Funktion
# ---------------------------------------------------------------------------


async def import_epo_bulk(
    pool: asyncpg.Pool,
    data_dir: str,
    batch_size: int = 10_000,
    progress_cb: Any = None,
) -> ImportResult:
    """EPO-Bulk-Import: Verschachtelte ZIP-Archive lesen, parsen, in PostgreSQL laden.

    Args:
        pool: asyncpg Connection-Pool.
        data_dir: Basis-Verzeichnis (EPO-Dateien in data_dir/EPO/).
        batch_size: Anzahl Datensaetze pro COPY-Batch.

    Returns:
        ImportResult mit Statistiken.
    """
    result = ImportResult(source="EPO")
    start_time = time.monotonic()

    epo_dir = Path(data_dir) / "EPO"
    if not epo_dir.exists():
        result.errors.append(f"EPO-Verzeichnis nicht gefunden: {epo_dir}")
        logger.error("epo_verzeichnis_fehlt", path=str(epo_dir))
        return result

    zip_files = sorted(epo_dir.glob("*.zip"))
    xml_files = sorted(epo_dir.glob("*.xml"))

    total_sources = len(zip_files) + len(xml_files)
    if total_sources == 0:
        result.errors.append(f"Keine Dateien in {epo_dir} gefunden")
        return result

    logger.info(
        "epo_import_gestartet",
        verzeichnis=str(epo_dir),
        anzahl_zip=len(zip_files),
        anzahl_xml=len(xml_files),
        batch_size=batch_size,
    )

    batch: list[dict] = []
    total_imported = 0
    total_skipped = 0

    async def _flush_batch() -> None:
        nonlocal batch, total_imported, total_skipped
        if not batch:
            return
        try:
            imported, skipped = await _insert_patent_batch(pool, batch)
            total_imported += imported
            total_skipped += skipped
        except Exception as exc:
            result.errors.append(f"Batch-Insert fehlgeschlagen: {exc}")
            logger.error("epo_batch_fehler", error=str(exc))
        batch = []

    # --- Phase 1: ZIP-Archive verarbeiten ---
    for zip_idx, zip_file in enumerate(zip_files):
        # Inkrementeller Import: bereits importierte Dateien ueberspringen
        if await _is_already_imported(pool, "epo", zip_file.name):
            logger.info(
                "ueberspringe_bereits_importierte_datei",
                datei=zip_file.name,
                quelle="epo",
            )
            result.files_processed += 1
            continue

        zip_start_time = time.monotonic()

        logger.info(
            "epo_zip_verarbeitung",
            zip_datei=zip_file.name,
            groesse_mb=round(zip_file.stat().st_size / (1024 * 1024), 1),
            fortschritt=f"{zip_idx + 1}/{len(zip_files)}",
        )

        try:
            count_before = total_imported + total_skipped + len(batch)

            for patent in _iter_patents_from_zip(zip_file):
                batch.append(patent)
                if len(batch) >= batch_size:
                    await _flush_batch()
                    if progress_cb:
                        progress_cb(result.files_processed, total_imported, zip_file.name)
                    total = total_imported + total_skipped
                    if total % 100_000 < batch_size:
                        logger.info(
                            "epo_import_fortschritt",
                            importiert=total_imported,
                            uebersprungen=total_skipped,
                            aktuelle_zip=zip_file.name,
                        )

            # Restlichen Batch fuer diese ZIP flushen
            if batch:
                await _flush_batch()

            result.files_processed += 1
            count_after = total_imported + total_skipped
            zip_record_count = count_after - count_before
            zip_duration = round(time.monotonic() - zip_start_time, 2)

            logger.info(
                "epo_zip_abgeschlossen",
                zip_datei=zip_file.name,
                patente_in_zip=zip_record_count,
                dauer_sekunden=zip_duration,
            )

            # Import in cross_schema.import_log protokollieren
            await _log_import(
                pool, "epo", zip_file.name, zip_record_count, zip_duration,
            )

            # Progress-Callback aktualisieren
            if progress_cb:
                progress_cb(result.files_processed, total_imported, zip_file.name)

        except Exception as exc:
            result.errors.append(f"Fehler bei ZIP {zip_file.name}: {exc}")
            logger.error("epo_zip_fehler", zip_datei=zip_file.name, error=str(exc))

    # --- Phase 2: Einzelne XML-Dateien (Rueckwaertskompatibilitaet) ---
    for xml_file in xml_files:
        # Inkrementeller Import: bereits importierte Dateien ueberspringen
        if await _is_already_imported(pool, "epo", xml_file.name):
            logger.info(
                "ueberspringe_bereits_importierte_datei",
                datei=xml_file.name,
                quelle="epo",
            )
            result.files_processed += 1
            continue

        xml_start_time = time.monotonic()
        xml_count_before = total_imported + total_skipped

        try:
            for patent in _iterparse_xml_stream(str(xml_file), xml_file.name):
                batch.append(patent)
                if len(batch) >= batch_size:
                    await _flush_batch()

            # Restlichen Batch fuer diese XML flushen
            if batch:
                await _flush_batch()

            result.files_processed += 1
            xml_record_count = (total_imported + total_skipped) - xml_count_before
            xml_duration = round(time.monotonic() - xml_start_time, 2)

            # Import in cross_schema.import_log protokollieren
            await _log_import(
                pool, "epo", xml_file.name, xml_record_count, xml_duration,
            )

        except Exception as exc:
            result.errors.append(f"Fehler bei {xml_file.name}: {exc}")

    result.records_imported = total_imported
    result.records_skipped = total_skipped
    result.duration_seconds = round(time.monotonic() - start_time, 2)

    logger.info(
        "epo_import_abgeschlossen",
        dateien_verarbeitet=result.files_processed,
        datensaetze_importiert=result.records_imported,
        datensaetze_uebersprungen=result.records_skipped,
        dauer_sekunden=result.duration_seconds,
    )

    return result
