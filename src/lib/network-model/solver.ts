import type { Highs, ModelData, Model } from "highs";
import { parseNetworkInput, type NetworkInput, type StorageInput } from "./schema";

export interface Intervention {
  edge_additions_mw: Record<string, number>;
  storage: StorageInput[];
}
export interface DispatchResult {
  total_cost_eur: number;
  total_co2_t: number | null;
  unserved_mwh: number;
  spill_mwh: number;
  max_constraint_violation: number;
  simultaneous_storage_intervals: number;
  price_eur_mwh: Record<string, number[]>;
  generation_mw: Record<string, number[]>;
  flow_mw: Record<string, number[]>;
  storage: Record<
    string,
    { charge_mw: number[]; discharge_mw: number[]; soc_mwh: number[]; spill_mw: number[] }
  >;
}
export function applyIntervention(input: NetworkInput, patch: Intervention): NetworkInput {
  const data = structuredClone(input);
  for (const [id, mw] of Object.entries(patch.edge_additions_mw)) {
    if (!Number.isFinite(mw) || mw < 0)
      throw new Error("Capacity additions must be finite and nonnegative");
    const edge = data.edges.find((e) => e.id === id);
    if (!edge) throw new Error(`Unknown edge ${id}`);
    edge.ab_mw = edge.ab_mw.map((v) => v + mw);
    edge.ba_mw = edge.ba_mw.map((v) => v + mw);
  }
  for (const storage of patch.storage) {
    if (
      storage.initial_mwh !== 0 ||
      storage.terminal_mwh !== 0 ||
      storage.inflow_mw?.some((v) => v !== 0) ||
      storage.cyclic
    )
      throw new Error(
        "New storage interventions must start and end empty; no added inventory subsidy",
      );
  }
  data.storage.push(...patch.storage);
  return parseNetworkInput(data);
}

/** Same lossless linked-period LP as tools/market_model.py. No price-spread calibration. */
export function compileNetwork(d: NetworkInput) {
  const H = d.timestamps.length,
    dt = d.interval_hours;
  const colCost: number[] = [],
    colLower: number[] = [],
    colUpper: number[] = [];
  const columns = new Map<string, number>();
  const key = (kind: string, id: string, t: number) => JSON.stringify([kind, id, t]);
  const add = (kind: string, id: string, t: number, cost: number, lo: number, hi: number) => {
    const index = colCost.length;
    columns.set(key(kind, id, t), index);
    colCost.push(cost);
    colLower.push(lo);
    colUpper.push(hi);
  };
  const ix = (kind: string, id: string, t: number) => {
    const v = columns.get(key(kind, id, t));
    if (v === undefined) throw new Error("Missing variable");
    return v;
  };
  for (const g of d.generators)
    for (let t = 0; t < H; t++)
      add("g", g.id, t, g.cost_eur_mwh * dt, g.min_mw?.[t] ?? 0, g.max_mw[t]!);
  for (const e of d.edges)
    for (let t = 0; t < H; t++) add("f", e.id, t, 0, -e.ba_mw[t]!, e.ab_mw[t]!);
  for (const r of d.flow_based_regions)
    for (const z of r.zones) for (let t = 0; t < H; t++) add("np", z, t, 0, -Infinity, Infinity);
  for (const z of d.zones)
    for (let t = 0; t < H; t++) {
      add("u", z, t, d.unserved_cost_eur_mwh * dt, 0, Infinity);
      add("spill", z, t, 0, 0, Infinity);
    }
  for (const s of d.storage) {
    for (let t = 0; t < H; t++) {
      add("charge", s.id, t, s.throughput_cost_eur_mwh * dt, 0, s.charge_power_mw ?? s.power_mw);
      add("discharge", s.id, t, s.throughput_cost_eur_mwh * dt, 0, s.power_mw);
      if (s.inflow_mw) add("water_spill", s.id, t, 0, 0, s.inflow_mw[t]!);
    }
    for (let t = 0; t <= H; t++) {
      const fixed = s.cyclic
        ? undefined
        : t === 0
          ? s.initial_mwh
          : t === H
            ? s.terminal_mwh
            : undefined;
      add("soc", s.id, t, 0, fixed ?? 0, fixed ?? s.energy_mwh);
    }
  }
  const starts = [0],
    indices: number[] = [],
    values: number[] = [],
    rowLower: number[] = [],
    rowUpper: number[] = [];
  const row = (entries: [number, number][], lo: number, hi: number) => {
    for (const [i, v] of entries)
      if (v !== 0) {
        indices.push(i);
        values.push(v);
      }
    starts.push(indices.length);
    rowLower.push(lo);
    rowUpper.push(hi);
  };
  for (const z of d.zones)
    for (let t = 0; t < H; t++) {
      const entries: [number, number][] = [
        [ix("u", z, t), 1],
        [ix("spill", z, t), -1],
      ];
      for (const g of d.generators) if (g.zone === z) entries.push([ix("g", g.id, t), 1]);
      for (const e of d.edges)
        if (e.a === z || e.b === z) entries.push([ix("f", e.id, t), e.a === z ? -1 : 1]);
      if (d.flow_based_regions.some((r) => r.zones.includes(z))) entries.push([ix("np", z, t), -1]);
      for (const s of d.storage)
        if (s.zone === z) entries.push([ix("charge", s.id, t), -1], [ix("discharge", s.id, t), 1]);
      const demand = d.load_mw[z]![t]! - d.external_net_import_mw[z]![t]!;
      row(entries, demand, demand);
    }
  for (const r of d.flow_based_regions) {
    for (let t = 0; t < H; t++)
      row(
        r.zones.map((z) => [ix("np", z, t), 1]),
        0,
        0,
      );
    for (const c of r.constraints)
      row(
        Object.entries(c.ptdf).map(([z, v]) => [ix("np", z, c.interval), v]),
        -Infinity,
        c.ram_mw,
      );
  }
  for (const s of d.storage)
    for (let t = 0; t < H; t++)
      row(
        [
          [ix("soc", s.id, t + 1), 1],
          [ix("soc", s.id, t), -Math.pow(1 - (s.standing_loss ?? 0), dt)],
          [ix("charge", s.id, t), -dt * s.charge_efficiency],
          [ix("discharge", s.id, t), dt / s.discharge_efficiency],
          ...(s.inflow_mw ? [[ix("water_spill", s.id, t), dt] as [number, number]] : []),
        ],
        dt * (s.inflow_mw?.[t] ?? 0),
        dt * (s.inflow_mw?.[t] ?? 0),
      );
  for (const s of d.storage)
    if (s.cyclic)
      row(
        [
          [ix("soc", s.id, 0), 1],
          [ix("soc", s.id, H), -1],
        ],
        0,
        0,
      );
  for (const g of d.generators) {
    if (g.energy_budget_mwh !== undefined)
      row(
        Array.from({ length: H }, (_, t) => [ix("g", g.id, t), dt]),
        -Infinity,
        g.energy_budget_mwh,
      );
    if (g.ramp_mw_per_hour !== undefined)
      for (let t = 1; t < H; t++)
        row(
          [
            [ix("g", g.id, t), 1],
            [ix("g", g.id, t - 1), -1],
          ],
          -g.ramp_mw_per_hour * dt,
          g.ramp_mw_per_hour * dt,
        );
  }
  const model: ModelData = {
    numCols: colCost.length,
    numRows: rowLower.length,
    colCost,
    colLower,
    colUpper,
    rowLower,
    rowUpper,
    matrix: {
      format: "csr",
      numRows: rowLower.length,
      numCols: colCost.length,
      starts: Int32Array.from(starts),
      indices: Int32Array.from(indices),
      values: Float64Array.from(values),
    },
  };
  return { model, ix };
}

/** Reuse native basis only when matrix, costs and row limits are identical. */
export class NetworkSolverSession {
  private model: Model | undefined;
  private signature = "";
  constructor(private highs: Highs) {}
  acquire(matrix: ModelData): Model {
    const signature = JSON.stringify([
      matrix.colCost,
      matrix.rowLower,
      matrix.rowUpper,
      matrix.matrix,
    ]);
    if (this.model && signature === this.signature) {
      this.model.changeColsBounds(
        { kind: "range", from: 0, to: matrix.numCols - 1 },
        matrix.colLower,
        matrix.colUpper,
      );
      this.model.zeroAllClocks();
    } else {
      this.model?.dispose();
      this.model = this.highs.createModel(matrix);
      this.signature = signature;
    }
    return this.model;
  }
  dispose() {
    this.model?.dispose();
    this.model = undefined;
    this.signature = "";
  }
}

function dispatchLinkedNetwork(
  highs: Highs,
  input: NetworkInput,
  session?: NetworkSolverSession,
): DispatchResult {
  const d = parseNetworkInput(input),
    { model: matrix, ix } = compileNetwork(d),
    H = d.timestamps.length,
    dt = d.interval_hours;
  const model = session ? session.acquire(matrix) : highs.createModel(matrix);
  try {
    model.options.set("output_flag", false);
    model.options.set("time_limit", 120);
    const result = model.run();
    if (result.modelStatus !== highs.constants.modelStatus.optimal)
      throw new Error(`No certified optimum (status ${result.modelStatus}); results withheld`);
    if (
      model.info.get("primal_solution_status") !== highs.constants.solutionStatus.feasible ||
      model.info.get("dual_solution_status") !== highs.constants.solutionStatus.feasible
    ) {
      throw new Error("Primal/dual solution unavailable; results withheld");
    }
    const solution = model.getSolution(),
      x = solution.colValue;
    if ([...x].some((v) => !Number.isFinite(v))) throw new Error("Nonfinite solver solution");
    const costs = matrix.colCost as number[],
      lo = matrix.colLower as number[],
      hi = matrix.colUpper as number[],
      rl = matrix.rowLower as number[],
      rh = matrix.rowUpper as number[];
    const a = matrix.matrix;
    let residual = 0,
      cost = 0;
    for (let j = 0; j < x.length; j++) {
      residual = Math.max(residual, lo[j]! - x[j]!, x[j]! - hi[j]!);
      cost += x[j]! * costs[j]!;
    }
    for (let r = 0; r < rl.length; r++) {
      let value = 0;
      for (let k = a.starts[r]!; k < a.starts[r + 1]!; k++)
        value += a.values[k]! * x[a.indices[k]!]!;
      residual = Math.max(residual, rl[r]! - value, value - rh[r]!);
    }
    if (
      !Number.isFinite(residual) ||
      !Number.isFinite(cost) ||
      residual > 1e-5 ||
      Math.abs(cost - model.getObjectiveValue()) > Math.max(1e-4, Math.abs(cost) * 1e-9)
    )
      throw new Error("Independent constraint/objective reconciliation failed");
    const series = (kind: string, id: string, n = H) =>
      Array.from({ length: n }, (_, t) => x[ix(kind, id, t)]!);
    const generation = Object.fromEntries(d.generators.map((g) => [g.id, series("g", g.id)]));
    const completeEmissions =
      d.generators.length > 0 && d.generators.every((g) => g.co2_t_per_mwh != null);
    let co2 = 0;
    for (const g of d.generators)
      co2 += generation[g.id]!.reduce((a, b) => a + b, 0) * dt * (g.co2_t_per_mwh ?? 0);
    const storage = Object.fromEntries(
      d.storage.map((s) => [
        s.id,
        {
          charge_mw: series("charge", s.id),
          discharge_mw: series("discharge", s.id),
          soc_mwh: series("soc", s.id, H + 1),
          spill_mw: s.inflow_mw ? series("water_spill", s.id) : Array(H).fill(0),
        },
      ]),
    );
    return {
      total_cost_eur: cost,
      total_co2_t: completeEmissions ? co2 : null,
      max_constraint_violation: residual,
      unserved_mwh: d.zones.reduce(
        (sum, z) => sum + series("u", z).reduce((a, b) => a + b, 0) * dt,
        0,
      ),
      spill_mwh: d.zones.reduce(
        (sum, z) => sum + series("spill", z).reduce((a, b) => a + b, 0) * dt,
        0,
      ),
      simultaneous_storage_intervals: Object.values(storage).reduce(
        (sum, s) =>
          sum + s.charge_mw.filter((v, t) => v > 1e-6 && s.discharge_mw[t]! > 1e-6).length,
        0,
      ),
      generation_mw: generation,
      flow_mw: Object.fromEntries(d.edges.map((e) => [e.id, series("f", e.id)])),
      storage,
      price_eur_mwh: Object.fromEntries(
        d.zones.map((z, i) => [
          z,
          Array.from({ length: H }, (_, t) => solution.rowDual[i * H + t]! / dt),
        ]),
      ),
    };
  } finally {
    if (!session) model.dispose();
  }
}

export function compareDispatch(baseline: DispatchResult, scenario: DispatchResult) {
  const benefit = baseline.total_cost_eur - scenario.total_cost_eur;
  if (benefit < -Math.max(0.01, Math.abs(baseline.total_cost_eur) * 1e-8))
    throw new Error("Capacity relaxation increased optimized cost");
  return {
    status: "experimental_not_validated" as const,
    period_benefit_eur: benefit,
    avoided_co2_t:
      baseline.total_co2_t !== null && scenario.total_co2_t !== null
        ? baseline.total_co2_t - scenario.total_co2_t
        : null,
    scarcity_affected: baseline.unserved_mwh > 1e-6 || scenario.unserved_mwh > 1e-6,
    storage_relaxation_affected:
      baseline.simultaneous_storage_intervals > 0 || scenario.simultaneous_storage_intervals > 0,
  };
}

/** Exact decomposition only when there are no intertemporal restrictions. */
export function dispatchNetwork(
  highs: Highs,
  input: NetworkInput,
  session?: NetworkSolverSession,
): DispatchResult {
  const d = parseNetworkInput(input);
  const linked =
    d.storage.length > 0 ||
    d.generators.some((g) => g.energy_budget_mwh !== undefined || g.ramp_mw_per_hour !== undefined);
  if (linked || d.timestamps.length <= 24) return dispatchLinkedNetwork(highs, d, session);
  const active = session ?? new NetworkSolverSession(highs);
  let aggregate: DispatchResult | undefined;
  try {
    for (let start = 0; start < d.timestamps.length; start += 24) {
      const end = Math.min(start + 24, d.timestamps.length);
      const chunk: NetworkInput = {
        ...d,
        timestamps: d.timestamps.slice(start, end),
        load_mw: Object.fromEntries(
          Object.entries(d.load_mw).map(([z, v]) => [z, v.slice(start, end)]),
        ),
        external_net_import_mw: Object.fromEntries(
          Object.entries(d.external_net_import_mw).map(([z, v]) => [z, v.slice(start, end)]),
        ),
        generators: d.generators.map((g) => ({
          ...g,
          max_mw: g.max_mw.slice(start, end),
          ...(g.min_mw ? { min_mw: g.min_mw.slice(start, end) } : {}),
        })),
        edges: d.edges.map((e) => ({
          ...e,
          ab_mw: e.ab_mw.slice(start, end),
          ba_mw: e.ba_mw.slice(start, end),
        })),
        flow_based_regions: d.flow_based_regions.map((r) => ({
          ...r,
          constraints: r.constraints
            .filter((c) => c.interval >= start && c.interval < end)
            .map((c) => ({ ...c, interval: c.interval - start })),
        })),
      };
      const next = dispatchLinkedNetwork(highs, chunk, active);
      if (!aggregate) aggregate = next;
      else {
        aggregate.total_cost_eur += next.total_cost_eur;
        aggregate.total_co2_t =
          aggregate.total_co2_t !== null && next.total_co2_t !== null
            ? aggregate.total_co2_t + next.total_co2_t
            : null;
        aggregate.unserved_mwh += next.unserved_mwh;
        aggregate.spill_mwh += next.spill_mwh;
        aggregate.max_constraint_violation = Math.max(
          aggregate.max_constraint_violation,
          next.max_constraint_violation,
        );
        for (const property of ["price_eur_mwh", "generation_mw", "flow_mw"] as const)
          for (const [id, values] of Object.entries(next[property]))
            aggregate[property][id]!.push(...values);
      }
    }
    return aggregate!;
  } finally {
    if (!session) active.dispose();
  }
}
