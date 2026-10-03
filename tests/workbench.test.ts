import "fake-indexeddb/auto";
import { afterAll, beforeEach, describe, expect, test } from "bun:test";
import { deleteDB } from "idb";
import { readFileSync } from "node:fs";
import {
  createScenario,
  insertUnit,
  listScenariosForTarget,
  getScenarioWithDetails,
  updateUnit,
  deleteUnit,
  deleteScenario,
  saveEvaluation,
} from "../src/lib/workbench";
import { runScenario } from "../src/lib/scenarios.functions";

const originalFetch = globalThis.fetch;
globalThis.fetch = (async () =>
  Response.json(
    JSON.parse(readFileSync("public/research/entsoe-fast-targets.json", "utf8")),
  )) as typeof fetch;
afterAll(() => {
  globalThis.fetch = originalFetch;
});
beforeEach(() => deleteDB("grid-conductor-workbench"));
const scenario = () =>
  createScenario({
    targetId: "FR>IT-North",
    name: "Local test",
    zoneA: "FR",
    zoneB: "IT-North",
    periodStart: "2025-01-01",
    periodEnd: "2025-12-31",
  });
const line = (scenarioId: string, mw = 700) =>
  insertUnit({
    scenarioId,
    unitType: "line",
    zoneCode: null,
    borderZoneA: "FR",
    borderZoneB: "IT-North",
    params: { added_mw: mw },
    capexMeur: 650,
    deliveryMonths: 72,
  });

describe("IndexedDB scenario lifecycle", () => {
  test("IDs, snapshots and unit order persist across closed/reopened database connections", async () => {
    const row = await scenario();
    const first = await line(row.id);
    const second = await line(row.id, 1000);
    const loaded = (await listScenariosForTarget(row.target_id))[0]!;
    expect(loaded.id).toBe(row.id);
    expect(loaded.period_start).toBe("2025-01-01");
    expect(loaded.units.map((unit) => unit.id)).toEqual([first.id, second.id]);
    await deleteScenario(row.id);
    expect(await listScenariosForTarget(row.target_id)).toEqual([]);
  });

  test("evaluates locally, saturates huge capacity, and invalidates edited/deleted units", async () => {
    const row = await scenario();
    const unit = await line(row.id, 200000);
    const result = await runScenario({ data: { id: row.id } });
    const published = JSON.parse(readFileSync("public/research/entsoe-fast-targets.json", "utf8"));
    const cap = published.targets.find(
      (item: { border: string }) => item.border === row.target_id,
    ).deadweight_loss_meur_year;
    expect(result.market_opportunity_meur).toBeCloseTo(cap, 4);
    expect((await getScenarioWithDetails(row.id)).status).toBe("complete");
    await updateUnit(unit.id, { params: { added_mw: 500 } });
    expect((await getScenarioWithDetails(row.id)).result).toBeNull();
    await runScenario({ data: { id: row.id } });
    await deleteUnit(unit.id);
    const loaded = await getScenarioWithDetails(row.id);
    expect(loaded.units).toEqual([]);
    expect(loaded.status).toBe("draft");
    expect(loaded.result).toBeNull();
  });

  test("concurrent intervention additions do not lose updates", async () => {
    const row = await scenario();
    await Promise.all([line(row.id), line(row.id), line(row.id)]);
    expect((await getScenarioWithDetails(row.id)).units).toHaveLength(3);
  });

  test("rejects stale evaluations after another edit", async () => {
    const row = await scenario();
    const unit = await line(row.id);
    const result = await runScenario({ data: { id: row.id } });
    const previous = await getScenarioWithDetails(row.id);
    await updateUnit(unit.id, { capexMeur: 123 });
    await expect(
      saveEvaluation(row.id, previous.updated_at, result, {
        period_start: row.period_start,
        period_end: row.period_end,
        metrics: {},
        passed: true,
      }),
    ).rejects.toThrow("Scenario changed");
    expect((await getScenarioWithDetails(row.id)).result).toBeNull();
  });
});
