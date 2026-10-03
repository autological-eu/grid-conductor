import { openDB, type DBSchema } from "idb";

/** Versioned browser-local store. A scenario owns its ordered units and result,
 * so edits and result invalidation are committed atomically. No cloud sync. */
export type StoredScenario = {
  id: string;
  target_id: string;
  name: string;
  description: string | null;
  is_template: boolean;
  status: "draft" | "running" | "complete";
  created_at: string;
  updated_at: string;
  zone_a: string;
  zone_b: string;
  period_start: string;
  period_end: string;
};

export type UnitRow = {
  id: string;
  scenario_id: string;
  unit_type: string;
  zone_code: string | null;
  border_zone_a: string | null;
  border_zone_b: string | null;
  params: Record<string, number>;
  capex_meur: number;
  delivery_months: number;
};

export type ScenarioResult = {
  scenario_id: string;
  status: string;
  created_at: string;
  market_opportunity_meur: number;
  climate_opportunity_ktco2: number;
  base_metrics: Record<string, number>;
  scenario_metrics: Record<string, number>;
  entsoe_indicators: Record<string, number | string | null>;
  hourly_summary: Record<string, number | string | string[] | null>;
};

export type ScenarioWithDetails = StoredScenario & {
  units: UnitRow[];
  result: ScenarioResult | null;
};

export type ValidationRow = {
  id: number;
  period_start: string;
  period_end: string;
  metrics: Record<string, number | string>;
  passed: boolean;
  created_at: string;
};

interface WorkbenchDB extends DBSchema {
  scenarios: { key: string; value: ScenarioWithDetails; indexes: { target: string } };
  validation: { key: string; value: ValidationRow };
}

const DATABASE_NAME = "grid-conductor-workbench";
function db() {
  if (typeof indexedDB === "undefined") {
    throw new Error("Scenario storage needs IndexedDB. Use a browser with local storage enabled.");
  }
  return openDB<WorkbenchDB>(DATABASE_NAME, 1, {
    upgrade(database) {
      database.createObjectStore("scenarios", { keyPath: "id" }).createIndex("target", "target_id");
      database.createObjectStore("validation");
    },
  });
}

async function withDatabase<T>(
  action: (database: Awaited<ReturnType<typeof db>>) => Promise<T>,
): Promise<T> {
  let database;
  try {
    database = await db();
    return await action(database);
  } catch (error) {
    if (error instanceof DOMException) {
      throw new Error(
        `Browser scenario storage is unavailable (${error.name}). Check storage permissions or free disk space.`,
      );
    }
    throw error;
  } finally {
    database?.close();
  }
}

export async function listScenariosForTarget(targetId: string): Promise<ScenarioWithDetails[]> {
  return withDatabase(async (database) => {
    const rows = await database.getAllFromIndex("scenarios", "target", targetId);
    return rows.sort(
      (a, b) => a.created_at.localeCompare(b.created_at) || a.id.localeCompare(b.id),
    );
  });
}

export async function getScenarioWithDetails(id: string): Promise<ScenarioWithDetails> {
  return withDatabase(async (database) => {
    const row = await database.get("scenarios", id);
    if (!row) throw new Error("Scenario not found");
    return row;
  });
}

export async function createScenario(input: {
  targetId: string;
  name: string;
  description?: string | undefined;
  zoneA: string;
  zoneB: string;
  periodStart: string;
  periodEnd: string;
}): Promise<ScenarioWithDetails> {
  const now = new Date().toISOString();
  const row: ScenarioWithDetails = {
    id: crypto.randomUUID(),
    target_id: input.targetId,
    name: input.name,
    description: input.description ?? null,
    is_template: false,
    status: "draft",
    created_at: now,
    updated_at: now,
    zone_a: input.zoneA,
    zone_b: input.zoneB,
    period_start: input.periodStart,
    period_end: input.periodEnd,
    units: [],
    result: null,
  };
  await withDatabase((database) => database.add("scenarios", row));
  return row;
}

/** Monotonic revision timestamp also guards evaluation against concurrent edits. */
function touch(row: ScenarioWithDetails) {
  row.updated_at = new Date(Math.max(Date.now(), Date.parse(row.updated_at) + 1)).toISOString();
}

async function mutate(id: string, update: (row: ScenarioWithDetails) => void) {
  return withDatabase(async (database) => {
    const tx = database.transaction("scenarios", "readwrite");
    const row = await tx.store.get(id);
    if (!row) {
      tx.abort();
      await tx.done.catch(() => {});
      throw new Error("Scenario not found");
    }
    update(row);
    touch(row);
    row.status = "draft";
    row.result = null;
    await tx.store.put(row);
    await tx.done;
  });
}

export async function deleteScenario(id: string): Promise<void> {
  await withDatabase((database) => database.delete("scenarios", id));
}

export async function insertUnit(input: {
  scenarioId: string;
  unitType: string;
  zoneCode: string | null;
  borderZoneA: string | null;
  borderZoneB: string | null;
  params: Record<string, number>;
  capexMeur: number;
  deliveryMonths: number;
}): Promise<UnitRow> {
  const unit: UnitRow = {
    id: crypto.randomUUID(),
    scenario_id: input.scenarioId,
    unit_type: input.unitType,
    zone_code: input.zoneCode,
    border_zone_a: input.borderZoneA,
    border_zone_b: input.borderZoneB,
    params: input.params,
    capex_meur: input.capexMeur,
    delivery_months: input.deliveryMonths,
  };
  await mutate(input.scenarioId, (row) => {
    row.units.push(unit);
  });
  return unit;
}

async function mutateUnit(id: string, update: (row: ScenarioWithDetails, unit: UnitRow) => void) {
  // Resolve parent once, then re-read inside the write transaction to avoid lost edits.
  const parent = await withDatabase(async (database) =>
    (await database.getAll("scenarios")).find((row) => row.units.some((unit) => unit.id === id)),
  );
  if (!parent) throw new Error("Intervention not found");
  await mutate(parent.id, (row) => {
    const unit = row.units.find((item) => item.id === id);
    if (!unit) throw new Error("Intervention not found");
    update(row, unit);
  });
}

export async function updateUnit(
  id: string,
  patch: {
    params?: Record<string, number> | undefined;
    capexMeur?: number | undefined;
    deliveryMonths?: number | undefined;
    zoneCode?: string | null | undefined;
  },
): Promise<void> {
  await mutateUnit(id, (_row, unit) => {
    if (patch.params !== undefined) unit.params = patch.params;
    if (patch.capexMeur !== undefined) unit.capex_meur = patch.capexMeur;
    if (patch.deliveryMonths !== undefined) unit.delivery_months = patch.deliveryMonths;
    if (patch.zoneCode !== undefined) unit.zone_code = patch.zoneCode;
  });
}

export async function deleteUnit(id: string): Promise<void> {
  await mutateUnit(id, (row) => {
    row.units = row.units.filter((unit) => unit.id !== id);
  });
}

/** Persist an evaluation and its data-availability diagnostic in one transaction.
 * Failed evaluations never leave a permanently running scenario. */
export async function saveEvaluation(
  id: string,
  revision: string,
  result: ScenarioResult,
  validation: Omit<ValidationRow, "id" | "created_at">,
): Promise<void> {
  await withDatabase(async (database) => {
    const tx = database.transaction(["scenarios", "validation"], "readwrite");
    const row = await tx.objectStore("scenarios").get(id);
    if (!row || row.updated_at !== revision) {
      tx.abort();
      await tx.done.catch(() => {});
      throw new Error(
        "Scenario changed during evaluation. Run it again with the current interventions.",
      );
    }
    row.result = result;
    row.status = "complete";
    touch(row);
    await tx.objectStore("scenarios").put(row);
    await tx
      .objectStore("validation")
      .put({ ...validation, id: Date.now(), created_at: new Date().toISOString() }, "latest");
    await tx.done;
  });
}

export async function latestValidation(): Promise<ValidationRow | null> {
  return withDatabase(async (database) => (await database.get("validation", "latest")) ?? null);
}
