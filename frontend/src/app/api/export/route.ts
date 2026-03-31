/* ──────────────────────────────────────────────
 * TI-Radar v3 -- API Proxy: /api/export
 * Proxies POST export requests (CSV/PDF/Excel)
 * to the FastAPI backend and streams the binary
 * response back to the client
 * ────────────────────────────────────────────── */

import { NextRequest, NextResponse } from "next/server";

const EXPORT_API_URL =
  process.env.EXPORT_API_URL || "http://localhost:8020";

const FORMAT_MIME: Record<string, string> = {
  csv: "text/csv",
  pdf: "application/pdf",
  xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
};

// S-21: Allowlist of accepted export formats — prevents open-format injection
const ALLOWED_FORMATS = new Set(["csv", "pdf", "xlsx"]);

export async function POST(request: NextRequest) {
  try {
    // S-15: Reject payloads exceeding 1 MB before reading the body
    const contentLength = parseInt(request.headers.get("content-length") || "0", 10);
    if (contentLength > 1_048_576) {
      return Response.json({ error: "Request too large" }, { status: 413 });
    }

    const body = await request.json();

    // S-21: Only allow known formats; fall back to csv for anything unexpected
    const format = ALLOWED_FORMATS.has(body.format) ? body.format : "csv";

    const res = await fetch(`${EXPORT_API_URL}/api/v1/export/${format}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const errorText = await res.text().catch(() => "Export fehlgeschlagen");
      return NextResponse.json(
        { error: errorText },
        { status: res.status }
      );
    }

    const buffer = await res.arrayBuffer();
    const mimeType = FORMAT_MIME[format] ?? "application/octet-stream";
    const technology = (body.technology as string) ?? "export";
    const safeFilename = technology.replace(/[^a-zA-Z0-9_-]/g, "-");

    return new NextResponse(buffer, {
      status: 200,
      headers: {
        "Content-Type": mimeType,
        "Content-Disposition": `attachment; filename="ti-radar_${safeFilename}.${format}"`,
      },
    });
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Interner Proxy-Fehler";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
