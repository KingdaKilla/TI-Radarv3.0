import { defineConfig } from "vitest/config";
import path from "node:path";

/* Vitest configuration for TI-Radar v3 frontend.
 * - Only collects tests under src/** (avoids node_modules / .next).
 * - Provides the same `@/*` path alias as tsconfig.json.
 */
export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    exclude: ["node_modules", ".next", "dist"],
    environment: "node",
    globals: false,
    reporters: "default",
    testTimeout: 10_000,
    // Single thread avoids worker-thread / OneDrive-cloud-sync hangs that
    // can occur on macOS when spawning multiple Vitest workers.
    pool: "threads",
    poolOptions: {
      threads: {
        singleThread: true,
        isolate: false,
      },
    },
    fileParallelism: false,
  },
});
