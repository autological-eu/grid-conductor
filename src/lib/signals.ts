/**
 * WaterTrace signal service — computes W1–W4 (+ raw series for W5, A2) from Electricity Maps v4 data.
 * Pure TypeScript: the Electricity Maps client is injected (`emGet`), so this file runs unchanged
 * on the server (src/lib/signals.ts) and in tests.
 */

import { WaterEngine, DEFAULT_OPTIONS, tertileLabels, bestWindow, type EmMix, type Options, type WaterFactors, type Profiles } from "./waterEngine";

export type EmGet = (path: string, params: Record<string, string | number | boolean>) => Promise<any>;

export interface Point { datetime: string; mix?: EmMix; import?: Record<string, number>; export?: Record<string, number>; isEstimated?: boolean }

export interface SignalRequest {
  action: "latest" | "history" | "forecast" | "benchmark";
  zone?: string;
  zones?: string[];
  horizonHours?: 6 | 24 | 48 | 72;
  days?: number;               // benchmark look-back (<= 100 for daily granularity)
  includeHydro?: boolean;
  mode?: "origin" | "fast";    // origin = one-hop origin-aware tracing (default); fast = flow-traced mix x local factors
  jobHours?: number;           // W4 best-window length
}

const hourKey = (iso: string) => iso.slice(0, 13); // align on the hour (UTC)

export class SignalService {
  private engine: WaterEngine;
  private emGet: EmGet;

  constructor(factors: WaterFactors, profiles: Profiles, emGet: EmGet) {
    this.engine = new WaterEngine(factors, profiles);
    this.emGet = emGet;
  }

  private opts(req: SignalRequest, metric: Options["metric"], scope: Options["scope"] = "freshwater"): Options {
    return { ...DEFAULT_OPTIONS, metric, scope, includeHydro: !!req.includeHydro };
  }

  /** Fetch mix (normal) + flows for a zone for a given endpoint flavour. */
  private async fetchZone(zone: string, flavour: "latest" | "history" | "forecast", horizonHours?: number, breakdownType: "normal" | "flow-traced" = "normal") {
    const extra: Record<string, string | number> = flavour === "forecast" ? { horizonHours: horizonHours ?? 72 } : {};
    const [mix, flows] = await Promise.all([
      this.emGet(`/v4/electricity-mix/${flavour}`, { zone, breakdownType, ...extra }),
      this.emGet(`/v4/electricity-flows/${flavour}`, { zone, ...extra }).catch(() => ({ data: [] })),
    ]);
    return { mix: (mix?.data ?? []) as Point[], flows: (flows?.data ?? []) as Point[] };
  }

  /** Core computation for aligned series of one zone + its importing neighbours. */
  private async computeSeries(req: SignalRequest, flavour: "latest" | "history" | "forecast") {
    const zone = req.zone!;
    // fast mode: Electricity Maps' flow-traced mix already contains imported generation by source;
    // we apply the consuming zone's factors to it (1 call, ignores origin-specific cooling).
    const own = await this.fetchZone(zone, flavour, req.horizonHours, req.mode === "fast" ? "flow-traced" : "normal");
    const flowsByHour = new Map(own.flows.map((p) => [hourKey(p.datetime), p]));
    const neighbours = new Set<string>();
    for (const p of own.flows) for (const [nb, mw] of Object.entries(p.import ?? {})) if ((mw ?? 0) > 0) neighbours.add(nb);

    // neighbour production intensities (consumption + withdrawal), keyed by hour
    const nbInt: Record<string, Map<string, { c: number; w: number }>> = {};
    if (req.mode !== "fast") {
      await Promise.all([...neighbours].map(async (nb) => {
        try {
          const r = await this.emGet(`/v4/electricity-mix/${flavour}`, {
            zone: nb, breakdownType: "normal", ...(flavour === "forecast" ? { horizonHours: req.horizonHours ?? 72 } : {}),
          });
          const m = new Map<string, { c: number; w: number }>();
          for (const p of (r?.data ?? []) as Point[]) {
            if (!p.mix) continue;
            m.set(hourKey(p.datetime), {
              c: this.engine.production(nb, p.mix, this.opts(req, "consumption")).intensity,
              w: this.engine.production(nb, p.mix, this.opts(req, "withdrawal")).intensity,
            });
          }
          nbInt[nb] = m;
        } catch { /* neighbour unavailable -> engine falls back to local intensity and flags it */ }
      }));
    }

    const points = own.mix.filter((p) => p.mix).map((p) => {
      const h = hourKey(p.datetime);
      const imports = flowsByHour.get(h)?.import ?? {};
      const prodC = this.engine.production(zone, p.mix!, this.opts(req, "consumption"));
      const prodW = this.engine.production(zone, p.mix!, this.opts(req, "withdrawal"));
      const prodWT = this.engine.production(zone, p.mix!, this.opts(req, "withdrawal", "total"));
      const nbC: Record<string, number | undefined> = {}, nbW: Record<string, number | undefined> = {};
      for (const nb of Object.keys(imports)) { nbC[nb] = nbInt[nb]?.get(h)?.c; nbW[nb] = nbInt[nb]?.get(h)?.w; }
      const useImports = req.mode === "fast" ? {} : imports;
      const c = this.engine.consumptionOneHop(prodC, useImports, nbC);
      const w = this.engine.consumptionOneHop(prodW, useImports, nbW);
      return {
        datetime: p.datetime,
        isEstimated: !!p.isEstimated,
        w1_consumption_L_per_kWh: c.intensity / 1000,
        w1_production_L_per_kWh: prodC.intensity / 1000,
        w2_withdrawal_L_per_kWh: w.intensity / 1000,
        w2_withdrawal_total_L_per_kWh: prodWT.intensity / 1000, // production-based, incl. seawater
        w3_imported_water_share: c.importedShare,
        w3_imported_power_share: c.importedPowerShare,
        w3_by_origin: Object.fromEntries(Object.entries(c.byOrigin).map(([k, v]) => [k, {
          mw: v.mw, L_per_kWh: v.intensity / 1000, water_m3_per_h: v.waterLph / 1000, estimated: v.estimated,
        }])),
        by_source: Object.fromEntries(Object.entries(prodC.bySource).filter(([, v]) => v.mw > 0).map(([k, v]) => [k, {
          mw: v.mw, factor_L_per_kWh: v.factor / 1000, water_m3_per_h: v.waterLph / 1000,
        }])),
        profile_calibrated: prodC.profileCalibrated,
      };
    });

    return { zone, neighbours: [...neighbours], points };
  }

  async handle(req: SignalRequest) {
    const meta = {
      unit: "L/kWh",
      method: req.mode === "fast" ? "fast: domestic mix x local factors (no origin tracing)" : "one-hop origin-aware flow tracing",
      includeHydro: !!req.includeHydro,
      factors: "Macknick et al. 2012 (NREL) operational medians",
      profiles: "illustrative cooling profiles (calibration pending)",
      generatedAt: new Date().toISOString(),
    };

    if (req.action === "latest" || req.action === "history") {
      return { meta, ...(await this.computeSeries(req, req.action)) };
    }

    if (req.action === "forecast") {
      const s = await this.computeSeries({ ...req, horizonHours: req.horizonHours ?? 72 }, "forecast");
      const series = s.points.map((p) => p.w1_consumption_L_per_kWh);
      const [carbon, price] = await Promise.all([
        this.emGet("/v4/carbon-intensity/forecast", { zone: req.zone!, horizonHours: req.horizonHours ?? 72 }).catch(() => null),
        this.emGet("/v4/price-day-ahead/forecast", { zone: req.zone!, horizonHours: req.horizonHours ?? 72 }).catch(() => null),
      ]);
      // field names per v4 reference; fall back to generic `value` if the schema differs
      const byHour = (r: any, field: string) => new Map(((r?.data ?? []) as any[]).map((d) => [hourKey(d.datetime), d[field] ?? d.value ?? null]));
      const cMap = byHour(carbon, "carbonIntensity"), pMap = byHour(price, "value");
      const labels = tertileLabels(series);
      const win = bestWindow(series, req.jobHours ?? 4);
      return {
        meta, zone: s.zone, neighbours: s.neighbours,
        w4_best_window: win ? { start: s.points[win.start]?.datetime, hours: req.jobHours ?? 4, mean_L_per_kWh: win.mean } : null,
        points: s.points.map((p, i) => ({
          ...p, w4_level: labels[i],
          carbon_g_per_kWh: cMap.get(hourKey(p.datetime)) ?? null,
          price_eur_per_MWh: pMap.get(hourKey(p.datetime)) ?? null,
        })),
      };
    }

    if (req.action === "benchmark") {
      const days = Math.min(req.days ?? 30, 100);
      const end = new Date(); const start = new Date(end.getTime() - days * 86400000);
      const rows = await Promise.all((req.zones ?? []).map(async (zone) => {
        try {
          // A2 uses flow-traced daily mix x local factors (fast approximation, one call per zone)
          const range = { zone, temporalGranularity: "daily", start: start.toISOString(), end: end.toISOString() };
          const [r, ci] = await Promise.all([
            this.emGet("/v4/electricity-mix/past-range", { ...range, breakdownType: "flow-traced" }),
            this.emGet("/v4/carbon-intensity/past-range", range).catch(() => null),
          ]);
          const vals = ((r?.data ?? []) as Point[]).filter((p) => p.mix).map((p) =>
            this.engine.production(zone, p.mix!, this.opts(req, "consumption")).intensity / 1000);
          const avg = vals.reduce((a, b) => a + b, 0) / (vals.length || 1);
          const cVals = ((ci?.data ?? []) as any[]).map((d) => d.carbonIntensity ?? d.value).filter((v) => typeof v === "number");
          const carbonAvg = cVals.length ? cVals.reduce((a: number, b: number) => a + b, 0) / cVals.length : null;
          return { zone, days: vals.length, avg_L_per_kWh: avg, min: Math.min(...vals), max: Math.max(...vals), daily: vals, carbon_avg_g_per_kWh: carbonAvg };
        } catch (e) { return { zone, error: String(e) }; }
      }));
      return { meta: { ...meta, method: "fast: flow-traced daily mix x local factors" }, rows };
    }

    throw new Error(`unknown action ${(req as any).action}`);
  }
}
