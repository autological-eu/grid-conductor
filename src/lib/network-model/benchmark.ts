import { parseNetworkInput, type NetworkInput } from "./schema";

/** Apply an explicit policy assumption to the pinned zero-carbon-cost archive.
 * Always use the original input, never an already adjusted scenario/workspace.
 */
export function benchmarkWithCarbonPrice(value: unknown, price: number): NetworkInput {
  if (![0, 40, 80, 120].includes(price)) throw new Error("Unsupported benchmark carbon price");
  const input = parseNetworkInput(value);
  if (!["pypsa-eur-37-2013-168h", "pypsa-eur-37-2013-168h-kirchhoff"].includes(input.dataset_id))
    throw new Error("Carbon sensitivity requires the original unpriced benchmark input");
  if (price === 0) return input;
  for (const generator of input.generators) {
    if (typeof generator.co2_t_per_mwh !== "number")
      throw new Error("Carbon sensitivity requires complete generation emissions factors");
    generator.cost_eur_mwh += price * generator.co2_t_per_mwh;
  }
  input.dataset_id += `-carbon-${price}`;
  input.provenance.assumptions.push(
    `Illustrative carbon price €${price}/t CO₂ added to archived zero-carbon generator costs using direct generation intensity. Not an observed ETS price or historical valuation.`,
  );
  return parseNetworkInput(input);
}
