/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Publication Calc Helpers
 *
 * Pure Helfer fuer die explizite "Pub/Projekt × Projekte ≈ Publikationen"-
 * Zeile im PublicationPanel (UC13). Vorher konnten Nutzer aus
 *   "8.0 Pub/Projekt" und "2.456 Publikationen"
 * die zugrundeliegende Projektzahl nur durch Kopfrechnen rekonstruieren.
 *
 * Trennung als reines Logik-Modul (kein React, keine recharts), damit es
 * unabhaengig in Vitest gepruefft werden kann.
 *
 * Bug v3.4.7/C-006 / A-4: `publications_per_project` = total_pub /
 * total_projects_with_pubs (also nur Projekte mit Publikationen, z.B. 932
 * von 1757 bei AI). Der UI-Label nutzte bisher den externen UC1-Projektzaehler
 * (1757), was zu der mathematisch falschen Zeile "50.1 × 1.757 = 46.689"
 * führte (50.1 × 1757 = 88.027). Korrekt: 50.1 × 932 = 46.693 ≈ 46.689.
 * Die Auflösungslogik priorisiert jetzt `total_projects_with_pubs`.
 * ────────────────────────────────────────────── */

/** Loest den Projektzaehler fuer die explizite Rechnung auf:
 *  - **Panel-eigener `total_projects_with_pubs` hat Vorrang**, damit die
 *    Rechnung mathematisch stimmt (`publications_per_project` wird gegen
 *    diesen Wert gebildet).
 *  - Sonst Fallback auf den externen Header-Zaehler (UC1.total_projects) —
 *    besser etwas anzeigen als gar nichts.
 *  - Liefert `null`, wenn beide Werte <= 0 sind. Die UI darf in diesem Fall
 *    keine Rechen-Zeile rendern.
 */
export function resolveProjectsCount(
  external: number | undefined,
  internal: number,
): number | null {
  // Panel-eigener Wert (total_projects_with_pubs) hat Vorrang, weil
  // publications_per_project genau gegen diesen Wert gebildet wurde.
  if (internal > 0) return internal;
  if (external !== undefined && external > 0) return external;
  return null;
}

/** Baut die explizite Rechen-Zeile als String:
 *    "50.1 Pub/Projekt × 932 Projekte (mit Pubs) ≈ 46.689 Publikationen"
 *  Liefert `null`, wenn die Bezugsgroesse fehlt (siehe `resolveProjectsCount`).
 *  Verwendet `de-DE`-Lokalisierung fuer die grossen Zahlen, damit das Format
 *  zu den Badges (`toLocaleString("de-DE")`) passt.
 *
 *  Der Suffix "(mit Pubs)" macht transparent, dass nur Projekte mit mindestens
 *  einer Publikation gezählt werden — wichtig für das Verständnis der
 *  Diskrepanz zu UC1.total_projects (der alle Projekte enthält).
 */
export function buildPublicationCalcRow(
  pubsPerProject: number,
  projects: number | null,
  totalPublications: number,
): string | null {
  if (projects === null) return null;
  return (
    `${pubsPerProject.toFixed(1)} Pub/Projekt` +
    ` \u00D7 ${projects.toLocaleString("de-DE")} Projekte (mit Pubs)` +
    ` \u2248 ${totalPublications.toLocaleString("de-DE")} Publikationen`
  );
}
