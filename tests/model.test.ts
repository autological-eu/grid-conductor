import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { solveScenarios, type ScreeningRow } from "../src/lib/fast-entsoe-lp";
import { summarizeStep1 } from "../src/lib/step1";

const published = JSON.parse(readFileSync("public/research/entsoe-fast-targets.json", "utf8"));
const rows = published.targets as Array<
  ScreeningRow & { deadweight_loss_meur_year: number | null }
>;

describe("unchanged annual screening semantics", () => {
  test("all published decision-matrix scenarios stay within their DWL cap", () => {
    for (const row of rows) {
      const cap = row.deadweight_loss_meur_year ?? 0;
      for (const result of solveScenarios(row)) {
        expect(result.annual_welfare_gain_meur).toBeGreaterThanOrEqual(0);
        expect(result.annual_welfare_gain_meur).toBeLessThanOrEqual(cap + 1e-6);
        expect(result.congestion_hours).toBe(row.congested_quarters / 4);
      }
    }
  });

  test("cable welfare is the exact annual trapezoid, with no x12 extrapolation", () => {
    const row = rows.find((row) => row.border === "FR>IT-North")!;
    const q = Math.min(1000, row.average_positive_spread_eur_mwh! / row.slope_a!);
    const expected =
      ((row.average_positive_spread_eur_mwh! * q - 0.5 * row.slope_a! * q * q) *
        0.25 *
        row.congested_quarters) /
      1e6;
    const cable = solveScenarios(row).find((result) => result.scenario === "cable_1000")!;
    expect(cable.annual_welfare_gain_meur).toBeCloseTo(expected, 10);
  });

  test("battery LP preserves daily cycles, efficiency and finite-difference shadow prices", () => {
    const row = rows.find((row) => row.border === "FR>IT-North")!;
    const result = solveScenarios(row).find((result) => result.scenario === "battery_200")!;
    expect(result.annual_welfare_gain_meur).toBeCloseTo(
      Math.min(
        (200 * 0.9 * row.average_positive_spread_eur_mwh! * 365) / 1e6,
        row.deadweight_loss_meur_year!,
      ),
      6,
    );
    expect(result.shadow_price_ateur_mwh).toBeCloseTo(
      0.9 * row.average_positive_spread_eur_mwh!,
      4,
    );
  });

  test("map exposes only positive claimable annual opportunities and preserves carbon proxy", () => {
    const summary = summarizeStep1(published);
    expect(summary.targets.length).toBeGreaterThan(50);
    for (const target of summary.targets) {
      const row = rows.find((row) => row.border === target.id)!;
      expect(target.market_opportunity_meur).toBeCloseTo(row.deadweight_loss_meur_year!, 2);
      expect(target.congested_hours).toBe(Math.round(row.congested_quarters / 4));
    }
  });
});
