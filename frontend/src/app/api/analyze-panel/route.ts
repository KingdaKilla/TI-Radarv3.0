/* ──────────────────────────────────────────────
 * TI-Radar v4 -- API Proxy: /api/analyze-panel
 * Proxies POST requests to the FastAPI analyze-panel endpoint
 * ────────────────────────────────────────────── */

import { NextRequest, NextResponse } from "next/server";

const INTERNAL_API_URL =
  process.env.INTERNAL_API_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    // S-15: Reject payloads exceeding 1 MB
    const contentLength = parseInt(request.headers.get("content-length") || "0", 10);
    if (contentLength > 1_048_576) {
      return Response.json({ error: "Request too large" }, { status: 413 });
    }

    const body = await request.json();

    // Forward to backend
    const apiKey = process.env.INTERNAL_API_KEY || "";
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (apiKey) headers["X-API-Key"] = apiKey;

    const res = await fetch(`${INTERNAL_API_URL}/api/v1/analyze-panel`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const errorText = await res.text().catch(() => "Unbekannter Backend-Fehler");
      return NextResponse.json(
        { error: errorText },
        { status: res.status },
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
