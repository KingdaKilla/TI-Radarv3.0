/* ──────────────────────────────────────────────
 * TI-Radar v2 -- Number Formatting Utilities
 * German locale number formatting for KPI display
 * ────────────────────────────────────────────── */

/**
 * Formatiert einen EUR-Betrag in lesbarer Form.
 * - >= 1.000.000.000 => "1,2 Mrd. EUR"
 * - >= 1.000.000     => "1,2 Mio. EUR"
 * - >= 1.000         => "1.234 EUR"
 * - sonst            => "123 EUR"
 */
export function formatEur(value: number): string {
  if (Math.abs(value) >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toLocaleString("de-DE", {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    })} Mrd. EUR`;
  }
  if (Math.abs(value) >= 1_000_000) {
    return `${(value / 1_000_000).toLocaleString("de-DE", {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    })} Mio. EUR`;
  }
  return `${value.toLocaleString("de-DE")} EUR`;
}

/**
 * Formatiert einen Prozentwert (0-1 oder 0-100).
 * Werte <= 1 werden als Anteil interpretiert und * 100 genommen.
 * => "42,3%"
 */
export function formatPercent(value: number): string {
  const pct = Math.abs(value) <= 1 ? value * 100 : value;
  return `${pct.toLocaleString("de-DE", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })}%`;
}

/**
 * Formatiert eine Ganzzahl mit Tausendertrennpunkten.
 * => "1.234"
 */
export function formatNumber(value: number): string {
  return value.toLocaleString("de-DE");
}
