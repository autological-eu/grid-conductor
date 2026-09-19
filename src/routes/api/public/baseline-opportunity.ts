import { createFileRoute } from "@tanstack/react-router";

/**
 * Baseline opportunity dataset (schema v2), bundled from the offline PyPSA-Eur
 * solve. See public/research/pypsa-targets.json for the canonical copy.
 */
export const Route = createFileRoute("/api/public/baseline-opportunity")({
  server: {
    handlers: {
      GET: async () => {
        const { baselineDataset } = await import("@/lib/baseline.server");
        return Response.json(baselineDataset());
      },
    },
  },
});
