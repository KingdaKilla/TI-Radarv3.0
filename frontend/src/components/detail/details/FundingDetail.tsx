"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v2 -- UC4: Förderungsanalyse (Detailansicht)
 * 6 Sektionen: MetricCards, Treemap, Förder-Trend-Chart,
 * Auto-Analyse, Top-Organisationen, Programm-Tabelle
 * ────────────────────────────────────────────── */

import { useMemo } from "react";
import {
  ComposedChart,
  Area,
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
import FundingTreemap from "@/components/charts/FundingTreemap";
import { CHART_COLORS } from "@/lib/chart-colors";
import { getCountryName } from "@/lib/countries";
import type { FundingPanel } from "@/lib/types";

interface FundingDetailProps {
  data: FundingPanel;
}

/* ── Konstanten ── */

const PROGRAM_DESCRIPTIONS: Record<string, string> = {
  "RIA": "Research & Innovation Action — Grundlagenforschung und angewandte Forschung",
  "IA": "Innovation Action — Marktnahe Entwicklung und Demonstration",
  "CSA": "Coordination & Support — Vernetzung und Kapazitätsaufbau",
  "ERC-STG": "ERC Starting Grant — Junge exzellente Forscher",
  "ERC-COG": "ERC Consolidator Grant — Etablierte Forscher",
  "ERC-ADG": "ERC Advanced Grant — Führende Forscher",
  "MSCA-DN": "Doktorandennetzwerke — Strukturierte Promotionsprogramme",
  "MSCA-PF": "Postdoctoral Fellowships — Individuelle Mobilitätsstipendien",
  "EIC-PATHFINDER": "Visionäre Forschung für bahnbrechende Technologien",
  "EIC-TRANSITION": "Überführung von Forschungsergebnissen in Innovation",
  "EIC-ACCELERATOR": "Skalierung von Deep-Tech Start-ups und KMU",
  "INFRAEOSC": "Europäische Open Science Cloud Infrastruktur",
  "DIGITAL-SIMPLE": "Digitale Infrastruktur und Technologien",
};

const ORG_TYPE_LABELS: Record<string, string> = {
  HES: "Hochschule",
  PRC: "Unternehmen",
  REC: "Forschung",
  PUB: "Behörde",
  OTH: "Sonstige",
};

/* ── Hilfsfunktionen ── */

function getProgramDescription(program: string): string {
  if (PROGRAM_DESCRIPTIONS[program]) return PROGRAM_DESCRIPTIONS[program];
  for (const [key, desc] of Object.entries(PROGRAM_DESCRIPTIONS)) {
    if (program.toUpperCase().includes(key)) return desc;
  }
  return "";
}

function formatCurrency(value: number): string {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)} Mrd. EUR`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)} Mio. EUR`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)} Tsd. EUR`;
  return `${value.toFixed(0)} EUR`;
}

function formatCurrencyShort(value: number): string {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)} Mrd.`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)} Mio.`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)} Tsd.`;
  return value.toFixed(0);
}

function formatCAGR(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function trendOf(v: number): "up" | "down" | "neutral" {
  return v > 0 ? "up" : v < 0 ? "down" : "neutral";
}

/* ── Komponente ── */

export default function FundingDetail({ data }: FundingDetailProps) {
  const dataCompleteYear = 2024;

  const avgPerProject =
    data.total_projects > 0 ? data.total_funding / data.total_projects : 0;

  const ts = data.funding_trend;
  const hasTrend = ts.length > 1;

  /* Lookup-Map für Tooltip (vermeidet O(n)-Suche bei jedem Mouse-Move) */
  const tsByYear = useMemo(
    () => new Map(ts.map((p) => [p.year, p])),
    [ts],
  );

  /* Peak-Jahr ermitteln */
  const peakYear = ts.length > 0
    ? ts.reduce((best, pt) => (pt.funding_eur > best.funding_eur ? pt : best), ts[0])
    : null;

  /* Top-Instrument ermitteln */
  const topProgram = data.by_program.length > 0
    ? data.by_program.reduce((best, p) => (p.total_funding > best.total_funding ? p : best), data.by_program[0])
    : null;

  /* Spalten-Sichtbarkeit für Org-Tabelle */
  const hasOrgCountry = data.top_organisations.some((o) => o.country_code);
  const hasOrgType = data.top_organisations.some((o) => o.organisation_type);

  return (
    <div className="flex flex-col gap-6">
      {/* ── Sektion 1: Kennzahlen ── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <MetricCard
          label="Förderung gesamt"
          value={formatCurrency(data.total_funding)}
        />
        <MetricCard
          label="Projekte gesamt"
          value={data.total_projects.toLocaleString("de-DE")}
        />
        <MetricCard
          label="Durchschnitt / Projekt"
          value={formatCurrency(avgPerProject)}
        />
        <MetricCard
          label="CAGR Förderung"
          value={formatCAGR(data.cagr)}
          trend={trendOf(data.cagr)}
        />
        <MetricCard
          label="Programme"
          value={data.by_program.length}
        />
        {data.avg_duration_months > 0 && (
          <MetricCard
            label="Ø Projektdauer"
            value={`${data.avg_duration_months.toFixed(1)} Mon.`}
          />
        )}
      </div>

      {/* ── Sektion 2: Treemap (Instrumente) ── */}
      <DetailChartSection ariaLabel="Förderung nach Instrument (Treemap)">
        <FundingTreemap data={data.by_program} />
      </DetailChartSection>

      {/* ── Sektion 3: Förder-Trend (ComposedChart) ── */}
      {hasTrend && (
        <DetailChartSection
          ariaLabel="Zeitreihe: Fördervolumen und Projektanzahl"
          heightPx={360}
        >
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={ts} margin={{ top: 20, right: 70, left: 20, bottom: 20 }}>
              <defs>
                <linearGradient id="detail-gradFunding" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={CHART_COLORS.green} stopOpacity={0.25} />
                  <stop offset="100%" stopColor={CHART_COLORS.green} stopOpacity={0.02} />
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
                tickFormatter={(v: number) => formatCurrencyShort(v)}
                width={70}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
                tickFormatter={(v: number) => v.toLocaleString("de-DE")}
                width={50}
              />

              <Tooltip
                content={({ payload, label }) => {
                  if (!payload?.length) return null;
                  const yearNum = Number(label);
                  const pt = tsByYear.get(yearNum);
                  const prev = tsByYear.get(yearNum - 1);
                  const yoyFunding =
                    prev && prev.funding_eur > 0 && pt
                      ? ((pt.funding_eur - prev.funding_eur) / prev.funding_eur) * 100
                      : null;

                  return (
                    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-panel)] px-3 py-2 text-xs shadow-lg">
                      <p className="mb-1 font-semibold text-[var(--color-text-primary)]">{yearNum}</p>
                      <p style={{ color: CHART_COLORS.green }}>
                        Förderung: {formatCurrency(pt?.funding_eur ?? 0)}
                        {yoyFunding !== null && (
                          <span className={yoyFunding >= 0 ? "ml-1 text-[var(--color-chart-growth)]" : "ml-1 text-[var(--color-chart-decline)]"}>
                            {yoyFunding >= 0 ? "+" : ""}{yoyFunding.toFixed(1)}%
                          </span>
                        )}
                      </p>
                      <p style={{ color: CHART_COLORS.orange }}>
                        Projekte: {(pt?.project_count ?? 0).toLocaleString("de-DE")}
                      </p>
                      {(pt?.participant_count ?? 0) > 0 && (
                        <p className="text-[var(--color-text-muted)]">
                          Organisationen: {pt!.participant_count.toLocaleString("de-DE")}
                        </p>
                      )}
                    </div>
                  );
                }}
              />

              <Legend
                formatter={(value: string) => {
                  const labels: Record<string, string> = {
                    funding_eur: "Fördervolumen (EUR)",
                    project_count: "Projekte",
                  };
                  return labels[value] ?? value;
                }}
              />

              <Area
                yAxisId="left"
                type="monotone"
                dataKey="funding_eur"
                fill="url(#detail-gradFunding)"
                stroke={CHART_COLORS.green}
                strokeWidth={2}
                dot={false}
                name="funding_eur"
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="project_count"
                stroke={CHART_COLORS.orange}
                strokeWidth={2}
                dot={{ r: 3 }}
                name="project_count"
              />
              {dataCompleteYear && ts.length > 0 && ts[ts.length - 1].year > dataCompleteYear && (
                <ReferenceArea
                  yAxisId="left"
                  x1={dataCompleteYear}
                  x2={ts[ts.length - 1].year}
                  fill="var(--color-text-muted)"
                  fillOpacity={0.08}
                  label={{ value: "Daten ggf. unvollständig", fontSize: 10, fill: "var(--color-text-muted)", position: "insideTop" }}
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </DetailChartSection>
      )}

      {/* ── Sektion 4: Auto-Analyse ── */}
      <DetailAnalysisSection>
        <div className="space-y-2 text-sm text-[var(--color-text-secondary)]">
          <p>
            Insgesamt wurden <strong>{formatCurrency(data.total_funding)}</strong> für{" "}
            <strong>{data.total_projects.toLocaleString("de-DE")}</strong> Projekte bewilligt
            (Ø <strong>{formatCurrency(avgPerProject)}</strong> pro Projekt).
            {data.avg_duration_months > 0 && (
              <> Die durchschnittliche Projektdauer beträgt <strong>{data.avg_duration_months.toFixed(1)} Monate</strong>.</>
            )}
          </p>

          {topProgram && (
            <p>
              Das dominierende Förderinstrument ist <strong>{topProgram.program}</strong> mit{" "}
              <strong>{formatCurrency(topProgram.total_funding)}</strong> ({(topProgram.share * 100).toFixed(1)}% Anteil)
              und <strong>{topProgram.project_count.toLocaleString("de-DE")}</strong> Projekten.
              {data.by_program.length > 1 && (
                <> Insgesamt verteilt sich die Förderung auf <strong>{data.by_program.length}</strong> Instrumente.</>
              )}
            </p>
          )}

          {data.cagr !== 0 && (
            <p>
              Die jährliche Wachstumsrate (CAGR) der Förderung beträgt{" "}
              <strong className={data.cagr >= 0 ? "text-[var(--color-chart-growth)]" : "text-[var(--color-chart-decline)]"}>
                {formatCAGR(data.cagr)}
              </strong>
              {data.cagr > 0
                ? " — ein wachsendes Investitionsinteresse der EU."
                : " — eine rückläufige Förderentwicklung."}
            </p>
          )}

          {peakYear && (
            <p>
              Das stärkste Förderjahr war <strong>{peakYear.year}</strong> mit{" "}
              <strong>{formatCurrency(peakYear.funding_eur)}</strong>
              {peakYear.participant_count > 0 && (
                <> und <strong>{peakYear.participant_count.toLocaleString("de-DE")}</strong> beteiligten Organisationen</>
              )}.
            </p>
          )}
        </div>
      </DetailAnalysisSection>

      {/* ── Sektion 5: Top-Organisationen ── */}
      {data.top_organisations.length > 0 && (
        <DetailDataSection title="Top-Förderempfänger">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wider text-[var(--color-text-muted)]">
                  <th className="px-3 py-2 w-8">#</th>
                  <th className="px-3 py-2">Organisation</th>
                  {hasOrgCountry && <th className="px-3 py-2">Land</th>}
                  {hasOrgType && <th className="px-3 py-2">Typ</th>}
                  <th className="px-3 py-2 text-right">Förderung</th>
                  <th className="px-3 py-2 text-right">Projekte</th>
                </tr>
              </thead>
              <tbody>
                {data.top_organisations.map((org, idx) => (
                  <tr
                    key={`${org.name}-${idx}`}
                    className="border-b border-[var(--color-border)] last:border-0"
                  >
                    <td className="px-3 py-2 text-[var(--color-text-muted)]">{idx + 1}</td>
                    <td className="px-3 py-2 font-medium text-[var(--color-text-primary)]">
                      {org.name.length > 50 ? org.name.slice(0, 47) + "\u2026" : org.name}
                    </td>
                    {hasOrgCountry && (
                      <td className="px-3 py-2 text-[var(--color-text-muted)]">
                        {getCountryName(org.country_code)}
                      </td>
                    )}
                    {hasOrgType && (
                      <td className="px-3 py-2 text-[var(--color-text-muted)]">
                        {ORG_TYPE_LABELS[org.organisation_type] ?? org.organisation_type}
                      </td>
                    )}
                    <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                      {formatCurrencyShort(org.funding_eur)} EUR
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                      {org.project_count.toLocaleString("de-DE")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </DetailDataSection>
      )}

      {/* ── Sektion 6: Vollständige Programm-Tabelle ── */}
      <DetailDataSection title="Förderinstrumente (vollständig)">
        {data.by_program.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wider text-[var(--color-text-muted)]">
                  <th className="px-3 py-2">Instrument</th>
                  <th className="px-3 py-2">Beschreibung</th>
                  <th className="px-3 py-2 text-right">Förderung</th>
                  <th className="px-3 py-2 text-right">Anteil</th>
                  <th className="px-3 py-2 text-right">Projekte</th>
                  <th className="px-3 py-2 text-right">Ø / Projekt</th>
                </tr>
              </thead>
              <tbody>
                {data.by_program.map((entry, idx) => (
                  <tr
                    key={`${entry.program}-${idx}`}
                    className="border-b border-[var(--color-border)] last:border-0"
                  >
                    <td className="px-3 py-2 font-medium text-[var(--color-text-secondary)]">
                      {entry.program}
                    </td>
                    <td className="px-3 py-2 text-xs text-[var(--color-text-muted)]">
                      {getProgramDescription(entry.program)}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                      {formatCurrencyShort(entry.total_funding)} EUR
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                      {(entry.share * 100).toFixed(1)}%
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                      {entry.project_count.toLocaleString("de-DE")}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                      {formatCurrencyShort(entry.avg_funding)} EUR
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t-2 border-[var(--color-border)] font-semibold">
                  <td className="px-3 py-2 text-[var(--color-text-primary)]">Gesamt</td>
                  <td className="px-3 py-2" />
                  <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-primary)]">
                    {formatCurrencyShort(data.total_funding)} EUR
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-primary)]">
                    100%
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-primary)]">
                    {data.total_projects.toLocaleString("de-DE")}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-primary)]">
                    {formatCurrencyShort(avgPerProject)} EUR
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        ) : (
          <p className="text-sm italic text-[var(--color-text-muted)]">
            Keine Förderdaten vorhanden.
          </p>
        )}
      </DetailDataSection>
    </div>
  );
}
