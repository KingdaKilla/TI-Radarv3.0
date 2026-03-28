import { ImageResponse } from "next/og";

export const size = { width: 32, height: 32 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          fontSize: 18,
          background: "#0a0a0f",
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#c8a846",
          fontWeight: 700,
          borderRadius: 6,
          border: "2px solid #c8a846",
        }}
      >
        TI
      </div>
    ),
    { ...size }
  );
}
