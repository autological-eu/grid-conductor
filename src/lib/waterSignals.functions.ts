import { createServerFn } from "@tanstack/react-start";

export const waterSignals = createServerFn({ method: "POST" })
  .inputValidator((data: unknown) => data as Record<string, unknown>)
  .handler(async ({ data }) => {
    const { handleWaterSignals } = await import("./waterSignals.server");
    return await handleWaterSignals(data as never);
  });
