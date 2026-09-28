// Server-only 2-node LP for the fast ENTSO-E target ladder (Step 2).
// Live on the bun server: reads the screening output published by
// tools/fast_entsoe_screening.py (public/research/entsoe-fast-targets.json)
// and solves a genuine 2-node transport LP per scenario with
// javascript-lp-solver. duals are recovered via finite-difference re-solve
// (jsLPSolver does not expose duals directly).
//
// Model (reduced form over the published aggregates — see
// docs/fast-entsoe-screening.md for the full derivation):
//   * Cable scenarios: marginal spread on the A>B corridor drops linearly with
//     added flow at rate slope_a (EUR/MWh per MW). We linearize capacity into
//     10 equal blocks; block k has marginal welfare v_k = avg_spread - slope*C/10*k.
//     Annual welfare = congested_quarters * 0.25 h * max{0, sum_k v_k*block}
//     (LP: pick all blocks with positive marginal value). The 0.25 h factor is
//     the per-quarter energy of the Step-1 screening samples, and congested
//     quarters now span the full YEAR, not one representative month.
//   * Battery scenarios: one cycle/day, charging at the low-price node (spread 0)
//     and discharging at avg spread via a 4-variable LP per cycle, x number of
//     cycles bounded by energy/MW ratio; annualized with round-trip efficiency.
//   * co_opt = cable_1000 blocks + battery_200 cycle (additive LP terms, same
//     slope penalty shared by the cable's added flow).
import fs from "node:fs";
import path from "node:path";
import solver, { type Model, type SolveResult } from "javascript-lp-solver";

export type LpScenario = "cable_500" | "cable_1000" | "battery_200" | "battery_100" | "co_opt";

export type ScenarioResult = {
  scenario: LpScenario;
  annual_welfare_gain_meur: number;
  annual_cap_cost_meur: number;
  net_annual_surplus_meur: number;
  capex_meur: number;
  payback_years: number | null;
  shadow_price_ateur_mwh: number | null;
  avg_spread_eur_mwh: number;
  congestion_hours: number;
};

// CAPEX / finance assumptions (documented in docs/fast-entsoe-screening.md).
const CABLE_CAPEX_MEUR_PER_MW = 0.016; // ~80 EUR/MW-km over 200 km
const BATTERY_CAPEX_MEUR_PER_MWH = 0.25;
const ANNUAL_CAPEX_FACTOR = 0.08; // annuity factor used to annualize capex
const ROUND_TRIP_EFFICIENCY = 0.9;
const HOURS_PER_SAMPLE = 0.25; // Step-1 samples are quarter-hours (energy = MW * 0.25 h)

// Each row is one directed border over the FULL screened year (Step-1 schema
// v3): `congested_quarters` spans the 12 concatenated months, so annual figures
// are true annual sums, NOT an x12 of a representative month.
export type ScreeningRow = {
  month: string;
  border: string;
  average_positive_spread_eur_mwh: number | null;
  congested_quarters: number;
  cap_ab_mw: number | null;
  slope_a: number | null;
  slope_b: number | null;
};

/** Build the jsLPSolver model for the block-discretized cable LP. */
export function blockLp(
  marginals: number[],
  blockMw: number,
  capMw: number,
  lastBlockExtra = 0,
): Model {
  const constraints: Model["constraints"] = { total: { max: capMw } };
  const variables: Model["variables"] = {};
  marginals.forEach((v, k) => {
    const id = `b${k}`;
    const isLast = k === marginals.length - 1;
    variables[id] = { welfare: v, total: 1, [id]: 1 };
    constraints[id] = { max: blockMw + (isLast ? lastBlockExtra : 0) };
  });
  return { optimize: "welfare", opType: "max", constraints, variables };
}

/** Build the jsLPSolver model for a single daily battery cycle. */
export function batteryCycleLp(batteryMw: number, batteryMwh: number, spread: number): Model {
  const h = 1; // one hour per leg
  return {
    optimize: "welfare",
    opType: "max",
    constraints: {
      energy: { max: 0 }, // d - rte*c <= 0
      chargeCap: { max: batteryMw * h },
      dischargeCap: { max: batteryMw * h },
      depth: { max: batteryMwh },
    },
    variables: {
      c: { energy: -ROUND_TRIP_EFFICIENCY, chargeCap: 1, depth: 1, welfare: 0 },
      d: { energy: 1, dischargeCap: 1, welfare: spread },
    },
  };
}

/** Battery LP honouring a per-unit round-trip efficiency (scenario battery override). */
export function batteryCycleLpEff(mw: number, mwh: number, spread: number, eff: number): Model {
  const h = 1; // one hour per leg
  return {
    optimize: "welfare",
    opType: "max",
    constraints: {
      energy: { max: 0 }, // d - rte*c <= 0
      chargeCap: { max: mw * h },
      dischargeCap: { max: mw * h },
      depth: { max: mwh },
    },
    variables: {
      c: { energy: -eff, chargeCap: 1, depth: 1, welfare: 0 },
      d: { energy: 1, dischargeCap: 1, welfare: spread },
    },
  };
}

function welfare(result: SolveResult | unknown): number {
  const r = result as SolveResult;
  return Number(r["result"] ?? 0);
}

function scenarioRow(
  scenario: LpScenario,
  welfare: number,
  annualCapCost: number,
  capex: number,
  shadow: number,
  spread: number,
  hours: number,
): ScenarioResult {
  const net = welfare - annualCapCost;
  return {
    scenario,
    annual_welfare_gain_meur: welfare,
    annual_cap_cost_meur: annualCapCost,
    net_annual_surplus_meur: net,
    capex_meur: capex,
    payback_years: net > 1e-9 ? capex / net : null,
    shadow_price_ateur_mwh: shadow,
    avg_spread_eur_mwh: spread,
    congestion_hours: hours,
  };
}

export function solveScenarios(row: ScreeningRow): ScenarioResult[] {
  const spread = row.average_positive_spread_eur_mwh ?? 0;
  const congestedSamples = row.congested_quarters ?? 0; // full-year quarter-hour samples
  const congestionHours = congestedSamples / 4;
  const slope = row.slope_a ?? 0;
  const baseCap = row.cap_ab_mw ?? 0;
  const results: ScenarioResult[] = [];

  const cableScenarios: Array<{ name: LpScenario; deltaC: number }> = [
    { name: "cable_500", deltaC: 500 },
    { name: "cable_1000", deltaC: 1000 },
  ];
  for (const { name, deltaC } of cableScenarios) {
    const blocks = 10;
    const blockMw = deltaC / blocks;
    const marginals = Array.from({ length: blocks }, (_, k) =>
      Math.max(0, spread - slope * ((k + 1) * blockMw)),
    );
    const model = blockLp(marginals, blockMw, deltaC + baseCap);
    const res = solver.Solve(model);
    // per-sample congestion value (EUR/h), sum of marginal blocks dispatched
    const welfarePerSample = welfare(res);
    // M€/yr = per-sample value x 0.25 h x the full year's congested quarters, /1e6
    const annual = (welfarePerSample * HOURS_PER_SAMPLE * congestedSamples) / 1e6;
    // shadow price = marginal value of 1 more MW on the last (most expensive)
    // block: dual of the dispatched intertie
    const resPert = solver.Solve(blockLp(marginals, blockMw, deltaC + baseCap, 1));
    const shadow = welfare(resPert) - welfarePerSample;
    const capex = deltaC * CABLE_CAPEX_MEUR_PER_MW;
    results.push(
      scenarioRow(
        name,
        annual,
        capex * ANNUAL_CAPEX_FACTOR,
        capex,
        shadow,
        spread,
        congestionHours,
      ),
    );
  }

  const batteryScenarios: Array<{ name: LpScenario; mw: number; mwh: number }> = [
    { name: "battery_200", mw: 200, mwh: 800 },
    { name: "battery_100", mw: 100, mwh: 400 },
  ];
  for (const { name, mw, mwh } of batteryScenarios) {
    const model = batteryCycleLp(mw, mwh, spread);
    const res = solver.Solve(model);
    const welfarePerCycle = welfare(res); // EUR per daily cycle
    const annual = (welfarePerCycle * 365) / 1e6; // M€/yr
    // shadow = finite-difference re-solve perturbing only power (+1 MW, energy
    // unchanged) so the marginal reads as the value of one extra MWh of
    // throughput (the discharge leg is one hour: 1 MW extra spills 1 MWh).
    const resPert = solver.Solve(batteryCycleLp(mw + 1, mwh, spread));
    const shadow = welfare(resPert) - welfarePerCycle;
    const capex = mwh * BATTERY_CAPEX_MEUR_PER_MWH;
    results.push(
      scenarioRow(
        name,
        annual,
        capex * ANNUAL_CAPEX_FACTOR,
        capex,
        shadow,
        spread,
        congestionHours,
      ),
    );
  }

  const cable1000 = results.find((r) => r.scenario === "cable_1000");
  const battery200 = results.find((r) => r.scenario === "battery_200");
  if (cable1000 && battery200) {
    const welfareSum = cable1000.annual_welfare_gain_meur + battery200.annual_welfare_gain_meur;
    const capexSum = cable1000.capex_meur + battery200.capex_meur;
    results.push(
      scenarioRow(
        "co_opt",
        welfareSum,
        capexSum * ANNUAL_CAPEX_FACTOR,
        capexSum,
        cable1000.shadow_price_ateur_mwh ?? 0,
        spread,
        congestionHours,
      ),
    );
  }

  return results;
}

export async function loadTargetsJson(): Promise<Record<string, unknown>> {
  const p = path.join(process.cwd(), "public", "research", "entsoe-fast-targets.json");
  return JSON.parse(fs.readFileSync(p, "utf-8")) as Record<string, unknown>;
}

export async function fastEntsoeLp(
  border: string,
): Promise<
  | { border: string; year: string; months: string[]; scenarios: ScenarioResult[] }
  | { error: string }
> {
  const data = await loadTargetsJson();
  const rows = (data["targets"] as Array<Record<string, unknown>>) ?? [];
  const year = String(data["year"] ?? "");
  const row = rows.find((r) => r["border"] === border && r["month"] === year);
  if (!row)
    return { error: `no screening row for border=${border} in ${year || "the published year"}` };
  return {
    border,
    year,
    months: (data["months"] as string[]) ?? [],
    scenarios: solveScenarios(row as unknown as ScreeningRow),
  };
}

/**
 * Custom scenario solving for the workbench's step-two flow. Takes the real
 * scenario units (line added MW, battery power/energy/efficiency) placed on a
 * directed border and solves the 2-node LP over the FULL-year screening row (
 * Step-1 schema v3), returning the annual aggregates directly.
 *
 * Supported today: `line` and `battery`. `solar` / `wind` / `demand_response`
 * are not representable in the 2-node reduced form yet and throw with a clear
 * message (wind/solar extension is planned).
 */
export type ScenarioUnitLike = {
  unit_type: string;
  zone_code: string | null;
  border_zone_a: string | null;
  border_zone_b: string | null;
  params: Record<string, number> | null;
};

export type FromUnitsResult = {
  border: string;
  months: string[];
  annual_welfare_gain_meur: number;
  shadow_price_ateur_mwh: number | null;
  avg_spread_eur_mwh: number;
  congestion_hours: number;
};

export async function solveFromUnits(
  border: string,
  units: ScenarioUnitLike[],
): Promise<FromUnitsResult | { error: string }> {
  const data = await loadTargetsJson();
  const rows = (data["targets"] as Array<Record<string, unknown>>) ?? [];
  const year = String(data["year"] ?? "");

  // Aggregate the placed units into LP sizes.
  let cableMw = 0;
  let batteryMw = 0;
  let batteryMwh = 0;
  let batteryEffSum = 0;
  let batteryCount = 0;
  const unsupported = new Set<string>();
  for (const u of units ?? []) {
    const p = u.params ?? {};
    switch (u.unit_type) {
      case "line":
        cableMw += p["added_mw"] ?? 0;
        break;
      case "battery":
        batteryMw += p["power_mw"] ?? 0;
        batteryMwh += p["energy_mwh"] ?? 0;
        batteryEffSum += p["efficiency"] ?? ROUND_TRIP_EFFICIENCY;
        batteryCount++;
        break;
      default:
        unsupported.add(u.unit_type);
        break;
    }
  }
  if (unsupported.size > 0) {
    throw new Error(
      `unsupported unit type(s) for the fast 2-node LP: ${[...unsupported].join(", ")}. ` +
        "Only line and battery are modelled for now.",
    );
  }

  const batteryEff = batteryCount > 0 ? batteryEffSum / batteryCount : ROUND_TRIP_EFFICIENCY;

  const row = rows.find((r) => r["border"] === border && r["month"] === year);
  if (!row)
    return { error: `no screening row for border=${border} in ${year || "the published year"}` };

  const solved = solveAnnual(
    row as unknown as ScreeningRow,
    cableMw,
    batteryMw,
    batteryMwh,
    batteryEff,
  );
  return {
    border,
    months: (data["months"] as string[]) ?? [],
    annual_welfare_gain_meur: solved.welfare,
    shadow_price_ateur_mwh: solved.shadow,
    avg_spread_eur_mwh: solved.spread,
    congestion_hours: solved.hours,
  };
}

function solveAnnual(
  row: ScreeningRow,
  cableMw: number,
  batteryMw: number,
  batteryMwh: number,
  batteryEff: number,
): { welfare: number; shadow: number | null; spread: number; hours: number } {
  const spread = row.average_positive_spread_eur_mwh ?? 0;
  const congestedSamples = row.congested_quarters ?? 0;
  const congestionHours = congestedSamples / 4;
  let annual = 0;
  let shadow: number | null = null;

  if (cableMw > 0) {
    const blocks = 10;
    const blockMw = cableMw / blocks;
    const slope = row.slope_a ?? 0;
    const baseCap = row.cap_ab_mw ?? 0;
    const marginals = Array.from({ length: blocks }, (_, k) =>
      Math.max(0, spread - slope * ((k + 1) * blockMw)),
    );
    const welfarePerSample = welfare(solver.Solve(blockLp(marginals, blockMw, cableMw + baseCap)));
    annual += (welfarePerSample * HOURS_PER_SAMPLE * congestedSamples) / 1e6;
    const resPert = solver.Solve(blockLp(marginals, blockMw, cableMw + baseCap, 1));
    shadow = welfare(resPert) - welfarePerSample;
  }

  if (batteryMw > 0 && batteryMwh > 0) {
    const welfarePerCycle = welfare(
      solver.Solve(batteryCycleLpEff(batteryMw, batteryMwh, spread, batteryEff)),
    );
    annual += (welfarePerCycle * 365) / 1e6;
    if (shadow == null) {
      const resPert = solver.Solve(
        batteryCycleLpEff(batteryMw + 1, batteryMwh, spread, batteryEff),
      );
      shadow = welfare(resPert) - welfarePerCycle;
    }
  }

  return { welfare: annual, shadow, spread, hours: congestionHours };
}
