/** All public assets share Vite's project-site base path. */
export function publicAsset(path: string): string {
  return `${import.meta.env?.BASE_URL ?? "/grid-conductor/"}${path.replace(/^\/+/, "")}`;
}

let screening: Promise<Record<string, unknown>> | undefined;
export function loadScreeningData(): Promise<Record<string, unknown>> {
  screening ??= fetch(publicAsset("research/entsoe-fast-targets.json"))
    .then(async (response) => {
      if (!response.ok) throw new Error(`Screening data unavailable (${response.status})`);
      const data = (await response.json()) as Record<string, unknown>;
      if (data["schema_version"] !== 3 || !Array.isArray(data["targets"])) {
        throw new Error("Unsupported screening dataset. Expected annual schema v3.");
      }
      return data;
    })
    .catch((error: unknown) => {
      screening = undefined;
      throw error;
    });
  return screening;
}
