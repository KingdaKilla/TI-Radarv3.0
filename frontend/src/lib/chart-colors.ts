/**
 * Okabe-Ito Farbpalette -- farbenblind-sicher
 * Empfohlen von Nature Methods fuer wissenschaftliche Visualisierungen.
 * Quelle: Okabe, M. & Ito, K. (2008)
 */
export const CHART_COLORS = {
  orange: "#E69F00",
  skyBlue: "#56B4E9",
  green: "#009E73",
  yellow: "#F0E442",
  blue: "#0072B2",
  vermillion: "#D55E00",
  purple: "#CC79A7",
  black: "#000000",
} as const;

/** Geordnete Farbpalette fuer kategorische Daten (max 8 Kategorien) */
export const PALETTE = [
  CHART_COLORS.blue,       // Primaerfarbe (ersetzt #338bff)
  CHART_COLORS.orange,     // Sekundaer (ersetzt #22c55e)
  CHART_COLORS.green,      // Tertiaer (ersetzt #f59e0b)
  CHART_COLORS.vermillion, // Quartaer (ersetzt #ef4444)
  CHART_COLORS.skyBlue,    // 5.
  CHART_COLORS.yellow,     // 6.
  CHART_COLORS.purple,     // 7.
  CHART_COLORS.black,      // 8.
] as const;

/** Spezifische Zuordnungen fuer konsistente Semantik */
export const SEMANTIC_COLORS = {
  patents: CHART_COLORS.blue,
  projects: CHART_COLORS.orange,
  publications: CHART_COLORS.purple,
  growth: CHART_COLORS.green,
  decline: CHART_COLORS.vermillion,
  neutral: CHART_COLORS.skyBlue,
} as const;
