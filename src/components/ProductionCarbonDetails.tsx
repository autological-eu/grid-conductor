import { publicAsset } from "@/lib/research";
import { useProductionCarbon } from "@/lib/production-carbon";

export function ProductionCarbonDetails({ a, b }: { a: string; b: string }) {
  const query = useProductionCarbon();
  const pair = query.data?.borders[[a, b].sort().join(">")];
  return (
    <details open className="mt-3 text-xs">
      <summary className="cursor-pointer py-2 font-medium">
        Production carbon · price-separation hours
      </summary>
      {query.isPending ? (
        <p>Loading published estimates…</p>
      ) : query.isError ? (
        <p>Carbon data unavailable. Try reloading the page.</p>
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
      <a
        className="mt-2 inline-block underline"
        href={publicAsset("docs/#3-evaluating-opportunities")}
      >
        Methods and coverage
      </a>
    </details>
  );
}

export function ProductionCarbonHighlight({ a, b }: { a: string; b: string }) {
  const query = useProductionCarbon();
  const pair = query.data?.borders[[a, b].sort().join(">")];
  return (
    <div className="rounded-md bg-muted px-2 py-1.5">
      <dt className="text-[11px] text-muted-foreground">Carbon intensity · g CO₂e/kWh</dt>
      <dd className="text-xs font-semibold">
        {[a, b].map((zone) => {
          const item = pair?.zones[zone];
          const intensity = item?.full_lifecycle_gco2e_kwh ?? item?.mapped_subset_gco2e_kwh;
          return (
            <div key={zone}>
              {zone}:{" "}
              {intensity == null
                ? query.isPending
                  ? "Loading…"
                  : "Unavailable"
                : intensity.toFixed(1)}
              {intensity != null && item?.full_lifecycle_gco2e_kwh == null ? " · partial" : ""}
            </div>
          );
        })}
      </dd>
    </div>
  );
}
