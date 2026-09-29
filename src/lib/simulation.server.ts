// Server-only zonal network model.
//
// Scope: the sub-network around a target border — the two zones plus their
// direct neighbours. Each hour is redispatched with an iterative
// price-coupling algorithm (a gradient method on the transport LP): energy is
// moved from the cheapest to the dearest connected zone until either prices
// equalise or a border hits its transfer limit.
//
// Inputs come from the static PyPSA-Eur baseline in public/research/baseline/,
// loaded by baseline-static.server.ts. Transfer limits are declared in
// cross_borders.json; they are never inferred from observed flow.
import { loadStaticNetwork } from "./baseline-static.server";

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

export async function loadNetwork(zoneA: string, zoneB: string): Promise<NetworkData> {
  return loadStaticNetwork(zoneA, zoneB);
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
// Each zone's aggregated curve is calibrated from its own hourly history (see
// baseline-static.server.ts): the observed marginal price is the clearing point,
// and the slope is the local inverse-elasticity of the residual supply curve.
//
// Solving is a damped Newton ascent on the dual of the coupling problem, run per
// hour. Candidate transfers are batched one per border, each pushed towards the
// direction that would equalise that border's two prices. For a batch scaled by
// a, the welfare gain is exactly quadratic in the transfer volumes under the
// linearised zonal curves:
//
//   dW(a) = a * sum_e x_e g_e  -  a^2 / 2 * sum_z s_z nu_z(a)^2
//
// where g_e is the price difference across border e, s_z is zone z's curve slope
// and nu_z is zone z's net export implied by the batch. The step length is the
// exact maximiser of that quadratic, a = G / Q, capped by the remaining ATC
// headroom, so every accepted iteration strictly increases welfare and the
// ascent is monotone.
//
// Batching is what keeps this from oscillating. Transferring on a single border
// at a time with the full step that equalises it overshoots that pair; the prices
// at both endpoints move, which makes a neighbouring border the new maximum, and
// its full step re-creates the spread just closed. Batching lets the line search
// see the cross terms and pick a step that is good for the whole sub-network.
//
// It stops on a KKT certificate, not on an iteration count: any interior border
// (one still with ATC headroom in the profitable direction) must have a price
// difference within PRICE_TOLERANCE. A saturated border is *allowed* to diverge —
// that divergence is the congestion rent, and treating it as a convergence error
// would mean the more congested an hour is, the less it counts as solved.
//
// Not modelled (deliberately, since the inputs are not public): block orders,
// complex/PUN orders, flow-based domains, intraday and balancing timeframes.
const PRICE_TOLERANCE = 0.01; // EUR/MWh, Euphemia price-convergence criterion
const MAX_ITERATIONS = 2000;
const CAP_EPSILON = 1e-6; // MW of ATC headroom still counted as interior
const MIN_STEP_MW = 1e-7; // below this a step cannot change anything meaningful

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
  /**
   * Congestion rent on the target border alone. The sub-network total can rise
   * while the target border is being relieved, because freeing energy at one
   * border shifts dispatch and can load up the others; this isolates the border
   * the scenario actually invests in.
   */
  targetRentEur: number;
  adverseFlowHours: number;
  priceMae: number;
  flowMae: number;
  directionAccuracy: number;
  /**
   * Largest price difference left on an *unsaturated* border, in EUR/MWh, over
   * every hour. This is the true KKT residual: at a solution it sits at or below
   * PRICE_TOLERANCE. Distinct from the spread on a saturated border, which is a
   * shadow price and legitimately non-zero.
   */
  maxDualResidualEurMwh: number;
  /** Total inner iterations across all hours, for the convergence/speed budget. */
  iterations: number;
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
    // Normalised like the extraCap keys above, so a unit's added_mw reaches this
    // border regardless of which way round the two zones are ordered.
    const key = e.a < e.b ? `${e.a}|${e.b}` : `${e.b}|${e.a}`;
    const add = extraCap[key] ?? 0;
    return {
      ai: zIdx.get(e.a)!,
      bi: zIdx.get(e.b)!,
      capAb: e.capAb + add, // ATC a -> b
      capBa: e.capBa + add, // ATC b -> a
      flow: e.flow,
      isTarget: (e.a === target.a && e.b === target.b) || (e.a === target.b && e.b === target.a),
    };
  });

  const price = new Float64Array(zones.length);
  const ci = new Float64Array(zones.length);
  const slope = new Float64Array(zones.map((z) => net.slope[z] ?? 0.02));
  const f = new Float64Array(edges.length);
  /** Per-border transfer in the current batch (MW, +ve = a -> b), and its zone imbalance. */
  const dirStep = new Float64Array(edges.length);
  const netExport = new Float64Array(zones.length);

  let welfare = 0;
  let co2 = 0;
  let congested = 0;
  let converged = 0;
  let adverse = 0;
  let rent = 0;
  let targetRent = 0;
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
  let maxDualResidual = 0;
  let totalIterations = 0;

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
    let hourSolved = false;

    for (; iter < MAX_ITERATIONS; iter++) {
      // 1. Direction per border: push towards equalising prices, but only as far
      //    as the ATC headroom allows. Borders already saturated in the
      //    profitable direction are binding, not unresolved, and are skipped.
      let anyInterior = false;
      let gradient = 0;
      residual = 0; // current KKT violation, not the worst ever seen
      for (let e = 0; e < edges.length; e++) {
        dirStep[e] = 0;
        const ed = edges[e]!;
        const g = price[ed.bi]! - price[ed.ai]!;
        const curvature = slope[ed.ai]! + slope[ed.bi]!;
        if (g > PRICE_TOLERANCE) {
          const head = ed.capAb - f[e]!;
          if (head <= CAP_EPSILON) continue;
          anyInterior = true;
          if (g > residual) residual = g;
          const x = Math.min(head, g / curvature);
          dirStep[e] = x;
          gradient += x * g;
        } else if (g < -PRICE_TOLERANCE) {
          const head = ed.capBa + f[e]!;
          if (head <= CAP_EPSILON) continue;
          anyInterior = true;
          if (-g > residual) residual = -g;
          const x = -Math.min(head, -g / curvature);
          dirStep[e] = x;
          gradient += x * g;
        }
      }
      if (!anyInterior || gradient <= 0) {
        hourSolved = true;
        break;
      }

      // 2. Imbalance the batch induces per zone, and the ATC limit on the step.
      netExport.fill(0);
      let stepLimit = Infinity;
      let batchSize = 0;
      for (let e = 0; e < edges.length; e++) {
        const x = dirStep[e]!;
        if (x === 0) continue;
        const ed = edges[e]!;
        netExport[ed.ai]! += x;
        netExport[ed.bi]! -= x;
        const head = x > 0 ? ed.capAb - f[e]! : ed.capBa + f[e]!;
        stepLimit = Math.min(stepLimit, head / Math.abs(x));
        batchSize += Math.abs(x);
      }

      // 3. Exact maximiser of the quadratic along this direction, capped so no
      //    border is pushed past its ATC. Because the cap is at a least 1 (the
      //    direction was already clipped to the headroom), the accepted step
      //    stays inside the increasing region and welfare strictly increases.
      let curvature2 = 0;
      for (let z = 0; z < zones.length; z++) {
        curvature2 += slope[z]! * netExport[z]! * netExport[z]!;
      }
      if (!(curvature2 > 0)) {
        hourSolved = true;
        break;
      }
      let a = gradient / curvature2;
      if (a > stepLimit) a = stepLimit;
      if (a * batchSize < MIN_STEP_MW) {
        hourSolved = true;
        break;
      }

      // 4. Apply the batch: welfare and CO2 from the same quadratic, prices from
      //    the curve slopes, flows from the batch direction.
      welfare += a * gradient - 0.5 * a * a * curvature2;
      for (let z = 0; z < zones.length; z++) {
        price[z] = price[z]! + a * slope[z]! * netExport[z]!;
      }
      for (let e = 0; e < edges.length; e++) {
        const x = dirStep[e]!;
        if (x === 0) continue;
        const ed = edges[e]!;
        const moved = a * x;
        const from = x > 0 ? ed.ai : ed.bi;
        const to = x > 0 ? ed.bi : ed.ai;
        co2 += moved * (ci[to]! - ci[from]!);
        f[e] = f[e]! + moved;
        // This border is now pinned against its ATC, so it can legitimately hold a
        // price difference: that divergence is the congestion rent.
        const limit = x > 0 ? ed.capAb : -ed.capBa;
        if (Math.abs(f[e]!) >= Math.abs(limit) - CAP_EPSILON) hourCongested = true;
      }
      extraTransfer += a * batchSize;
    }
    if (hourCongested) congested++;
    if (hourSolved) converged++;
    totalIterations += iter;
    if (residual > maxDualResidual) maxDualResidual = residual;

    // Congestion rent and adverse-flow check on saturated borders.
    let hourAdverse = false;
    for (let e = 0; e < edges.length; e++) {
      const ed = edges[e]!;
      const spread = price[ed.bi]! - price[ed.ai]!;
      if (Math.abs(spread) > PRICE_TOLERANCE) {
        rent += Math.abs(f[e]!) * Math.abs(spread);
        if (ed.isTarget) targetRent += Math.abs(f[e]!) * Math.abs(spread);
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
    targetRentEur: targetRent,
    adverseFlowHours: adverse,
    priceMae: priceN ? priceErr / priceN : 0,
    flowMae: flowN ? flowErr / flowN : 0,
    directionAccuracy: flowN ? dirOk / flowN : 0,
    maxDualResidualEurMwh: maxDualResidual,
    iterations: totalIterations,
  };
}
