import { createServerFn } from "@tanstack/react-start";

/** Create (or top up) the import plan: one job per zone and signal. */
export const planImport = createServerFn({ method: "POST" }).handler(async () => {
  const { planJobs } = await import("./import.server");
  return planJobs();
});

export const getImportProgress = createServerFn({ method: "GET" }).handler(async () => {
  const { importProgress } = await import("./import.server");
  return importProgress();
});

/** Process a bounded number of 10-day chunks; safe to call repeatedly. */
export const runImportBatch = createServerFn({ method: "POST" })
  .inputValidator((data: { chunks?: number } | undefined) => data ?? {})
  .handler(async ({ data }) => {
    const { importBatch } = await import("./import.server");
    return importBatch({ chunks: data.chunks ?? 6 });
  });
