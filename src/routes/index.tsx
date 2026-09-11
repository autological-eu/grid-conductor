import { lazy, Suspense, useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import {
  BarChart3,
  CloudSun,
  Droplets,
  Factory,
  Gauge,
  Handshake,
  Map as MapIcon,
  Rocket,
  Search,
  Users,
} from "lucide-react";
import { PageHeader } from "@/components/AppShell";
import { SignalCard } from "@/components/SignalCard";
import { DataBadge, ProfilesChip } from "@/components/DataBadge";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useZone } from "@/hooks/useZone";
import { useLatest } from "@/hooks/useWaterSignals";
import { zoneLabel } from "@/lib/zones";
import { fmtL, fmtPct } from "@/lib/format";

const OverviewSignalMap = lazy(() => import("@/components/OverviewSignalMap"));

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "WaterTrace — Water signals for every kilowatt-hour" },
      {
        name: "description",
        content:
          "A concept water layer on Electricity Maps data: hourly water intensity, low-water windows, facility footprints and siting benchmarks.",
      },
      { property: "og:title", content: "WaterTrace — Water signals for every kilowatt-hour" },
      {
        property: "og:description",
        content:
          "Water consumption and withdrawal intensity, forecasts and facility footprints for electricity zones.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Overview,
});

const STRIP_ZONES = ["DK-DK1", "DE", "FR", "ES", "US-SW-AZPS"];

const STEPS = [
  { icon: Search, title: "The gap", text: "Every grid has a carbon signal. None has a water signal." },
  { icon: Droplets, title: "Which water", text: "What power plants consume per kWh — not tap water at the office." },
  { icon: Factory, title: "Why it matters", text: "US data centres use roughly 12× more water off-site through electricity than on-site cooling (LBNL via ITIF)." },
  { icon: MapIcon, title: "Not every litre is equal", text: "A litre in Arizona is not a litre in Norway. Local water stress matters (concept X1)." },
  { icon: Gauge, title: "The signal", text: "W1 water consumption intensity in L/kWh, hourly, with a 72 h forecast." },
  { icon: CloudSun, title: "How", text: "Generation mix and cross-border flows × water factors by fuel and cooling type." },
  { icon: Users, title: "Who it is for", text: "Data centres, CSRD/GRI reporters, ESG software, utilities and traders." },
  { icon: Handshake, title: "Partnerships", text: "X1–X6 add water stress, satellite cooling, weather, hydrology and site telemetry." },
  { icon: Rocket, title: "Next", text: "Pilot across EU and US zones; validate against Wattnet and the LBNL Water IMPACT Tool." },
];

function StripCard({ zone }: { zone: string }) {
  const q = useLatest(zone);
  const p = q.data?.points?.[q.data.points.length - 1];
  if (q.isLoading) return <Skeleton className="h-40 rounded-xl" />;
  return (
    <SignalCard
      id="W1"
      title={zoneLabel(zone)}
      value={q.error ? "—" : fmtL(p?.w1_consumption_L_per_kWh)}
      unit="L/kWh"
      subtitle={q.error ? "data unavailable right now" : `${zone} · water consumed now`}
      badge="live"
      chip={<ProfilesChip />}
    />
  );
}

function Overview() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const { zone } = useZone();
  const dk = useLatest("DK-DK1");
  const dkPoint = dk.data?.points?.[dk.data.points.length - 1];
  const topOrigin = dkPoint
    ? Object.entries(dkPoint.w3_by_origin).sort((a, b) => b[1].water_m3_per_h - a[1].water_m3_per_h)[0]?.[0]
    : undefined;

  return (
    <div className="space-y-10">
      <section className="rounded-2xl border border-border bg-gradient-to-br from-water/10 to-transparent p-8">
        <h1 className="max-w-3xl text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
          Electricity Maps shows the carbon behind every kWh. WaterTrace adds the water.
        </h1>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          Hourly, flow-traced water signals for any grid zone, built on the Electricity Maps API.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Button asChild>
            <Link to="/live" search={{ zone }}>
              Explore live signals
            </Link>
          </Button>
          <Button asChild variant="secondary">
            <Link to="/concepts" search={{ zone }}>
              See partner concepts
            </Link>
          </Button>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-medium text-muted-foreground">Water intensity right now</h2>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          {STRIP_ZONES.map((z) => (
            <StripCard key={z} zone={z} />
          ))}
        </div>
      </section>

      <section aria-label="Global live water signals">
        {mounted ? (
          <Suspense fallback={<Skeleton className="h-[620px] rounded-xl" />}>
            <OverviewSignalMap />
          </Suspense>
        ) : (
          <Skeleton className="h-[620px] rounded-xl" />
        )}
      </section>

      <section className="space-y-4">
        <PageHeader title="Why a water layer" />
        <ol className="space-y-4">
          {STEPS.map((s, i) => (
            <li key={s.title} className="flex gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-water/10 text-water">
                <s.icon className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">
                  {i + 1}. {s.title}
                </p>
                <p className="text-sm text-muted-foreground">{s.text}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section>
        <Card>
          <CardContent className="space-y-3 p-6">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-sm font-medium">Live example — West Denmark</h2>
              <DataBadge kind="live" />
            </div>
            {dk.isLoading ? (
              <Skeleton className="h-20 rounded-lg" />
            ) : dkPoint ? (
              <p className="text-lg text-foreground">
                {fmtPct(dkPoint.w3_imported_water_share, 0)}% of the water behind electricity consumed
                in West Denmark right now is embedded in imports
                {topOrigin ? `, mostly from ${topOrigin}` : ""}. Static annual factors would miss this.
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">Live data unavailable right now.</p>
            )}
            <div className="flex flex-wrap gap-3 pt-2">
              <Button asChild size="sm">
                <Link to="/live" search={{ zone }}>
                  Explore live signals
                </Link>
              </Button>
              <Button asChild size="sm" variant="secondary">
                <Link to="/benchmark" search={{ zone }}>
                  Compare zones
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
