# Konsistenz-Audit · Rolle A (Dokumentierer) · Technologie: autonomous driving

Quelle: `docs/testing/ergebnisse/konsistenz/raw/raw_autonomous.json`
Live-System: `https://app.drakain.de`

## Header (Executive-Summary-Kopfzeile)

| Feld | Wert |
|---|---|
| Technologie | AUTONOMOUS DRIVING |
| Patente | **734** |
| EU-Projekte | **235** |
| Publikationen | **0** |
| Phase | **Reife** |
| Entwicklung | Rückläufige Entwicklung |
| Wettbewerb | Wettbewerbsintensiver Markt |
| Förderung | **€755 M** |
| Forschungsimpact (Label) | Sehr hoher Forschungsimpact |

Header-Kopfzeile im Volltext:
> "AUTONOMOUS DRIVING | Technologie-Intelligence Analyse | 734 | Patente | 235 | EU-Projekte | 0 | Publikationen | Phase: Reife | Rückläufige Entwicklung | Wettbewerbsintensiver Markt | €755M Förderung | Sehr hoher Forschungsimpact | Geographische Perspektive …"

## UC × beobachtete Kern-Metrik/en

**Kritischer Befund der Rohdaten:** In allen 13 Panels ist `activeTab = "Neue Analyse"` und der `mainText` identisch — er enthält ausschließlich die Executive-Summary-Kopfzeile sowie die allgemeinen Cluster-Info-Texte (`Dieser Analysebereich umfasst: …`). **Keine einzige panel-spezifische Nutzdatenzeile** (kein HHI-Wert, kein CAGR, keine Top-Länder, keine h-Index-Zahl, keine Grant-Rate, keine CPC-Klasse, keine Akteurs-Typ-Verteilung, keine Jahresreihe) liegt in der JSON-Extraktion vor.

| Tab | UC | Versprochene Kern-Metrik | Beobachtet (im Dump) |
|---|---|---|---|
| Aktivitätstrends | UC1 Technologie-Landschaft | CAGR / Jahresreihen Patente-Projekte-Publikationen | — keine (nur Landing-Text) |
| S-Kurve & Reife | UC2 Reifegrad-Analyse | Phase + R² + Fit-Kurve | Phase-Badge aus Header: **Reife** (kein R², kein Zeitraum, keine Kurvendaten) |
| Technologiekonvergenz | UC5 Cross-Tech Intelligence | CPC-Konvergenz + Whitespace | — keine CPC-Klassen genannt |
| Wettbewerb & HHI | UC3 Wettbewerbsanalyse | HHI-Wert + dominante Akteure | — kein HHI-Wert; nur Header-Label "Wettbewerbsintensiver Markt" |
| Dynamik & Persistenz | UC8 Zeitliche Entwicklung | Neue/Persistente/Ausgeschiedene Akteure | — keine Zahlen |
| Akteurs-Typen | UC11 Akteurs-Typen | Breakdown Hochschule/Forschung/Industrie/öffentlich | — kein Breakdown |
| Förderung | UC4 Förderungsanalyse | EU-Fördervolumen × Forschungsgebiet × Zeit | Gesamt aus Header: **€755 M** (keine Aufschlüsselung, kein Zeitverlauf) |
| Forschungsimpact | UC7 Forschungsimpact | h-Index, Zitationen, Top-Institutionen | — keine Zahl; nur Header-Label "Sehr hoher Forschungsimpact" |
| Publikationen | UC13 Publikations-Impact | Pub × Projekte + Pub/Project-Effizienz | Header: **0 Publikationen** |
| Geographie | UC6 Geographische Verteilung | Globale Verteilung, Top-Länder, EU-Anteil | — keine Länder genannt |
| Tech-Cluster | UC9 Technologie-Cluster | 5-dim Profil (Aktivität/Vielfalt/Dichte/Kohärenz/Wachstum) | — keine Dimensionen |
| EuroSciVoc | UC10 Wissenschaftsdisziplinen | Disziplinen-Zuordnung | — keine Disziplin genannt |
| Patenterteilung | UC12 Erteilungsquoten | Grant-Rate + Time-to-Grant | — kein Wert |

## Warnung-Liste: Panels mit "Keine Daten" / leer / nur Landing-Text

Jeder einzelne Tab liefert im Dump **keine Detail-Payload**. Alle `mainText`-Felder enthalten wortgleich denselben Text (Landing-Screen). Zusätzlich ist `activeTab` für **jeden** Tab `"Neue Analyse"` statt des eigentlichen Tab-Namens — Hinweis darauf, dass während der Extraktion der Panelwechsel nicht aktiv wurde bzw. das jeweilige Panel nicht in den sichtbaren `main`-Bereich geladen wurde.

Konkrete Warnungen:

- **UC1 Aktivitätstrends:** `activeTab=Neue Analyse`, keine Jahresreihe, kein CAGR-Wert im Dump.
- **UC2 S-Kurve & Reife:** Phase `Reife` nur aus Header ableitbar; kein R², kein Zeitraum, keine Fit-Metriken.
- **UC5 Technologiekonvergenz:** Keine CPC-Klassen, keine Whitespace-Lücken im Dump.
- **UC3 Wettbewerb & HHI:** Kein HHI-Zahlwert; nur qualitatives Header-Label.
- **UC8 Dynamik & Persistenz:** Kein Entry/Exit/Persistence-Count.
- **UC11 Akteurs-Typen:** Kein %-Breakdown.
- **UC4 Förderung:** Nur Gesamtsumme `€755 M` aus Header; keine Aufschlüsselung nach Gebiet/Jahr.
- **UC7 Forschungsimpact:** Kein h-Index, keine Top-Institutionen.
- **UC13 Publikationen:** Header meldet **0 Publikationen** — Detail-Panel im Dump leer (konsistent mit 0, aber keine Pub/Project-Effizienz vorhanden).
- **UC6 Geographie:** Keine Länder, kein EU-Anteil, keine Karten-Labels.
- **UC9 Tech-Cluster:** Keine 5-dim Scores.
- **UC10 EuroSciVoc:** Keine Disziplin genannt.
- **UC12 Patenterteilung:** Keine Grant-Rate, kein Time-to-Grant.

## Hinweis zur Extraktion

Da alle 13 `mainText`-Einträge byteweise identisch sind und `activeTab` durchgängig `"Neue Analyse"` lautet, liegt der Verdacht nahe, dass die Extraktion für **autonomous driving** die Panels nicht aktivieren konnte (z. B. weil das Dashboard auf dem Landing-Screen "Neue Analyse" stehen blieb). Rolle B und C müssen berücksichtigen, dass belastbare Aussagen über UC-Liefertreue nur aus den Header-Kennzahlen möglich sind — alle Panel-Details fehlen im Dump.
