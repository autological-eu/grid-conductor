// Server-only ENTSO-E Transparency Platform client.
// Used for official cross-border capacity (NTC) figures, which Electricity Maps
// does not publish. Falls back silently when no key or no published data.
const BASE = "https://web-api.tp.entsoe.eu/api";

// EIC area codes for the bidding zones we model.
export const EIC_BY_ZONE: Record<string, string> = {
  AT: "10YAT-APG------L",
  BE: "10YBE----------2",
  BG: "10YCA-BULGARIA-R",
  CH: "10YCH-SWISSGRIDZ",
  CZ: "10YCZ-CEPS-----N",
  DE: "10Y1001A1001A82H",
  "DK-DK1": "10YDK-1--------W",
  "DK-DK2": "10YDK-2--------M",
  EE: "10Y1001A1001A39I",
  ES: "10YES-REE------0",
  FI: "10YFI-1--------U",
  FR: "10YFR-RTE------C",
  GR: "10YGR-HTSO-----Y",
  HR: "10YHR-HEP------M",
  HU: "10YHU-MAVIR----U",
  IE: "10Y1001A1001A59C",
  "IT-CNO": "10Y1001A1001A70O",
  "IT-CSO": "10Y1001A1001A71M",
  "IT-NO": "10Y1001A1001A73I",
  "IT-SAR": "10Y1001A1001A74G",
  "IT-SIC": "10Y1001A1001A75E",
  "IT-SO": "10Y1001A1001A788",
  LT: "10YLT-1001A0008Q",
  LU: "10YLU-CEGEDEL-NQ",
  LV: "10YLV-1001A00074",
  NL: "10YNL----------L",
  "NO-NO1": "10YNO-1--------2",
  "NO-NO2": "10YNO-2--------T",
  "NO-NO3": "10YNO-3--------J",
  "NO-NO4": "10YNO-4--------9",
  "NO-NO5": "10Y1001A1001A48H",
  PL: "10YPL-AREA-----S",
  PT: "10YPT-REN------W",
  RO: "10YRO-TEL------P",
  RS: "10YCS-SERBIATSOV",
  "SE-SE1": "10Y1001A1001A44P",
  "SE-SE2": "10Y1001A1001A45N",
  "SE-SE3": "10Y1001A1001A46L",
  "SE-SE4": "10Y1001A1001A47J",
  SI: "10YSI-ELES-----O",
  SK: "10YSK-SEPS-----K",
};

function stamp(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getUTCFullYear()}${p(d.getUTCMonth() + 1)}${p(d.getUTCDate())}${p(d.getUTCHours())}00`;
}

/**
 * Day-ahead net transfer capacity (document A61, business type A93) for a
 * direction, in MW. Returns the highest published value in the window, or null
 * when the key is missing or ENTSO-E publishes nothing for this border.
 */
export async function fetchNtcMw(
  fromZone: string,
  toZone: string,
  start: Date,
  end: Date,
): Promise<number | null> {
  const token = process.env["ENTSOE_API_KEY"];
  const inDomain = EIC_BY_ZONE[toZone];
  const outDomain = EIC_BY_ZONE[fromZone];
  if (!token || !inDomain || !outDomain) return null;

  const url =
    `${BASE}?securityToken=${encodeURIComponent(token)}` +
    `&documentType=A61&businessType=A93&contract_MarketAgreement.Type=A01` +
    `&in_Domain=${inDomain}&out_Domain=${outDomain}` +
    `&periodStart=${stamp(start)}&periodEnd=${stamp(end)}`;

  try {
    const res = await fetch(url, { headers: { Accept: "application/xml" } });
    if (!res.ok) return null;
    const xml = await res.text();
    const values = [...xml.matchAll(/<quantity>([\d.]+)<\/quantity>/g)].map((m) =>
      Number(m[1]),
    );
    if (!values.length) return null;
    return Math.max(...values);
  } catch {
    return null;
  }
}
