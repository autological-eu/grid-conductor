import { createFileRoute } from "@tanstack/react-router";
import { timingSafeEqual } from "crypto";

/**
 * Daily refresh endpoint, called by a database schedule.
 * Tops up the rolling one-year import window and recomputes targets.
 * Protected by a shared secret stored server-side; safe to re-run.
 */
export const Route = createFileRoute("/api/public/daily-refresh")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const { supabaseAdmin } = await import("@/integrations/supabase/client.server");

        // verify the shared secret against the value stored in app_config
        const provided = request.headers.get("x-refresh-secret") ?? "";
        const { data: cfg } = await supabaseAdmin
          .from("app_config")
          .select("value")
          .eq("key", "daily_refresh_secret")
          .single();
        const expected = cfg?.value ?? "";
        const ok =
          provided.length > 0 &&
          provided.length === expected.length &&
          timingSafeEqual(Buffer.from(provided), Buffer.from(expected));
        if (!ok) return Response.json({ error: "Unauthorized" }, { status: 401 });

        const { planJobs, importBatch } = await import("@/lib/import.server");

        await planJobs();

        // bounded incremental run: a daily run only has ~1 new day per job
        let batches = 0;
        let last: Record<string, unknown> = {};
        for (; batches < 60; batches++) {
          last = (await importBatch({ chunks: 10 })) as Record<string, unknown>;
          if (last["complete"] || last["throttled"] || last["skipped"] === "paused") break;
        }

        const { data: targets, error } = await supabaseAdmin.rpc("compute_targets", {
          min_spread: 1,
          congestion_ratio: 0.98,
          relief_share: 0.1,
        });

        return Response.json({
          ok: true,
          batches,
          importState: last["complete"] ? "complete" : "partial",
          targets: error ? null : ((targets as number) ?? 0),
          targetError: error?.message ?? null,
        });
      },
    },
  },
});
