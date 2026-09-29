import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { unitDef } from "./units";

const idIn = (data: unknown) => z.object({ id: z.string().uuid() }).parse(data);

export const listScenarios = createServerFn({ method: "GET" })
  .inputValidator((d: unknown) => z.object({ targetId: z.string().min(1) }).parse(d))
  .handler(async ({ data }) => {
    const { listScenariosForTarget } = await import("./workbench.server");
    return listScenariosForTarget(data.targetId);
  });

export const createScenario = createServerFn({ method: "POST" })
  .inputValidator((d: unknown) =>
    z
      .object({
        targetId: z.string().min(1),
        name: z.string().min(1).max(120),
        description: z.string().max(500).optional(),
      })
      .parse(d),
  )
  .handler(async ({ data }) => {
    const { createScenario } = await import("./workbench.server");
    const { baselineDataset } = await import("./baseline.server");

    // Snapshot the border and the modelled window onto the scenario so a run
    // never needs a dataset lookup, and so runs stay stable if the published
    // targets are later regenerated for a different period.
    const report = baselineDataset();
    const [zoneA, zoneB] = data.targetId.includes(">")
      ? data.targetId.split(">")
      : (data.targetId.split("-") as [string, string]);

    return createScenario({
      targetId: data.targetId,
      name: data.name,
      description: data.description,
      zoneA: zoneA ?? data.targetId,
      zoneB: zoneB ?? "",
      periodStart: report.start,
      periodEnd: report.end_exclusive,
    });
  });

export const deleteScenario = createServerFn({ method: "POST" })
  .inputValidator(idIn)
  .handler(async ({ data }) => {
    const { deleteScenario } = await import("./workbench.server");
    deleteScenario(data.id);
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
    const { insertUnit } = await import("./workbench.server");
    const def = unitDef(data.unitType);
    const params = data.params ?? def.defaults;
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
    const { updateUnit } = await import("./workbench.server");
    updateUnit(data.id, {
      params: data.params,
      capexMeur: data.capexMeur,
      deliveryMonths: data.deliveryMonths,
      zoneCode: data.zoneCode,
    });
    return { ok: true };
  });

export const deleteUnit = createServerFn({ method: "POST" })
  .inputValidator(idIn)
  .handler(async ({ data }) => {
    const { deleteUnit } = await import("./workbench.server");
    deleteUnit(data.id);
    return { ok: true };
  });

/**
 * Run the PyPSA-Eur hourly sub-network model for a scenario and store the
 * result plus ENTSO-E CBA indicators.
 *
 * Welfare comes from the zonal transport LP in `./simulation.server`: for each
 * hour the dual ascent maximises `a*sum(x*g) - a^2/2*sum(s_z*nu_z^2)` subject to
 * ATC headroom, so the value of added capacity is concave by construction and
 * the year-long total is a real re-dispatch, not a spread heuristic.
 */
export const runScenario = createServerFn({ method: "POST" })
  .inputValidator(idIn)
  .handler(async ({ data }) => {
    const { getScenarioWithDetails, setScenarioStatus, upsertResult, insertValidation } =
      await import("./workbench.server");
    const { loadNetwork, runDispatch } = await import("./simulation.server");

    const scenario = getScenarioWithDetails(data.id);
    const target = { a: scenario.zone_a, b: scenario.zone_b };

    setScenarioStatus(data.id, "running");

    const net = await loadNetwork(target.a, target.b);
    const base = runDispatch(net, [], target);
    const scen = runDispatch(net, scenario.units, target);

    const years = Math.max(base.hours, 1) / 8760;
    const marketMeur = (scen.welfareEur - base.welfareEur) / 1e6 / years;
    const climateKt = -(scen.co2Kg - base.co2Kg) / 1e6 / years;

    const capex = scenario.units.reduce((s, u) => s + Number(u.capex_meur ?? 0), 0);
    const delivery = scenario.units.reduce(
      (m, u) => Math.max(m, Number(u.delivery_months ?? 0)),
      0,
    );
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
        "ENTSO-E CBA 4.0 style indicators. Hourly market clearing follows the ENTSO-E " +
        "single day-ahead coupling (Euphemia) ATC algorithm: welfare maximisation with " +
        "balanced net positions, ATC limits, price convergence where borders are free and " +
        "price splitting only across saturated borders. Prices, dispatches and CO2 come " +
        "from the PyPSA-Eur full-year baseline solve; added capacity is priced by a zonal " +
        "dual-ascent re-dispatch, which has no merit-order scarcity pricing and therefore " +
        "understates relief on heavily congested borders (compare the LP duals in " +
        "public/research/pypsa-targets.json).",
    };

    const payload = {
      scenario_id: data.id,
      status: "complete",
      created_at: new Date().toISOString(),
      market_opportunity_meur: round(marketMeur, 4),
      climate_opportunity_ktco2: round(climateKt, 4),
      base_metrics: jsonify(base),
      scenario_metrics: jsonify(scen),
      entsoe_indicators: entsoe,
      hourly_summary: {
        hours_modelled: base.hours,
        zones_modelled: net.zones.length,
        borders_modelled: net.edges.length,
        period_start: scenario.period_start,
        period_end: scenario.period_end,
      },
    };

    upsertResult(data.id, payload);
    setScenarioStatus(data.id, "complete");

    // Model validation: how closely the base run reproduces the baseline solve.
    // The KKT gate is the strict one - it is the only check that can detect a
    // converged-but-wrong dispatch, since price/flow error is measured against
    // the same solve that produced the input series.
    insertValidation({
      periodStart: scenario.period_start,
      periodEnd: scenario.period_end,
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

/** Latest model validation entry (null when nothing has run yet). */
export const getValidation = createServerFn({ method: "GET" }).handler(async () => {
  const { latestValidation } = await import("./workbench.server");
  const v = latestValidation();
  return v
    ? {
        period_start: v.period_start,
        period_end: v.period_end,
        passed: v.passed,
        metrics: v.metrics,
      }
    : null;
});

function round(v: number, d: number) {
  const f = 10 ** d;
  return Math.round((Number.isFinite(v) ? Number(v) : 0) * f) / f;
}

function jsonify(r: Record<string, number>) {
  return Object.fromEntries(Object.entries(r).map(([k, v]) => [k, round(v, 3)]));
}
