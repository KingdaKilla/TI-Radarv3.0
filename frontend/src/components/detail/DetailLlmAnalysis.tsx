"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3.5.0 -- DetailLlmAnalysis
 * Ruft das LLM-Feature (POST /api/analyze-panel) beim Öffnen einer
 * Detailansicht auf und rendert das Ergebnis via DetailAnalysisSection.
 *
 * Der useAnalysis-Hook:
 *   - cached pro (technology + useCaseKey), damit Re-Renders keine
 *     Duplicate-Requests triggern
 *   - nutzt AbortController für Schlüssel-Wechsel
 *   - liefert analysisText + isLoading + error + modelUsed
 *
 * Graceful Degradation: Bei Fehler oder fehlender LLM-Verfügbarkeit
 * bleibt `analysisText` leer — die Section zeigt den Placeholder-Text
 * "Textuelle Analyse wird in einer zukünftigen Version hinzugefügt".
 * ────────────────────────────────────────────── */

import { useAnalysis } from "@/hooks/useAnalysis";
import DetailAnalysisSection from "./DetailAnalysisSection";

interface DetailLlmAnalysisProps {
  technology: string;
  useCaseKey: string;
  panelData: Record<string, unknown> | null | undefined;
}

export default function DetailLlmAnalysis({
  technology,
  useCaseKey,
  panelData,
}: DetailLlmAnalysisProps) {
  const { analysisText, isLoading, modelUsed, error } = useAnalysis(
    technology,
    useCaseKey,
    panelData,
  );

  // Wenn Analyse leer UND Fehler auftritt, zeigen wir trotzdem Placeholder
  // via DetailAnalysisSection (siehe dessen Default-Zweig). Error selbst
  // loggen wir in Console, ohne UI-Disruption.
  if (error) {
    // eslint-disable-next-line no-console
    console.warn("[DetailLlmAnalysis] Analyse fehlgeschlagen:", error);
  }

  return (
    <DetailAnalysisSection
      analysisText={analysisText}
      isLoading={isLoading}
    >
      {modelUsed && analysisText ? (
        <p className="mt-3 text-[10px] italic text-[var(--color-text-muted)]">
          Textuelle Analyse generiert von {modelUsed}.
        </p>
      ) : null}
    </DetailAnalysisSection>
  );
}
