import "fake-indexeddb/auto";
import { expect, test } from "bun:test";
import fixture from "./fixtures/network.json";
import { parseNetworkInput } from "../src/lib/network-model/schema";
import { loadNetworkWorkspace, saveNetworkWorkspace } from "../src/lib/network-model/persistence";

test("retired prepared benchmark is removed from browser-local workspace", async () => {
  const input = parseNetworkInput({ ...fixture, dataset_id: "pypsa-eur-37-retired" });
  await saveNetworkWorkspace({ input, patch: { edge_additions_mw: {}, storage: [] } });
  expect(await loadNetworkWorkspace()).toBeUndefined();
  expect(await loadNetworkWorkspace()).toBeUndefined();
});

test("supported browser-local input and interventions survive retirement cleanup", async () => {
  const input = parseNetworkInput({ ...fixture, dataset_id: "retained-reference-test" });
  const value = { input, patch: { edge_additions_mw: { AB: 50 }, storage: [] } };
  await saveNetworkWorkspace(value);
  expect(await loadNetworkWorkspace()).toEqual(value);
});
