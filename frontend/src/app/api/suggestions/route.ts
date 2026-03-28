/* ──────────────────────────────────────────────
 * TI-Radar v3 -- API Proxy: /api/suggestions
 * Proxies GET requests for autocomplete
 * suggestions to the FastAPI backend
 * ────────────────────────────────────────────── */

import { NextRequest, NextResponse } from "next/server";

const INTERNAL_API_URL =
  process.env.INTERNAL_API_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const q = searchParams.get("q") ?? "";

    if (q.trim().length < 2) {
      return NextResponse.json([]);
    }

    const res = await fetch(
      `${INTERNAL_API_URL}/api/v1/suggestions?q=${encodeURIComponent(q)}`,
      { method: "GET" }
    );

    if (!res.ok) {
      const errorText = await res.text().catch(() => "Unbekannter Backend-Fehler");
      return NextResponse.json(
        { error: errorText },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Interner Proxy-Fehler";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
