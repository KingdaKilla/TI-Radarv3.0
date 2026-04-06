"""PDF-Exporter fuer TI-Radar Analyseergebnisse.

Erzeugt professionelle Patent Landscape Reports im PDF-Format
gemaess WIPO Guidelines for Preparing Patent Landscape Reports (Pub. 946).

Report-Struktur (18 Sektionen):
  1.  Titelseite (Technologie, Zeitraum, Datum, Datenquellen)
  2.  Inhaltsverzeichnis (automatisch generiert)
  3.  Executive Summary (Zusammenfassung der Kernerkenntnisse)
  4.  Methodik (Suchstrategie, Datenbanken, Zeitraum, Metriken)
  5.  Technologie-Uebersicht (UC1: Landschaft — Zeitreihe, CAGR)
  6.  Reifegrad-Analyse (UC2: S-Kurve, Phase, R², AICc)
  7.  Wettbewerbsanalyse (UC3: Top-Akteure, HHI, CR4)
  8.  Foerderungsanalyse (UC4: Programme, Instrumente)
  9.  Technologiefluss (UC5: Jaccard-Heatmap, Top-CPC-Paare)
  10. Geographische Verteilung (UC6: Laender, EU-Anteil)
  11. Forschungsimpact (UC7: h-Index, Journals, Zitations-Trend)
  12. Zeitliche Dynamik (UC8: Akteur-Dynamik, Themen)
  13. Technologie-Cluster (UC9: Radar-Dimensionen, Cluster-Tabelle)
  14. Wissenschaftsdisziplinen (UC10: EuroSciVoc, Shannon-Index)
  15. Akteurs-Typverteilung (UC11: Donut, Typ-Erklaerungen)
  16. Erteilungsquoten (UC12: Anmeldungen/Erteilungen, Quote)
  17. Datenqualitaetshinweise (Truncation Bias, Abdeckung, Limitierungen)
  18. Anhang (Datenquellen-Details, Methodenbeschreibung)

Verwendet Jinja2-Templates mit eingebettetem CSS — gerendert via WeasyPrint.
Verwendet dieselben UC-Spaltendefinitionen wie CSV-/Excel-Exporter
fuer konsistente Datenstruktur ueber alle Export-Formate.
"""

from __future__ import annotations

import base64
import html
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend fuer Server
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import structlog
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from weasyprint import HTML

from src.exporters.csv_exporter import (
    EXTRA_UC_DEFS,
    UC_COLUMN_DEFS,
    _extract_rows,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Verzeichnisse fuer Templates
# ---------------------------------------------------------------------------

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
_BASE_HTML_PATH = _TEMPLATE_DIR / "report_base.html"
_STYLES_CSS_PATH = _TEMPLATE_DIR / "report_styles.css"


# ---------------------------------------------------------------------------
# UC-Metadaten: Anzeigename, Beschreibung (deutsch), WIPO-Sektionsnummer
# ---------------------------------------------------------------------------

# Reihenfolge und Sektionsnummern gemaess WIPO Pub. 946 Mapping
# Sektionen 1-2 = Executive Summary + Methodik (fest)
# Sektionen 3-14 = UC-Analysen (dynamisch)
# Sektion 15/16/17/18 = Datenqualitaet + Anhang (fest)

UC_DISPLAY_META: dict[str, tuple[str, str, int]] = {
    # Cluster 1: Technologie & Reife
    "landscape": (
        "Technologie-Übersicht",
        "Patent- und Projektaktivität im Zeitverlauf mit CAGR-Wachstumsrate",
        3,
    ),
    "maturity": (
        "Reifegrad-Analyse",
        "S-Kurve, Reifephase, Bestimmtheitsmaß R² und AICc",
        4,
    ),
    "cpc_flow": (
        "Technologiefluss",
        "Jaccard-Heatmap, Co-Occurrence und Top-CPC-Paare",
        5,
    ),
    # Cluster 2: Marktakteure
    "competitive": (
        "Wettbewerbsanalyse",
        "Top-Akteure, HHI-Konzentrationsindex und CR4",
        6,
    ),
    "temporal": (
        "Zeitliche Dynamik",
        "Akteur-Persistenz, Programm-Evolution und Themen im Zeitverlauf",
        7,
    ),
    "actor_type": (
        "Akteurs-Typverteilung",
        "Verteilung nach Organisationstyp (Hochschule, Industrie, KMU, Forschung)",
        8,
    ),
    # Cluster 3: Forschung & Förderung
    "funding": (
        "Förderungsanalyse",
        "EU-Förderprogramme, Instrumente und Fördervolumen",
        9,
    ),
    "research_impact": (
        "Forschungsimpact",
        "h-Index, Top-Journals, Zitations-Trend",
        10,
    ),
    # Cluster 4: Geographische Perspektive
    "geographic": (
        "Geographische Verteilung",
        "Länderverteilung, EU-Anteil und Kooperationspaare",
        11,
    ),
    "tech_cluster": (
        "Technologie-Cluster",
        "Radar-Dimensionen, Cluster-Analyse und verwandte Technologiefelder",
        12,
    ),
    "euroscivoc": (
        "Wissenschaftsdisziplinen",
        "EuroSciVoc-Taxonomie und Shannon-Diversitätsindex",
        13,
    ),
    "patent_grant": (
        "Erteilungsquoten",
        "Patentanmeldungen vs. Erteilungen und Erteilungsquote im Zeitverlauf",
        14,
    ),
}

# Deutsche Spalten-Labels fuer die Tabellen-Header
COLUMN_LABELS_DE: dict[str, str] = {
    "year": "Jahr",
    "patent_count": "Patente",
    "project_count": "Projekte",
    "publication_count": "Publikationen",
    "funding_eur": "Förderung (€)",
    "cagr": "CAGR (%)",
    "cumulative": "Kumuliert",
    "fitted": "S-Kurve (Fit)",
    "annual_count": "Jährlich",
    "cumulative_patents": "Kumulierte Patente",
    "maturity_phase": "Reifephase",
    "s_curve_r2": "S-Kurve R²",
    "actor_name": "Akteur",
    "name": "Name",
    "country": "Land",
    "country_code": "Ländercode",
    "country_name": "Land",
    "hhi_share": "HHI-Anteil",
    "share": "Anteil",
    "framework": "Rahmenprogramm",
    "ec_funding": "EC-Förderung (€)",
    "funding_scheme": "Förderinstrument",
    "avg_project_size": "Ø Projektgröße (€)",
    "participant_count": "Teilnehmer",
    "code_a": "CPC-Code A",
    "code_b": "CPC-Code B",
    "description_a": "Beschreibung A",
    "description_b": "Beschreibung B",
    "similarity": "Ähnlichkeit",
    "jaccard_index": "Jaccard-Index",
    "co_occurrence_count": "Co-Occurrence",
    "collaboration_pairs": "Kooperationspaare",
    "title": "Titel",
    "paper_title": "Publikationstitel",
    "citation_count": "Zitationen",
    "citations": "Zitationen",
    "venue": "Zeitschrift/Konferenz",
    "doi": "DOI",
    "h_index_contribution": "h-Index Beitrag",
    "persistence_type": "Persistenz-Typ",
    "first_year": "Erstes Jahr",
    "last_year": "Letztes Jahr",
    "first_active_year": "Erstes aktives Jahr",
    "last_active_year": "Letztes aktives Jahr",
    "active_years_count": "Aktive Jahre",
    "persistence_years": "Persistenz (Jahre)",
    "label": "Bezeichnung",
    "actor_count": "Akteure",
    "density": "Dichte",
    "coherence": "Kohärenz",
    "total_projects": "Projekte gesamt",
    "type": "Typ",
    "actor_share": "Akteursanteil",
    "application_count": "Anmeldungen",
    "grant_count": "Erteilungen",
    "grant_rate": "Erteilungsquote",
    "pending_count": "Ausstehend",
}


# ---------------------------------------------------------------------------
# Jinja2 Environment
# ---------------------------------------------------------------------------


def _create_jinja_env() -> Environment:
    """Erstellt die Jinja2-Umgebung mit Custom-Filtern."""
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Custom-Filter registrieren
    env.filters["format_kpi"] = _format_kpi_value
    env.filters["format_currency"] = _format_currency_value

    return env


# ---------------------------------------------------------------------------
# Hauptfunktion
# ---------------------------------------------------------------------------


async def generate_pdf(
    technology: str,
    analysis_data: dict[str, Any],
    uc_keys: list[str],
) -> bytes:
    """Generiert einen PDF-Report gemaess WIPO Pub. 946 Struktur.

    Laedt das Jinja2-HTML-Template und CSS, baut den vollstaendigen
    Template-Kontext auf und rendert das finale Dokument via WeasyPrint.

    Args:
        technology: Name der analysierten Technologie.
        analysis_data: Vollstaendiges RadarResponse-JSON vom Orchestrator.
        uc_keys: Liste der zu exportierenden UC-Schluessel.

    Returns:
        PDF-Datei als Bytes.
    """
    logger.info("pdf_generierung_gestartet", technology=technology, uc_count=len(uc_keys))

    # Jinja2-Umgebung und Template laden
    jinja_env = _create_jinja_env()
    template = jinja_env.get_template("report_base.html")
    css_styles = _STYLES_CSS_PATH.read_text(encoding="utf-8")

    # Metadaten extrahieren
    analysis_period = analysis_data.get("analysis_period", "")
    export_date = datetime.now().strftime("%d.%m.%Y um %H:%M Uhr")
    data_sources = "EPO OPS, CORDIS, OpenAIRE, Semantic Scholar, GLEIF"

    # Inhaltsverzeichnis-Eintraege aufbauen
    toc_entries = _build_toc_entries(uc_keys)

    # Sektionsnummer fuer Datenqualitaet berechnen (nach letztem UC)
    toc_quality_number = _get_quality_section_number(uc_keys)

    # UC-Panel-Daten als dict bereitstellen (fuer direkten Zugriff im Template)
    panel_data = {uc_key: analysis_data.get(uc_key, {}) for uc_key in uc_keys}

    # Datentabellen fuer alle UCs vorrendern
    table_html_map = _build_all_tables(analysis_data, uc_keys)

    # Explainability-Sektion (falls im Response vorhanden)
    explainability_html = Markup(_build_explainability(analysis_data))

    # Executive Summary Text (falls vorhanden)
    executive_summary_text = analysis_data.get("executive_summary", "")

    # Template-Kontext zusammenstellen
    context: dict[str, Any] = {
        # Globale Metadaten
        "css_styles": css_styles,
        "technology": technology,
        "analysis_period": analysis_period,
        "export_date": export_date,
        "data_sources": data_sources,
        "uc_count": len(uc_keys),
        "uc_keys": uc_keys,
        # Inhaltsverzeichnis
        "toc_entries": toc_entries,
        "toc_quality_number": toc_quality_number,
        # Executive Summary
        "executive_summary_text": executive_summary_text,
        # UC-Panel-Daten (fuer KPI-Zugriff im Template)
        "landscape": panel_data.get("landscape", {}),
        "maturity": panel_data.get("maturity", {}),
        "competitive": panel_data.get("competitive", {}),
        "funding": panel_data.get("funding", {}),
        "cpc_flow": panel_data.get("cpc_flow", {}),
        "geographic": panel_data.get("geographic", {}),
        "research_impact": panel_data.get("research_impact", {}),
        "temporal": panel_data.get("temporal", {}),
        "tech_cluster": panel_data.get("tech_cluster", {}),
        "euroscivoc": panel_data.get("euroscivoc", {}),
        "actor_type": panel_data.get("actor_type", {}),
        "patent_grant": panel_data.get("patent_grant", {}),
        # SVG-Inline-Visualisierungen (Markup() verhindert Jinja2-Autoescape)
        "landscape_chart": Markup(_build_bar_chart_svg(
            panel_data.get("landscape", {}), "time_series", "year", "patent_count", "Patente pro Jahr"
        )),
        "funding_chart": Markup(_build_bar_chart_svg(
            panel_data.get("funding", {}), "time_series", "year", "funding_eur", "Förderung pro Jahr (EUR)", divisor=1_000_000, suffix="M"
        )),
        "competitive_chart": Markup(_build_horizontal_bar_svg(
            panel_data.get("competitive", {}), "top_actors", "name", "patent_count", "Top-Akteure nach Patenten", limit=8
        )),
        "geographic_chart": Markup(_build_horizontal_bar_svg(
            panel_data.get("geographic", {}), "country_distribution", "country_name", "patent_count", "Top-Länder nach Patenten", limit=10
        )),
        "maturity_chart": Markup(_build_bar_chart_svg(
            panel_data.get("maturity", {}), "s_curve_data", "year", "cumulative", "Kumulative Patente (S-Kurve)"
        )),
        "cpc_flow_chart": Markup(_build_horizontal_bar_svg(
            panel_data.get("cpc_flow", {}), "top_pairs", "code_a", "co_occurrence_count", "Top CPC-Code-Paare (Co-Occurrence)", limit=10
        )),
        "research_impact_chart": Markup(_build_bar_chart_svg(
            panel_data.get("research_impact", {}), "citation_trend", "year", "total_citations", "Zitationen pro Jahr"
        )),
        "temporal_chart": Markup(_build_bar_chart_svg(
            panel_data.get("temporal", {}), "entrant_persistence_trend", "year", "total_active", "Aktive Akteure pro Jahr"
        )),
        "tech_cluster_chart": Markup(_build_horizontal_bar_svg(
            panel_data.get("tech_cluster", {}), "clusters", "label", "patent_count", "Cluster nach Patentanzahl", limit=10
        )),
        "euroscivoc_chart": Markup(_build_horizontal_bar_svg(
            panel_data.get("euroscivoc", {}), "fields_of_science", "label", "total_projects", "Wissenschaftsfelder nach Projekten", limit=10
        )),
        "actor_type_chart": Markup(_build_horizontal_bar_svg(
            panel_data.get("actor_type", {}), "type_breakdown", "label", "actor_count", "Akteurs-Typen", limit=8
        )),
        "patent_grant_chart": Markup(_build_bar_chart_svg(
            panel_data.get("patent_grant", {}), "year_trend", "year", "grant_count", "Erteilte Patente pro Jahr"
        )),
        # Vorgerenderte Datentabellen (als HTML-Strings)
        "landscape_table": table_html_map.get("landscape", ""),
        "maturity_table": table_html_map.get("maturity", ""),
        "competitive_table": table_html_map.get("competitive", ""),
        "funding_table": table_html_map.get("funding", ""),
        "cpc_flow_table": table_html_map.get("cpc_flow", ""),
        "geographic_table": table_html_map.get("geographic", ""),
        "research_impact_table": table_html_map.get("research_impact", ""),
        "temporal_table": table_html_map.get("temporal", ""),
        "tech_cluster_table": table_html_map.get("tech_cluster", ""),
        "euroscivoc_table": table_html_map.get("euroscivoc", ""),
        "actor_type_table": table_html_map.get("actor_type", ""),
        "patent_grant_table": table_html_map.get("patent_grant", ""),
        # Explainability
        "explainability_html": explainability_html,
    }

    # Template rendern
    final_html = template.render(**context)

    # PDF rendern
    pdf_bytes = HTML(string=final_html).write_pdf()

    logger.info(
        "pdf_generierung_abgeschlossen",
        technology=technology,
        size_bytes=len(pdf_bytes),
        sections=len(uc_keys),
        wipo_struktur=True,
    )

    return pdf_bytes


# ---------------------------------------------------------------------------
# Inhaltsverzeichnis
# ---------------------------------------------------------------------------


def _build_toc_entries(uc_keys: list[str]) -> list[dict[str, Any]]:
    """Erzeugt strukturierte TOC-Eintraege fuer die UC-Sektionen."""
    entries: list[dict[str, Any]] = []

    for uc_key in uc_keys:
        display_name, description, section_num = UC_DISPLAY_META.get(
            uc_key, (uc_key.replace("_", " ").title(), "", 99)
        )
        entries.append({
            "number": section_num,
            "title": display_name,
            "description": description,
            "uc_key": uc_key,
        })

    return entries


def _get_quality_section_number(uc_keys: list[str]) -> int:
    """Berechnet die Sektionsnummer fuer 'Datenqualitaetshinweise'.

    Basiert auf der hoechsten UC-Sektionsnummer + 1.
    """
    max_section = 2  # Mindestens nach Methodik
    for uc_key in uc_keys:
        _, _, section_num = UC_DISPLAY_META.get(uc_key, ("", "", 0))
        if section_num > max_section:
            max_section = section_num
    return max_section + 1


# ---------------------------------------------------------------------------
# Datentabellen fuer alle UCs
# ---------------------------------------------------------------------------


def _build_all_tables(data: dict[str, Any], uc_keys: list[str]) -> dict[str, Markup]:
    """Baut HTML-Datentabellen fuer alle angeforderten Use-Cases.

    Returns:
        Dict mit UC-Key -> HTML-String der Datentabelle.
    """
    tables: dict[str, Markup] = {}

    for uc_key in uc_keys:
        panel_data = data.get(uc_key, {})
        if not panel_data:
            continue

        table_html = _build_data_table(uc_key, panel_data)
        if table_html:
            tables[uc_key] = Markup(table_html)

    return tables


def _build_data_table(uc_key: str, panel_data: dict[str, Any]) -> str:
    """Erzeugt eine HTML-Datentabelle fuer den jeweiligen Use-Case.

    Verwendet dieselben Spaltendefinitionen wie CSV-/Excel-Exporter.
    """
    if uc_key in UC_COLUMN_DEFS:
        _, columns, data_key = UC_COLUMN_DEFS[uc_key]
        rows = _extract_rows(panel_data, data_key, columns)
    elif uc_key in EXTRA_UC_DEFS:
        _, data_key = EXTRA_UC_DEFS[uc_key]
        columns, rows = _extract_generic_rows(panel_data, data_key)
    else:
        columns, rows = _extract_generic_rows(panel_data, "")
    if not rows:
        return ""

    # Tabelle aufbauen
    parts: list[str] = ['<table class="data-table">']

    # Header
    parts.append("  <thead><tr>")
    for col in columns:
        label = COLUMN_LABELS_DE.get(col, col.replace("_", " ").title())
        parts.append(f"    <th>{_esc(label)}</th>")
    parts.append("  </tr></thead>")

    # Body (maximal 50 Zeilen im PDF für Lesbarkeit)
    max_rows = 50
    parts.append("  <tbody>")
    for row in rows[:max_rows]:
        parts.append("    <tr>")
        for col_idx, val in enumerate(row):
            col_name = columns[col_idx] if col_idx < len(columns) else ""
            css_class = _cell_css_class(col_name, val)
            formatted = _format_cell_value(col_name, val)
            parts.append(f"      <td{css_class}>{_esc(formatted)}</td>")
        parts.append("    </tr>")
    parts.append("  </tbody>")

    parts.append("</table>")

    # Hinweis bei abgeschnittenen Daten
    if len(rows) > max_rows:
        parts.append(
            f'<p class="text-muted text-small">'
            f"Hinweis: {len(rows)} Zeilen gesamt — hier werden die ersten {max_rows} angezeigt. "
            f"Vollständige Daten im CSV- oder Excel-Export."
            f"</p>"
        )

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Explainability-Sektion
# ---------------------------------------------------------------------------


def _build_explainability(data: dict[str, Any]) -> str:
    """Erzeugt die Explainability-Sektion aus dem RadarResponse.

    Zeigt Auditierungsinformationen wie Verarbeitungszeit, Fehler
    und UC-Erfolgsquote an.
    """
    total_time = data.get("total_processing_time_ms")
    success_count = data.get("successful_uc_count")
    total_count = data.get("total_uc_count")
    uc_errors = data.get("uc_errors", [])
    explainability = data.get("explainability", {})

    if not total_time and not explainability:
        return ""

    parts: list[str] = ['<div class="summary-box mt-2">']
    parts.append("  <h4>Auditierungsinformationen</h4>")

    if total_time is not None:
        parts.append(f"  <p><strong>Verarbeitungszeit:</strong> {total_time} ms</p>")
    if success_count is not None and total_count is not None:
        parts.append(
            f"  <p><strong>Erfolgsquote:</strong> {success_count} von {total_count} Use-Cases erfolgreich</p>"
        )

    # Einzelne UC-Fehler auflisten
    if uc_errors:
        parts.append("  <p><strong>Fehlgeschlagene Use-Cases:</strong></p>")
        parts.append("  <ul>")
        for error in uc_errors:
            if isinstance(error, dict):
                uc = error.get("use_case", "unbekannt")
                msg = error.get("error_message", error.get("error_code", ""))
                parts.append(f"    <li>{_esc(uc)}: {_esc(str(msg))}</li>")
        parts.append("  </ul>")

    # Explainability-Details (z.B. Datenabdeckung, Konfidenz)
    if isinstance(explainability, dict):
        for key, value in explainability.items():
            parts.append(f"  <p><strong>{_esc(key.replace('_', ' ').title())}:</strong> {_esc(str(value))}</p>")

    parts.append("</div>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Hilfsfunktionen: Datenextraktion und Formatierung
# ---------------------------------------------------------------------------


def _extract_generic_rows(
    panel_data: dict[str, Any],
    data_key: str,
) -> tuple[list[str], list[list[Any]]]:
    """Extrahiert Spalten und Zeilen aus generischen Panel-Daten.

    Wird fuer UCs ohne spezifische Spaltendefinition verwendet.

    Returns:
        Tuple aus (Spaltenkoepfe, Zeilendaten).
    """
    items = panel_data.get(data_key, []) if data_key else []
    if not items and isinstance(panel_data.get("data"), dict):
        items = panel_data["data"].get(data_key, []) if data_key else []

    if isinstance(items, list) and items and isinstance(items[0], dict):
        columns = list(items[0].keys())
        rows: list[list[Any]] = []
        for item in items:
            row = [item.get(col, "") for col in columns]
            rows.append(row)
        return columns, rows

    # Fallback: Key-Value-Paare
    columns = ["Schlüssel", "Wert"]
    rows = []
    for key, value in panel_data.items():
        if key in ("metadata", "data", "result", "summary"):
            continue
        if isinstance(value, (dict, list)):
            rows.append([key, str(value)[:200]])
        elif value is not None:
            rows.append([key, str(value)])
    return columns, rows


def _format_kpi_value(value: Any) -> str:
    """Formatiert einen KPI-Wert fuer die Anzeige.

    Jinja2-Filter: {{ value | format_kpi }}
    """
    if isinstance(value, float):
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.1f} Mio."
        if abs(value) >= 1_000:
            return f"{value / 1_000:.1f} Tsd."
        return f"{value:.2f}"
    if isinstance(value, int):
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.1f} Mio."
        if abs(value) >= 1_000:
            return f"{value:,}".replace(",", ".")
        return str(value)
    return str(value)


def _format_currency_value(value: Any) -> str:
    """Formatiert einen Waehrungswert fuer die Anzeige.

    Jinja2-Filter: {{ value | format_currency }}
    """
    try:
        num = float(value)
        if num >= 1_000_000_000:
            return f"{num / 1_000_000_000:.2f} Mrd. \u20ac"
        if num >= 1_000_000:
            return f"{num / 1_000_000:.2f} Mio. \u20ac"
        if num >= 1_000:
            return f"{num:,.0f} \u20ac".replace(",", ".")
        return f"{num:.2f} \u20ac"
    except (ValueError, TypeError):
        return str(value)


def _format_cell_value(column: str, value: Any) -> str:
    """Formatiert einen Zellenwert basierend auf dem Spaltentyp."""
    if value is None or value == "":
        return "\u2014"  # Em-Dash fuer leere Werte

    if column in ("ec_funding", "total_funding", "funding_amount"):
        try:
            num = float(value)
            if num >= 1_000_000:
                return f"{num / 1_000_000:.2f} Mio. \u20ac"
            return f"{num:,.0f} \u20ac".replace(",", ".")
        except (ValueError, TypeError):
            return str(value)

    if column in ("cagr", "hhi_share", "jaccard_index", "s_curve_r2"):
        try:
            return f"{float(value):.4f}"
        except (ValueError, TypeError):
            return str(value)

    if column in ("patent_count", "project_count", "citations",
                   "co_occurrence_count", "persistence_years",
                   "cumulative_patents", "collaboration_pairs"):
        try:
            return f"{int(value):,}".replace(",", ".")
        except (ValueError, TypeError):
            return str(value)

    # Lange Texte kuerzen (z.B. paper_title)
    s = str(value)
    if len(s) > 80:
        return s[:77] + "..."
    return s


def _cell_css_class(column: str, value: Any) -> str:
    """Bestimmt die CSS-Klasse fuer eine Tabellenzelle."""
    numeric_columns = {
        "patent_count", "project_count", "citations", "year",
        "co_occurrence_count", "persistence_years", "cumulative_patents",
        "collaboration_pairs", "first_year", "last_year",
        "cagr", "hhi_share", "jaccard_index", "s_curve_r2",
        "ec_funding", "total_funding", "funding_amount",
        "h_index_contribution",
    }
    if column in numeric_columns:
        return ' class="num"'
    return ""


def _esc(text: str) -> str:
    """HTML-Escaping fuer sicheres Einbetten von Nutzerdaten."""
    return html.escape(str(text), quote=True)


# ---------------------------------------------------------------------------
# Matplotlib-basierte Chart-Generierung (PNG Base64 fuer WeasyPrint)
# ---------------------------------------------------------------------------

_CHART_COLOR = "#2a4365"
_CHART_COLOR_LIGHT = "#4a7ab5"
_CHART_COLORS = ["#2a4365", "#4a7ab5", "#6b9fd2", "#0072B2", "#009E73",
                 "#E69F00", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442"]

# Globale matplotlib-Konfiguration (einmalig)
plt.rcParams.update({
    "font.size": 8,
    "axes.titlesize": 10,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "figure.facecolor": "white",
    "axes.facecolor": "#fafbfc",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linewidth": 0.5,
})


def _safe_num(val: Any) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _fig_to_base64_img(fig: plt.Figure) -> str:
    """Konvertiert eine matplotlib-Figur in ein base64-kodiertes HTML <img>-Tag."""
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    buf.seek(0)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f'<img src="data:image/png;base64,{b64}" style="width:100%;max-width:700px;margin:8px 0">'


def _build_bar_chart_svg(
    panel: dict[str, Any],
    data_key: str,
    x_key: str,
    y_key: str,
    title: str,
    divisor: float = 1,
    suffix: str = "",
) -> str:
    """Erzeugt ein vertikales Balkendiagramm als matplotlib PNG."""
    items = panel.get(data_key, [])
    if not items or not isinstance(items, list):
        return ""

    x_vals = [str(e.get(x_key, "")) for e in items]
    y_vals = [_safe_num(e.get(y_key, 0)) / divisor for e in items]

    if not y_vals or max(y_vals) == 0:
        return ""

    fig, ax = plt.subplots(figsize=(9, 2.8))
    bars = ax.bar(range(len(x_vals)), y_vals, color=_CHART_COLOR, width=0.7, zorder=3)
    ax.set_title(title, fontweight="bold", pad=10)
    ax.set_xticks(range(len(x_vals)))
    ax.set_xticklabels([str(v)[-4:] for v in x_vals], rotation=45 if len(x_vals) > 8 else 0, ha="right" if len(x_vals) > 8 else "center")
    ax.set_ylabel(suffix if suffix else None)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}{suffix}"))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()

    return _fig_to_base64_img(fig)


def _build_horizontal_bar_svg(
    panel: dict[str, Any],
    data_key: str,
    label_key: str,
    value_key: str,
    title: str,
    limit: int = 10,
) -> str:
    """Erzeugt ein horizontales Balkendiagramm als matplotlib PNG."""
    items = panel.get(data_key, [])
    if not items or not isinstance(items, list):
        return ""

    entries = [(str(e.get(label_key, ""))[:30], _safe_num(e.get(value_key, 0))) for e in items[:limit]]
    entries = [(l, v) for l, v in entries if v > 0]
    if not entries:
        return ""

    labels, values = zip(*reversed(entries))  # reversed fuer top-to-bottom
    n = len(labels)
    fig_h = max(2.0, 0.35 * n + 0.8)

    fig, ax = plt.subplots(figsize=(9, fig_h))
    colors = [_CHART_COLORS[i % len(_CHART_COLORS)] for i in range(n)]
    bars = ax.barh(range(n), values, color=colors, height=0.65, zorder=3)
    ax.set_yticks(range(n))
    ax.set_yticklabels(labels)
    ax.set_title(title, fontweight="bold", pad=10)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Werte an Balken schreiben
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + max(values) * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{val:,.0f}", va="center", fontsize=6, color="#64748b")

    fig.tight_layout()
    return _fig_to_base64_img(fig)
