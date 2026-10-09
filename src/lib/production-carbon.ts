import { useQuery } from "@tanstack/react-query";
import { publicAsset } from "./research";

type Estimate = {
  geographic_scope: string;
  expected_hours: number;
  complete_generation_hours: number;
  full_lifecycle_gco2e_kwh: number | null;
  mapped_subset_gco2e_kwh: number | null;
  mapped_generation_share: number | null;
};
type Report = {
  schema_version: number;
  borders: Record<string, { zones: Record<string, Estimate> }>;
};
export function useProductionCarbon() {
  return useQuery({
    queryKey: ["production-carbon-map-2025"],
    queryFn: async () => {
      const response = await fetch(publicAsset("research/production-carbon-2025/map-summary.json"));
      if (!response.ok) throw new Error("Carbon data unavailable");
      const value = (await response.json()) as Report;
      if (value.schema_version !== 1 || !value.borders)
        throw new Error("Unsupported carbon report");
      return value;
    },
    staleTime: Infinity,
  });
}
