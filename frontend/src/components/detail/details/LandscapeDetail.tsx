"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v2 -- UC1: Technologie-Landschaft (Detailansicht)
 * Dual-Y-Axes Zeitreihe, Aktivitaetsverteilung,
 * berechnete Insights, vollstaendige CPC-Tabelle
 * ────────────────────────────────────────────── */

import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceArea,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import MetricCard from "@/components/charts/MetricCard";
import DetailChartSection from "@/components/detail/DetailChartSection";
import DetailAnalysisSection from "@/components/detail/DetailAnalysisSection";
import DetailDataSection from "@/components/detail/DetailDataSection";
import { SEMANTIC_COLORS } from "@/lib/chart-colors";
import type { LandscapePanel } from "@/lib/types";

interface LandscapeDetailProps {
  data: LandscapePanel;
  dataCompleteYear?: number;
}

function formatCAGR(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function trendOf(v: number): "up" | "down" | "neutral" {
  return v > 0 ? "up" : v < 0 ? "down" : "neutral";
}

export default function LandscapeDetail({ data, dataCompleteYear }: LandscapeDetailProps) {
  const ts = data.time_series;
  const hasPub = data.total_publications > 0;

  // --- #6: Publikationen CAGR berechnen ---
  const firstPub = ts.find((p) => p.publications > 0);
  const lastPub = [...ts].reverse().find((p) => p.publications > 0);
  const pubCagr =
    firstPub && lastPub && firstPub !== lastPub && firstPub.publications > 0
      ? Math.pow(lastPub.publications / firstPub.publications, 1 / (lastPub.year - firstPub.year)) - 1
      : 0;

  // --- #5: Berechnete Insights ---
  const totalActivity = data.total_patents + data.total_projects + data.total_publications;
  const patShare = totalActivity > 0 ? ((data.total_patents / totalActivity) * 100).toFixed(1) : "0";
  const projShare = totalActivity > 0 ? ((data.total_projects / totalActivity) * 100).toFixed(1) : "0";
  const pubShare = totalActivity > 0 ? ((data.total_publications / totalActivity) * 100).toFixed(1) : "0";
  const peakYear = ts.length > 0
    ? ts.reduce((max, pt) =>
        pt.patents + pt.projects + pt.publications > max.patents + max.projects + max.publications ? pt : max,
        ts[0]
      )
    : null;

  // --- #10: Verteilungs-Donut ---
  const distributionData = [
    { name: "Patente", value: data.total_patents },
    { name: "Projekte", value: data.total_projects },
    ...(hasPub ? [{ name: "Publikationen", value: data.total_publications }] : []),
  ].filter((d) => d.value > 0);
  const distColors = [SEMANTIC_COLORS.patents, SEMANTIC_COLORS.projects, SEMANTIC_COLORS.publications];

  return (
    <div className="flex flex-col gap-6">
      {/* --- #6: Erweiterte Kennzahlen (inkl. Publikationen) --- */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <MetricCard label="Patente gesamt" value={data.total_patents.toLocaleString("de-DE")} />
        <MetricCard label="Projekte gesamt" value={data.total_projects.toLocaleString("de-DE")} />
        {hasPub && (
          <MetricCard label="Publikationen gesamt" value={data.total_publications.toLocaleString("de-DE")} />
        )}
        <MetricCard label="CAGR Patente" value={formatCAGR(data.cagr_patents)} trend={trendOf(data.cagr_patents)} />
        <MetricCard label="CAGR Projekte" value={formatCAGR(data.cagr_projects)} trend={trendOf(data.cagr_projects)} />
        {hasPub && (
          <MetricCard label="CAGR Publikationen" value={formatCAGR(pubCagr)} trend={trendOf(pubCagr)} />
        )}
      </div>

      {/* --- #10: Aktivitaetsverteilung Mini-Donut + #2: Dual-Y-Axes Chart --- */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[200px_1fr]">
        {/* Donut */}
        {distributionData.length > 1 && (
          <div className="flex flex-col items-center justify-center">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
              Verteilung
            </p>
            <ResponsiveContainer width={160} height={160}>
              <PieChart>
                <Pie
                  data={distributionData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={70}
                  paddingAngle={2}
                >
                  {distributionData.map((_, i) => (
                    <Cell key={i} fill={distColors[i]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value: number, name: string) => [
                    value.toLocaleString("de-DE"),
                    name,
                  ]}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="mt-1 flex flex-wrap justify-center gap-x-3 gap-y-1 text-[10px] text-[var(--color-text-muted)]">
              {distributionData.map((d, i) => (
                <span key={d.name} className="flex items-center gap-1">
                  <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: distColors[i] }} />
                  {d.name}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Zeitreihen-Chart mit Dual Y-Axes */}
        <DetailChartSection ariaLabel="Zeitreihe: Patente, Projekte und Publikationen">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={ts} margin={{ top: 20, right: hasPub ? 70 : 30, left: 20, bottom: 20 }}>
              <defs>
                <linearGradient id="detail-gradPatents" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={SEMANTIC_COLORS.patents} stopOpacity={0.15} />
                  <stop offset="95%" stopColor={SEMANTIC_COLORS.patents} stopOpacity={0} />
                </linearGradient>
                <linearGradient id="detail-gradProjects" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={SEMANTIC_COLORS.projects} stopOpacity={0.15} />
                  <stop offset="95%" stopColor={SEMANTIC_COLORS.projects} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis dataKey="year" tick={{ fontSize: 12, fill: "var(--color-text-muted)" }} />

              {/* #2: Linke Y-Achse: Patente + Projekte */}
              <YAxis
                yAxisId="left"
                tick={{ fontSize: 12, fill: "var(--color-text-muted)" }}
                width={60}
                label={{
                  value: "Patente / Projekte",
                  angle: -90,
                  position: "insideLeft",
                  offset: -5,
                  style: { fontSize: 11, fill: "var(--color-text-muted)" },
                }}
              />

              {/* #2: Rechte Y-Achse: Publikationen (wenn vorhanden) */}
              {hasPub && (
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  tick={{ fontSize: 12, fill: "var(--color-text-muted)" }}
                  width={60}
                  label={{
                    value: "Publikationen",
                    angle: 90,
                    position: "insideRight",
                    offset: -5,
                    style: { fontSize: 11, fill: "var(--color-text-muted)" },
                  }}
                />
              )}

              {/* #9: Custom Tooltip mit Absolut + YoY */}
              <Tooltip
                content={({ payload, label }) => {
                  if (!payload || payload.length === 0) return null;
                  const current = ts.find((p) => p.year === label);
                  const prev = ts.find((p) => p.year === (label as number) - 1);
                  if (!current) return null;
                  const yoy = (c: number, p: number) => (p > 0 ? ((c - p) / p) * 100 : null);
                  const row = (lbl: string, val: number, prevVal: number | undefined, color: string) => {
                    const g = prevVal != null ? yoy(val, prevVal) : null;
                    return (
                      <p key={lbl} style={{ color }}>
                        {lbl}: {val.toLocaleString("de-DE")}
                        {g !== null && (
                          <span className={g >= 0 ? "text-green-500" : "text-red-500"}>
                            {" "}({g >= 0 ? "+" : ""}{g.toFixed(1)}%)
                          </span>
                        )}
                      </p>
                    );
                  };
                  return (
                    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-panel)] px-3 py-2 text-xs shadow-lg">
                      <p className="mb-1 font-semibold text-[var(--color-text-primary)]">{label}</p>
                      {row("Patente", current.patents, prev?.patents, SEMANTIC_COLORS.patents)}
                      {row("Projekte", current.projects, prev?.projects, SEMANTIC_COLORS.projects)}
                      {hasPub && row("Publikationen", current.publications, prev?.publications, SEMANTIC_COLORS.publications)}
                    </div>
                  );
                }}
              />

              <Legend
                formatter={(value: string) =>
                  value === "patents" ? "Patente" : value === "publications" ? "Publikationen" : "Projekte"
                }
              />

              {/* #1 + #3: Areas mit tooltipType="none" + Okabe-Ito */}
              <Area yAxisId="left" type="monotone" dataKey="patents" fill="url(#detail-gradPatents)" stroke="none" fillOpacity={1} legendType="none" tooltipType="none" />
              <Area yAxisId="left" type="monotone" dataKey="projects" fill="url(#detail-gradProjects)" stroke="none" fillOpacity={1} legendType="none" tooltipType="none" />
              {hasPub && (
                <Area yAxisId={hasPub ? "right" : "left"} type="monotone" dataKey="publications" fill={SEMANTIC_COLORS.publications} stroke="none" fillOpacity={0.08} legendType="none" tooltipType="none" />
              )}

              {/* Lines */}
              <Line yAxisId="left" type="monotone" dataKey="patents" stroke={SEMANTIC_COLORS.patents} strokeWidth={2} dot={false} activeDot={{ r: 5 }} />
              <Line yAxisId="left" type="monotone" dataKey="projects" stroke={SEMANTIC_COLORS.projects} strokeWidth={2} dot={false} activeDot={{ r: 5 }} />
              {hasPub && (
                <Line yAxisId="right" type="monotone" dataKey="publications" stroke={SEMANTIC_COLORS.publications} strokeWidth={2} dot={false} activeDot={{ r: 5 }} />
              )}

              {/* #4: Datenvollstaendigkeit */}
              {dataCompleteYear && ts.length > 0 && ts[ts.length - 1].year > dataCompleteYear && (
                <ReferenceArea
                  yAxisId="left"
                  x1={dataCompleteYear}
                  x2={ts[ts.length - 1].year}
                  fill="#9ca3af"
                  fillOpacity={0.15}
                  label={{ value: "Daten unvollständig", position: "insideTop", fontSize: 10, fill: "#9ca3af" }}
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </DetailChartSection>
      </div>

      {/* --- #5: Berechnete Analyse-Insights --- */}
      <DetailAnalysisSection>
        <div className="space-y-2 text-sm text-[var(--color-text-secondary)]">
          <p>
            Die Gesamtaktivität verteilt sich auf{" "}
            <strong>{patShare}%</strong> Patente,{" "}
            <strong>{projShare}%</strong> Projekte
            {hasPub && <> und <strong>{pubShare}%</strong> Publikationen</>}.
          </p>
          {peakYear && (
            <p>
              Das aktivste Jahr war <strong>{peakYear.year}</strong> mit{" "}
              {(peakYear.patents + peakYear.projects + peakYear.publications).toLocaleString("de-DE")} Aktivitäten insgesamt.
            </p>
          )}
          <p>
            Der CAGR für Patente beträgt{" "}
            <strong className={data.cagr_patents >= 0 ? "text-[var(--color-chart-growth)]" : "text-[var(--color-chart-decline)]"}>
              {formatCAGR(data.cagr_patents)}
            </strong>
            , für Projekte{" "}
            <strong className={data.cagr_projects >= 0 ? "text-[var(--color-chart-growth)]" : "text-[var(--color-chart-decline)]"}>
              {formatCAGR(data.cagr_projects)}
            </strong>
            {hasPub && (
              <>
                {" "}und für Publikationen{" "}
                <strong className={pubCagr >= 0 ? "text-[var(--color-chart-growth)]" : "text-[var(--color-chart-decline)]"}>
                  {formatCAGR(pubCagr)}
                </strong>
              </>
            )}.
          </p>
        </div>
      </DetailAnalysisSection>

      {/* --- #7: Vollstaendige Zeitreihen-Tabelle --- */}
      <DetailDataSection title="Zeitreihe (vollständig)">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wider text-[var(--color-text-muted)]">
                <th className="px-3 py-2">Jahr</th>
                <th className="px-3 py-2 text-right">Patente</th>
                <th className="px-3 py-2 text-right">Projekte</th>
                {hasPub && <th className="px-3 py-2 text-right">Publikationen</th>}
              </tr>
            </thead>
            <tbody>
              {ts.map((pt) => (
                <tr key={pt.year} className="border-b border-[var(--color-border)] last:border-0">
                  <td className="px-3 py-2 font-medium text-[var(--color-text-primary)]">{pt.year}</td>
                  <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                    {pt.patents.toLocaleString("de-DE")}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                    {pt.projects.toLocaleString("de-DE")}
                  </td>
                  {hasPub && (
                    <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                      {pt.publications.toLocaleString("de-DE")}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DetailDataSection>

      {/* --- #8: CPC-Klassen (mit verbessertem Empty State) --- */}
      {data.top_cpc_codes.length > 0 ? (
        <DetailDataSection title="CPC-Klassen (vollständig)">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wider text-[var(--color-text-muted)]">
                  <th className="px-3 py-2">Code</th>
                  <th className="px-3 py-2">Bezeichnung</th>
                  <th className="px-3 py-2 text-right">Anzahl</th>
                </tr>
              </thead>
              <tbody>
                {data.top_cpc_codes.map((cpc) => (
                  <tr key={cpc.code} className="border-b border-[var(--color-border)] last:border-0">
                    <td className="px-3 py-2 font-mono text-[var(--color-text-secondary)]">{cpc.code}</td>
                    <td className="px-3 py-2 text-[var(--color-text-secondary)]">{cpc.label}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                      {cpc.count.toLocaleString("de-DE")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </DetailDataSection>
      ) : (
        <DetailDataSection title="CPC-Klassen">
          <p className="text-sm text-[var(--color-text-muted)]">
            CPC-Klassifikationsdaten werden aus EPO-Patentdaten gewonnen.
            Sobald der EPO-Datenimport und das CPC-Enrichment für diese Technologie
            abgeschlossen sind, erscheinen hier die zugehörigen CPC-Klassen mit Häufigkeiten.
          </p>
        </DetailDataSection>
      )}
    </div>
  );
}
