"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v2 -- UC3: Wettbewerbsanalyse (Detailansicht)
 * 6 Kennzahlen, Akteurs-Balkendiagramm, HHI-Trend,
 * Kollaborationsnetzwerk (react-force-graph-2d), Analyse-Text, Akteurs-Tabelle
 * ────────────────────────────────────────────── */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import type { ForceGraphMethods } from "react-force-graph-2d";
import {
  BarChart,
  Bar,
  ComposedChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceArea,
  ReferenceLine,
} from "recharts";
import MetricCard from "@/components/charts/MetricCard";
import DetailChartSection from "@/components/detail/DetailChartSection";
import DetailAnalysisSection from "@/components/detail/DetailAnalysisSection";
import DetailDataSection from "@/components/detail/DetailDataSection";
import { CHART_COLORS, SEMANTIC_COLORS, PALETTE } from "@/lib/chart-colors";
import { getCountryName } from "@/lib/countries";
import type { CompetitivePanel } from "@/lib/types";

// react-force-graph-2d uses Canvas 2D (no WebGL/Three.js) — SSR disabled
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

// ── Helpers ──

function truncateName(name: string, max = 22): string {
  if (name.length <= max) return name;
  return name.slice(0, max - 1).trimEnd() + "\u2026";
}

/** HHI → Farbe (DOJ Merger Guidelines Schwellenwerte) */
function hhiColor(hhi: number): string {
  if (hhi < 1500) return CHART_COLORS.green;
  if (hhi < 2500) return CHART_COLORS.orange;
  return CHART_COLORS.vermillion;
}

/** HHI → Qualitative Einordnung */
function hhiLabel(hhi: number): string {
  if (hhi < 1500) return "Wettbewerbsintensiv";
  if (hhi < 2500) return "Moderat konzentriert";
  return "Hoch konzentriert";
}

/** Community-ID → Farbe (max 8 Communities) */
const COMMUNITY_COLORS = [...PALETTE];

// ── Component ──

interface CompetitiveDetailProps {
  data: CompetitivePanel;
}

export default function CompetitiveDetail({ data }: CompetitiveDetailProps) {
  const chartHeight = Math.max(400, data.top_assignees.length * 40 + 80);
  const topActor = data.top_assignees.length > 0 ? data.top_assignees[0] : null;

  // Dynamic columns
  const hasProjects = data.top_assignees.some((a) => a.project_count > 0);
  const hasCountry = data.top_assignees.some((a) => a.country_code !== "");
  const hasActorType = data.top_assignees.some((a) => a.actor_type !== "" && a.actor_type !== "Sonstige");
  const hasMarketShare = data.top_assignees.some((a) => a.market_share > 0);
  const totalPatents = data.top_assignees.reduce((s, a) => s + a.patent_count, 0);

  // HHI trend domain
  const hhiMax = data.hhi_trend.length > 0
    ? Math.max(3000, ...data.hhi_trend.map((p) => p.hhi)) * 1.1
    : 3000;

  // HHI trend interpretation
  const hhiTrendDirection = (() => {
    if (data.hhi_trend.length < 2) return null;
    const first = data.hhi_trend[0].hhi;
    const last = data.hhi_trend[data.hhi_trend.length - 1].hhi;
    const diff = last - first;
    if (Math.abs(diff) < 100) return "stabil";
    return diff > 0 ? "steigend" : "fallend";
  })();

  // Network graph — container width measurement
  const graphContainerRef = useRef<HTMLDivElement>(null);
  const [graphWidth, setGraphWidth] = useState(0);

  useEffect(() => {
    const el = graphContainerRef.current;
    if (!el) return;
    setGraphWidth(el.clientWidth);
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) setGraphWidth(entry.contentRect.width);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Force-graph ref for d3-force tuning + zoomToFit
  const fgRef = useRef<ForceGraphMethods | undefined>(undefined);

  // Network graph data — filter to largest connected component so
  // isolated pairs/triples don't push zoomToFit out too far
  const hasNetwork = data.network_nodes.length > 0 && data.network_edges.length > 0;
  const graphData = useMemo(() => {
    const nodeIds = new Set(data.network_nodes.map((n) => n.id));
    // Build adjacency list
    const adj = new Map<string, Set<string>>();
    for (const id of nodeIds) adj.set(id, new Set());
    for (const e of data.network_edges) {
      if (nodeIds.has(e.source) && nodeIds.has(e.target)) {
        adj.get(e.source)!.add(e.target);
        adj.get(e.target)!.add(e.source);
      }
    }
    // BFS to find connected components
    const visited = new Set<string>();
    let largestComponent = new Set<string>();
    for (const startId of nodeIds) {
      if (visited.has(startId)) continue;
      const component = new Set<string>();
      const queue = [startId];
      while (queue.length > 0) {
        const cur = queue.pop()!;
        if (visited.has(cur)) continue;
        visited.add(cur);
        component.add(cur);
        for (const neighbor of adj.get(cur) ?? []) {
          if (!visited.has(neighbor)) queue.push(neighbor);
        }
      }
      if (component.size > largestComponent.size) largestComponent = component;
    }

    const filteredNodes = data.network_nodes.filter((n) => largestComponent.has(n.id));
    const filteredEdges = data.network_edges.filter(
      (e) => largestComponent.has(e.source) && largestComponent.has(e.target),
    );

    return {
      nodes: filteredNodes.map((n) => ({
        id: n.id,
        label: n.label,
        val: Math.max(1, Math.log(n.size + 1) * 2),
        color: COMMUNITY_COLORS[n.community % COMMUNITY_COLORS.length],
      })),
      links: filteredEdges.map((e) => ({
        source: e.source,
        target: e.target,
        weight: Math.max(0.5, Math.log(e.weight + 1) * 1.5),
      })),
      totalNodes: data.network_nodes.length,
      shownNodes: filteredNodes.length,
    };
  }, [data.network_nodes, data.network_edges]);

  // Configure d3-force: strong charge repulsion spreads nodes,
  // stronger center prevents outliers from drifting too far
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    const charge = fg.d3Force("charge");
    if (charge) charge.strength(-400);
    const link = fg.d3Force("link");
    if (link) link.distance(80);
    const center = fg.d3Force("center");
    if (center) center.strength(0.1);
    fg.d3ReheatSimulation();
  }, [graphData]);

  const handleEngineStop = useCallback(() => {
    fgRef.current?.zoomToFit(400, 50);
  }, []);

  const paintNodeLabel = useCallback(
    (node: Record<string, unknown>, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const label = String(node.label ?? "");
      if (!label) return;
      // Show truncated labels at all zoom levels, full labels when zoomed in
      const displayLabel = globalScale < 1.2 ? truncateName(label, 14) : label;
      const fontSize = Math.min(10, 10 / globalScale);
      ctx.font = `${fontSize}px sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillStyle = "#9ca3af";
      ctx.fillText(
        displayLabel,
        Number(node.x ?? 0),
        Number(node.y ?? 0) + Number(node.val ?? 3) + 2,
      );
    },
    [],
  );

  return (
    <div className="flex flex-col gap-6">
      {/* ── Sektion 1: 6 Kennzahlen ── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        {/* HHI mit Farbindikator */}
        <div className="flex items-center gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-4 py-3">
          <div
            className="h-3 w-3 shrink-0 rounded-full"
            style={{ backgroundColor: hhiColor(data.hhi_index) }}
          />
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium text-[var(--color-text-muted)]">
              HHI-Index
            </span>
            <span className="text-xl font-bold text-[var(--color-text-primary)]">
              {data.hhi_index.toFixed(0)}
            </span>
          </div>
        </div>

        <MetricCard
          label="CR4"
          value={`${(data.cr4_share * 100).toFixed(1)}%`}
          unit="Top-4 Anteil"
        />
        <MetricCard
          label="Akteure"
          value={data.total_actors > 0 ? data.total_actors : data.top_assignees.length}
        />
        <MetricCard
          label="Top-Akteur"
          value={topActor ? truncateName(topActor.name, 18) : "k. A."}
        />
        <MetricCard
          label="Top-3 Anteil"
          value={`${(data.top3_share * 100).toFixed(1)}%`}
        />
        <MetricCard
          label="Top-10 Anteil"
          value={`${(data.top10_share * 100).toFixed(1)}%`}
        />
      </div>

      {/* ── Sektion 2: Horizontales Balkendiagramm ── */}
      <DetailChartSection
        ariaLabel="Wettbewerber nach Patenten und Projekten (vollständig)"
        heightPx={chartHeight}
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data.top_assignees}
            layout="vertical"
            margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
            barCategoryGap="20%"
          >
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
            <XAxis
              type="number"
              tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
            />
            <YAxis
              dataKey="name"
              type="category"
              width={140}
              tick={{ fontSize: 10, fill: "var(--color-text-secondary)" }}
              tickFormatter={(v: string) => truncateName(v)}
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
              stackId="total"
              fill={SEMANTIC_COLORS.patents}
              radius={[0, 0, 0, 0]}
              name="patent_count"
            />
            <Bar
              dataKey="project_count"
              stackId="total"
              fill={SEMANTIC_COLORS.projects}
              radius={[0, 4, 4, 0]}
              name="project_count"
            />
          </BarChart>
        </ResponsiveContainer>
      </DetailChartSection>

      {/* ── Sektion 3: HHI-Trend ── */}
      {data.hhi_trend.length > 1 && (
        <DetailChartSection ariaLabel="HHI-Konzentrationstrend über Zeit" heightPx={300}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={data.hhi_trend}
              margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
            >
              <defs>
                <linearGradient id="detail-gradHhi" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={hhiColor(data.hhi_index)} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={hhiColor(data.hhi_index)} stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis
                dataKey="year"
                tick={{ fontSize: 12, fill: "var(--color-text-muted)" }}
              />
              <YAxis
                domain={[0, hhiMax]}
                tick={{ fontSize: 12, fill: "var(--color-text-muted)" }}
                width={60}
                label={{
                  value: "HHI",
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
                  value.toFixed(0),
                  "HHI",
                ]}
              />
              {/* Konzentrationszonen */}
              <ReferenceArea y1={0} y2={1500} fill={CHART_COLORS.green} fillOpacity={0.06} />
              <ReferenceArea y1={1500} y2={2500} fill={CHART_COLORS.orange} fillOpacity={0.06} />
              <ReferenceArea y1={2500} y2={hhiMax} fill={CHART_COLORS.vermillion} fillOpacity={0.06} />
              <ReferenceLine
                y={1500}
                stroke={CHART_COLORS.orange}
                strokeDasharray="4 4"
                strokeOpacity={0.6}
                label={{
                  value: "1.500 — Moderat",
                  position: "right",
                  fontSize: 10,
                  fill: "var(--color-text-muted)",
                }}
              />
              <ReferenceLine
                y={2500}
                stroke={CHART_COLORS.vermillion}
                strokeDasharray="4 4"
                strokeOpacity={0.6}
                label={{
                  value: "2.500 — Hoch",
                  position: "right",
                  fontSize: 10,
                  fill: "var(--color-text-muted)",
                }}
              />
              <Area
                type="monotone"
                dataKey="hhi"
                stroke={hhiColor(data.hhi_index)}
                strokeWidth={2}
                fill="url(#detail-gradHhi)"
                name="HHI"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </DetailChartSection>
      )}

      {/* ── Sektion 4: Kollaborationsnetzwerk ── */}
      {hasNetwork && graphData.nodes.length > 0 && (
        <>
          <DetailChartSection ariaLabel="Kollaborationsnetzwerk" heightPx={450}>
            <div
              ref={graphContainerRef}
              style={{ width: "100%", height: "100%", overflow: "hidden" }}
            >
              {graphWidth > 0 && (
                <ForceGraph2D
                  ref={fgRef}
                  graphData={graphData}
                  width={graphWidth}
                  height={400}
                  nodeRelSize={3}
                  nodeLabel="label"
                  nodeVal="val"
                  nodeColor="color"
                  linkWidth={(link: Record<string, unknown>) => Number(link.weight ?? 1)}
                  linkColor={() => "rgba(156,163,175,0.35)"}
                  nodeCanvasObjectMode={() => "after"}
                  nodeCanvasObject={paintNodeLabel}
                  enableZoomInteraction={true}
                  enablePanInteraction={true}
                  d3AlphaDecay={0.02}
                  d3VelocityDecay={0.3}
                  warmupTicks={50}
                  cooldownTicks={200}
                  onEngineStop={handleEngineStop}
                />
              )}
            </div>
          </DetailChartSection>
          {graphData.totalNodes > graphData.shownNodes && (
            <p className="text-center text-xs text-[var(--color-text-muted)] -mt-4">
              Größte Komponente: {graphData.shownNodes} von {graphData.totalNodes} Akteuren
              ({graphData.totalNodes - graphData.shownNodes} isolierte Akteure ausgeblendet)
            </p>
          )}
        </>
      )}

      {/* ── Sektion 5: Analyse ── */}
      <DetailAnalysisSection>
        <div className="space-y-3 text-sm text-[var(--color-text-secondary)]">
          {/* Absatz 1: Marktstruktur */}
          <p>
            Der Markt ist mit einem HHI von{" "}
            <strong className="text-[var(--color-text-primary)]">
              {data.hhi_index.toFixed(0)}
            </strong>{" "}
            <strong style={{ color: hhiColor(data.hhi_index) }}>
              {hhiLabel(data.hhi_index).toLowerCase()}
            </strong>.
            {data.cr4_share > 0 && (
              <>
                {" "}Die Top-4-Akteure kontrollieren zusammen{" "}
                <strong>{(data.cr4_share * 100).toFixed(1)}%</strong> des
                Marktes (CR4).
              </>
            )}
          </p>

          {/* Absatz 2: Akteurs-Landschaft */}
          <p>
            Insgesamt wurden{" "}
            <strong className="text-[var(--color-text-primary)]">
              {data.total_actors > 0
                ? data.total_actors
                : data.top_assignees.length}
            </strong>{" "}
            Akteure identifiziert.
            {topActor && (
              <>
                {" "}Führend ist{" "}
                <strong className="text-[var(--color-text-primary)]">
                  {topActor.name}
                </strong>{" "}
                mit einem Marktanteil von{" "}
                <strong>{(topActor.market_share * 100).toFixed(1)}%</strong>
                {topActor.patent_count > 0 && (
                  <> ({topActor.patent_count.toLocaleString("de-DE")} Patente)</>
                )}.
              </>
            )}
            {data.top3_share > 0 && (
              <>
                {" "}Die Top-3 vereinen{" "}
                <strong>{(data.top3_share * 100).toFixed(1)}%</strong>,
                die Top-10{" "}
                <strong>{(data.top10_share * 100).toFixed(1)}%</strong>{" "}
                der Gesamtaktivität.
                {data.top3_share > 0.6 && (
                  <> Dies deutet auf eine starke Kopflastigkeit hin.</>
                )}
                {data.top3_share < 0.3 && (
                  <> Die Aktivität ist relativ gleichmäßig verteilt.</>
                )}
              </>
            )}
          </p>

          {/* Absatz 3: HHI-Trend */}
          {hhiTrendDirection && data.hhi_trend.length >= 2 && (
            <p>
              {hhiTrendDirection === "steigend" && (
                <>
                  Die Marktkonzentration hat sich im Betrachtungszeitraum{" "}
                  <strong className="text-[var(--color-chart-decline)]">
                    erhöht
                  </strong>{" "}
                  — der Wettbewerb wird enger.
                </>
              )}
              {hhiTrendDirection === "fallend" && (
                <>
                  Die Marktkonzentration ist{" "}
                  <strong className="text-[var(--color-chart-growth)]">
                    gesunken
                  </strong>{" "}
                  — neue Akteure diversifizieren das Feld.
                </>
              )}
              {hhiTrendDirection === "stabil" && (
                <>
                  Die Marktkonzentration ist über den Betrachtungszeitraum{" "}
                  <strong>stabil</strong> geblieben.
                </>
              )}
              {" "}Der HHI lag {data.hhi_trend[0].year} bei{" "}
              <strong>{data.hhi_trend[0].hhi.toFixed(0)}</strong> und{" "}
              {data.hhi_trend[data.hhi_trend.length - 1].year} bei{" "}
              <strong>
                {data.hhi_trend[data.hhi_trend.length - 1].hhi.toFixed(0)}
              </strong>.
            </p>
          )}

          {/* Absatz 4: Methodenhinweis */}
          <p className="text-xs text-[var(--color-text-muted)]">
            Der HHI (Herfindahl-Hirschman Index) berechnet sich als Summe der
            quadrierten Marktanteile aller Akteure (Skala 0–10.000).
            Schwellenwerte nach den US-Merger-Leitlinien: &lt; 1.500 =
            wettbewerbsintensiv, 1.500–2.500 = moderat konzentriert, &gt; 2.500
            = hoch konzentriert. Die CR4 gibt den kumulierten Marktanteil der
            vier größten Akteure an.
          </p>
        </div>
      </DetailAnalysisSection>

      {/* ── Sektion 6: Erweiterte Akteurs-Tabelle ── */}
      <DetailDataSection title="Akteure (vollständig)">
        {data.top_assignees.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wider text-[var(--color-text-muted)]">
                  <th className="px-3 py-2">#</th>
                  <th className="px-3 py-2">Name</th>
                  {hasCountry && <th className="px-3 py-2">Land</th>}
                  {hasActorType && <th className="px-3 py-2">Typ</th>}
                  <th className="px-3 py-2 text-right">Patente</th>
                  <th className="px-3 py-2 text-right">Patentanteil</th>
                  {hasProjects && (
                    <th className="px-3 py-2 text-right">Projekte</th>
                  )}
                  {hasMarketShare && (
                    <th className="px-3 py-2 text-right">Marktanteil</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {data.top_assignees.map((actor, idx) => (
                  <tr
                    key={`${actor.name}-${idx}`}
                    className="border-b border-[var(--color-border)] last:border-0"
                  >
                    <td className="px-3 py-2 tabular-nums text-[var(--color-text-muted)]">
                      {idx + 1}
                    </td>
                    <td className="px-3 py-2 text-[var(--color-text-secondary)]">
                      {actor.name}
                    </td>
                    {hasCountry && (
                      <td className="px-3 py-2 text-[var(--color-text-muted)]">
                        {actor.country_code
                          ? getCountryName(actor.country_code)
                          : "–"}
                      </td>
                    )}
                    {hasActorType && (
                      <td className="px-3 py-2 text-[var(--color-text-muted)]">
                        {actor.actor_type || "–"}
                      </td>
                    )}
                    <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                      {actor.patent_count.toLocaleString("de-DE")}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                      {totalPatents > 0
                        ? `${((actor.patent_count / totalPatents) * 100).toFixed(1)}%`
                        : "–"}
                    </td>
                    {hasProjects && (
                      <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                        {actor.project_count.toLocaleString("de-DE")}
                      </td>
                    )}
                    {hasMarketShare && (
                      <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-muted)]">
                        {(actor.market_share * 100).toFixed(1)}%
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm italic text-[var(--color-text-muted)]">
            Keine Akteurs-Daten vorhanden.
          </p>
        )}
      </DetailDataSection>
    </div>
  );
}
