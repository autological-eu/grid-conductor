import fs from "node:fs";
import path from "node:path";
import type { EntsoeZoneMeta } from "./entsoeZones";
import { entsoeZoneMeta } from "./entsoeZones";

/**
 * Step-1 -> EuropeMap adapter (server-side).
 *
 * Turns `public/research/entsoe-fast-targets.json` (the Step-1 ENTSO-E
 * screening: 51 borders x 2 months, per-border "lost congestion rent" under a
 * capacity ladder) into the exact `ZoneSummary[]`/`TargetRow[]` contract the
 * EuropeMap workbench renders.
 *
 * The Step-1 JSON **does not** ship coordinates, zone names or carbon data, so
 * we supply them from `ENTS OE_ZONES` (ENTS OE zone meta, static, client-safe).
 * It **does not** ship a climate number either — the `climate_loss_ktco2`
 * column is a locally-estimated approximation "(est.)" derived from the
 * released energy implied by each border's opportunity rent:
 *
 *   released_MWh_yr    = opportunity_meur_yr * 1e6 / average_positive_spread_eur_mwh
 *   climate_ktco2(est) = released_MWh_yr * |carbon_b - carbon_a| (g/kWh) / 1e6
 *
 * Only exposure areas with a positive opportunity are kept (the map draws
 * congested borders as heat lines; a zero-opportunity border is invisible).
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
  opportunity_meur_yr?: Record<string, number | null> | null;
  congested_hours?: number | null;
  observed_quarters?: number | null;
  average_positive_spread_eur_mwh?: number | null;
};

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

  const zoneHour = new Map<string, number>();
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
      const m = entsoeZoneMeta(code) as EntsoeZoneMeta;
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
    const opps = months
      .map((m) => m.opportunity_meur_yr?.["1000"])
      .filter((v): v is number => typeof v === "number" && v > 0);
    if (opps.length === 0) continue;

    const metaA = entsoeZoneMeta(a);
    const metaB = entsoeZoneMeta(b);

    // Yearly view: mean across screened months (2026-01, 2026-08).
    const marketLossMeur = mean(opps);
    const avgSpread = mean(
      months
        .map((m) => m.average_positive_spread_eur_mwh)
        .filter((v): v is number => typeof v === "number"),
    );
    const congestedHours = mean(
      months.map((m) => m.congested_hours).filter((v): v is number => typeof v === "number"),
    );
    const totalHours = round(
      sum(
        months.map((m) => m.observed_quarters).filter((v): v is number => typeof v === "number"),
      ) / months.length,
    );

    const carbonDelta = Math.abs(metaB.carbon_g_per_kwh - metaA.carbon_g_per_kwh);
    const climate = avgSpread > 0 ? (marketLossMeur * carbonDelta) / avgSpread : 0;

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
      market_loss_meur: round2(marketLossMeur),
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
