/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Publication Calc Helpers (MIN-11)
 *
 * Pure Helfer fuer die explizite "Pub/Projekt × Projekte ≈ Publikationen"-
 * Zeile im PublicationPanel (UC13). Vorher konnten Nutzer aus
 *   "8.0 Pub/Projekt" und "2.456 Publikationen"
 * die zugrundeliegende Projektzahl nur durch Kopfrechnen rekonstruieren.
 *
 * Trennung als reines Logik-Modul (kein React, keine recharts), damit es
 * unabhaengig in Vitest gepruefft werden kann.
 * ────────────────────────────────────────────── */

/** Loest den Projektzaehler fuer die explizite Rechnung auf:
 *  - Externer (Header-/UC1-)Projektzaehler hat Vorrang, damit die Rechnung
 *    numerisch zum Header passt.
 *  - Sonst Fallback auf den Panel-eigenen Wert (UC13.total_projects_with_pubs).
 *  - Liefert `null`, wenn beide Werte <= 0 sind. Die UI darf in diesem Fall
 *    keine Rechen-Zeile rendern.
 */
export function resolveProjectsCount(
  external: number | undefined,
  internal: number,
): number | null {
  if (external !== undefined && external > 0) return external;
  if (internal > 0) return internal;
  return null;
}

/** Baut die explizite Rechen-Zeile als String:
 *    "8.0 Pub/Projekt × 307 Projekte ≈ 2.456 Publikationen"
 *  Liefert `null`, wenn die Bezugsgroesse fehlt (siehe `resolveProjectsCount`).
 *  Verwendet `de-DE`-Lokalisierung fuer die grossen Zahlen, damit das Format
 *  zu den Badges (`toLocaleString("de-DE")`) passt.
 */
export function buildPublicationCalcRow(
  pubsPerProject: number,
  projects: number | null,
  totalPublications: number,
): string | null {
  if (projects === null) return null;
  return (
    `${pubsPerProject.toFixed(1)} Pub/Projekt` +
    ` \u00D7 ${projects.toLocaleString("de-DE")} Projekte` +
    ` \u2248 ${totalPublications.toLocaleString("de-DE")} Publikationen`
  );
}
