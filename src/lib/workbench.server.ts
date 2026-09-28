/// <reference types="bun" />
import * as path from "node:path";
import fs from "node:fs";
import { Database } from "bun:sqlite";

/**
 * Local workbench scenario store, backed by a single SQLite database
 * (data/workbench/scenarios.db, gitignored). Replaces the old Supabase-backed
 * scenario CRUD so the workbench runs fully offline.
 *
 * Tables mirror the former Supabase schema 1:1 (scenarios / scenario_units /
 * scenario_results / model_validation) so future export or migration is
 * straightforward. JSON columns (params, metrics, ...) are stored as TEXT and
 * parsed on read.
 *
 * NOTE: `bun:sqlite` only exists in the bun runtime, so this store is for the
 * local dev server (`bun run dev`). A deployed Cloudflare/Wrangler build has
 * no filesystem or bun built-ins; if that target is ever needed, provide a
 * KV/D1 adapter behind this same module boundary.
 */
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

const DEFAULT_DB_PATH = path.join(process.cwd(), "data", "workbench", "scenarios.db");

/**
 * Minimal permissive handle over bun:sqlite. The upstream generic type models
 * bindings as `ParamsType[]` arrays, which fights plain `run(sql, a, b, ...)`
 * and `query(...).get(id)` calls; the runtime accepts positional bindings, so
 * we wrap only the surface this store uses.
 */
interface Db {
  exec(sql: string): void;
  run(sql: string, ...params: unknown[]): { changes: number; lastInsertRowid: number | bigint };
  query(
    sql: string,
    ...params: unknown[]
  ): {
    all(...bindings: unknown[]): Array<Record<string, unknown>>;
    get(...bindings: unknown[]): Record<string, unknown> | null;
  };
}

let _db: Db | undefined;

function db(): Db {
  if (_db) return _db;
  const file = process.env["WORKBENCH_DB_PATH"] ?? DEFAULT_DB_PATH;
  fs.mkdirSync(path.dirname(file), { recursive: true });
  _db = new Database(file, { create: true }) as unknown as Db;
  _db.exec("PRAGMA journal_mode = WAL;");
  _db.exec("PRAGMA foreign_keys = ON;");
  _db.exec(`
    CREATE TABLE IF NOT EXISTS scenarios (
      id TEXT PRIMARY KEY NOT NULL,
      target_id TEXT NOT NULL,
      name TEXT NOT NULL,
      description TEXT,
      is_template INTEGER NOT NULL DEFAULT 0,
      status TEXT NOT NULL DEFAULT 'draft',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      zone_a TEXT NOT NULL,
      zone_b TEXT NOT NULL,
      period_start TEXT NOT NULL DEFAULT '2025-01-01',
      period_end TEXT NOT NULL DEFAULT '2025-12-31'
    );
    CREATE INDEX IF NOT EXISTS idx_scenarios_target ON scenarios(target_id);

    CREATE TABLE IF NOT EXISTS scenario_units (
      id TEXT PRIMARY KEY NOT NULL,
      scenario_id TEXT NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
      unit_type TEXT NOT NULL,
      zone_code TEXT,
      border_zone_a TEXT,
      border_zone_b TEXT,
      params TEXT NOT NULL DEFAULT '{}',
      capex_meur REAL NOT NULL DEFAULT 0,
      delivery_months INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_units_scenario ON scenario_units(scenario_id);

    CREATE TABLE IF NOT EXISTS scenario_results (
      scenario_id TEXT PRIMARY KEY NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
      status TEXT NOT NULL DEFAULT 'complete',
      created_at TEXT NOT NULL,
      market_opportunity_meur REAL,
      climate_opportunity_ktco2 REAL,
      base_metrics TEXT,
      scenario_metrics TEXT,
      entsoe_indicators TEXT,
      hourly_summary TEXT
    );

    CREATE TABLE IF NOT EXISTS model_validation (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      period_start TEXT NOT NULL DEFAULT '2025-01-01',
      period_end TEXT NOT NULL DEFAULT '2025-12-31',
      metrics TEXT,
      passed INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL
    );
  `);
  return _db;
}

function scenarioFromRow(row: Record<string, unknown> | null | undefined): StoredScenario {
  if (!row) throw new Error("Scenario not found");
  return {
    id: String(row["id"]),
    target_id: String(row["target_id"]),
    name: String(row["name"]),
    description: row["description"] == null ? null : String(row["description"]),
    is_template: Number(row["is_template"]) === 1,
    status: String(row["status"]) as StoredScenario["status"],
    created_at: String(row["created_at"]),
    updated_at: String(row["updated_at"]),
    zone_a: String(row["zone_a"]),
    zone_b: String(row["zone_b"]),
    period_start: String(row["period_start"]),
    period_end: String(row["period_end"]),
  };
}

function unitFromRow(row: Record<string, unknown>): UnitRow {
  return {
    id: String(row["id"]),
    scenario_id: String(row["scenario_id"]),
    unit_type: String(row["unit_type"]),
    zone_code: row["zone_code"] == null ? null : String(row["zone_code"]),
    border_zone_a: row["border_zone_a"] == null ? null : String(row["border_zone_a"]),
    border_zone_b: row["border_zone_b"] == null ? null : String(row["border_zone_b"]),
    params: parseJson(row["params"], {}),
    capex_meur: Number(row["capex_meur"] ?? 0),
    delivery_months: Number(row["delivery_months"] ?? 0),
  };
}

function resultFromRow(row: Record<string, unknown>): ScenarioResult {
  return {
    scenario_id: String(row["scenario_id"]),
    status: String(row["status"]),
    created_at: String(row["created_at"]),
    market_opportunity_meur: Number(row["market_opportunity_meur"] ?? 0),
    climate_opportunity_ktco2: Number(row["climate_opportunity_ktco2"] ?? 0),
    base_metrics: parseJson(row["base_metrics"], {}),
    scenario_metrics: parseJson(row["scenario_metrics"], {}),
    entsoe_indicators: parseJson(row["entsoe_indicators"], {}),
    hourly_summary: parseJson(row["hourly_summary"], {}),
  };
}

function parseJson<T>(value: unknown, fallback: T): T {
  if (typeof value !== "string" || value.length === 0) return fallback;
  try {
    return JSON.parse(value) as T;
  } catch {
    return fallback;
  }
}

function hydrate(d: Db, row: Record<string, unknown>): ScenarioWithDetails {
  const scenario = scenarioFromRow(row);
  const units = d
    .query("SELECT * FROM scenario_units WHERE scenario_id = ? ORDER BY created_at")
    .all(scenario.id) as unknown as Array<Record<string, unknown>>;
  const result = d
    .query("SELECT * FROM scenario_results WHERE scenario_id = ?")
    .get(scenario.id) as unknown as Record<string, unknown> | null;
  return {
    ...scenario,
    units: units.map(unitFromRow),
    result: result ? resultFromRow(result) : null,
  };
}

export function listScenariosForTarget(targetId: string): ScenarioWithDetails[] {
  const d = db();
  const scenarios = d
    .query("SELECT * FROM scenarios WHERE target_id = ? ORDER BY created_at")
    .all(targetId) as unknown as Array<Record<string, unknown>>;
  return scenarios.map((s) => hydrate(d, s));
}

export function listAllScenarios(): ScenarioWithDetails[] {
  const d = db();
  const scenarios = d
    .query("SELECT * FROM scenarios ORDER BY created_at")
    .all() as unknown as Array<Record<string, unknown>>;
  return scenarios.map((s) => hydrate(d, s));
}

export function getScenarioWithDetails(id: string): ScenarioWithDetails {
  const d = db();
  const row = d.query("SELECT * FROM scenarios WHERE id = ?").get(id) as unknown as Record<
    string,
    unknown
  > | null;
  return hydrate(d, row ?? {});
}

export function createScenario(input: {
  targetId: string;
  name: string;
  description?: string | undefined;
  zoneA: string;
  zoneB: string;
  periodStart: string;
  periodEnd: string;
}): StoredScenario {
  const d = db();
  const now = new Date().toISOString();
  const id = globalThis.crypto.randomUUID();
  d.run(
    "INSERT INTO scenarios (id, target_id, name, description, is_template, status, created_at, updated_at, zone_a, zone_b, period_start, period_end) VALUES (?, ?, ?, ?, 0, 'draft', ?, ?, ?, ?, ?, ?)",
    id,
    input.targetId,
    input.name,
    input.description ?? null,
    now,
    now,
    input.zoneA,
    input.zoneB,
    input.periodStart,
    input.periodEnd,
  );
  const row = d.query("SELECT * FROM scenarios WHERE id = ?").get(id) as unknown as Record<
    string,
    unknown
  >;
  return scenarioFromRow(row);
}

export function getScenario(id: string): StoredScenario {
  const row = db().query("SELECT * FROM scenarios WHERE id = ?").get(id) as unknown as Record<
    string,
    unknown
  > | null;
  return scenarioFromRow(row);
}

export function setScenarioStatus(id: string, status: StoredScenario["status"]): void {
  db().run(
    "UPDATE scenarios SET status = ?, updated_at = ? WHERE id = ?",
    status,
    new Date().toISOString(),
    id,
  );
}

export function deleteScenario(id: string): void {
  const d = db();
  d.run("DELETE FROM scenario_units WHERE scenario_id = ?", id);
  d.run("DELETE FROM scenario_results WHERE scenario_id = ?", id);
  d.run("DELETE FROM scenarios WHERE id = ?", id);
}

export function insertUnit(input: {
  scenarioId: string;
  unitType: string;
  zoneCode: string | null;
  borderZoneA: string | null;
  borderZoneB: string | null;
  params: Record<string, number>;
  capexMeur: number;
  deliveryMonths: number;
}): UnitRow {
  const d = db();
  const id = globalThis.crypto.randomUUID();
  d.run(
    "INSERT INTO scenario_units (id, scenario_id, unit_type, zone_code, border_zone_a, border_zone_b, params, capex_meur, delivery_months, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
    id,
    input.scenarioId,
    input.unitType,
    input.zoneCode,
    input.borderZoneA,
    input.borderZoneB,
    JSON.stringify(input.params),
    input.capexMeur,
    input.deliveryMonths,
    new Date().toISOString(),
  );
  const row = d.query("SELECT * FROM scenario_units WHERE id = ?").get(id) as unknown as Record<
    string,
    unknown
  >;
  return unitFromRow(row);
}

export function updateUnit(
  id: string,
  patch: {
    params?: Record<string, number> | undefined;
    capexMeur?: number | undefined;
    deliveryMonths?: number | undefined;
    zoneCode?: string | null | undefined;
  },
): void {
  const fields: string[] = [];
  const values: Array<string | number | null> = [];
  if (patch.params !== undefined) {
    fields.push("params = ?");
    values.push(JSON.stringify(patch.params));
  }
  if (patch.capexMeur !== undefined) {
    fields.push("capex_meur = ?");
    values.push(patch.capexMeur);
  }
  if (patch.deliveryMonths !== undefined) {
    fields.push("delivery_months = ?");
    values.push(patch.deliveryMonths);
  }
  if (patch.zoneCode !== undefined) {
    fields.push("zone_code = ?");
    values.push(patch.zoneCode);
  }
  if (fields.length === 0) return;
  values.push(id);
  db().run(`UPDATE scenario_units SET ${fields.join(", ")} WHERE id = ?`, ...values);
}

export function deleteUnit(id: string): void {
  db().run("DELETE FROM scenario_units WHERE id = ?", id);
}

export function upsertResult(scenarioId: string, result: ScenarioResult): void {
  const d = db();
  d.run("DELETE FROM scenario_results WHERE scenario_id = ?", scenarioId);
  d.run(
    "INSERT INTO scenario_results (scenario_id, status, created_at, market_opportunity_meur, climate_opportunity_ktco2, base_metrics, scenario_metrics, entsoe_indicators, hourly_summary) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    scenarioId,
    result.status,
    result.created_at,
    result.market_opportunity_meur,
    result.climate_opportunity_ktco2,
    JSON.stringify(result.base_metrics),
    JSON.stringify(result.scenario_metrics),
    JSON.stringify(result.entsoe_indicators),
    JSON.stringify(result.hourly_summary),
  );
}

export function insertValidation(input: {
  periodStart: string;
  periodEnd: string;
  metrics: Record<string, number | string>;
  passed: boolean;
}): void {
  db().run(
    "INSERT INTO model_validation (period_start, period_end, metrics, passed, created_at) VALUES (?, ?, ?, ?, ?)",
    input.periodStart,
    input.periodEnd,
    JSON.stringify(input.metrics),
    input.passed ? 1 : 0,
    new Date().toISOString(),
  );
}

export function latestValidation(): ValidationRow | null {
  const row = db()
    .query("SELECT * FROM model_validation ORDER BY id DESC LIMIT 1")
    .get() as unknown as Record<string, unknown> | null;
  if (!row) return null;
  return {
    id: Number(row["id"]),
    period_start: String(row["period_start"]),
    period_end: String(row["period_end"]),
    metrics: parseJson<Record<string, number | string>>(row["metrics"], {}),
    passed: Number(row["passed"]) === 1,
    created_at: String(row["created_at"]),
  };
}
