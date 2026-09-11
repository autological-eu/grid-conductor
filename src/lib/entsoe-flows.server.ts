// Server-only ENTSO-E Transparency Platform readers for hourly cross-border
// physical flows (document A11) and actual total load (document A65).
// Electricity Maps' plan does not cover these signals, so ENTSO-E is the source
// of truth for congestion detection.
import { EIC_BY_ZONE } from "./entsoe.server";

const BASE = "https://web-api.tp.entsoe.eu/api";

function stamp(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getUTCFullYear()}${p(d.getUTCMonth() + 1)}${p(d.getUTCDate())}${p(d.getUTCHours())}00`;
}

export type Point = { ts: string; value: number };

/** Parse an ENTSO-E Publication/GL market document into hourly points. */
export function parseTimeSeries(xml: string): Point[] {
  const out = new Map<string, { sum: number; n: number }>();
  const periods = xml.matchAll(
    /<Period>[\s\S]*?<start>([^<]+)<\/start>[\s\S]*?<resolution>([^<]+)<\/resolution>([\s\S]*?)<\/Period>/g,
  );
  for (const [, start, resolution, body] of periods) {
    const t0 = Date.parse(start!);
    const minutes =
      resolution === "PT15M" ? 15 : resolution === "PT30M" ? 30 : resolution === "PT60M" ? 60 : 60;
    for (const [, pos, qty] of body!.matchAll(
      /<position>(\d+)<\/position>\s*<quantity>([\d.\-]+)<\/quantity>/g,
    )) {
      const t = t0 + (Number(pos) - 1) * minutes * 60_000;
      const hour = new Date(Math.floor(t / 3_600_000) * 3_600_000).toISOString();
      const acc = out.get(hour) ?? { sum: 0, n: 0 };
      acc.sum += Number(qty);
      acc.n += 1;
      out.set(hour, acc);
    }
  }
  return [...out.entries()].map(([ts, a]) => ({ ts, value: a.sum / a.n }));
}

async function entsoe(params: Record<string, string>): Promise<string | null> {
  const token = process.env["ENTSOE_API_KEY"];
  if (!token) return null;
  const q = new URLSearchParams({ securityToken: token, ...params });
  // ENTSO-E allows 400 requests/minute and temporarily bans on excess; back off.
  let res = await fetch(`${BASE}?${q}`, { headers: { Accept: "application/xml" } });
  for (let attempt = 0; res.status === 429 && attempt < 6; attempt++) {
    await new Promise((r) => setTimeout(r, 30_000 * (attempt + 1)));
    res = await fetch(`${BASE}?${q}`, { headers: { Accept: "application/xml" } });
  }
  if (!res.ok) throw new Error(`ENTSO-E ${res.status}`);
  const xml = await res.text();
  if (xml.includes("Acknowledgement_MarketDocument")) return null; // no data published
  return xml;
}

/** Hourly physical flow from one zone to another, in MW (always >= 0). */
export async function fetchPhysicalFlow(
  fromZone: string,
  toZone: string,
  start: Date,
  end: Date,
): Promise<Point[]> {
  const out_Domain = EIC_BY_ZONE[fromZone];
  const in_Domain = EIC_BY_ZONE[toZone];
  if (!out_Domain || !in_Domain) return [];
  const xml = await entsoe({
    documentType: "A11",
    in_Domain,
    out_Domain,
    periodStart: stamp(start),
    periodEnd: stamp(end),
  });
  return xml ? parseTimeSeries(xml) : [];
}

/** Hourly actual total load for a zone, in MW. */
export async function fetchActualLoad(
  zone: string,
  start: Date,
  end: Date,
): Promise<Point[]> {
  const domain = EIC_BY_ZONE[zone];
  if (!domain) return [];
  const xml = await entsoe({
    documentType: "A65",
    processType: "A16",
    outBiddingZone_Domain: domain,
    periodStart: stamp(start),
    periodEnd: stamp(end),
  });
  return xml ? parseTimeSeries(xml) : [];
}
