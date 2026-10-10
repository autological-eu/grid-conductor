/** Publish only the carbon metric used by the baseline sidebar.
 * Inputs are ignored processed ENTSO-E generation data, not bundled hourly arrays.
 * Run Python publish_map_carbon_2025.py first to reconstruct these inputs. */
import { readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import assert from "node:assert/strict";
import { meanCarbonSpread, type CarbonHour } from "../src/lib/carbon-spread";

const folder = "data/carbon-pilot/baseline-inputs-2025";
const bytes = await readFile(`${folder}/map-summary.json`);
const source = JSON.parse(bytes.toString());
assert.equal(source.year, 2025);
const hash = (raw: Uint8Array) => createHash("sha256").update(raw).digest("hex");
const prices: Record<string, (number | null)[]> = {};
const carbon: Record<string, CarbonHour[]> = {};
for (const [zone, receipt] of Object.entries(source.hourly_files)) {
  const record = receipt as { sha256: string };
  const raw = await readFile(`${folder}/hourly/${zone}.json`);
  assert.equal(hash(raw), record.sha256, `Changed generation input: ${zone}`);
  const quote = await readFile(`public/research/zone-prices-2025/${zone}.json`);
  assert.equal(hash(quote), source.price_sha256[zone], `Changed price input: ${zone}`);
  prices[zone] = JSON.parse(quote.toString());
  carbon[zone] = JSON.parse(raw.toString());
  assert.equal(prices[zone]?.length, 8760);
  assert.equal(carbon[zone]?.length, 8760);
}
const borders: Record<string, ReturnType<typeof meanCarbonSpread>> = {};
for (const pair of Object.keys(source.borders)) {
  const [a, b] = pair.split(">");
  assert(a && b && prices[a] && prices[b] && carbon[a] && carbon[b]);
  const value = meanCarbonSpread(prices[a], prices[b], carbon[a], carbon[b]);
  assert.deepEqual(value, meanCarbonSpread(prices[b], prices[a], carbon[b], carbon[a]));
  borders[pair] = value;
}
const report = {
  schema_version: 1,
  year: 2025,
  unit: "g CO2e/kWh",
  selection: source.selection,
  borders,
  source_summary_sha256: hash(bytes),
  publisher_sha256: hash(await readFile(import.meta.path)),
  metric_sha256: hash(await readFile("src/lib/carbon-spread.ts")),
  price_sha256: source.price_sha256,
  generation_sha256: Object.fromEntries(
    Object.entries(source.hourly_files).map(([zone, record]) => [
      zone,
      (record as { sha256: string }).sha256,
    ]),
  ),
  factor_version: source.factor_version,
  factor_source: source.factor_source,
  factors: source.factors,
  zones: source.zones,
  provenance: source.provenance,
  limitations: source.limitations,
};
await writeFile("public/research/carbon-spreads-2025.json", JSON.stringify(report) + "\n");
console.log(
  `Verified and published ${Object.keys(borders).length} unchanged border carbon metrics`,
);
