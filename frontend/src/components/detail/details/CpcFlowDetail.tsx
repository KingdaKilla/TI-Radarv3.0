"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- UC5: CPC-Technologiefluss (Detailansicht)
 * 6 Sektionen: MetricCards, Chord-Diagramm, Auto-Analyse,
 * Kombinationstabelle, Whitespace-Heatmap + Tabelle
 * ────────────────────────────────────────────── */

import MetricCard from "@/components/charts/MetricCard";
import DetailChartSection from "@/components/detail/DetailChartSection";
import DetailAnalysisSection from "@/components/detail/DetailAnalysisSection";
import DetailDataSection from "@/components/detail/DetailDataSection";
import CpcChordDiagram from "@/components/charts/CpcChordDiagram";
import WhitespaceHeatmap from "@/components/charts/WhitespaceHeatmap";
import type { CpcFlowPanel } from "@/lib/types";

interface CpcFlowDetailProps {
  data: CpcFlowPanel;
}

/* ── Hilfsfunktionen ── */

function jaccardLabel(j: number): string {
  if (j >= 0.5) return "Starke Konvergenz";
  if (j >= 0.2) return "Moderate Konvergenz";
  if (j >= 0.05) return "Geringe Überschneidung";
  return "Kaum Überschneidung";
}

export default function CpcFlowDetail({ data }: CpcFlowDetailProps) {
  /* CPC-Code → Beschreibung Lookup */
  const cpcLabels: Record<string, string> = {};
  for (const node of data.nodes) {
    cpcLabels[node.id] = node.label;
  }

  const hasChordData = data.nodes.length >= 2 && data.links.length > 0;

  /* Jaccard-Statistiken */
  const allJaccards = data.top_combinations.map((c) => c.jaccard).filter((j) => j > 0);
  const avgJaccard = allJaccards.length > 0
    ? allJaccards.reduce((a, b) => a + b, 0) / allJaccards.length
    : 0;
  const maxJaccard = allJaccards.length > 0
    ? Math.max(...allJaccards)
    : 0;

  /* Stärkstes Paar */
  const topPair = data.top_combinations.length > 0
    ? data.top_combinations.reduce((best, c) => (c.jaccard > best.jaccard ? c : best), data.top_combinations[0])
    : null;

  /* Max Co-Occurrence */
  const maxCoOcc = data.links.length > 0
    ? Math.max(...data.links.map((l) => l.value))
    : 0;

  return (
    <div className="flex flex-col gap-6">
      {/* ── Sektion 1: Kennzahlen ── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <MetricCard
          label="CPC-Klassen"
          value={data.nodes.length}
        />
        <MetricCard
          label="Verbindungen"
          value={data.links.length}
        />
        <MetricCard
          label="Top-Kombinationen"
          value={data.top_combinations.length}
        />
        <MetricCard
          label="Ø Jaccard-Index"
          value={avgJaccard > 0 ? avgJaccard.toFixed(3) : "—"}
        />
        <MetricCard
          label="Max. Jaccard"
          value={maxJaccard > 0 ? maxJaccard.toFixed(3) : "—"}
        />
        <MetricCard
          label="Max. Co-Occurrence"
          value={maxCoOcc > 0 ? maxCoOcc.toLocaleString("de-DE") : "—"}
        />
      </div>

      {/* ── Sektion 2: Heatmap ── */}
      {hasChordData ? (
        <DetailChartSection ariaLabel="Chord-Diagramm: CPC-Technologiefluss (Detailansicht)">
          <CpcChordDiagram nodes={data.nodes} links={data.links} />
        </DetailChartSection>
      ) : (
        <DetailChartSection ariaLabel="CPC-Chord-Diagramm nicht verfügbar">
          <div className="flex h-full items-center justify-center">
            <p className="text-sm italic text-[var(--color-text-muted)]">
              Nicht genügend Daten für die Chord-Darstellung (mind. 2 Knoten und 1 Verbindung erforderlich).
            </p>
          </div>
        </DetailChartSection>
      )}

      {/* ── Sektion 3: Auto-Analyse ── */}
      <DetailAnalysisSection>
        <div className="space-y-2 text-sm text-[var(--color-text-secondary)]">
          <p>
            Die Analyse umfasst <strong>{data.nodes.length}</strong> CPC-Technologieklassen
            mit <strong>{data.links.length}</strong> paarweisen Verbindungen.
            {data.top_combinations.length > 0 && (
              <> Davon wurden <strong>{data.top_combinations.length}</strong> relevante Kombinationen identifiziert.</>
            )}
          </p>

          {topPair && topPair.jaccard > 0 && (
            <p>
              Die stärkste technologische Konvergenz besteht zwischen{" "}
              <strong className="font-mono">{topPair.codes[0]}</strong> und{" "}
              <strong className="font-mono">{topPair.codes[1]}</strong> mit einem
              Jaccard-Index von <strong>{topPair.jaccard.toFixed(3)}</strong> ({jaccardLabel(topPair.jaccard)}).
              {topPair.count > 0 && (
                <> Diese Codes treten in <strong>{topPair.count.toLocaleString("de-DE")}</strong> Patenten gemeinsam auf.</>
              )}
            </p>
          )}

          {avgJaccard > 0 && (
            <p>
              Der durchschnittliche Jaccard-Index der Top-Kombinationen beträgt{" "}
              <strong>{avgJaccard.toFixed(3)}</strong> — dies deutet auf{" "}
              {avgJaccard >= 0.2
                ? "eine ausgeprägte technologische Konvergenz hin."
                : avgJaccard >= 0.05
                  ? "moderate technologische Überschneidungen hin."
                  : "eher spezialisierte, wenig überlappende Technologiefelder hin."}
            </p>
          )}

          <p className="text-xs text-[var(--color-text-muted)]">
            Methodik: Der Jaccard-Index misst die Ähnlichkeit zweier CPC-Code-Mengen als Verhältnis
            von Schnittmenge zu Vereinigungsmenge (J = |A∩B| / |A∪B|). Werte nahe 1 zeigen starke
            Ko-Klassifikation an, Werte nahe 0 bedeuten unabhängige Technologiefelder.
          </p>
        </div>
      </DetailAnalysisSection>

      {/* ── Sektion 4: Vollständige Kombinationstabelle ── */}
      <DetailDataSection title="CPC-Kombinationen (vollständig)">
        {data.top_combinations.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wider text-[var(--color-text-muted)]">
                  <th className="px-3 py-2 w-8">#</th>
                  <th className="px-3 py-2">CPC-Codes</th>
                  <th className="px-3 py-2">Bezeichnung</th>
                  <th className="px-3 py-2 text-right">Jaccard</th>
                  <th className="px-3 py-2">Konvergenz</th>
                  <th className="px-3 py-2 text-right">Häufigkeit</th>
                </tr>
              </thead>
              <tbody>
                {data.top_combinations.map((combo, idx) => (
                  <tr
                    key={`${combo.codes.join("-")}-${idx}`}
                    className="border-b border-[var(--color-border)] last:border-0"
                  >
                    <td className="px-3 py-2 tabular-nums text-[var(--color-text-muted)]">
                      {idx + 1}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-1">
                        {combo.codes.map((code) => (
                          <span
                            key={code}
                            className="rounded bg-blue-100 px-1.5 py-0.5 font-mono text-xs text-blue-800 dark:bg-blue-900/30 dark:text-blue-400"
                          >
                            {code}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-3 py-2 text-xs text-[var(--color-text-secondary)]">
                      {combo.codes.map((code) => cpcLabels[code] || code).join(" × ")}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                      {combo.jaccard.toFixed(3)}
                    </td>
                    <td className="px-3 py-2 text-xs text-[var(--color-text-muted)]">
                      {jaccardLabel(combo.jaccard)}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                      {combo.count.toLocaleString("de-DE")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm italic text-[var(--color-text-muted)]">
            Keine CPC-Kombinationen vorhanden.
          </p>
        )}
      </DetailDataSection>

      {/* ── Sektion 5: Whitespace-Analyse ── */}
      {data.whitespace_opportunities.length > 0 && (
        <DetailDataSection title="Whitespace-Analyse — Innovationslücken">
          <p className="mb-4 text-sm text-[var(--color-text-secondary)]">
            CPC-Code-Paare mit hoher Einzelaktivität aber geringer Ko-Klassifikation.
            Diese Lücken können unerschlossene Innovationschancen darstellen —
            Technologiefelder, die bisher kaum kombiniert wurden (Yoon &amp; Park, 2005).
          </p>

          {/* Whitespace Opportunity Heatmap */}
          <DetailChartSection
            ariaLabel="Heatmap: Whitespace Opportunity Scores"
            heightPx={350}
          >
            <WhitespaceHeatmap
              opportunities={data.whitespace_opportunities}
              cpcLabels={cpcLabels}
            />
          </DetailChartSection>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wider text-[var(--color-text-muted)]">
                  <th className="px-3 py-2 w-8">#</th>
                  <th className="px-3 py-2">CPC-Codes</th>
                  <th className="px-3 py-2">Bezeichnung</th>
                  <th className="px-3 py-2 text-right">Patente A</th>
                  <th className="px-3 py-2 text-right">Patente B</th>
                  <th className="px-3 py-2 text-right">Jaccard</th>
                  <th className="px-3 py-2 text-right">Opportunity Score</th>
                </tr>
              </thead>
              <tbody>
                {data.whitespace_opportunities.map((ws, idx) => (
                  <tr
                    key={`${ws.code_a}-${ws.code_b}`}
                    className="border-b border-[var(--color-border)] last:border-0"
                  >
                    <td className="px-3 py-2 tabular-nums text-[var(--color-text-muted)]">
                      {idx + 1}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-1">
                        <span className="rounded bg-amber-100 px-1.5 py-0.5 font-mono text-xs text-amber-800 dark:bg-amber-900/30 dark:text-amber-400">
                          {ws.code_a}
                        </span>
                        <span className="rounded bg-amber-100 px-1.5 py-0.5 font-mono text-xs text-amber-800 dark:bg-amber-900/30 dark:text-amber-400">
                          {ws.code_b}
                        </span>
                      </div>
                    </td>
                    <td className="px-3 py-2 text-xs text-[var(--color-text-secondary)]">
                      {cpcLabels[ws.code_a] || ws.code_a} × {cpcLabels[ws.code_b] || ws.code_b}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                      {ws.freq_a.toLocaleString("de-DE")}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                      {ws.freq_b.toLocaleString("de-DE")}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                      {ws.jaccard.toFixed(3)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800 dark:bg-amber-900/30 dark:text-amber-400">
                        {ws.opportunity_score.toFixed(2)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-[var(--color-text-muted)]">
            Opportunity Score = (1 − Jaccard) × √(Patente_A × Patente_B) / max(Patente).
            Hohe Werte = beide Felder aktiv, aber kaum kombiniert.
          </p>
        </DetailDataSection>
      )}
    </div>
  );
}
