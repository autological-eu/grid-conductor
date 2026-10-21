import { publicAsset } from "@/lib/research";

export type Resolution = "hourly" | "daily";
export type Samples = (number | null)[];
export type CountryEntry = {
  code: string;
  name: string;
  file: string;
  sha256: string;
  json_sha256: string;
  bytes: number;
  price_zones: string[];
  observed_price_zones: number;
  generation_source_areas: string[];
};
export type ExplorerManifest = {
  schema_version: number;
  year: number;
  hours: number;
  start_utc: string;
  generation_scale: number;
  price_scale: number;
  model: {
    id: string;
    label: string;
    mae_eur_mwh: number;
    accepted_baseline: boolean;
    witness_sha256: string;
  };
  technologies: { id: string; label: string; psr: string }[];
  ember_fuels: string[];
  countries: CountryEntry[];
  sources: Record<
    "irena" | "ember" | "entsoe",
    { url: string; description: string; sha256?: string }
  >;
  limitations: string[];
};
export type GenerationArea = {
  id: string;
  label: string;
  source_areas: string[];
  scope_note: string;
  missing_source_areas: string[];
  model: string[];
  lower: string[];
  upper: string[];
  observed: string[];
  observed_hours: number[];
};
export type PriceArea = {
  zone: string;
  scope: string;
  model: string;
  observed: string;
  known_hours: number;
  mae: number | null;
  bias: number | null;
  correlation: number | null;
};
export type CountryData = {
  schema_version: number;
  country: string;
  name: string;
  model_id: string;
  hours: number;
  series: Record<string, Samples>;
  generation: GenerationArea[];
  prices: PriceArea[];
  source_generation: {
    area: string;
    scope: string;
    provenance: { month: number; processed_sha256: string }[];
    psr: Record<string, string>;
  }[];
  monthly: { month: number; fuel: string; observed_twh: number | null; model_twh: number }[];
  ember_rows: Record<string, string>[];
  irena_rows: {
    country: string;
    provider_area: string;
    technology: string;
    capacity_2024: { mw: number; source_flag: string | null };
    capacity_2025: { mw: number; source_flag: string | null };
  }[];
};
export type PlotPoint = {
  time: number;
  model: number | null;
  observed: number | null;
  interval: [number, number] | null;
};
export const YEAR_START = Date.UTC(2025, 0, 1);
export const HOUR = 3_600_000;

export async function loadManifest(signal: AbortSignal): Promise<ExplorerManifest> {
  const response = await fetch(publicAsset("research/country-explorer-2025/manifest.json"), {
    signal,
  });
  if (!response.ok) throw new Error("Country data index could not be loaded.");
  const data = (await response.json()) as ExplorerManifest;
  if (
    data.schema_version !== 1 ||
    data.year !== 2025 ||
    data.hours !== 8760 ||
    !data.countries.length
  )
    throw new Error("Unsupported country data index.");
  return data;
}

export async function loadCountry(
  entry: CountryEntry,
  model: string,
  signal: AbortSignal,
): Promise<CountryData> {
  const response = await fetch(publicAsset(`research/country-explorer-2025/${entry.file}`), {
    signal,
  });
  if (!response.ok) throw new Error(`Data for ${entry.name} could not be loaded.`);
  const data = (await decodeCountryBytes(await response.arrayBuffer(), entry)) as CountryData;
  if (
    data.schema_version !== 1 ||
    data.country !== entry.code ||
    data.hours !== 8760 ||
    data.model_id !== model
  )
    throw new Error("Country data does not match the selected run.");
  for (const series of Object.values(data.series)) {
    if (series.length !== 8760 || series.some((v) => v !== null && !Number.isSafeInteger(v)))
      throw new Error("Invalid hourly series.");
  }
  for (const area of data.generation)
    for (const refs of [area.model, area.lower, area.upper, area.observed]) {
      if (refs.length !== 13 || refs.some((ref) => !data.series[ref]))
        throw new Error("Incomplete generation series.");
    }
  for (const area of data.prices)
    if (!data.series[area.model] || !data.series[area.observed])
      throw new Error("Incomplete price series.");
  return data;
}

export async function decodeCountryBytes(
  bytes: ArrayBuffer,
  entry: Pick<CountryEntry, "sha256" | "json_sha256">,
): Promise<unknown> {
  const header = new Uint8Array(bytes, 0, Math.min(bytes.byteLength, 2));
  const gzipEncoded = header[0] === 0x1f && header[1] === 0x8b;
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  const hex = Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
  if (hex !== (gzipEncoded ? entry.sha256 : entry.json_sha256))
    throw new Error("Country data changed during download. Please refresh the page.");
  if (!gzipEncoded) return JSON.parse(new TextDecoder().decode(bytes)) as unknown;
  if (typeof DecompressionStream === "undefined")
    throw new Error(
      "This browser cannot open compressed data. Please use a current browser, or download the data file below.",
    );
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
  return JSON.parse(await new Response(stream).text()) as unknown;
}

export function dateWindow(start: string, end: string): [number, number] | null {
  if (![start, end].every((value) => /^2025-\d{2}-\d{2}$/.test(value))) return null;
  const a = Date.parse(start + "T00:00:00Z");
  const b = Date.parse(end + "T00:00:00Z");
  if (
    !Number.isFinite(a) ||
    !Number.isFinite(b) ||
    new Date(a).toISOString().slice(0, 10) !== start ||
    new Date(b).toISOString().slice(0, 10) !== end
  )
    return null;
  const lo = (a - YEAR_START) / HOUR;
  const hi = (b - YEAR_START) / HOUR + 24;
  return lo >= 0 && hi <= 8760 && lo < hi ? [lo, hi] : null;
}

export function plotSeries(
  data: CountryData,
  modelRef: string,
  observedRef: string,
  scale: number,
  range: [number, number],
  resolution: Resolution,
  bounds?: [string, string],
): PlotPoint[] {
  const rows: PlotPoint[] = [];
  const step = resolution === "hourly" ? 1 : 24;
  const mean = (ref: string, start: number, stop: number): number | null => {
    const values = data.series[ref];
    if (!values) return null;
    let sum = 0;
    for (let i = start; i < stop; i++) {
      const v = values[i];
      if (v === null || v === undefined) return null;
      sum += v;
    }
    return sum / (stop - start) / scale;
  };
  for (let i = range[0]; i < range[1]; i += step) {
    const stop = Math.min(i + step, range[1]);
    const lo = bounds ? mean(bounds[0], i, stop) : null;
    const hi = bounds ? mean(bounds[1], i, stop) : null;
    rows.push({
      time: YEAR_START + i * HOUR,
      model: mean(modelRef, i, stop),
      observed: mean(observedRef, i, stop),
      interval: lo !== null && hi !== null ? [lo, hi] : null,
    });
  }
  return rows;
}

export function csvCell(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value);
  return /[",\n\r]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}
export function toCsv(rows: unknown[][]): string {
  return rows.map((row) => row.map(csvCell).join(",")).join("\n") + "\n";
}
const decoded = (data: CountryData, ref: string, hour: number, scale: number) => {
  const v = data.series[ref]?.[hour];
  return v === null || v === undefined ? null : v / scale;
};

export function priceCsv(data: CountryData, scale: number): string {
  const rows: unknown[][] = [
    [
      "utc_start",
      ...data.prices.flatMap((p) => [`${p.zone}_observed_eur_mwh`, `${p.zone}_model_eur_mwh`]),
    ],
  ];
  for (let t = 0; t < 8760; t++)
    rows.push([
      new Date(YEAR_START + t * HOUR).toISOString(),
      ...data.prices.flatMap((p) => [
        decoded(data, p.observed, t, scale),
        decoded(data, p.model, t, scale),
      ]),
    ]);
  return toCsv(rows);
}
export function generationCsv(
  data: CountryData,
  area: GenerationArea,
  manifest: ExplorerManifest,
): string {
  const rows: unknown[][] = [
    [
      "utc_start",
      "area",
      ...manifest.technologies.flatMap((f) =>
        ["observed", "model_illustration", "conditional_lower", "conditional_upper"].map(
          (k) => `${f.id}_${k}_mw`,
        ),
      ),
    ],
  ];
  for (let t = 0; t < 8760; t++)
    rows.push([
      new Date(YEAR_START + t * HOUR).toISOString(),
      area.id,
      ...manifest.technologies.flatMap((_, i) =>
        [area.observed, area.model, area.lower, area.upper].map((refs) =>
          decoded(data, refs[i]!, t, manifest.generation_scale),
        ),
      ),
    ]);
  return toCsv(rows);
}
export function sourceGenerationCsv(data: CountryData, scale: number): string {
  const columns = data.source_generation.flatMap((a) =>
    Object.entries(a.psr).map(([code, ref]) => ({ column: `${a.area}_${code}_mwh`, ref })),
  );
  const rows: unknown[][] = [["utc_start", ...columns.map((c) => c.column)]];
  for (let t = 0; t < 8760; t++)
    rows.push([
      new Date(YEAR_START + t * HOUR).toISOString(),
      ...columns.map((c) => decoded(data, c.ref, t, scale)),
    ]);
  return toCsv(rows);
}
export function recordCsv(rows: Record<string, unknown>[]): string {
  const keys = [...new Set(rows.flatMap((row) => Object.keys(row)))];
  return toCsv([keys, ...rows.map((row) => keys.map((k) => row[k]))]);
}
export function saveCsv(name: string, content: string): void {
  const url = URL.createObjectURL(new Blob([content], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
