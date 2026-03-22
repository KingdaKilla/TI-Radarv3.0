"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v2 -- UC2: Reifegrad-Analyse (Detailansicht)
 * S-Kurve mit Phasengrenzen, jährliche Wachstumsrate,
 * Modellvergleich (AICc) und berechnete Insights
 * ────────────────────────────────────────────── */

import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
} from "recharts";
import MetricCard from "@/components/charts/MetricCard";
import DetailChartSection from "@/components/detail/DetailChartSection";
import DetailAnalysisSection from "@/components/detail/DetailAnalysisSection";
import DetailDataSection from "@/components/detail/DetailDataSection";
import type { MaturityPanel } from "@/lib/types";

// ── Helpers ──

/** Phase für einen kumulativen Wert (Gao et al. 2013: 10/50/90%-Schwellen).
 *  Fallback auf Backend-Phase wenn saturation_level nicht verfügbar. */
function phaseForYear(
  cumulative: number,
  saturation: number,
  fallback: { label: string; color: string },
): { label: string; color: string } {
  if (saturation <= 0) return fallback;
  const pct = (cumulative / saturation) * 100;
  if (pct < 10) return { label: "Entstehung", color: "#3b82f6" };
  if (pct < 50) return { label: "Wachstum", color: "#22c55e" };
  if (pct < 90) return { label: "Reife", color: "#f59e0b" };
  return { label: "Sättigung", color: "#f97316" };
}

/** R²-Qualitätsstufe */
function r2Quality(r2: number): { label: string; color: string } {
  if (r2 >= 0.95) return { label: "Ausgezeichnet", color: "var(--color-success)" };
  if (r2 >= 0.85) return { label: "Gut", color: "var(--color-warning, #f59e0b)" };
  return { label: "Eingeschränkt", color: "var(--color-error)" };
}

/** Delta-AICc-Interpretation (Burnham & Anderson 2002) */
function aiccInterpretation(delta: number): string {
  if (delta < 2) return "Modelle kaum unterscheidbar — beide Anpassungen ähnlich plausibel.";
  if (delta <= 7) return "Moderater Vorteil für das ausgewählte Modell.";
  return "Starke Evidenz für das ausgewählte Modell.";
}

/** Modellname auf Deutsch */
function modelLabel(name: string): string {
  const map: Record<string, string> = { logistic: "Logistisch", gompertz: "Gompertz", richards: "Richards" };
  return map[name.toLowerCase()] ?? name;
}

/** Alternatives Modell für AICc-Vergleich */
const ALT_MODEL: Record<string, string> = {
  logistic: "Gompertz",
  gompertz: "Logistisch",
  richards: "Logistisch",
};

// ── Phase config ──

const PHASE_CONFIG: Record<
  MaturityPanel["phase"],
  { label: string; color: string; description: string }
> = {
  emergence: {
    label: "Entstehung",
    color: "#3b82f6",
    description:
      "Die Technologie befindet sich in einer frühen Entwicklungsphase. Erste Patente und Forschungsprojekte werden sichtbar, aber die Aktivität ist noch gering.",
  },
  growth: {
    label: "Wachstum",
    color: "#22c55e",
    description:
      "Die Technologie zeigt starkes Wachstum. Die Zahl der Patente und Projekte steigt überproportional an, und die S-Kurve befindet sich im steilsten Abschnitt.",
  },
  maturity: {
    label: "Reife",
    color: "#f59e0b",
    description:
      "Die Technologie hat eine reife Phase erreicht. Das Wachstum verlangsamt sich, und die kumulierten Patente nähern sich der Sättigung.",
  },
  saturation: {
    label: "Sättigung",
    color: "#f97316",
    description:
      "Die Technologie ist weitgehend gesättigt. Neue Patente kommen nur noch in geringem Umfang hinzu, und der Markt ist etabliert.",
  },
  decline: {
    label: "Rückgang",
    color: "#ef4444",
    description:
      "Die Technologie zeigt Anzeichen eines Rückgangs. Die Patentaktivität nimmt ab, möglicherweise zugunsten neuerer Alternativen.",
  },
};

// ── Component ──

interface MaturityDetailProps {
  data: MaturityPanel;
}

export default function MaturityDetail({ data }: MaturityDetailProps) {
  const phaseInfo = PHASE_CONFIG[data.phase];
  const r2q = r2Quality(data.r_squared);

  // Derived values
  const peakYearPt = data.s_curve_data.length > 0
    ? data.s_curve_data.reduce((max, pt) =>
        pt.annual_count > max.annual_count ? pt : max,
        data.s_curve_data[0]
      )
    : null;

  const lastYear = data.s_curve_data.length > 0
    ? data.s_curve_data[data.s_curve_data.length - 1].year
    : null;

  // Phase boundary Y values at 10%, 50%, 90% of saturation
  const sat = data.saturation_level;
  const phaseBoundaries = sat > 0
    ? [
        { pct: 10, y: sat * 0.1, label: "10% — Entstehung/Wachstum" },
        { pct: 50, y: sat * 0.5, label: "50% — Wendepunkt" },
        { pct: 90, y: sat * 0.9, label: "90% — Reife/Sättigung" },
      ]
    : [];

  // Alternative model name for AICc comparison
  const altModelName = ALT_MODEL[data.model_name.toLowerCase()] ?? "Alternativ";

  return (
    <div className="flex flex-col gap-6">
      {/* ── Sektion 1: Kennzahlen (6 Karten) ── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <div className="flex items-center gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-4 py-3">
          <div
            className="h-3 w-3 shrink-0 rounded-full"
            style={{ backgroundColor: phaseInfo.color }}
          />
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium text-[var(--color-text-muted)]">Reifephase</span>
            <span className="text-xl font-bold text-[var(--color-text-primary)]">{data.phase_label}</span>
          </div>
        </div>
        <MetricCard
          label="Reifegrad"
          value={`${data.maturity_percent.toFixed(1)}%`}
          unit="des Sättigungsniveaus"
        />
        <div className="rounded-lg" style={{ borderLeft: `4px solid ${r2q.color}` }}>
          <MetricCard
            label="Modellgüte (R²)"
            value={`${(data.r_squared * 100).toFixed(1)}%`}
            unit={r2q.label}
          />
        </div>
        <MetricCard
          label="Wendepunkt"
          value={data.inflection_year ?? "k. A."}
        />
        <MetricCard
          label="Sättigungsniveau"
          value={data.saturation_level.toLocaleString("de-DE")}
          unit="kum. Patente"
        />
        <MetricCard
          label="CAGR"
          value={`${(data.cagr * 100).toFixed(1)}%`}
          trend={data.cagr > 0 ? "up" : data.cagr < 0 ? "down" : "neutral"}
        />
      </div>

      {/* ── Sektion 2: S-Kurve ── */}
      <DetailChartSection ariaLabel="S-Kurve: Technologie-Reifegrad (Detailansicht)">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={data.s_curve_data}
            margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
          >
            <defs>
              <linearGradient id="detail-gradientFitted" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={phaseInfo.color} stopOpacity={0.3} />
                <stop offset="95%" stopColor={phaseInfo.color} stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
            <XAxis
              dataKey="year"
              tick={{ fontSize: 12, fill: "var(--color-text-muted)" }}
            />
            <YAxis
              tick={{ fontSize: 12, fill: "var(--color-text-muted)" }}
              width={80}
              label={{
                value: "Kumulative Patente",
                angle: -90,
                position: "insideLeft",
                offset: -5,
                style: { fontSize: 11, fill: "var(--color-text-muted)" },
              }}
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
                name === "cumulative" ? "Kumuliert" : "S-Kurve (Fit)",
              ]}
            />
            <Legend
              formatter={(value: string) =>
                value === "cumulative" ? "Kumuliert (beobachtet)" : "S-Kurve (Fit)"
              }
            />

            {/* Phasengrenzen bei 10%, 50%, 90% des Sättigungsniveaus */}
            {phaseBoundaries.map((b) => (
              <ReferenceLine
                key={b.pct}
                y={b.y}
                stroke="var(--color-text-muted)"
                strokeDasharray="4 4"
                strokeOpacity={0.5}
                label={{
                  value: b.label,
                  position: "right",
                  fontSize: 10,
                  fill: "var(--color-text-muted)",
                }}
              />
            ))}

            {/* Wendepunkt (vertikale Linie) */}
            {data.inflection_year && (
              <ReferenceLine
                x={data.inflection_year}
                stroke="var(--color-text-muted)"
                strokeDasharray="5 5"
                label={{
                  value: "Wendepunkt",
                  position: "top",
                  fontSize: 11,
                  fill: "var(--color-text-muted)",
                }}
              />
            )}

            {/* Datenvollständigkeit */}
            {data.data_complete_year &&
              data.s_curve_data.length > 0 &&
              data.s_curve_data[data.s_curve_data.length - 1].year >
                data.data_complete_year && (
                <ReferenceArea
                  x1={data.data_complete_year}
                  x2={data.s_curve_data[data.s_curve_data.length - 1].year}
                  fill="#9ca3af"
                  fillOpacity={0.15}
                  label={{
                    value: "Daten unvollständig",
                    position: "insideTop",
                    fontSize: 10,
                    fill: "#9ca3af",
                  }}
                />
              )}

            <Area
              type="monotone"
              dataKey="fitted"
              stroke={phaseInfo.color}
              strokeWidth={2}
              fill="url(#detail-gradientFitted)"
              name="fitted"
            />
            <Area
              type="monotone"
              dataKey="cumulative"
              stroke="var(--color-text-muted)"
              strokeWidth={1}
              strokeDasharray="4 4"
              fill="none"
              name="cumulative"
            />
          </AreaChart>
        </ResponsiveContainer>
      </DetailChartSection>

      {/* ── Sektion 3: Jährliche Wachstumsrate ── */}
      <DetailChartSection ariaLabel="Jährliche Patentanmeldungen" heightPx={280}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data.s_curve_data}
            margin={{ top: 10, right: 30, left: 20, bottom: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
            <XAxis
              dataKey="year"
              tick={{ fontSize: 12, fill: "var(--color-text-muted)" }}
            />
            <YAxis
              tick={{ fontSize: 12, fill: "var(--color-text-muted)" }}
              width={60}
              label={{
                value: "Jährliche Patente",
                angle: -90,
                position: "insideLeft",
                offset: -5,
                style: { fontSize: 11, fill: "var(--color-text-muted)" },
              }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--color-bg-panel)",
                border: "1px solid var(--color-border)",
                borderRadius: "8px",
                fontSize: "13px",
              }}
              formatter={(value: number) => [
                value.toLocaleString("de-DE"),
                "Patente (jährlich)",
              ]}
            />
            {data.inflection_year && (
              <ReferenceLine
                x={data.inflection_year}
                stroke="var(--color-text-muted)"
                strokeDasharray="5 5"
                label={{
                  value: "Wendepunkt",
                  position: "top",
                  fontSize: 10,
                  fill: "var(--color-text-muted)",
                }}
              />
            )}
            <Bar dataKey="annual_count" name="Jährlich" radius={[2, 2, 0, 0]}>
              {data.s_curve_data.map((pt) => (
                <Cell
                  key={pt.year}
                  fill={phaseForYear(pt.cumulative, data.saturation_level, phaseInfo).color}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </DetailChartSection>

      {/* ── Sektion 4: Berechnete Insights ── */}
      <DetailAnalysisSection>
        <div className="space-y-3 text-sm text-[var(--color-text-secondary)]">
          <p>
            Die Technologie befindet sich in der Phase{" "}
            <strong className="text-[var(--color-text-primary)]">
              {data.phase_label}
            </strong>{" "}
            mit einem Reifegrad von{" "}
            <strong>{data.maturity_percent.toFixed(1)}%</strong>.{" "}
            {data.saturation_level > 0 && (
              <>
                Das geschätzte Sättigungsniveau liegt bei{" "}
                <strong>{data.saturation_level.toLocaleString("de-DE")}</strong>{" "}
                kumulativen Patenten.
              </>
            )}
          </p>

          <p>
            {peakYearPt && peakYearPt.annual_count > 0 ? (
              <>
                Das Jahr mit der höchsten Patentaktivität war{" "}
                <strong>{peakYearPt.year}</strong> mit{" "}
                <strong>{peakYearPt.annual_count.toLocaleString("de-DE")}</strong>{" "}
                Anmeldungen.{" "}
              </>
            ) : (
              <>Detaillierte Jahresdaten sind derzeit nicht verfügbar. </>
            )}
            Der CAGR beträgt{" "}
            <strong
              className={
                data.cagr >= 0
                  ? "text-[var(--color-chart-growth)]"
                  : "text-[var(--color-chart-decline)]"
              }
            >
              {(data.cagr * 100).toFixed(1)}%
            </strong>
            {data.inflection_year && (
              <>
                , der Wendepunkt wurde im Jahr{" "}
                <strong>{data.inflection_year}</strong> erreicht
              </>
            )}
            .
          </p>

          <p>
            Das ausgewählte Modell ({modelLabel(data.model_name)}) erreicht eine
            Bestimmtheit von{" "}
            <strong>R² = {(data.r_squared * 100).toFixed(1)}%</strong>{" "}
            ({r2q.label}).
            {data.delta_aicc > 0 && (
              <>
                {" "}Der Delta-AICc zum nächstbesten Modell beträgt{" "}
                <strong>{data.delta_aicc.toFixed(1)}</strong>:{" "}
                {aiccInterpretation(data.delta_aicc)}
              </>
            )}
          </p>
        </div>
      </DetailAnalysisSection>

      {/* ── Sektion 5: Modellvergleich ── */}
      <DetailDataSection title="Modellvergleich (AICc)">
        <div className="space-y-4">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wider text-[var(--color-text-muted)]">
                  <th className="px-3 py-2">Modell</th>
                  <th className="px-3 py-2 text-right">R²</th>
                  <th className="px-3 py-2 text-right">AICc</th>
                  <th className="px-3 py-2 text-right">ΔAICc</th>
                  <th className="px-3 py-2 text-right">Ausgewählt</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-[var(--color-border)]">
                  <td className="px-3 py-2 font-medium text-[var(--color-text-primary)]">
                    {modelLabel(data.model_name)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                    {(data.r_squared * 100).toFixed(1)}%
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                    {data.aicc_selected.toFixed(1)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                    0,0
                  </td>
                  <td className="px-3 py-2 text-right text-[var(--color-success)]">
                    ✓
                  </td>
                </tr>
                {data.aicc_alternative > 0 && (
                <tr className="border-b border-[var(--color-border)] last:border-0">
                  <td className="px-3 py-2 text-[var(--color-text-secondary)]">
                    {altModelName}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                    —
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                    {data.aicc_alternative.toFixed(1)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                    {data.delta_aicc.toFixed(1)}
                  </td>
                  <td className="px-3 py-2 text-right text-[var(--color-text-muted)]">
                    —
                  </td>
                </tr>
                )}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-[var(--color-text-muted)]">
            Modellselektion nach Burnham &amp; Anderson (2002): ΔAICc &lt; 2 =
            kaum unterscheidbar, 2–7 = moderater Vorteil, &gt; 7 = starke Evidenz.
          </p>
        </div>
      </DetailDataSection>

      {/* Phasen-Details */}
      <DetailDataSection title="Phasen-Details">
        <div className="rounded-lg border border-[var(--color-border)] p-4">
          <div className="mb-2 flex items-center gap-2">
            <div
              className="h-3 w-3 rounded-full"
              style={{ backgroundColor: phaseInfo.color }}
            />
            <span className="text-sm font-semibold text-[var(--color-text-primary)]">
              {phaseInfo.label}
            </span>
          </div>
          <p className="text-sm text-[var(--color-text-secondary)]">
            {phaseInfo.description}
          </p>
        </div>
      </DetailDataSection>

      {/* Zeitreihe */}
      <DetailDataSection title="Zeitreihe (vollständig)">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wider text-[var(--color-text-muted)]">
                <th className="px-3 py-2">Jahr</th>
                <th className="px-3 py-2 text-right">Jährlich</th>
                <th className="px-3 py-2 text-right">Kumulativ</th>
                <th className="px-3 py-2 text-right">Modell (Fit)</th>
                <th className="px-3 py-2">Phase</th>
              </tr>
            </thead>
            <tbody>
              {data.s_curve_data.map((pt) => (
                <tr
                  key={pt.year}
                  className="border-b border-[var(--color-border)] last:border-0"
                >
                  <td className="px-3 py-2 font-medium text-[var(--color-text-primary)]">
                    {pt.year}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                    {pt.annual_count.toLocaleString("de-DE")}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                    {pt.cumulative.toLocaleString("de-DE")}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                    {pt.fitted.toLocaleString("de-DE", {
                      maximumFractionDigits: 0,
                    })}
                  </td>
                  <td className="px-3 py-2 text-[var(--color-text-muted)]">
                    {phaseForYear(pt.cumulative, data.saturation_level, phaseInfo).label}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DetailDataSection>
    </div>
  );
}
