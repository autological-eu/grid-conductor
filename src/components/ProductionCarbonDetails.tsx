import { useQuery } from "@tanstack/react-query";
import { publicAsset } from "@/lib/research";

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
export function ProductionCarbonDetails({ a, b }: { a: string; b: string }) {
  const query = useQuery({
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
  const pair = query.data?.borders[[a, b].sort().join(">")];
  return (
    <details className="mt-3 text-xs">
      <summary className="cursor-pointer py-2 font-medium">
        Production carbon · price-separation hours
      </summary>
      {query.isPending ? (
        <p>Loading published estimates…</p>
      ) : !pair ? (
        <p>Generation coverage unavailable.</p>
      ) : (
        <div className="space-y-2">
          {[a, b].map((zone) => {
            const item = pair.zones[zone];
            if (!item) return <p key={zone}>{zone}: unavailable</p>;
            const full = item.full_lifecycle_gco2e_kwh;
            const subset = item.mapped_subset_gco2e_kwh;
            return (
              <div key={zone} className="rounded-md bg-muted p-2">
                <p className="font-medium">
                  {zone}:{" "}
                  {full !== null
                    ? `${full.toFixed(1)} g CO₂e/kWh · reported generation`
                    : subset !== null
                      ? `${subset.toFixed(1)} g CO₂e/kWh · mapped subset only`
                      : "Unavailable"}
                </p>
                <p>
                  {item.complete_generation_hours.toLocaleString()} /{" "}
                  {item.expected_hours.toLocaleString()} selected hours have complete reported
                  generation.
                  {item.mapped_generation_share !== null
                    ? ` Factors cover ${(item.mapped_generation_share * 100).toFixed(1)}% of that generation.`
                    : ""}
                </p>
                <p className="text-muted-foreground">{item.geographic_scope}</p>
              </div>
            );
          })}
          <p className="text-muted-foreground">
            Experimental estimates using generic IPCC pilot factors. Energy-weighted production
            lifecycle estimates for observed hourly price spreads &gt; €5/MWh. Partial subsets are
            not full-zone intensity. This is not consumption intensity or avoided emissions; price
            separation does not prove physical congestion.
          </p>
        </div>
      )}
      <a className="mt-2 inline-block underline" href={publicAsset("docs/production-carbon-2025/")}>
        Methods and coverage
      </a>
    </details>
  );
}
