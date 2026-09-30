import { beforeAll, expect, test } from "bun:test";
import loadHighs, { type Highs } from "highs";
import fixture from "./fixtures/network.json";
import referenceCases from "./fixtures/network-reference.json";
import { parseNetworkInput } from "../src/lib/network-model/schema";
import {
  applyIntervention,
  compareDispatch,
  dispatchNetwork,
} from "../src/lib/network-model/solver";
import "fake-indexeddb/auto";
import { loadNetworkWorkspace, saveNetworkWorkspace } from "../src/lib/network-model/persistence";
let highs: Highs;
beforeAll(async () => {
  highs = await loadHighs();
});
const data = () => parseNetworkInput(structuredClone(fixture));

test("joint dispatch exact finite benefit and saturation; not a rent metric", () => {
  const d = data(),
    baseline = dispatchNetwork(highs, d);
  expect(baseline.total_cost_eur).toBeCloseTo(16400, 6);
  expect(baseline.price_eur_mwh["A"]).toEqual([10, 10]);
  expect(baseline.price_eur_mwh["B"]).toEqual([100, 100]);
  const result = dispatchNetwork(
    highs,
    applyIntervention(d, { edge_additions_mw: { AB: 50 }, storage: [] }),
  );
  expect(compareDispatch(baseline, result).period_benefit_eur).toBeCloseTo(9000, 6);
  expect(compareDispatch(baseline, result).avoided_co2_t).toBeCloseTo(100, 6);
  expect(
    dispatchNetwork(highs, applyIntervention(d, { edge_additions_mw: { AB: 500 }, storage: [] }))
      .total_cost_eur,
  ).toBeCloseTo(2000, 6);
});
test("chronological storage respects empty terminal, efficiency and energy conservation", () => {
  const d = data();
  d.edges = [];
  d.load_mw = { A: [0, 100], B: [0, 0] };
  d.generators = [
    { id: "renewable", zone: "A", max_mw: [100, 0], cost_eur_mwh: 0, co2_t_per_mwh: 0 },
    { id: "gas", zone: "A", max_mw: [100, 100], cost_eur_mwh: 100, co2_t_per_mwh: 1 },
  ];
  const baseline = dispatchNetwork(highs, d);
  d.storage = [
    {
      id: "battery",
      zone: "A",
      power_mw: 100,
      energy_mwh: 100,
      initial_mwh: 0,
      terminal_mwh: 0,
      charge_efficiency: 0.9,
      discharge_efficiency: 0.9,
      throughput_cost_eur_mwh: 1,
    },
  ];
  const r = dispatchNetwork(highs, d);
  expect(r.storage["battery"]!.soc_mwh).toEqual([0, 90, 0]);
  expect(r.storage["battery"]!.discharge_mw[1]).toBeCloseTo(81, 6);
  expect(r.total_cost_eur).toBeCloseTo(2081, 6);
  expect(compareDispatch(baseline, r).avoided_co2_t).toBeCloseTo(81, 6);
});
test("energy budget and ramp constraints couple intervals", () => {
  const d = data();
  d.generators[0]!.energy_budget_mwh = 20;
  expect(dispatchNetwork(highs, d).total_cost_eur).toBeCloseTo(18200, 6);
  d.generators[0]!.max_mw = [0, 200];
  d.generators[0]!.ramp_mw_per_hour = 5;
  expect(dispatchNetwork(highs, d).total_cost_eur).toBeCloseTo(19550, 6);
});
test("flow-based net positions replace internal bilateral network", () => {
  const d = data();
  d.edges = [];
  d.flow_based_regions = [
    {
      id: "region",
      zones: ["A", "B"],
      constraints: [0, 1].map((t) => ({
        id: `row-${t}`,
        interval: t,
        ptdf: { A: 1, B: 0 },
        ram_mw: 20,
      })),
    },
  ];
  expect(dispatchNetwork(highs, d).total_cost_eur).toBeCloseTo(16400, 6);
  d.edges = data().edges;
  expect(() => parseNetworkInput(d)).toThrow("double-count");
});
test("strict input gates reject missing data and unsupported physical assumptions", () => {
  const d = data();
  d.generators[0]!.max_mw.pop();
  expect(() => parseNetworkInput(d)).toThrow("Incomplete");
  expect(() => parseNetworkInput({ ...fixture, standing_loss: 0.01 })).toThrow();
  expect(() => applyIntervention(data(), { edge_additions_mw: { AB: -1 }, storage: [] })).toThrow();
  const d2 = data();
  d2.timestamps[1] = d2.timestamps[0]!;
  expect(() => parseNetworkInput(d2)).toThrow();
});
test("shortage and incomplete carbon factors are explicit", () => {
  const d = data();
  d.generators = [];
  const r = dispatchNetwork(highs, d);
  expect(r.unserved_mwh).toBeCloseTo(200, 6);
  expect(r.total_co2_t).toBeNull();
  expect(compareDispatch(r, r).scarcity_affected).toBe(true);
});
test("browser-local network workspace round trip remains separate from screening scenarios", async () => {
  const workspace = { input: data(), patch: { edge_additions_mw: { AB: 50 }, storage: [] } };
  await saveNetworkWorkspace(workspace);
  expect(await loadNetworkWorkspace()).toEqual(workspace);
});
test("reference Python/SciPy parity for linked chronology and network constraints", () => {
  for (const { input, expected: reference } of referenceCases.cases) {
    const d = parseNetworkInput(input);
    const browser = dispatchNetwork(highs, d);
    expect(browser.total_cost_eur).toBeCloseTo(reference.total_cost_eur, 5);
    expect(browser.unserved_mwh).toBeCloseTo(reference.unserved_mwh, 6);
    for (const g of d.generators)
      for (let t = 0; t < d.timestamps.length; t++)
        expect(browser.generation_mw[g.id]![t]).toBeCloseTo(
          (reference.hourly[t]!.generation_mw as Record<string, number>)[g.id],
          5,
        );
  }
});

test("independent-hour decomposition matches repeated exact solves without sampling", () => {
  const d = data();
  d.timestamps = Array.from({ length: 49 }, (_, t) =>
    new Date(Date.UTC(2025, 0, 1) + t * 3600000).toISOString(),
  );
  d.load_mw = { A: Array(49).fill(0), B: Array.from({ length: 49 }, (_, t) => 50 + t) };
  d.external_net_import_mw = { A: Array(49).fill(0), B: Array(49).fill(0) };
  d.generators.forEach((g) => {
    g.max_mw = Array(49).fill(200);
  });
  d.edges.forEach((e) => {
    e.ab_mw = Array(49).fill(20);
    e.ba_mw = Array(49).fill(20);
  });
  const r = dispatchNetwork(highs, d);
  expect(r.total_cost_eur).toBeCloseTo(
    d.load_mw.B.reduce((cost, load) => cost + 20 * 10 + (load - 20) * 100, 0),
    5,
  );
  expect(r.price_eur_mwh["B"]).toHaveLength(49);
  expect(r.flow_mw["AB"]).toEqual(Array(49).fill(20));
});
test("signed emissions can worsen even when operating cost improves", () => {
  const d = data();
  d.generators[0]!.co2_t_per_mwh = 1;
  d.generators[1]!.co2_t_per_mwh = 0;
  const baseline = dispatchNetwork(highs, d),
    scenario = dispatchNetwork(
      highs,
      applyIntervention(d, { edge_additions_mw: { AB: 50 }, storage: [] }),
    );
  expect(compareDispatch(baseline, scenario).avoided_co2_t).toBeCloseTo(-100, 6);
});
test("parallel investments interact and cannot be valued by adding standalone benefits", () => {
  const d = data();
  d.edges.push({ ...d.edges[0]!, id: "AB2" });
  const base = dispatchNetwork(highs, d),
    a = dispatchNetwork(
      highs,
      applyIntervention(d, { edge_additions_mw: { AB: 50 }, storage: [] }),
    ),
    b = dispatchNetwork(
      highs,
      applyIntervention(d, { edge_additions_mw: { AB2: 50 }, storage: [] }),
    ),
    both = dispatchNetwork(
      highs,
      applyIntervention(d, { edge_additions_mw: { AB: 50, AB2: 50 }, storage: [] }),
    );
  expect(compareDispatch(base, both).period_benefit_eur).toBeLessThan(
    compareDispatch(base, a).period_benefit_eur + compareDispatch(base, b).period_benefit_eur,
  );
});

test("added storage cannot introduce a free initial inventory subsidy", () => {
  expect(() =>
    applyIntervention(data(), {
      edge_additions_mw: {},
      storage: [
        {
          id: "free",
          zone: "A",
          power_mw: 100,
          energy_mwh: 100,
          initial_mwh: 100,
          terminal_mwh: 0,
          charge_efficiency: 1,
          discharge_efficiency: 1,
          throughput_cost_eur_mwh: 0,
        },
      ],
    }),
  ).toThrow("inventory subsidy");
});

test("schema-v2 reservoir conserves inflow, standing loss and cyclic inventory", () => {
  const d = data();
  d.schema_version = 2;
  d.zones = ["A"];
  d.load_mw = { A: [0, 10] };
  d.external_net_import_mw = { A: [0, 0] };
  d.generators = [{ id: "gas", zone: "A", max_mw: [20, 20], cost_eur_mwh: 100, co2_t_per_mwh: 1 }];
  d.edges = [];
  d.storage = [
    {
      id: "hydro",
      zone: "A",
      power_mw: 10,
      charge_power_mw: 0,
      energy_mwh: 10,
      initial_mwh: 0,
      terminal_mwh: 0,
      charge_efficiency: 1,
      discharge_efficiency: 0.9,
      throughput_cost_eur_mwh: 0,
      inflow_mw: [10, 0],
      standing_loss: 0.1,
      cyclic: true,
    },
  ];
  const r = dispatchNetwork(highs, d);
  expect(r.total_cost_eur).toBeCloseTo(190, 6);
  expect(r.storage["hydro"]!.discharge_mw[1]).toBeCloseTo(8.1, 6);
  expect(r.storage["hydro"]!.soc_mwh[0]).toBeCloseTo(r.storage["hydro"]!.soc_mwh[2]!, 6);
  d.storage[0]!.inflow_mw = [100, 0];
  expect(dispatchNetwork(highs, d).storage["hydro"]!.spill_mw[0]).toBeGreaterThan(0);
  d.storage[0]!.inflow_mw = [0, 0];
  expect(dispatchNetwork(highs, d).total_cost_eur).toBeCloseTo(1000, 6);
  d.schema_version = 1;
  expect(() => parseNetworkInput(d)).toThrow("schema v2");
});
