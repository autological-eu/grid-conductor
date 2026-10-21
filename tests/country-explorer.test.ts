import { describe, expect, test } from "bun:test";
import { createHash } from "node:crypto";
import { gzipSync } from "node:zlib";
import {
  dateWindow,
  decodeCountryBytes,
  plotSeries,
  priceCsv,
  recordCsv,
  technologyTotals,
  type CountryData,
} from "../src/lib/country-explorer";

describe("country explorer coverage and exports", () => {
  test("oil quantities compare the same observed hours without zero-filling missing oil", () => {
    expect(technologyTotals([10, 20, 30], [5, null, 15], 10)).toEqual({
      annualModel: 0.000006,
      observed: 0.000002,
      matchedModel: 0.000004,
      known: 2,
    });
    expect(technologyTotals([0, 0], [null, null], 10)).toEqual({
      annualModel: 0,
      observed: null,
      matchedModel: null,
      known: 0,
    });
    expect(technologyTotals([0, 0], [0, 0], 10)).toEqual({
      annualModel: 0,
      observed: 0,
      matchedModel: 0,
      known: 2,
    });
  });
  test("integrity checks work whether the host serves gzip or transparently decoded JSON", async () => {
    const value = { country: "NO", source: null, price: -12.25 };
    const json = new TextEncoder().encode(JSON.stringify(value));
    const gzip = Uint8Array.from(gzipSync(json));
    const sha = (bytes: Uint8Array) => createHash("sha256").update(bytes).digest("hex");
    const entry = { sha256: sha(gzip), json_sha256: sha(json) };
    expect(await decodeCountryBytes(json.buffer, entry)).toEqual(value);
    expect(await decodeCountryBytes(gzip.buffer, entry)).toEqual(value);
    await expect(decodeCountryBytes(new TextEncoder().encode("{}").buffer, entry)).rejects.toThrow(
      "changed during download",
    );
  });
  test("date windows include every hour of the final day and reject invalid dates", () => {
    expect(dateWindow("2025-01-01", "2025-12-31")).toEqual([0, 8760]);
    expect(dateWindow("2025-03-30", "2025-03-30")).toEqual([2112, 2136]); // UTC day, no DST loss.
    expect(dateWindow("2025-02-30", "2025-03-01")).toBeNull();
    expect(dateWindow("2025-06-01", "2025-05-31")).toBeNull();
    expect(dateWindow("2024-12-31", "2025-01-01")).toBeNull();
  });
  test("missing observations remain gaps in hourly and daily charts", () => {
    const source = Array<number | null>(8760).fill(100);
    source[12] = null;
    const data = {
      series: {
        m: Array<number>(8760).fill(200),
        o: source,
        l: Array<number>(8760).fill(150),
        h: Array<number>(8760).fill(250),
      },
    } as unknown as CountryData;
    const hourly = plotSeries(data, "m", "o", 10, [0, 24], "hourly", ["l", "h"]);
    expect(hourly).toHaveLength(24);
    expect(hourly[12]?.observed).toBeNull();
    expect(hourly[12]?.model).toBe(20);
    const daily = plotSeries(data, "m", "o", 10, [0, 48], "daily", ["l", "h"]);
    expect(daily[0]?.observed).toBeNull();
    expect(daily[1]?.observed).toBe(10);
    expect(daily[0]?.interval).toEqual([15, 25]);
  });
  test("price CSV keeps all zones, missing cells, negative prices and all8760 hours", () => {
    const missing = Array<number | null>(8760).fill(null);
    const data = {
      prices: [
        { zone: "NO1", model: "m", observed: "o" },
        { zone: "NO5", model: "m", observed: "absent" },
      ],
      series: {
        m: Array<number>(8760).fill(-1250),
        o: Array<number>(8760).fill(0),
        absent: missing,
      },
    } as unknown as CountryData;
    const rows = priceCsv(data, 1000).trimEnd().split("\n");
    expect(rows).toHaveLength(8761);
    expect(rows[0]).toContain("NO5_observed_eur_mwh");
    expect(rows[1]).toBe("2025-01-01T00:00:00.000Z,0,-1.25,,-1.25");
    expect(rows.at(-1)).toStartWith("2025-12-31T23:00:00.000Z");
  });
  test("source CSV preserves provider strings, zero and unknown separately", () => {
    expect(
      recordCsv([
        { Area: 'a,"b"', generation: 0 },
        { Area: "unknown", generation: null },
      ]),
    ).toBe('Area,generation\n"a,""b""",0\nunknown,\n');
  });
});
