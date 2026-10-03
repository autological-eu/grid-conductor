import { expect, test } from "bun:test";
import { summarizeStep1 } from "../src/lib/step1";

test("corridor spread removes capacity multiplier and includes reverse price observations", () => {
  const result = summarizeStep1({
    targets: [
      {
        month: "2025",
        border: "FR>IT-North",
        deadweight_loss_meur_year: 9999,
        realized_rent_meur_year: 20,
        opportunity_meur_year: { "500": 200 },
        observed_quarters: 35040,
      },
      {
        month: "2025",
        border: "IT-North>FR",
        deadweight_loss_meur_year: 0,
        realized_rent_meur_year: -3,
        opportunity_meur_year: { "500": 10 },
        observed_quarters: 35040,
      },
    ],
  });
  expect(result.targets[0]?.price_spread_eur_mw_year).toBe(420000);
  expect(result.targets[0]?.market_opportunity_meur).toBe(9999);
  expect(result.targets[0]?.mean_absolute_spread_eur_mwh).toBeCloseTo(420000 / 8760);
  expect(result.targets[0]?.congestion_rent_meur_year).toBe(17);
});

test("incompatible directional coverage has no fabricated mean", () => {
  const result = summarizeStep1({
    targets: [
      {
        month: "2025",
        border: "FR>IT-North",
        deadweight_loss_meur_year: 1,
        observed_quarters: 4,
        opportunity_meur_year: { "500": 1 },
      },
    ],
  });
  expect(result.targets[0]?.mean_absolute_spread_eur_mwh).toBeNull();
  expect(result.targets[0]?.congestion_rent_meur_year).toBeNull();
});
