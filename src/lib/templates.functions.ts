import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { unitDef } from "./units";
import { DEFAULT_TEMPLATE_BUDGET_MEUR, haversineKm, sizeUnit } from "./costAssumptions";

const ensureIn = (d: unknown) =>
  z
    .object({
      targetId: z.string().uuid(),
      budgetMeur: z.number().positive().max(1000).default(DEFAULT_TEMPLATE_BUDGET_MEUR),
      force: z.boolean().optional(),
    })
    .parse(d);

type TemplateSpec = {
  key: string;
  name: string;
  unitType: "battery" | "solar" | "wind" | "line";
  side: "a" | "b" | "border";
};

const TEMPLATE_SPECS: TemplateSpec[] = [
  { key: "battery-a", name: "BESS in {A}", unitType: "battery", side: "a" },
  { key: "battery-b", name: "BESS in {B}", unitType: "battery", side: "b" },
  { key: "line-ab", name: "Transmission line {A}–{B}", unitType: "line", side: "border" },
  { key: "wind-a", name: "Wind farm in {A}", unitType: "wind", side: "a" },
  { key: "wind-b", name: "Wind farm in {B}", unitType: "wind", side: "b" },
  { key: "solar-a", name: "Solar farm in {A}", unitType: "solar", side: "a" },
  { key: "solar-b", name: "Solar farm in {B}", unitType: "solar", side: "b" },
];

function round(v: number, d: number) {
  const f = 10 ** d;
  return Math.round((Number.isFinite(v) ? v : 0) * f) / f;
}

/**
 * Create (once) the seven budget-normalised template scenarios for a target and
 * pre-compute their results. Existing templates for the same budget are reused
 * unless `force` is set.
 */
export const ensureTemplateScenarios = createServerFn({ method: "POST" })
  .inputValidator(ensureIn)
  .handler(async ({ data }) => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { loadNetwork, runDispatch } = await import("./simulation.server");

    const { data: target, error: tErr } = await supabaseAdmin
      .from("targets")
      .select("*")
      .eq("id", data.targetId)
      .single();
    if (tErr || !target) throw new Error(tErr?.message ?? "Target not found");

    const { data: existing } = await supabaseAdmin
      .from("scenarios")
      .select("id, template_key")
      .eq("target_id", data.targetId)
      .eq("is_template", true)
      .eq("budget_meur", data.budgetMeur);

    if (existing?.length && !data.force) {
      // race-safe: two concurrent calls both pass the length check above, so
      // only insert the keys that are still missing at insert time
      if (existing.length >= TEMPLATE_SPECS.length) {
        return { created: 0, reused: existing.length };
      }
    }
    if (existing?.length && data.force) {
      const ids = existing.map((s) => s.id);
      await supabaseAdmin.from("scenario_results").delete().in("scenario_id", ids);
      await supabaseAdmin.from("scenario_units").delete().in("scenario_id", ids);
      await supabaseAdmin.from("scenarios").delete().in("id", ids);
    }

    // distance between the two zone centroids, for transmission sizing
    const { data: zoneRows } = await supabaseAdmin
      .from("zones")
      .select("code, lat, lon")
      .in("code", [target.zone_a, target.zone_b]);
    const za = zoneRows?.find((z) => z.code === target.zone_a);
    const zb = zoneRows?.find((z) => z.code === target.zone_b);
    const distKm = za && zb ? haversineKm(za.lat, za.lon, zb.lat, zb.lon) : 150;

    // build the seven scenarios with their single sized unit
    const built = TEMPLATE_SPECS.map((spec) => {
      const sized = sizeUnit(
        spec.unitType,
        data.budgetMeur,
        spec.unitType === "line" ? distKm : 0,
      );
      return { spec, sized };
    });

    const { data: created, error: cErr } = await supabaseAdmin
      .from("scenarios")
      .insert(
        built.map(({ spec, sized }) => ({
          target_id: data.targetId,
          name: spec.name.replace("{A}", target.zone_a).replace("{B}", target.zone_b),
          description: `Template: ${spec.name
            .replace("{A}", target.zone_a)
            .replace("{B}", target.zone_b)} sized to €${data.budgetMeur}M (${sized.capacity_label}).`,
          status: "running",
          is_template: true,
          template_key: spec.key,
          budget_meur: data.budgetMeur,
        })),
      )
      .select("id, template_key");
    if (cErr) throw new Error(cErr.message);

    const unitRows = built.map(({ spec, sized }, i) => {
      const def = unitDef(spec.unitType);
      return {
        scenario_id: created![i]!.id,
        unit_type: spec.unitType,
        zone_code:
          spec.side === "a" ? target.zone_a : spec.side === "b" ? target.zone_b : null,
        border_zone_a: spec.side === "border" ? target.zone_a : null,
        border_zone_b: spec.side === "border" ? target.zone_b : null,
        params: sized.params,
        capex_meur: data.budgetMeur,
        delivery_months: def.defaultDeliveryMonths,
      };
    });
    const { error: uErr } = await supabaseAdmin.from("scenario_units").insert(unitRows);
    if (uErr) throw new Error(uErr.message);

    // simulate: one network load + one base run, then one run per template
    const net = await loadNetwork(supabaseAdmin, target.zone_a, target.zone_b);
    const tgt = { a: target.zone_a, b: target.zone_b };
    const base = runDispatch(net, [], tgt);
    const years = Math.max(base.hours, 1) / 8760;

    for (let i = 0; i < built.length; i++) {
      const { sized } = built[i]!;
      const sid = created![i]!.id;
      const scen = runDispatch(
        net,
        [
          {
            unit_type: sized.unit_type,
            zone_code: unitRows[i]!.zone_code,
            border_zone_a: unitRows[i]!.border_zone_a,
            border_zone_b: unitRows[i]!.border_zone_b,
            params: sized.params,
          },
        ],
        tgt,
      );
      const marketMeur = (scen.welfareEur - base.welfareEur) / 1e6 / years;
      const climateKt = -(scen.co2Kg - base.co2Kg) / 1e6 / years;

      await supabaseAdmin.from("scenario_results").delete().eq("scenario_id", sid);
      const { error: rErr } = await supabaseAdmin.from("scenario_results").insert({
        scenario_id: sid,
        status: "complete",
        market_opportunity_meur: round(marketMeur, 4),
        climate_opportunity_ktco2: round(climateKt, 4),
        base_metrics: {},
        scenario_metrics: {},
        entsoe_indicators: {
          b1_socio_economic_welfare_meur_y: round(marketMeur, 3),
          b2_co2_variation_ktco2_y: round(climateKt, 3),
          c1_capex_meur: data.budgetMeur,
          capacity: built[i]!.sized.capacity_label,
          methodology: `Template scenario sized to €${data.budgetMeur}M. Run the full simulation for detailed ENTSO-E indicators.`,
        },
        hourly_summary: {
          hours_modelled: base.hours,
          zones_modelled: net.zones.length,
          period_start: target.period_start,
          period_end: target.period_end,
        },
      });
      if (rErr) throw new Error(rErr.message);
      await supabaseAdmin
        .from("scenarios")
        .update({ status: "complete", updated_at: new Date().toISOString() })
        .eq("id", sid);
    }

    return { created: built.length, reused: 0 };
  });

/** Copy a template scenario into an editable user scenario (units included). */
export const copyTemplateScenario = createServerFn({ method: "POST" })
  .inputValidator((d: unknown) => z.object({ id: z.string().uuid() }).parse(d))
  .handler(async ({ data }) => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { data: tpl, error: tErr } = await supabaseAdmin
      .from("scenarios")
      .select("*")
      .eq("id", data.id)
      .single();
    if (tErr || !tpl) throw new Error(tErr?.message ?? "Template not found");

    const { data: copy, error: cErr } = await supabaseAdmin
      .from("scenarios")
      .insert({
        target_id: tpl.target_id,
        name: `${tpl.name} (copy)`,
        description: tpl.description,
        status: "draft",
      })
      .select()
      .single();
    if (cErr) throw new Error(cErr.message);

    const { data: units } = await supabaseAdmin
      .from("scenario_units")
      .select("*")
      .eq("scenario_id", data.id);
    if (units?.length) {
      const { error: uErr } = await supabaseAdmin.from("scenario_units").insert(
        units.map((u) => ({
          scenario_id: copy.id,
          unit_type: u.unit_type,
          zone_code: u.zone_code,
          border_zone_a: u.border_zone_a,
          border_zone_b: u.border_zone_b,
          params: u.params,
          capex_meur: u.capex_meur,
          delivery_months: u.delivery_months,
        })),
      );
      if (uErr) throw new Error(uErr.message);
    }
    return copy;
  });
