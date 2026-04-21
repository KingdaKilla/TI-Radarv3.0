"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- UC13: Publikations-Impact (Detailansicht)
 * Publication trend bar chart + top projects horizontal bar
 * + full publications table + auto-generated analysis
 * ────────────────────────────────────────────── */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceArea,
} from "recharts";
import MetricCard from "@/components/charts/MetricCard";
import DetailChartSection from "@/components/detail/DetailChartSection";
import DetailAnalysisSection from "@/components/detail/DetailAnalysisSection";
import DetailDataSection from "@/components/detail/DetailDataSection";
import { CHART_COLORS, SEMANTIC_COLORS } from "@/lib/chart-colors";
import type { PublicationPanel } from "@/lib/types";

interface PublicationDetailProps {
  data: PublicationPanel;
}

export default function PublicationDetail({ data }: PublicationDetailProps) {
  const dataCompleteYear = 2025; // CORDIS-Publikationen 2026 noch unvollstaendig

  /* ── Chart data: publication trend ── */
  const trendData = data.pub_trend.map((entry) => ({
    ...entry,
  }));

  /* ── Chart data: top projects by pub efficiency ── */
  const projectData = data.top_projects.map((p) => ({
    ...p,
    label: p.project_acronym,
  }));

  /* Dynamische Hoehe: min 400px, 40px pro Projekt */
  const projectChartHeight = Math.max(400, projectData.length * 40);

  return (
    <div className="flex flex-col gap-6">
      {/* ── Kennzahlen ── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MetricCard
          label="Publikationen gesamt"
          value={data.total_publications.toLocaleString("de-DE")}
        />
        <MetricCard
          label="Projekte mit Publikationen"
          value={data.total_projects_with_pubs.toLocaleString("de-DE")}
        />
        <MetricCard
          label="Publikationen / Projekt"
          value={data.publications_per_project.toFixed(1)}
        />
        <MetricCard
          label="DOI-Abdeckung"
          value={`${(data.doi_coverage * 100).toFixed(1)}%`}
        />
      </div>

      {/* ── Publikationstrend (BarChart) ── */}
      {trendData.length > 0 && (
        <DetailChartSection ariaLabel="Publikationstrend über Zeit">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={trendData}
              margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
            >
              <defs>
                <linearGradient id="detail-pubTrend" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={SEMANTIC_COLORS.publications} stopOpacity={0.8} />
                  <stop offset="95%" stopColor={SEMANTIC_COLORS.publications} stopOpacity={0.3} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis
                dataKey="year"
                tick={{ fontSize: 12, fill: "var(--color-text-muted)" }}
              />
              <YAxis
                tick={{ fontSize: 12, fill: "var(--color-text-muted)" }}
                width={55}
                label={{
                  value: "Publikationen",
                  angle: -90,
                  position: "insideLeft",
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
                formatter={(value, name) => {
                  const v = typeof value === "number" ? value.toLocaleString("de-DE") : String(value ?? "–");
                  if (name === "publication_count") return [v, "Publikationen"];
                  if (name === "project_count") return [v, "Projekte"];
                  return [v, name];
                }}
              />
              <Bar
                dataKey="publication_count"
                fill="url(#detail-pubTrend)"
                radius={[3, 3, 0, 0]}
                barSize={20}
              />
              {dataCompleteYear && trendData.length > 0 && trendData[trendData.length - 1].year > dataCompleteYear && (
                <ReferenceArea
                  x1={dataCompleteYear}
                  x2={trendData[trendData.length - 1].year}
                  fill="var(--color-text-muted)"
                  fillOpacity={0.08}
                  label={{ value: "Daten ggf. unvollständig", fontSize: 10, fill: "var(--color-text-muted)", position: "insideTop" }}
                />
              )}
            </BarChart>
          </ResponsiveContainer>
        </DetailChartSection>
      )}

      {/* ── Top-Projekte nach Pub-Effizienz (horizontal BarChart) ── */}
      {projectData.length > 0 && (
        <DetailChartSection
          ariaLabel="Top-Projekte nach Publikationseffizienz"
          heightPx={projectChartHeight}
        >
          <ResponsiveContainer width="100%" height={projectChartHeight}>
            <BarChart
              data={projectData}
              layout="vertical"
              margin={{ top: 10, right: 30, left: 10, bottom: 10 }}
            >
              <defs>
                <linearGradient id="detail-pubEfficiency" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="5%" stopColor={CHART_COLORS.green} stopOpacity={0.9} />
                  <stop offset="95%" stopColor={CHART_COLORS.green} stopOpacity={0.6} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis
                type="number"
                tick={{ fontSize: 12, fill: "var(--color-text-muted)" }}
                label={{
                  value: "Pub. / Mio. EUR",
                  position: "insideBottom",
                  offset: -5,
                  style: { fontSize: 12, fill: "var(--color-text-muted)" },
                }}
              />
              <YAxis
                dataKey="label"
                type="category"
                width={120}
                tick={{ fontSize: 11, fill: "var(--color-text-secondary)" }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--color-bg-panel)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "8px",
                  fontSize: "13px",
                }}
                formatter={(value, name) => {
                  if (name === "publications_per_million_eur")
                    return [typeof value === "number" ? value.toFixed(1) : String(value ?? "–"), "Pub. / Mio. EUR"];
                  return [typeof value === "number" ? value.toLocaleString("de-DE") : String(value ?? "–"), name];
                }}
              />
              <Bar
                dataKey="publications_per_million_eur"
                fill="url(#detail-pubEfficiency)"
                radius={[0, 4, 4, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </DetailChartSection>
      )}

      {/* ── Top-Publikationen Tabelle ── */}
      <DetailDataSection title="Top-Publikationen">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wider text-[var(--color-text-muted)]">
                <th className="pb-3 pr-4">Titel</th>
                <th className="pb-3 pr-4">DOI</th>
                <th className="pb-3 pr-4">Journal</th>
                <th className="pb-3 pr-4 text-right">Jahr</th>
                <th className="pb-3">Projekt</th>
              </tr>
            </thead>
            <tbody>
              {data.top_publications.map((pub, idx) => (
                <tr
                  key={`${pub.doi || idx}`}
                  className="border-b border-[var(--color-border)]/50 text-[var(--color-text-secondary)]"
                >
                  <td className="py-2 pr-4 font-medium max-w-[300px] truncate" title={pub.title}>
                    {pub.title}
                  </td>
                  <td className="py-2 pr-4 text-xs">
                    {pub.doi ? (
                      <a
                        href={`https://doi.org/${pub.doi}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:underline" style={{ color: SEMANTIC_COLORS.publications }}
                      >
                        {pub.doi}
                      </a>
                    ) : (
                      <span className="text-[var(--color-text-muted)]">—</span>
                    )}
                  </td>
                  <td className="py-2 pr-4 text-xs">{pub.journal || "—"}</td>
                  <td className="py-2 pr-4 text-right">{pub.publication_year}</td>
                  <td className="py-2 font-medium">{pub.project_acronym}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DetailDataSection>
    </div>
  );
}
