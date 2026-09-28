// Server-only Electricity Maps client.
// v4 everywhere. Auth header is `auth-token` (not Bearer). A real User-Agent is
// required or Cloudflare answers 403 "error code: 1010".
const BASE = "https://api.electricitymaps.com";

export class EmapsError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

function qs(input: Record<string, unknown>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(input)) {
    if (v === undefined || v === null) continue;
    p.set(k, String(v));
  }
  const s = p.toString();
  return s ? `?${s}` : "";
}

export async function emapsFetch<T>(path: string, query: Record<string, unknown> = {}): Promise<T> {
  const apiKey = process.env["ELECTRICITY_MAPS_API_KEY"];
  if (!apiKey) throw new EmapsError("ELECTRICITY_MAPS_API_KEY is not configured", 0);
  const url = `${BASE}${path}${qs(query)}`;
  const res = await fetch(url, {
    headers: {
      "auth-token": apiKey,
      "User-Agent": "lovable-grid-simulator/1.0",
      Accept: "application/json",
    },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new EmapsError(`Electricity Maps ${res.status}: ${body.slice(0, 300)}`, res.status);
  }
  return (await res.json()) as T;
}

export function pickRows<T = Record<string, unknown>>(resp: unknown): T[] {
  const r = resp as Record<string, unknown> | null;
  if (r == null) return [];
  if (Array.isArray(r["data"])) return r["data"] as T[];
  if (Array.isArray(r["history"])) return r["history"] as T[];
  if (Array.isArray(r["forecast"])) return r["forecast"] as T[];
  return [resp as T];
}

export type SignalKey = "price" | "carbon" | "load" | "mix" | "flows";

export const SIGNAL_PATHS: Record<SignalKey, string> = {
  price: "/v4/price-day-ahead/past-range",
  carbon: "/v4/carbon-intensity/past-range",
  load: "/v4/total-load/past-range",
  mix: "/v4/electricity-mix/past-range",
  flows: "/v4/electricity-flows/past-range",
};

export type RawPoint = Record<string, unknown> & { datetime?: string };

export async function fetchSignalRange(
  signal: SignalKey,
  zone: string,
  start: string,
  end: string,
): Promise<RawPoint[]> {
  const extra: Record<string, unknown> = signal === "mix" ? { breakdownType: "normal" } : {};
  const resp = await emapsFetch(SIGNAL_PATHS[signal], {
    zone,
    start,
    end,
    temporalGranularity: "hourly",
    disableCallerLookup: true,
    ...extra,
  });
  return pickRows<RawPoint>(resp);
}
