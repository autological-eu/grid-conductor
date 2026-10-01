import loadHighs from "highs";
import { readFile, writeFile } from "node:fs/promises";
import { parseNetworkInput } from "../src/lib/network-model/schema";
import { benchmarkWithCarbonPrice } from "../src/lib/network-model/benchmark";
import {
  applyIntervention,
  dispatchNetwork,
  NetworkSolverSession,
  type Intervention,
} from "../src/lib/network-model/solver";
const directory = "public/research/network-benchmark";
const input = parseNetworkInput(
  JSON.parse(await readFile(`${directory}/kirchhoff-input.json`, "utf8")),
);
const manifest = JSON.parse(await readFile(`${directory}/manifest.json`, "utf8")) as {
  cases: ({ id: string } & Intervention)[];
};
const native = JSON.parse(await readFile(`${directory}/results.json`, "utf8")) as {
  cases: { id: string; ac_cost_eur: number; ac_benefit_eur: number }[];
};
const highs = await loadHighs(),
  trials = [];
for (let repeat = 0; repeat < 3; repeat++) {
  const session = new NetworkSolverSession(highs),
    rows = [];
  try {
    for (const scenario of manifest.cases) {
      const start = performance.now(),
        result = dispatchNetwork(highs, applyIntervention(input, scenario), session);
      const reference = native.cases.find((r) => r.id === scenario.id)!;
      const difference = result.total_cost_eur - reference.ac_cost_eur;
      if (
        Math.abs(difference) > 0.01 ||
        result.unserved_mwh > 1e-6 ||
        result.max_constraint_violation > 1e-5
      )
        throw new Error(`Kirchhoff parity failed ${scenario.id}: ${difference}`);
      rows.push({
        id: scenario.id,
        total_cost_eur: result.total_cost_eur,
        total_co2_t: result.total_co2_t,
        native_ac_difference_eur: difference,
        max_constraint_violation: result.max_constraint_violation,
        elapsed_ms: performance.now() - start,
        unserved_mwh: result.unserved_mwh,
        simultaneous_storage_intervals: result.simultaneous_storage_intervals,
      });
      console.log(JSON.stringify({ repeat, ...rows.at(-1) }));
    }
  } finally {
    session.dispose();
  }
  trials.push(rows);
}
await writeFile(
  "data/pypsa-eur/network-benchmark/kirchhoff-bun-results.json",
  JSON.stringify({ trials }, null, 2),
);

const carbon = JSON.parse(await readFile(`${directory}/carbon-sensitivity.json`, "utf8")) as {
  cases: {
    carbon_price_eur_t: number;
    id: string;
    patch: Intervention;
    pypsa_ac: { total_cost_eur: number; total_co2_t: number };
  }[];
};
const carbonRows = [];
for (const price of [0, 40, 80, 120]) {
  const data = benchmarkWithCarbonPrice(input, price),
    session = new NetworkSolverSession(highs);
  try {
    for (const row of carbon.cases.filter((r) => r.carbon_price_eur_t === price)) {
      const result = dispatchNetwork(highs, applyIntervention(data, row.patch), session);
      const difference = result.total_cost_eur - row.pypsa_ac.total_cost_eur;
      if (
        Math.abs(difference) > 0.01 ||
        result.unserved_mwh > 1e-6 ||
        result.max_constraint_violation > 1e-5 ||
        result.simultaneous_storage_intervals
      )
        throw new Error(`Carbon AC parity failed ${price}/${row.id}`);
      carbonRows.push({
        price,
        id: row.id,
        total_cost_eur: result.total_cost_eur,
        native_ac_difference_eur: difference,
        co2_difference_t: result.total_co2_t! - row.pypsa_ac.total_co2_t,
        max_constraint_violation: result.max_constraint_violation,
      });
    }
  } finally {
    session.dispose();
  }
}
await writeFile(
  "data/pypsa-eur/network-benchmark/kirchhoff-carbon-results.json",
  JSON.stringify({ cases: carbonRows }, null, 2),
);
console.log("All sixteen carbon-policy cases reproduce native PyPSA AC objectives.");
