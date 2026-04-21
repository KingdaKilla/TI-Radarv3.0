"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- UC10: Wissenschaftsdisziplinen (Detailansicht)
 * Full horizontal bar chart + complete fields table
 * with dynamic columns + index explanations
 * ────────────────────────────────────────────── */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import MetricCard from "@/components/charts/MetricCard";
import DetailChartSection from "@/components/detail/DetailChartSection";
import DetailAnalysisSection from "@/components/detail/DetailAnalysisSection";
import DetailDataSection from "@/components/detail/DetailDataSection";
import { CHART_COLORS } from "@/lib/chart-colors";
import type { EuroSciVocPanel } from "@/lib/types";

interface EuroSciVocDetailProps {
  data: EuroSciVocPanel;
}

export default function EuroSciVocDetail({ data }: EuroSciVocDetailProps) {
  // Bug v3.4.10/α-C: Primär disciplines (Level 2, bis 50 Einträge) —
  // fields_of_science ist bei engen Technologien oft zu spärlich befüllt.
  const disciplinesChart = (data.disciplines ?? [])
    .filter((d) => d.share > 0)
    .slice(0, 25)
    .map((d) => ({
      id: d.id,
      label: d.label,
      total_publications: d.publication_count ?? 0,
      total_projects: d.project_count,
      share: d.share,
      share_pct: d.share * 100,
    }));
  const fieldsChart = data.fields_of_science.map((f) => ({
    ...f,
    share_pct: f.share * 100,
  }));
  const chartData = disciplinesChart.length > 0 ? disciplinesChart : fieldsChart;

  /* Dynamische Höhe: min 500px, 40px pro Feld */
  const chartHeight = Math.max(500, chartData.length * 40);

  /* Dynamische Spalten: nur anzeigen, wenn mindestens ein Wert > 0 */
  const hasPublications = chartData.some((f) => (f.total_publications ?? 0) > 0);
  const hasProjects = chartData.some((f) => (f.total_projects ?? 0) > 0);

  return (
    <div className="flex flex-col gap-6">
      {/* ── Kennzahlen ── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MetricCard
          label="Shannon-Index"
          value={data.interdisciplinarity.shannon_index.toFixed(2)}
        />
        <MetricCard
          label="Simpson-Index"
          value={data.interdisciplinarity.simpson_index.toFixed(3)}
        />
        <MetricCard
          label="Aktive Disziplinen"
          value={data.interdisciplinarity.active_disciplines}
        />
        <MetricCard
          label="Mapping-Abdeckung"
          value={`${(data.mapping_coverage * 100).toFixed(1)}%`}
        />
      </div>

      {/* ── Index-Erklaerungen ── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 text-[10px] text-[var(--color-text-muted)] -mt-2">
        <p>Vielfalt der Disziplinen — höher = gleichmäßiger verteilt</p>
        <p>Konzentration — niedriger = diverser</p>
        <p>Anzahl aktive Wissenschaftsdisziplinen</p>
        <p>Anteil der zuordenbaren Projekte</p>
      </div>

      {/* ── Alle Wissenschaftsfelder (vergroessert) ── */}
      {chartData.length > 0 && (
        <DetailChartSection
          ariaLabel="Alle Wissenschaftsfelder nach Anteil"
          heightPx={chartHeight}
        >
          <ResponsiveContainer width="100%" height={chartHeight}>
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ top: 10, right: 30, left: 10, bottom: 10 }}
            >
              <defs>
                <linearGradient id="detail-esvcBar" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="5%" stopColor={CHART_COLORS.purple} stopOpacity={0.9} />
                  <stop offset="95%" stopColor={CHART_COLORS.purple} stopOpacity={0.6} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis
                type="number"
                tick={{ fontSize: 12, fill: "var(--color-text-muted)" }}
                tickFormatter={(v) => `${v.toFixed(0)}%`}
                label={{
                  value: "Anteil (%)",
                  position: "insideBottom",
                  offset: -5,
                  style: { fontSize: 12, fill: "var(--color-text-muted)" },
                }}
              />
              <YAxis
                dataKey="label"
                type="category"
                width={160}
                tick={{ fontSize: 11, fill: "var(--color-text-secondary)" }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--color-bg-panel)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "8px",
                  fontSize: "13px",
                }}
                formatter={(value: number) => [`${value.toFixed(1)}%`, "Anteil"]}
              />
              <Bar
                dataKey="share_pct"
                fill="url(#detail-esvcBar)"
                radius={[0, 4, 4, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </DetailChartSection>
      )}

      {/* ── Vollstaendige Felder-Tabelle ── */}
      <DetailDataSection title="Wissenschaftsfelder">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wider text-[var(--color-text-muted)]">
                <th className="pb-3 pr-4">Feld</th>
                {hasPublications && (
                  <th className="pb-3 pr-4 text-right">Publikationen</th>
                )}
                {hasProjects && (
                  <th className="pb-3 pr-4 text-right">Projekte</th>
                )}
                <th className="pb-3 pr-4 text-right">Unterfelder</th>
                <th className="pb-3 pr-4 text-right">Anteil</th>
                <th className="pb-3 text-right">CAGR</th>
              </tr>
            </thead>
            <tbody>
              {data.fields_of_science.map((field) => (
                <tr
                  key={field.id}
                  className="border-b border-[var(--color-border)]/50 text-[var(--color-text-secondary)]"
                >
                  <td className="py-2 pr-4 font-medium">{field.label}</td>
                  {hasPublications && (
                    <td className="py-2 pr-4 text-right">
                      {field.total_publications.toLocaleString("de-DE")}
                    </td>
                  )}
                  {hasProjects && (
                    <td className="py-2 pr-4 text-right">
                      {field.total_projects.toLocaleString("de-DE")}
                    </td>
                  )}
                  <td className="py-2 pr-4 text-right">
                    {field.active_sub_fields.toLocaleString("de-DE")}
                  </td>
                  <td className="py-2 pr-4 text-right">
                    {(field.share * 100).toFixed(1)}%
                  </td>
                  <td
                    className={`py-2 text-right font-medium ${
                      field.cagr >= 0
                        ? "text-green-600 dark:text-green-400"
                        : "text-red-500 dark:text-red-400"
                    }`}
                  >
                    {(field.cagr * 100).toFixed(1)}%
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
