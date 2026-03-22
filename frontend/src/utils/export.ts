/* ──────────────────────────────────────────────
 * TI-Radar v2 -- Client-Side CSV Export
 * Generates and triggers download of CSV files
 * ────────────────────────────────────────────── */

/**
 * Erzeugt einen CSV-String aus Header-Zeile und Datenzeilen.
 * Felder mit Semikolon, Anführungszeichen oder Zeilenumbrüchen
 * werden korrekt escaped (RFC 4180 kompatibel).
 *
 * Verwendet Semikolon als Trennzeichen (DE-Standard für Excel).
 */
export function generateCsv(
  headers: string[],
  rows: (string | number)[][]
): string {
  const escape = (val: string | number): string => {
    const str = String(val);
    if (str.includes(";") || str.includes('"') || str.includes("\n")) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  };

  const headerLine = headers.map(escape).join(";");
  const dataLines = rows.map((row) => row.map(escape).join(";"));

  // BOM für korrekte UTF-8-Erkennung in Excel
  return "\uFEFF" + [headerLine, ...dataLines].join("\n");
}

/**
 * Erzeugt eine CSV-Datei und triggert den Download im Browser.
 */
export function downloadCsv(
  filename: string,
  headers: string[],
  rows: (string | number)[][]
): void {
  const csv = generateCsv(headers, rows);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);

  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename.endsWith(".csv") ? filename : `${filename}.csv`;
  document.body.appendChild(anchor);
  anchor.click();

  // Cleanup
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}
