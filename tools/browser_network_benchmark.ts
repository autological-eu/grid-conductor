import { chromium } from "playwright";
import { readdir, readFile, writeFile } from "node:fs/promises";
const base = process.env["SMOKE_URL"] ?? "http://127.0.0.1:4173/grid-conductor/";
const manifest = JSON.parse(
  await readFile("public/research/network-benchmark/manifest.json", "utf8"),
);
const filename = (await readdir("dist/assets")).find(
  (f) => f.startsWith("worker-") && f.endsWith(".js"),
);
if (!filename) throw new Error("Production build required");
const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
const trials = [];
try {
  for (let repeat = 0; repeat < 3; repeat++) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const failures: string[] = [];
    page.on("pageerror", (error) => failures.push(error.message));
    await page.goto(`${base}network/`);
    const results = await page.evaluate(
      async ({ base, filename, cases }) => {
        const beforeFetch = performance.now();
        const response = await fetch(`${base}research/network-benchmark/input.json`);
        if (!response.ok) throw new Error("Input fetch failed");
        const input = await response.json();
        const input_fetch_parse_ms = performance.now() - beforeFetch;
        const worker = new Worker(`${base}assets/${filename}`, { type: "module" });
        const results = [];
        try {
          for (const scenario of cases) {
            const start = performance.now();
            const result = await new Promise<Record<string, unknown>>((resolve, reject) => {
              const timer = setTimeout(
                () => reject(new Error("Benchmark worker timed out")),
                120000,
              );
              worker.onerror = (error) => {
                clearTimeout(timer);
                reject(new Error(error.message));
              };
              worker.onmessage = (event) => {
                if (event.data.kind === "progress") return;
                clearTimeout(timer);
                if (event.data.kind === "error") reject(new Error(event.data.message));
                else resolve(event.data);
              };
              worker.postMessage({ input, patch: scenario });
            });
            const scenarioResult = result["scenario"] as {
              total_cost_eur: number;
              total_co2_t: number | null;
              unserved_mwh: number;
              max_constraint_violation: number;
              simultaneous_storage_intervals: number;
            };
            results.push({
              id: scenario.id,
              request_ms: performance.now() - start,
              solve_ms: result["elapsed_ms"],
              baseline_cached: result["baseline_cached"],
              input_sha256: result["input_sha256"],
              ...scenarioResult,
            });
          }
        } finally {
          worker.terminate();
        }
        return { input_fetch_parse_ms, cases: results };
      },
      { base, filename, cases: manifest.cases },
    );
    if (failures.length) throw new Error(failures.join("\n"));
    trials.push(results);
    await page.close();
    console.log(
      JSON.stringify({
        repeat,
        input_fetch_parse_ms: results.input_fetch_parse_ms,
        cases: results.cases.map((r) => ({
          id: r.id,
          request_ms: r.request_ms,
          solve_ms: r.solve_ms,
          total_cost_eur: r.total_cost_eur,
          max_constraint_violation: r.max_constraint_violation,
        })),
      }),
    );
  }
  await writeFile(
    "data/pypsa-eur/network-benchmark/browser-results.json",
    JSON.stringify(
      {
        runtime: `Chromium ${browser.version()}`,
        viewport: "1440x1000 desktop on development Linux host",
        timing_scope:
          "request includes structured clone, input validation/hash, cold worker/WASM startup on first request, solving and returning full results; dataset fetch/parse reported separately. Later requests cache baseline.",
        trials,
      },
      null,
      2,
    ),
  );
} finally {
  await browser.close();
}
