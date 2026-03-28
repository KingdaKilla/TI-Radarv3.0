"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Cluster Accordion
 * Expandable sections for thematic UC clusters
 * Collapsed state shows summary metrics badges
 * ────────────────────────────────────────────── */

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import type { Cluster } from "@/lib/clusters";
import type { ReactNode } from "react";

interface ClusterAccordionProps {
  clusters: Cluster[];
  renderContent: (cluster: Cluster) => ReactNode;
}

export default function ClusterAccordion({
  clusters,
  renderContent,
}: ClusterAccordionProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  return (
    <div className="space-y-3">
      {clusters.map((cluster) => {
        const isExpanded = expandedId === cluster.id;
        return (
          <div
            key={cluster.id}
            className="panel-card overflow-hidden"
          >
            {/* Accordion Header */}
            <button
              onClick={() => setExpandedId(isExpanded ? null : cluster.id)}
              className="w-full flex items-center justify-between p-5 text-left transition-colors hover:bg-[var(--color-bg-secondary)]"
              aria-expanded={isExpanded}
              aria-controls={`cluster-content-${cluster.id}`}
            >
              <div className="flex-1 min-w-0">
                <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">
                  {cluster.title}
                </h3>
                <p className="text-sm text-[var(--color-text-muted)] mt-0.5 truncate">
                  {cluster.subtitle}
                </p>
              </div>

              {/* Collapsed Metrics */}
              {!isExpanded && (
                <div className="hidden sm:flex gap-4 mr-4">
                  {cluster.metrics.map((m, i) => (
                    <div key={i} className="text-center">
                      <div className="text-xs text-[var(--color-text-muted)]">
                        {m.label}
                      </div>
                      <div className="text-sm font-mono text-[var(--color-text-secondary)]">
                        {m.value}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <ChevronDown
                className={`h-5 w-5 shrink-0 text-[var(--color-text-muted)] transition-transform ${
                  isExpanded ? "rotate-180" : ""
                }`}
                aria-hidden="true"
              />
            </button>

            {/* Expanded Content */}
            {isExpanded && (
              <div
                id={`cluster-content-${cluster.id}`}
                className="border-t border-[var(--color-border)] p-5"
              >
                {renderContent(cluster)}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
