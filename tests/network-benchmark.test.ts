import { expect, test } from "bun:test";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import loadHighs from "highs";
import { benchmarkWithCarbonPrice } from "../src/lib/network-model/benchmark";
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

test("carbon-price sensitivity reproduces paired cost and emissions differences", async () => {
  const base = "public/research/network-benchmark/";
  const raw = await readFile(`${base}input.json`);
  const input = parseNetworkInput(JSON.parse(raw.toString()));
  const report = JSON.parse(await readFile(`${base}carbon-sensitivity.json`, "utf8")) as {
    source_input_file_sha256: string;
    cases: {
      carbon_price_eur_t: number;
      id: string;
      patch: Intervention;
      pypsa_transport: {
        total_cost_eur: number;
        total_co2_t: number;
        carbon_inclusive_benefit_eur: number;
        avoided_co2_t: number;
        non_carbon_operating_benefit_eur: number;
      };
    }[];
  };
  expect(createHash("sha256").update(raw).digest("hex")).toBe(report.source_input_file_sha256);
  const priced = benchmarkWithCarbonPrice(input, 80);
  expect(priced.dataset_id).toBe("pypsa-eur-37-2013-168h-carbon-80");
  expect(input.dataset_id).toBe("pypsa-eur-37-2013-168h");
  expect(priced.generators[0]!.cost_eur_mwh).toBe(
    input.generators[0]!.cost_eur_mwh + 80 * input.generators[0]!.co2_t_per_mwh!,
  );
  expect(() => benchmarkWithCarbonPrice(priced, 80)).toThrow("original unpriced");
  expect(() => benchmarkWithCarbonPrice(input, -1)).toThrow("Unsupported");
  const incomplete = structuredClone(input);
  incomplete.generators[0]!.co2_t_per_mwh = null;
  expect(() => benchmarkWithCarbonPrice(incomplete, 80)).toThrow("complete generation emissions");
  const originalGenerators = JSON.parse(raw.toString()).generators;
  expect(input.generators).toEqual(originalGenerators);
  const highs = await loadHighs(),
    session = new NetworkSolverSession(highs);
  try {
    const rows = report.cases.filter(
      (r) => r.carbon_price_eur_t === 80 && ["baseline", "swepol-plus-500"].includes(r.id),
    );
    expect(rows).toHaveLength(2);
    for (const row of rows) {
      const result = dispatchNetwork(highs, applyIntervention(priced, row.patch), session);
      expect(Math.abs(result.total_cost_eur - row.pypsa_transport.total_cost_eur)).toBeLessThan(
        0.01,
      );
      expect(Math.abs(result.total_co2_t! - row.pypsa_transport.total_co2_t)).toBeLessThan(1e-5);
      const reference = row.pypsa_transport;
      expect(
        Math.abs(
          reference.carbon_inclusive_benefit_eur -
            reference.non_carbon_operating_benefit_eur -
            80 * reference.avoided_co2_t,
        ),
      ).toBeLessThan(0.01);
      if (row.id !== "baseline") expect(reference.avoided_co2_t).toBeGreaterThan(0);
    }
  } finally {
    session.dispose();
  }
}, 30000);
