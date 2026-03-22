"use client";

import { useState } from "react";
import { BarChart3, Table2 } from "lucide-react";

interface ChartTableToggleProps {
  chartContent: React.ReactNode;
  tableContent: React.ReactNode;
  defaultView?: "chart" | "table";
}

export default function ChartTableToggle({
  chartContent,
  tableContent,
  defaultView = "chart",
}: ChartTableToggleProps) {
  const [view, setView] = useState<"chart" | "table">(defaultView);

  return (
    <div>
      <div className="flex justify-end mb-2">
        <div className="inline-flex rounded-lg border border-[var(--color-border)] p-0.5" role="tablist">
          <button
            role="tab"
            aria-selected={view === "chart"}
            aria-label="Diagramm-Ansicht"
            onClick={() => setView("chart")}
            className={`rounded-md px-2 py-1 text-xs transition-colors ${
              view === "chart"
                ? "bg-[var(--color-accent)] text-white"
                : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
            }`}
          >
            <BarChart3 className="h-3.5 w-3.5" />
          </button>
          <button
            role="tab"
            aria-selected={view === "table"}
            aria-label="Tabellen-Ansicht"
            onClick={() => setView("table")}
            className={`rounded-md px-2 py-1 text-xs transition-colors ${
              view === "table"
                ? "bg-[var(--color-accent)] text-white"
                : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
            }`}
          >
            <Table2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
      {view === "chart" ? chartContent : tableContent}
    </div>
  );
}
