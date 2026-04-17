"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- UC10: Wissenschaftsdisziplinen
 * EuroSciVoc taxonomy mapping showing scientific
 * discipline distribution and interdisciplinarity
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
import { CHART_COLORS } from "@/lib/chart-colors";
import PanelCard from "./PanelCard";
import type { EuroSciVocPanel as EuroSciVocPanelData } from "@/lib/types";

interface EuroSciVocPanelProps {
  data: EuroSciVocPanelData | null;
  isLoading: boolean;
  error: string | null;
  onDetailClick?: () => void;
  queryTimeSeconds?: number;
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export default function EuroSciVocPanel({
  data,
  isLoading,
  error,
  onDetailClick,
  queryTimeSeconds,
}: EuroSciVocPanelProps) {
  const chartData = data?.fields_of_science.map((f) => ({
    ...f,
    share_pct: f.share * 100,
  }));

  return (
    <PanelCard
      title="Wissenschaftsdisziplinen"
      ucNumber={10}
      ucKey="euroscivoc"
      isLoading={isLoading}
      error={error}
      onDetailClick={data ? onDetailClick : undefined}
      queryTimeSeconds={queryTimeSeconds}
    >
      {data && (
        <div className="flex flex-col gap-4">
          {/* Badges — Bug v3.4.7/A-003 (F8): Terminologie war inkonsistent
              (Panel: "2 Felder" vs. Detail: "50 Disziplinen"). Jetzt klar:
              active_fields = aktive Wissenschaftsfelder (Level 1),
              active_disciplines = Level 2 Disziplinen im Mapping. */}
          <div className="flex flex-wrap items-center justify-center gap-2">
            <span className="badge-info">
              {data.interdisciplinarity.active_fields}{" "}
              {data.interdisciplinarity.active_fields === 1 ? "Fachgebiet" : "Fachgebiete"}
            </span>
            <span className="badge bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
              {data.interdisciplinarity.active_disciplines} Disziplinen
            </span>
            <span className="badge bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
              {data.total_mapped_publications.toLocaleString("de-DE")} Projekte
            </span>
          </div>

          {/* Fields of Science Bar Chart */}
          <div className="h-[clamp(13rem,40vh,28rem)]" aria-label="Wissenschaftsfelder nach Anteil">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData?.slice(0, 7)}
                layout="vertical"
                margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis
                  type="number"
                  tick={{ fontSize: 10, fill: "var(--color-text-muted)" }}
                  tickFormatter={(v) => `${v.toFixed(0)}%`}
                />
                <YAxis
                  dataKey="label"
                  type="category"
                  width={120}
                  tick={{ fontSize: 10, fill: "var(--color-text-secondary)" }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--color-bg-panel)",
                    border: "1px solid var(--color-border)",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                  formatter={(value: number) => [
                    `${value.toFixed(1)}%`,
                    "Anteil",
                  ]}
                />
                <Bar dataKey="share_pct" fill={CHART_COLORS.purple} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Metrics Footer */}
          <p className="text-xs text-[var(--color-text-muted)]">
            {data.total_mapped_publications.toLocaleString("de-DE")} Projekte
            zugeordnet &middot; Shannon-Index:{" "}
            {data.interdisciplinarity.active_fields < 2
              ? "—"
              : data.interdisciplinarity.shannon_index.toFixed(2)}
          </p>
        </div>
      )}
    </PanelCard>
  );
}
