export type CarbonHour = readonly [number | null, number | null, number | null];

/** UTC hourly production intensities, restricted to jointly observed price gaps. */
export function meanCarbonSpread(
  pricesA: readonly (number | null)[],
  pricesB: readonly (number | null)[],
  carbonA: readonly CarbonHour[],
  carbonB: readonly CarbonHour[],
) {
  if (![pricesB, carbonA, carbonB].every((rows) => rows.length === pricesA.length))
    throw new Error("Carbon/price chronology mismatch");
  let selected = 0,
    fullHours = 0,
    subsetHours = 0,
    fullSum = 0,
    subsetSum = 0;
  const known = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
  for (let i = 0; i < pricesA.length; i++) {
    const pa = pricesA[i],
      pb = pricesB[i];
    if (!known(pa) || !known(pb) || Math.abs(pa - pb) <= 5) continue;
    selected++;
    const a = carbonA[i],
      b = carbonB[i];
    if (!a || !b) throw new Error("Missing carbon row");
    if (known(a[0]) && known(b[0])) {
      fullHours++;
      fullSum += Math.abs(a[0] - b[0]);
    }
    if (known(a[1]) && known(b[1])) {
      subsetHours++;
      subsetSum += Math.abs(a[1] - b[1]);
    }
  }
  const complete = selected > 0 && fullHours === selected;
  return {
    value: complete ? fullSum / fullHours : subsetHours ? subsetSum / subsetHours : null,
    hours: complete ? fullHours : subsetHours,
    selectedHours: selected,
    partial: !complete,
  };
}
