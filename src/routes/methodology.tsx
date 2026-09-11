import { useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { PageHeader } from "@/components/AppShell";
import { DataBadge, ProfilesChip } from "@/components/DataBadge";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Label } from "@/components/ui/label";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useZone } from "@/hooks/useZone";
import { useLatest } from "@/hooks/useWaterSignals";
import { callWaterSignals, type SeriesResponse } from "@/lib/waterApi";
import { WATER_FACTORS, ZONE_PROFILES } from "@/lib/seedData";
import { zoneLabel } from "@/lib/zones";
import { fmtL } from "@/lib/format";

export const Route = createFileRoute("/methodology")({
  head: () => ({
    meta: [
      { title: "Methodology & API — WaterTrace" },
      {
        name: "description",
        content:
          "How WaterTrace turns the Electricity Maps mix and flows into hourly water intensity: formulas, factors, zone profiles, API shape and limitations.",
      },
      { property: "og:title", content: "Methodology & API — WaterTrace" },
      {
        property: "og:description",
        content: "Formulas, water factors, illustrative cooling profiles and the concept API shape.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: MethodologyPage,
});

const FORMULAS = [
  "f(k,z) = Σ_c share(c,k,z) × factor(k,c)",
  "W1 production I(z) = Σ G_k f(k,z) / Σ G_k",
  "W1 consumption (one-hop) = (Σ G_k f(k,z) + Σ Imp_n I_n) / (Σ G_k + Σ Imp_n)",
  "W3 = Σ Imp_n I_n / (Σ G_k f(k,z) + Σ Imp_n I_n)",
  "A1 total water = IT kWh × (WUE + PUE × EWIF)",
];

type MethodBadge = "live" | "assumption" | "mock";

interface SignalMethod {
  id: string;
  name: string;
  badge: MethodBadge;
  meaning: string;
  model: string;
  inputs: string;
}

const SIGNAL_METHODS: SignalMethod[] = [
  {
    id: "W1",
    name: "Water Consumption Intensity (EWIF)",
    badge: "live",
    meaning: "Freshwater evaporated or otherwise lost at power plants for each kWh delivered to the selected zone.",
    model: "Each Electricity Maps generation source is multiplied by its water-consumption factor and cooling-profile share. Imported electricity is valued using the exporting neighbour’s production intensity at the same hour, then combined with domestic generation using one-hop flow tracing.",
    inputs: "Electricity Maps electricity mix and cross-border flows; Macknick et al. 2012 operational water factors; illustrative zone cooling profiles.",
  },
  {
    id: "W2",
    name: "Water Withdrawal Intensity",
    badge: "live",
    meaning: "Freshwater taken from rivers, lakes or groundwater per kWh, including water that is later returned.",
    model: "Uses the same hourly generation and import tracing as W1, but applies withdrawal rather than consumption factors. Freshwater is the headline scope; total withdrawal additionally counts seawater-cooled generation.",
    inputs: "Electricity Maps electricity mix and flows; Macknick et al. 2012 withdrawal factors; illustrative cooling profiles.",
  },
  {
    id: "W3",
    name: "Imported Water Share",
    badge: "live",
    meaning: "The share of W1 embedded in imported electricity rather than domestic generation.",
    model: "For every importing neighbour, imported MW is multiplied by that neighbour’s hourly W1 production intensity. Imported water is divided by total domestic-plus-imported water, with each neighbour retained as a separate origin.",
    inputs: "Electricity Maps cross-border flows and each available neighbour’s electricity mix; W1 factors and cooling profiles.",
  },
  {
    id: "W4",
    name: "Water Forecast & Low-Water Windows",
    badge: "live",
    meaning: "A 72-hour outlook showing when electricity is expected to carry lower or higher water consumption.",
    model: "The W1 method is applied to each forecast hour. Hours are labelled low, medium or high relative to forecast-horizon tertiles. The best job window is the contiguous period with the lowest mean W1 for the chosen duration.",
    inputs: "Electricity Maps forecast electricity mix and flows; the same water factors and cooling profiles used by W1.",
  },
  {
    id: "W5",
    name: "Water–Carbon–Price Optimiser",
    badge: "live",
    meaning: "A comparable hourly score for scheduling against water, carbon and electricity-price priorities.",
    model: "Forecast W1, carbon intensity and day-ahead price are each min–max normalised over the horizon, multiplied by the selected weights and combined. Lower is better; low-carbon but high-water hours are explicitly flagged.",
    inputs: "Electricity Maps forecast mix, flows, carbon intensity and day-ahead prices; W1 water factors and cooling profiles.",
  },
  {
    id: "A1",
    name: "Facility Water Footprint",
    badge: "live",
    meaning: "Direct on-site and indirect electricity-related operational water for a data-centre workload.",
    model: "For each hour, direct water is IT energy × WUE. Indirect water is IT energy × PUE × W1. Hourly values are summed for the selected period and reported separately and together.",
    inputs: "Live W1 from Electricity Maps; user-entered IT load, WUE and PUE. Default facility values are assumptions until replaced by measured values.",
  },
  {
    id: "A2",
    name: "Zone Benchmark & Siting",
    badge: "live",
    meaning: "A like-for-like comparison of average grid water and carbon intensity across candidate zones.",
    model: "Daily flow-traced Electricity Maps generation mixes are multiplied by each consuming zone’s local factors, then averaged across 30 days. This fast method avoids per-neighbour tracing and also retains the daily min–max range.",
    inputs: "Electricity Maps past-range flow-traced mix and carbon intensity; Macknick et al. 2012 factors; illustrative zone profiles.",
  },
  {
    id: "X1",
    name: "Water-Stress-Weighted Intensity",
    badge: "mock",
    meaning: "W1 adjusted to distinguish water consumed in water-scarce basins from water consumed in lower-stress locations.",
    model: "Conceptually assigns generation to plant locations and basin stress, then multiplies consumed water by a WRI Aqueduct or AWARE characterisation factor before aggregation.",
    inputs: "Proposed: live W1, plant locations, WRI Aqueduct 4.0 or AWARE 2.0. Current display uses deterministic synthetic data only.",
  },
  {
    id: "X2",
    name: "Satellite Cooling Intelligence",
    badge: "mock",
    meaning: "Evidence of each thermal plant’s cooling technology to replace broad zone assumptions.",
    model: "Conceptually classifies cooling towers, ponds, dry coolers, and intake/outfall structures from satellite imagery, then capacity-weights those classifications into calibrated cooling profiles.",
    inputs: "Proposed: Sentinel-2 or a satellite analytics partner plus a licensed plant registry. Current plant IDs and classifications are synthetic.",
  },
  {
    id: "X3",
    name: "Heat-Adjusted Evaporation",
    badge: "mock",
    meaning: "An hourly adjustment for greater cooling-tower evaporation during hot and humid conditions.",
    model: "Conceptually links each plant to wet-bulb temperature and applies a calibrated temperature-response curve to tower-cooled consumption factors before calculating W1.",
    inputs: "Proposed: ECMWF/ERA5 weather through Copernicus, plant locations and calibrated cooling response curves. Current uplift is synthetic.",
  },
  {
    id: "X4",
    name: "Reservoir Evaporation",
    badge: "mock",
    meaning: "Location-specific water consumption attributed to hydropower reservoir evaporation.",
    model: "Conceptually estimates net reservoir evaporation from water-surface area and meteorology, allocates it to hydropower output, and replaces the broad default hydro factor with a site-specific L/kWh value.",
    inputs: "Proposed: satellite water-surface observations, ERA5 evaporation, reservoir boundaries and hydropower generation. Current refinements are synthetic.",
  },
  {
    id: "X5",
    name: "Cooling-Water Derating & Price-Spike Risk",
    badge: "mock",
    meaning: "Forward risk that warm or low river water limits thermal generation and contributes to electricity-price pressure.",
    model: "Conceptually compares forecast river temperature and flow with plant cooling constraints, estimates MW at risk, and relates the resulting supply reduction to price-spike probability.",
    inputs: "Proposed: Copernicus GloFAS, national hydrology data, plant cooling limits and Electricity Maps power/price data. Current risk series is synthetic.",
  },
  {
    id: "X6",
    name: "Site Telemetry Fusion",
    badge: "mock",
    meaning: "A measured facility footprint that replaces default WUE, PUE and load assumptions.",
    model: "Conceptually aligns hourly DCIM/BMS readings with hourly W1, applies the A1 formula to measured IT energy, WUE and PUE, and preserves the measured-versus-modelled evidence trail.",
    inputs: "Proposed: facility DCIM/BMS telemetry, such as EcoStruxure IT, combined with live W1. Current telemetry is synthetic.",
  },
];

const COOLINGS = ["tower", "once_through", "once_through_sea", "pond", "dry"] as const;

interface FactorRow {
  fuel: string;
  cooling: string;
  consumption: number;
  consumptionRange: string;
  withdrawal: number;
  withdrawalRange: string;
}

type Stat = { median: number; min: number; max: number };
const perKwh = (v: number) => v / 1000;
const range = (s: Stat) => `${fmtL(perKwh(s.min))}–${fmtL(perKwh(s.max))}`;

function flattenFactors(): FactorRow[] {
  const out: FactorRow[] = [];
  const thermal = WATER_FACTORS.thermal as Record<string, Record<string, { consumption: Stat; withdrawal: Stat }>>;
  for (const [fuel, byCooling] of Object.entries(thermal)) {
    for (const [cooling, v] of Object.entries(byCooling)) {
      out.push({
        fuel,
        cooling,
        consumption: perKwh(v.consumption.median),
        consumptionRange: range(v.consumption),
        withdrawal: perKwh(v.withdrawal.median),
        withdrawalRange: range(v.withdrawal),
      });
    }
  }
  const single = WATER_FACTORS.single as Record<string, { consumption: Stat; withdrawal: Stat }>;
  for (const [fuel, v] of Object.entries(single)) {
    out.push({
      fuel,
      cooling: "n/a",
      consumption: perKwh(v.consumption.median),
      consumptionRange: range(v.consumption),
      withdrawal: perKwh(v.withdrawal.median),
      withdrawalRange: range(v.withdrawal),
    });
  }
  return out;
}

const FACTOR_NOTES = Object.entries(WATER_FACTORS.notes as Record<string, string>);

function MethodologyPage() {
  const { zone } = useZone();
  const latest = useLatest(zone);
  const baseW1 = latest.data?.points?.[latest.data.points.length - 1]?.w1_consumption_L_per_kWh;

  const zoneMeta = (ZONE_PROFILES.zones as Array<{ key: string; name: string; region: string; cooling: Record<string, Record<string, number>> }>).find(
    (z) => z.key === zone,
  );
  const fuels = zoneMeta ? Object.keys(zoneMeta.cooling) : [];
  const [fuel, setFuel] = useState<string>("");
  const activeFuel = fuel || fuels[0] || "";
  const [shares, setShares] = useState<Record<string, number>>({});
  const [whatIfW1, setWhatIfW1] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);

  const current = useMemo(() => {
    const base = zoneMeta?.cooling[activeFuel] ?? {};
    const merged: Record<string, number> = {};
    for (const c of COOLINGS) merged[c] = shares[c] ?? base[c] ?? 0;
    return merged;
  }, [zoneMeta, activeFuel, shares]);

  async function runWhatIf() {
    if (!zoneMeta) return;
    const sum = Object.values(current).reduce((a, b) => a + b, 0) || 1;
    const normalised = Object.fromEntries(Object.entries(current).map(([k, v]) => [k, v / sum]));
    setBusy(true);
    try {
      const res = await callWaterSignals<SeriesResponse>({
        action: "latest",
        zone,
        profileOverrides: { [zone]: { ...zoneMeta.cooling, [activeFuel]: normalised } },
      });
      setWhatIfW1(res.points[res.points.length - 1]?.w1_consumption_L_per_kWh ?? null);
    } catch {
      setWhatIfW1(null);
    } finally {
      setBusy(false);
    }
  }

  const factors = flattenFactors();

  const examples = {
    latest: { action: "latest", zone, includeHydro: false, mode: "origin" },
    history: { action: "history", zone, includeHydro: false, mode: "origin" },
    forecast: { action: "forecast", zone, horizonHours: 72, jobHours: 4, includeHydro: false },
    benchmark: { action: "benchmark", zones: ["DE", "FR", "US-TEX-ERCO"], days: 30 },
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Methodology & API"
        description="How the water signals are computed, which factors are used, and the API shape they could be served through."
      />

      <Card>
        <CardContent className="space-y-3 p-5">
          <h2 className="text-sm font-medium">Formulas</h2>
          <pre className="overflow-x-auto rounded-lg bg-muted p-4 font-mono text-xs leading-relaxed">
            {FORMULAS.join("\n")}
          </pre>
          <p className="text-xs text-muted-foreground">
            G_k = generation by fuel k, Imp_n = imports from neighbour n, I_n = that neighbour's own
            production intensity (one-hop tracing).
          </p>
        </CardContent>
      </Card>

      <section className="space-y-4" aria-labelledby="signal-methods-title">
        <div className="max-w-3xl space-y-2">
          <h2 id="signal-methods-title" className="text-lg font-semibold">How each signal is modelled</h2>
          <p className="text-sm text-muted-foreground">
            Live signals combine Electricity Maps power-system data with public water factors. Cooling profiles
            remain illustrative until calibrated. Concept signals describe the intended partner-data method and
            currently use synthetic values only.
          </p>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          {SIGNAL_METHODS.map((signal) => (
            <article key={signal.id} className="space-y-4 rounded-lg border bg-card p-5 text-card-foreground">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-mono text-xs font-semibold text-water">{signal.id}</p>
                  <h3 className="font-semibold">{signal.name}</h3>
                </div>
                <DataBadge kind={signal.badge} />
              </div>
              <p className="text-sm leading-relaxed">{signal.meaning}</p>
              <dl className="space-y-3 text-sm">
                <div>
                  <dt className="font-medium">How it is modelled</dt>
                  <dd className="mt-1 leading-relaxed text-muted-foreground">{signal.model}</dd>
                </div>
                <div>
                  <dt className="font-medium">Data used</dt>
                  <dd className="mt-1 leading-relaxed text-muted-foreground">{signal.inputs}</dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      </section>

      <Card>
        <CardContent className="space-y-3 p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-medium">Water factors (Macknick et al. 2012, NREL)</h2>
            <DataBadge kind="assumption" />
          </div>
          <div className="max-h-[420px] overflow-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fuel</TableHead>
                  <TableHead>Cooling</TableHead>
                  <TableHead>Consumption L/kWh (min–max)</TableHead>
                  <TableHead>Withdrawal L/kWh (min–max)</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {factors.map((f) => (
                  <TableRow key={`${f.fuel}-${f.cooling}`}>
                    <TableCell className="text-xs">{f.fuel}</TableCell>
                    <TableCell className="text-xs">{f.cooling}</TableCell>
                    <TableCell className="text-xs tabular-nums">
                      {fmtL(f.consumption)} <span className="text-muted-foreground">({f.consumptionRange})</span>
                    </TableCell>
                    <TableCell className="text-xs tabular-nums">
                      {fmtL(f.withdrawal)} <span className="text-muted-foreground">({f.withdrawalRange})</span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <p className="text-xs text-muted-foreground">
            Operational medians converted to litres per kWh delivered; min–max shows the reported range.
          </p>
          <ul className="list-disc space-y-1 pl-5 text-xs text-muted-foreground">
            {FACTOR_NOTES.map(([k, v]) => (
              <li key={k}>
                <span className="font-medium text-foreground">{k}:</span> {v}
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-3 p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-medium">Zone cooling profiles</h2>
            <ProfilesChip />
          </div>
          <div className="rounded-lg border border-amber/30 bg-amber/10 px-4 py-3 text-sm">
            ILLUSTRATIVE — {ZONE_PROFILES.status}
          </div>
          <p className="text-xs text-muted-foreground">
            Calibration plan — US: {ZONE_PROFILES.calibration.US} EU: {ZONE_PROFILES.calibration.EU}
          </p>
          <div className="max-h-[360px] overflow-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Zone</TableHead>
                  <TableHead>Fuel</TableHead>
                  {COOLINGS.map((c) => (
                    <TableHead key={c}>{c}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {(ZONE_PROFILES.zones as Array<{ key: string; cooling: Record<string, Record<string, number>> }>).flatMap((z) =>
                  Object.entries(z.cooling).map(([f, shares2]) => (
                    <TableRow key={`${z.key}-${f}`}>
                      <TableCell className="font-mono text-xs">{z.key}</TableCell>
                      <TableCell className="text-xs">{f}</TableCell>
                      {COOLINGS.map((c) => (
                        <TableCell key={c} className="text-xs tabular-nums">
                          {shares2[c] ? `${Math.round(shares2[c]! * 100)}%` : "—"}
                        </TableCell>
                      ))}
                    </TableRow>
                  )),
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-4 p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-medium">What-if: cooling mix for {zoneLabel(zone)}</h2>
            <DataBadge kind="assumption" />
          </div>
          <div className="flex flex-wrap gap-2">
            {fuels.map((f) => (
              <Button
                key={f}
                size="sm"
                variant={f === activeFuel ? "default" : "secondary"}
                onClick={() => {
                  setFuel(f);
                  setShares({});
                  setWhatIfW1(null);
                }}
              >
                {f}
              </Button>
            ))}
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {COOLINGS.map((c) => (
              <div key={c} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <Label>{c}</Label>
                  <span className="tabular-nums text-muted-foreground">
                    {Math.round((current[c] ?? 0) * 100)}%
                  </span>
                </div>
                <Slider
                  value={[current[c] ?? 0]}
                  min={0}
                  max={1}
                  step={0.05}
                  onValueChange={(v) => setShares((s) => ({ ...current, ...s, [c]: v[0] ?? 0 }))}
                />
              </div>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button size="sm" onClick={runWhatIf} disabled={busy || !zoneMeta}>
              {busy ? "Computing…" : "Recompute W1"}
            </Button>
            <p className="text-sm text-muted-foreground">
              W1 now: {fmtL(baseW1)} L/kWh
              {whatIfW1 != null ? ` → what-if: ${fmtL(whatIfW1)} L/kWh` : ""}
            </p>
          </div>
          <p className="text-xs text-muted-foreground">
            Shares are normalised to 100% before the request. Nothing is saved.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-3 p-5">
          <h2 className="text-sm font-medium">
            WaterTrace API (concept): the shape Electricity Maps could expose as /v4/water-intensity/*
          </h2>
          <pre className="overflow-x-auto rounded-lg bg-muted p-4 font-mono text-xs">
            {Object.entries(examples)
              .map(([k, v]) => `POST /api/water-signals  # ${k}\n${JSON.stringify(v, null, 2)}`)
              .join("\n\n")}
          </pre>
          <Collapsible>
            <CollapsibleTrigger asChild>
              <Button variant="secondary" size="sm">
                Show live JSON response for {zone}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <pre className="mt-3 max-h-96 overflow-auto rounded-lg bg-muted p-4 font-mono text-[11px]">
                {latest.data ? JSON.stringify(latest.data, null, 2) : "Loading…"}
              </pre>
            </CollapsibleContent>
          </Collapsible>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardContent className="space-y-2 p-5 text-sm text-muted-foreground">
            <h2 className="text-sm font-medium text-foreground">Sources & licences</h2>
            <ul className="list-disc space-y-1 pl-5">
              <li>Electricity Maps (commercial API) — mix, flows, carbon, price</li>
              <li>Macknick et al. 2012 / NREL — water factors (public)</li>
              <li>WRI Aqueduct 4.0 — water stress (CC BY 4.0)</li>
              <li>AWARE (WULCA) — characterisation factors</li>
              <li>Global Energy Monitor — plant registry (CC BY 4.0)</li>
              <li>Copernicus ERA5 / GloFAS — weather and hydrology</li>
              <li>EIA — cooling and generator data (public domain)</li>
            </ul>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="space-y-2 p-5 text-sm text-muted-foreground">
            <h2 className="text-sm font-medium text-foreground">Limitations & validation plan</h2>
            <ul className="list-disc space-y-1 pl-5">
              <li>Factors are literature medians, not plant-measured values</li>
              <li>Cooling profiles are illustrative until calibrated</li>
              <li>Hydro reservoir evaporation is excluded by default</li>
              <li>Imports use one-hop tracing, not full network tracing</li>
              <li>The benchmark uses the fast method (daily mix × local factors)</li>
            </ul>
            <p>
              Validation: Wattnet (EU), LBNL Water IMPACT Tool (US), EIA cooling-water data.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
