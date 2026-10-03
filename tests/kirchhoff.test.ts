import { beforeAll, expect, test } from "bun:test";
import loadHighs, { type Highs } from "highs";
import { readFile } from "node:fs/promises";
import fixture from "./fixtures/network.json";
import { parseNetworkInput } from "../src/lib/network-model/schema";
import { kirchhoffCycles } from "../src/lib/network-model/kirchhoff";
import {
  dispatchNetwork,
  applyIntervention,
  NetworkSolverSession,
  type Intervention,
} from "../src/lib/network-model/solver";
let highs: Highs;
beforeAll(async () => {
  highs = await loadHighs();
});
function triangle() {
  const d = structuredClone(fixture) as Record<string, unknown>;
  Object.assign(d, {
    schema_version: 3,
    zones: ["A", "B", "C"],
    timestamps: ["2025-01-01T00:00:00Z"],
    load_mw: { A: [0], B: [0], C: [100] },
    external_net_import_mw: { A: [0], B: [0], C: [0] },
    generators: [
      { id: "cheap", zone: "A", max_mw: [100], cost_eur_mwh: 0, co2_t_per_mwh: 0 },
      { id: "expensive", zone: "C", max_mw: [100], cost_eur_mwh: 100, co2_t_per_mwh: 1 },
    ],
    edges: [
      { id: "AB", a: "A", b: "B", ab_mw: [100], ba_mw: [100] },
      { id: "BC", a: "B", b: "C", ab_mw: [100], ba_mw: [100] },
      { id: "AC", a: "A", b: "C", ab_mw: [10], ba_mw: [10] },
    ],
    ac_branches: ["AB", "BC", "AC"].map((edge_id) => ({ edge_id, reactance: 1 })),
    storage: [],
  });
  return parseNetworkInput(d);
}
test("Kirchhoff triangle prevents free routing and changes finite investment value", () => {
  const d = triangle(),
    result = dispatchNetwork(highs, d);
  expect(result.total_cost_eur).toBeCloseTo(8500, 6);
  expect(result.flow_mw["AB"]![0]).toBeCloseTo(5, 6);
  expect(result.flow_mw["BC"]![0]).toBeCloseTo(5, 6);
  expect(result.flow_mw["AC"]![0]).toBeCloseTo(10, 6);
  const relaxed = structuredClone(d);
  delete relaxed.ac_branches;
  relaxed.schema_version = 2;
  expect(dispatchNetwork(highs, relaxed).total_cost_eur).toBeCloseTo(0, 6);
  expect(
    dispatchNetwork(highs, applyIntervention(d, { edge_additions_mw: { AC: 90 }, storage: [] }))
      .total_cost_eur,
  ).toBeCloseTo(0, 6);
  const invalid = structuredClone(d);
  invalid.schema_version = 2;
  expect(() => parseNetworkInput(invalid)).toThrow("schema v3");
});
test("complete cycle basis handles parallel branches and disconnected forests", () => {
  const edges = [
    { id: "a", a: "A", b: "B" },
    { id: "b", a: "A", b: "B" },
    { id: "c", a: "X", b: "Y" },
  ];
  const cycles = kirchhoffCycles(
    edges,
    edges.map((e) => ({ edge_id: e.id, reactance: 1 })),
  );
  expect(cycles).toEqual([
    [
      ["b", 1],
      ["a", -1],
    ],
  ]);
});
test("published Kirchhoff network reproduces every independent PyPSA AC reference", async () => {
  const directory = "public/research/network-benchmark";
  const input = parseNetworkInput(
    JSON.parse(await readFile(`${directory}/kirchhoff-input.json`, "utf8")),
  );
  const manifest = JSON.parse(await readFile(`${directory}/manifest.json`, "utf8")) as {
    cases: ({ id: string } & Intervention)[];
  };
  const native = JSON.parse(await readFile(`${directory}/results.json`, "utf8")) as {
    cases: { id: string; ac_cost_eur: number }[];
  };
  const session = new NetworkSolverSession(highs);
  try {
    for (const scenario of manifest.cases) {
      const result = dispatchNetwork(highs, applyIntervention(input, scenario), session);
      expect(
        Math.abs(
          result.total_cost_eur - native.cases.find((r) => r.id === scenario.id)!.ac_cost_eur,
        ),
      ).toBeLessThan(0.01);
      expect(result.max_constraint_violation).toBeLessThan(1e-5);
      expect(result.unserved_mwh).toBeLessThan(1e-6);
    }
  } finally {
    session.dispose();
  }
}, 60000);
