"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- UC-C: Publikations-Impact Chain
 * Bar chart showing publication trend per year
 * with summary metrics (total pubs, pubs/project)
 * ────────────────────────────────────────────── */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceArea,
} from "recharts";
import PanelCard from "./PanelCard";
import { SEMANTIC_COLORS } from "@/lib/chart-colors";
import {
  resolveProjectsCount,
  buildPublicationCalcRow,
} from "@/lib/publication-calc";
import type { PublicationPanel as PublicationPanelData } from "@/lib/types";

interface PublicationPanelProps {
  data: PublicationPanelData | null;
  isLoading: boolean;
  error: string | null;
  onDetailClick?: () => void;
  queryTimeSeconds?: number;
  /** MIN-11: Externer (Header-)Projektzaehler. Wenn gesetzt, wird er
   *  fuer die explizite "Pub/Projekt × Projekte ≈ Publikationen"-Rechnung
   *  bevorzugt, damit die UI dieselbe Bezugsgroesse wie der Header (UC1)
   *  zeigt. Faellt sonst auf `data.total_projects_with_pubs` zurueck. */
  projectsCount?: number;
  /** MAJ-7/MAJ-8: Letztes vollstaendig abgeschlossenes Kalenderjahr.
   *  Wenn die Pub-Trend-Daten ueber dieses Jahr hinausgehen, zeigt der
   *  Chart eine ReferenceArea „Daten ggf. unvollstaendig" — exakt wie
   *  LandscapePanel/MaturityPanel.  Bisher fehlte der Hinweis trotz
   *  Bedarf laut KONSOLIDIERUNG.md MAJ-8. */
  dataCompleteYear?: number;
}

export default function PublicationPanel({
  data,
  isLoading,
  error,
  onDetailClick,
  queryTimeSeconds,
  projectsCount,
  dataCompleteYear,
}: PublicationPanelProps) {
  return (
    <PanelCard
      title="Publikations-Impact"
      ucNumber={13}
      ucLabel="C"
      ucKey="publication"
      isLoading={isLoading}
      error={error}
      onDetailClick={data ? onDetailClick : undefined}
      queryTimeSeconds={queryTimeSeconds}
    >
      {data && (
        <div className="flex flex-col gap-4">
          {/* Badges */}
          <div className="flex flex-wrap items-center justify-center gap-2">
            <span className="badge-info">
              {data.total_publications.toLocaleString("de-DE")} Publikationen
            </span>
            <span className="badge bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
              {data.publications_per_project.toFixed(1)} Pub/Projekt
            </span>
            <span className="badge bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
              DOI: {(data.doi_coverage * 100).toFixed(0)}%
            </span>
          </div>

          {/* CRIT-1 / MIN-11: Explizite Rechnung sichtbar machen, damit Nutzer
              nachvollziehen, wie sich total_publications zusammensetzt.
              MIN-11: Wenn ein externer Projektzaehler (z. B. Header/UC1)
              uebergeben wird, hat dieser Vorrang -- so passt die Rechnung
              numerisch zum Header-Wert. */}
          {(() => {
            const projects = resolveProjectsCount(
              projectsCount,
              data.total_projects_with_pubs,
            );
            const text = buildPublicationCalcRow(
              data.publications_per_project,
              projects,
              data.total_publications,
            );
            if (text === null) return null;
            return (
              <p
                data-testid="publication-calc-row"
                className="text-center text-[11px] text-[var(--color-text-muted)]"
                title="CORDIS-Projekt-Publikationen: dieselbe Query wie im Header (UC1)."
              >
                {text}
              </p>
            );
          })()}

          {/* Bar Chart: Publication Trend */}
          <div className="h-[clamp(13rem,40vh,28rem)]" aria-label="Publikationstrend pro Jahr">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.pub_trend}>
                <XAxis
                  dataKey="year"
                  tick={{ fill: "var(--color-text-muted)", fontSize: 11 }}
                  tickLine={false}
                  axisLine={{ stroke: "var(--color-border)" }}
                />
                <YAxis
                  tick={{ fill: "var(--color-text-muted)", fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  width={40}
                />
                <Tooltip
                  content={({ payload, label }) => {
                    if (!payload || payload.length === 0) return null;
                    const d = payload[0]?.payload as PublicationPanelData["pub_trend"][number] | undefined;
                    if (!d) return null;
                    return (
                      <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-panel)] px-3 py-2 text-xs shadow-lg">
                        <p className="font-semibold text-[var(--color-text-primary)]">{label}</p>
                        <p className="text-[var(--color-text-muted)]">
                          {(d.publication_count ?? 0).toLocaleString("de-DE")} Publikationen
                        </p>
                        <p className="text-[var(--color-text-muted)]">
                          {(d.project_count ?? 0).toLocaleString("de-DE")} Projekte
                        </p>
                      </div>
                    );
                  }}
                />
                <Bar
                  dataKey="publication_count"
                  fill={SEMANTIC_COLORS.publications}
                  name="Publikationen"
                  radius={[2, 2, 0, 0]}
                />
                {dataCompleteYear &&
                  data.pub_trend.length > 0 &&
                  data.pub_trend[data.pub_trend.length - 1].year > dataCompleteYear && (
                    <ReferenceArea
                      x1={dataCompleteYear}
                      x2={data.pub_trend[data.pub_trend.length - 1].year}
                      fill="#9ca3af"
                      fillOpacity={0.15}
                      label={{
                        value: "Daten ggf. unvollständig",
                        position: "insideTop",
                        fontSize: 9,
                        fill: "#9ca3af",
                      }}
                    />
                  )}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </PanelCard>
  );
}
