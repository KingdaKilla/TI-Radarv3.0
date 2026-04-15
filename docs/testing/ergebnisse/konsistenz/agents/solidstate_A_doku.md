# Konsistenz-Audit TI-Radar v3 — Rolle A (Dokumentierer)
## Technologie: `solid state battery`

**Quelle:** `docs/testing/ergebnisse/konsistenz/raw/raw3_solidstate.json`
**Datum:** 2026-04-14

---

## 1. Header-KPIs (Executive Summary)

| Feld | Wert |
|---|---|
| Patente | **358** |
| EU-Projekte | **113** |
| Publikationen | **0** |
| Phase | **Reife Stagnation** (Doppel-Label) |
| Wettbewerb | **Wettbewerbsintensiver Markt** |
| Förderung | **€297M** |
| Forschungsimpact | **Sehr hoch** |
| Cluster (Fokus) | UC6 Geographische Verteilung (via Kopfzeilen-Text) |

---

## 2. UC-Panel-Metriken (Beobachtungsprotokoll)

| UC | Tab | Kern-Metriken (beobachtet) | Jahresachse |
|---|---|---|---|
| UC1 | Aktivitätstrends | Patente CAGR **35.5 %**, Projekte CAGR **30.7 %**; Top-CPC: Y02E60/10 (12.631), H01M10/0562 (8.872), H01M10/052 (6.986), H01M10/0525 (6.601), Y02P70/50 (5.515) | **2017–2026** |
| UC2 | S-Kurve & Reife | Phase **Reife**, R² = **0.982**, Wendepunkt **2024**, Konfidenz **94 %**; Phasen-Leiste: Entstehung→Wachstum→Reife→Sättigung→Rückgang | **2016–2026** |
| UC5 | Technologiekonvergenz | **10 CPC-Klassen**, Ø Jaccard **0.328**, **10 Whitespace-Lücken**; Sektionen: Y02E, H01M, Y02P, H01B, C01P, C01B, C01G, Y02T, C08F, C08L | — |
| UC3 | Wettbewerb & HHI | **Niedrige Konzentration**; Top-Anmelder (abgeschnitten): FRAUNHOFER…, AVESTA HOLDING, CENTRO DE INVESTI…, FUNDACIO INSTITUT…, UPPSALA UNIVERSIT…, SPECIFICPOLYMERS, PULSEDEON OY, AGENCIA ESTATAL C… (Skala 0–28) | — |
| UC8 | Dynamik & Persistenz | **22 Akteure**, **Schrumpfend (-97 netto)**; Segmente: Persistente / Neue / Ausgeschieden | **2016–2026** |
| UC11 | Akteurs-Typen | **365 Akteure**, dominiert: **KMU / Unternehmen**; Kategorien: KMU/Unternehmen, Higher Education, Research Organisation, Other, Public Body | — |
| UC4 | Förderung | Gesamt **296,6 Mio. EUR**, **113 Projekte**; Instrumente: HORIZON-RIA, RIA, HORIZON-IA, HORIZON-ERC, HORIZON-EIC, ERC-COG, ERC-ADG, HORIZON…, ERC-STG, IA | — |
| UC7 | Forschungsimpact | **200 Publikationen**, **196,4 Zitate/Pub.**, **15 Institutionen** | **2016–2025** |
| UC13 | Publikationen | **11,2 Pub/Projekt**, **DOI 83 %** | **2016–2024** |
| UC6 | Geographie | **10 Länder**, Top: **Deutschland**; Reihenfolge: DE, FR, BE, ES, UK, IT, SE, NL, AT, FI | — |
| UC9 | Tech-Cluster | **3 Cluster**, **44 Akteure**, **119 CPC-Klassen**; 5-dim Profil (Patente/Akteure/Dichte/Kohärenz/Wachstum) für CPC-Sektionen C, H, Y | — |
| UC10 | EuroSciVoc | **1 Feld**, **106 Projekte**; dominantes Feld: **„law"**, Shannon-Index **4,77**; Prozente: 0 % / 0 % / 0 % / 1 % / 1 % | — |
| UC12 | Patenterteilung | Quote **13,2 %**, **39,2 Mon.** bis Erteilung, **12.074 Anmeldungen**, **1.592 Erteilungen** | **2016–2026** |

---

## 3. Panels mit Warnhinweis „Daten ggf. unvollständig"

- UC1 Aktivitätstrends
- UC2 S-Kurve & Reife
- UC8 Dynamik & Persistenz
- UC7 Forschungsimpact
- UC12 Patenterteilung

**Ohne Warnhinweis, obwohl potenziell relevant:** UC13 Publikationen (Achse 2016–2024, d. h. aktueller Rand fehlt/abweichend), UC4 Förderung, UC3 Wettbewerb, UC11 Akteurs-Typen, UC10 EuroSciVoc.

---

## 4. Nachvollziehbarkeits-Metadaten pro Panel

| UC | Quellen | Ladezeit |
|---|---|---|
| UC1 | 2 | 13,4 s |
| UC2 | 1 | 13,4 s |
| UC5 | 1 | 13,4 s |
| UC3 | 2 | 13,4 s |
| UC8 | 2 | 13,4 s |
| UC11 | 1 | 13,4 s |
| UC4 | 1 | 13,4 s |
| UC7 | 2 | 13,4 s |
| UC13 | 1 | 13,4 s |
| UC6 | 2 | 13,4 s |
| UC9 | 1 | 13,4 s |
| UC10 | 1 | 13,4 s |
| UC12 | 1 | 13,4 s |

Alle Panels: identische Ladezeit **13,4 s** (deutet auf synchrones, gemeinsames Laden/Caching hin).

---

## 5. Sichtbare Diskrepanzen zwischen Header und Panels (Roh-Beobachtung)

1. **Publikationen**: Header **0**, UC7 **200 Publikationen** + 196,4 Zitate/Pub.
2. **Phase**: Header **„Reife Stagnation"** (Doppelbegriff), UC2 **„Reife"** (einfach); zusätzlich CAGR-Patente **+35,5 %** — schwer vereinbar mit „Stagnation".
3. **Wettbewerb**: Header **„Wettbewerbsintensiver Markt"**, UC3 **„Niedrige Konzentration"**.
4. **Projekte**: Header **113** = UC4 **113** ✓, aber UC10 **106 Projekte** ✗ (−7).
5. **Dynamik**: UC8 „22 Akteure" vs. UC11 „365 Akteure" — unterschiedliche Zählbasen.
6. **EuroSciVoc**: Dominierendes Feld **„law"** für Festkörperbatterien — inhaltlich unplausibel.
7. **Jahresachsen divergieren** im selben Dashboard:
   - 2016–2026: UC2, UC8, UC12
   - 2017–2026: UC1
   - 2016–2025: UC7
   - 2016–2024: UC13
8. **Rundungs-Diskrepanz**: Header **€297M** vs. UC4 **296,6 Mio. EUR** (geringfügig, Rundung).
9. **UC12**: 1.592 / 12.074 = 13,19 % ✓ (rechnerisch konsistent mit angezeigter Quote 13,2 %).
10. **UC13 Plausibilitätsprobe**: 11,2 Pub/Projekt × 113 Projekte ≈ **1.266 Pubs** — stimmt weder mit Header (0) noch mit UC7 (200) überein.

---

## 6. Cluster-Zugehörigkeit / Sonstiges

- Header-Kopfzeile nennt explizit „Geographische Perspektive" (doppelt) und UC6 als Einleitungs-UC des aktuell offenen Clusters.
- UC9 Tech-Cluster zeigt nur **3 Cluster / 44 Akteure** — deutlich weniger als UC11 (365) und UC8 (22); drei verschiedene Akteurs-Zählungen im selben Dashboard.
- UC10 Prozentleiste zeigt vier Werte mit **0 %** + zweimal **1 %**, obwohl nur **1 Feld** gemeldet wird — Darstellung intransparent.

---

**Executive Summary (2 Sätze):** Das Dashboard liefert für `solid state battery` konsistente Patent-/Projekt-/Förderungs-Kopfzahlen, widerspricht sich aber flächendeckend in den Panel-Details (0 vs. 200 Publikationen, „Reife Stagnation" bei +35,5 % CAGR, „wettbewerbsintensiv" bei niedriger HHI-Konzentration, drei unterschiedliche Akteurs-Zählungen, vier verschiedene Jahresachsen). Die EuroSciVoc-Zuordnung „law" als dominantes wissenschaftliches Feld macht UC10 für diese Technologie unbrauchbar.

**Kritischster Befund:** UC10 klassifiziert Festkörperbatterie-Projekte unter „law" — die Wissenschaftstaxonomie ist für diese Tech komplett fehlgeroutet und damit entscheidungsirrelevant.
