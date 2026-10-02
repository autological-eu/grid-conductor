import loadHighs from "highs";
import { parseNetworkInput } from "../src/lib/network-model/schema";
import {
  applyIntervention,
  dispatchNetwork,
  type Intervention,
} from "../src/lib/network-model/solver";
const folder = process.argv[2];
if (!folder) throw new Error("Provide benchmark folder");
const input = parseNetworkInput(await Bun.file(`${folder}/input.json`).json());
const cases = (await Bun.file(`${folder}/cases.json`).json()) as ({ id: string } & Intervention)[];
const highs = await loadHighs();
const rows = [];
for (const scenario of cases) {
  const start = performance.now();
  const result = dispatchNetwork(highs, applyIntervention(input, scenario));
  rows.push({
    id: scenario.id,
    cost_eur: result.total_cost_eur,
    elapsed_seconds: (performance.now() - start) / 1000,
    shortage_mwh: result.unserved_mwh,
    max_constraint_violation: result.max_constraint_violation,
  });
  await Bun.write(`${folder}/${scenario.id}-fast.json`, JSON.stringify(result));
  await Bun.write(`${folder}/fast-cases.json`, JSON.stringify(rows, null, 2));
}
