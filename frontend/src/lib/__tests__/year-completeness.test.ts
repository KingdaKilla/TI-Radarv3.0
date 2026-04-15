/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Tests for year-completeness helper (AP8)
 *
 * Konsistenz-Audit MAJ-7/MAJ-8:
 *  - Wenn das Backend ``data_complete_year`` liefert UND eine Zeitreihe
 *    Jahre danach enthaelt, MUSS der Hinweis "Daten ggf. unvollstaendig"
 *    angezeigt werden — andernfalls nicht.
 * ────────────────────────────────────────────── */

import { describe, expect, it } from "vitest";

import {
  incompleteYearRange,
  lastCompleteYear,
} from "../year-completeness";

describe("incompleteYearRange", () => {
  it("returns range when series ends after dataCompleteYear", () => {
    const series = [{ year: 2023 }, { year: 2024 }, { year: 2025 }, { year: 2026 }];
    const range = incompleteYearRange(series, 2025);
    expect(range).toEqual({ start: 2025, end: 2026 });
  });

  it("returns null when series ends exactly at dataCompleteYear", () => {
    const series = [{ year: 2023 }, { year: 2024 }, { year: 2025 }];
    expect(incompleteYearRange(series, 2025)).toBeNull();
  });

  it("returns null when series ends before dataCompleteYear", () => {
    const series = [{ year: 2020 }, { year: 2021 }];
    expect(incompleteYearRange(series, 2025)).toBeNull();
  });

  it("returns null when dataCompleteYear missing", () => {
    const series = [{ year: 2025 }, { year: 2026 }];
    expect(incompleteYearRange(series, undefined)).toBeNull();
    expect(incompleteYearRange(series, null)).toBeNull();
    expect(incompleteYearRange(series, 0)).toBeNull();
  });

  it("returns null on empty series", () => {
    expect(incompleteYearRange([], 2025)).toBeNull();
    expect(incompleteYearRange(null, 2025)).toBeNull();
    expect(incompleteYearRange(undefined, 2025)).toBeNull();
  });
});

describe("lastCompleteYear", () => {
  it("returns previous year for mid-year date", () => {
    expect(lastCompleteYear(new Date(2026, 3, 14))).toBe(2025);
  });

  it("returns previous year for January 1st", () => {
    expect(lastCompleteYear(new Date(2026, 0, 1))).toBe(2025);
  });

  it("returns previous year for December 31st", () => {
    expect(lastCompleteYear(new Date(2026, 11, 31))).toBe(2025);
  });
});
