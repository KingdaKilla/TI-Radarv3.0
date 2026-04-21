"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3.5.0 -- DetailLlmAnalysis
 * Ruft das LLM-Feature (POST /api/analyze-panel) beim Öffnen einer
 * Detailansicht auf und rendert das Ergebnis via DetailAnalysisSection.
 *
 * v3.6.6: Statische Analyse-Narrative wurden aus den 13 Detail-
 * Komponenten entfernt - diese Komponente ist jetzt der einzige
 * Analyse-Block im Detail-Overlay. Die Section trägt Header
 * "KI-Analyse" + Badge "KI-generiert" + Halluzinations-Disclaimer.
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

  if (error) {
    // eslint-disable-next-line no-console
    console.warn("[DetailLlmAnalysis] Analyse fehlgeschlagen:", error);
  }

  return (
    <DetailAnalysisSection analysisText={analysisText} isLoading={isLoading}>
      {modelUsed && analysisText ? <>Modell: {modelUsed}</> : null}
    </DetailAnalysisSection>
  );
}
