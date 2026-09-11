import { useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Scatter,
  ComposedChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PageHeader } from "@/components/AppShell";
import { DataBadge } from "@/components/DataBadge";
import { ChartSkeleton, ErrorCard } from "@/components/States";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { useZone } from "@/hooks/useZone";
import { useForecast } from "@/hooks/useWaterSignals";
import { zoneLabel } from "@/lib/zones";
import { bestWindow, tripleScore } from "@/lib/waterEngine";
import { fmtL, localHour, localTime, utcLabel } from "@/lib/format";

export const Route = createFileRoute("/forecast")({
  head: () => ({
    meta: [
      { title: "Forecast & Scheduler — WaterTrace" },
      {
        name: "description",
        content:
          "72-hour water intensity forecast, low-water windows and a water–carbon–price optimiser for flexible loads.",
      },
      { property: "og:title", content: "Forecast & Scheduler — WaterTrace" },
      {
        property: "og:description",
        content: "Find the lowest-water hours to run flexible workloads in any grid zone.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: ForecastPage,
});

const LEVEL_FILL: Record<string, string> = {
  low: "var(--teal)",
  medium: "var(--amber)",
  high: "var(--coral)",
};

function ForecastPage() {
  const { zone } = useZone();
  const [jobHours, setJobHours] = useState(4);
  const [wWater, setWWater] = useState(1 / 3);
  const [wCarbon, setWCarbon] = useState(1 / 3);
  const [wPrice, setWPrice] = useState(1 / 3);

  const q = useForecast(zone, { jobHours });
  const points = q.data?.points ?? [];

  const water = points.map((p) => p.w1_consumption_L_per_kWh);
  const carbon = points.map((p) => p.carbon_g_per_kWh ?? 0);
  const hasPrice = points.some((p) => p.price_eur_per_MWh != null);
  const price = hasPrice ? points.map((p) => p.price_eur_per_MWh ?? 0) : null;

  const win = useMemo(() => (water.length ? bestWindow(water, jobHours) : null), [water, jobHours]);
  const nowValue = water[0];
  const vsNow = win && nowValue ? ((win.mean - nowValue) / nowValue) * 100 : null;

  const triple = useMemo(
    () =>
      water.length
        ? tripleScore(water, carbon, price, { water: wWater, carbon: wCarbon, price: wPrice })
        : null,
    [water, carbon, price, wWater, wCarbon, wPrice],
  );

  const scoreWin = useMemo(
    () => (triple ? bestWindow(triple.score, jobHours) : null),
    [triple, jobHours],
  );

  const scoreData = points.map((p, i) => ({
    t: p.datetime,
    score: triple?.score[i] ?? 0,
    tradeOff: triple?.tradeOff[i] ? (triple?.score[i] ?? 0) : null,
    water: water[i],
    carbon: carbon[i],
  }));

  const bands = points.map((p, i) => ({ i, level: p.w4_level ?? "medium", t: p.datetime }));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Forecast & scheduler"
        description={`72 h water forecast and low-water windows for ${zoneLabel(zone)} (${zone}).`}
      />

      {q.isLoading ? (
        <ChartSkeleton height={320} />
      ) : q.error ? (
        <ErrorCard error={q.error} onRetry={() => q.refetch()} />
      ) : (
        <>
          <Card>
            <CardContent className="space-y-3 p-5">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-sm font-medium text-foreground">W4 — 72 h water intensity forecast</h2>
                <DataBadge kind="live" />
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={points.map((p) => ({ t: p.datetime, w1: p.w1_consumption_L_per_kWh }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  {bands.map((b) => (
                    <ReferenceArea
                      key={b.i}
                      x1={b.t}
                      x2={bands[b.i + 1]?.t ?? b.t}
                      fill={LEVEL_FILL[b.level]}
                      fillOpacity={0.1}
                      strokeOpacity={0}
                    />
                  ))}
                  <XAxis dataKey="t" tickFormatter={localHour} fontSize={11} stroke="var(--muted-foreground)" minTickGap={40} />
                  <YAxis fontSize={11} stroke="var(--muted-foreground)" width={56} />
                  <Tooltip
                    labelFormatter={(v: string) => `${localTime(v)} · ${utcLabel(v)}`}
                    formatter={(v: number) => [`${fmtL(v)} L/kWh`, "W1"]}
                    contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8 }}
                  />
                  <Area type="monotone" dataKey="w1" stroke="var(--water)" fill="var(--water)" fillOpacity={0.2} />
                </AreaChart>
              </ResponsiveContainer>
              <p className="text-xs text-muted-foreground">
                Background bands: teal = low-water hours, amber = medium, coral = high (tertiles of the horizon).
              </p>
            </CardContent>
          </Card>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardContent className="space-y-4 p-5">
                <div className="flex items-center justify-between gap-3">
                  <h2 className="text-sm font-medium text-foreground">Best low-water window</h2>
                  <DataBadge kind="live" />
                </div>
                <div className="max-w-[180px] space-y-1">
                  <Label htmlFor="job">Job length (hours)</Label>
                  <Input
                    id="job"
                    type="number"
                    min={1}
                    max={24}
                    value={jobHours}
                    onChange={(e) =>
                      setJobHours(Math.max(1, Math.min(24, Number(e.target.value) || 1)))
                    }
                  />
                </div>
                {win && points[win.start] ? (
                  <div className="space-y-1">
                    <p className="text-3xl font-semibold tabular-nums text-foreground">
                      {fmtL(win.mean)} <span className="text-sm font-normal text-muted-foreground">L/kWh mean</span>
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {localTime(points[win.start]!.datetime)} →{" "}
                      {localTime(points[Math.min(points.length - 1, win.start + jobHours)]!.datetime)}
                    </p>
                    {vsNow != null ? (
                      <p className="text-sm text-teal">
                        vs now: {vsNow <= 0 ? "−" : "+"}
                        {Math.abs(vsNow).toFixed(0)}%
                      </p>
                    ) : null}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No window available.</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardContent className="space-y-4 p-5">
                <div className="flex items-center justify-between gap-3">
                  <h2 className="text-sm font-medium text-foreground">W5 — weights</h2>
                  <DataBadge kind="live" />
                </div>
                <WeightSlider label="Water" value={wWater} onChange={setWWater} />
                <WeightSlider label="Carbon" value={wCarbon} onChange={setWCarbon} />
                {hasPrice ? (
                  <WeightSlider label="Price" value={wPrice} onChange={setWPrice} />
                ) : (
                  <p className="text-sm text-muted-foreground">Price not available for this zone.</p>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardContent className="space-y-3 p-5">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-sm font-medium text-foreground">
                  W5 — combined water · carbon{hasPrice ? " · price" : ""} score (0 = best)
                </h2>
                <DataBadge kind="live" />
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <ComposedChart data={scoreData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="t" tickFormatter={localHour} fontSize={11} stroke="var(--muted-foreground)" minTickGap={40} />
                  <YAxis fontSize={11} stroke="var(--muted-foreground)" width={56} />
                  <Tooltip
                    labelFormatter={(v: string) => `${localTime(v)} · ${utcLabel(v)}`}
                    contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8 }}
                  />
                  <Line type="monotone" dataKey="water" stroke="var(--water)" dot={false} strokeOpacity={0.25} name="water" />
                  <Line type="monotone" dataKey="carbon" stroke="var(--muted-foreground)" dot={false} strokeOpacity={0.2} name="carbon" yAxisId={0} />
                  <Line type="monotone" dataKey="score" stroke="var(--teal)" strokeWidth={2} dot={false} name="combined score" />
                  <Scatter dataKey="tradeOff" fill="var(--concept)" name="low-carbon but high-water hour" />
                </ComposedChart>
              </ResponsiveContainer>
              {scoreWin && points[scoreWin.start] ? (
                <p className="text-sm text-foreground">
                  Best combined {jobHours} h window: {localTime(points[scoreWin.start]!.datetime)} (score{" "}
                  {scoreWin.mean.toFixed(2)}).
                </p>
              ) : null}
              <p className="text-xs text-muted-foreground">
                Carbon-only scheduling can push load into high-water hours. W5 makes the trade-off visible.
              </p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function WeightSlider({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <Label>{label}</Label>
        <span className="tabular-nums text-muted-foreground">{value.toFixed(2)}</span>
      </div>
      <Slider value={[value]} min={0} max={1} step={0.05} onValueChange={(v) => onChange(v[0] ?? 0)} />
    </div>
  );
}
