import { z } from "zod";

const finite = z.number().finite();
const nonnegative = finite.nonnegative();
const series = z.array(nonnegative);
const id = z.string().min(1).max(160);
const generator = z
  .object({
    id,
    zone: id,
    max_mw: series,
    min_mw: series.optional(),
    cost_eur_mwh: finite,
    co2_t_per_mwh: nonnegative.nullable().optional(),
    energy_budget_mwh: nonnegative.optional(),
    ramp_mw_per_hour: nonnegative.optional(),
  })
  .strict();
export const storageSchema = z
  .object({
    id,
    zone: id,
    power_mw: nonnegative,
    energy_mwh: nonnegative,
    initial_mwh: nonnegative,
    terminal_mwh: nonnegative,
    charge_efficiency: finite.positive().max(1),
    discharge_efficiency: finite.positive().max(1),
    throughput_cost_eur_mwh: nonnegative,
    charge_power_mw: nonnegative.optional(),
    inflow_mw: series.optional(),
    standing_loss: finite.nonnegative().lt(1).optional(),
    cyclic: z.boolean().optional(),
  })
  .strict();
const inputSchema = z
  .object({
    schema_version: z.union([z.literal(1), z.literal(2), z.literal(3)]),
    dataset_id: id,
    provenance: z
      .object({
        source: z.string().min(1),
        source_sha256: z.string().regex(/^[a-f0-9]{64}$/),
        assumptions: z.array(z.string()).min(1),
      })
      .strict(),
    timestamps: z
      .array(z.string().datetime({ offset: true }))
      .min(1)
      .max(8784),
    interval_hours: finite.positive(),
    zones: z.array(id).min(1).max(100),
    load_mw: z.record(series),
    external_net_import_mw: z.record(z.array(finite)),
    generators: z.array(generator).max(2000),
    edges: z.array(z.object({ id, a: id, b: id, ab_mw: series, ba_mw: series }).strict()).max(1000),
    storage: z.array(storageSchema).max(200),
    ac_branches: z
      .array(z.object({ edge_id: id, reactance: finite.positive() }).strict())
      .max(1000)
      .optional(),
    flow_based_regions: z
      .array(
        z
          .object({
            id,
            zones: z.array(id),
            constraints: z.array(
              z
                .object({
                  id,
                  interval: z.number().int().nonnegative(),
                  ptdf: z.record(finite),
                  ram_mw: finite,
                })
                .strict(),
            ),
          })
          .strict(),
      )
      .default([]),
    unserved_cost_eur_mwh: finite.positive(),
  })
  .strict();
export type NetworkInput = z.infer<typeof inputSchema>;
export type StorageInput = z.infer<typeof storageSchema>;

/** Fail closed: dispatch output is never accepted as renewable availability. */
export function parseNetworkInput(value: unknown): NetworkInput {
  const d = inputSchema.parse(value);
  const H = d.timestamps.length;
  const assert = (condition: boolean, message: string) => {
    if (!condition) throw new Error(message);
  };
  const unique = (values: string[], label: string) =>
    assert(new Set(values).size === values.length, `Duplicate ${label}`);
  unique(d.zones, "zones");
  unique(d.timestamps, "timestamps");
  for (let t = 1; t < H; t++)
    assert(
      Math.abs(
        (Date.parse(d.timestamps[t]!) - Date.parse(d.timestamps[t - 1]!)) / 3600000 -
          d.interval_hours,
      ) < 1e-8,
      "Intervals must be consecutive",
    );
  const check = (xs: number[]) => assert(xs.length === H, "Incomplete hourly series");
  for (const mapping of [d.load_mw, d.external_net_import_mw]) {
    assert(
      Object.keys(mapping).sort().join("\0") === [...d.zones].sort().join("\0"),
      "Unmapped zone series",
    );
    Object.values(mapping).forEach(check);
  }
  unique(
    d.generators.map((g) => g.id),
    "generators",
  );
  unique(
    d.edges.map((e) => e.id),
    "edges",
  );
  unique(
    d.storage.map((s) => s.id),
    "storage",
  );
  for (const g of d.generators) {
    assert(d.zones.includes(g.zone), "Unknown generator zone");
    check(g.max_mw);
    if (g.min_mw) {
      check(g.min_mw);
      assert(
        g.min_mw.every((v, t) => v <= g.max_mw[t]!),
        "Inverted generator limits",
      );
    }
  }
  for (const e of d.edges) {
    assert(d.zones.includes(e.a) && d.zones.includes(e.b) && e.a !== e.b, "Invalid edge zones");
    check(e.ab_mw);
    check(e.ba_mw);
  }
  if (d.ac_branches !== undefined) {
    assert(d.schema_version === 3, "Kirchhoff branches require input schema v3");
    assert(d.ac_branches.length > 0, "Declare at least one AC branch");
    assert(
      d.flow_based_regions.length === 0,
      "Combined AC-cycle and regional PTDF physics is unsupported",
    );
    unique(
      d.ac_branches.map((b) => b.edge_id),
      "AC branches",
    );
    assert(
      d.ac_branches.every((b) => d.edges.some((e) => e.id === b.edge_id)),
      "Unknown AC branch edge",
    );
  } else assert(d.schema_version !== 3, "Schema v3 requires explicit AC branches");
  for (const s of d.storage) {
    if (s.inflow_mw) check(s.inflow_mw);
    if (
      d.schema_version === 1 &&
      [s.charge_power_mw, s.inflow_mw, s.standing_loss, s.cyclic].some((v) => v !== undefined)
    )
      throw new Error("Reservoir features require input schema v2");
    if (s.cyclic && (s.initial_mwh !== 0 || s.terminal_mwh !== 0))
      throw new Error("Cyclic inventory is endogenous; fixed boundary fields must be zero");
    assert(
      d.zones.includes(s.zone) && Math.max(s.initial_mwh, s.terminal_mwh) <= s.energy_mwh,
      "Invalid storage zone or inventory",
    );
  }
  unique(
    d.flow_based_regions.map((r) => r.id),
    "regions",
  );
  const assigned = new Set<string>();
  for (const r of d.flow_based_regions) {
    unique(r.zones, "regional zones");
    unique(
      r.constraints.map((c) => c.id),
      "constraint IDs",
    );
    assert(
      r.zones.length >= 2 && r.zones.every((z) => d.zones.includes(z) && !assigned.has(z)),
      "Invalid or overlapping region",
    );
    r.zones.forEach((z) => assigned.add(z));
    assert(
      !d.edges.some((e) => r.zones.includes(e.a) && r.zones.includes(e.b)),
      "Internal bilateral edges double-count PTDF network",
    );
    const covered = new Set<number>();
    for (const c of r.constraints) {
      assert(
        c.interval < H && Object.keys(c.ptdf).sort().join("\0") === [...r.zones].sort().join("\0"),
        "Incomplete PTDF mapping",
      );
      covered.add(c.interval);
    }
    assert(covered.size === H, "Missing PTDF intervals");
  }
  // A browser resource guard, not a statement of physical network limits.
  assert(
    H *
      (d.generators.length +
        d.edges.length +
        2 * d.zones.length +
        4 * d.storage.length +
        assigned.size) <=
      (d.storage.length ||
      d.generators.some(
        (g) => g.energy_budget_mwh !== undefined || g.ramp_mw_per_hour !== undefined,
      )
        ? 150000
        : 1500000),
    "Model exceeds browser column budget; use a smaller exact period or offline solver",
  );
  return d;
}
