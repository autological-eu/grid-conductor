import { useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Download } from "lucide-react";
import { PageHeader } from "@/components/AppShell";
import { DataBadge } from "@/components/DataBadge";
import { SignalCard } from "@/components/SignalCard";
import { ChartSkeleton, ConceptBanner, ErrorCard } from "@/components/States";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useZone } from "@/hooks/useZone";
import { useForecast, useHistory } from "@/hooks/useWaterSignals";
import { zoneLabel } from "@/lib/zones";
import { facilityFootprint } from "@/lib/waterEngine";
import { fmtL, fmtNum, fmtPct, localHour, localTime, utcLabel } from "@/lib/format";

export const Route = createFileRoute("/footprint")({
  head: () => ({
    meta: [
      { title: "Facility Water Footprint — WaterTrace" },
      {
        name: "description",
        content:
          "Turn IT load, WUE and PUE into direct and indirect water use per hour, with a CSV evidence file for ESRS E3 and GRI 303 work.",
      },
      { property: "og:title", content: "Facility Water Footprint — WaterTrace" },
      {
        property: "og:description",
        content: "Direct and indirect facility water use from hourly grid water intensity.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: FootprintPage,
});

function FootprintPage() {
  const { zone } = useZone();
  const [itKw, setItKw] = useState(5000);
  const [wue, setWue] = useState(1.8);
  const [pue, setPue] = useState(1.3);
  const [altWue, setAltWue] = useState(0.2);
  const [period, setPeriod] = useState<"history" | "forecast">("history");

  const history = useHistory(zone, { enabled: period === "history" });
  const forecast = useForecast(zone, { enabled: period === "forecast" });
  const q = period === "history" ? history : forecast;
  const points = q.data?.points ?? [];

  const itKwh = points.map(() => itKw);
  const ewif = points.map((p) => p.w1_consumption_L_per_kWh * 1000);

  const result = useMemo(
    () => (points.length ? facilityFootprint(itKwh, ewif, wue, pue) : null),
    [points.length, itKw, wue, pue],
  );
  const alt = useMemo(
    () => (points.length ? facilityFootprint(itKwh, ewif, altWue, pue) : null),
    [points.length, itKw, altWue, pue],
  );

  const hourly = points.map((p, i) => ({
    t: p.datetime,
    direct: (itKwh[i]! * wue) / 1000,
    indirect: (itKwh[i]! * pue * (ewif[i]! / 1000)) / 1000,
  }));

  const donut = result
    ? [
        { name: "Direct (on-site)", value: result.directL / 1000 },
        { name: "Indirect (grid)", value: result.indirectL / 1000 },
      ]
    : [];

  function exportCsv() {
    const header = [
      `# WaterTrace facility water footprint — evidence file (ESRS E3 / GRI 303 working paper)`,
      `# method: IT kWh x (WUE + PUE x EWIF); EWIF = W1 water consumption intensity (freshwater, flow-traced)`,
      `# factors: Macknick et al. 2012 (NREL) operational medians`,
      `# profiles: illustrative cooling profiles (calibration pending)`,
      `# zone: ${zone} (${zoneLabel(zone)}) · period: ${period === "history" ? "last 24 h" : "next 72 h"}`,
      `# generated_at: ${new Date().toISOString()}`,
      `datetime_utc,zone,it_kwh,wue,pue,ewif_L_per_kWh,direct_L,indirect_L,total_L`,
    ];
    const rows = points.map((p, i) => {
      const direct = itKwh[i]! * wue;
      const indirect = itKwh[i]! * pue * (ewif[i]! / 1000);
      return [
        new Date(p.datetime).toISOString(),
        zone,
        itKwh[i]!.toFixed(2),
        wue,
        pue,
        p.w1_consumption_L_per_kWh.toFixed(4),
        direct.toFixed(2),
        indirect.toFixed(2),
        (direct + indirect).toFixed(2),
      ].join(",");
    });
    const blob = new Blob([[...header, ...rows].join("\n")], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `watertrace-footprint-${zone}-${period}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Facility water footprint"
        description={`A1 — direct and indirect operational water for a facility in ${zoneLabel(zone)} (${zone}).`}
      />
      <ConceptBanner />

      <Card>
        <CardContent className="grid gap-4 p-5 sm:grid-cols-2 xl:grid-cols-4">
          <div className="space-y-1">
            <Label htmlFor="it">IT load (kW)</Label>
            <Input id="it" type="number" value={itKw} onChange={(e) => setItKw(Number(e.target.value) || 0)} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="wue">WUE (L/kWh IT)</Label>
            <Input id="wue" type="number" step="0.1" value={wue} onChange={(e) => setWue(Number(e.target.value) || 0)} />
            <p className="text-xs text-muted-foreground">industry average ~1.8, air-cooled ~0</p>
          </div>
          <div className="space-y-1">
            <Label htmlFor="pue">PUE</Label>
            <Input id="pue" type="number" step="0.05" value={pue} onChange={(e) => setPue(Number(e.target.value) || 0)} />
          </div>
          <div className="space-y-1">
            <Label>Period</Label>
            <Tabs value={period} onValueChange={(v) => setPeriod(v as "history" | "forecast")}>
              <TabsList className="w-full">
                <TabsTrigger value="history" className="flex-1">
                  Last 24 h
                </TabsTrigger>
                <TabsTrigger value="forecast" className="flex-1">
                  Next 72 h
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </CardContent>
      </Card>

      {q.isLoading ? (
        <ChartSkeleton height={300} />
      ) : q.error ? (
        <ErrorCard error={q.error} onRetry={() => q.refetch()} />
      ) : result ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <SignalCard
              id="A1"
              title="Total water"
              value={fmtNum(result.totalL / 1000, 1)}
              unit="m³"
              subtitle={period === "history" ? "last 24 h" : "next 72 h"}
              badge="assumption"
            />
            <SignalCard
              id="A1"
              title="Direct (on-site)"
              value={fmtNum(result.directL / 1000, 1)}
              unit="m³"
              subtitle="IT kWh × WUE"
              badge="assumption"
            />
            <SignalCard
              id="A1"
              title="Indirect (grid)"
              value={fmtNum(result.indirectL / 1000, 1)}
              unit="m³"
              subtitle="IT kWh × PUE × EWIF"
              badge="assumption"
            />
            <SignalCard
              id="A1"
              title="Indirect share"
              value={fmtPct(result.indirectShare, 0)}
              unit="%"
              subtitle="of total operational water"
              badge="assumption"
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardContent className="space-y-3 p-5">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-medium">Direct vs indirect</h2>
                  <DataBadge kind="assumption" />
                </div>
                <ResponsiveContainer width="100%" height={260}>
                  <PieChart>
                    <Pie data={donut} dataKey="value" nameKey="name" innerRadius={60} outerRadius={95}>
                      <Cell fill="var(--teal)" />
                      <Cell fill="var(--water)" />
                    </Pie>
                    <Legend />
                    <Tooltip
                      formatter={(v: number) => [`${fmtNum(v, 1)} m³`, "water"]}
                      contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8 }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="space-y-3 p-5">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-medium">Hourly water use (m³)</h2>
                  <DataBadge kind="assumption" />
                </div>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={hourly}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="t" tickFormatter={localHour} fontSize={11} stroke="var(--muted-foreground)" minTickGap={30} />
                    <YAxis fontSize={11} stroke="var(--muted-foreground)" width={50} />
                    <Tooltip
                      labelFormatter={(v: string) => `${localTime(v)} · ${utcLabel(v)}`}
                      formatter={(v: number, n: string) => [`${fmtNum(v, 2)} m³`, n]}
                      contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8 }}
                    />
                    <Bar dataKey="direct" stackId="a" fill="var(--teal)" />
                    <Bar dataKey="indirect" stackId="a" fill="var(--water)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardContent className="space-y-3 p-5">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-medium">What if WUE were lower?</h2>
                <DataBadge kind="assumption" />
              </div>
              <div className="max-w-[200px] space-y-1">
                <Label htmlFor="alt">Alternative WUE</Label>
                <Input id="alt" type="number" step="0.1" value={altWue} onChange={(e) => setAltWue(Number(e.target.value) || 0)} />
              </div>
              {alt ? (
                <p className="text-sm text-foreground">
                  Total would fall from {fmtNum(result.totalL / 1000, 1)} m³ to {fmtNum(alt.totalL / 1000, 1)} m³ — a
                  saving of {fmtNum((result.totalL - alt.totalL) / 1000, 1)} m³ (
                  {fmtPct((result.totalL - alt.totalL) / result.totalL, 0)}%).
                </p>
              ) : null}
              <p className="text-xs text-muted-foreground">
                Note: a lower WUE usually means more air cooling, which can raise PUE and therefore indirect water.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="flex flex-wrap items-center justify-between gap-3 p-5">
              <div>
                <h2 className="text-sm font-medium">Evidence file (ESRS E3 / GRI 303 working paper)</h2>
                <p className="text-xs text-muted-foreground">
                  One row per hour, with method and factor metadata in the header.
                </p>
              </div>
              <Button onClick={exportCsv} variant="secondary">
                <Download className="mr-2 h-4 w-4" /> Export CSV
              </Button>
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}
