"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- UC9: Technologie-Cluster
 * Radar chart showing cluster fingerprints across
 * 5 normalized dimensions
 * ────────────────────────────────────────────── */

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
import PanelCard from "./PanelCard";
import InfoTooltip from "@/components/ui/InfoTooltip";
import { PALETTE } from "@/lib/chart-colors";
import type { TechClusterPanel as TechClusterPanelData, TechCluster } from "@/lib/types";

interface TechClusterPanelProps {
  data: TechClusterPanelData | null;
  isLoading: boolean;
  error: string | null;
  onDetailClick?: () => void;
  queryTimeSeconds?: number;
}

const CLUSTER_COLORS = PALETTE.slice(0, 5);

/** Min-Max Normalisierung auf 0-100 */
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

export default function TechClusterPanel({
  data,
  isLoading,
  error,
  onDetailClick,
  queryTimeSeconds,
}: TechClusterPanelProps) {
  const topClusters = data?.clusters.slice(0, 5) ?? [];
  const radarData = data ? buildRadarData(topClusters) : [];

  return (
    <PanelCard
      title="Technologie-Cluster"
      ucNumber={9}
      ucKey="tech_cluster"
      isLoading={isLoading}
      error={error}
      onDetailClick={data ? onDetailClick : undefined}
      queryTimeSeconds={queryTimeSeconds}
    >
      {data && (
        <div className="flex flex-col gap-4">
          {/* Summary Badges */}
          <div className="flex flex-wrap items-center justify-center gap-2">
            <span className="badge-info">
              {data.quality.num_clusters} Cluster
            </span>
            <span className="badge bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300 inline-flex items-center gap-1">
              {data.total_actors.toLocaleString("de-DE")} Cluster-Mitglieder
              <InfoTooltip
                text={
                  `UC9 zaehlt Akteure, die mindestens einen CPC-Code innerhalb eines ` +
                  `identifizierten Tech-Clusters halten ` +
                  `(Scope: ${data.actor_scope_label ?? "Cluster-Mitglieder"}). ` +
                  `Diese Zahl ist typischerweise kleiner als UC8 (aktive Akteure im ` +
                  `Zeitfenster) und UC11 (klassifizierte Organisationen) — ` +
                  `unterschiedliche Scopes zaehlen unterschiedliche Populationen.`
                }
              />
            </span>
            <span className="badge bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
              {data.total_cpc_codes} CPC-Klassen
            </span>
            {data.quality.avg_silhouette > 0 && (
              <span className="badge-success">
                Silhouette: {data.quality.avg_silhouette.toFixed(2)}
              </span>
            )}
          </div>

          {/* Radar Chart */}
          {radarData.length > 0 && (
            <div className="h-[clamp(14rem,42vh,30rem)]" aria-label="Cluster-Radar: 5 Dimensionen">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="70%">
                  <PolarGrid stroke="var(--color-border)" />
                  <PolarAngleAxis
                    dataKey="axis"
                    tick={{ fontSize: 9, fill: "var(--color-text-muted)" }}
                  />
                  <PolarRadiusAxis
                    angle={90}
                    domain={[0, 100]}
                    tick={false}
                    axisLine={false}
                  />
                  {topClusters.map((c, idx) => (
                    <Radar
                      key={c.cluster_id}
                      dataKey={c.label}
                      stroke={CLUSTER_COLORS[idx % CLUSTER_COLORS.length]}
                      fill={CLUSTER_COLORS[idx % CLUSTER_COLORS.length]}
                      fillOpacity={0.15}
                      strokeWidth={1.5}
                    />
                  ))}
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--color-bg-panel)",
                      border: "1px solid var(--color-border)",
                      borderRadius: "8px",
                      fontSize: "11px",
                    }}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: "10px" }}
                    iconSize={8}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
    </PanelCard>
  );
}
