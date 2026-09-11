import { lazy, Suspense, useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ErrorBar,
  LabelList,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { PageHeader } from "@/components/AppShell";
import { DataBadge } from "@/components/DataBadge";
import { ChartSkeleton, ErrorCard } from "@/components/States";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useBenchmark } from "@/hooks/useWaterSignals";
import { PILOT_ZONES, ZONE_KEYS, zoneLabel } from "@/lib/zones";
import { ZONE_PROFILES } from "@/lib/seedData";
import { fmtL, fmtNum } from "@/lib/format";

const ZoneMap = lazy(() => import("@/components/ZoneMap"));

export const Route = createFileRoute("/benchmark")({
  head: () => ({
    meta: [
      { title: "Benchmark & Siting — WaterTrace" },
      {
        name: "description",
        content:
          "Compare 30-day average water and carbon intensity across 15 pilot grid zones to inform siting and cloud-region choices.",
      },
      { property: "og:title", content: "Benchmark & Siting — WaterTrace" },
      {
        property: "og:description",
        content: "Zone ranking, water-vs-carbon quadrants and a map of pilot grid zones.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: BenchmarkPage,
});

type Filter = "all" | "EU" | "US";

function BenchmarkPage() {
  const [filter, setFilter] = useState<Filter>("all");
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const q = useBenchmark(ZONE_KEYS, 30);

  const rows = (q.data?.rows ?? [])
    .filter((r) => !r.error && r.avg_L_per_kWh != null)
    .filter((r) =>
      filter === "all" ? true : PILOT_ZONES.find((z) => z.key === r.zone)?.group === filter,
    )
    .map((r) => ({
      zone: r.zone,
      name: zoneLabel(r.zone),
      avg: r.avg_L_per_kWh!,
      min: r.min ?? r.avg_L_per_kWh!,
      max: r.max ?? r.avg_L_per_kWh!,
      carbon: r.carbon_avg_g_per_kWh ?? 0,
      err: [r.avg_L_per_kWh! - (r.min ?? r.avg_L_per_kWh!), (r.max ?? r.avg_L_per_kWh!) - r.avg_L_per_kWh!],
    }))
    .sort((a, b) => a.avg - b.avg);

  const maxAvg = Math.max(1, ...rows.map((r) => r.avg));
  const color = (v: number) => (v / maxAvg < 0.34 ? "var(--teal)" : v / maxAvg < 0.67 ? "var(--amber)" : "var(--coral)");

  const zoneMeta = ZONE_PROFILES.zones as Array<{ key: string; name: string; lat: number; lon: number }>;
  const mapPoints = rows
    .map((r) => {
      const m = zoneMeta.find((z) => z.key === r.zone);
      return m ? { zone: r.zone, name: r.name, lat: m.lat, lon: m.lon, avg: r.avg } : null;
    })
    .filter(Boolean) as Array<{ zone: string; name: string; lat: number; lon: number; avg: number }>;

  const midCarbon = rows.length ? (Math.min(...rows.map((r) => r.carbon)) + Math.max(...rows.map((r) => r.carbon))) / 2 : 0;
  const midWater = rows.length ? (Math.min(...rows.map((r) => r.avg)) + Math.max(...rows.map((r) => r.avg))) / 2 : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Benchmark & siting"
        description="A2 — 30-day average water and carbon intensity across the 15 pilot zones."
      />

      <Tabs value={filter} onValueChange={(v) => setFilter(v as Filter)}>
        <TabsList>
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="EU">EU</TabsTrigger>
          <TabsTrigger value="US">US</TabsTrigger>
        </TabsList>
      </Tabs>

      {q.isLoading ? (
        <ChartSkeleton height={420} />
      ) : q.error ? (
        <ErrorCard error={q.error} onRetry={() => q.refetch()} />
      ) : (
        <>
          <Card>
            <CardContent className="space-y-3 p-5">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-sm font-medium">Ranking — average water intensity (L/kWh)</h2>
                <DataBadge kind="live" />
              </div>
              <ResponsiveContainer width="100%" height={Math.max(280, rows.length * 32)}>
                <BarChart data={rows} layout="vertical" margin={{ left: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis type="number" fontSize={11} stroke="var(--muted-foreground)" />
                  <YAxis type="category" dataKey="zone" width={110} fontSize={11} stroke="var(--muted-foreground)" />
                  <Tooltip
                    contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8 }}
                    formatter={(v: number, _n, item: { payload?: { min: number; max: number; name: string } }) => [
                      `${fmtL(v)} L/kWh (min ${fmtL(item?.payload?.min)} – max ${fmtL(item?.payload?.max)})`,
                      item?.payload?.name ?? "zone",
                    ]}
                  />
                  <Bar dataKey="avg" radius={[0, 6, 6, 0]}>
                    {rows.map((r) => (
                      <Cell key={r.zone} fill={color(r.avg)} />
                    ))}
                    <ErrorBar dataKey="err" width={4} strokeWidth={1} stroke="var(--muted-foreground)" direction="x" />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="space-y-3 p-5">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-sm font-medium">Water vs carbon</h2>
                <DataBadge kind="live" />
              </div>
              <ResponsiveContainer width="100%" height={380}>
                <ScatterChart margin={{ top: 20, right: 30, bottom: 20, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis
                    type="number"
                    dataKey="carbon"
                    name="carbon"
                    unit=" g"
                    fontSize={11}
                    stroke="var(--muted-foreground)"
                  />
                  <YAxis type="number" dataKey="avg" name="water" unit=" L" fontSize={11} stroke="var(--muted-foreground)" />
                  <ZAxis range={[80, 80]} />
                  <Tooltip
                    contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8 }}
                    formatter={(v: number, n: string) => [
                      n === "water" ? `${fmtL(v)} L/kWh` : `${fmtNum(v, 0)} gCO2eq/kWh`,
                      n,
                    ]}
                  />
                  <Scatter data={rows} fill="var(--water)">
                    <LabelList dataKey="zone" position="top" fontSize={10} fill="var(--muted-foreground)" />
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
              <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                <span>↖ low carbon · high water</span>
                <span className="text-right">↗ high carbon · high water</span>
                <span>↙ low carbon · low water</span>
                <span className="text-right">↘ high carbon · low water</span>
              </div>
              <p className="text-xs text-muted-foreground">
                Quadrant midpoints: {fmtNum(midCarbon, 0)} gCO2eq/kWh and {fmtL(midWater)} L/kWh.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="space-y-3 p-5">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-sm font-medium">Map — circle size ∝ average water intensity</h2>
                <DataBadge kind="live" />
              </div>
              {mounted ? (
                <Suspense fallback={<ChartSkeleton height={420} />}>
                  <ZoneMap points={mapPoints} />
                </Suspense>
              ) : (
                <ChartSkeleton height={420} />
              )}
              <p className="text-xs text-muted-foreground">
                A2 uses the fast method (flow-traced daily mix × local factors).
              </p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
