import { useQuery } from "@tanstack/react-query";
import { publicAsset } from "@/lib/research";
import { meanCarbonSpread, type CarbonHour } from "@/lib/carbon-spread";

export function CarbonSpreadStat({ a, b }: { a: string; b: string }) {
  const query = useQuery({
    queryKey: ["carbon-spread-2025", ...[a, b].sort()],
    queryFn: async () => {
      const paths = [
        `research/zone-prices-2025/${a}.json`,
        `research/zone-prices-2025/${b}.json`,
        `research/production-carbon-2025/hourly/${a}.json`,
        `research/production-carbon-2025/hourly/${b}.json`,
      ];
      const data = await Promise.all(
        paths.map(async (path) => {
          const response = await fetch(publicAsset(path));
          if (!response.ok) throw new Error("Carbon spread data unavailable");
          const rows: unknown = await response.json();
          if (!Array.isArray(rows) || rows.length !== 8760)
            throw new Error("Invalid hourly chronology");
          return rows;
        }),
      );
      return meanCarbonSpread(
        data[0] as (number | null)[],
        data[1] as (number | null)[],
        data[2] as CarbonHour[],
        data[3] as CarbonHour[],
      );
    },
    staleTime: Infinity,
  });
  const estimate = query.data;
  return (
    <div className="rounded-md bg-muted px-2 py-1.5">
      <dt className="text-[11px] text-muted-foreground">Mean absolute carbon spread</dt>
      <dd className="text-xs font-semibold">
        {query.isPending
          ? "Loading…"
          : estimate?.value == null
            ? "Unavailable"
            : `${estimate.value.toFixed(1)} g CO₂e/kWh`}
      </dd>
      {estimate?.value != null && (
        <dd className="text-[11px] text-muted-foreground">
          {estimate.hours.toLocaleString()} / {estimate.selectedHours.toLocaleString()} price-gap
          hours
        </dd>
      )}
    </div>
  );
}
