"""Prompt-Templates fuer die LLM-gesteuerte UC-Panel-Analyse.

Jeder UC hat ein eigenes deutsches Prompt-Template, das die Panel-Daten
als Kontext erhaelt und eine differenzierte Analyse in 2-3 Absaetzen anfordert.

Platzhalter:
  {technology} — Technologie-Suchbegriff
  {data}       — Serialisierte Panel-Daten (JSON)
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Deutsche Prompt-Templates fuer alle 12 Use Cases
# ---------------------------------------------------------------------------

UC_PROMPTS: dict[str, str] = {
    # UC1 — Technologie-Landschaft
    "landscape": """Analysiere die folgenden Technologie-Landschaftsdaten fuer "{technology}":
{data}

Erstelle eine differenzierte Analyse in 2-3 Absaetzen basierend auf den konkreten Datenpunkten:

**Aktivitaetsprofil:** Wie viele Patente und Projekte wurden gefunden? Wie verhaelt sich das Verhaeltnis Patent-zu-Projekt? Nenne die konkreten Zahlen und interpretiere, ob die Technologie eher patent- oder forschungsgetrieben ist.

**Wachstumsdynamik:** Interpretiere die CAGR-Werte fuer Patente und Projekte. Steigt die Aktivitaet, stagniert sie oder faellt sie? Nenne die CAGR-Prozentwerte und ordne sie ein (z.B. >10%: starkes Wachstum, <0%: ruecklaeufig).

**Technologische Schwerpunkte:** Welche CPC-Klassen dominieren und was bedeuten sie inhaltlich? Gibt es ueberraschende Verflechtungen oder Luecken?

Nenne durchgehend konkrete Zahlen und Werte aus den Daten. Antworte auf Deutsch.""",

    # UC2 — Reifegrad-Analyse (S-Kurve)
    "maturity": """Analysiere die S-Kurven-Reifegraddaten fuer "{technology}":
{data}

Erstelle eine differenzierte Analyse in 2-3 Absaetzen basierend auf den konkreten Datenpunkten:

**Aktuelle Reifephase:** In welcher Phase befindet sich die Technologie (Emerging, Growth, Mature, Declining)? Was bedeutet das fuer Investitions- und Adoptionsentscheidungen? Nenne den konkreten Phase-Wert.

**Modellguete:** Wie gut passt die S-Kurve (R²-Wert)? Ein R² > 0.85 deutet auf zuverlaessige Prognose hin, < 0.6 auf hohes Unsicherheitsniveau. Interpretiere den konkreten Wert und was er fuer die Aussagekraft bedeutet.

**Prognose und strategische Implikationen:** Basierend auf dem S-Kurven-Verlauf — wann koennte der Wendepunkt (Inflection Point) erreicht werden? Was empfiehlt sich fuer Akteure: fruehe Positionierung oder abwartende Beobachtung?

Nenne durchgehend konkrete Zahlen und Werte aus den Daten. Antworte auf Deutsch.""",

    # UC3 — Wettbewerbsanalyse
    "competitive": """Analysiere die Wettbewerbsdaten fuer "{technology}":
{data}

Erstelle eine differenzierte Analyse in 2-3 Absaetzen basierend auf den konkreten Datenpunkten:

**Marktstruktur:** Interpretiere den HHI-Wert — ist der Markt fragmentiert (<1000), moderat konzentriert (1000-2500) oder hochkonzentriert (>2500)? Nenne den konkreten HHI und erklaere die strategischen Implikationen.

**Akteurs-Landschaft:** Wer sind die Top-Akteure nach Patentanteilen? Wie gross ist der Abstand zwischen dem fuehrenden Akteur und den Verfolgern? Gibt es ueberraschende Akteure (z.B. Universitaeten unter Industrieunternehmen)?

**Wettbewerbsdynamik:** Zeigen die Daten Konsolidierung (steigende Konzentration) oder Fragmentierung (neue Akteure)? Welche Chancen oder Risiken ergeben sich fuer neue Marktteilnehmer?

Nenne durchgehend konkrete Zahlen, Prozentwerte und Akteursnamen aus den Daten. Antworte auf Deutsch.""",

    # UC4 — Foerderungsanalyse
    "funding": """Analysiere die Foerderungsdaten fuer "{technology}":
{data}

Erstelle eine differenzierte Analyse in 2-3 Absaetzen basierend auf den konkreten Datenpunkten:

**Foerdervolumen und Trend:** Wie hoch ist das gesamte EU-Foerdervolumen? Steigt oder sinkt die Foerderung ueber die Zeit? Nenne konkrete Betraege und Zeitraeume.

**Foerderinstrumente:** Wie verteilen sich RIA (Research & Innovation Actions), IA (Innovation Actions) und CSA (Coordination & Support Actions)? Was sagt die Verteilung ueber den Reifegrad der Technologie-Foerderung aus (RIA-dominiert = fruehe Phase, IA-dominiert = Marktnaehe)?

**Strategische Ausrichtung:** Welche Horizon-Programme foerdern die Technologie am staerksten? Welche thematischen Schwerpunkte zeichnen sich ab und was bedeutet das fuer die EU-Technologiepolitik?

Nenne durchgehend konkrete Zahlen und Programmnamen aus den Daten. Antworte auf Deutsch.""",

    # UC5 — CPC-Technologiefluss
    "cpc_flow": """Analysiere die CPC-Technologiefluss-Daten fuer "{technology}":
{data}

Erstelle eine differenzierte Analyse in 2-3 Absaetzen basierend auf den konkreten Datenpunkten:

**Staerkste Verflechtungen:** Welche CPC-Klassenpaare haben die hoechsten Jaccard-Koeffizienten? Nenne die konkreten Werte und erklaere, was die Ko-Klassifikation technologisch bedeutet (z.B. H04L+G06N = Telekommunikation trifft auf KI).

**Netzwerkstruktur:** Gibt es CPC-Klassen die als Hubs fungieren (viele Verbindungen) vs. isolierte Technologiefelder? Was bedeutet hohe Vernetzung fuer Technologietransfer-Potenzial?

**Konvergenztrends:** Deuten die Flussmuster auf Technologie-Konvergenz hin? Welche bisher getrennten Felder wachsen zusammen und was sind die Implikationen fuer interdisziplinaere Innovation?

Nenne durchgehend konkrete Jaccard-Werte und CPC-Klassen aus den Daten. Antworte auf Deutsch.""",

    # UC6 — Geographische Verteilung
    "geographic": """Analysiere die geographischen Verteilungsdaten fuer "{technology}":
{data}

Erstelle eine differenzierte Analyse in 2-3 Absaetzen basierend auf den konkreten Datenpunkten:

**Fuehrende Laender:** Welche Laender dominieren bei Patenten und welche bei Forschungsprojekten? Nenne die Top-3-5 mit konkreten Zahlen oder Anteilen. Gibt es Laender die in Forschung stark sind aber wenig patentieren (oder umgekehrt)?

**Konzentration vs. Diversitaet:** Wie konzentriert ist die globale Aktivitaet? Wird die Technologie von wenigen Laendern dominiert oder ist sie breit verteilt? Nenne konkrete Konzentrationskennzahlen.

**Kollaborationsmuster:** Welche Laenderpaare kollaborieren am intensivsten? Gibt es ueberraschende Kooperationsachsen (z.B. EU-Asien-Bruecken)? Was bedeutet die geographische Verteilung fuer die Wettbewerbsposition Europas?

Nenne durchgehend konkrete Laender, Zahlen und Prozentwerte aus den Daten. Antworte auf Deutsch.""",

    # UC7 — Forschungsimpact
    "research_impact": """Analysiere die Forschungsimpact-Daten fuer "{technology}":
{data}

Erstelle eine differenzierte Analyse in 2-3 Absaetzen basierend auf den konkreten Datenpunkten:

**Impact-Kennzahlen:** Wie hoch ist der h-Index fuer dieses Technologiefeld? Nenne den konkreten Wert und ordne ihn ein (Vergleich: h-Index >50 = etabliertes Grossfeld, <10 = Nischengebiet). Wie entwickeln sich die Zitationszahlen ueber die Zeit?

**Einflussreichste Forschung:** Welche Publikationen oder Autoren stechen durch besonders hohe Zitationszahlen hervor? Was sind deren thematische Schwerpunkte?

**Forschungstrend:** Steigt der Impact (mehr Zitationen, hoehere Qualitaet) oder laesst er nach? Was bedeutet das fuer die wissenschaftliche Reife des Feldes und die Verbindung zwischen Forschung und Anwendung?

Nenne durchgehend konkrete Zahlen, h-Index-Werte und Zitationszahlen aus den Daten. Antworte auf Deutsch.""",

    # UC8 — Zeitliche Entwicklung
    "temporal": """Analysiere die zeitlichen Entwicklungsdaten fuer "{technology}":
{data}

Erstelle eine differenzierte Analyse in 2-3 Absaetzen basierend auf den konkreten Datenpunkten:

**Akteursdynamik:** Wie hat sich die Anzahl aktiver Akteure ueber die Zeit veraendert? Gibt es Phasen starken Zuwachses oder Abgangs? Wie hoch ist die Persistenzrate (bleiben Akteure langfristig aktiv)?

**Programm-Evolution:** Wie haben sich die Foerderprogramme und -volumina ueber die Jahre entwickelt? Gab es Brueche oder Beschleunigungen durch bestimmte politische Initiativen?

**Technologiebreite:** Wird das Feld breiter (mehr CPC-Klassen, mehr Disziplinen) oder enger (Spezialisierung)? Was bedeutet der zeitliche Verlauf fuer die Zukunftsaussichten der Technologie?

Nenne durchgehend konkrete Jahreszahlen, Trends und Veraenderungsraten aus den Daten. Antworte auf Deutsch.""",

    # UC9 — Technologie-Cluster
    "tech_cluster": """Analysiere die Technologie-Cluster-Daten fuer "{technology}":
{data}

Erstelle eine differenzierte Analyse in 2-3 Absaetzen basierend auf den konkreten Datenpunkten:

**Cluster-Qualitaet:** Wie viele Cluster wurden identifiziert und wie gut ist die Trennung (Silhouette Score)? Nenne den konkreten Score und interpretiere ihn (>0.5 = gute Trennung, <0.25 = fragwuerdig). Was bedeutet das fuer die technologische Differenzierung?

**Cluster-Charakteristik:** Welche CPC-Klassen praegen die groessten Cluster? Handelt es sich um thematisch kohaerente Technologiegruppen oder um heterogene Mischungen?

**Innovationspotenzial:** Welche Cluster zeigen Wachstum (steigende Patentaktivitaet) und welche stagnieren? Gibt es kleine aber schnell wachsende Cluster die auf emerging sub-fields hindeuten?

Nenne durchgehend konkrete Cluster-IDs, Scores und CPC-Klassen aus den Daten. Antworte auf Deutsch.""",

    # UC10 — Wissenschaftsdisziplinen (EuroSciVoc)
    "euroscivoc": """Analysiere die EuroSciVoc-Wissenschaftsdisziplinen-Daten fuer "{technology}":
{data}

Erstelle eine differenzierte Analyse in 2-3 Absaetzen basierend auf den konkreten Datenpunkten:

**Disziplinaere Schwerpunkte:** Welche Wissenschaftsdisziplinen dominieren und mit welchem Anteil? Nenne die Top-5 mit konkreten Prozentwerten. Entspricht die Verteilung den Erwartungen oder gibt es Ueberraschungen?

**Interdisziplinaritaet:** Wie hoch ist der Shannon-Diversitaetsindex? Nenne den konkreten Wert und interpretiere ihn (hoch = stark interdisziplinaer, niedrig = disziplinaer fokussiert). Was bedeutet das fuer das Innovationspotenzial?

**Aufkommende Disziplinen:** Gibt es Disziplinen die erst kuerzlich an Bedeutung gewonnen haben? Welche Schnittstellen zwischen Disziplinen koennten besonders innovationstraechtig sein?

Nenne durchgehend konkrete Disziplin-Namen, Anteile und Index-Werte aus den Daten. Antworte auf Deutsch.""",

    # UC11 — Akteurs-Typverteilung
    "actor_type": """Analysiere die Akteurs-Typverteilungsdaten fuer "{technology}":
{data}

Erstelle eine differenzierte Analyse in 2-3 Absaetzen basierend auf den konkreten Datenpunkten:

**Akteursverteilung:** Wie verteilen sich HES (Hochschulen), PRC (Unternehmen), REC (Forschungseinrichtungen) und andere Akteurstypen? Nenne die konkreten Anteile. Welcher Typ dominiert und was sagt das ueber den Reifegrad der Technologie?

**Forschung vs. Anwendung:** Ueberwiegt Grundlagenforschung (hoher HES/REC-Anteil) oder industrielle Anwendung (hoher PRC-Anteil)? Wie ist das Verhaeltnis und was bedeutet es fuer den Technologietransfer?

**Strategische Implikationen:** Ist die Akteurslandschaft ausgewogen oder gibt es Schieflagen? Was empfiehlt sich fuer die Foerderpolitik — mehr Industriebeteiligung foerdern oder akademische Freiheit staerken?

Nenne durchgehend konkrete Akteurszahlen, Typen und Anteile aus den Daten. Antworte auf Deutsch.""",

    # UC12 — Erteilungsquoten (Patent Grant)
    "patent_grant": """Analysiere die Patent-Erteilungsdaten fuer "{technology}":
{data}

Erstelle eine differenzierte Analyse in 2-3 Absaetzen basierend auf den konkreten Datenpunkten:

**Erteilungsquote:** Wie hoch ist die Grant Rate und wie verhaelt sie sich zum typischen EPO-Durchschnitt (~50-60%)? Nenne den konkreten Prozentwert. Eine hohe Rate deutet auf etablierte Patentqualitaet hin, eine niedrige auf ein schwieriges IP-Umfeld.

**Zeitlicher Verlauf:** Wie entwickeln sich Anmeldungen und Erteilungen ueber die Jahre? Gibt es eine zunehmende oder abnehmende Luecke zwischen Anmeldungen und Grants? Nenne konkrete Jahreszahlen und Trends.

**Innovationsreife:** Was sagen die Erteilungsmuster ueber die technologische Reife aus? Eine stabile hohe Grant Rate bei steigenden Anmeldungen signalisiert ein gesundes Innovationsfeld. Welche Handlungsempfehlung ergibt sich?

Nenne durchgehend konkrete Quoten, Zahlen und Zeitraeume aus den Daten. Antworte auf Deutsch.""",
}

# ---------------------------------------------------------------------------
# System-Prompt fuer alle UC-Analysen
# ---------------------------------------------------------------------------

SYSTEM_PROMPT: str = """Du bist ein Experte fuer Technologie-Intelligence und analysierst \
strukturierte Daten aus Patent-, Foerderungs- und Publikationsdatenbanken. \
Deine Aufgabe ist es, die bereitgestellten Daten differenziert zu interpretieren \
und strategische Erkenntnisse abzuleiten.

Richtlinien:
- Antworte in 2-3 strukturierten Absaetzen mit konkreten Datenpunkten
- Nenne immer spezifische Zahlen, Prozentwerte und Kennzahlen aus den Daten
- Interpretiere die Werte: Was bedeuten sie im Kontext, was ist hoch/niedrig?
- Verwende Fachbegriffe und erklaere sie bei Bedarf
- Stuetze dich ausschliesslich auf die bereitgestellten Daten
- Leite strategische Implikationen und Handlungsempfehlungen ab
- Formatiere mit **Fettdruck** fuer Schluesselerkenntnisse"""


# ---------------------------------------------------------------------------
# RAG Context Prompt Template — fuer AnalyzePanelWithContext
# ---------------------------------------------------------------------------

RAG_CONTEXT_TEMPLATE = """
Relevante Dokumente aus der Wissensbasis:

{context_block}

---
Panel-Daten (aggregiert):
{panel_data}

Analysiere {use_case_key} fuer die Technologie "{technology}".
Beziehe die oben genannten Dokumente in deine Analyse ein und verweise auf konkrete Quellen.
"""

# ---------------------------------------------------------------------------
# Chat Prompt Templates — fuer interaktiven Chat mit RAG-Kontext
# ---------------------------------------------------------------------------

CHAT_SYSTEM_PROMPT = """Du bist ein Technologie-Experte fuer "{technology}" im TI-Radar System.
Du antwortest ausfuehrlich und faktenbasiert auf Basis der bereitgestellten Quellen und Analyse-Daten.

Richtlinien:
- Antworte in mehreren Absaetzen, nicht nur in einem Satz
- Erklaere Kennzahlen verstaendlich: Was bedeuten HHI, CAGR, R², Shannon-Index konkret?
- Nenne spezifische Zahlen und Werte aus den bereitgestellten Daten
- Ordne die Werte ein: Ist ein Wert hoch oder niedrig? Was bedeutet das?
- Leite strategische Schlussfolgerungen ab
- Zitiere Quellen mit [1], [2], etc. am Ende relevanter Aussagen
- Wenn du etwas nicht aus den Quellen oder Daten beantworten kannst, sage das ehrlich
- Verwende **Fettdruck** fuer Schluesselerkenntnisse

Antworte auf {language}."""

CHAT_USER_TEMPLATE = """
{panel_block}
Quellen:
{sources_block}

Frage: {user_message}
"""


def format_context_block(documents: list) -> str:  # type: ignore[type-arg]
    """Formatiert RetrievedDocuments als nummerierter Kontext-Block.

    Args:
        documents: Liste von RetrievedDocument-Objekten (Protobuf oder Mock).

    Returns:
        Nummerierter Text-Block mit Quelle, Titel und Snippet.
    """
    lines: list[str] = []
    for i, doc in enumerate(documents, 1):
        source_label = getattr(doc, "source", "unknown")
        title = getattr(doc, "title", "")
        snippet = getattr(doc, "text_snippet", "")
        lines.append(f"[{i}] ({source_label}) {title}: {snippet}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Panel-Kontext Formatierung — fuer analyseberuecksichtigenden Chat
# ---------------------------------------------------------------------------

_PANEL_LABELS: dict[str, str] = {
    "landscape": "Technologie-Landschaft (UC1)",
    "maturity": "Reifegrad / S-Kurve (UC2)",
    "competitive": "Wettbewerbsanalyse (UC3)",
    "funding": "Foerderungsanalyse (UC4)",
    "cpc_flow": "CPC-Technologiefluss (UC5)",
    "geographic": "Geographische Verteilung (UC6)",
    "research_impact": "Forschungsimpact (UC7)",
    "temporal": "Zeitliche Entwicklung (UC8)",
    "tech_cluster": "Technologie-Cluster (UC9)",
    "euroscivoc": "Wissenschaftsdisziplinen (UC10)",
    "actor_type": "Akteurs-Typverteilung (UC11)",
    "patent_grant": "Patent-Erteilungsquoten (UC12)",
    "publication": "Publikationsanalyse (UC-C)",
}


def format_panel_context(panel_context_json: str) -> str:
    """Formatiert Panel-Kontext-JSON als lesbaren Kontext-Block.

    Args:
        panel_context_json: JSON-String mit Panel-Daten aus dem Frontend.
            Erwartet: {"active_panel": "maturity", "data": {...}}
            Oder: {"panels": {"landscape": {...}, "maturity": {...}}}

    Returns:
        Formatierter Text-Block oder leerer String wenn kein Kontext.
    """
    if not panel_context_json or panel_context_json.strip() in ("", "{}"):
        return ""

    try:
        import json
        ctx = json.loads(panel_context_json)
    except (json.JSONDecodeError, TypeError):
        return f"Analyse-Daten:\n{panel_context_json[:8000]}"

    if not ctx:
        return ""

    lines: list[str] = []

    # Format 1: Single active panel
    active = ctx.get("active_panel", "")
    if active and "data" in ctx:
        label = _PANEL_LABELS.get(active, active)
        lines.append(f"Aktuell angezeigte Analyse: {label}")
        data_str = json.dumps(ctx["data"], ensure_ascii=False, indent=2)
        if len(data_str) > 8000:
            data_str = data_str[:8000] + "\n... [gekuerzt]"
        lines.append(data_str)
        return "\n".join(lines)

    # Format 2: Multiple panels summary
    panels = ctx.get("panels", ctx)
    if isinstance(panels, dict):
        for key, val in panels.items():
            if key in _PANEL_LABELS and val:
                label = _PANEL_LABELS[key]
                summary = json.dumps(val, ensure_ascii=False)
                if len(summary) > 1000:
                    summary = summary[:1000] + "..."
                lines.append(f"- {label}: {summary}")
        return "\n".join(lines) if lines else ""

    return ""
