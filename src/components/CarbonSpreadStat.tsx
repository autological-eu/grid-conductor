import { useQuery } from "@tanstack/react-query";
import { publicAsset } from "@/lib/research";
import { type meanCarbonSpread } from "@/lib/carbon-spread";

export function CarbonSpreadStat({ a, b }: { a: string; b: string }) {
  const query = useQuery({
    queryKey: ["carbon-spread-2025", ...[a, b].sort()],
    queryFn: async () => {
      const response = await fetch(publicAsset("research/carbon-spreads-2025.json"));
      if (!response.ok) throw new Error("Carbon spread data unavailable");
      const report = (await response.json()) as {
        schema_version: number;
        year: number;
        borders: Record<string, ReturnType<typeof meanCarbonSpread>>;
      };
      if (report.schema_version !== 1 || report.year !== 2025 || !report.borders)
        throw new Error("Unsupported carbon baseline");
      return report.borders[[a, b].sort().join(">")] ?? null;
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
    </div>
  );
}
