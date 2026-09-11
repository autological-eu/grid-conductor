import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/api/water-signals")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        try {
          const body = await request.json();
          const { handleWaterSignals } = await import("@/lib/waterSignals.server");
          const result = await handleWaterSignals(body);
          return Response.json(result);
        } catch (e) {
          return Response.json({ error: e instanceof Error ? e.message : String(e) }, { status: 500 });
        }
      },
    },
  },
});
