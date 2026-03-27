"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v2 -- UC7: Forschungsimpact (Detailansicht)
 * 5 Sektionen: MetricCards, Zitations-Trend, Auto-Analyse,
 * Top Journals-Tabelle
 * ────────────────────────────────────────────── */

import { useMemo } from "react";
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceArea,
} from "recharts";
import MetricCard from "@/components/charts/MetricCard";
import DetailChartSection from "@/components/detail/DetailChartSection";
import DetailAnalysisSection from "@/components/detail/DetailAnalysisSection";
import DetailDataSection from "@/components/detail/DetailDataSection";
import { CHART_COLORS } from "@/lib/chart-colors";
import type { ResearchImpactPanel } from "@/lib/types";

interface ResearchImpactDetailProps {
  data: ResearchImpactPanel;
}

export default function ResearchImpactDetail({ data }: ResearchImpactDetailProps) {
  const ct = data.citation_trend;

  /* Aggregationen */
  const totalCitations = ct.reduce((s, pt) => s + pt.total_citations, 0);
  const hIndex = data.top_institutions.length > 0 ? data.top_institutions[0].h_index : 0;

  /* Peak-Jahr */
  const peakYear = ct.length > 0
    ? ct.reduce((best, pt) => (pt.total_citations > best.total_citations ? pt : best), ct[0])
    : null;

  /* Top-Institution */
  const topInstitution = data.top_institutions.length > 0
    ? data.top_institutions[0]
    : null;

  /* Datenvollständigkeit: Semantic Scholar hat 2024 vollständig (Stand 2026) */
  const dataCompleteYear = 2025;
  const lastYear = ct.length > 0 ? ct[ct.length - 1].year : 0;

  /* Lookup-Map für Tooltip */
  const ctByYear = useMemo(
    () => new Map(ct.map((p) => [p.year, p])),
    [ct],
  );

  return (
    <div className="flex flex-col gap-6">
      {/* ── Sektion 1: Kennzahlen ── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <MetricCard
          label="Publikationen"
          value={data.total_papers.toLocaleString("de-DE")}
        />
        <MetricCard
          label="Zitationen gesamt"
          value={totalCitations.toLocaleString("de-DE")}
        />
        <MetricCard
          label="Ø Zitate / Paper"
          value={data.avg_citations.toFixed(1)}
        />
        {hIndex > 0 && (
          <MetricCard
            label="h-Index"
            value={hIndex}
          />
        )}
        <MetricCard
          label="Institutionen"
          value={data.top_institutions.length}
        />
        {data.collaboration_rate > 0 && (
          <MetricCard
            label="Kollaborationsrate"
            value={`${(data.collaboration_rate * 100).toFixed(1)}%`}
          />
        )}
      </div>

      {/* ── Sektion 2: Zitations-Trend ── */}
      {ct.length > 0 && (
        <DetailChartSection ariaLabel="Zitations-Trend: Publikationen und Zitationen pro Jahr">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={ct}
              margin={{ top: 20, right: 60, left: 20, bottom: 20 }}
            >
              <defs>
                <linearGradient id="detail-researchBar" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={CHART_COLORS.blue} stopOpacity={0.8} />
                  <stop offset="95%" stopColor={CHART_COLORS.blue} stopOpacity={0.3} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis
                dataKey="year"
                tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
                tickLine={false}
              />
              <YAxis
                yAxisId="left"
                tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
                width={50}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
                width={60}
              />

              <Tooltip
                content={({ payload, label }) => {
                  if (!payload?.length) return null;
                  const yearNum = Number(label);
                  const pt = ctByYear.get(yearNum);
                  const prev = ctByYear.get(yearNum - 1);
                  const yoyCit =
                    prev && prev.total_citations > 0 && pt
                      ? ((pt.total_citations - prev.total_citations) / prev.total_citations) * 100
                      : null;

                  return (
                    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-panel)] px-3 py-2 text-xs shadow-lg">
                      <p className="mb-1 font-semibold text-[var(--color-text-primary)]">{yearNum}</p>
                      <p style={{ color: CHART_COLORS.blue }}>
                        Publikationen: {(pt?.publication_count ?? 0).toLocaleString("de-DE")}
                      </p>
                      <p style={{ color: CHART_COLORS.orange }}>
                        Zitationen: {(pt?.total_citations ?? 0).toLocaleString("de-DE")}
                        {yoyCit !== null && (
                          <span className={yoyCit >= 0 ? "ml-1 text-[var(--color-chart-growth)]" : "ml-1 text-[var(--color-chart-decline)]"}>
                            {yoyCit >= 0 ? "+" : ""}{yoyCit.toFixed(1)}%
                          </span>
                        )}
                      </p>
                    </div>
                  );
                }}
              />

              <Legend
                formatter={(value: string) => {
                  const labels: Record<string, string> = {
                    publication_count: "Publikationen",
                    total_citations: "Zitationen",
                  };
                  return labels[value] ?? value;
                }}
              />

              <Bar
                yAxisId="left"
                dataKey="publication_count"
                fill="url(#detail-researchBar)"
                radius={[4, 4, 0, 0]}
                name="publication_count"
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="total_citations"
                stroke={CHART_COLORS.orange}
                strokeWidth={2.5}
                dot={{ r: 3, fill: CHART_COLORS.orange }}
                name="total_citations"
              />

              {lastYear > dataCompleteYear && (
                <ReferenceArea
                  x1={dataCompleteYear}
                  x2={lastYear}
                  fill="#9ca3af"
                  fillOpacity={0.15}
                  label={{ value: "unvollst.", fontSize: 10, fill: "#9ca3af" }}
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </DetailChartSection>
      )}

      {/* ── Sektion 3: Auto-Analyse ── */}
      <DetailAnalysisSection>
        <div className="space-y-2 text-sm text-[var(--color-text-secondary)]">
          <p>
            Für diese Technologie wurden <strong>{data.total_papers.toLocaleString("de-DE")}</strong> Publikationen
            mit insgesamt <strong>{totalCitations.toLocaleString("de-DE")}</strong> Zitationen identifiziert
            (Ø <strong>{data.avg_citations.toFixed(1)}</strong> Zitate pro Paper).
            {hIndex > 0 && (
              <> Der h-Index beträgt <strong>{hIndex}</strong> — d.h. mindestens {hIndex} Publikationen
              wurden jeweils mindestens {hIndex}-mal zitiert (Hirsch 2005).</>
            )}
          </p>

          {topInstitution && (
            <p>
              Die fuehrende Institution ist <strong>{topInstitution.institution}</strong> mit{" "}
              <strong>{topInstitution.paper_count}</strong> EU-Projektbeteiligungen.
              {data.top_institutions.length > 1 && (
                <> Insgesamt sind <strong>{data.top_institutions.length}</strong> Institutionen in EU-Forschungsprojekten zu diesem Thema aktiv.</>
              )}
            </p>
          )}

          {peakYear && (
            <p>
              Das zitationsstärkste Jahr war <strong>{peakYear.year}</strong> mit{" "}
              <strong>{peakYear.total_citations.toLocaleString("de-DE")}</strong> Zitationen
              und <strong>{peakYear.publication_count.toLocaleString("de-DE")}</strong> Publikationen.
            </p>
          )}

          <p className="text-xs text-[var(--color-text-muted)]">
            Datenquellen: Semantic Scholar Academic Graph (Publikationen, Zitationen),
            CORDIS EU Research Projects (Institutionen). Der h-Index nach Hirsch (2005)
            misst die Forschungsproduktivitaet und den Zitationseinfluss eines Themenfeldes.
          </p>
        </div>
      </DetailAnalysisSection>

      {/* ── Sektion 4: Top Institutionen-Tabelle ── */}
      {data.top_institutions.length > 0 && (
      <DetailDataSection title="Top Forschungsinstitutionen (CORDIS)">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wider text-[var(--color-text-muted)]">
                <th className="px-3 py-2 w-8">#</th>
                <th className="px-3 py-2">Institution</th>
                <th className="px-3 py-2 text-right">Projekte</th>
              </tr>
            </thead>
            <tbody>
              {data.top_institutions.map((inst, idx) => (
                <tr
                  key={`${inst.institution}-${idx}`}
                  className="border-b border-[var(--color-border)] last:border-0"
                >
                  <td className="px-3 py-2 tabular-nums text-[var(--color-text-muted)]">
                    {idx + 1}
                  </td>
                  <td className="px-3 py-2 font-medium text-[var(--color-text-secondary)]">
                    {inst.institution}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                    {inst.paper_count.toLocaleString("de-DE")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DetailDataSection>
      )}
    </div>
  );
}
