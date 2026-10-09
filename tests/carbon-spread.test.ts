import { expect, test } from "bun:test";
import { meanCarbonSpread } from "../src/lib/carbon-spread";

test("averages hourly absolute contrasts, not the absolute contrast of means", () => {
  const result = meanCarbonSpread(
    [10, 10],
    [0, 0],
    [
      [10, 10, 1],
      [90, 90, 1],
    ],
    [
      [90, 90, 1],
      [10, 10, 1],
    ],
  );
  expect(result.value).toBe(80);
  expect(result.partial).toBe(false);
});
test("partial factors compare only simultaneously known subsets and retain coverage", () => {
  const result = meanCarbonSpread(
    [10, 10, 5, null],
    [0, 0, 0, 0],
    [
      [null, 20, 0.5],
      [null, null, null],
      [null, 500, 0.5],
      [null, 100, 0.5],
    ],
    [
      [null, 50, 0.9],
      [null, 70, 0.9],
      [null, 0, 0.9],
      [null, 0, 0.9],
    ],
  );
  expect(result).toEqual({ value: 30, hours: 1, selectedHours: 2, partial: true });
});
test("missing data stays unavailable and incompatible chronology fails", () => {
  expect(meanCarbonSpread([10], [0], [[null, null, null]], [[null, null, null]]).value).toBeNull();
  expect(() => meanCarbonSpread([10], [], [], [])).toThrow("chronology mismatch");
});
