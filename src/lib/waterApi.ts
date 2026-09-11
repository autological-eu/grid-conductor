export type WaterMode = "origin" | "fast";

export interface WaterPoint {
  datetime: string;
  isEstimated?: boolean;
  w1_consumption_L_per_kWh: number;
  w1_production_L_per_kWh: number;
  w2_withdrawal_L_per_kWh: number;
  w2_withdrawal_total_L_per_kWh: number;
  w3_imported_water_share: number;
  w3_imported_power_share: number;
  w3_by_origin: Record<string, { mw: number; L_per_kWh: number; water_m3_per_h: number; estimated?: boolean }>;
  by_source: Record<string, { mw: number; factor_L_per_kWh: number; water_m3_per_h: number }>;
  profile_calibrated?: boolean;
  w4_level?: "low" | "medium" | "high";
  carbon_g_per_kWh?: number | null;
  price_eur_per_MWh?: number | null;
}

export interface WaterMeta {
  unit: string;
  method: string;
  includeHydro: boolean;
  factors: string;
  profiles: string;
  generatedAt: string;
}

export interface SeriesResponse {
  meta: WaterMeta;
  zone: string;
  neighbours: string[];
  points: WaterPoint[];
  w4_best_window?: { start: string; hours: number; mean_L_per_kWh: number } | null;
}

export interface BenchmarkRow {
  zone: string;
  days?: number;
  avg_L_per_kWh?: number;
  min?: number;
  max?: number;
  daily?: number[];
  carbon_avg_g_per_kWh?: number | null;
  error?: string;
}

export interface BenchmarkResponse {
  meta: WaterMeta;
  rows: BenchmarkRow[];
}

export async function callWaterSignals<T = unknown>(body: Record<string, unknown>): Promise<T> {
  const res = await fetch("/api/water-signals", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const json = (await res.json()) as { error?: string } & T;
  if (!res.ok || (json && typeof json === "object" && "error" in json && json.error)) {
    throw new Error(json?.error ?? `Request failed (${res.status})`);
  }
  return json as T;
}
