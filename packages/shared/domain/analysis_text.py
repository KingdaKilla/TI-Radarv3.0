"""Reine Funktionen fuer deterministische Analyse-Textgenerierung (UC1-UC8).

Alle Funktionen sind zustandslos und ohne I/O — testbar und auditierbar.
Template-basierte deutsche Texte, kein LLM erforderlich.
"""

from __future__ import annotations

from shared.domain.models import (
    CompetitivePanel,
    CpcFlowPanel,
    FundingPanel,
    GeographicPanel,
    LandscapePanel,
    MaturityPanel,
    ResearchImpactPanel,
    TechClusterPanel,
    TemporalPanel,
)

# ---------------------------------------------------------------------------
# Hilfsfunktionen (Formatierung)
# ---------------------------------------------------------------------------


def _fmt_int(value: int) -> str:
    """Integer mit deutschem Tausender-Punkt (1.234)."""
    return f"{value:,}".replace(",", ".")


def _fmt_pct(value: float, decimals: int = 1) -> str:
    """Prozent mit Komma (67,3%)."""
    return f"{value:.{decimals}f}".replace(".", ",") + "%"


def _fmt_eur(value: float) -> str:
    """Euro-Formatierung (1,2 Mrd. EUR / 345,6 Mio. EUR)."""
    if value >= 1e9:
        num = f"{value / 1e9:.1f}".replace(".", ",")
        return f"{num} Mrd. EUR"
    if value >= 1e6:
        num = f"{value / 1e6:.1f}".replace(".", ",")
        return f"{num} Mio. EUR"
    if value >= 1e3:
        num = f"{value / 1e3:.0f}"
        return f"{num} Tsd. EUR"
    return f"{value:.0f} EUR"


def _trend_word(cagr_value: float) -> str:
    """CAGR als qualitative Bewertung."""
    if cagr_value > 15:
        return "sehr starkes Wachstum"
    if cagr_value > 5:
        return "solides Wachstum"
    if cagr_value > 0:
        return "leichtes Wachstum"
    if cagr_value > -5:
        return "Stagnation"
    return "einen Rueckgang"


def _hhi_interpretation(hhi: float) -> str:
    """Qualitative Einordnung des HHI-Index (DOJ/FTC-Schwellenwerte)."""
    if hhi < 1500:
        return "nicht konzentriert"
    if hhi < 2500:
        return "moderat konzentriert"
    return "hoch konzentriert"


# ---------------------------------------------------------------------------
# UC1: Technology Landscape
# ---------------------------------------------------------------------------


def generate_landscape_text(panel: LandscapePanel) -> str:
    """Analysetext fuer UC1 — Technologie-Landschaft."""
    total = panel.total_patents + panel.total_projects + panel.total_publications
    if total == 0:
        return ""

    parts: list[str] = []

    # Gesamtaktivitaeten + Aufschluesselung
    parts.append(
        f"Die Landschaftsanalyse identifiziert insgesamt {_fmt_int(total)} "
        f"technologische Aktivitaeten, aufgeteilt in {_fmt_int(panel.total_patents)} Patente, "
        f"{_fmt_int(panel.total_projects)} EU-Forschungsprojekte und "
        f"{_fmt_int(panel.total_publications)} akademische Publikationen."
    )

    # Dominante Quelle + Interpretation
    source_map = {
        "Patente": panel.total_patents,
        "Projekte": panel.total_projects,
        "Publikationen": panel.total_publications,
    }
    dominant_source = max(source_map, key=lambda k: source_map[k])
    dominant_share = source_map[dominant_source] / total * 100 if total > 0 else 0
    if dominant_share > 60:
        parts.append(
            f"Mit {_fmt_pct(dominant_share)} dominieren {dominant_source} das Aktivitaetsprofil "
            f"deutlich, was auf eine stark {_source_orientation(dominant_source)} "
            f"Technologielandschaft hindeutet."
        )
    else:
        parts.append(
            f"{dominant_source} bilden mit {_fmt_pct(dominant_share)} die groesste Einzelquelle. "
            f"Die relativ ausgeglichene Verteilung deutet auf ein Technologiefeld hin, das "
            f"sowohl in der industriellen Anwendung als auch in der Forschung aktiv ist."
        )

    # Verhaeltnis Patent/Projekt
    if panel.total_patents > 0 and panel.total_projects > 0:
        ratio = panel.total_patents / panel.total_projects
        if ratio > 5:
            parts.append(
                f"Das Patent-zu-Projekt-Verhaeltnis von {ratio:.1f}:1 signalisiert, dass "
                f"die Technologie bereits stark kommerzialisiert ist und die industrielle "
                f"Schutzrechtsstrategie die oeffentliche Forschungsfoerderung ueberwiegt."
            )
        elif ratio > 2:
            parts.append(
                f"Mit einem Patent-zu-Projekt-Verhaeltnis von {ratio:.1f}:1 zeigt sich eine "
                f"gesunde Balance zwischen industrieller Patentierung und oeffentlich "
                f"gefoerderten Forschungsaktivitaeten."
            )
        elif ratio < 0.5:
            parts.append(
                f"Das niedrige Patent-zu-Projekt-Verhaeltnis von {ratio:.1f}:1 deutet darauf hin, "
                f"dass die Technologie sich noch in einem fruehen, forschungsgetriebenen "
                f"Stadium befindet (Watts & Porter 1997)."
            )

    # Top-Land
    if panel.top_countries:
        top = panel.top_countries[0]
        country_name = str(top.get("country", ""))
        country_total = int(top.get("total", 0))
        if country_name and total > 0:
            country_share = country_total / total * 100
            parts.append(
                f"Das fuehrende Land ist {country_name} mit {_fmt_int(country_total)} "
                f"Aktivitaeten ({_fmt_pct(country_share)} Anteil)."
            )
            # Zweites Land
            if len(panel.top_countries) > 1:
                second = panel.top_countries[1]
                second_name = str(second.get("country", ""))
                second_total = int(second.get("total", 0))
                if second_name:
                    gap = country_total - second_total
                    parts.append(
                        f"Auf Platz zwei folgt {second_name} mit {_fmt_int(second_total)} "
                        f"Aktivitaeten — ein Abstand von {_fmt_int(gap)} zum Spitzenreiter."
                    )

    # Patent-Wachstumsrate
    if panel.time_series:
        last_entry = panel.time_series[-1]
        patents_growth = last_entry.get("patents_growth")
        if patents_growth is not None and patents_growth != 0:
            direction = "positiv" if float(patents_growth) > 0 else "negativ"
            parts.append(
                f"Die Patentwachstumsrate im letzten erfassten Jahr betraegt "
                f"{_fmt_pct(float(patents_growth))} und entwickelt sich damit {direction} "
                f"(Year-over-Year-Methode nach Watts & Porter 1997)."
            )

    # Projekt-Wachstumsrate
    if panel.time_series:
        last_entry = panel.time_series[-1]
        projects_growth = last_entry.get("projects_growth")
        if projects_growth is not None and projects_growth != 0:
            parts.append(
                f"Die Projektwachstumsrate im letzten Jahr liegt bei "
                f"{_fmt_pct(float(projects_growth))}."
            )

    # Zeitreihen-Trend (mehrere Jahre)
    if len(panel.time_series) >= 3:
        years = [int(ts.get("year", 0)) for ts in panel.time_series if ts.get("year")]
        if years:
            parts.append(
                f"Die Zeitreihe umfasst {len(years)} Jahre "
                f"({min(years)}\u2013{max(years)}), was eine belastbare "
                f"Trendanalyse ermoeglicht."
            )

    # Aktive Laender
    if panel.top_countries:
        n_countries = len(panel.top_countries)
        parts.append(
            f"Insgesamt sind {_fmt_int(n_countries)} Laender im Technologiefeld aktiv, "
            f"was auf eine breite internationale Forschungsbasis schliessen laesst."
        )

    return " ".join(parts)


def _source_orientation(source: str) -> str:
    """Qualitative Einordnung der dominanten Quelle."""
    if source == "Patente":
        return "industriell und anwendungsorientierte"
    if source == "Projekte":
        return "durch oeffentliche Forschungsfoerderung getriebene"
    return "akademisch und publikationsgetriebene"


# ---------------------------------------------------------------------------
# UC2: Technology Maturity Assessment
# ---------------------------------------------------------------------------


def generate_maturity_text(panel: MaturityPanel) -> str:
    """Analysetext fuer UC2 — Reifegrad-Analyse (Gao et al. 2013)."""
    if not panel.phase:
        return ""

    parts: list[str] = []

    # Phase + Reifegrad-Prozent + Kontext
    phase_label = panel.phase_de if panel.phase_de else panel.phase
    parts.append(
        f"Die Technologie befindet sich in der Phase \"{phase_label}\" "
        f"mit einem Reifegrad von {_fmt_pct(panel.maturity_percent)} "
        f"(Schwellenwerte nach Gao et al. 2013: <10% Aufkommend, "
        f"10\u201350% Wachsend, 50\u201390% Ausgereift, \u226590% Saettigung)."
    )

    # Phasen-Interpretation
    if panel.maturity_percent < 10:
        parts.append(
            "In dieser fruehen Entstehungsphase ist die Technologie noch durch "
            "explorative Forschung und wenige Patentanmeldungen gekennzeichnet. "
            "Das Innovationspotenzial ist hoch, jedoch besteht erhebliche Unsicherheit "
            "bezueglich der technologischen Tragfaehigkeit."
        )
    elif panel.maturity_percent < 50:
        parts.append(
            "Die Wachstumsphase ist typischerweise durch einen starken Anstieg der "
            "Patentaktivitaet und zunehmendes kommerzielles Interesse gekennzeichnet. "
            "Unternehmen bauen in dieser Phase gezielt Patentportfolios auf, "
            "um Marktpositionen zu sichern."
        )
    elif panel.maturity_percent < 90:
        parts.append(
            "In der Reifephase verlangsamt sich die Innovationsgeschwindigkeit. "
            "Neue Patente betreffen haeufig inkrementelle Verbesserungen statt "
            "grundlegender Durchbrueche. Der Markt konsolidiert sich zunehmend."
        )
    else:
        parts.append(
            "Die Saettigungsphase ist erreicht — das Wachstumspotenzial "
            "ist weitgehend ausgeschoepft. Neue Patente konzentrieren sich "
            "auf Nischenanwendungen oder Kombinationstechnologien."
        )

    # R²-Qualitaet + Modell
    if panel.r_squared > 0:
        if panel.r_squared >= 0.9:
            quality = "exzellente"
            quality_note = (
                "Die Daten folgen dem theoretischen S-Kurven-Verlauf nahezu perfekt."
            )
        elif panel.r_squared >= 0.7:
            quality = "gute"
            quality_note = (
                "Die Daten stimmen weitgehend mit dem theoretischen Modell ueberein."
            )
        elif panel.r_squared >= 0.5:
            quality = "akzeptable"
            quality_note = (
                "Das Modell erklaert die Daten nur teilweise — die Ergebnisse "
                "sollten mit Vorsicht interpretiert werden."
            )
        else:
            quality = "schwache"
            quality_note = (
                "Das Modell passt nur schlecht zu den Daten. Die Phasenklassifikation "
                "ist daher mit hoher Unsicherheit behaftet."
            )
        model_info = f" ({panel.fit_model})" if panel.fit_model else ""
        parts.append(
            f"Der S-Curve-Fit{model_info} zeigt eine {quality} "
            f"Anpassungsguete (R\u00b2 = {panel.r_squared:.3f}). {quality_note}"
        )

    # CAGR + Trend
    if panel.cagr != 0:
        parts.append(
            f"Die jaehrliche Wachstumsrate (CAGR) der Patentanmeldungen betraegt "
            f"{_fmt_pct(panel.cagr)} und zeigt damit {_trend_word(panel.cagr)}."
        )

    # Wendepunkt
    if panel.inflection_year > 0:
        parts.append(
            f"Der Wendepunkt der S-Kurve liegt bei {panel.inflection_year:.0f} — "
            f"ab diesem Zeitpunkt verlangsamt sich die Wachstumsdynamik. "
            f"Der Wendepunkt markiert den Uebergang von beschleunigtem zu "
            f"verlangsamtem Wachstum im logistischen Modell."
        )

    # Konfidenz + Datenbasis
    if panel.confidence > 0:
        n_years = len(panel.time_series)
        total_patents = sum(
            int(ts.get("patents", 0)) for ts in panel.time_series
        )
        conf_pct = panel.confidence * 100
        if conf_pct >= 80:
            conf_note = "Die Analyse ist belastbar."
        elif conf_pct >= 50:
            conf_note = "Die Analyse hat eine mittlere Aussagekraft."
        else:
            conf_note = "Die eingeschraenkte Datenbasis limitiert die Aussagekraft."
        parts.append(
            f"Die Konfidenz der Analyse betraegt {_fmt_pct(conf_pct, 0)}, "
            f"basierend auf {n_years} Jahren Patentdaten mit insgesamt "
            f"{_fmt_int(total_patents)} Patentfamilien. {conf_note}"
        )

    # Verbleibendes Potenzial
    if 0 < panel.maturity_percent < 90:
        remaining = 90.0 - panel.maturity_percent
        parts.append(
            f"Bis zur Saettigungsgrenze (90%) verbleiben noch "
            f"{_fmt_pct(remaining)} Wachstumspotenzial — "
            f"die Technologie hat damit noch signifikanten Raum fuer "
            f"weitere Patentaktivitaeten und Marktdurchdringung."
        )

    # Methodischer Hinweis
    parts.append(
        "Die Analyse basiert ausschliesslich auf Patentdaten (OECD 2009) und "
        "verwendet ein logistisches S-Curve-Modell (Franses 1994). "
        "Patentfamilien werden dedupliziert, um Mehrfachzaehlungen zu vermeiden."
    )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# UC3: Competitive Intelligence
# ---------------------------------------------------------------------------


def generate_competitive_text(panel: CompetitivePanel) -> str:
    """Analysetext fuer UC3 — Wettbewerbs-Analyse (Garcia-Vega 2006)."""
    if not panel.top_actors:
        return ""

    parts: list[str] = []

    # HHI + Konzentration + Einordnung
    if panel.hhi_index > 0:
        level_map = {"Low": "gering", "Moderate": "moderat", "High": "hoch"}
        level_map.get(panel.concentration_level, panel.concentration_level)
        interpretation = _hhi_interpretation(panel.hhi_index)
        parts.append(
            f"Der Herfindahl-Hirschman-Index (HHI) betraegt {_fmt_int(int(panel.hhi_index))} — "
            f"der Markt ist damit {interpretation} "
            f"(DOJ/FTC-Schwellenwerte: <1.500 gering, 1.500\u20132.500 moderat, >2.500 hoch; "
            f"Garcia-Vega 2006 validiert die Anwendung auf Patentdaten)."
        )

    # Top-Akteur mit Detail
    top = panel.top_actors[0]
    top_name = str(top.get("name", ""))
    top_share = float(top.get("share", 0)) * 100
    top_count = int(top.get("count", 0))
    if top_name:
        parts.append(
            f"Der fuehrende Akteur ist {top_name} mit {_fmt_int(top_count)} Aktivitaeten "
            f"und einem Marktanteil von {_fmt_pct(top_share)}."
        )
        # Zweiter Akteur + Abstand
        if len(panel.top_actors) > 1:
            second = panel.top_actors[1]
            second_name = str(second.get("name", ""))
            second_share = float(second.get("share", 0)) * 100
            if second_name:
                gap = top_share - second_share
                parts.append(
                    f"Auf Platz zwei folgt {second_name} mit {_fmt_pct(second_share)} "
                    f"— ein Abstand von {_fmt_pct(gap, 1)} Prozentpunkten zum Marktfuehrer."
                )

    # Top-3-Anteil + Interpretation
    if panel.top_3_share > 0:
        top3_pct = panel.top_3_share * 100
        if top3_pct > 70:
            interpretation = (
                "Das Technologiefeld wird von wenigen grossen Akteuren dominiert. "
                "Fuer neue Marktteilnehmer bestehen hohe Eintrittsbarrieren."
            )
        elif top3_pct > 50:
            interpretation = (
                "Es besteht eine deutliche Dominanz der drei groessten Akteure, "
                "jedoch mit verbleibendem Raum fuer spezialisierte Nischenanbieter."
            )
        elif top3_pct > 30:
            interpretation = (
                "Die moderate Konzentration signalisiert einen wettbewerbsintensiven Markt "
                "mit Chancen fuer mittlere Akteure."
            )
        else:
            interpretation = (
                "Der Markt ist stark fragmentiert — kein einzelner Akteur dominiert, "
                "was auf einen dynamischen und offenen Wettbewerb hindeutet."
            )
        parts.append(
            f"Die Top-3-Akteure halten zusammen {_fmt_pct(top3_pct)} "
            f"des Gesamtmarktes. {interpretation}"
        )

    # Gesamtanzahl Akteure + Einordnung
    total_actors = len(panel.full_actors) if panel.full_actors else len(panel.top_actors)
    if total_actors > 100:
        actor_note = (
            "Diese hohe Anzahl deutet auf ein breit aufgestelltes Technologiefeld "
            "mit vielen beteiligten Organisationen hin."
        )
    elif total_actors > 20:
        actor_note = (
            "Das Akteursfeld ist mittelgross und umfasst sowohl etablierte "
            "Unternehmen als auch spezialisierte Forschungseinrichtungen."
        )
    else:
        actor_note = (
            "Die geringe Akteursanzahl deutet auf ein Nischenfeld oder eine "
            "fruehe Marktphase hin."
        )
    parts.append(
        f"Insgesamt wurden {_fmt_int(total_actors)} Akteure identifiziert. {actor_note}"
    )

    # Netzwerk-Stats + Interpretation
    if panel.network_nodes and panel.network_edges:
        n_nodes = len(panel.network_nodes)
        n_edges = len(panel.network_edges)
        density = (2 * n_edges) / (n_nodes * (n_nodes - 1)) if n_nodes > 1 else 0
        parts.append(
            f"Das Kooperationsnetzwerk umfasst {_fmt_int(n_nodes)} Knoten "
            f"und {_fmt_int(n_edges)} Kanten "
            f"(Netzwerkdichte: {density:.3f})."
        )
        if density > 0.3:
            parts.append(
                "Die hohe Netzwerkdichte zeigt intensive Kooperationsbeziehungen "
                "zwischen den Akteuren."
            )
        elif density > 0.1:
            parts.append(
                "Die moderate Netzwerkdichte deutet auf selektive, "
                "aber relevante Kooperationsstrukturen hin."
            )
        else:
            parts.append(
                "Die niedrige Netzwerkdichte signalisiert, dass die meisten Akteure "
                "eher unabhaengig agieren als in Kooperationsverbunden."
            )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# UC4: Funding Radar
# ---------------------------------------------------------------------------


def generate_funding_text(panel: FundingPanel) -> str:
    """Analysetext fuer UC4 — EU-Foerderungs-Analyse."""
    if panel.total_funding_eur <= 0:
        return ""

    parts: list[str] = []

    # Gesamtfoerderung
    parts.append(
        f"Die EU-Gesamtfoerderung fuer dieses Technologiefeld belaeuft sich auf "
        f"{_fmt_eur(panel.total_funding_eur)}."
    )

    # Projekte + Durchschnitt + Einordnung
    if panel.time_series:
        total_projects = sum(int(ts.get("projects", 0)) for ts in panel.time_series)
        if total_projects > 0:
            parts.append(
                f"Verteilt auf {_fmt_int(total_projects)} Projekte ergibt sich "
                f"eine durchschnittliche Projektgroesse von "
                f"{_fmt_eur(panel.avg_project_size)}."
            )
            if panel.avg_project_size > 5_000_000:
                parts.append(
                    "Die ueberdurchschnittlich hohe Projektgroesse deutet auf "
                    "Grossprojekte hin, die typischerweise als Research & Innovation "
                    "Actions (RIA) oder integrierte Verbundprojekte ausgeschrieben werden."
                )
            elif panel.avg_project_size > 1_000_000:
                parts.append(
                    "Die Projektgroesse liegt im mittleren Bereich fuer "
                    "EU-Rahmenprogramm-Projekte."
                )
            elif panel.avg_project_size > 0:
                parts.append(
                    "Die vergleichsweise kleineren Projekte deuten auf "
                    "Coordination & Support Actions (CSA) oder "
                    "fruehe Machbarkeitsstudien hin."
                )

    # CAGR + Trend + Zeitraum
    if panel.funding_cagr != 0:
        period_info = f" ({panel.funding_cagr_period})" if panel.funding_cagr_period else ""
        abs_cagr = abs(panel.funding_cagr)
        parts.append(
            f"Die jaehrliche Wachstumsrate (CAGR) der Foerderung betraegt "
            f"{_fmt_pct(panel.funding_cagr)}{period_info} "
            f"und zeigt damit {_trend_word(panel.funding_cagr)}."
        )
        if abs_cagr > 20:
            parts.append(
                "Diese aussergewoehnlich hohe Wachstumsrate deutet auf ein "
                "Technologiefeld hin, das zunehmend strategische Prioritaet "
                "in der EU-Forschungspolitik geniesst."
            )

    # Dominantes Programm + Kontext
    if panel.by_programme:
        top_prog = panel.by_programme[0]
        prog_name = str(top_prog.get("programme", ""))
        prog_funding = float(top_prog.get("funding", 0))
        prog_projects = int(top_prog.get("projects", 0))
        if prog_name and panel.total_funding_eur > 0:
            prog_share = prog_funding / panel.total_funding_eur * 100
            parts.append(
                f"Das dominierende Foerderprogramm ist {prog_name} "
                f"mit {_fmt_eur(prog_funding)} ({_fmt_pct(prog_share)} "
                f"der Gesamtfoerderung, {_fmt_int(prog_projects)} Projekte)."
            )
            if len(panel.by_programme) > 1:
                second_prog = panel.by_programme[1]
                second_name = str(second_prog.get("programme", ""))
                if second_name:
                    parts.append(
                        f"An zweiter Stelle steht {second_name}."
                    )

    # Instrument-Breakdown (Top 3)
    if panel.instrument_breakdown:
        instr_totals: dict[str, int] = {}
        for entry in panel.instrument_breakdown:
            instr = str(entry.get("instrument", ""))
            count = int(entry.get("count", 0))
            if instr:
                instr_totals[instr] = instr_totals.get(instr, 0) + count
        top_instruments = sorted(instr_totals.items(), key=lambda x: x[1], reverse=True)[:3]
        if top_instruments:
            instr_strs = [f"{name} ({_fmt_int(cnt)} Projekte)" for name, cnt in top_instruments]
            parts.append(
                f"Die haeufigsten Foerderinstrumente sind: {', '.join(instr_strs)}."
            )

    # Zeitreihen-Trend
    if len(panel.time_series) >= 3:
        first_funding = float(panel.time_series[0].get("funding", 0))
        last_funding = float(panel.time_series[-1].get("funding", 0))
        if first_funding > 0 and last_funding > 0:
            if last_funding > first_funding * 2:
                parts.append(
                    "Ueber den Betrachtungszeitraum hat sich die jaehrliche "
                    "Foerderung mehr als verdoppelt — ein starkes Signal fuer "
                    "wachsendes politisches Interesse an dieser Technologie."
                )
            elif last_funding < first_funding * 0.5:
                parts.append(
                    "Die jaehrliche Foerderung hat sich im Betrachtungszeitraum "
                    "deutlich reduziert, was auf eine Verschiebung der "
                    "Forschungsprioritaeten hindeuten koennte."
                )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# UC5: CPC Flow
# ---------------------------------------------------------------------------


def generate_cpc_flow_text(panel: CpcFlowPanel) -> str:
    """Analysetext fuer UC5 — CPC-Technologiefluss (Jaccard-Index)."""
    if not panel.matrix or not panel.labels:
        return ""

    parts: list[str] = []

    # Patente + Verbindungen
    parts.append(
        f"Die Technologiefluss-Analyse untersucht die Co-Klassifikation von "
        f"{_fmt_int(panel.total_patents_analyzed)} Patenten und identifiziert "
        f"{_fmt_int(panel.total_connections)} Verbindungen zwischen "
        f"CPC-Technologieklassen."
    )

    # CPC-Codes + Level
    parts.append(
        f"Auf CPC-Level {panel.cpc_level} wurden {_fmt_int(len(panel.labels))} "
        f"unterschiedliche Klassen identifiziert."
    )

    # Staerkste Verbindung
    n = len(panel.matrix)
    max_val = 0.0
    max_i = 0
    max_j = 1
    for i in range(n):
        for j in range(i + 1, n):
            if panel.matrix[i][j] > max_val:
                max_val = panel.matrix[i][j]
                max_i = i
                max_j = j
    if max_val > 0 and max_i < len(panel.labels) and max_j < len(panel.labels):
        label_a = panel.labels[max_i]
        label_b = panel.labels[max_j]
        desc_a = panel.cpc_descriptions.get(label_a, "")
        desc_b = panel.cpc_descriptions.get(label_b, "")
        name_a = f"{label_a} ({desc_a})" if desc_a else label_a
        name_b = f"{label_b} ({desc_b})" if desc_b else label_b
        parts.append(
            f"Die staerkste Verflechtung besteht zwischen {name_a} und {name_b} "
            f"mit einem Jaccard-Index von {max_val:.3f}."
        )
        if max_val > 0.5:
            parts.append(
                "Dieser hohe Jaccard-Wert zeigt, dass beide Klassen "
                "haeufig gemeinsam in Patenten auftreten und eng verwandte "
                "Technologiefelder repraesentieren."
            )
        elif max_val > 0.2:
            parts.append(
                "Dieser moderate Jaccard-Wert signalisiert eine erkennbare, "
                "aber nicht dominante technologische Verwandtschaft."
            )

    # Schwaechste Verbindung (>0)
    min_val = 1.0
    for i in range(n):
        for j in range(i + 1, n):
            if 0 < panel.matrix[i][j] < min_val:
                min_val = panel.matrix[i][j]
    if 0 < min_val < max_val:
        parts.append(
            f"Die schwaechste nicht-triviale Verbindung hat einen Jaccard-Index "
            f"von {min_val:.3f} — die Spanne der Verflechtung ist damit "
            f"{'breit' if (max_val - min_val) > 0.2 else 'eng'}."
        )

    # Durchschnittlicher Jaccard + Interpretation
    off_diag_values: list[float] = []
    for i in range(n):
        for j in range(i + 1, n):
            if panel.matrix[i][j] > 0:
                off_diag_values.append(panel.matrix[i][j])
    if off_diag_values:
        avg_jaccard = sum(off_diag_values) / len(off_diag_values)
        total_pairs = n * (n - 1) // 2
        active_pairs = len(off_diag_values)
        sparsity = (total_pairs - active_pairs) / total_pairs * 100 if total_pairs > 0 else 0
        parts.append(
            f"Der durchschnittliche Jaccard-Index (nicht-null) betraegt {avg_jaccard:.3f} "
            f"bei {active_pairs} von {total_pairs} moeglichen Paaren "
            f"({_fmt_pct(sparsity)} der Matrix sind null)."
        )

        if avg_jaccard > 0.3:
            parts.append(
                "Die hohe durchschnittliche Verflechtung deutet auf ein "
                "breites, interdisziplinaeres Technologiefeld hin, in dem "
                "Innovationen haeufig Technologiegrenzen ueberschreiten."
            )
        elif avg_jaccard > 0.1:
            parts.append(
                "Die moderate Verflechtung zeigt ein Technologiefeld "
                "mit erkennbaren Querbezuegen, das jedoch auch klar "
                "abgegrenzte Teilbereiche aufweist."
            )
        else:
            parts.append(
                "Die geringe Verflechtung deutet auf ein spezialisiertes "
                "Technologiefeld hin, dessen Teilbereiche weitgehend "
                "unabhaengig voneinander agieren."
            )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# UC6: Geographic Intelligence
# ---------------------------------------------------------------------------


_EU_COUNTRIES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "EL", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT",
    "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
    # EEA
    "IS", "LI", "NO",
}


def generate_geographic_text(panel: GeographicPanel) -> str:
    """Analysetext fuer UC6 — Geografische Analyse."""
    if panel.total_countries == 0:
        return ""

    parts: list[str] = []

    # Laender + Staedte + Kontext
    parts.append(
        f"Die geografische Analyse zeigt eine Praesenz der Technologie in "
        f"{_fmt_int(panel.total_countries)} Laendern und "
        f"{_fmt_int(panel.total_cities)} Staedten."
    )

    if panel.total_countries > 30:
        parts.append(
            "Die breite internationale Verteilung signalisiert ein global "
            "relevantes Technologiefeld mit weitverzweigter Forschungsbasis."
        )
    elif panel.total_countries > 10:
        parts.append(
            "Die Technologie ist in einer substanziellen Anzahl von Laendern "
            "vertreten, was auf internationales Interesse und Relevanz hindeutet."
        )
    else:
        parts.append(
            "Die Aktivitaet konzentriert sich auf wenige Laender, was auf ein "
            "spezialisiertes Nischenfeld oder regionale Schwerpunkte hindeutet."
        )

    # Cross-Border-Anteil
    if panel.cross_border_share > 0:
        cb_pct = panel.cross_border_share * 100
        parts.append(
            f"Der Anteil grenzueberschreitender Projekte betraegt "
            f"{_fmt_pct(cb_pct)}."
        )
        if cb_pct > 80:
            parts.append(
                "Der sehr hohe Cross-Border-Anteil unterstreicht die stark "
                "internationale Ausrichtung der Forschungskooperationen "
                "in diesem Technologiefeld."
            )
        elif cb_pct > 50:
            parts.append(
                "Der ueberwiegende Anteil grenzueberschreitender Projekte "
                "zeigt, dass internationale Zusammenarbeit in diesem Feld "
                "die Norm ist."
            )

    # Top-Land + Anteil
    if panel.country_distribution:
        top = panel.country_distribution[0]
        country_name = str(top.get("country", ""))
        country_total = int(top.get("total", 0))
        all_total = sum(int(c.get("total", 0)) for c in panel.country_distribution)
        if country_name and all_total > 0:
            top_share = country_total / all_total * 100
            parts.append(
                f"Das fuehrende Land ist {country_name} mit {_fmt_int(country_total)} "
                f"Aktivitaeten ({_fmt_pct(top_share)} Anteil)."
            )
            # Zweites + drittes Land
            if len(panel.country_distribution) > 2:
                second = str(panel.country_distribution[1].get("country", ""))
                third = str(panel.country_distribution[2].get("country", ""))
                if second and third:
                    parts.append(
                        f"Es folgen {second} und {third} auf den Plaetzen zwei und drei."
                    )

    # Top-Kooperationspaar
    if panel.collaboration_pairs:
        top_pair = panel.collaboration_pairs[0]
        pair_a = str(top_pair.get("country_a", ""))
        pair_b = str(top_pair.get("country_b", ""))
        pair_count = int(top_pair.get("count", 0))
        if pair_a and pair_b:
            parts.append(
                f"Die staerkste Kooperationsachse verlaeuft zwischen "
                f"{pair_a} und {pair_b} mit {_fmt_int(pair_count)} gemeinsamen Projekten."
            )
            # Zweites Kooperationspaar
            if len(panel.collaboration_pairs) > 1:
                second_pair = panel.collaboration_pairs[1]
                sp_a = str(second_pair.get("country_a", ""))
                sp_b = str(second_pair.get("country_b", ""))
                sp_count = int(second_pair.get("count", 0))
                if sp_a and sp_b:
                    parts.append(
                        f"An zweiter Stelle steht die Achse {sp_a}\u2013{sp_b} "
                        f"mit {_fmt_int(sp_count)} Projekten."
                    )

    # Europa-Fokus (EU vs. non-EU in Top 10)
    if panel.country_distribution:
        top_10 = panel.country_distribution[:10]
        eu_count = sum(
            1 for c in top_10
            if str(c.get("country", "")).upper() in _EU_COUNTRIES
        )
        non_eu = len(top_10) - eu_count
        if eu_count > non_eu:
            parts.append(
                f"In den Top-10 dominieren EU-/EWR-Staaten "
                f"({eu_count} von {len(top_10)}). "
                f"Dies spiegelt den europaeischen Fokus der Datenquellen "
                f"(EPO, CORDIS) wider und ist kein Indikator fuer eine rein "
                f"europaeische Technologieentwicklung."
            )
        elif eu_count > 0:
            parts.append(
                f"In den Top-10 befinden sich {eu_count} EU-/EWR-Staaten "
                f"und {non_eu} Drittstaaten — ein Hinweis auf ein "
                f"international diversifiziertes Technologiefeld."
            )

    # Top-Staedte
    if panel.city_distribution and len(panel.city_distribution) >= 2:
        top_city = str(panel.city_distribution[0].get("city", ""))
        top_city_count = int(panel.city_distribution[0].get("count", 0))
        if top_city:
            parts.append(
                f"Auf Stadtebene fuehrt {top_city} mit "
                f"{_fmt_int(top_city_count)} Aktivitaeten."
            )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# UC7: Research Impact
# ---------------------------------------------------------------------------


def generate_research_impact_text(panel: ResearchImpactPanel) -> str:
    """Analysetext fuer UC7 — Forschungsimpact (Banks 2006, Valenzuela et al. 2015)."""
    if panel.total_papers == 0:
        return ""

    parts: list[str] = []

    # h-Index + Einordnung
    parts.append(
        f"Der h-Index des Technologiefeldes betraegt {panel.h_index} "
        f"(Topic-Level-Adaption nach Banks 2006)."
    )
    if panel.h_index >= 50:
        parts.append(
            "Dieser sehr hohe h-Index signalisiert ein etabliertes Forschungsgebiet "
            "mit grosser akademischer Wirkung und zahlreichen hochzitierten Arbeiten."
        )
    elif panel.h_index >= 20:
        parts.append(
            "Dieser solide h-Index deutet auf ein aktives Forschungsgebiet "
            "mit einer relevanten Zitationsbasis hin."
        )
    elif panel.h_index >= 5:
        parts.append(
            "Der moderate h-Index weist auf ein aufkommendes oder nischenspezifisches "
            "Forschungsgebiet mit begrenzter, aber wachsender akademischer Resonanz hin."
        )
    else:
        parts.append(
            "Der niedrige h-Index signalisiert ein junges oder stark spezialisiertes "
            "Forschungsfeld mit bisher geringer Zitationswirkung."
        )

    # Papers + Durchschnittszitationen
    avg_fmt = f"{panel.avg_citations:.1f}".replace(".", ",")
    parts.append(
        f"Basierend auf {_fmt_int(panel.total_papers)} analysierten Papers "
        f"ergibt sich ein Durchschnitt von {avg_fmt} Zitationen pro Paper."
    )

    # Zitationsverteilung-Skewness (aus Top-Paper vs. Durchschnitt)
    if panel.top_papers and panel.avg_citations > 0:
        top_citations = int(panel.top_papers[0].get("citations", 0))
        if top_citations > panel.avg_citations * 10:
            parts.append(
                "Die Zitationsverteilung ist stark rechtsschief — wenige "
                "hochzitierte Arbeiten ueberragen den Durchschnitt deutlich. "
                "Dies ist typisch fuer wissenschaftliche Felder (Lotka-Verteilung)."
            )

    # Influential Ratio
    if panel.influential_ratio > 0:
        infl_pct = panel.influential_ratio * 100
        parts.append(
            f"Der Anteil einflussreicher Zitationen betraegt "
            f"{_fmt_pct(infl_pct)} "
            f"(Valenzuela et al. 2015 — experimentelle Metrik)."
        )
        if infl_pct > 10:
            parts.append(
                "Der ueberdurchschnittlich hohe Anteil einflussreicher Zitationen "
                "deutet darauf hin, dass Arbeiten in diesem Feld haeufig als "
                "methodische oder konzeptionelle Grundlage weiterverwendet werden."
            )

    # Top-Paper
    if panel.top_papers:
        top = panel.top_papers[0]
        title = str(top.get("title", ""))
        citations = int(top.get("citations", 0))
        year = top.get("year")
        if title:
            short_title = title[:80] + "..." if len(title) > 80 else title
            year_info = f" ({year})" if year else ""
            parts.append(
                f"Das meistzitierte Paper ist \"{short_title}\"{year_info} "
                f"mit {_fmt_int(citations)} Zitationen."
            )

    # Top-Venue
    if panel.top_venues:
        top_venue = panel.top_venues[0]
        venue_name = str(top_venue.get("venue", ""))
        venue_count = int(top_venue.get("count", 0))
        if venue_name:
            parts.append(
                f"Die fuehrende Publikationsquelle ist \"{venue_name}\" "
                f"mit {_fmt_int(venue_count)} Papers."
            )
            if len(panel.top_venues) > 1:
                second_venue = str(panel.top_venues[1].get("venue", ""))
                if second_venue:
                    parts.append(
                        f"Es folgt \"{second_venue}\" an zweiter Stelle."
                    )

    # Publikationstypen
    if panel.publication_types:
        type_strs = []
        for pt in panel.publication_types[:3]:
            pt_name = str(pt.get("type", ""))
            pt_count = int(pt.get("count", 0))
            if pt_name and pt_count > 0:
                type_strs.append(f"{pt_name} ({_fmt_int(pt_count)})")
        if type_strs:
            parts.append(
                f"Die Publikationstypen verteilen sich wie folgt: {', '.join(type_strs)}."
            )

    # Citation Trend
    if len(panel.citation_trend) >= 3:
        first_year_cit = int(panel.citation_trend[0].get("total_citations", 0))
        last_year_cit = int(panel.citation_trend[-1].get("total_citations", 0))
        if first_year_cit > 0 and last_year_cit > first_year_cit * 2:
            parts.append(
                "Der Zitationstrend zeigt eine deutlich steigende Tendenz — "
                "das akademische Interesse an dieser Technologie waechst "
                "ueber den Betrachtungszeitraum signifikant."
            )
        elif first_year_cit > 0 and last_year_cit < first_year_cit * 0.5:
            parts.append(
                "Der Zitationstrend ist ruecklaeufig, was auf abnehmendes "
                "akademisches Interesse hindeuten koennte."
            )

    # Sampling-Hinweis
    if panel.total_papers >= 200:
        parts.append(
            "Methodischer Hinweis: Die Analyse basiert auf den Top-200 "
            "relevantesten Papers der Semantic Scholar Academic Graph API. "
            "Der h-Index ist daher eine Approximation und kein vollstaendiger "
            "Korpus-h-Index (Banks 2006)."
        )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# UC8: Temporal Dynamics
# ---------------------------------------------------------------------------


def generate_temporal_text(panel: TemporalPanel) -> str:
    """Analysetext fuer UC8 — Temporale Dynamik (Malerba & Orsenigo 1999)."""
    if not panel.entrant_persistence_trend:
        return ""

    parts: list[str] = []

    # New Entrant Rate + Einordnung
    ner_pct = panel.new_entrant_rate * 100
    parts.append(
        f"Die aktuelle Neueintrittrate betraegt {_fmt_pct(ner_pct)} "
        f"(Malerba & Orsenigo 1999)."
    )
    if ner_pct > 50:
        parts.append(
            "Mehr als die Haelfte der Akteure im letzten Jahr sind Neulinge — "
            "das Technologiefeld ist hoch dynamisch mit starker Fluktuation "
            "und niedrigen Eintrittsbarrieren."
        )
    elif ner_pct > 30:
        parts.append(
            "Die hohe Neueintrittrate signalisiert ein wachsendes Feld, "
            "in dem regelmaessig neue Akteure hinzukommen."
        )
    elif ner_pct > 10:
        parts.append(
            "Die moderate Neueintrittrate deutet auf ein reifendes Feld hin, "
            "in dem der Zugang fuer neue Akteure zwar moeglich, aber "
            "zunehmend anspruchsvoll ist."
        )
    elif ner_pct > 0:
        parts.append(
            "Die niedrige Neueintrittrate signalisiert ein konsolidiertes Feld "
            "mit hohen Eintrittsbarrieren und dominierenden Bestandsakteuren."
        )

    # Persistence Rate + Einordnung
    pr_pct = panel.persistence_rate * 100
    parts.append(
        f"Die Verbleibrate liegt bei {_fmt_pct(pr_pct)}."
    )
    if pr_pct > 70:
        parts.append(
            "Die hohe Verbleibrate zeigt, dass Akteure langfristig im Feld "
            "aktiv bleiben — ein Zeichen fuer nachhaltiges Engagement "
            "und stabile Marktpositionen."
        )
    elif pr_pct > 40:
        parts.append(
            "Die moderate Verbleibrate deutet auf eine Mischung aus "
            "langfristigen Akteuren und opportunistischen Teilnehmern hin."
        )
    elif pr_pct > 0:
        parts.append(
            "Die geringe Verbleibrate signalisiert starke Fluktuation — "
            "viele Akteure verlassen das Feld nach kurzer Zeit wieder."
        )

    # Kombination: Schumpeterian Regime
    if ner_pct > 30 and pr_pct < 50:
        parts.append(
            "Die Kombination aus hoher Neueintrittrate und niedriger Verbleibrate "
            "entspricht dem \"Schumpeter Mark I\"-Muster (creative destruction), "
            "typisch fuer innovative, aber instabile Technologiefelder."
        )
    elif ner_pct < 20 and pr_pct > 60:
        parts.append(
            "Die Kombination aus niedriger Neueintrittrate und hoher Verbleibrate "
            "entspricht dem \"Schumpeter Mark II\"-Muster (creative accumulation), "
            "typisch fuer oligopolistische, technologisch reife Maerkte."
        )

    # Dominantes Programm
    if panel.dominant_programme:
        parts.append(
            f"Das dominierende Foerderinstrument ist {panel.dominant_programme}."
        )

    # Top-Akteur + Detail
    if panel.actor_timeline:
        top = panel.actor_timeline[0]
        name = str(top.get("name", ""))
        total_count = int(top.get("total_count", 0))
        years_active = int(top.get("years_active", 0))
        if name:
            parts.append(
                f"Der aktivste Akteur ist {name} mit {_fmt_int(total_count)} "
                f"Aktivitaeten ueber {years_active} aktive Jahre."
            )
            if len(panel.actor_timeline) > 1:
                second = panel.actor_timeline[1]
                second_name = str(second.get("name", ""))
                if second_name:
                    parts.append(
                        f"An zweiter Stelle steht {second_name}."
                    )

    # Technologie-Breite Trend
    if len(panel.technology_breadth) >= 2:
        first = panel.technology_breadth[0]
        last = panel.technology_breadth[-1]
        first_sub = int(first.get("unique_cpc_subclasses", 0))
        last_sub = int(last.get("unique_cpc_subclasses", 0))
        first_sec = int(first.get("unique_cpc_sections", 0))
        last_sec = int(last.get("unique_cpc_sections", 0))
        if first_sub > 0 and last_sub > 0:
            if last_sub > first_sub:
                change_pct = (last_sub - first_sub) / first_sub * 100
                parts.append(
                    f"Die Technologie-Breite hat sich von {first_sub} auf "
                    f"{last_sub} CPC-Subklassen ausgeweitet (+{_fmt_pct(change_pct, 0)}). "
                    f"Das Feld wird technologisch diverser und erschliesst "
                    f"zunehmend angrenzende Technologiebereiche "
                    f"(Leydesdorff et al. 2015)."
                )
            elif last_sub < first_sub:
                change_pct = (first_sub - last_sub) / first_sub * 100
                parts.append(
                    f"Die Technologie-Breite hat sich von {first_sub} auf "
                    f"{last_sub} CPC-Subklassen verringert (-{_fmt_pct(change_pct, 0)}). "
                    f"Das Feld konvergiert technologisch und konzentriert sich "
                    f"auf Kernbereiche (Leydesdorff et al. 2015)."
                )
            else:
                parts.append(
                    f"Die Technologie-Breite bleibt stabil bei "
                    f"{last_sub} CPC-Subklassen (Level 4)."
                )

        # Sektionen-Breite (Level 1: A-H)
        if first_sec > 0 and last_sec > 0 and last_sec != first_sec:
            parts.append(
                f"Auf CPC-Sektionsebene (A\u2013H) hat sich die Breite "
                f"von {first_sec} auf {last_sec} Sektionen veraendert."
            )

    # Entrant/Persistence Trend ueber Zeit
    if len(panel.entrant_persistence_trend) >= 3:
        first_ner = float(panel.entrant_persistence_trend[0].get("new_entrant_rate", 0)) * 100
        last_ner = float(panel.entrant_persistence_trend[-1].get("new_entrant_rate", 0)) * 100
        if first_ner > 0 and last_ner > 0:
            if last_ner < first_ner * 0.5:
                parts.append(
                    "Die Neueintrittrate ist ueber den Betrachtungszeitraum deutlich "
                    "gesunken, was auf eine zunehmende Markkonsolidierung hindeutet."
                )
            elif last_ner > first_ner * 1.5:
                parts.append(
                    "Die Neueintrittrate ist ueber den Betrachtungszeitraum deutlich "
                    "gestiegen — ein Zeichen fuer wachsendes Interesse neuer Akteure."
                )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# UC9: Multi-Dimensionale Technologie-Cluster-Analyse
# ---------------------------------------------------------------------------


def generate_tech_cluster_text(panel: TechClusterPanel) -> str:
    """Analysetext fuer UC9 — Internationaler Vergleich (EU vs. Global).

    Referenzen: Porter & Cunningham (2005) Tech Mining,
    Frietsch & Schmoch (2010) Transnational patent activity.
    """
    if panel.global_patents == 0 and panel.global_actors == 0:
        return ""

    parts: list[str] = []

    # EU-Anteil Patente
    eu_pat_pct = panel.eu_patent_share * 100
    parts.append(
        f"Im internationalen Vergleich stammen {_fmt_pct(eu_pat_pct)} der "
        f"identifizierten Patente ({_fmt_int(panel.eu_patents)} von "
        f"{_fmt_int(panel.global_patents)}) aus dem EU/EEA-Raum."
    )

    # EU-Anteil Akteure
    eu_act_pct = panel.eu_actor_share * 100
    parts.append(
        f"Bei den Akteuren entfallen {_fmt_pct(eu_act_pct)} auf europaeische "
        f"Einrichtungen ({_fmt_int(panel.eu_actors)} von "
        f"{_fmt_int(panel.global_actors)} Akteuren)."
    )

    # Interpretations-Schwellen
    if eu_pat_pct >= 40:
        parts.append(
            "Europa nimmt eine starke Position in diesem Technologiefeld ein."
        )
    elif eu_pat_pct >= 20:
        parts.append(
            "Europa ist ein relevanter, aber nicht dominierender Akteur "
            "in diesem Technologiefeld."
        )
    else:
        parts.append(
            "Das Technologiefeld wird ueberwiegend von aussereuropaeischen "
            "Akteuren gepraegt."
        )

    # Top-EU-Akteur
    if panel.eu_top_actors:
        top = panel.eu_top_actors[0]
        parts.append(
            f"Der fuehrende europaeische Akteur ist {top.get('name', '')} "
            f"mit {_fmt_int(int(top.get('count', 0)))} Aktivitaeten."
        )

    # Top-Globaler-Akteur
    if panel.global_top_actors:
        top_g = panel.global_top_actors[0]
        parts.append(
            f"Global fuehrt {top_g.get('name', '')} "
            f"mit {_fmt_int(int(top_g.get('count', 0)))} Aktivitaeten "
            f"(Frietsch & Schmoch 2010)."
        )

    return " ".join(parts)
