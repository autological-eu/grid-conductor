import { z } from "zod";
import { unitDef } from "./units";
import { entsoeZoneMeta } from "./entsoeZones";
import { loadStep1Summary } from "./step1";

const idIn = (data: unknown) => z.object({ id: z.string().uuid() }).parse(data);

/** Scenario/year window used for all fast-entsoe workbench targets. */
const PERIOD_START = "2025-01-01";
const PERIOD_END = "2025-12-31";

/** Keep validation at the service boundary without a network/server abstraction. */
function browserFunction<T, R>(
  validate: (data: unknown) => T,
  handler: (input: { data: T }) => Promise<R>,
) {
  return async (input?: { data: T }): Promise<R> => handler({ data: validate(input?.data) });
}

export const listScenarios = browserFunction(
  (d: unknown) => z.object({ targetId: z.string().min(1) }).parse(d),
  async ({ data }) => {
    const { listScenariosForTarget } = await import("./workbench");
    return listScenariosForTarget(data.targetId);
  },
);

export const createScenario = browserFunction(
  (d: unknown) =>
    z
      .object({
        targetId: z.string().min(1),
        name: z.string().min(1).max(120),
        description: z.string().max(500).optional(),
      })
      .parse(d),
  async ({ data }) => {
    const { createScenario } = await import("./workbench");

    // Fast-entsoe targets are directed borders ("FR>IT-North"); snapshot the
    // zone pair and year window onto the scenario so runs never need a lookup.
    let zoneA = data.targetId.split(">")[0] ?? data.targetId;
    let zoneB = data.targetId.split(">")[1] ?? "";
    const t = (await loadStep1Summary()).targets.find((x) => x.id === data.targetId);
    if (!t) throw new Error("This bottleneck is not in the published screening dataset.");
    zoneA = t.zone_a;
    zoneB = t.zone_b;

    return createScenario({
      targetId: data.targetId,
      name: data.name,
      description: data.description,
      zoneA,
      zoneB,
      periodStart: PERIOD_START,
      periodEnd: PERIOD_END,
    });
  },
);

export const deleteScenario = browserFunction(idIn, async ({ data }) => {
  const { deleteScenario } = await import("./workbench");
  await deleteScenario(data.id);
  return { ok: true };
});

export const addUnit = browserFunction(
  (d: unknown) =>
    z
      .object({
        scenarioId: z.string().uuid(),
        unitType: z.enum(["battery", "line"]),
        zoneCode: z.string().nullable().optional(),
        borderZoneA: z.string().nullable().optional(),
        borderZoneB: z.string().nullable().optional(),
        params: z.record(z.string(), z.number().finite().min(0)).optional(),
      })
      .parse(d),
  async ({ data }) => {
    const { insertUnit } = await import("./workbench");
    const def = unitDef(data.unitType);
    const params = { ...def.defaults, ...data.params };
    if (data.unitType === "battery" && (params["efficiency"] ?? 0) > 1)
      throw new Error("Battery efficiency must be between 0 and 1.");
    const { getScenarioWithDetails } = await import("./workbench");
    const scenario = await getScenarioWithDetails(data.scenarioId);
    if (
      data.unitType === "battery" &&
      data.zoneCode &&
      ![scenario.zone_a, scenario.zone_b].includes(data.zoneCode)
    )
      throw new Error("Place the battery in one of this bottleneck's zones.");
    if (
      data.unitType === "line" &&
      (data.borderZoneA !== scenario.zone_a || data.borderZoneB !== scenario.zone_b) &&
      (data.borderZoneA !== scenario.zone_b || data.borderZoneB !== scenario.zone_a)
    )
      throw new Error("Place the line on the selected bottleneck.");
    return insertUnit({
      scenarioId: data.scenarioId,
      unitType: data.unitType,
      zoneCode: data.zoneCode ?? null,
      borderZoneA: data.borderZoneA ?? null,
      borderZoneB: data.borderZoneB ?? null,
      params,
      capexMeur: def.defaultCapexMeur,
      deliveryMonths: def.defaultDeliveryMonths,
    });
  },
);

export const updateUnit = browserFunction(
  (d: unknown) =>
    z
      .object({
        id: z.string().uuid(),
        params: z.record(z.string(), z.number().finite().min(0)).optional(),
        capexMeur: z.number().min(0).optional(),
        deliveryMonths: z.number().int().min(0).max(240).optional(),
        zoneCode: z.string().nullable().optional(),
      })
      .parse(d),
  async ({ data }) => {
    const { updateUnit } = await import("./workbench");
    if ((data.params?.["efficiency"] ?? 0) > 1)
      throw new Error("Battery efficiency must be between 0 and 1.");
    await updateUnit(data.id, {
      params: data.params,
      capexMeur: data.capexMeur,
      deliveryMonths: data.deliveryMonths,
      zoneCode: data.zoneCode,
    });
    return { ok: true };
  },
);

export const deleteUnit = browserFunction(idIn, async ({ data }) => {
  const { deleteUnit } = await import("./workbench");
  await deleteUnit(data.id);
  return { ok: true };
});

/** Run the fast 2-node LP model for a scenario and store results. */
export const runScenario = browserFunction(idIn, async ({ data }) => {
  const { getScenarioWithDetails, saveEvaluation } = await import("./workbench");
  const { solveFromUnits } = await import("./fast-entsoe-lp");

  const scenario = await getScenarioWithDetails(data.id);

  const border = `${scenario.zone_a}>${scenario.zone_b}`;
  const unitLikes = scenario.units.map((u) => ({
    unit_type: u.unit_type,
    zone_code: u.zone_code,
    border_zone_a: u.border_zone_a,
    border_zone_b: u.border_zone_b,
    params: u.params,
  }));

  const result = await solveFromUnits(border, unitLikes);
  if ("error" in result) throw new Error(result.error);

  // Market opportunity is the LP's gross annual welfare gain over the full
  // 2025 year row (no x12 representative-month factor), capped at the
  // border's deadweight-loss estimate — a scenario can never claim more than
  // the map's market opportunity. The 2-node LP has no CI signal, so the
  // climate side mirrors the Step-1 adapter's locally-estimated "released
  // energy x carbon contrast" quantity from the target's own zone carbon
  // estimates.
  const marketMeur = result.annual_welfare_gain_meur;
  const carbonDelta = Math.abs(
    entsoeZoneMeta(scenario.zone_a).carbon_g_per_kwh -
      entsoeZoneMeta(scenario.zone_b).carbon_g_per_kwh,
  );
  const climateKt =
    result.avg_spread_eur_mwh > 0 ? (marketMeur * carbonDelta) / result.avg_spread_eur_mwh : 0;

  const capex = scenario.units.reduce((s, u) => s + Number(u.capex_meur ?? 0), 0);
  const delivery = scenario.units.reduce((m, u) => Math.max(m, Number(u.delivery_months ?? 0)), 0);
  const lifetimeYears = 25;
  const npvMeur = marketMeur * lifetimeYears - capex;
  const bcRatio = capex > 0 ? (marketMeur * lifetimeYears) / capex : null;
  const paybackYears = marketMeur > 0 ? capex / marketMeur : null;

  const entsoe = {
    b1_socio_economic_welfare_meur_y: round(marketMeur, 3),
    b2_co2_variation_ktco2_y: round(climateKt, 3),
    c1_capex_meur: round(capex, 2),
    c2_delivery_months: delivery,
    npv_25y_meur: round(npvMeur, 2),
    benefit_cost_ratio: bcRatio == null ? null : round(bcRatio, 2),
    simple_payback_years: paybackYears == null ? null : round(paybackYears, 1),
    avg_spread_eur_mwh: round(result.avg_spread_eur_mwh, 3),
    shadow_price_ateur_mwh:
      result.shadow_price_ateur_mwh == null ? null : round(result.shadow_price_ateur_mwh, 4),
    methodology:
      "Fast ENTSO-E screening, Step 2: a reduced-form 2-node transport LP over the " +
      `screened border (12-month ENTSO-E 2025 year, annual sum, no x12 ` +
      "representative-month factor). Line units raise the corridor transfer " +
      "limit with an exact trapezoid price response (welfare = spread*q - " +
      "slope*q^2/2, saturating at the border's deadweight loss); battery units " +
      "shift one cycle per day at the average positive spread. Gains are " +
      "capped at the market opportunity. Shadow price recovered by " +
      "finite-difference re-solve. Screening ranks candidates; it is not " +
      "dispatch-grade valuation.",
  };

  const payload = {
    scenario_id: data.id,
    status: "complete",
    created_at: new Date().toISOString(),
    market_opportunity_meur: round(marketMeur, 4),
    climate_opportunity_ktco2: round(climateKt, 4),
    base_metrics: {
      avg_spread_eur_mwh: round(result.avg_spread_eur_mwh, 3),
      congested_hours: round(result.congestion_hours, 1),
      annual_welfare_gain_meur: 0,
      net_annual_surplus_meur: 0,
    },
    scenario_metrics: {
      avg_spread_eur_mwh: round(result.avg_spread_eur_mwh, 3),
      congested_hours: round(result.congestion_hours, 1),
      annual_welfare_gain_meur: round(marketMeur, 3),
      net_annual_surplus_meur: round(marketMeur - capex * 0.08, 3),
    },
    entsoe_indicators: entsoe,
    hourly_summary: {
      hours_modelled: Math.round(result.congestion_hours),
      zones_modelled: 2,
      borders_modelled: 1,
      period_start: scenario.period_start,
      period_end: scenario.period_end,
      months: result.months,
    },
  };

  // LP-derived validation placeholder: the Step-2 LP is a screening aggregate,
  // not a calibrated hourly simulation, so the predeclared Euphemia accuracy
  // gates do not apply. `passed` reflects data availability only.
  await saveEvaluation(data.id, scenario.updated_at, payload, {
    period_start: scenario.period_start,
    period_end: scenario.period_end,
    metrics: {
      avg_spread_eur_mwh: round(result.avg_spread_eur_mwh, 3),
      congestion_hours: round(result.congestion_hours, 1),
      annual_welfare_gain_meur: round(marketMeur, 3),
      screened_months: result.months.length,
      methodology: "fast-entsoe Step-2 LP screening aggregates (not a calibrated hourly model)",
    },
    passed:
      result.avg_spread_eur_mwh > 0 && result.congestion_hours > 0 && result.months.length > 0,
  });

  return payload;
});

/** Latest LP-derived model validation entry (null when nothing ran yet). */
export const getValidation = browserFunction(
  () => undefined,
  async () => {
    const { latestValidation } = await import("./workbench");
    const v = await latestValidation();
    return v
      ? {
          period_start: v.period_start,
          period_end: v.period_end,
          passed: v.passed,
          metrics: v.metrics,
        }
      : null;
  },
);

function round(v: number, d: number) {
  const f = 10 ** d;
  return Math.round((Number.isFinite(v) ? v : 0) * f) / f;
}
