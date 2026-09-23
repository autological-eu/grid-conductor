import { createServerFn } from "@tanstack/react-start";

/**
 * Step-1 -> workbench map. Replaces the Supabase `zone_summary` /
 * `targets` reads with the cached fast-entsoe screening output
 * (`public/research/entsoe-fast-targets.json`), rendered through the same
 * `ZoneSummary[]` / `TargetRow[]` contract the EuropeMap workbench consumes.
 */
export const listFastSummary = createServerFn({ method: "GET" }).handler(async () => {
  const { loadStep1SummaryCwd } = await import("./step1.server");
  return loadStep1SummaryCwd();
});
