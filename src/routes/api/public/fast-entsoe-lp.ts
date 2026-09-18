import { createFileRoute } from "@tanstack/react-router";

/**
 * Live 2-node LP for a fast-screened border (Step 2 of the ENTSO-E fast
 * screening ladder). Reads the cached screening output (Step 1) and returns
 * the decision-matrix scenarios: cable_500 / cable_1000 / battery_200 /
 * battery_100 / co_opt. Public GET; computation is cheap and stateless.
 */
export const Route = createFileRoute("/api/public/fast-entsoe-lp")({
  server: {
    handlers: {
      GET: async ({ request }) => {
        const url = new URL(request.url);
        const border = url.searchParams.get("border");
        const month = (url.searchParams.get("month") ?? "2026-08") as "2026-01" | "2026-08";
        if (!border) return Response.json({ error: "missing border" }, { status: 400 });

        const { fastEntsoeLp } = await import("@/lib/fast-entsoe-lp.server");
        const result = await fastEntsoeLp(border, month);
        if ("error" in result) return Response.json(result, { status: 404 });
        return Response.json(result);
      },
    },
  },
});
