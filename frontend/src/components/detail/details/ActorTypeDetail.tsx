"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v2 -- UC11: Akteurs-Typverteilung (Detailansicht)
 * Enlarged donut chart + full type breakdown table
 * with dynamic columns + type explanations
 * ────────────────────────────────────────────── */

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import MetricCard from "@/components/charts/MetricCard";
import DetailChartSection from "@/components/detail/DetailChartSection";
import DetailAnalysisSection from "@/components/detail/DetailAnalysisSection";
import DetailDataSection from "@/components/detail/DetailDataSection";
import { CHART_COLORS, PALETTE } from "@/lib/chart-colors";
import type { ActorTypePanel } from "@/lib/types";

interface ActorTypeDetailProps {
  data: ActorTypePanel;
}

const TYPE_COLORS: Record<string, string> = {
  "Higher Education": CHART_COLORS.blue,
  "Private Company": CHART_COLORS.orange,
  "Research Organisation": CHART_COLORS.green,
  "Other": CHART_COLORS.skyBlue,
  "Public Body": CHART_COLORS.purple,
};

const FALLBACK_COLORS = PALETTE;

function formatEur(value: number): string {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)} Mrd. EUR`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)} Mio. EUR`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)} Tsd. EUR`;
  return `${value.toLocaleString("de-DE")} EUR`;
}

export default function ActorTypeDetail({ data }: ActorTypeDetailProps) {
  const chartData = data.type_breakdown.map((entry) => ({
    name: entry.label,
    value: entry.actor_count,
    share: entry.actor_share,
    funding: entry.funding_eur,
  }));

  /* Dynamische Spalten: nur anzeigen, wenn mindestens ein Wert > 0 */
  const hasPatents = data.type_breakdown.some((t) => t.patent_count > 0);
  const hasFunding = data.type_breakdown.some((t) => t.funding_eur > 0);
  const hasProjects = data.type_breakdown.some((t) => t.project_count > 0);

  return (
    <div className="flex flex-col gap-6">
      {/* ── Kennzahlen ── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MetricCard
          label="Klassifizierte Akteure"
          value={data.total_classified_actors.toLocaleString("de-DE")}
        />
        <MetricCard
          label="Klassifizierungsrate"
          value={`${(data.classification_coverage * 100).toFixed(1)}%`}
        />
        <MetricCard
          label="KMU-Anteil"
          value={`${(data.sme_share * 100).toFixed(1)}%`}
        />
        <MetricCard
          label="Organisationstypen"
          value={data.type_breakdown.length}
        />
      </div>

      {/* ── Donut-Chart (vergroessert) ── */}
      <DetailChartSection ariaLabel="Verteilung nach Organisationstyp">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={90}
              outerRadius={150}
              dataKey="value"
              nameKey="name"
              paddingAngle={2}
              label={({ name, share }) =>
                `${name}: ${(share * 100).toFixed(1)}%`
              }
              labelLine={{ strokeWidth: 1 }}
            >
              {chartData.map((entry, idx) => (
                <Cell
                  key={entry.name}
                  fill={TYPE_COLORS[entry.name] ?? FALLBACK_COLORS[idx % FALLBACK_COLORS.length]}
                />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--color-bg-panel)",
                border: "1px solid var(--color-border)",
                borderRadius: "8px",
                fontSize: "13px",
              }}
              formatter={(value: number, name: string) => [
                value.toLocaleString("de-DE"),
                name,
              ]}
            />
            <Legend
              wrapperStyle={{ fontSize: "13px" }}
              formatter={(value: string) => (
                <span className="text-[var(--color-text-secondary)]">{value}</span>
              )}
            />
          </PieChart>
        </ResponsiveContainer>
      </DetailChartSection>

      {/* ── Typ-Erklaerungen ── */}
      <div className="grid grid-cols-2 gap-2 text-[10px] text-[var(--color-text-muted)] sm:grid-cols-3">
        <p><span className="font-semibold" style={{ color: CHART_COLORS.blue }}>HES</span> — Hochschulen und Universitäten</p>
        <p><span className="font-semibold" style={{ color: CHART_COLORS.orange }}>PRC</span> — Privatunternehmen (inkl. KMU)</p>
        <p><span className="font-semibold" style={{ color: CHART_COLORS.green }}>REC</span> — Außeruniversitäre Forschungseinrichtungen</p>
        <p><span className="font-semibold" style={{ color: CHART_COLORS.skyBlue }}>OTH</span> — Sonstige Organisationen</p>
        <p><span className="font-semibold" style={{ color: CHART_COLORS.purple }}>PUB</span> — Öffentliche Einrichtungen und Behörden</p>
      </div>

      {/* ── Auto-Analyse ── */}
      <DetailAnalysisSection>
        <div className="space-y-2 text-sm text-[var(--color-text-secondary)]">
          <p>
            Insgesamt wurden <strong>{data.total_classified_actors.toLocaleString("de-DE")}</strong> Akteure
            klassifiziert (Abdeckung: <strong>{(data.classification_coverage * 100).toFixed(1)}%</strong>).
            {data.sme_share > 0 && (
              <> Der KMU-Anteil liegt bei <strong>{(data.sme_share * 100).toFixed(1)}%</strong>
              {data.sme_share >= 0.5
                ? " — KMU dominieren die Akteurslandschaft."
                : data.sme_share >= 0.3
                  ? " — ein signifikanter Anteil der Akteure sind KMU."
                  : " — die Akteurslandschaft wird von größeren Organisationen geprägt."}
              </>
            )}
          </p>

          {data.type_breakdown.length > 0 && (() => {
            const sorted = [...data.type_breakdown].sort((a, b) => b.actor_share - a.actor_share);
            const dominant = sorted[0];
            return (
              <p>
                Der häufigste Organisationstyp ist <strong>{dominant.label}</strong> mit{" "}
                <strong>{dominant.actor_count.toLocaleString("de-DE")}</strong> Akteuren
                ({(dominant.actor_share * 100).toFixed(1)}%).
                {sorted.length >= 2 && (
                  <> Es folgt <strong>{sorted[1].label}</strong> mit{" "}
                  <strong>{sorted[1].actor_count.toLocaleString("de-DE")}</strong> Akteuren
                  ({(sorted[1].actor_share * 100).toFixed(1)}%).</>
                )}
              </p>
            );
          })()}

          {data.type_breakdown.some((t) => t.funding_eur > 0) && (() => {
            const topFunded = [...data.type_breakdown].sort((a, b) => b.funding_eur - a.funding_eur)[0];
            return (
              <p>
                Den größten Anteil an der Förderung erhält <strong>{topFunded.label}</strong> mit{" "}
                <strong>{formatEur(topFunded.funding_eur)}</strong>.
              </p>
            );
          })()}
        </div>
      </DetailAnalysisSection>

      {/* ── Vollstaendige Typ-Tabelle ── */}
      <DetailDataSection title="Aufschlüsselung nach Organisationstyp">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wider text-[var(--color-text-muted)]">
                <th className="pb-3 pr-4">Typ</th>
                <th className="pb-3 pr-4 text-right">Akteure</th>
                {hasPatents && (
                  <th className="pb-3 pr-4 text-right">Patente</th>
                )}
                {hasProjects && (
                  <th className="pb-3 pr-4 text-right">Projekte</th>
                )}
                {hasFunding && (
                  <th className="pb-3 pr-4 text-right">Förderung</th>
                )}
                <th className="pb-3 text-right">Anteil</th>
              </tr>
            </thead>
            <tbody>
              {data.type_breakdown.map((entry) => (
                <tr
                  key={entry.label}
                  className="border-b border-[var(--color-border)]/50 text-[var(--color-text-secondary)]"
                >
                  <td className="py-2 pr-4 font-medium">
                    <span className="flex items-center gap-2">
                      <span
                        className="inline-block h-3 w-3 rounded-full"
                        style={{
                          backgroundColor:
                            TYPE_COLORS[entry.label] ??
                            FALLBACK_COLORS[data.type_breakdown.indexOf(entry) % FALLBACK_COLORS.length],
                        }}
                        aria-hidden="true"
                      />
                      {entry.label}
                    </span>
                  </td>
                  <td className="py-2 pr-4 text-right">
                    {entry.actor_count.toLocaleString("de-DE")}
                  </td>
                  {hasPatents && (
                    <td className="py-2 pr-4 text-right">
                      {entry.patent_count.toLocaleString("de-DE")}
                    </td>
                  )}
                  {hasProjects && (
                    <td className="py-2 pr-4 text-right">
                      {entry.project_count.toLocaleString("de-DE")}
                    </td>
                  )}
                  {hasFunding && (
                    <td className="py-2 pr-4 text-right">
                      {formatEur(entry.funding_eur)}
                    </td>
                  )}
                  <td className="py-2 text-right">
                    {(entry.actor_share * 100).toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DetailDataSection>
    </div>
  );
}
