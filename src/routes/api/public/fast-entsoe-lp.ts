import { createFileRoute } from "@tanstack/react-router";

/**
 * Live 2-node LP for a fast-screened border (Step 2 of the ENTSO-E fast
 * screening ladder). Reads the cached ANNUAL screening output (Step 1,
 * schema_version 3) and returns the decision-matrix scenarios: cable_500 /
 * cable_1000 / battery_200 / battery_100 / co_opt. Public GET; computation is
 * cheap and stateless.
 */
export const Route = createFileRoute("/api/public/fast-entsoe-lp")({
  server: {
    handlers: {
      GET: async ({ request }) => {
        const url = new URL(request.url);
        const border = url.searchParams.get("border");
        if (!border) return Response.json({ error: "missing border" }, { status: 400 });

        const { fastEntsoeLp } = await import("@/lib/fast-entsoe-lp.server");
        const result = await fastEntsoeLp(border);
        if ("error" in result) return Response.json(result, { status: 404 });
        return Response.json(result);
      },
    },
  },
});
