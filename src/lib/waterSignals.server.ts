// @ts-nocheck -- kept byte-identical to the supplied reference implementation
// src/lib/waterSignals.server.ts — SERVER-ONLY. Never import this file from client components.
import { SignalService, type SignalRequest } from "./signals";
import { WATER_FACTORS, ZONE_PROFILES } from "./seedData";

const EM_BASE = "https://api.electricitymaps.com";
const ALLOWED = /^\/v4\/(electricity-mix|electricity-flows|carbon-intensity|price-day-ahead)\/(latest|history|forecast|past|past-range)$/;
const TTL_S: Record<string, number> = { latest: 600, history: 1800, forecast: 1800, past: 86400, "past-range": 21600 };
const cache = new Map<string, { at: number; payload: unknown }>();

function getToken(): string {
  const token = (process.env['ELECTRICITY_MAPS_API_KEY'] || process.env['ELECTRICITYMAPS_API_TOKEN']) as string | undefined;
  if (!token) throw new Error("ELECTRICITYMAPS_API_TOKEN is not available on the server");
  return token;
}

async function emGet(path: string, params: Record<string, string | number | boolean>) {
  if (!ALLOWED.test(path)) throw new Error(`path not allowed: ${path}`);
  const qs = new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString();
  const key = `${path}?${qs}`;
  const ttl = TTL_S[path.split("/").pop()!] ?? 600;
  const hit = cache.get(key);
  if (hit && (Date.now() - hit.at) / 1000 < ttl) return hit.payload;
  const res = await fetch(`${EM_BASE}${key}`, { headers: { "auth-token": getToken() } });
  if (!res.ok) throw new Error(`Electricity Maps ${res.status} on ${path} (${params.zone ?? ""})`);
  const raw = await res.json();
  // v4 returns the series under `history` / `forecast`; normalise to `data` for the signal service.
  const payload =
    raw && !Array.isArray(raw.data)
      ? { ...raw, data: Array.isArray(raw.history) ? raw.history : Array.isArray(raw.forecast) ? raw.forecast : raw.data }
      : raw;
  cache.set(key, { at: Date.now(), payload });
  if (cache.size > 1000) cache.delete(cache.keys().next().value as string);
  return payload;
}

export type WaterSignalsBody = SignalRequest & { profileOverrides?: Record<string, unknown> };

export async function handleWaterSignals(body: WaterSignalsBody) {
  const profiles = body.profileOverrides
    ? { ...ZONE_PROFILES, zones: ZONE_PROFILES.zones.map((z: any) => (body.profileOverrides![z.key] ? { ...z, cooling: body.profileOverrides![z.key] } : z)) }
    : ZONE_PROFILES;
  const svc = new SignalService(WATER_FACTORS as any, profiles as any, emGet);
  return svc.handle(body);
}
