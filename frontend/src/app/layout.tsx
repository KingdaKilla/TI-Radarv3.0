"use client";

import { Inter } from "next/font/google";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
// DevTools nur im Development laden (Button unten rechts entfernt)
import { useState } from "react";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 60 * 1000, // 5 Minuten
            retry: 2,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <html lang="de" className={`${inter.variable} dark`} suppressHydrationWarning>
      <head>
        <title>TI-Radar v3 | Technologie-Intelligence Dashboard</title>
        <meta
          name="description"
          content="Technologie-Intelligence Radar -- Analyse von Patenten, Forschungsprojekten und Marktdaten"
        />
      </head>
      <body className="min-h-screen font-sans">
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      </body>
    </html>
  );
}
