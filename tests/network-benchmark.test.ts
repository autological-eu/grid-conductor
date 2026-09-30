import { expect, test } from "bun:test";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import loadHighs from "highs";
import { parseNetworkInput } from "../src/lib/network-model/schema";
import {
  applyIntervention,
  dispatchNetwork,
  NetworkSolverSession,
  type Intervention,
} from "../src/lib/network-model/solver";

test("published real reservoir network reproduces independent PyPSA transport cases", async () => {
  const base = "public/research/network-benchmark/";
  const raw = await readFile(`${base}input.json`);
  const input = parseNetworkInput(JSON.parse(raw.toString()));
  const manifest = JSON.parse(await readFile(`${base}manifest.json`, "utf8")) as {
    input_file_sha256: string;
    cases: ({ id: string } & Intervention)[];
  };
  const report = JSON.parse(await readFile(`${base}results.json`, "utf8")) as {
    input_file_sha256: string;
    cases: { id: string; transport_cost_eur: number }[];
  };
  expect(createHash("sha256").update(raw).digest("hex")).toBe(manifest.input_file_sha256);
  expect(report.input_file_sha256).toBe(manifest.input_file_sha256);
  const highs = await loadHighs(),
    session = new NetworkSolverSession(highs);
  try {
    for (const scenario of manifest.cases) {
      const result = dispatchNetwork(highs, applyIntervention(input, scenario), session);
      const expected = report.cases.find((row) => row.id === scenario.id)!;
      expect(Math.abs(result.total_cost_eur - expected.transport_cost_eur)).toBeLessThan(0.01);
      expect(result.max_constraint_violation).toBeLessThan(1e-5);
      expect(result.unserved_mwh).toBeLessThan(1e-6);
      expect(result.simultaneous_storage_intervals).toBe(0);
    }
  } finally {
    session.dispose();
  }
}, 30000);
