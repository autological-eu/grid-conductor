import fs from "node:fs";
import path from "node:path";
import { entsoeZoneMeta } from "./entsoeZones";

/**
 * Step-1 -> EuropeMap adapter (server-side).
 *
 * Turns `public/research/entsoe-fast-targets.json` (the Step-1 ENTSO-E
 * screening: directed borders x screened months, per-direction "lost congestion
 * rent" under a capacity ladder) into the exact `ZoneSummary[]`/`TargetRow[]`
 * contract the EuropeMap workbench renders.
 *
 * The Step-1 JSON **does not** ship coordinates, zone names or carbon data, so
 * we supply them from `ENTSOE_ZONES` (static, client-safe). It **does not**
 * ship a climate number either — the `climate_loss_ktco2` column is a
 * locally-estimated approximation "(est.)" derived from the released energy
 * implied by each border's monthly opportunity rent:
 *
 *   released_MWh (per screened month) = opportunity_meur_month * 1e6 / average_positive_spread_eur_mwh
 *   climate_ktco2 (est.) per year     = 12 * released_MWh * |carbon_b - carbon_a| (g/kWh) / 1e6
 *
 * Only directed exposure areas with a positive opportunity in any screened
 * month are kept (the map draws congested borders as heat lines; a
 * zero-opportunity direction is invisible). The Step-1 figures are MONTHLY
 * (quarter-hour sums already carry the 0.25 h factor); this adapter averages
 * them across the screened months, annualises x12 to the "MEUR/y" / "ktCO2/y"
 * UI contract, and converts congested sample counts to real hours for display.
 */
export type Step1Summary = {
  zones: Array<{
    code: string;
    name: string;
    country_code: string;
    lat: number;
    lon: number;
    avg_carbon_intensity: number | null;
    avg_price: number | null;
    hours: number;
  }>;
  targets: Array<{
    id: string;
    zone_a: string;
    zone_b: string;
    zone_a_name: string;
    zone_b_name: string;
    a_lat: number;
    a_lon: number;
    b_lat: number;
    b_lon: number;
    congested_hours: number;
    total_hours: number;
    market_loss_meur: number;
    climate_loss_ktco2: number;
  }>;
};

type Step1BorderMonth = {
  month: string;
  border: string;
  opportunity_meur_month?: Record<string, number | null> | null;
  congested_quarters?: number | null;
  observed_quarters?: number | null;
  average_positive_spread_eur_mwh?: number | null;
};

/** Step-2 annualisation: the screened month is treated as representative. */
const MONTHS_PER_YEAR = 12;

type Step1File = {
  targets?: Step1BorderMonth[];
};

export function loadStep1Summary(filePath: string): Step1Summary {
  const raw = JSON.parse(fs.readFileSync(filePath, "utf-8")) as Step1File;
  const rows = raw.targets ?? [];

  const byBorder = new Map<string, Step1BorderMonth[]>();
  for (const r of rows) {
    const list = byBorder.get(r.border) ?? [];
    list.push(r);
    byBorder.set(r.border, list);
  }

  const zones = new Map<
    string,
    {
      code: string;
      name: string;
      country_code: string;
      lat: number;
      lon: number;
      avg_carbon_intensity: number | null;
      avg_price: null;
      hours: number;
    }
  >();
  const addZone = (code: string, hours: number) => {
    if (!zones.has(code)) {
      const m = entsoeZoneMeta(code);
      zones.set(code, {
        code,
        name: m.name,
        country_code: m.country_code,
        lat: m.lat,
        lon: m.lon,
        avg_carbon_intensity: m.carbon_g_per_kwh,
        avg_price: null,
        hours: 0,
      });
    }
    zones.get(code)!.hours = Math.max(zones.get(code)!.hours, hours);
  };

  const targets = [] as Step1Summary["targets"];
  for (const [border, months] of byBorder) {
    const [a, b] = (border ?? "").split(">");
    if (!a || !b) continue;
    // Opportunity is never negative; a border direction congested in one month
    // but not another contributes its actual (possibly zero) monthly value, so
    // the mean shares the same denominator as the congestion/spread metrics.
    // Directions with no positive opportunity in ANY screened month are dropped
    // (the map draws only congested directions).
    const opps = months
      .map((m) => m.opportunity_meur_month?.["1000"])
      .filter((v): v is number => typeof v === "number");
    if (!opps.some((v) => v > 0)) continue;

    const metaA = entsoeZoneMeta(a);
    const metaB = entsoeZoneMeta(b);

    // Mean M€/month across the screened months, annualised x12 (screened month
    // is representative) to match the "MEUR/y" / "ktCO2/y" UI contract.
    const marketLossMeurYr = mean(opps) * MONTHS_PER_YEAR;
    const avgSpread = mean(
      months
        .map((m) => m.average_positive_spread_eur_mwh)
        .filter((v): v is number => typeof v === "number"),
    );
    // Sample counts -> real hours (quarter-hour screening samples).
    const congestedHours =
      mean(
        months.map((m) => m.congested_quarters).filter((v): v is number => typeof v === "number"),
      ) / 4;
    const totalHours =
      sum(
        months.map((m) => m.observed_quarters).filter((v): v is number => typeof v === "number"),
      ) /
      months.length /
      4;

    const carbonDelta = Math.abs(metaB.carbon_g_per_kwh - metaA.carbon_g_per_kwh);
    const climate = avgSpread > 0 ? (marketLossMeurYr * carbonDelta) / avgSpread : 0;

    targets.push({
      id: border,
      zone_a: a,
      zone_b: b,
      zone_a_name: metaA.name,
      zone_b_name: metaB.name,
      a_lat: metaA.lat,
      a_lon: metaA.lon,
      b_lat: metaB.lat,
      b_lon: metaB.lon,
      congested_hours: round(congestedHours),
      total_hours: round(totalHours),
      market_loss_meur: round2(marketLossMeurYr),
      climate_loss_ktco2: round2(climate),
    });

    for (const code of [a, b]) {
      addZone(code, Math.round(totalHours));
    }
  }

  return { zones: [...zones.values()], targets };
}

function mean(xs: number[]): number {
  return xs.length ? xs.reduce((s, v) => s + v, 0) / xs.length : 0;
}
function sum(xs: number[]): number {
  return xs.reduce((s, v) => s + v, 0);
}
function round(x: number): number {
  return Math.round(x);
}
function round2(x: number): number {
  return Math.round(x * 100) / 100;
}
