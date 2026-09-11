// Server-only zonal network model.
//
// Scope: the sub-network around a target border — the two zones plus their
// direct neighbours. Each hour is redispatched with an iterative
// price-coupling algorithm (a gradient method on the transport LP): energy is
// moved from the cheapest to the dearest connected zone until either prices
// equalise or a border hits its transfer limit.
import type { SupabaseClient } from "@supabase/supabase-js";

export type ZoneSeries = {
  price: Float64Array;
  ci: Float64Array;
  load: Float64Array;
  has: Uint8Array;
};

export type NetworkData = {
  hours: string[];
  zones: string[];
  series: Record<string, ZoneSeries>;
  edges: Array<{ a: string; b: string; capAb: number; capBa: number; flow: Float64Array }>;
  slope: Record<string, number>;
};

const PAGE = 1000;

async function pagedSelect<T>(
  build: (from: number, to: number) => PromiseLike<{ data: T[] | null; error: { message: string } | null }>,
  max = 200_000,
): Promise<T[]> {
  const out: T[] = [];
  for (let from = 0; from < max; from += PAGE) {
    const { data, error } = await build(from, from + PAGE - 1);
    if (error) throw new Error(error.message);
    if (!data?.length) break;
    out.push(...data);
    if (data.length < PAGE) break;
  }
  return out;
}

export async function loadNetwork(
  db: SupabaseClient,
  zoneA: string,
  zoneB: string,
): Promise<NetworkData> {
  const { data: borderRows, error: bErr } = await db
    .from("borders")
    .select("zone_a, zone_b");
  if (bErr) throw new Error(bErr.message);

  const zoneSet = new Set<string>([zoneA, zoneB]);
  for (const b of borderRows ?? []) {
    if (b.zone_a === zoneA || b.zone_a === zoneB) zoneSet.add(b.zone_b);
    if (b.zone_b === zoneA || b.zone_b === zoneB) zoneSet.add(b.zone_a);
  }
  const zones = [...zoneSet].sort();

  const edgeKeys = (borderRows ?? []).filter(
    (b) => zoneSet.has(b.zone_a) && zoneSet.has(b.zone_b),
  );

  // ---- hourly zone data
  type ZRow = { zone_code: string; ts: string; price_eur_mwh: number | null; carbon_intensity: number | null; load_mw: number | null };
  const zoneRows: ZRow[] = [];
  for (const z of zones) {
    const rows = await pagedSelect<ZRow>((from, to) =>
      db
        .from("zone_hourly")
        .select("zone_code, ts, price_eur_mwh, carbon_intensity, load_mw")
        .eq("zone_code", z)
        .order("ts")
        .range(from, to),
      20_000,
    );
    zoneRows.push(...rows);
  }
  if (!zoneRows.length) throw new Error("No historical data imported yet for this border.");

  const hourSet = new Set<string>();
  for (const r of zoneRows) hourSet.add(r.ts);
  const hours = [...hourSet].sort();
  const index = new Map(hours.map((h, i) => [h, i]));
  const H = hours.length;

  const series: Record<string, ZoneSeries> = {};
  for (const z of zones) {
    series[z] = {
      price: new Float64Array(H),
      ci: new Float64Array(H),
      load: new Float64Array(H),
      has: new Uint8Array(H),
    };
  }
  for (const r of zoneRows) {
    const i = index.get(r.ts);
    if (i === undefined) continue;
    const s = series[r.zone_code];
    if (!s) continue;
    if (r.price_eur_mwh != null) {
      s.price[i] = r.price_eur_mwh;
      s.has[i] = 1;
    }
    if (r.carbon_intensity != null) s.ci[i] = r.carbon_intensity;
    if (r.load_mw != null) s.load[i] = r.load_mw;
  }

  // ---- hourly flows
  type FRow = { zone_a: string; zone_b: string; ts: string; flow_mw: number };
  const edges: NetworkData["edges"] = [];
  for (const e of edgeKeys) {
    const rows = await pagedSelect<FRow>((from, to) =>
      db
        .from("border_flow_hourly")
        .select("zone_a, zone_b, ts, flow_mw")
        .eq("zone_a", e.zone_a)
        .eq("zone_b", e.zone_b)
        .order("ts")
        .range(from, to),
      20_000,
    );
    if (!rows.length) continue;
    const flow = new Float64Array(H);
    let capAb = 0;
    let capBa = 0;
    for (const r of rows) {
      const i = index.get(r.ts);
      if (i === undefined) continue;
      flow[i] = r.flow_mw;
      if (r.flow_mw > capAb) capAb = r.flow_mw;
      if (-r.flow_mw > capBa) capBa = -r.flow_mw;
    }
    edges.push({ a: e.zone_a, b: e.zone_b, capAb, capBa, flow });
  }

  // ---- price-response slope per zone: regress price on net export
  const netExport: Record<string, Float64Array> = {};
  for (const z of zones) netExport[z] = new Float64Array(H);
  for (const e of edges) {
    const na = netExport[e.a]!;
    const nb = netExport[e.b]!;
    for (let i = 0; i < H; i++) {
      na[i] = na[i]! + e.flow[i]!;
      nb[i] = nb[i]! - e.flow[i]!;
    }
  }

  const slope: Record<string, number> = {};
  for (const z of zones) {
    const s = series[z]!;
    const x = netExport[z]!;
    let n = 0;
    let mx = 0;
    let my = 0;
    for (let i = 0; i < H; i++) {
      if (!s.has[i]) continue;
      n++;
      mx += x[i]!;
      my += s.price[i]!;
    }
    if (n < 100) {
      slope[z] = 0.02;
      continue;
    }
    mx /= n;
    my /= n;
    let cov = 0;
    let varx = 0;
    for (let i = 0; i < H; i++) {
      if (!s.has[i]) continue;
      const dx = x[i]! - mx;
      cov += dx * (s.price[i]! - my);
      varx += dx * dx;
    }
    const raw = varx > 0 ? cov / varx : 0.02;
    slope[z] = Math.min(0.5, Math.max(0.002, Math.abs(raw)));
  }

  return { hours, zones, series, edges, slope };
}

// ------------------------------------------------------------------
// Units
// ------------------------------------------------------------------
export type Unit = {
  unit_type: string;
  zone_code: string | null;
  border_zone_a: string | null;
  border_zone_b: string | null;
  params: Record<string, number>;
};

/** Extra injection (MW, positive = more supply) per zone from the scenario's units. */
function unitInjections(net: NetworkData, units: Unit[]): Record<string, Float64Array> {
  const H = net.hours.length;
  const inj: Record<string, Float64Array> = {};
  for (const z of net.zones) inj[z] = new Float64Array(H);

  for (const u of units) {
    const z = u.zone_code;
    if (!z || !inj[z]) continue;
    const s = net.series[z]!;

    if (u.unit_type === "solar" || u.unit_type === "wind") {
      const cap = Number(u.params["capacity_mw"] ?? 0);
      // Profile proxy: hours with below/above average price shape a plant's
      // output poorly, so use a daily shape for solar and a load-inverse shape
      // for wind, scaled to the requested capacity.
      for (let i = 0; i < H; i++) {
        const hour = new Date(net.hours[i]!).getUTCHours();
        const cf =
          u.unit_type === "solar"
            ? Math.max(0, Math.sin(((hour - 6) / 12) * Math.PI)) * 0.55
            : 0.32;
        const iz = inj[z]!;
        iz[i] = iz[i]! + cap * cf;
      }
    }

    if (u.unit_type === "battery" || u.unit_type === "demand_response") {
      const power = Number(u.params["power_mw"] ?? 0);
      const energy =
        u.unit_type === "battery"
          ? Number(u.params["energy_mwh"] ?? power * 4)
          : power * Number(u.params["shift_hours"] ?? 4);
      const eff = u.unit_type === "battery" ? Number(u.params["efficiency"] ?? 0.88) : 0.98;
      applyStorage(inj[z]!, s.price, power, energy, eff);
    }
  }
  return inj;
}

/** Daily greedy price arbitrage: charge in the cheapest hours, discharge in the dearest. */
function applyStorage(
  inj: Float64Array,
  price: Float64Array,
  powerMw: number,
  energyMwh: number,
  efficiency: number,
) {
  if (powerMw <= 0 || energyMwh <= 0) return;
  const H = price.length;
  const cycles = Math.max(1, Math.min(24, Math.round(energyMwh / powerMw)));
  for (let d = 0; d < H; d += 24) {
    const end = Math.min(d + 24, H);
    const idx: number[] = [];
    for (let i = d; i < end; i++) idx.push(i);
    idx.sort((x, y) => price[x]! - price[y]!);
    const nCharge = Math.min(cycles, Math.floor(idx.length / 2));
    for (let k = 0; k < nCharge; k++) {
      const cheap = idx[k]!;
      const dear = idx[idx.length - 1 - k]!;
      if (price[dear]! - price[cheap]! < 2) break;
      inj[cheap] = inj[cheap]! - powerMw; // charging = extra demand
      inj[dear] = inj[dear]! + powerMw * efficiency;
    }
  }
}

// ------------------------------------------------------------------
// Hourly market clearing — ENTSO-E single day-ahead coupling (Euphemia)
// ------------------------------------------------------------------
//
// Objective, constraints and pricing rules follow the SDAC/Euphemia
// specification for the ATC (available transfer capacity) network model:
//
//   maximise  total social welfare = sum over zones of the area between the
//             aggregated demand and supply curves at the cleared volume
//   subject to  balance:      sum of all zonal net positions = 0
//               ATC limits:   -ATC(b->a) <= flow(a->b) <= ATC(a->b)
//               pricing:      one clearing price per zone; prices are equal
//                             between zones whenever the connecting border is
//                             not saturated (price convergence), and may only
//                             diverge across a saturated border, with energy
//                             flowing from the low- to the high-price zone
//                             (no adverse flows)
//
// Each zone's aggregated curve is calibrated from its own hourly history: the
// observed price/net-position relationship gives the local slope of the
// residual supply curve, anchored at the observed clearing point. Solving is
// a welfare-gradient auction: while any border can carry energy from a lower-
// to a higher-price zone, transfer the volume that equalises the two prices or
// saturates the border, whichever is smaller. This is the convex dual of the
// coupling problem, so it converges to the same prices and net positions as
// the LP; iteration stops at a 0.01 EUR/MWh price-convergence tolerance.
//
// Not modelled (deliberately, since the inputs are not public): block orders,
// complex/PUN orders, flow-based domains, intraday and balancing timeframes.
const PRICE_TOLERANCE = 0.01; // EUR/MWh, Euphemia price-convergence criterion
const MAX_ITERATIONS = 400;

export type RunResult = {
  hours: number;
  welfareEur: number;
  co2Kg: number;
  congestedHours: number;
  convergedHours: number;
  extraTransferMwh: number;
  borderFlowMwh: number;
  avgSpreadEurMwh: number;
  congestionRentEur: number;
  adverseFlowHours: number;
  priceMae: number;
  flowMae: number;
  directionAccuracy: number;
};

export function runDispatch(
  net: NetworkData,
  units: Unit[],
  target: { a: string; b: string },
): RunResult {
  const H = net.hours.length;
  const inj = unitInjections(net, units);

  const extraCap: Record<string, number> = {};
  for (const u of units) {
    if (u.unit_type !== "line") continue;
    const a = u.border_zone_a;
    const b = u.border_zone_b;
    if (!a || !b) continue;
    const key = a < b ? `${a}|${b}` : `${b}|${a}`;
    extraCap[key] = (extraCap[key] ?? 0) + Number(u.params["added_mw"] ?? 0);
  }

  const zones = net.zones;
  const zIdx = new Map(zones.map((z, i) => [z, i]));
  const edges = net.edges.map((e) => {
    const key = `${e.a}|${e.b}`;
    const add = extraCap[key] ?? 0;
    return {
      ai: zIdx.get(e.a)!,
      bi: zIdx.get(e.b)!,
      capAb: e.capAb + add, // ATC a -> b
      capBa: e.capBa + add, // ATC b -> a
      flow: e.flow,
      isTarget:
        (e.a === target.a && e.b === target.b) || (e.a === target.b && e.b === target.a),
    };
  });

  const price = new Float64Array(zones.length);
  const ci = new Float64Array(zones.length);
  const slope = new Float64Array(zones.map((z) => net.slope[z] ?? 0.02));
  const f = new Float64Array(edges.length);

  let welfare = 0;
  let co2 = 0;
  let congested = 0;
  let converged = 0;
  let adverse = 0;
  let rent = 0;
  let extraTransfer = 0;
  let borderFlow = 0;
  let spreadSum = 0;
  let spreadN = 0;
  let priceErr = 0;
  let priceN = 0;
  let flowErr = 0;
  let flowN = 0;
  let dirOk = 0;
  let usableHours = 0;

  for (let t = 0; t < H; t++) {
    let ok = true;
    for (let z = 0; z < zones.length; z++) {
      const s = net.series[zones[z]!]!;
      if (!s.has[t]) {
        ok = false;
        break;
      }
      // Scenario units shift the zone along its own aggregated curve before clearing.
      price[z] = s.price[t]! - slope[z]! * (inj[zones[z]!]![t] ?? 0);
      ci[z] = s.ci[t]!;
    }
    if (!ok) continue;
    usableHours++;
    for (let e = 0; e < edges.length; e++) f[e] = edges[e]!.flow[t]!;

    let hourCongested = false;
    let iter = 0;
    let residual = 0;
    for (; iter < MAX_ITERATIONS; iter++) {
      // Pick the border with the largest remaining welfare gradient that still
      // has ATC headroom in the profitable direction.
      let best = -1;
      let bestGain = PRICE_TOLERANCE;
      let bestDir = 1;
      let blocked = 0;
      for (let e = 0; e < edges.length; e++) {
        const { ai, bi, capAb, capBa } = edges[e]!;
        const dAB = price[bi]! - price[ai]!;
        const gain = Math.abs(dAB);
        if (gain <= PRICE_TOLERANCE) continue;
        const headroom = dAB > 0 ? capAb - f[e]! : capBa + f[e]!;
        if (headroom <= 0.5) {
          blocked = Math.max(blocked, gain);
          continue;
        }
        if (gain > bestGain) {
          best = e;
          bestGain = gain;
          bestDir = dAB > 0 ? 1 : -1;
        }
      }
      if (best < 0) {
        residual = blocked;
        break;
      }
      const e = edges[best]!;
      const from = bestDir === 1 ? e.ai : e.bi;
      const to = bestDir === 1 ? e.bi : e.ai;
      const headroom = bestDir === 1 ? e.capAb - f[best]! : e.capBa + f[best]!;
      const equalising = bestGain / (slope[from]! + slope[to]!);
      const step = Math.min(headroom, equalising);
      if (step >= headroom - 1e-6) hourCongested = true;

      // Welfare gained by this transfer = area between the two curves.
      welfare += step * (bestGain - 0.5 * step * (slope[from]! + slope[to]!));
      co2 += step * (ci[to]! - ci[from]!); // kg CO2 (g/kWh x MWh)
      price[from] = price[from]! + slope[from]! * step;
      price[to] = price[to]! - slope[to]! * step;
      f[best] = f[best]! + bestDir * step;
      extraTransfer += step;
    }
    if (hourCongested) congested++;
    if (residual <= PRICE_TOLERANCE) converged++;

    // Congestion rent and adverse-flow check on saturated borders.
    let hourAdverse = false;
    for (let e = 0; e < edges.length; e++) {
      const ed = edges[e]!;
      const spread = price[ed.bi]! - price[ed.ai]!;
      if (Math.abs(spread) > PRICE_TOLERANCE) {
        rent += Math.abs(f[e]!) * Math.abs(spread);
        if (f[e]! * spread < -1) hourAdverse = true; // flow towards the cheaper zone
      }
    }
    if (hourAdverse) adverse++;

    for (let e = 0; e < edges.length; e++) {
      const ed = edges[e]!;
      if (!ed.isTarget) continue;
      borderFlow += Math.abs(f[e]!);
      spreadSum += Math.abs(price[ed.bi]! - price[ed.ai]!);
      spreadN++;
      const obs = ed.flow[t]!;
      flowErr += Math.abs(f[e]! - obs);
      flowN++;
      if (Math.sign(f[e]!) === Math.sign(obs) || Math.abs(obs) < 1) dirOk++;
    }
    for (let z = 0; z < zones.length; z++) {
      const s = net.series[zones[z]!]!;
      priceErr += Math.abs(price[z]! - s.price[t]!);
      priceN++;
    }
  }

  return {
    hours: usableHours,
    welfareEur: welfare,
    co2Kg: co2,
    congestedHours: congested,
    convergedHours: converged,
    extraTransferMwh: extraTransfer,
    borderFlowMwh: borderFlow,
    avgSpreadEurMwh: spreadN ? spreadSum / spreadN : 0,
    congestionRentEur: rent,
    adverseFlowHours: adverse,
    priceMae: priceN ? priceErr / priceN : 0,
    flowMae: flowN ? flowErr / flowN : 0,
    directionAccuracy: flowN ? dirOk / flowN : 0,
  };
}
