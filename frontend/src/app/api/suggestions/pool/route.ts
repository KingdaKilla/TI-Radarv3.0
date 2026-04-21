/* ──────────────────────────────────────────────
 * TI-Radar v3.6.7 -- API Proxy: /api/suggestions/pool
 * Liefert die komplette kuratierte Technologie-Whitelist
 * fuer die Frontend-Validierung der Technologie-Eingabe.
 * ────────────────────────────────────────────── */

import { NextResponse } from "next/server";

const INTERNAL_API_URL =
  process.env.INTERNAL_API_URL || "http://localhost:8000";

export async function GET() {
  try {
    const res = await fetch(`${INTERNAL_API_URL}/api/v1/suggestions/pool`, {
      method: "GET",
    });

    if (!res.ok) {
      const errorText = await res
        .text()
        .catch(() => "Unbekannter Backend-Fehler");
      return NextResponse.json({ error: errorText }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Interner Proxy-Fehler";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
