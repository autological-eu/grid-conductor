// Shared (client-safe) definition of the analysis window: the last full year,
// ending at midnight UTC of yesterday.
export function analysisWindow(now: Date = new Date()): { start: Date; end: Date } {
  const end = new Date(
    Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()),
  );
  end.setUTCDate(end.getUTCDate() - 1);
  const start = new Date(end);
  start.setUTCFullYear(start.getUTCFullYear() - 1);
  return { start, end };
}

export const SIGNALS = ["price", "carbon", "load", "mix", "flows"] as const;
export type Signal = (typeof SIGNALS)[number];

export const SIGNAL_LABELS: Record<Signal, string> = {
  price: "Day-ahead price",
  carbon: "Carbon intensity",
  load: "Demand",
  mix: "Generation mix",
  flows: "Cross-border flows",
};
