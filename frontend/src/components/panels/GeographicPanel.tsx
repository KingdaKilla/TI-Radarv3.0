"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v2 -- UC6: Geographische Verteilung
 * Country-level patent and project distribution
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
import PanelCard from "./PanelCard";
import { CHART_COLORS } from "@/lib/chart-colors";
import { COUNTRY_NAMES } from "@/lib/countries";
import type { GeographicPanel as GeographicPanelData } from "@/lib/types";

interface GeographicPanelProps {
  data: GeographicPanelData | null;
  isLoading: boolean;
  error: string | null;
  onDetailClick?: () => void;
}

export default function GeographicPanel({
  data,
  isLoading,
  error,
  onDetailClick,
}: GeographicPanelProps) {
  const chartCountries = data?.countries
    .filter(c => c.patent_count > 0 || c.project_count > 0)
    .slice(0, 10)
    .map(c => ({
      ...c,
      country_name: c.country_name || COUNTRY_NAMES[c.country_code] || c.country_code,
    }));
  const barCount = chartCountries?.length ?? 0;
  /* ~40px per bar + 40px padding — scale height to actual data */
  const chartHeight = Math.max(120, barCount * 40 + 40);

  return (
    <PanelCard
      title="Geographische Verteilung"
      ucNumber={6}
      isLoading={isLoading}
      error={error}
      onDetailClick={data ? onDetailClick : undefined}
    >
      {data && (
        <div className="flex flex-col items-center justify-center gap-4 h-full">
          {/* Badges */}
          <div className="flex flex-wrap items-center justify-center gap-2">
            <span className="badge-info">
              {data.countries.length} Länder
            </span>
            {data.top_country && (
              <span className="badge bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                Top: {data.top_country}
              </span>
            )}
          </div>

          {/* Länderverteilung */}
          <div className="w-full" style={{ height: chartHeight }} aria-label="Patente und Projekte nach Land">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={chartCountries}
                    layout="vertical"
                    margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis
                      type="number"
                      tick={{ fontSize: 10, fill: "var(--color-text-muted)" }}
                    />
                    <YAxis
                      dataKey="country_name"
                      type="category"
                      width={100}
                      interval={0}
                      tick={{ fontSize: 8, fill: "var(--color-text-secondary)" }}
                      tickFormatter={(v: string) =>
                        v.length > 14 ? v.slice(0, 13).trimEnd() + "…" : v
                      }
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "var(--color-bg-panel)",
                        border: "1px solid var(--color-border)",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                      formatter={(value: number, name: string) => [
                        value.toLocaleString("de-DE"),
                        name === "patent_count" ? "Patente" : "Projekte",
                      ]}
                    />
                    <Bar
                      dataKey="patent_count"
                      fill={CHART_COLORS.blue}
                      radius={[0, 4, 4, 0]}
                      name="patent_count"
                    />
                    <Bar
                      dataKey="project_count"
                      fill={CHART_COLORS.orange}
                      radius={[0, 4, 4, 0]}
                      name="project_count"
                    />
                  </BarChart>
                </ResponsiveContainer>
          </div>
        </div>
      )}
    </PanelCard>
  );
}
