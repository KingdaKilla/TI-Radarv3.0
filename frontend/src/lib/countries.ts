/* ──────────────────────────────────────────────
 * TI-Radar v3 -- EU Country Codes
 * EU-27 member states + associated countries
 * (German labels for UI display)
 * ────────────────────────────────────────────── */

/** EU-27 Mitgliedstaaten */
export const EU_COUNTRIES: Record<string, string> = {
  AT: "Österreich",
  BE: "Belgien",
  BG: "Bulgarien",
  CY: "Zypern",
  CZ: "Tschechien",
  DE: "Deutschland",
  DK: "Dänemark",
  EE: "Estland",
  ES: "Spanien",
  FI: "Finnland",
  FR: "Frankreich",
  GR: "Griechenland",
  HR: "Kroatien",
  HU: "Ungarn",
  IE: "Irland",
  IT: "Italien",
  LT: "Litauen",
  LU: "Luxemburg",
  LV: "Lettland",
  MT: "Malta",
  NL: "Niederlande",
  PL: "Polen",
  PT: "Portugal",
  RO: "Rumänien",
  SE: "Schweden",
  SI: "Slowenien",
  SK: "Slowakei",
};

/** Assoziierte Länder (Horizon Europe) */
export const ASSOCIATED_COUNTRIES: Record<string, string> = {
  AL: "Albanien",
  AM: "Armenien",
  BA: "Bosnien und Herzegowina",
  CH: "Schweiz",
  FO: "Färöer",
  GE: "Georgien",
  IL: "Israel",
  IS: "Island",
  KO: "Kosovo",
  MD: "Moldawien",
  ME: "Montenegro",
  MK: "Nordmazedonien",
  NO: "Norwegen",
  RS: "Serbien",
  TN: "Tunesien",
  TR: "Türkei",
  UA: "Ukraine",
  UK: "Vereinigtes Königreich",
};

/** Weitere globale Länder (nicht EU/assoziiert) */
export const GLOBAL_COUNTRIES: Record<string, string> = {
  US: "Vereinigte Staaten",
  CN: "China",
  JP: "Japan",
  KR: "Südkorea",
  IN: "Indien",
  BR: "Brasilien",
  CA: "Kanada",
  AU: "Australien",
  TW: "Taiwan",
  SG: "Singapur",
  RU: "Russland",
  ZA: "Südafrika",
  MX: "Mexiko",
  GB: "Vereinigtes Königreich",
};

/** Alle Länder (EU-27 + assoziiert) */
export const ALL_COUNTRIES: Record<string, string> = {
  ...EU_COUNTRIES,
  ...ASSOCIATED_COUNTRIES,
};

/** Vollständiges Länder-Lookup (EU + assoziiert + global) */
export const COUNTRY_NAMES: Record<string, string> = {
  ...EU_COUNTRIES,
  ...ASSOCIATED_COUNTRIES,
  ...GLOBAL_COUNTRIES,
};

/**
 * Gibt den deutschen Namen für einen Ländercode zurück.
 * Falls unbekannt, wird der Code selbst zurückgegeben.
 */
export function getCountryName(code: string): string {
  return COUNTRY_NAMES[code.toUpperCase()] ?? code;
}
