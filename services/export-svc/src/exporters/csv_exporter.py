"""CSV-Exporter fuer TI-Radar Analyseergebnisse.

Generiert CSV-Inhalte aus dem RadarResponse-JSON mit einer Sektion
pro Use-Case. Jeder UC hat spezifische Spaltenkoepfe, die den
jeweiligen Analyse-Dimensionen entsprechen.

UC-spezifische Spalten:
  UC1 (Landscape):       year, patent_count, project_count, cagr
  UC2 (Maturity):        year, cumulative_patents, maturity_phase, s_curve_r2
  UC3 (Competitive):     actor_name, country, patent_count, project_count, hhi_share
  UC4 (Funding):         year, framework, ec_funding, project_count, funding_scheme
  UC5 (CPC-Flow):        code_a, code_b, jaccard_index, co_occurrence_count
  UC6 (Geographic):      country, patent_count, project_count, collaboration_pairs
  UC7 (Research-Impact): paper_title, year, citations, venue, h_index_contribution
  UC8 (Temporal):        actor_name, first_year, last_year, persistence_years, patent_count
"""

from __future__ import annotations

import csv
import io
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# UC-spezifische Spaltendefinitionen
# ---------------------------------------------------------------------------

# Jeder Eintrag: (UC-Panel-Key, Anzeigename, Spaltenkoepfe, Pfad zu den Daten)
UC_COLUMN_DEFS: dict[str, tuple[str, list[str], str]] = {
    "landscape": (
        "UC1 Landscape",
        ["year", "patent_count", "project_count", "cagr"],
        "yearly_data",
    ),
    "maturity": (
        "UC2 Maturity",
        ["year", "cumulative_patents", "maturity_phase", "s_curve_r2"],
        "yearly_data",
    ),
    "competitive": (
        "UC3 Competitive",
        ["actor_name", "country", "patent_count", "project_count", "hhi_share"],
        "actors",
    ),
    "funding": (
        "UC4 Funding",
        ["year", "framework", "ec_funding", "project_count", "funding_scheme"],
        "funding_entries",
    ),
    "cpc_flow": (
        "UC5 CPC-Flow",
        ["code_a", "code_b", "jaccard_index", "co_occurrence_count"],
        "pairs",
    ),
    "geographic": (
        "UC6 Geographic",
        ["country", "patent_count", "project_count", "collaboration_pairs"],
        "countries",
    ),
    "research_impact": (
        "UC7 Research-Impact",
        ["paper_title", "year", "citations", "venue", "h_index_contribution"],
        "papers",
    ),
    "temporal": (
        "UC8 Temporal",
        ["actor_name", "first_year", "last_year", "persistence_years", "patent_count"],
        "actors",
    ),
}

# Zusaetzliche UCs (UC9, UC10, UC11, UC12) mit generischem Fallback
EXTRA_UC_DEFS: dict[str, tuple[str, str]] = {
    "tech_cluster": ("UC9 Tech-Cluster", "clusters"),
    "actor_type": ("UC11 Actor-Type", "actor_types"),
    "patent_grant": ("UC12 Patent-Grant", "grants"),
    "euroscivoc": ("UC10 EuroSciVoc", "categories"),
}


# ---------------------------------------------------------------------------
# Hauptfunktion
# ---------------------------------------------------------------------------


async def export_csv(data: dict[str, Any], use_cases: list[str]) -> bytes:
    """Generiert CSV-Inhalte aus RadarResponse-JSON.

    Erzeugt eine zusammenhaengende CSV-Datei mit einer klar abgegrenzten
    Sektion pro Use-Case. Sektionen werden durch Leerzeilen und einen
    Header-Kommentar getrennt.

    Args:
        data: RadarResponse als dict (von Orchestrator oder Cache).
        use_cases: Liste der zu exportierenden UC-Namen.

    Returns:
        UTF-8-kodierte CSV-Bytes mit BOM fuer Excel-Kompatibilitaet.
    """
    output = io.StringIO()
    writer = csv.writer(output, dialect="excel", lineterminator="\n")

    # Metadaten-Header
    technology = data.get("technology", "Unbekannt")
    period = data.get("analysis_period", "")
    writer.writerow(["# TI-Radar Export"])
    writer.writerow(["# Technologie", technology])
    writer.writerow(["# Analysezeitraum", period])
    writer.writerow([])  # Leerzeile

    sections_written = 0

    for uc_name in use_cases:
        panel_data = data.get(uc_name, {})
        if not panel_data:
            logger.debug("uc_panel_leer", uc=uc_name)
            continue

        if uc_name in UC_COLUMN_DEFS:
            display_name, columns, data_key = UC_COLUMN_DEFS[uc_name]
            rows = _extract_rows(panel_data, data_key, columns)
            _write_section(writer, display_name, columns, rows)
            sections_written += 1

        elif uc_name in EXTRA_UC_DEFS:
            display_name, data_key = EXTRA_UC_DEFS[uc_name]
            _write_generic_section(writer, display_name, panel_data, data_key)
            sections_written += 1

        else:
            # Unbekannter UC — generischer Export als Key-Value
            _write_generic_section(writer, uc_name, panel_data, "")
            sections_written += 1

    if sections_written == 0:
        writer.writerow(["# Keine Daten fuer die angeforderten Use-Cases vorhanden"])

    logger.info("csv_generiert", sections=sections_written, use_cases=use_cases)

    # UTF-8 BOM fuer Excel-Kompatibilitaet
    csv_content = output.getvalue()
    return b"\xef\xbb\xbf" + csv_content.encode("utf-8")


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _extract_rows(
    panel_data: dict[str, Any],
    data_key: str,
    columns: list[str],
) -> list[list[Any]]:
    """Extrahiert Zeilen aus Panel-Daten anhand des Daten-Schluessels.

    Durchsucht verschiedene moegliche Verschachtelungsebenen im
    Panel-JSON, da die Protobuf-zu-JSON-Konvertierung unterschiedliche
    Strukturen erzeugen kann.
    """
    # Direkt im Panel
    items = panel_data.get(data_key, [])

    # Verschachtelt unter "data" oder "result"
    if not items and isinstance(panel_data.get("data"), dict):
        items = panel_data["data"].get(data_key, [])
    if not items and isinstance(panel_data.get("result"), dict):
        items = panel_data["result"].get(data_key, [])

    # Fallback: Wenn items ein Dict ist (z.B. einzelnes Objekt)
    if isinstance(items, dict):
        items = [items]

    # Wenn items eine Liste von Dicts ist, Spalten extrahieren
    if isinstance(items, list):
        rows: list[list[Any]] = []
        for item in items:
            if isinstance(item, dict):
                row = [item.get(col, "") for col in columns]
                rows.append(row)
            elif isinstance(item, (list, tuple)):
                rows.append(list(item))
        return rows

    return []


def _write_section(
    writer: csv.writer,
    display_name: str,
    columns: list[str],
    rows: list[list[Any]],
) -> None:
    """Schreibt eine UC-Sektion in den CSV-Writer.

    Format:
      # UC-Name
      spalte1, spalte2, ...
      wert1, wert2, ...
      (Leerzeile)
    """
    writer.writerow([f"# {display_name}"])
    writer.writerow(columns)

    for row in rows:
        # Werte formatieren (None -> leer, Floats auf 6 Dezimalstellen)
        formatted = []
        for val in row:
            if val is None:
                formatted.append("")
            elif isinstance(val, float):
                formatted.append(f"{val:.6f}")
            else:
                formatted.append(str(val))
        writer.writerow(formatted)

    writer.writerow([])  # Trennzeile


def _write_generic_section(
    writer: csv.writer,
    display_name: str,
    panel_data: dict[str, Any],
    data_key: str,
) -> None:
    """Schreibt eine generische Sektion fuer UCs ohne spezifische Spaltendefinition.

    Versucht die Daten als Tabelle darzustellen, falls die Struktur
    eine Liste von Dicts enthaelt. Andernfalls werden Key-Value-Paare
    zeilenweise ausgegeben.
    """
    writer.writerow([f"# {display_name}"])

    # Daten unter dem angegebenen Schluessel suchen
    items = panel_data.get(data_key, []) if data_key else []
    if not items and isinstance(panel_data.get("data"), dict):
        items = panel_data["data"].get(data_key, []) if data_key else []

    if isinstance(items, list) and items and isinstance(items[0], dict):
        # Spaltenkoepfe aus dem ersten Eintrag ableiten
        columns = list(items[0].keys())
        writer.writerow(columns)
        for item in items:
            row = [item.get(col, "") for col in columns]
            writer.writerow([str(v) if v is not None else "" for v in row])
    else:
        # Flaches Key-Value-Format fuer Skalare und einfache Strukturen
        writer.writerow(["key", "value"])
        for key, value in panel_data.items():
            if key in ("metadata", "data", "result"):
                continue  # Metadaten ueberspringen
            if isinstance(value, (dict, list)):
                writer.writerow([key, str(value)[:500]])
            else:
                writer.writerow([key, str(value) if value is not None else ""])

    writer.writerow([])  # Trennzeile
