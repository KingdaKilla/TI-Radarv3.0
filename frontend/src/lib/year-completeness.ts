/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Frontend Helper: Jahres-Vollstaendigkeit (MAJ-7/MAJ-8)
 *
 * Zentrale Logik fuer den ReferenceArea-Hinweis "Daten ggf. unvollstaendig":
 *   - Nimmt einen optionalen ``dataCompleteYear`` (vom Backend) entgegen.
 *   - Nimmt eine Zeitreihe (mit ``year``-Feldern) entgegen.
 *   - Liefert Start/Ende der Highlight-Region oder ``null`` (kein Hinweis).
 *
 * Spiegelt strukturell ``packages/shared/domain/year_completeness.py`` —
 * gleiche Definition: Jahr ``Y`` ist abgeschlossen wenn ``today.year > Y``.
 * ────────────────────────────────────────────── */

export interface IncompleteYearRange {
  /** Erstes Jahr, das im Highlight liegt (= dataCompleteYear). */
  start: number;
  /** Letztes Jahr in der Zeitreihe. */
  end: number;
}

/**
 * Bestimmt den Bereich der Zeitreihe, der wegen unvollstaendiger Jahre
 * markiert werden soll. Liefert ``null`` wenn kein Hinweis noetig ist
 * (z. B. weil ``dataCompleteYear`` fehlt oder die Reihe vor dem Cutoff endet).
 */
export function incompleteYearRange<T extends { year: number }>(
  series: readonly T[] | null | undefined,
  dataCompleteYear: number | null | undefined,
): IncompleteYearRange | null {
  if (!dataCompleteYear) return null;
  if (!series || series.length === 0) return null;
  const last = series[series.length - 1].year;
  if (last <= dataCompleteYear) return null;
  return { start: dataCompleteYear, end: last };
}

/** Letztes vollstaendig abgeschlossenes Kalenderjahr (Client-seitiger Fallback). */
export function lastCompleteYear(today: Date = new Date()): number {
  return today.getFullYear() - 1;
}
