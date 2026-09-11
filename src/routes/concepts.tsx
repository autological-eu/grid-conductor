import { useState, type ReactNode } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PageHeader } from "@/components/AppShell";
import { DataBadge } from "@/components/DataBadge";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useZone } from "@/hooks/useZone";
import { useLatest } from "@/hooks/useWaterSignals";
import { PILOT_ZONES, zoneLabel } from "@/lib/zones";
import { fmtL, fmtNum, fmtPct } from "@/lib/format";
import {
  MOCK_HYDRO_REFINED,
  X4_DEFAULT_HYDRO_L_PER_KWH,
  x1StressWeighted,
  x2ConfidenceUplift,
  x2Plants,
  x3Weather,
  x5Derating,
  x6Telemetry,
} from "@/lib/conceptMocks";

export const Route = createFileRoute("/concepts")({
  head: () => ({
    meta: [
      { title: "Partner Concepts — WaterTrace" },
      {
        name: "description",
        content:
          "Six concept water signals (X1–X6) that become possible with water-stress, satellite, Copernicus and site telemetry partners.",
      },
      { property: "og:title", content: "Partner Concepts — WaterTrace" },
      {
        property: "og:description",
        content: "Concept signals shown with synthetic mock data, and the partnerships each one needs.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: ConceptsPage,
});

const chartTooltip = {
  background: "var(--card)",
  border: "1px solid var(--border)",
  borderRadius: 8,
};

function ConceptCard({
  id,
  name,
  value,
  needs,
  unlocks,
  children,
}: {
  id: string;
  name: string;
  value: string;
  needs: string;
  unlocks: string;
  children: ReactNode;
}) {
  return (
    <Card className="h-full border-concept/30">
      <CardContent className="flex h-full flex-col gap-3 p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-concept/10 px-1.5 py-0.5 font-mono text-[11px] font-semibold text-concept">
              {id}
            </span>
            <span className="text-sm font-medium">{name}</span>
          </div>
          <DataBadge kind="mock" />
        </div>
        <p className="text-sm text-foreground">{value}</p>
        <p className="text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Needs:</span> {needs}
        </p>
        <p className="text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Unlocks:</span> {unlocks}
        </p>
        <div className="mt-auto pt-2">
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="secondary" size="sm">
                Open concept view
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-xl">
              <SheetHeader>
                <SheetTitle className="flex items-center gap-2">
                  <span className="font-mono text-sm text-concept">{id}</span> {name}
                </SheetTitle>
                <SheetDescription>
                  Synthetic mock data only — never mixed with live Electricity Maps values.
                </SheetDescription>
              </SheetHeader>
              <div className="space-y-4 px-4 pb-8">
                <DataBadge kind="mock" />
                {children}
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </CardContent>
    </Card>
  );
}

function ConceptsPage() {
  const { zone } = useZone();
  const latest = useLatest(zone);
  const liveW1 =
    latest.data?.points?.[latest.data.points.length - 1]?.w1_consumption_L_per_kWh ?? 1.0;
  const [heatwave, setHeatwave] = useState(false);

  const x1 = PILOT_ZONES.map((z) => x1StressWeighted(z.key, liveW1));
  const rankBefore = [...x1].sort((a, b) => a.stressWeighted_Leq_per_kWh - b.stressWeighted_Leq_per_kWh);
  const plants = x2Plants(zone);
  const uplift = x2ConfidenceUplift(zone);
  const weather = x3Weather(zone, 72, heatwave);
  const hydro = PILOT_ZONES.map((z) => ({
    zone: z.key,
    default: X4_DEFAULT_HYDRO_L_PER_KWH,
    refined: MOCK_HYDRO_REFINED[z.key] ?? X4_DEFAULT_HYDRO_L_PER_KWH,
  }));
  const derating = x5Derating(zone, 14);
  const telemetry = x6Telemetry(72);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Partner concepts"
        description="X1–X6 show what becomes possible with additional data partners. Every figure here is synthetic mock data."
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <ConceptCard
          id="X1"
          name="Water-Stress-Weighted Intensity"
          value="Weight each litre by the water stress of the basin it came from."
          needs="WRI Aqueduct 4.0 / AWARE 2.0 + power-plant locations."
          unlocks="ESRS E3 'consumption in areas at water risk', better siting."
        >
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Zone</TableHead>
                <TableHead>Stress</TableHead>
                <TableHead>×</TableHead>
                <TableHead>L-eq/kWh</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {x1.map((r) => (
                <TableRow key={r.zone}>
                  <TableCell className="font-mono text-xs">{r.zone}</TableCell>
                  <TableCell className="text-xs">{r.category}</TableCell>
                  <TableCell className="text-xs tabular-nums">{r.multiplier}</TableCell>
                  <TableCell className="text-xs tabular-nums">{r.stressWeighted_Leq_per_kWh}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div>
            <p className="mb-2 text-sm font-medium">Rank after stress weighting (best first)</p>
            <ol className="space-y-1 text-xs text-muted-foreground">
              {rankBefore.map((r, i) => (
                <li key={r.zone}>
                  {i + 1}. {zoneLabel(r.zone)} — {r.stressWeighted_Leq_per_kWh} L-eq/kWh
                </li>
              ))}
            </ol>
          </div>
        </ConceptCard>

        <ConceptCard
          id="X2"
          name="Satellite Cooling Intelligence"
          value="Classify each plant's cooling technology from imagery instead of guessing."
          needs="Satellite imagery + ML (e.g. AiDASH; Sentinel-2 open tier; EIA-860 labels)."
          unlocks="Audit-grade cooling factors and global coverage."
        >
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Unit</TableHead>
                <TableHead>Fuel</TableHead>
                <TableHead>Registry</TableHead>
                <TableHead>Satellite</TableHead>
                <TableHead>Conf.</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {plants.map((p) => (
                <TableRow key={p.id}>
                  <TableCell className="font-mono text-xs">{p.id}</TableCell>
                  <TableCell className="text-xs">{p.fuel}</TableCell>
                  <TableCell className="text-xs">{p.registryCooling}</TableCell>
                  <TableCell className="text-xs">{p.satelliteCooling}</TableCell>
                  <TableCell className="text-xs tabular-nums">{p.confidence}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div className="space-y-2">
            <p className="text-sm">Profile confidence</p>
            <Progress value={uplift.profileConfidenceBefore * 100} />
            <p className="text-xs text-muted-foreground">
              before {fmtPct(uplift.profileConfidenceBefore, 0)}%
            </p>
            <Progress value={uplift.profileConfidenceAfter * 100} />
            <p className="text-xs text-muted-foreground">
              after {fmtPct(uplift.profileConfidenceAfter, 0)}% · W1 correction{" "}
              {uplift.w1Correction >= 0 ? "+" : ""}
              {fmtPct(uplift.w1Correction, 0)}%
            </p>
          </div>
        </ConceptCard>

        <ConceptCard
          id="X3"
          name="Heat-Adjusted Evaporation"
          value="Scale tower evaporation with wet-bulb temperature instead of an annual average."
          needs="ECMWF/ERA5 reanalysis and forecasts (Copernicus)."
          unlocks="Accurate summer peaks and heatwave water forecasts."
        >
          <div className="flex items-center gap-2">
            <Switch id="hw" checked={heatwave} onCheckedChange={setHeatwave} />
            <Label htmlFor="hw">Heatwave scenario</Label>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={weather}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="hour" fontSize={11} stroke="var(--muted-foreground)" />
              <YAxis fontSize={11} stroke="var(--muted-foreground)" />
              <Tooltip contentStyle={chartTooltip} />
              <Line dataKey="wetBulbC" stroke="var(--concept)" dot={false} name="wet-bulb °C" />
              <Line dataKey="towerEvaporationUplift" stroke="var(--amber)" dot={false} name="evaporation uplift" />
            </LineChart>
          </ResponsiveContainer>
        </ConceptCard>

        <ConceptCard
          id="X4"
          name="Reservoir Evaporation"
          value="Replace one global hydro number with reservoir-specific evaporation."
          needs="Satellite water-surface extent + ERA5 evaporation."
          unlocks="Fair hydro treatment: Nordic reservoirs vs arid ones."
        >
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={hydro}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="zone" fontSize={9} angle={-40} textAnchor="end" height={70} stroke="var(--muted-foreground)" />
              <YAxis fontSize={11} stroke="var(--muted-foreground)" />
              <Tooltip contentStyle={chartTooltip} formatter={(v: number) => [`${fmtL(v)} L/kWh`, "hydro"]} />
              <Bar dataKey="default" fill="var(--muted-foreground)" name="global default" />
              <Bar dataKey="refined" fill="var(--concept)" name="refined (mock)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ConceptCard>

        <ConceptCard
          id="X5"
          name="Cooling-Water Derating & Price-Spike Risk"
          value="Warn when rivers get too warm for thermal plants to run at full output."
          needs="River temperature and flow (Copernicus GloFAS, national hydrology)."
          unlocks="Trading and hedging alerts ahead of summer derating."
        >
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={derating}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="day" fontSize={11} stroke="var(--muted-foreground)" />
              <YAxis fontSize={11} stroke="var(--muted-foreground)" />
              <Tooltip contentStyle={chartTooltip} />
              <ReferenceLine y={27} stroke="var(--coral)" strokeDasharray="4 3" label="limit" />
              <Line dataKey="riverTempC" stroke="var(--concept)" dot={false} name="river °C" />
            </LineChart>
          </ResponsiveContainer>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={derating}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="day" fontSize={11} stroke="var(--muted-foreground)" />
              <YAxis fontSize={11} stroke="var(--muted-foreground)" />
              <Tooltip
                contentStyle={chartTooltip}
                formatter={(v: number, n: string) => [n === "capacityAtRiskMW" ? `${fmtNum(v, 0)} MW` : v, n]}
              />
              <Bar dataKey="capacityAtRiskMW" fill="var(--coral)" name="capacity at risk" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <p className="text-xs text-muted-foreground">
            Peak price-spike probability:{" "}
            {fmtPct(Math.max(...derating.map((d) => d.priceSpikeProbability)), 0)}%
          </p>
        </ConceptCard>

        <ConceptCard
          id="X6"
          name="Site Telemetry Fusion"
          value="Fuse measured WUE and PUE from the facility with the grid water signal."
          needs="DCIM/BMS data (e.g. EcoStruxure IT)."
          unlocks="Measured, not modelled, facility reporting."
        >
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={telemetry}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="hour" fontSize={11} stroke="var(--muted-foreground)" />
              <YAxis fontSize={11} stroke="var(--muted-foreground)" />
              <Tooltip contentStyle={chartTooltip} />
              <ReferenceLine y={1.8} stroke="var(--muted-foreground)" strokeDasharray="4 3" label="A1 WUE default" />
              <ReferenceLine y={1.3} stroke="var(--muted-foreground)" strokeDasharray="2 4" label="A1 PUE default" />
              <Line dataKey="measuredWUE" stroke="var(--concept)" dot={false} name="measured WUE" />
              <Line dataKey="measuredPUE" stroke="var(--water)" dot={false} name="measured PUE" />
            </LineChart>
          </ResponsiveContainer>
        </ConceptCard>
      </div>

      <Card>
        <CardContent className="space-y-4 p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-medium">Partnership map</h2>
            <DataBadge kind="mock" />
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="rounded-xl border border-border p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Grid core</p>
              <p className="mt-2 text-sm">Electricity Maps — mix, flows, carbon, price</p>
            </div>
            <div className="rounded-xl border border-concept/40 bg-concept/5 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-concept">WaterTrace engine</p>
              <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                <li>WRI / WULCA — water stress (X1)</li>
                <li>Satellite partner — cooling types (X2)</li>
                <li>Copernicus — weather, hydrology (X3–X5)</li>
                <li>DCIM partners — site telemetry (X6)</li>
              </ul>
            </div>
            <div className="rounded-xl border border-border p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Outputs</p>
              <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                <li>Data-centre operators</li>
                <li>ESG / sustainability software</li>
                <li>Utilities and traders</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
