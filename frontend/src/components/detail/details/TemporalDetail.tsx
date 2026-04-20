"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- UC8: Zeitliche Entwicklung (Detailansicht)
 * Enlarged actor dynamics chart + topic lists
 * ────────────────────────────────────────────── */

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceArea,
} from "recharts";
import { TrendingUp, TrendingDown } from "lucide-react";
import MetricCard from "@/components/charts/MetricCard";
import DetailChartSection from "@/components/detail/DetailChartSection";
import DetailAnalysisSection from "@/components/detail/DetailAnalysisSection";
import DetailDataSection from "@/components/detail/DetailDataSection";
import { CHART_COLORS } from "@/lib/chart-colors";
import type { TemporalPanel } from "@/lib/types";

interface TemporalDetailProps {
  data: TemporalPanel;
}

export default function TemporalDetail({ data }: TemporalDetailProps) {
  const dataCompleteYear = 2024; // CORDIS-Daten 2025 noch ~90% vollständig

  const sortedTrend = [...data.entrant_trend].sort((a, b) => a.year - b.year);

  const latestYear =
    sortedTrend.length > 0
      ? sortedTrend[sortedTrend.length - 1]
      : null;

  // Bug v3.4.9/N3: Die Detail-Net-Berechnung summierte new/exited über ALLE
  // Jahre inklusive des laufenden Rumpfjahres (2026). Dort ist exited_actors
  // typischerweise sehr groß (alle Akteure die nicht mehr auftauchen in den
  // unvollständigen Daten), wodurch Net fälschlich negativ wurde → Text
  // "schrumpfende Akteurslandschaft" trotz offensichtlich wachsendem
  // Gesamtverlauf. Analog zum Panel-Fix in v3.4.7: nur vollständige Jahre
  // (year <= dataCompleteYear) für die Net-Aussage nutzen; das Chart selbst
  // zeigt weiterhin alle Jahre inkl. Rumpfjahr.
  const completeYears = sortedTrend.filter((p) => p.year <= dataCompleteYear);
  const summaryBasis = completeYears.length > 0 ? completeYears : sortedTrend;
  const startYear = summaryBasis.length > 0 ? summaryBasis[0].year : null;
  const endYear = summaryBasis.length > 0 ? summaryBasis[summaryBasis.length - 1].year : null;
  const totalNew = summaryBasis.reduce((s, p) => s + p.new_entrants, 0);
  const totalExited = summaryBasis.reduce((s, p) => s + p.exited_actors, 0);
  const net = totalNew - totalExited;

  return (
    <div className="flex flex-col gap-6">
      {/* ── Kennzahlen ──
          Bug v3.4.10/α-F: "Aufkommende Themen" + "Abnehmende Themen" +
          "Themen-Cluster" wurden entfernt, weil das Backend sie nicht
          konsistent befüllt (Topic-Modeling-Job existiert nur als Plan).
          Aktuelle Metriken beschränken sich auf die Akteurs-Dynamik, die
          belastbare Datenbasis hat. */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <MetricCard
          label="Aktive Akteure (letztes Jahr)"
          value={latestYear ? latestYear.total_active.toLocaleString("de-DE") : "–"}
        />
        {startYear !== null && endYear !== null && (
          <MetricCard
            label={`Neu eingestiegen ${startYear}–${endYear}`}
            value={totalNew.toLocaleString("de-DE")}
            trend="up"
          />
        )}
        {startYear !== null && endYear !== null && (
          <MetricCard
            label={`Ausgeschieden ${startYear}–${endYear}`}
            value={totalExited.toLocaleString("de-DE")}
            trend="down"
          />
        )}
      </div>

      {/* ── Akteur-Dynamik (vergroessert) ── */}
      {data.entrant_trend.length > 0 && (
        <DetailChartSection ariaLabel="Akteur-Dynamik: Neue, persistente und ausgeschiedene Akteure pro Jahr">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={data.entrant_trend}
              margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
            >
              <defs>
                <linearGradient id="detail-temporalPersistent" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={CHART_COLORS.blue} stopOpacity={0.6} />
                  <stop offset="95%" stopColor={CHART_COLORS.blue} stopOpacity={0.1} />
                </linearGradient>
                <linearGradient id="detail-temporalNew" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={CHART_COLORS.orange} stopOpacity={0.6} />
                  <stop offset="95%" stopColor={CHART_COLORS.orange} stopOpacity={0.1} />
                </linearGradient>
                <linearGradient id="detail-temporalExited" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={CHART_COLORS.vermillion} stopOpacity={0.4} />
                  <stop offset="95%" stopColor={CHART_COLORS.vermillion} stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis
                dataKey="year"
                tick={{ fontSize: 12, fill: "var(--color-text-muted)" }}
              />
              <YAxis
                tick={{ fontSize: 12, fill: "var(--color-text-muted)" }}
                width={50}
                label={{
                  value: "Akteure",
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
                formatter={(value: number, name: string) => {
                  const labels: Record<string, string> = {
                    new_entrants: "Neue Akteure",
                    persistent_actors: "Persistente",
                    exited_actors: "Ausgeschieden",
                  };
                  return [value.toLocaleString("de-DE"), labels[name] ?? name];
                }}
              />
              <Legend
                wrapperStyle={{ fontSize: "13px" }}
                formatter={(value: string) => {
                  const labels: Record<string, string> = {
                    new_entrants: "Neue Akteure",
                    persistent_actors: "Persistente",
                    exited_actors: "Ausgeschieden",
                  };
                  return labels[value] ?? value;
                }}
              />
              <Area
                dataKey="persistent_actors"
                stackId="actors"
                type="monotone"
                fill="url(#detail-temporalPersistent)"
                stroke={CHART_COLORS.blue}
                strokeWidth={2}
                fillOpacity={0.6}
              />
              <Area
                dataKey="new_entrants"
                stackId="actors"
                type="monotone"
                fill="url(#detail-temporalNew)"
                stroke={CHART_COLORS.orange}
                strokeWidth={2}
                fillOpacity={0.6}
              />
              <Area
                dataKey="exited_actors"
                type="monotone"
                fill="url(#detail-temporalExited)"
                stroke={CHART_COLORS.vermillion}
                strokeWidth={2}
                fillOpacity={0.3}
              />
              {dataCompleteYear && data.entrant_trend.length > 0 && data.entrant_trend[data.entrant_trend.length - 1].year > dataCompleteYear && (
                <ReferenceArea
                  x1={dataCompleteYear}
                  x2={data.entrant_trend[data.entrant_trend.length - 1].year}
                  fill="var(--color-text-muted)"
                  fillOpacity={0.08}
                  label={{ value: "Daten ggf. unvollständig", fontSize: 10, fill: "var(--color-text-muted)", position: "insideTop" }}
                />
              )}
            </AreaChart>
          </ResponsiveContainer>
        </DetailChartSection>
      )}

      {/* ── Auto-Analyse ── */}
      <DetailAnalysisSection>
        <div className="space-y-2 text-sm text-[var(--color-text-secondary)]">
          {startYear && endYear && (
            <p>
              Im Zeitraum <strong>{startYear}–{endYear}</strong> waren insgesamt{" "}
              <strong>{totalNew.toLocaleString("de-DE")}</strong> neue Akteure eingetreten,
              während <strong>{totalExited.toLocaleString("de-DE")}</strong> ausgeschieden sind.
              Der Nettosaldo von{" "}
              <strong className={net >= 0 ? "text-[var(--color-chart-growth)]" : "text-[var(--color-chart-decline)]"}>
                {net >= 0 ? "+" : ""}{net.toLocaleString("de-DE")}
              </strong>{" "}
              {net > 0
                ? "deutet auf ein wachsendes Technologiefeld hin."
                : net < 0
                  ? "zeigt eine schrumpfende Akteurslandschaft."
                  : "zeigt eine stabile Akteurslandschaft."}
            </p>
          )}

          {latestYear && (
            <p>
              Im letzten erfassten Jahr ({latestYear.year}) waren{" "}
              <strong>{latestYear.total_active.toLocaleString("de-DE")}</strong> Akteure aktiv,
              davon <strong>{latestYear.persistent_actors.toLocaleString("de-DE")}</strong> persistent
              und <strong>{latestYear.new_entrants.toLocaleString("de-DE")}</strong> neu hinzugekommen.
            </p>
          )}

          {/* Bug v3.4.10/α-F: Topic-Narrativ (aufkommende/abnehmende Themen)
              entfernt — Backend-Feature ist nicht produktionsreif. */}
        </div>
      </DetailAnalysisSection>

      {/* ── Metriken-Erklärung ── */}
      <DetailDataSection title="Metriken-Erklärung">
        <div className="space-y-3 text-sm text-[var(--color-text-secondary)]">
          <p>
            <strong className="text-[var(--color-text-primary)]">Neue Akteure:</strong>{" "}
            Organisationen, die im jeweiligen Jahr erstmals in Patenten oder Projekten
            zu dieser Technologie erscheinen.
          </p>
          <p>
            <strong className="text-[var(--color-text-primary)]">Persistente Akteure:</strong>{" "}
            Organisationen, die bereits in Vorjahren aktiv waren und weiterhin Patente
            anmelden oder Projekte durchführen.
          </p>
          <p>
            <strong className="text-[var(--color-text-primary)]">Ausgeschiedene Akteure:</strong>{" "}
            Organisationen, die in einem Vorjahr aktiv waren, aber im jeweiligen Jahr
            nicht mehr erscheinen.
          </p>
        </div>
      </DetailDataSection>

      {/* ── Programme und Themen-Cluster ── */}
      {data.clusters.length > 0 && (
        <DetailDataSection title="Programme und Themen-Cluster">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wider text-[var(--color-text-muted)]">
                  <th className="px-3 py-2">Jahr</th>
                  <th className="px-3 py-2">Cluster/Programm</th>
                  <th className="px-3 py-2 text-right">Patente/Projekte</th>
                  <th className="px-3 py-2">Keywords</th>
                </tr>
              </thead>
              <tbody>
                {data.clusters.map((cluster, idx) => (
                  <tr
                    key={`${cluster.year}-${cluster.cluster_label}-${idx}`}
                    className="border-b border-[var(--color-border)] last:border-0"
                  >
                    <td className="px-3 py-2 tabular-nums text-[var(--color-text-muted)]">
                      {cluster.year}
                    </td>
                    <td className="px-3 py-2 text-[var(--color-text-secondary)]">
                      {cluster.cluster_label}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                      {cluster.patent_count.toLocaleString("de-DE")}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-1">
                        {cluster.keywords.map((kw) => (
                          <span
                            key={kw}
                            className="inline-block rounded-full border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-2 py-0.5 text-xs text-[var(--color-text-muted)]"
                          >
                            {kw}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </DetailDataSection>
      )}

      {/* ── Aufkommende Themen ── */}
      {data.emerging_topics.length > 0 && (
        <DetailDataSection title="Aufkommende Themen">
          <div className="flex flex-wrap gap-2">
            {data.emerging_topics.map((topic) => (
              <span
                key={topic}
                className="inline-flex items-center gap-1.5 rounded-full border border-green-200 bg-green-50 px-3 py-1.5 text-sm font-medium text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-300"
              >
                <TrendingUp className="h-3.5 w-3.5" aria-hidden="true" />
                {topic}
              </span>
            ))}
          </div>
        </DetailDataSection>
      )}

      {/* ── Abnehmende Themen ── */}
      {data.declining_topics.length > 0 && (
        <DetailDataSection title="Abnehmende Themen">
          <div className="flex flex-wrap gap-2">
            {data.declining_topics.map((topic) => (
              <span
                key={topic}
                className="inline-flex items-center gap-1.5 rounded-full border border-red-200 bg-red-50 px-3 py-1.5 text-sm font-medium text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300"
              >
                <TrendingDown className="h-3.5 w-3.5" aria-hidden="true" />
                {topic}
              </span>
            ))}
          </div>
        </DetailDataSection>
      )}
    </div>
  );
}
