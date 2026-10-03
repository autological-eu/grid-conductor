import { loadScreeningData } from "./research";
import { entsoeZoneMeta } from "./entsoeZones";

/**
 * Step-1 -> EuropeMap adapter (browser-side).
 *
 * Turns `public/research/entsoe-fast-targets.json` (the Step-1 ENTSO-E
 * screening: directed borders x the full calendar year) into the exact
 * `ZoneSummary[]`/`TargetRow[]` contract the EuropeMap workbench renders.
 *
 * The map headline is accumulated absolute observed price spread in €/MW-year,
 * recovered from the two directed 500 MW fixed-price ladders by dividing out
 * 500 MW. These retain the source's known-price AND known-flow coverage mask.
 * The experimental welfare bound remains separate for scenario evaluation.
 *
 * The Step-1 JSON **does not** ship coordinates, zone names or carbon data, so
 * we supply them from `ENTSOE_ZONES` (static, client-safe). It **does not**
 * ship a climate number either — the `climate_loss_ktco2` column is a
 * locally-estimated approximation "(est.)" derived from the released energy
 * implied by each border's annual market opportunity:
 *
 *   released_energy (MWh/yr) = market_opportunity_meur * 1e6 / average_positive_spread_eur_mwh
 *   climate_ktco2 (est.)/yr  = released_energy * |carbon_b - carbon_a| (g/kWh) / 1e6
 *
 * Only directed exposure areas with positive annual market opportunity are kept
 * (the map draws congested borders as heat lines; a direction with no claimable
 * opportunity is invisible). The step-1 screening now sizes every border that
 * moves energy with a positive price-response slope (interconnector capacity is
 * direction-independent, so a one-way border's reverse direction inherits the
 * pair's observed capacity) and the adapter drops directions whose bounded
 * deadweight loss is absent — those the Step-2 LP cannot claim at all. The
 * Step-1 rows are ANNUAL (schema_version 3: full calendar
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
    /** Bounded deadweight-loss estimate (the cap the Step-2 LP enforces). */
    market_opportunity_meur: number;
    price_spread_eur_mw_year?: number;
    mean_absolute_spread_eur_mwh?: number | null;
    congestion_rent_meur_year?: number | null;
    climate_loss_ktco2: number;
    observed_capacity_mw: number | null;
  }>;
};

type Step1BorderAnnual = {
  month: string;
  border: string;
  realized_rent_meur_year?: number | null;
  opportunity_meur_year?: Record<string, number | null> | null;
  deadweight_loss_meur_year?: number | null;
  congested_quarters?: number | null;
  observed_quarters?: number | null;
  average_positive_spread_eur_mwh?: number | null;
};

type Step1File = {
  targets?: Step1BorderAnnual[];
};

export function summarizeStep1(raw: Step1File): Step1Summary {
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
    // Market opportunity is never negative; we keep only directions the model
    // can actually claim — those with a positive bounded DWL (the cap the
    // Step-2 LP enforces). A direction whose opportunity lives entirely under
    // the 5 EUR/MWh congestion threshold has no DWL and would render on the map
    // but return 0 from every scenario, so it is dropped instead. The annual
    // row is the full-year sum, so the "MEUR/y" / "ktCO2/y" UI contract is
    // exact.
    const dwls = months
      .map((m) => m.deadweight_loss_meur_year)
      .filter((v): v is number => typeof v === "number" && v > 0);
    if (!dwls.some((v) => v > 0)) continue;
    const marketOpportunityMeurYr = mean(dwls);

    const reverse = byBorder.get(`${b}>${a}`) ?? [];
    const pairRows = [...months, ...reverse];
    const spreadArea = pairRows.reduce(
      (sum, row) => sum + ((row.opportunity_meur_year?.["500"] ?? 0) * 1e6) / 500,
      0,
    );
    const coveredHours = (months[0]?.observed_quarters ?? 0) / 4;
    const compatible =
      months.length === 1 &&
      reverse.length === 1 &&
      coveredHours > 0 &&
      reverse[0]?.observed_quarters === months[0]?.observed_quarters &&
      pairRows.every((row) => typeof row.opportunity_meur_year?.["500"] === "number");
    const meanSpread = compatible ? spreadArea / coveredHours : null;
    const rent =
      pairRows.length === 2 &&
      pairRows.every((row) => typeof row.realized_rent_meur_year === "number")
        ? pairRows.reduce((sum, row) => sum + (row.realized_rent_meur_year ?? 0), 0)
        : null;

    const metaA = entsoeZoneMeta(a);
    const metaB = entsoeZoneMeta(b);

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
    const climate = avgSpread > 0 ? (marketOpportunityMeurYr * carbonDelta) / avgSpread : 0;

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
      market_opportunity_meur: round2(marketOpportunityMeurYr),
      mean_absolute_spread_eur_mwh: meanSpread,
      congestion_rent_meur_year: rent,
      price_spread_eur_mw_year: [...months, ...(byBorder.get(`${b}>${a}`) ?? [])].reduce(
        (sum, row) => sum + ((row.opportunity_meur_year?.["500"] ?? 0) * 1e6) / 500,
        0,
      ),
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

/** Load the published screening artifact; no server or API credential required. */
export async function loadStep1Summary(): Promise<Step1Summary> {
  return summarizeStep1(await loadScreeningData());
}
