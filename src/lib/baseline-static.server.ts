// Server-only loader for the static PyPSA-Eur baseline published by
// tools/extract_baseline.py into public/research/baseline/.
//
// The build target is Nitro on Cloudflare Workers, which has no filesystem, so
// the artefacts are fetched over HTTP from the same origin as the request and
// parsed into typed arrays. Parsing is cached per isolate; the arrays are the
// only large allocation (~12 MB for a full year at 34 countries / 75 borders).
//
// Border limits come from cross_borders.json, never from observed flow.
import { getRequest } from "@tanstack/react-start/server";
import type { NetworkData, ZoneSeries } from "./simulation.server";

type Border = {
  id: string;
  country_a: string;
  country_b: string;
  capacity_mw: number;
  cap_ab_mw: number;
  cap_ba_mw: number;
};

type Columns = Record<string, Float64Array>;

export type Country = {
  code: string;
  name: string;
  lat: number;
  lon: number;
  n_buses: number;
};

export type Grid = {
  hours: string[];
  borders: Border[];
  price: Columns;
  carbon: Columns;
  load: Columns;
  flow: Columns;
};

const ARTIFACTS = {
  price: "hourly_price.csv",
  carbon: "hourly_carbon.csv",
  load: "hourly_load.csv",
  flow: "hourly_flow.csv",
  borders: "cross_borders.json",
  countries: "countries.json",
} as const;

const GENERATOR = "tools/build_pypsa_network.py && tools/extract_baseline.py";

/**
 * Tuning for the supply-curve slope estimator in priceSlope().
 *
 * BINDING_SPREAD_EUR_MWH selects the hours where a border is actually
 * constraining. It sits two orders of magnitude above the redispatch convergence
 * tolerance (0.01) and well below the March window's median cross-zone spread
 * (7.9 EUR/MWh), so it keeps the binding hours and discards the slack ones where
 * the difference is just noise around zero. 57 of the 75 modelled borders bind
 * for at least 24 hours at this threshold.
 *
 * MIN_BINDING_HOURS rejects borders with too little binding history: 24 hours is
 * a full day, below which a single spell would dominate the mean.
 */
const BINDING_SPREAD_EUR_MWH = 1;
const MIN_BINDING_HOURS = 24;

/** Used only when no border in the sub-network ever binds. */
const FALLBACK_SLOPE = 0.02;

let cache: Grid | null = null;
let inflight: Promise<Grid> | null = null;

function origin(): string {
  // getRequest() throws when there is no request in scope (scripts, tests,
  // background jobs), so the ambient-request path has to be guarded rather
  // than null-checked.
  let requestOrigin: string | null = null;
  try {
    const req = getRequest();
    if (req?.url) requestOrigin = new URL(req.url).origin;
  } catch {
    requestOrigin = null;
  }
  if (requestOrigin) return requestOrigin;

  const configured = process.env["PUBLIC_SITE_URL"];
  if (configured) return new URL(configured).origin;
  throw new Error(
    "Cannot resolve the origin for the static baseline. Set PUBLIC_SITE_URL to an absolute site URL.",
  );
}

async function artifact(name: string): Promise<string> {
  const res = await fetch(new URL(`/research/baseline/${name}`, origin()));
  if (!res.ok) {
    throw new Error(
      `Static baseline artefact ${name} is unavailable (HTTP ${res.status}). ` +
        `Regenerate it with ${GENERATOR}.`,
    );
  }
  return res.text();
}

/** Split one CSV record, tolerating CRLF and a trailing comma. */
function fields(line: string): string[] {
  const parts = line.replace(/\r$/, "").split(",");
  if (parts.length > 1 && parts[parts.length - 1] === "") parts.pop();
  return parts;
}

/**
 * Parse a wide hourly CSV into one Float64Array per data column. Empty or
 * non-numeric cells become NaN so downstream code can treat them as missing
 * rather than silently reading them as zero.
 */
function parseWide(text: string, label: string): { hours: string[]; columns: Columns } {
  const lines = text.split("\n");
  let cursor = 0;
  while (cursor < lines.length && lines[cursor]!.trim() === "") cursor += 1;
  if (cursor >= lines.length) throw new Error(`Static baseline ${label} is empty.`);

  const names = fields(lines[cursor]!).slice(1);
  cursor += 1;

  const pending: Record<string, number[]> = {};
  for (const name of names) pending[name] = [];
  const hours: string[] = [];

  for (; cursor < lines.length; cursor += 1) {
    const line = lines[cursor]!;
    if (line.trim() === "") continue;
    const parts = fields(line);
    hours.push(parts[0]!);
    for (let c = 0; c < names.length; c += 1) {
      const cell = parts[c + 1];
      pending[names[c]!]!.push(cell === undefined || cell === "" ? NaN : Number(cell));
    }
  }

  if (hours.length === 0) throw new Error(`Static baseline ${label} has no data rows.`);

  const columns: Columns = {};
  for (const name of names) {
    const values = pending[name]!;
    if (values.length !== hours.length) {
      throw new Error(
        `Static baseline ${label} column ${name} has ${values.length} values ` +
          `for ${hours.length} hours.`,
      );
    }
    columns[name] = Float64Array.from(values);
  }
  return { hours, columns };
}

async function load(): Promise<Grid> {
  const [priceText, carbonText, loadText, flowText, bordersText] = await Promise.all([
    artifact(ARTIFACTS.price),
    artifact(ARTIFACTS.carbon),
    artifact(ARTIFACTS.load),
    artifact(ARTIFACTS.flow),
    artifact(ARTIFACTS.borders),
  ]);

  const price = parseWide(priceText, ARTIFACTS.price);
  const carbon = parseWide(carbonText, ARTIFACTS.carbon);
  const loadGrid = parseWide(loadText, ARTIFACTS.load);
  const flow = parseWide(flowText, ARTIFACTS.flow);

  const H = price.hours.length;
  for (const [label, grid] of [
    [ARTIFACTS.carbon, carbon],
    [ARTIFACTS.load, loadGrid],
    [ARTIFACTS.flow, flow],
  ] as const) {
    if (grid.hours.length !== H) {
      throw new Error(
        `Static baseline ${label} has ${grid.hours.length} hours but ${ARTIFACTS.price} has ${H}; ` +
          `the artefacts are from different runs.`,
      );
    }
    for (let i = 0; i < H; i += 1) {
      if (grid.hours[i] !== price.hours[i]) {
        throw new Error(`Static baseline ${label} is not hour-aligned with price at row ${i}.`);
      }
    }
  }

  const borders = JSON.parse(bordersText) as Border[];
  if (!Array.isArray(borders) || borders.length === 0) {
    throw new Error("Static baseline cross_borders.json is empty.");
  }
  for (const border of borders) {
    if (!flow.columns[border.id]) {
      throw new Error(
        `Static baseline border ${border.id} has no flow column in ${ARTIFACTS.flow}.`,
      );
    }
    if (!Number.isFinite(border.cap_ab_mw) || !Number.isFinite(border.cap_ba_mw)) {
      throw new Error(
        `Static baseline border ${border.id} has no declared transfer limit; ` +
          `capacity must not be inferred from flow.`,
      );
    }
  }

  return {
    hours: price.hours,
    borders,
    price: price.columns,
    carbon: carbon.columns,
    load: loadGrid.columns,
    flow: flow.columns,
  };
}

/** The parsed baseline for this isolate, fetched at most once. */
export async function baselineGrid(): Promise<Grid> {
  if (cache) return cache;
  inflight ??= load()
    .then((g) => {
      cache = g;
      return g;
    })
    .finally(() => {
      inflight = null;
    });
  return inflight;
}

let countriesCache: Country[] | null = null;

/** Countries covered by the static baseline, with display names and centroids. */
export async function listBaselineCountries(): Promise<Country[]> {
  if (countriesCache) return countriesCache;
  const text = await artifact(ARTIFACTS.countries);
  const parsed = JSON.parse(text) as Country[];
  if (!Array.isArray(parsed) || parsed.length === 0) {
    throw new Error("Static baseline countries.json is empty.");
  }
  for (const country of parsed) {
    if (!Number.isFinite(country.lat) || !Number.isFinite(country.lon)) {
      throw new Error(`Static baseline country ${country.code} has no centroid.`);
    }
  }
  countriesCache = parsed;
  return parsed;
}

/**
 * Build the sub-network for one border: the two zones plus their direct
 * neighbours, matching the topology discovery the Supabase `borders` table used
 * to provide.
 */
export async function loadStaticNetwork(zoneA: string, zoneB: string): Promise<NetworkData> {
  const g = await baselineGrid();
  const priceA = g.price[zoneA];
  const priceB = g.price[zoneB];
  if (!priceA || !priceB) {
    throw new Error(
      `Unknown country code in ${zoneA}-${zoneB}; the static baseline covers ` +
        `${Object.keys(g.price).sort().join(", ")}.`,
    );
  }

  const zoneSet = new Set<string>([zoneA, zoneB]);
  for (const border of g.borders) {
    if (border.country_a === zoneA || border.country_a === zoneB) zoneSet.add(border.country_b);
    if (border.country_b === zoneA || border.country_b === zoneB) zoneSet.add(border.country_a);
  }
  const zones = [...zoneSet].sort();

  const H = g.hours.length;
  const series: Record<string, ZoneSeries> = {};
  for (const z of zones) {
    const price = g.price[z];
    const carbon = g.carbon[z];
    const load = g.load[z];
    if (!price || !carbon || !load)
      throw new Error(`Static baseline is missing a series for ${z}.`);
    const has = new Uint8Array(H);
    for (let i = 0; i < H; i += 1) has[i] = Number.isFinite(price[i]!) ? 1 : 0;
    series[z] = { price, ci: carbon, load, has };
  }

  const edges: NetworkData["edges"] = [];
  for (const border of g.borders) {
    if (!zoneSet.has(border.country_a) || !zoneSet.has(border.country_b)) continue;
    const flow = g.flow[border.id];
    if (!flow) continue;
    edges.push({
      a: border.country_a,
      b: border.country_b,
      capAb: border.cap_ab_mw,
      capBa: border.cap_ba_mw,
      flow,
    });
  }

  return { hours: g.hours, zones, series, edges, slope: priceSlope(H, zones, series, edges) };
}

/**
 * Price-response slope per zone: the local slope of the residual supply curve,
 * in EUR/MWh per MW, derived from the nodal price differences in the solve.
 *
 * The obvious alternative - regressing each zone's own price on its own net
 * export - is not identifiable from a single solved equilibrium per hour. With
 * one bus per country the marginal price is set by the same system-wide unit, so
 * price is nearly common-mode while net export is driven mostly by demand. On the
 * March window that fit returns values from -0.0038 to +0.0059 with a median of
 * 0.00002, pushing 10 of 15 zones onto its clamp floor: noise, not a slope.
 * Regressing the flow on the spread over binding hours is worse, because both
 * co-move with demand: the median fitted slope is negative (-0.010), and it
 * explodes where the flow barely varies (IT-ME fitted -10555).
 *
 * What is directly observable is the price separation a border actually sustains
 * while it is binding, and the capacity over which that separation applies. So
 * each border's contribution is its mean absolute nodal price difference across
 * binding hours divided by its binding capacity, and that sensitivity is split
 * between the two zones in proportion to load, keeping `slope[a] + slope[b]`
 * equal to the pair's contribution. The redispatch needs exactly that sum: it
 * takes the transfer that closes a spread of `gain` to be `gain` divided by
 * `slope[from] + slope[to]`.
 *
 * This is a proxy for the supply-curve slope, not an identification of it. It is
 * positive and finite by construction, it scales with how genuinely constrained
 * the border is, and it reproduces the 1e-4..1e-1 range the solver's own price
 * response implies. It is a research assumption and is documented as such.
 *
 * It also avoids a circularity the regression version carried: the observed
 * price differences come from the same PyPSA solve whose redispatch this slope
 * then reproduces, so measuring the slope from those differences keeps the
 * calibration and the simulation consistent with one another.
 *
 * Borders that never bind have no measurable separation and contribute nothing;
 * a zone with no binding border inherits the median pair contribution so every
 * zone stays finite and positive.
 */
function priceSlope(
  H: number,
  zones: string[],
  series: Record<string, ZoneSeries>,
  edges: NetworkData["edges"],
): Record<string, number> {
  const meanLoad = (z: string): number => {
    const load = series[z]?.load;
    if (!load || load.length === 0) return 0;
    let sum = 0;
    let n = 0;
    for (let i = 0; i < load.length; i += 1) {
      const v = load[i]!;
      if (!Number.isFinite(v)) continue;
      sum += v;
      n += 1;
    }
    return n === 0 ? 0 : sum / n;
  };

  const slope: Record<string, number> = {};
  for (const z of zones) slope[z] = 0;
  const betas: number[] = [];
  /** Per zone: the pair sensitivities of its binding borders, and its load share of each. */
  const seen: Record<string, number[]> = {};
  const share: Record<string, number[]> = {};
  for (const z of zones) {
    seen[z] = [];
    share[z] = [];
  }

  for (const e of edges) {
    const pa = series[e.a]?.price;
    const pb = series[e.b]?.price;
    if (!pa || !pb) continue;

    let n = 0;
    let separation = 0;
    for (let i = 0; i < H; i += 1) {
      const a = pa[i]!;
      const b = pb[i]!;
      if (!Number.isFinite(a) || !Number.isFinite(b)) continue;
      const spread = Math.abs(a - b);
      if (spread < BINDING_SPREAD_EUR_MWH) continue;
      separation += spread;
      n += 1;
    }
    if (n < MIN_BINDING_HOURS) continue;

    const capacity = Math.min(e.capAb, e.capBa);
    if (!(capacity > 0)) continue;
    const beta = separation / n / capacity;
    if (!Number.isFinite(beta) || beta <= 0) continue;

    betas.push(beta);
    const la = meanLoad(e.a);
    const lb = meanLoad(e.b);
    const total = la + lb;
    const wa = total > 0 ? la / total : 0.5;
    seen[e.a]!.push(beta);
    share[e.a]!.push(wa);
    seen[e.b]!.push(beta);
    share[e.b]!.push(1 - wa);
  }

  if (betas.length === 0) {
    // Nothing in this sub-network ever binds; fall back to the historical default
    // for every zone rather than inventing a sensitivity.
    for (const z of zones) slope[z] = FALLBACK_SLOPE;
    return slope;
  }

  const pairMedian = median(betas);
  for (const z of zones) {
    if (seen[z]!.length === 0) {
      // Unbound in the baseline: assume it behaves like the median binding border.
      slope[z] = pairMedian / 2;
      continue;
    }
    // Average rather than sum. Each binding border is an independent estimate of
    // the same pair response; it does not compound, so a hub like IT must not
    // collect five times the sensitivity just for touching five borders. The
    // median also keeps one very tight border (GR-IT) from dominating a zone.
    const beta = median(seen[z]!);
    const weight = median(share[z]!);
    slope[z] = beta * weight;
  }
  return slope;
}

function median(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((x, y) => x - y);
  const mid = sorted.length >> 1;
  return sorted.length % 2 === 1 ? sorted[mid]! : (sorted[mid - 1]! + sorted[mid]!) / 2;
}
