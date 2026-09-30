import loadHighs from "highs";
import { parseNetworkInput } from "../src/lib/network-model/schema";
import {
  applyIntervention,
  dispatchNetwork,
  NetworkSolverSession,
} from "../src/lib/network-model/solver";
// Structural synthetic benchmark only. These numbers are not European estimates.
const highs = await loadHighs();
for (const [Z, H] of [
  [2, 24],
  [10, 168],
  [34, 8760],
]) {
  const zones = Array.from({ length: Z! }, (_, i) => `z${i}`),
    hours = H!,
    zero = Array(hours).fill(0),
    series = Array(hours).fill(100);
  const input = parseNetworkInput({
    schema_version: 1,
    dataset_id: "synthetic-performance-only",
    provenance: {
      source: "Synthetic benchmark; not research",
      source_sha256: "0".repeat(64),
      assumptions: ["Linear transport chain; one generator per zone; fixed loads"],
    },
    timestamps: Array.from({ length: hours }, (_, t) =>
      new Date(Date.UTC(2025, 0, 1) + t * 3600000).toISOString(),
    ),
    interval_hours: 1,
    zones,
    load_mw: Object.fromEntries(zones.map((z) => [z, series])),
    external_net_import_mw: Object.fromEntries(zones.map((z) => [z, zero])),
    generators: zones.map((zone, i) => ({
      id: `g${i}`,
      zone,
      max_mw: Array(hours).fill(150),
      cost_eur_mwh: 10 + i * 2,
      co2_t_per_mwh: 0.1,
    })),
    edges: zones.slice(1).map((b, i) => ({
      id: `e${i}`,
      a: zones[i],
      b,
      ab_mw: Array(hours).fill(20),
      ba_mw: Array(hours).fill(20),
    })),
    storage: [],
    flow_based_regions: [],
    unserved_cost_eur_mwh: 10000,
  });
  const session = new NetworkSolverSession(highs);
  const start = performance.now();
  const baseline = dispatchNetwork(highs, input, session);
  const baselineMs = performance.now() - start;
  const scenarioStart = performance.now();
  const scenario = dispatchNetwork(
    highs,
    applyIntervention(input, { edge_additions_mw: { e0: 50 }, storage: [] }),
    session,
  );
  const scenarioMs = performance.now() - scenarioStart;
  session.dispose();
  console.log(
    JSON.stringify({
      kind: "synthetic_structural_not_research",
      runtime: "Bun HiGHS WASM",
      zones: Z,
      intervals: H,
      baseline_ms: Math.round(baselineMs),
      scenario_ms: Math.round(scenarioMs),
      benefit_eur: baseline.total_cost_eur - scenario.total_cost_eur,
      max_constraint_violation: scenario.max_constraint_violation,
      peak_rss_bytes: process.resourceUsage().maxRSS * 1024,
    }),
  );
}
