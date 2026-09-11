// @ts-nocheck -- kept byte-identical to the supplied reference implementation
/**
 * WaterTrace water signal engine — pure TypeScript, no dependencies.
 * Use the same file in the backend server module and in the frontend (src/lib/waterEngine.ts).
 *
 * Units: power in MW, water intensity in L/MWh (divide by 1000 for L/kWh),
 * hourly water volume in L/h (MW x L/MWh).
 */

export type Metric = "consumption" | "withdrawal";
export type Scope = "freshwater" | "total";
export type CoolingTech = "tower" | "once_through" | "once_through_sea" | "pond" | "dry";
export type ThermalFuel = "nuclear" | "coal" | "gas" | "oil" | "biomass";
export type SingleSource = "geothermal" | "solar" | "wind" | "hydro";

export const GENERATION_SOURCES = [
  "nuclear", "geothermal", "biomass", "coal", "wind", "solar",
  "hydro", "gas", "oil", "unknown", "hydro storage", "battery storage",
] as const;
export type Source = (typeof GENERATION_SOURCES)[number];

const THERMAL: ThermalFuel[] = ["nuclear", "coal", "gas", "oil", "biomass"];

export interface FactorStat { median: number; min: number; max: number }
export interface FactorPair { consumption: FactorStat; withdrawal: FactorStat }
export interface WaterFactors {
  thermal: Record<ThermalFuel, Partial<Record<Exclude<CoolingTech, "once_through_sea">, FactorPair>>>;
  single: Record<SingleSource, FactorPair>;
}
export type CoolingShares = Partial<Record<CoolingTech, number>>;
export interface ZoneProfile { key: string; cooling: Partial<Record<ThermalFuel, CoolingShares>>; calibrated?: boolean }
export interface Profiles { default: CoolingShares; zones: ZoneProfile[] }

/** Electricity Maps v4 `mix` object (values in MW). Storage may be a number or {charge, discharge}. */
export type EmMix = Partial<Record<Source, number | { charge?: number; discharge?: number } | null>> & {
  flows?: { imports?: number; exports?: number } | null;
};

export interface Options {
  metric: Metric;          // consumption (default headline) or withdrawal
  scope: Scope;            // freshwater (headline) or total (incl. seawater)
  includeHydro: boolean;   // add reservoir evaporation (low confidence)
  stat?: "median" | "min" | "max"; // uncertainty band
}
export const DEFAULT_OPTIONS: Options = { metric: "consumption", scope: "freshwater", includeHydro: false, stat: "median" };

export interface SourceBreakdown { mw: number; factor: number; waterLph: number }
export interface ProductionResult {
  zone: string;
  intensity: number;            // L/MWh of domestic generation
  waterLph: number;             // L/h
  generationMW: number;
  bySource: Record<string, SourceBreakdown>;
  profileCalibrated: boolean;
}

export class WaterEngine {
  private factors: WaterFactors;
  private profiles: Profiles;
  private profileByKey: Map<string, ZoneProfile>;

  constructor(factors: WaterFactors, profiles: Profiles) {
    this.factors = factors;
    this.profiles = profiles;
    this.profileByKey = new Map(profiles.zones.map((z) => [z.key, z]));
  }

  /** Cooling shares for a thermal fuel in a zone (falls back to the default profile). */
  coolingShares(zone: string, fuel: ThermalFuel): CoolingShares {
    return this.profileByKey.get(zone)?.cooling?.[fuel] ?? this.profiles.default;
  }

  /** Water factor (L/MWh) for one thermal fuel in one zone, weighted by cooling technology shares. */
  thermalFactor(zone: string, fuel: ThermalFuel, o: Options): number {
    const stat = o.stat ?? "median";
    const shares = this.coolingShares(zone, fuel);
    const techs = this.factors.thermal[fuel];
    let f = 0;
    for (const [tech, share] of Object.entries(shares) as [CoolingTech, number][]) {
      if (!share) continue;
      if (tech === "once_through_sea" && o.scope === "freshwater") continue; // seawater = 0 freshwater
      const lookup = tech === "once_through_sea" ? "once_through" : tech;
      const pair = techs[lookup as keyof typeof techs] ?? techs.tower!; // missing tech -> tower
      f += share * pair[o.metric][stat];
    }
    return f;
  }

  singleFactor(source: SingleSource, o: Options): number {
    if (source === "hydro" && !o.includeHydro) return 0;
    return this.factors.single[source][o.metric][o.stat ?? "median"];
  }

  /** Domestic generation water intensity for one timestamp (use breakdownType=normal mix). */
  production(zone: string, mix: EmMix, o: Options = DEFAULT_OPTIONS): ProductionResult {
    const bySource: Record<string, SourceBreakdown> = {};
    let thermalWater = 0, thermalMw = 0;
    const mwOf = (s: Source): number => {
      const v = mix[s];
      if (v == null) return 0;
      if (typeof v === "number") return Math.max(0, v);
      return Math.max(0, v.discharge ?? 0); // storage: only discharge is supply
    };
    for (const s of GENERATION_SOURCES) {
      if (s === "unknown") continue;
      const mw = mwOf(s);
      let factor = 0;
      if ((THERMAL as string[]).includes(s)) {
        factor = this.thermalFactor(zone, s as ThermalFuel, o);
        thermalWater += mw * factor; thermalMw += mw;
      } else if (s === "geothermal" || s === "solar" || s === "wind" || s === "hydro") {
        factor = this.singleFactor(s, o);
      } // storage discharge: factor 0
      bySource[s] = { mw, factor, waterLph: mw * factor };
    }
    const unknownMw = mwOf("unknown");
    const unknownFactor = thermalMw > 0 ? thermalWater / thermalMw : this.thermalFactor(zone, "gas", o);
    bySource["unknown"] = { mw: unknownMw, factor: unknownFactor, waterLph: unknownMw * unknownFactor };
    const generationMW = Object.values(bySource).reduce((a, b) => a + b.mw, 0);
    const waterLph = Object.values(bySource).reduce((a, b) => a + b.waterLph, 0);
    return {
      zone, bySource, generationMW, waterLph,
      intensity: generationMW > 0 ? waterLph / generationMW : 0,
      profileCalibrated: this.profileByKey.get(zone)?.calibrated ?? false,
    };
  }

  /**
   * W1/W2/W3 — consumption-based (flow-traced) intensity, one-hop version.
   * imports: MW imported from each neighbour (Electricity Maps electricity-flows `import`).
   * neighbourIntensity: production intensity (L/MWh) of each neighbour at the same timestamp.
   * Exports do not change the intensity of what is consumed (proportional sharing).
   */
  consumptionOneHop(
    local: ProductionResult,
    imports: Record<string, number>,
    neighbourIntensity: Record<string, number | undefined>,
  ) {
    const byOrigin: Record<string, { mw: number; intensity: number; waterLph: number; estimated: boolean }> = {};
    let impMw = 0, impWater = 0;
    for (const [nb, raw] of Object.entries(imports ?? {})) {
      const mw = Math.max(0, raw ?? 0);
      if (!mw) continue;
      const known = neighbourIntensity[nb];
      const intensity = known ?? local.intensity; // fallback: assume local intensity, flag it
      byOrigin[nb] = { mw, intensity, waterLph: mw * intensity, estimated: known == null };
      impMw += mw; impWater += mw * intensity;
    }
    const totalMw = local.generationMW + impMw;
    const totalWater = local.waterLph + impWater;
    return {
      intensity: totalMw > 0 ? totalWater / totalMw : 0,   // L/MWh consumed
      importedShare: totalWater > 0 ? impWater / totalWater : 0, // W3
      importedPowerShare: totalMw > 0 ? impMw / totalMw : 0,
      local: { mw: local.generationMW, intensity: local.intensity, waterLph: local.waterLph },
      byOrigin,
    };
  }
}

/**
 * V2 — full network flow tracing (proportional sharing, Bialek 1996 / Tranberg et al. 2019).
 * For each zone i:  x_i * (P_i + sum_j F_ji) = W_i + sum_j F_ji * x_j
 * zones: domestic generation (MW) and water (L/h). flows: MW from -> to (positive).
 * boundary: intensities of zones outside the solved set that export into it.
 */
export function networkTrace(
  zones: Record<string, { generationMW: number; waterLph: number }>,
  flows: { from: string; to: string; mw: number }[],
  boundary: Record<string, number> = {},
  iterations = 200, tol = 1e-6,
): Record<string, number> {
  const x: Record<string, number> = {};
  for (const [k, z] of Object.entries(zones)) x[k] = z.generationMW > 0 ? z.waterLph / z.generationMW : 0;
  const inflows: Record<string, { from: string; mw: number }[]> = {};
  for (const f of flows) if (f.mw > 0) (inflows[f.to] ??= []).push({ from: f.from, mw: f.mw });
  for (let it = 0; it < iterations; it++) {
    let delta = 0;
    for (const [k, z] of Object.entries(zones)) {
      let num = z.waterLph, den = z.generationMW;
      for (const f of inflows[k] ?? []) {
        const xf = f.from in x ? x[f.from] : boundary[f.from];
        if (xf == null) continue;
        num += f.mw * xf; den += f.mw;
      }
      const nx = den > 0 ? num / den : 0;
      delta = Math.max(delta, Math.abs(nx - x[k]));
      x[k] = nx;
    }
    if (delta < tol) break;
  }
  return x;
}

/** W4 — best contiguous window of `duration` steps (lowest mean). */
export function bestWindow(series: number[], duration: number): { start: number; mean: number } | null {
  if (duration <= 0 || series.length < duration) return null;
  let sum = 0;
  for (let i = 0; i < duration; i++) sum += series[i];
  let best = { start: 0, mean: sum / duration };
  for (let i = duration; i < series.length; i++) {
    sum += series[i] - series[i - duration];
    const mean = sum / duration;
    if (mean < best.mean) best = { start: i - duration + 1, mean };
  }
  return best;
}

/** W4 — label each step low / medium / high by tertile of the horizon. */
export function tertileLabels(series: number[]): ("low" | "medium" | "high")[] {
  const sorted = [...series].sort((a, b) => a - b);
  const q = (p: number) => sorted[Math.min(sorted.length - 1, Math.floor(p * sorted.length))];
  const t1 = q(1 / 3), t2 = q(2 / 3);
  return series.map((v) => (v < t1 ? "low" : v < t2 ? "medium" : "high"));
}

const minmax = (s: number[]) => {
  const lo = Math.min(...s), hi = Math.max(...s);
  return s.map((v) => (hi > lo ? (v - lo) / (hi - lo) : 0));
};

/** W5 — water/carbon/price co-optimisation score (0 = best). Price may be null (e.g. no price in zone). */
export function tripleScore(
  water: number[], carbon: number[], price: number[] | null,
  weights = { water: 1 / 3, carbon: 1 / 3, price: 1 / 3 },
) {
  const w = minmax(water), c = minmax(carbon), p = price ? minmax(price) : null;
  const wp = p ? weights.price : 0;
  const total = weights.water + weights.carbon + wp || 1;
  const score = w.map((_, i) => (weights.water * w[i] + weights.carbon * c[i] + (p ? wp * p[i] : 0)) / total);
  // trade-off flag: low-carbon but high-water hours (e.g. nuclear on tower cooling)
  const tradeOff = w.map((_, i) => c[i] < 0.33 && w[i] > 0.66);
  return { score, tradeOff };
}

/** A1 — facility operational water footprint. EWIF in L/MWh per step; IT energy in kWh per step. */
export function facilityFootprint(itKwh: number[], ewifLperMWh: number[], wue: number, pue: number) {
  let direct = 0, indirect = 0;
  for (let i = 0; i < itKwh.length; i++) {
    direct += itKwh[i] * wue;
    indirect += itKwh[i] * pue * (ewifLperMWh[i] / 1000);
  }
  return { directL: direct, indirectL: indirect, totalL: direct + indirect, indirectShare: direct + indirect > 0 ? indirect / (direct + indirect) : 0 };
}
