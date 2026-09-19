import { createServerFn } from "@tanstack/react-start";

export const listZoneSummary = createServerFn({ method: "GET" }).handler(async () => {
  const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
  const { data, error } = await supabaseAdmin.rpc("zone_summary");
  if (error) throw new Error(error.message);
  return (data ?? []) as Array<{
    code: string;
    name: string;
    country_code: string;
    lat: number;
    lon: number;
    avg_carbon_intensity: number | null;
    avg_price: number | null;
    hours: number;
  }>;
});

export const listTargets = createServerFn({ method: "GET" }).handler(async () => {
  const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
  const { baselineDataset, mapToTargetRows, ensureTargetIds } = await import("./baseline.server");

  const report = baselineDataset();
  const { data: zones } = await supabaseAdmin.from("zones").select("code, name, country_code");
  const zoneRows = (zones ?? []).map((z) => ({
    code: z.code,
    name: z.name,
    country_code: z.country_code,
  }));

  await ensureTargetIds(supabaseAdmin, report);

  return mapToTargetRows(report, zoneRows).sort((a, b) => b.market_loss_meur - a.market_loss_meur);
});

export const refreshTargets = createServerFn({ method: "POST" }).handler(async () => {
  return {
    targets: 0,
    note: "Targets are served from the offline PyPSA-Eur baseline solve (research/baseline-manifest.json); the legacy compute_targets RPC no longer drives the map.",
  };
});

/**
 * Overlay official ENTSO-E day-ahead transfer capacity on the top targets, so
 * congestion is measured against published limits where they exist.
 */
export const refreshOfficialCapacity = createServerFn({ method: "POST" }).handler(async () => {
  const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
  const { fetchNtcMw } = await import("./entsoe.server");

  const { data: targets, error } = await supabaseAdmin
    .from("targets")
    .select("id, zone_a, zone_b, period_end, metrics")
    .order("market_loss_meur", { ascending: false })
    .limit(15);
  if (error) throw new Error(error.message);

  let updated = 0;
  for (const t of targets ?? []) {
    const end = new Date(t.period_end);
    const start = new Date(end.getTime() - 7 * 86_400_000);
    const [ab, ba] = await Promise.all([
      fetchNtcMw(t.zone_a, t.zone_b, start, end),
      fetchNtcMw(t.zone_b, t.zone_a, start, end),
    ]);
    if (ab == null && ba == null) continue;
    const metrics = { ...(t.metrics as Record<string, unknown>) };
    if (ab != null) metrics["ntc_ab_mw"] = ab;
    if (ba != null) metrics["ntc_ba_mw"] = ba;
    metrics["ntc_source"] = "ENTSO-E day-ahead NTC";
    await supabaseAdmin
      .from("targets")
      .update({ metrics: metrics as never })
      .eq("id", t.id);
    updated++;
  }
  return { updated, checked: targets?.length ?? 0 };
});

export const getValidation = createServerFn({ method: "GET" }).handler(async () => {
  const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
  const { data } = await supabaseAdmin
    .from("model_validation")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();
  return data;
});
