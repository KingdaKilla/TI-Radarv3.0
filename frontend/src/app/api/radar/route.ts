/* ──────────────────────────────────────────────
 * TI-Radar v3 -- API Proxy: /api/radar
 * Proxies POST requests to the FastAPI backend
 * or returns mock data when use_mock is set
 * ────────────────────────────────────────────── */

import { NextRequest, NextResponse } from "next/server";
import { readFile } from "fs/promises";
import path from "path";

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

    // Mock mode: return pre-captured JSON response
    if (body.use_mock) {
      try {
        const mockPath = path.join(process.cwd(), "public", "mock", "quantum_computing.json");
        const mockData = await readFile(mockPath, "utf-8");
        const parsed = JSON.parse(mockData);
        // Override technology name to match what the user typed
        if (parsed.technology) parsed.technology = body.technology;
        return NextResponse.json(parsed);
      } catch {
        return NextResponse.json(
          { error: "Mock-Daten nicht gefunden. Datei: public/mock/quantum_computing.json" },
          { status: 404 },
        );
      }
    }

    // Live mode: forward to backend
    const apiKey = process.env.INTERNAL_API_KEY || "";
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (apiKey) headers["X-API-Key"] = apiKey;

    const res = await fetch(`${INTERNAL_API_URL}/api/v1/radar`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });

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
