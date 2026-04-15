/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Tests fuer Publication Calc (MIN-11)
 *
 * Konsistenz-Audit MIN-11:
 *  - UC13 zeigte "8.0 Pub/Projekt" und "2.456 Publikationen" ohne
 *    explizite Multiplikation. Nutzer mussten den Bezugswert (Projekte)
 *    selbst berechnen.
 *  - Fix: Explizite Rechen-Zeile "8.0 Pub/Projekt × 307 Projekte ≈
 *    2.456 Publikationen". Die Bezugsgroesse soll dem Header (UC1) folgen,
 *    wenn dieser durchgereicht wird.
 * ────────────────────────────────────────────── */

import { describe, expect, it } from "vitest";

import {
  buildPublicationCalcRow,
  resolveProjectsCount,
} from "../publication-calc";

describe("resolveProjectsCount – Bezugsgroesse fuer Pub-Rechnung (MIN-11)", () => {
  it("bevorzugt den externen (Header-)Projektzaehler, wenn vorhanden", () => {
    expect(resolveProjectsCount(307, 280)).toBe(307);
  });

  it("faellt auf den panel-eigenen Wert zurueck, wenn extern nicht gesetzt", () => {
    expect(resolveProjectsCount(undefined, 280)).toBe(280);
  });

  it("ignoriert den externen Wert, wenn er 0 ist", () => {
    expect(resolveProjectsCount(0, 280)).toBe(280);
  });

  it("liefert null, wenn beide Werte <= 0 sind", () => {
    expect(resolveProjectsCount(undefined, 0)).toBeNull();
    expect(resolveProjectsCount(0, 0)).toBeNull();
  });
});

describe("buildPublicationCalcRow – sichtbare Multiplikation (MIN-11)", () => {
  it("rendert das vom Audit geforderte Format mit dem Header-Wert", () => {
    // Live-Beispiel mRNA (Header: 307 Projekte, 8.0 Pub/Projekt, 2.456 Pubs)
    const row = buildPublicationCalcRow(8.0, 307, 2456);
    expect(row).toBe("8.0 Pub/Projekt \u00D7 307 Projekte \u2248 2.456 Publikationen");
  });

  it("nutzt 1 Nachkommastelle fuer Pub/Projekt", () => {
    const row = buildPublicationCalcRow(7.95, 307, 2440);
    expect(row).toContain("8.0 Pub/Projekt");
  });

  it("nutzt de-DE-Lokalisierung mit Punkt als Tausendertrenner", () => {
    const row = buildPublicationCalcRow(8.0, 1234, 12_456);
    expect(row).toContain("1.234 Projekte");
    expect(row).toContain("12.456 Publikationen");
  });

  it("liefert null, wenn keine Bezugsgroesse vorhanden ist", () => {
    expect(buildPublicationCalcRow(8.0, null, 2456)).toBeNull();
  });
});
