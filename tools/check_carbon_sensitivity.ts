/** Independent WASM parity check before publishing the carbon sensitivity. */
import loadHighs from "highs";
import { readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { benchmarkWithCarbonPrice } from "../src/lib/network-model/benchmark";
import { parseNetworkInput } from "../src/lib/network-model/schema";
import {
  applyIntervention,
  dispatchNetwork,
  NetworkSolverSession,
  type Intervention,
} from "../src/lib/network-model/solver";
const directory = "public/research/network-benchmark";
const raw = await readFile(`${directory}/input.json`);
const base = parseNetworkInput(JSON.parse(raw.toString()));
interface NativeResult {
  total_cost_eur: number;
  total_co2_t: number;
  carbon_inclusive_benefit_eur: number;
  avoided_co2_t: number;
}
const report = JSON.parse(
  await readFile("data/pypsa-eur/network-benchmark/carbon/native-results.json", "utf8"),
) as {
  source_input_file_sha256: string;
  cases: {
    carbon_price_eur_t: number;
    id: string;
    patch: Intervention;
    pypsa_transport: NativeResult;
    wasm?: Record<string, number>;
  }[];
  gates?: Record<string, number | string | boolean>;
};
if (createHash("sha256").update(raw).digest("hex") !== report.source_input_file_sha256)
  throw new Error("Source input changed");
const highs = await loadHighs();
let maxError = 0,
  maxResidual = 0,
  maxEmissionsError = 0;
for (const price of [0, 40, 80, 120]) {
  const input = benchmarkWithCarbonPrice(base, price);
  const session = new NetworkSolverSession(highs);
  try {
    for (const row of report.cases.filter((r) => r.carbon_price_eur_t === price)) {
      const result = dispatchNetwork(highs, applyIntervention(input, row.patch), session);
      if (
        result.total_co2_t === null ||
        result.unserved_mwh > 1e-6 ||
        result.simultaneous_storage_intervals
      )
        throw new Error("Feasibility/emissions gate failed");
      const error = Math.abs(result.total_cost_eur - row.pypsa_transport.total_cost_eur);
      maxError = Math.max(maxError, error);
      maxResidual = Math.max(maxResidual, result.max_constraint_violation);
      maxEmissionsError = Math.max(
        maxEmissionsError,
        Math.abs(result.total_co2_t - row.pypsa_transport.total_co2_t),
      );
      if (error > 0.01 || result.max_constraint_violation > 1e-5)
        throw new Error("Numerical parity failed");
      row.wasm = {
        total_cost_eur: result.total_cost_eur,
        total_co2_t: result.total_co2_t,
        max_constraint_violation: result.max_constraint_violation,
      };
      console.log(`${price} €/t ${row.id}: matched`);
    }
  } finally {
    session.dispose();
  }
}
report.gates = {
  source_input_hash_match: true,
  transport_objectives_within_one_cent: true,
  max_objective_difference_eur: maxError,
  max_constraint_violation: maxResidual,
  max_emissions_difference_t: maxEmissionsError,
  unserved_energy_absent: true,
  simultaneous_storage_cycling_absent: true,
  historical_validation: "not_performed",
  wasm_runtime: "Bun 1.4.2 / HiGHS WASM 1.15.3",
};
await writeFile(`${directory}/carbon-sensitivity.json`, JSON.stringify(report, null, 2) + "\n");
