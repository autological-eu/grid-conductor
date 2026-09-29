import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { unitDef } from "./units";

const idIn = (data: unknown) => z.object({ id: z.string().uuid() }).parse(data);

export const listScenarios = createServerFn({ method: "GET" })
  .inputValidator((d: unknown) => z.object({ targetId: z.string().uuid() }).parse(d))
  .handler(async ({ data }) => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const [{ data: scenarios }, { data: units }, { data: results }] = await Promise.all([
      supabaseAdmin
        .from("scenarios")
        .select("*")
        .eq("target_id", data.targetId)
        .order("created_at"),
      supabaseAdmin.from("scenario_units").select("*").order("created_at"),
      supabaseAdmin.from("scenario_results").select("*"),
    ]);
    const ids = new Set((scenarios ?? []).map((s) => s.id));
    return (scenarios ?? []).map((s) => ({
      ...s,
      units: (units ?? []).filter((u) => u.scenario_id === s.id),
      result: (results ?? []).find((r) => r.scenario_id === s.id) ?? null,
      _ok: ids.size,
    }));
  });

export const createScenario = createServerFn({ method: "POST" })
  .inputValidator((d: unknown) =>
    z
      .object({
        targetId: z.string().uuid(),
        name: z.string().min(1).max(120),
        description: z.string().max(500).optional(),
      })
      .parse(d),
  )
  .handler(async ({ data }) => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { data: row, error } = await supabaseAdmin
      .from("scenarios")
      .insert({
        target_id: data.targetId,
        name: data.name,
        description: data.description ?? null,
      })
      .select()
      .single();
    if (error) throw new Error(error.message);
    return row;
  });

export const deleteScenario = createServerFn({ method: "POST" })
  .inputValidator(idIn)
  .handler(async ({ data }) => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    await supabaseAdmin.from("scenario_results").delete().eq("scenario_id", data.id);
    await supabaseAdmin.from("scenario_units").delete().eq("scenario_id", data.id);
    const { error } = await supabaseAdmin.from("scenarios").delete().eq("id", data.id);
    if (error) throw new Error(error.message);
    return { ok: true };
  });

export const addUnit = createServerFn({ method: "POST" })
  .inputValidator((d: unknown) =>
    z
      .object({
        scenarioId: z.string().uuid(),
        unitType: z.enum(["battery", "solar", "wind", "line", "demand_response"]),
        zoneCode: z.string().nullable().optional(),
        borderZoneA: z.string().nullable().optional(),
        borderZoneB: z.string().nullable().optional(),
        params: z.record(z.string(), z.number()).optional(),
      })
      .parse(d),
  )
  .handler(async ({ data }) => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const def = unitDef(data.unitType);
    const params = data.params ?? def.defaults;
    const { data: row, error } = await supabaseAdmin
      .from("scenario_units")
      .insert({
        scenario_id: data.scenarioId,
        unit_type: data.unitType,
        zone_code: data.zoneCode ?? null,
        border_zone_a: data.borderZoneA ?? null,
        border_zone_b: data.borderZoneB ?? null,
        params,
        capex_meur: def.defaultCapexMeur,
        delivery_months: def.defaultDeliveryMonths,
      })
      .select()
      .single();
    if (error) throw new Error(error.message);
    return row;
  });

export const updateUnit = createServerFn({ method: "POST" })
  .inputValidator((d: unknown) =>
    z
      .object({
        id: z.string().uuid(),
        params: z.record(z.string(), z.number()).optional(),
        capexMeur: z.number().min(0).optional(),
        deliveryMonths: z.number().int().min(0).max(240).optional(),
        zoneCode: z.string().nullable().optional(),
      })
      .parse(d),
  )
  .handler(async ({ data }) => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const patch: Record<string, unknown> = {};
    if (data.params) patch["params"] = data.params;
    if (data.capexMeur !== undefined) patch["capex_meur"] = data.capexMeur;
    if (data.deliveryMonths !== undefined) patch["delivery_months"] = data.deliveryMonths;
    if (data.zoneCode !== undefined) patch["zone_code"] = data.zoneCode;
    const { error } = await supabaseAdmin
      .from("scenario_units")
      .update(patch as never)
      .eq("id", data.id);
    if (error) throw new Error(error.message);
    return { ok: true };
  });

export const deleteUnit = createServerFn({ method: "POST" })
  .inputValidator(idIn)
  .handler(async ({ data }) => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { error } = await supabaseAdmin.from("scenario_units").delete().eq("id", data.id);
    if (error) throw new Error(error.message);
    return { ok: true };
  });

/** Run the network model for a scenario and store results + ENTSO-E CBA indicators. */
export const runScenario = createServerFn({ method: "POST" })
  .inputValidator(idIn)
  .handler(async ({ data }) => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { loadNetwork, runDispatch } = await import("./simulation.server");

    const { data: scenario, error: sErr } = await supabaseAdmin
      .from("scenarios")
      .select("*, targets:target_id (*)")
      .eq("id", data.id)
      .single();
    if (sErr || !scenario) throw new Error(sErr?.message ?? "Scenario not found");
    const target = scenario.targets as unknown as {
      zone_a: string;
      zone_b: string;
      period_start: string;
      period_end: string;
    };

    const { data: units } = await supabaseAdmin
      .from("scenario_units")
      .select("*")
      .eq("scenario_id", data.id);

    await supabaseAdmin.from("scenarios").update({ status: "running" }).eq("id", data.id);

    const net = await loadNetwork(target.zone_a, target.zone_b);
    const tgt = { a: target.zone_a, b: target.zone_b };
    const base = runDispatch(net, [], tgt);
    const scen = runDispatch(
      net,
      (units ?? []).map((u) => ({
        unit_type: u.unit_type,
        zone_code: u.zone_code,
        border_zone_a: u.border_zone_a,
        border_zone_b: u.border_zone_b,
        params: (u.params ?? {}) as Record<string, number>,
      })),
      tgt,
    );

    const years = Math.max(base.hours, 1) / 8760;
    const marketMeur = (scen.welfareEur - base.welfareEur) / 1e6 / years;
    const climateKt = -(scen.co2Kg - base.co2Kg) / 1e6 / years;

    const capex = (units ?? []).reduce((s, u) => s + Number(u.capex_meur ?? 0), 0);
    const delivery = (units ?? []).reduce((m, u) => Math.max(m, Number(u.delivery_months ?? 0)), 0);
    const lifetimeYears = 25;
    const npvMeur = marketMeur * lifetimeYears - capex;
    const bcRatio = capex > 0 ? (marketMeur * lifetimeYears) / capex : null;
    const paybackYears = marketMeur > 0 ? capex / marketMeur : null;

    const entsoe = {
      b1_socio_economic_welfare_meur_y: round(marketMeur, 3),
      b2_co2_variation_ktco2_y: round(climateKt, 3),
      b3_res_integration_gwh_y: round(
        (scen.extraTransferMwh - base.extraTransferMwh) / 1000 / years,
        2,
      ),
      b4_losses_variation_gwh_y: round(
        ((scen.borderFlowMwh - base.borderFlowMwh) * 0.02) / 1000 / years,
        3,
      ),
      b5_security_of_supply_congested_hours_avoided: Math.round(
        (base.congestedHours - scen.congestedHours) / years,
      ),
      b6_flexibility_avg_spread_reduction_eur_mwh: round(
        base.avgSpreadEurMwh - scen.avgSpreadEurMwh,
        3,
      ),
      b7_transfer_capability_mwh_y: round((scen.borderFlowMwh - base.borderFlowMwh) / years, 1),
      b8_congestion_rent_variation_meur_y: round(
        (scen.congestionRentEur - base.congestionRentEur) / 1e6 / years,
        3,
      ),
      b9_price_convergence_hours_gained: Math.round(
        (scen.convergedHours - base.convergedHours) / years,
      ),
      c1_capex_meur: round(capex, 2),
      c2_delivery_months: delivery,
      npv_25y_meur: round(npvMeur, 2),
      benefit_cost_ratio: bcRatio == null ? null : round(bcRatio, 2),
      simple_payback_years: paybackYears == null ? null : round(paybackYears, 1),
      methodology:
        "ENTSO-E CBA 4.0 style indicators. Hourly market clearing follows the ENTSO-E single day-ahead coupling (Euphemia) ATC algorithm: welfare maximisation with balanced net positions, ATC limits, price convergence where borders are free and price splitting only across saturated borders.",
    };

    const payload = {
      scenario_id: data.id,
      status: "complete",
      market_opportunity_meur: round(marketMeur, 4),
      climate_opportunity_ktco2: round(climateKt, 4),
      base_metrics: jsonify(base),
      scenario_metrics: jsonify(scen),
      entsoe_indicators: entsoe,
      hourly_summary: {
        hours_modelled: base.hours,
        zones_modelled: net.zones.length,
        borders_modelled: net.edges.length,
        period_start: target.period_start,
        period_end: target.period_end,
      },
    };

    await supabaseAdmin.from("scenario_results").delete().eq("scenario_id", data.id);
    const { error: rErr } = await supabaseAdmin.from("scenario_results").insert(payload);
    if (rErr) throw new Error(rErr.message);

    await supabaseAdmin
      .from("scenarios")
      .update({ status: "complete", updated_at: new Date().toISOString() })
      .eq("id", data.id);

    // Model validation: how closely the base run reproduces observed flows/prices.
    await supabaseAdmin.from("model_validation").insert({
      period_start: target.period_start,
      period_end: target.period_end,
      metrics: {
        price_mae_eur_mwh: round(base.priceMae, 3),
        border_flow_mae_mw: round(base.flowMae, 1),
        flow_direction_accuracy: round(base.directionAccuracy, 4),
        price_convergence_share: round(base.convergedHours / Math.max(base.hours, 1), 4),
        adverse_flow_hours: base.adverseFlowHours,
        congestion_rent_meur: round(base.congestionRentEur / 1e6, 3),
        target_rent_meur: round(base.targetRentEur / 1e6, 3),
        kkt_dual_residual_eur_mwh: round(base.maxDualResidualEurMwh, 4),
        solver_iterations: base.iterations,
        hours: base.hours,
        zones: net.zones.length,
      },
      passed:
        base.directionAccuracy > 0.8 &&
        base.priceMae < 10 &&
        base.adverseFlowHours === 0 &&
        base.convergedHours === base.hours &&
        base.maxDualResidualEurMwh <= 0.01,
    });

    return payload;
  });

function round(v: number, d: number) {
  const f = 10 ** d;
  return Math.round((Number.isFinite(v) ? v : 0) * f) / f;
}

function jsonify(r: Record<string, number>) {
  return Object.fromEntries(Object.entries(r).map(([k, v]) => [k, round(v, 3)]));
}
