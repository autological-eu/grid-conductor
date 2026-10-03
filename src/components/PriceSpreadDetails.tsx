import { publicAsset } from "@/lib/research";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "./ui/dialog";
import { Button } from "./ui/button";

async function prices(zone: string) {
  const response = await fetch(
    `https://api.energy-charts.info/price?bzn=${encodeURIComponent(zone)}&start=2025-01-01&end=2025-12-31`,
  );
  if (!response.ok)
    throw new Error(`Price source unavailable (${response.status}). Try again later.`);
  const data = (await response.json()) as {
    unix_seconds: number[];
    price: (number | null)[];
    unit: string;
  };
  if (data.unit !== "EUR / MWh" || data.unix_seconds.length !== data.price.length)
    throw new Error("Unexpected price source format");
  const quarters = new Map<number, number>();
  data.unix_seconds.forEach((time, i) => {
    const value = data.price[i];
    const duration = (data.unix_seconds[i + 1] ?? time + 900) - time;
    if (duration !== 900 && duration !== 3600) throw new Error("Unsupported price interval");
    if (value == null || !Number.isFinite(value)) return;
    for (let t = time; t < time + duration; t += 900) quarters.set(t, value);
  });
  return quarters;
}

export function PriceSpreadDetails({ a, b }: { a: string; b: string }) {
  const [open, setOpen] = useState(false);
  const query = useQuery({
    queryKey: ["hourly-prices", a, b, 2025],
    enabled: open,
    staleTime: Infinity,
    retry: false,
    queryFn: async () => {
      if ([a, b].sort().join("|") === "FR|IT-North") {
        const response = await fetch(publicAsset("research/fr-it-screening/hourly-spreads.json"));
        if (!response.ok) throw new Error("Published hourly trace unavailable");
        const data = (await response.json()) as (number | null)[];
        return data.map((value) => (value == null ? null : a === "FR" ? value : -value));
      }
      const [left, right] = await Promise.all([prices(a), prices(b)]);
      const start = Date.UTC(2025, 0, 1) / 1000;
      return Array.from({ length: 8760 }, (_, i) => {
        const differences: number[] = [];
        for (let q = 0; q < 4; q++) {
          const t = start + i * 3600 + q * 900;
          const x = left.get(t),
            y = right.get(t);
          if (x == null || y == null) return null;
          differences.push(y - x);
        }
        return differences.reduce((sum, v) => sum + v, 0) / 4;
      });
    },
  });
  const data = query.data ?? [];
  const values = data.filter((v): v is number => v != null);
  const low = Math.min(0, ...values),
    high = Math.max(1, ...values);
  const y = (v: number) => 230 - ((v - low) / (high - low)) * 210;
  let pen = false;
  const path = data
    .map((v, i) => {
      if (v == null) {
        pen = false;
        return "";
      }
      const command = `${pen ? "L" : "M"}${((i / 8759) * 900 + 55).toFixed(1)},${y(v).toFixed(1)}`;
      pen = true;
      return command;
    })
    .join(" ");
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="mt-3 w-full">
          Hourly price difference
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>
            {b} − {a}: hourly day-ahead price difference, 2025
          </DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          Signed difference in €/MWh. Hourly means require four known quarter-hours. Gaps remain
          blank.
        </p>
        {query.isPending && <p>Loading public historical prices…</p>}
        {query.error && (
          <p role="alert">
            {query.error.message} This zone may not be supported by the public provider.
          </p>
        )}
        {query.data && (
          <>
            <svg
              viewBox="0 0 1000 270"
              role="img"
              aria-label={`Hourly price difference ${b} minus ${a}`}
              className="w-full"
            >
              <line x1="55" x2="955" y1={y(0)} y2={y(0)} stroke="currentColor" opacity=".3" />
              <path d={path} fill="none" stroke="currentColor" strokeWidth=".8" />
              <text x="0" y="20" fontSize="14">
                {high.toFixed(0)}
              </text>
              <text x="0" y="230" fontSize="14">
                {low.toFixed(0)}
              </text>
              <text x="55" y="260" fontSize="14">
                Jan
              </text>
              <text x="470" y="260" fontSize="14">
                Jul · UTC
              </text>
              <text x="925" y="260" fontSize="14">
                Dec
              </text>
            </svg>
            <p className="text-sm">
              Coverage: {values.length.toLocaleString()} / 8,760 hours. Absolute hourly-mean spread
              sum:{" "}
              {values
                .reduce((sum, v) => sum + Math.abs(v), 0)
                .toLocaleString(undefined, { maximumFractionDigits: 0 })}{" "}
              €/MW-year.
            </p>
          </>
        )}
        <p className="text-xs text-muted-foreground">
          Public Energy-Charts / SMARD price source (CC BY 4.0). Fetched on demand; requires
          internet. This price-only trace has no scheduled-flow coverage mask and can differ from
          the map’s archived screening input. No cable benefit or welfare is inferred.
        </p>
      </DialogContent>
    </Dialog>
  );
}
