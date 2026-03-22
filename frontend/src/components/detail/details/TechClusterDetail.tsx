"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v2 -- UC9: Technologie-Cluster (Detailansicht)
 * Enlarged radar chart + full cluster table with
 * dominant topics + expandable rows
 * ────────────────────────────────────────────── */

import { Fragment, useState } from "react";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { ChevronDown, ChevronRight } from "lucide-react";
import MetricCard from "@/components/charts/MetricCard";
import DetailChartSection from "@/components/detail/DetailChartSection";
import DetailAnalysisSection from "@/components/detail/DetailAnalysisSection";
import DetailDataSection from "@/components/detail/DetailDataSection";
import { PALETTE } from "@/lib/chart-colors";
import type { TechClusterPanel, TechCluster } from "@/lib/types";

interface TechClusterDetailProps {
  data: TechClusterPanel;
}

const CLUSTER_COLORS = [...PALETTE];

function normalize(value: number, min: number, max: number): number {
  if (max === min) return 50;
  return Math.round(((value - min) / (max - min)) * 100);
}

function buildRadarData(clusters: TechCluster[]) {
  if (clusters.length === 0) return [];

  const vals = {
    patent: clusters.map((c) => c.patent_count),
    actor: clusters.map((c) => c.actor_count),
    density: clusters.map((c) => c.density),
    coherence: clusters.map((c) => c.coherence),
    cagr: clusters.map((c) => c.cagr),
  };

  const ranges = Object.fromEntries(
    Object.entries(vals).map(([k, arr]) => [
      k,
      { min: Math.min(...arr), max: Math.max(...arr) },
    ])
  ) as Record<string, { min: number; max: number }>;

  const dimensions = [
    { key: "patent", label: "Patente", field: "patent_count" as const },
    { key: "actor", label: "Akteure", field: "actor_count" as const },
    { key: "density", label: "Dichte", field: "density" as const },
    { key: "coherence", label: "Kohärenz", field: "coherence" as const },
    { key: "cagr", label: "Wachstum", field: "cagr" as const },
  ];

  return dimensions.map((dim) => {
    const entry: Record<string, string | number> = { axis: dim.label };
    clusters.forEach((c) => {
      entry[c.label] = normalize(
        c[dim.field],
        ranges[dim.key].min,
        ranges[dim.key].max
      );
    });
    return entry;
  });
}

export default function TechClusterDetail({ data }: TechClusterDetailProps) {
  const radarData = buildRadarData(data.clusters);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  return (
    <div className="flex flex-col gap-6">
      {/* Kennzahlen */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MetricCard label="Cluster" value={data.quality.num_clusters} />
        <MetricCard
          label="Akteure gesamt"
          value={data.total_actors.toLocaleString("de-DE")}
        />
        <MetricCard
          label="CPC-Klassen"
          value={data.total_cpc_codes.toLocaleString("de-DE")}
        />
        <MetricCard
          label="Silhouette-Score"
          value={data.quality.avg_silhouette.toFixed(3)}
        />
      </div>

      {/* Radar-Chart (vergroessert) */}
      {radarData.length > 0 && (
        <DetailChartSection ariaLabel="Cluster-Radar: 5 Dimensionen (alle Cluster)">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="75%">
              <PolarGrid stroke="var(--color-border)" />
              <PolarAngleAxis
                dataKey="axis"
                tick={{ fontSize: 13, fill: "var(--color-text-muted)" }}
              />
              <PolarRadiusAxis
                angle={90}
                domain={[0, 100]}
                tick={{ fontSize: 10, fill: "var(--color-text-muted)" }}
              />
              {data.clusters.map((c, idx) => (
                <Radar
                  key={c.cluster_id}
                  dataKey={c.label}
                  stroke={CLUSTER_COLORS[idx % CLUSTER_COLORS.length]}
                  fill={CLUSTER_COLORS[idx % CLUSTER_COLORS.length]}
                  fillOpacity={0.12}
                  strokeWidth={2}
                />
              ))}
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--color-bg-panel)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
              />
              <Legend wrapperStyle={{ fontSize: "11px" }} iconSize={10} />
            </RadarChart>
          </ResponsiveContainer>
        </DetailChartSection>
      )}

      {/* Dimensionen-Erklaerungen */}
      <div className="grid grid-cols-1 gap-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-panel)] p-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="text-xs">
          <p className="font-semibold text-[var(--color-text-primary)]">Patente</p>
          <p className="text-[var(--color-text-muted)]">Anzahl der Patentfamilien, die dem Cluster zugeordnet sind</p>
        </div>
        <div className="text-xs">
          <p className="font-semibold text-[var(--color-text-primary)]">Akteure</p>
          <p className="text-[var(--color-text-muted)]">Anzahl distinkte Organisationen (Anmelder/Projektpartner) im Cluster</p>
        </div>
        <div className="text-xs">
          <p className="font-semibold text-[var(--color-text-primary)]">Dichte</p>
          <p className="text-[var(--color-text-muted)]">Vernetzungsgrad: Anteil tatsächlicher Co-Patentierungen an allen möglichen Verbindungen (0=isoliert, 1=vollständig vernetzt)</p>
        </div>
        <div className="text-xs">
          <p className="font-semibold text-[var(--color-text-primary)]">Kohärenz</p>
          <p className="text-[var(--color-text-muted)]">Thematische Geschlossenheit: Wie stark überlappen sich die CPC-Klassifikationen der Akteure im Cluster</p>
        </div>
        <div className="text-xs">
          <p className="font-semibold text-[var(--color-text-primary)]">Wachstum (CAGR)</p>
          <p className="text-[var(--color-text-muted)]">Jährliche Wachstumsrate der Patentaktivität im Cluster über den Analysezeitraum</p>
        </div>
      </div>

      {/* ── Auto-Analyse ── */}
      <DetailAnalysisSection>
        <div className="space-y-2 text-sm text-[var(--color-text-secondary)]">
          <p>
            Die Community-Detection identifizierte <strong>{data.quality.num_clusters}</strong> Technologie-Cluster
            mit einem Silhouette-Score von <strong>{data.quality.avg_silhouette.toFixed(3)}</strong>
            {data.quality.avg_silhouette >= 0.5
              ? " (gute Trennschärfe)."
              : data.quality.avg_silhouette >= 0.25
                ? " (moderate Trennschärfe)."
                : " (schwache Trennschärfe — Cluster überlappen stark)."}
            {data.quality.modularity > 0 && (
              <> Die Modularität beträgt <strong>{data.quality.modularity.toFixed(3)}</strong>.</>
            )}
          </p>

          {data.clusters.length > 0 && (() => {
            const largest = data.clusters.reduce((b, c) => (c.patent_count > b.patent_count ? c : b), data.clusters[0]);
            const fastest = data.clusters.reduce((b, c) => (c.cagr > b.cagr ? c : b), data.clusters[0]);
            return (
              <>
                <p>
                  Das größte Cluster ist <strong>{largest.label}</strong> mit{" "}
                  <strong>{largest.patent_count.toLocaleString("de-DE")}</strong> Patenten
                  und <strong>{largest.actor_count.toLocaleString("de-DE")}</strong> Akteuren.
                </p>
                {fastest.cagr > 0 && fastest.label !== largest.label && (
                  <p>
                    Das am schnellsten wachsende Cluster ist <strong>{fastest.label}</strong> mit
                    einer CAGR von{" "}
                    <strong className="text-[var(--color-chart-growth)]">
                      {(fastest.cagr * 100).toFixed(1)}%
                    </strong>.
                  </p>
                )}
              </>
            );
          })()}
        </div>
      </DetailAnalysisSection>

      {/* Vollstaendige Cluster-Tabelle */}
      <DetailDataSection title="Cluster-Übersicht">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wider text-[var(--color-text-muted)]">
                <th className="pb-3 pr-4 w-8"></th>
                <th className="pb-3 pr-4">ID</th>
                <th className="pb-3 pr-4">Label</th>
                <th className="pb-3 pr-4 text-right">Akteure</th>
                <th className="pb-3 pr-4 text-right">Patente</th>
                <th className="pb-3 pr-4 text-right">CPC-Codes</th>
                <th className="pb-3 pr-4 text-right">Kohärenz</th>
                <th className="pb-3 pr-4 text-right">CAGR</th>
                <th className="pb-3">Themen</th>
              </tr>
            </thead>
            <tbody>
              {data.clusters.map((cluster) => (
                <Fragment key={cluster.cluster_id}>
                  <tr
                    className="cursor-pointer border-b border-[var(--color-border)]/50 text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]"
                    onClick={() =>
                      setExpandedId(
                        expandedId === cluster.cluster_id
                          ? null
                          : cluster.cluster_id
                      )
                    }
                  >
                    <td className="py-2 pr-2 text-[var(--color-text-muted)]">
                      {expandedId === cluster.cluster_id ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                    </td>
                    <td className="py-2 pr-4 text-[var(--color-text-muted)]">
                      {cluster.cluster_id}
                    </td>
                    <td className="py-2 pr-4 font-medium">{cluster.label}</td>
                    <td className="py-2 pr-4 text-right">
                      {cluster.actor_count.toLocaleString("de-DE")}
                    </td>
                    <td className="py-2 pr-4 text-right">
                      {cluster.patent_count.toLocaleString("de-DE")}
                    </td>
                    <td className="py-2 pr-4 text-right">
                      {cluster.cpc_codes.length}
                    </td>
                    <td className="py-2 pr-4 text-right">
                      {cluster.coherence.toFixed(3)}
                    </td>
                    <td
                      className={`py-2 pr-4 text-right font-medium ${
                        cluster.cagr >= 0
                          ? "text-green-600 dark:text-green-400"
                          : "text-red-500 dark:text-red-400"
                      }`}
                    >
                      {(cluster.cagr * 100).toFixed(1)}%
                    </td>
                    <td className="py-2">
                      <div className="flex flex-wrap gap-1">
                        {cluster.dominant_topics.map((topic) => (
                          <span
                            key={topic}
                            className="inline-block rounded bg-[var(--color-bg-secondary)] px-1.5 py-0.5 text-xs text-[var(--color-text-muted)]"
                          >
                            {topic}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                  {expandedId === cluster.cluster_id && (
                    <tr key={`${cluster.cluster_id}-expanded`}>
                      <td colSpan={9} className="bg-[var(--color-bg-secondary)] px-4 py-3">
                        <div className="space-y-3">
                          <div>
                            <p className="text-xs font-semibold text-[var(--color-text-muted)] mb-1">CPC-Klassifikationen</p>
                            <div className="flex flex-wrap gap-1">
                              {cluster.cpc_codes.map((code) => (
                                <span key={code} className="badge-info text-[10px]">{code}</span>
                              ))}
                            </div>
                          </div>
                          <div className="grid grid-cols-3 gap-4 text-xs">
                            <div>
                              <p className="text-[var(--color-text-muted)]">Dichte</p>
                              <p className="font-medium text-[var(--color-text-primary)]">{cluster.density.toFixed(4)}</p>
                            </div>
                            <div>
                              <p className="text-[var(--color-text-muted)]">Kohärenz</p>
                              <p className="font-medium text-[var(--color-text-primary)]">{cluster.coherence.toFixed(4)}</p>
                            </div>
                            <div>
                              <p className="text-[var(--color-text-muted)]">CAGR</p>
                              <p className={`font-medium ${cluster.cagr >= 0 ? "text-green-600" : "text-red-500"}`}>
                                {(cluster.cagr * 100).toFixed(1)}%
                              </p>
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </DetailDataSection>
    </div>
  );
}
