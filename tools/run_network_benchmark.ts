import loadHighs from "highs";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { parseNetworkInput } from "../src/lib/network-model/schema";
import {
  applyIntervention,
  dispatchNetwork,
  NetworkSolverSession,
  type Intervention,
} from "../src/lib/network-model/solver";
const directory = "public/research/network-benchmark",
  output = "data/pypsa-eur/network-benchmark";
const raw = await readFile(`${directory}/input.json`, "utf8"),
  input = parseNetworkInput(JSON.parse(raw));
const manifest = JSON.parse(await readFile(`${directory}/manifest.json`, "utf8")) as {
  cases: ({ id: string } & Intervention)[];
};
await mkdir(output, { recursive: true });
const init = performance.now(),
  highs = await loadHighs(),
  runtime_ms = performance.now() - init;
const trials = [];
for (let repeat = 0; repeat < 3; repeat++) {
  const session = new NetworkSolverSession(highs),
    cases = [];
  try {
    for (const scenario of manifest.cases) {
      const start = performance.now(),
        data = applyIntervention(input, scenario),
        r = dispatchNetwork(highs, data, session);
      cases.push({
        id: scenario.id,
        elapsed_ms: performance.now() - start,
        total_cost_eur: r.total_cost_eur,
        total_co2_t: r.total_co2_t,
        unserved_mwh: r.unserved_mwh,
        max_constraint_violation: r.max_constraint_violation,
        simultaneous_storage_intervals: r.simultaneous_storage_intervals,
      });
      if (repeat === 0) await writeFile(`${output}/${scenario.id}-wasm.json`, JSON.stringify(r));
      console.log(JSON.stringify({ repeat, ...cases.at(-1) }));
    }
  } finally {
    session.dispose();
  }
  trials.push(cases);
}
await mkdir(output, { recursive: true });
await writeFile(
  `${output}/bun-results.json`,
  JSON.stringify(
    {
      runtime: "Bun 1.4.2 / HiGHS WASM 1.15.3",
      runtime_ms,
      trials,
      peak_rss_bytes: process.resourceUsage().maxRSS * 1024,
    },
    null,
    2,
  ),
);
