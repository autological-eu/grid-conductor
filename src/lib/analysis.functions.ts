import { createServerFn } from "@tanstack/react-start";

/**
 * Zone rollup for the workbench map, computed from the static PyPSA-Eur
 * baseline (public/research/baseline/) instead of the retired `zone_summary`
 * RPC. `country_code` equals `code` because every zone is a country.
 */
export const listZoneSummary = createServerFn({ method: "GET" }).handler(async () => {
  const { baselineGrid, listBaselineCountries } = await import("./baseline-static.server");
  const [countries, hours] = await Promise.all([listBaselineCountries(), baselineGrid()]);

  return countries.map((country) => {
    const price = hours.price[country.code];
    const carbon = hours.carbon[country.code];
    return {
      code: country.code,
      name: country.name,
      country_code: country.code,
      lat: country.lat,
      lon: country.lon,
      avg_carbon_intensity: mean(carbon),
      avg_price: mean(price),
      hours: price?.length ?? 0,
    };
  });
});

/** Mean over the finite entries of a series, or null when nothing is present. */
function mean(values: Float64Array | undefined): number | null {
  if (!values || values.length === 0) return null;
  let sum = 0;
  let n = 0;
  for (let i = 0; i < values.length; i += 1) {
    const v = values[i]!;
    if (!Number.isFinite(v)) continue;
    sum += v;
    n += 1;
  }
  return n === 0 ? null : round(sum / n);
}

function round(value: number): number {
  return Math.round(value * 1000) / 1000;
}

export const listTargets = createServerFn({ method: "GET" }).handler(async () => {
  const { baselineDataset, mapToTargetRows } = await import("./baseline.server");
  const { listBaselineCountries } = await import("./baseline-static.server");

  // Zone names come from the extracted baseline itself: every zone is a
  // country, so `country_code === code` and no external lookup is needed.
  const countries = await listBaselineCountries();
  const zoneRows = countries.map((c) => ({
    code: c.code,
    name: c.name,
    country_code: c.code,
  }));

  return mapToTargetRows(baselineDataset(), zoneRows).sort(
    (a, b) => b.market_loss_meur - a.market_loss_meur,
  );
});

export const refreshTargets = createServerFn({ method: "POST" }).handler(async () => {
  return {
    targets: 0,
    note: "Targets are served from the offline PyPSA-Eur baseline solve (research/baseline-manifest.json); the legacy compute_targets RPC no longer drives the map.",
  };
});

/**
 * Fetch official ENTSO-E day-ahead NTC for the top baseline borders, to compare
 * the PyPSA modelled rating against the published limit. Read-only: the
 * workbench has no `targets` table to write back to, so the fetched values are
 * returned for display and the modelled rating stays the scenario input.
 */
export const refreshOfficialCapacity = createServerFn({ method: "POST" }).handler(async () => {
  const { fetchNtcMw } = await import("./entsoe.server");
  const { listTargets } = await import("./analysis.functions");

  const targets = (await listTargets()).slice(0, 15);
  const checked: Array<Record<string, string | number | null>> = [];
  for (const t of targets) {
    const end = new Date(t.period_end_exclusive);
    const start = new Date(end.getTime() - 7 * 86_400_000);
    const [ab, ba] = await Promise.all([
      fetchNtcMw(t.zone_a, t.zone_b, start, end),
      fetchNtcMw(t.zone_b, t.zone_a, start, end),
    ]);
    if (ab == null && ba == null) continue;
    checked.push({
      id: t.id,
      border: `${t.zone_a}-${t.zone_b}`,
      ntc_ab_mw: ab,
      ntc_ba_mw: ba,
      modelled_capacity_mw: t.observed_capacity_mw,
    });
  }
  return { updated: 0, checked: targets.length, published: checked.length, rows: checked };
});

export const getValidation = createServerFn({ method: "GET" }).handler(async () => {
  const { latestValidation } = await import("./workbench.server");
  return latestValidation();
});
