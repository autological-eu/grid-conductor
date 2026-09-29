// .server.ts: bundled mirror of public/research/pypsa-targets.json (schema v2).
// tools/baseline_opportunity.py writes both copies; the mirror keeps the dataset
// available to server code without filesystem access (Cloudflare Workers).
import baselineJson from "@/data/baseline-targets.json";
import type { SupabaseClient } from "@supabase/supabase-js";
import type { Database } from "@/integrations/supabase/types";

export type BaselineAsset = {
  component: "Line" | "Link";
  id: string;
  nominal_mw: number;
};

export type BaselineTarget = {
  id: string;
  a: string;
  b: string;
  assets: BaselineAsset[];
  status: string;
  baseline_rent_meur: number | null;
  mean_abs_spread_eur_mwh: number;
  max_abs_spread_eur_mwh: number;
  spread_hours: number;
  congested_hours: number;
  marginal_value_eur_mw: number;
  opportunity_meur: number | null;
  modelled_opportunity_meur: number | null;
  modelled_climate_opportunity_tonnes: number | null;
};

export type BaselineNode = { id: string; x: number; y: number };

export type BaselineDataset = {
  schema_version: number;
  status: string;
  start: string;
  end_exclusive: string;
  metric: string;
  baseline_metric: string;
  unit: string;
  window_years: number;
  additional_mw: number | null;
  annual_opportunity_meur: number | null;
  network_sha256: string;
  upstream_commit: string;
  baseline_cost_eur: number;
  baseline_rent_meur_total: number;
  baseline_co2_tonnes: number;
  lmp_recheck_max_eur_mwh: number | null;
  kkt_max_residual: number;
  validation: {
    status: string;
    price_basis: string | null;
    entsoe_quantities: string;
    jao: string;
  };
  nodes: BaselineNode[];
  targets: BaselineTarget[];
};

const dataset = baselineJson as unknown as BaselineDataset;

export function baselineDataset(): BaselineDataset {
  return dataset;
}

export function windowHours(startIso: string, endIso: string): number {
  const start = Date.parse(startIso);
  const end = Date.parse(endIso);
  if (!Number.isFinite(start) || !Number.isFinite(end)) return 0;
  return Math.round((end - start) / 3_600_000);
}

export type CountryZone = {
  code: string;
  name: string;
  country_code: string;
};

/** Workbench (EuropeMap) row mapped from the baseline dataset. The rent is the
 * per-window congestion rent; there is no validation climate figure yet. */
export type BaselineTargetRow = {
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
  /** Window the rent and spread figures cover, so the UI can label the unit rather
   *  than leaving the reader to guess what "per window" spans. */
  period_start: string;
  period_end_exclusive: string;
  window_years: number;
  climate_loss_ktco2: number | null;
  observed_capacity_mw: number;
  /** Additive diagnostics for the sidebar; not part of the legacy row shape. */
  baseline_rent_meur: number | null;
  mean_abs_spread_eur_mwh: number;
  marginal_value_eur_mw: number;
};

export function mapToTargetRows(
  report: BaselineDataset,
  zones: CountryZone[] = [],
): BaselineTargetRow[] {
  const byCountry = new Map(zones.map((z) => [z.country_code, z.name]));
  const nodes = new Map(report.nodes.map((n) => [n.id, n]));
  const hours = windowHours(report.start, report.end_exclusive);
  return report.targets.map((t) => {
    const aNode = nodes.get(t.a);
    const bNode = nodes.get(t.b);
    const capacity = t.assets.reduce((sum, a) => sum + a.nominal_mw, 0);
    return {
      id: t.id,
      zone_a: t.a,
      zone_b: t.b,
      zone_a_name: byCountry.get(t.a) ?? t.a,
      zone_b_name: byCountry.get(t.b) ?? t.b,
      a_lat: aNode?.y ?? 0,
      a_lon: aNode?.x ?? 0,
      b_lat: bNode?.y ?? 0,
      b_lon: bNode?.x ?? 0,
      congested_hours: t.congested_hours,
      total_hours: hours,
      market_loss_meur: t.baseline_rent_meur ?? 0,
      period_start: report.start,
      period_end_exclusive: report.end_exclusive,
      window_years: report.window_years,
      climate_loss_ktco2: null,
      observed_capacity_mw: capacity,
      baseline_rent_meur: t.baseline_rent_meur,
      mean_abs_spread_eur_mwh: t.mean_abs_spread_eur_mwh,
      marginal_value_eur_mw: t.marginal_value_eur_mw,
    };
  });
}

/** Insert minimal identity rows into the legacy `targets` table for baseline
 * borders the DB does not know, so the scenarios.target_id FK resolves. This is
 * FK integrity only: the workbench reads the numbers from the bundled dataset,
 * not from these rows. */
export async function ensureTargetIds(
  db: Pick<SupabaseClient<Database>, "from">,
  report: BaselineDataset,
): Promise<{ present: number; inserted: number }> {
  const rows = mapToTargetRows(report);
  const { data: existing } = await db.from("targets").select("id");
  const have = new Set((existing ?? []).map((r) => r.id));
  const missing = rows.filter((r) => !have.has(r.id));
  if (missing.length === 0) return { present: have.size, inserted: 0 };

  const { start, end_exclusive, window_years, status } = report;
  for (let i = 0; i < missing.length; i += 100) {
    const chunk: Database["public"]["Tables"]["targets"]["Insert"][] = missing
      .slice(i, i + 100)
      .map((r) => ({
        id: r.id,
        zone_a: r.zone_a,
        zone_b: r.zone_b,
        period_start: start,
        period_end: end_exclusive,
        market_loss_meur: 0,
        climate_loss_ktco2: 0,
        congested_hours: r.congested_hours,
        total_hours: r.total_hours,
        observed_capacity_mw: r.observed_capacity_mw,
        metrics: {
          baseline_rent_meur: r.baseline_rent_meur,
          mean_abs_spread_eur_mwh: r.mean_abs_spread_eur_mwh,
          marginal_value_eur_mw: r.marginal_value_eur_mw,
          status,
          window_years,
        },
      }));
    await db.from("targets").upsert(chunk, { onConflict: "id", ignoreDuplicates: true });
  }
  return { present: have.size, inserted: missing.length };
}
