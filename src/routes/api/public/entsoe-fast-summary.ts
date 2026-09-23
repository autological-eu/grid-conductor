import path from "node:path";
import { createFileRoute } from "@tanstack/react-router";

/**
 * Step-1 -> EuropeMap summary (continents/zone + congested-border targets).
 * Reads the cached screening output (Step 1) and returns the `ZoneSummary[]` /
 * `TargetRow[]` contract the EuropeMap workbench renders: per-zone lat/lon,
 * name, carbon estimate, plus directed bordered targets with market and
 * climate loss columns. Public GET; stateless.
 */
export const Route = createFileRoute("/api/public/entsoe-fast-summary")({
  server: {
    handlers: {
      GET: async () => {
        const { loadStep1Summary } = await import("@/lib/step1.server");
        const p = path.join(process.cwd(), "public", "research", "entsoe-fast-targets.json");
        return Response.json(loadStep1Summary(p));
      },
    },
  },
});
