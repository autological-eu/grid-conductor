import { publicAsset } from "@/lib/research";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "./ui/dialog";
import { Button } from "./ui/button";

type Prices = (number | null)[];
async function prices(zone: string): Promise<Prices> {
  const manifestResponse = await fetch(publicAsset("research/zone-prices-2025/manifest.json"));
  if (!manifestResponse.ok) throw new Error("Price coverage manifest unavailable");
  const manifest = (await manifestResponse.json()) as Record<
    string,
    { status: string; error?: string }
  >;
  if (manifest[zone]?.status !== "published")
    throw new Error(
      `Hourly prices for ${zone} are not yet published. Direct ENTSO-E collection is required.`,
    );
  const response = await fetch(publicAsset(`research/zone-prices-2025/${zone}.json`));
  if (!response.ok) throw new Error(`No verified published hourly prices for ${zone}.`);
  const data: unknown = await response.json();
  if (
    !Array.isArray(data) ||
    data.length !== 8760 ||
    data.some((v) => v !== null && (typeof v !== "number" || !Number.isFinite(v)))
  )
    throw new Error(`Invalid published prices for ${zone}`);
  return data as Prices;
}

export function PriceSpreadDetails({ a, b }: { a: string; b: string }) {
  const [open, setOpen] = useState(false);
  const [month, setMonth] = useState("year");
  const query = useQuery({
    queryKey: ["published-zone-prices", a, b, 2025],
    enabled: open,
    staleTime: Infinity,
    retry: false,
    queryFn: async () => Promise.all([prices(a), prices(b)]),
  });
  const begin =
    month === "year" ? 0 : (Date.UTC(2025, Number(month), 1) - Date.UTC(2025, 0, 1)) / 3600000;
  const end =
    month === "year"
      ? 8760
      : (Date.UTC(2025, Number(month) + 1, 1) - Date.UTC(2025, 0, 1)) / 3600000;
  const left = query.data?.[0].slice(begin, end) ?? [],
    right = query.data?.[1].slice(begin, end) ?? [];
  const values = [...left, ...right].filter((v): v is number => v != null);
  const low = Math.min(0, ...values),
    high = Math.max(1, ...values);
  const y = (v: number) => 230 - ((v - low) / (high - low)) * 210;
  const x = (i: number) => 55 + (i / Math.max(1, end - begin - 1)) * 900;
  const line = (data: Prices) => {
    let pen = false;
    return data
      .map((v, i) => {
        if (v == null) {
          pen = false;
          return "";
        }
        const command = `${pen ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`;
        pen = true;
        return command;
      })
      .join(" ");
  };
  const shade = left
    .map((v, i) => {
      const w = right[i],
        v2 = left[i + 1],
        w2 = right[i + 1];
      return v == null || w == null || v2 == null || w2 == null
        ? ""
        : `M${x(i)},${y(v)}L${x(i + 1)},${y(v2)}L${x(i + 1)},${y(w2)}L${x(i)},${y(w)}Z`;
    })
    .join(" ");
  const known = left.filter((v, i) => v != null && right[i] != null).length;
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
            {a} and {b}: hourly day-ahead prices, 2025
          </DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          Two observed price series in €/MWh. The shaded area shows their difference, not congestion
          rent or recoverable welfare.
        </p>
        <label className="text-sm">
          Period{" "}
          <select
            aria-label="Price chart period"
            value={month}
            onChange={(e) => setMonth(e.target.value)}
            className="rounded border bg-background p-1"
          >
            <option value="year">Full year</option>
            {Array.from({ length: 12 }, (_, i) => (
              <option key={i} value={i}>
                {new Date(Date.UTC(2025, i, 1)).toLocaleString("en", {
                  month: "long",
                  timeZone: "UTC",
                })}
              </option>
            ))}
          </select>
        </label>
        {query.isPending && <p>Loading published historical prices…</p>}
        {query.error && <p role="alert">{query.error.message}</p>}
        {query.data && (
          <>
            <div className="flex gap-4 text-sm">
              <span style={{ color: "#2563eb" }}>━ {a}</span>
              <span style={{ color: "#d97706" }}>━ {b}</span>
              <span>Shading: price difference</span>
            </div>
            <svg
              viewBox="0 0 1000 270"
              role="img"
              aria-label={`Hourly prices for ${a} and ${b}, shaded price difference`}
              className="w-full"
            >
              <path d={shade} fill="#64748b" opacity=".22" />
              <line x1="55" x2="955" y1={y(0)} y2={y(0)} stroke="currentColor" opacity=".3" />
              <path d={line(left)} fill="none" stroke="#2563eb" strokeWidth=".9" />
              <path d={line(right)} fill="none" stroke="#d97706" strokeWidth=".9" />
              <text x="0" y="20" fontSize="14">
                {high.toFixed(0)}
              </text>
              <text x="0" y="230" fontSize="14">
                {low.toFixed(0)}
              </text>
              <text x="55" y="260" fontSize="14">
                {new Date(Date.UTC(2025, 0, 1) + begin * 3600000).toISOString().slice(0, 10)}
              </text>
              <text x="800" y="260" fontSize="14">
                {new Date(Date.UTC(2025, 0, 1) + (end - 1) * 3600000).toISOString().slice(0, 10)}{" "}
                UTC
              </text>
            </svg>
            <p className="text-sm">
              Coverage: {known.toLocaleString()} / {(end - begin).toLocaleString()} hours in this
              view. Missing hours break both shading and lines.
            </p>
          </>
        )}
        <p className="text-xs text-muted-foreground">
          Published hourly means from ENTSO-E A44 or openly licensed Energy-Charts / SMARD (CC BY
          4.0). No live third-party request. Quarter-hour prices are averaged only for complete
          hours. This price-only trace may differ from the archived screening’s price-and-flow
          coverage mask.{" "}
          <a
            href={publicAsset("research/zone-prices-2025/manifest.json")}
            target="_blank"
            rel="noreferrer"
            className="underline"
          >
            Source and coverage manifest
          </a>
        </p>
      </DialogContent>
    </Dialog>
  );
}
