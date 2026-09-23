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
//     Annual welfare = congested_quarters * 0.25 h * max{0, sum_k v_k*block} * 12
//     (LP: pick all blocks with positive marginal value). The 0.25 h factor is
//     the per-quarter energy of the Step-1 screening samples, and x12 annualizes
//     the single screened month.
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
  const congestedSamples = row.congested_quarters ?? 0; // quarter-hour samples in the month
  const congestionHours = congestedSamples / 4;
  const slope = row.slope_a ?? 0;
  const baseCap = row.cap_ab_mw ?? 0;
  const monthsPerYear = 12;
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
    // M€/yr = per-sample value x 0.25 h x the month's congested quarters, annualized x12, /1e6
    const annual = (welfarePerSample * HOURS_PER_SAMPLE * congestedSamples * monthsPerYear) / 1e6;
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
  month: "2026-01" | "2026-08" = "2026-08",
): Promise<{ border: string; month: string; scenarios: ScenarioResult[] } | { error: string }> {
  const data = await loadTargetsJson();
  const rows = (data["targets"] as Array<Record<string, unknown>>) ?? [];
  const row = rows.find((r) => r["border"] === border && r["month"] === month);
  if (!row) return { error: `no screening row for border=${border} month=${month}` };
  return {
    border,
    month,
    scenarios: solveScenarios(row as unknown as ScreeningRow),
  };
}
