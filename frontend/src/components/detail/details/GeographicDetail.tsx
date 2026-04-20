"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- UC6: Geographische Verteilung (Detailansicht)
 * 5 Sektionen: MetricCards, Balkendiagramm, Auto-Analyse,
 * Kooperationspaare, Ländertabelle
 * ────────────────────────────────────────────── */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import MetricCard from "@/components/charts/MetricCard";
import DetailChartSection from "@/components/detail/DetailChartSection";
import DetailAnalysisSection from "@/components/detail/DetailAnalysisSection";
import DetailDataSection from "@/components/detail/DetailDataSection";
import { CHART_COLORS, SEMANTIC_COLORS } from "@/lib/chart-colors";
import { COUNTRY_NAMES, getCountryName } from "@/lib/countries";
import type { GeographicPanel } from "@/lib/types";

interface GeographicDetailProps {
  data: GeographicPanel;
}

export default function GeographicDetail({ data }: GeographicDetailProps) {
  /* Ländernamen per Lookup ergänzen */
  const countries = data.countries.map((c) => ({
    ...c,
    country_name: c.country_name || COUNTRY_NAMES[c.country_code] || c.country_code,
  }));

  /* Aggregationen */
  const totalPatents = countries.reduce((s, c) => s + c.patent_count, 0);
  const totalProjects = countries.reduce((s, c) => s + c.project_count, 0);

  /* Top-3 Konzentration */
  const sortedByTotal = [...countries].sort(
    (a, b) => (b.patent_count + b.project_count) - (a.patent_count + a.project_count),
  );
  const top3Total = sortedByTotal.slice(0, 3).reduce(
    (s, c) => s + c.patent_count + c.project_count, 0,
  );
  const grandTotal = totalPatents + totalProjects;
  const top3Share = grandTotal > 0 ? (top3Total / grandTotal) * 100 : 0;

  /* Dynamische Höhe für Balkendiagramm */
  const chartHeight = Math.max(500, countries.length * 36 + 80);

  /* Kooperationspaare sortiert */
  const coopPairs = [...data.cooperation_pairs].sort(
    (a, b) => b.co_project_count - a.co_project_count,
  );

  return (
    <div className="flex flex-col gap-6">
      {/* ── Sektion 1: Kennzahlen ── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <MetricCard
          label="Top-Land"
          value={data.top_country}
        />
        <MetricCard
          label="EU-Anteil"
          value={`${(data.eu_share * 100).toFixed(1)}%`}
        />
        <MetricCard
          label="Länder"
          value={countries.length}
        />
        <MetricCard
          // Bug v3.4.9/S: Der Wert ist die Summe der Patent-Counts über die
          // zurückgegebenen Länder (Top-20). Im Executive-Summary steht dagegen
          // `landscape.total_patents` (EU-27 insgesamt). Die beiden Zahlen
          // können differieren, weil der Country-Breakdown auf Top-20 limitiert
          // ist und Patente ohne klares Herkunftsland nicht zählbar sind. Das
          // Label wird daher präzisiert.
          label="Patente (Top-20 Länder)"
          value={totalPatents.toLocaleString("de-DE")}
        />
        <MetricCard
          label="Projekte (Top-20 Länder)"
          value={totalProjects.toLocaleString("de-DE")}
        />
        <MetricCard
          label="Top-3 Anteil"
          value={`${top3Share.toFixed(1)}%`}
        />
      </div>

      {/* ── Sektion 2: Gruppiertes Balkendiagramm ── */}
      <DetailChartSection
        ariaLabel="Patente und Projekte nach Land (vollständig)"
        heightPx={chartHeight}
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={countries}
            layout="vertical"
            margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
            <XAxis
              type="number"
              tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
            />
            <YAxis
              dataKey="country_name"
              type="category"
              width={120}
              tick={{ fontSize: 10, fill: "var(--color-text-secondary)" }}
              tickFormatter={(v: string) =>
                v.length > 16 ? v.slice(0, 15).trimEnd() + "\u2026" : v
              }
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--color-bg-panel)",
                border: "1px solid var(--color-border)",
                borderRadius: "8px",
                fontSize: "13px",
              }}
              formatter={(value: number, name: string) => [
                value.toLocaleString("de-DE"),
                name === "patent_count" ? "Patente" : "Projekte",
              ]}
            />
            <Legend
              formatter={(value: string) =>
                value === "patent_count" ? "Patente" : "Projekte"
              }
            />
            <Bar
              dataKey="patent_count"
              fill={SEMANTIC_COLORS.patents}
              radius={[0, 4, 4, 0]}
              name="patent_count"
            />
            <Bar
              dataKey="project_count"
              fill={SEMANTIC_COLORS.projects}
              radius={[0, 4, 4, 0]}
              name="project_count"
            />
          </BarChart>
        </ResponsiveContainer>
      </DetailChartSection>

      {/* ── Sektion 3: Auto-Analyse ── */}
      <DetailAnalysisSection>
        <div className="space-y-2 text-sm text-[var(--color-text-secondary)]">
          <p>
            Die Technologie ist in <strong>{countries.length}</strong> Ländern vertreten,
            mit insgesamt <strong>{totalPatents.toLocaleString("de-DE")}</strong> Patenten
            und <strong>{totalProjects.toLocaleString("de-DE")}</strong> EU-Projekten.
            {data.eu_share > 0 && (
              <> Der Anteil grenzüberschreitender Kooperationen liegt bei{" "}
              <strong>{(data.eu_share * 100).toFixed(1)}%</strong>.</>
            )}
          </p>

          {sortedByTotal.length >= 3 && (
            <p>
              Die drei aktivsten Länder sind{" "}
              <strong>{sortedByTotal[0].country_name}</strong>,{" "}
              <strong>{sortedByTotal[1].country_name}</strong> und{" "}
              <strong>{sortedByTotal[2].country_name}</strong> —
              sie vereinen <strong>{top3Share.toFixed(1)}%</strong> der Gesamtaktivität.
              {top3Share > 60
                ? " Die geographische Konzentration ist hoch."
                : top3Share > 40
                  ? " Die Verteilung ist moderat konzentriert."
                  : " Die Aktivität ist breit gestreut."}
            </p>
          )}

          {coopPairs.length > 0 && (
            <p>
              Insgesamt wurden <strong>{coopPairs.length}</strong> bilaterale Kooperationspaare identifiziert.
              {coopPairs[0] && (
                <> Das stärkste Paar ist{" "}
                <strong>{getCountryName(coopPairs[0].country_a)}</strong> – <strong>{getCountryName(coopPairs[0].country_b)}</strong>{" "}
                mit <strong>{coopPairs[0].co_project_count.toLocaleString("de-DE")}</strong> gemeinsamen Projekten.</>
              )}
            </p>
          )}
        </div>
      </DetailAnalysisSection>

      {/* ── Sektion 4: Kooperationspaare ── */}
      {coopPairs.length > 0 && (
        <DetailDataSection title="Bilaterale Kooperationen">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wider text-[var(--color-text-muted)]">
                  <th className="px-3 py-2 w-8">#</th>
                  <th className="px-3 py-2">Land A</th>
                  <th className="px-3 py-2">Land B</th>
                  <th className="px-3 py-2 text-right">Gemeinsame Projekte</th>
                </tr>
              </thead>
              <tbody>
                {coopPairs.map((pair, idx) => (
                  <tr
                    key={`${pair.country_a}-${pair.country_b}-${idx}`}
                    className="border-b border-[var(--color-border)] last:border-0"
                  >
                    <td className="px-3 py-2 tabular-nums text-[var(--color-text-muted)]">
                      {idx + 1}
                    </td>
                    <td className="px-3 py-2 text-[var(--color-text-secondary)]">
                      {getCountryName(pair.country_a)}
                    </td>
                    <td className="px-3 py-2 text-[var(--color-text-secondary)]">
                      {getCountryName(pair.country_b)}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                      {pair.co_project_count.toLocaleString("de-DE")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </DetailDataSection>
      )}

      {/* ── Sektion 5: Vollständige Ländertabelle ── */}
      <DetailDataSection title="Länder (vollständig)">
        {countries.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wider text-[var(--color-text-muted)]">
                  <th className="px-3 py-2 w-8">#</th>
                  <th className="px-3 py-2">Land</th>
                  <th className="px-3 py-2">Code</th>
                  <th className="px-3 py-2 text-right">Patente</th>
                  <th className="px-3 py-2 text-right">Projekte</th>
                  <th className="px-3 py-2 text-right">Anteil</th>
                </tr>
              </thead>
              <tbody>
                {countries.map((country, idx) => {
                  const countryTotal = country.patent_count + country.project_count;
                  const pct = grandTotal > 0 ? (countryTotal / grandTotal) * 100 : 0;
                  return (
                    <tr
                      key={country.country_code}
                      className="border-b border-[var(--color-border)] last:border-0"
                    >
                      <td className="px-3 py-2 tabular-nums text-[var(--color-text-muted)]">
                        {idx + 1}
                      </td>
                      <td className="px-3 py-2 font-medium text-[var(--color-text-secondary)]">
                        {country.country_name}
                      </td>
                      <td className="px-3 py-2 font-mono text-[var(--color-text-muted)]">
                        {country.country_code}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                        {country.patent_count.toLocaleString("de-DE")}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                        {country.project_count.toLocaleString("de-DE")}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                        {pct.toFixed(1)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot>
                <tr className="border-t-2 border-[var(--color-border)] font-semibold">
                  <td className="px-3 py-2 text-[var(--color-text-primary)]" />
                  <td className="px-3 py-2 text-[var(--color-text-primary)]">Gesamt</td>
                  <td className="px-3 py-2" />
                  <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-primary)]">
                    {totalPatents.toLocaleString("de-DE")}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-primary)]">
                    {totalProjects.toLocaleString("de-DE")}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-primary)]">
                    100%
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        ) : (
          <p className="text-sm italic text-[var(--color-text-muted)]">
            Keine Länderdaten vorhanden.
          </p>
        )}
      </DetailDataSection>
    </div>
  );
}
