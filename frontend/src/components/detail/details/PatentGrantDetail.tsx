"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- UC12: Erteilungsquoten (Detailansicht)
 * Enlarged composed chart + full year trend table
 * ────────────────────────────────────────────── */

import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceArea,
} from "recharts";
import MetricCard from "@/components/charts/MetricCard";
import DetailChartSection from "@/components/detail/DetailChartSection";
import DetailAnalysisSection from "@/components/detail/DetailAnalysisSection";
import DetailDataSection from "@/components/detail/DetailDataSection";
import { CHART_COLORS } from "@/lib/chart-colors";
import type { PatentGrantPanel } from "@/lib/types";

interface PatentGrantDetailProps {
  data: PatentGrantPanel;
}

export default function PatentGrantDetail({ data }: PatentGrantDetailProps) {
  const dataCompleteYear = 2025;

  const chartData = data.year_trend.map((entry) => ({
    ...entry,
    grant_rate_pct: entry.grant_rate * 100,
  }));

  return (
    <div className="flex flex-col gap-6">
      {/* ── Kennzahlen ── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MetricCard
          label="Erteilungsquote"
          value={`${(data.summary.grant_rate * 100).toFixed(1)}%`}
        />
        <MetricCard
          label="Bearbeitungszeit"
          value={data.summary.avg_time_to_grant_months.toFixed(1)}
          unit="Monate"
        />
        <MetricCard
          label="Anmeldungen"
          value={data.summary.total_applications.toLocaleString("de-DE")}
        />
        <MetricCard
          label="Erteilungen"
          value={data.summary.total_grants.toLocaleString("de-DE")}
        />
      </div>

      {/* ── Datenqualitäts-Hinweis ── */}
      <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-4 py-3 text-xs text-[var(--color-text-secondary)]">
        <p>
          Alle Zahlen beziehen sich auf Patentanmeldungen (A-Dokumente) und -erteilungen
          (B-Dokumente) im Bereich der gesuchten Technologie (CPC-gefiltert).
          Die Bearbeitungszeit ergibt sich aus dem Median zwischen Erstanmeldung
          und Erteilungsdatum der zugehörigen Patentfamilien.
        </p>
      </div>

      {/* ── Anmeldungen / Erteilungen / Quote (vergroessert) ── */}
      {chartData.length > 0 && (
        <DetailChartSection ariaLabel="Anmeldungen, Erteilungen und Quote ueber Zeit">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={chartData}
              margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
            >
              <defs>
                <linearGradient id="detail-grantApply" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={CHART_COLORS.skyBlue} stopOpacity={0.8} />
                  <stop offset="95%" stopColor={CHART_COLORS.skyBlue} stopOpacity={0.3} />
                </linearGradient>
                <linearGradient id="detail-grantGrant" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={CHART_COLORS.green} stopOpacity={0.8} />
                  <stop offset="95%" stopColor={CHART_COLORS.green} stopOpacity={0.3} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis
                dataKey="year"
                tick={{ fontSize: 12, fill: "var(--color-text-muted)" }}
              />
              <YAxis
                yAxisId="left"
                tick={{ fontSize: 12, fill: "var(--color-text-muted)" }}
                width={55}
                label={{
                  value: "Anzahl",
                  angle: -90,
                  position: "insideLeft",
                  style: { fontSize: 12, fill: "var(--color-text-muted)" },
                }}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={{ fontSize: 12, fill: "var(--color-text-muted)" }}
                tickFormatter={(v) => `${v}%`}
                domain={[0, 100]}
                width={55}
                label={{
                  value: "Quote (%)",
                  angle: 90,
                  position: "insideRight",
                  style: { fontSize: 12, fill: "var(--color-text-muted)" },
                }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--color-bg-panel)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "8px",
                  fontSize: "13px",
                }}
                formatter={(value: number, name: string) => {
                  if (name === "grant_rate_pct")
                    return [`${value.toFixed(1)}%`, "Quote"];
                  if (name === "application_count")
                    return [value.toLocaleString("de-DE"), "Anmeldungen"];
                  if (name === "grant_count")
                    return [value.toLocaleString("de-DE"), "Erteilungen"];
                  return [value, name];
                }}
              />
              <Legend
                wrapperStyle={{ fontSize: "13px" }}
                formatter={(value: string) => {
                  const labels: Record<string, string> = {
                    application_count: "Anmeldungen",
                    grant_count: "Erteilungen",
                    grant_rate_pct: "Quote (%)",
                  };
                  return labels[value] ?? value;
                }}
              />
              <Bar
                yAxisId="left"
                dataKey="application_count"
                fill="url(#detail-grantApply)"
                radius={[3, 3, 0, 0]}
                barSize={16}
              />
              <Bar
                yAxisId="left"
                dataKey="grant_count"
                fill="url(#detail-grantGrant)"
                radius={[3, 3, 0, 0]}
                barSize={16}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="grant_rate_pct"
                stroke={CHART_COLORS.blue}
                strokeWidth={2.5}
                dot={{ r: 4, fill: CHART_COLORS.blue }}
                activeDot={{ r: 6 }}
              />
              {dataCompleteYear && chartData.length > 0 && chartData[chartData.length - 1].year > dataCompleteYear && (
                <ReferenceArea
                  yAxisId="left"
                  x1={dataCompleteYear}
                  x2={chartData[chartData.length - 1].year}
                  fill="var(--color-text-muted)"
                  fillOpacity={0.08}
                  label={{ value: "Daten ggf. unvollständig", fontSize: 10, fill: "var(--color-text-muted)", position: "insideTop" }}
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </DetailChartSection>
      )}

      {/* ── Auto-Analyse ── */}
      <DetailAnalysisSection>
        <div className="space-y-2 text-sm text-[var(--color-text-secondary)]">
          <p>
            Die Gesamterteilungsquote liegt bei{" "}
            <strong>{(data.summary.grant_rate * 100).toFixed(1)}%</strong> —
            von <strong>{data.summary.total_applications.toLocaleString("de-DE")}</strong> Anmeldungen
            wurden <strong>{data.summary.total_grants.toLocaleString("de-DE")}</strong> erteilt.
            {data.summary.grant_rate >= 0.6
              ? " Dies entspricht einer überdurchschnittlich hohen Erteilungsquote."
              : data.summary.grant_rate >= 0.3
                ? " Dies liegt im typischen Bereich für Technologiepatente."
                : " Dies deutet auf ein stark umkämpftes Patentumfeld hin."}
          </p>

          {data.summary.avg_time_to_grant_months > 0 && (
            <p>
              Die durchschnittliche Bearbeitungszeit beträgt{" "}
              <strong>{data.summary.avg_time_to_grant_months.toFixed(1)} Monate</strong>
              {data.summary.avg_time_to_grant_months > 48
                ? " — dies ist vergleichsweise lang und kann auf komplexe Prüfungsverfahren hindeuten."
                : data.summary.avg_time_to_grant_months > 24
                  ? " — ein typischer Wert für europäische Patentverfahren."
                  : " — vergleichsweise kurz für Patentverfahren."}
            </p>
          )}

          {data.year_trend.length > 0 && (() => {
            const peakApp = data.year_trend.reduce((b, y) =>
              y.application_count > b.application_count ? y : b, data.year_trend[0]);
            const latest = data.year_trend[data.year_trend.length - 1];
            const earliest = data.year_trend[0];
            return (
              <>
                <p>
                  Das anmeldungsstärkste Jahr war <strong>{peakApp.year}</strong> mit{" "}
                  <strong>{peakApp.application_count.toLocaleString("de-DE")}</strong> Anmeldungen
                  (Quote: {(peakApp.grant_rate * 100).toFixed(1)}%).
                </p>
                {latest.year !== earliest.year && (
                  <p>
                    Im Vergleich: {earliest.year} gab es{" "}
                    <strong>{earliest.application_count.toLocaleString("de-DE")}</strong> Anmeldungen,
                    im Jahr {latest.year} waren es{" "}
                    <strong>{latest.application_count.toLocaleString("de-DE")}</strong>.
                  </p>
                )}
              </>
            );
          })()}
        </div>
      </DetailAnalysisSection>

      {/* ── Vollstaendige Jahrestrend-Tabelle ── */}
      <DetailDataSection title="Erteilungstrend nach Jahr">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wider text-[var(--color-text-muted)]">
                <th className="pb-3 pr-4">Jahr</th>
                <th className="pb-3 pr-4 text-right">Anmeldungen</th>
                <th className="pb-3 pr-4 text-right">Erteilungen</th>
                <th className="pb-3 text-right">Quote</th>
              </tr>
            </thead>
            <tbody>
              {data.year_trend.map((entry) => (
                <tr
                  key={entry.year}
                  className="border-b border-[var(--color-border)]/50 text-[var(--color-text-secondary)]"
                >
                  <td className="py-2 pr-4 font-medium">{entry.year}</td>
                  <td className="py-2 pr-4 text-right">
                    {entry.application_count.toLocaleString("de-DE")}
                  </td>
                  <td className="py-2 pr-4 text-right">
                    {entry.grant_count.toLocaleString("de-DE")}
                  </td>
                  <td className="py-2 text-right font-medium">
                    {(entry.grant_rate * 100).toFixed(1)}%
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
