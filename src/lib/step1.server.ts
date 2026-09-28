import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { entsoeZoneMeta } from "./entsoeZones";

/**
 * Step-1 -> EuropeMap adapter (server-side).
 *
 * Turns `public/research/entsoe-fast-targets.json` (the Step-1 ENTSO-E
 * screening: directed borders x the full calendar year, per-direction "lost
 * congestion rent" under a capacity ladder) into the exact
 * `ZoneSummary[]`/`TargetRow[]` contract the EuropeMap workbench renders.
 *
 * The Step-1 JSON **does not** ship coordinates, zone names or carbon data, so
 * we supply them from `ENTSOE_ZONES` (static, client-safe). It **does not**
 * ship a climate number either — the `climate_loss_ktco2` column is a
 * locally-estimated approximation "(est.)" derived from the released energy
 * implied by each border's annual opportunity rent:
 *
 *   released_energy (MWh/yr) = opportunity_meur_year * 1e6 / average_positive_spread_eur_mwh
 *   climate_ktco2 (est.)/yr  = released_energy * |carbon_b - carbon_a| (g/kWh) / 1e6
 *
 * Only directed exposure areas with positive annual opportunity are kept (the
 * map draws congested borders as heat lines; a zero-opportunity direction is
 * invisible). The Step-1 rows are ANNUAL (schema_version 3: full calendar
 * year, no x12 representative-month factor); this adapter maps the annual row
 * straight onto the "MEUR/y" / "ktCO2/y" UI contract and converts congested
 * sample counts to real hours for display.
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
    observed_capacity_mw: number | null;
  }>;
};

type Step1BorderAnnual = {
  month: string;
  border: string;
  opportunity_meur_year?: Record<string, number | null> | null;
  congested_quarters?: number | null;
  observed_quarters?: number | null;
  average_positive_spread_eur_mwh?: number | null;
};

type Step1File = {
  targets?: Step1BorderAnnual[];
};

export function loadStep1Summary(filePath: string): Step1Summary {
  const raw = JSON.parse(fs.readFileSync(filePath, "utf-8")) as Step1File;
  const rows = raw.targets ?? [];

  const byBorder = new Map<string, Step1BorderAnnual[]>();
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
    // Opportunity is never negative; a direction with no positive opportunity in
    // the year is dropped (the map draws only congested directions). The annual
    // row is the full-year sum, so the "MEUR/y" / "ktCO2/y" UI contract is exact.
    const opps = months
      .map((m) => m.opportunity_meur_year?.["1000"])
      .filter((v): v is number => typeof v === "number");
    if (!opps.some((v) => v > 0)) continue;

    const metaA = entsoeZoneMeta(a);
    const metaB = entsoeZoneMeta(b);

    const marketLossMeurYr = mean(opps);
    const avgSpread = mean(
      months
        .map((m) => m.average_positive_spread_eur_mwh)
        .filter((v): v is number => typeof v === "number"),
    );
    // Sample counts -> real hours (quarter-hour screening samples span the year).
    const congestedHours =
      mean(
        months.map((m) => m.congested_quarters).filter((v): v is number => typeof v === "number"),
      ) / 4;
    const totalHours =
      mean(
        months.map((m) => m.observed_quarters).filter((v): v is number => typeof v === "number"),
      ) / 4;

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
      observed_capacity_mw: null,
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
function round(x: number): number {
  return Math.round(x);
}
function round2(x: number): number {
  return Math.round(x * 100) / 100;
}

/** The Step-1 screening artifact the workbench renders. */
const SUMMARY_PATH = path.join(process.cwd(), "public", "research", "entsoe-fast-targets.json");

/** Read the Step-1 summary from its well-known path (server-side). */
export function loadStep1SummaryCwd(): Step1Summary {
  return loadStep1Summary(SUMMARY_PATH);
}

/**
 * Deterministic target row id for a fast-entsoe directed border. The
 * `scenarios.target_id` column is a FK to `targets.id` (a Postgres uuid), but
 * fast-entsoe targets are identified by their border string ("FR>IT-North"),
 * so we map each border to a stable uuid4-style hash that survives edits,
 * re-runs and deploys. Existing Electricity-Maps target rows are untouched.
 */
export function borderUuid(border: string): string {
  const bytes = [
    ...createHash("sha256").update(`grid-conductor:${border}`).digest().subarray(0, 16),
  ];
  bytes[6] = (bytes[6]! & 0x0f) | 0x40;
  bytes[8] = (bytes[8]! & 0x3f) | 0x80;
  const hex = bytes.map((b) => b.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
