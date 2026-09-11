import { createFileRoute } from "@tanstack/react-router";
import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Droplets } from "lucide-react";
import { PageHeader } from "@/components/AppShell";
import { SignalCard } from "@/components/SignalCard";
import { DataBadge, ProfilesChip } from "@/components/DataBadge";
import { CardsSkeleton, ChartSkeleton, ConceptBanner, ErrorCard } from "@/components/States";
import { Card, CardContent } from "@/components/ui/card";
import { useZone } from "@/hooks/useZone";
import { useHistory, useLatest } from "@/hooks/useWaterSignals";
import { zoneLabel } from "@/lib/zones";
import { fmtL, fmtNum, fmtPct, localHour, utcLabel } from "@/lib/format";
import type { WaterPoint } from "@/lib/waterApi";

export const Route = createFileRoute("/live")({
  head: () => ({
    meta: [
      { title: "Live Signals — WaterTrace" },
      {
        name: "description",
        content:
          "Live water consumption intensity, withdrawal intensity and imported water share for the selected electricity zone.",
      },
      { property: "og:title", content: "Live Signals — WaterTrace" },
      {
        property: "og:description",
        content: "W1, W2 and W3 water signals for the selected electricity zone.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: LivePage,
});

function ChartCard({
  title,
  badge,
  children,
  note,
}: {
  title: string;
  badge: "live" | "assumption" | "mock";
  children: React.ReactNode;
  note?: string | undefined;
}) {
  return (
    <Card>
      <CardContent className="space-y-3 p-5">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-sm font-medium text-foreground">{title}</h2>
          <DataBadge kind={badge} />
        </div>
        {children}
        {note ? <p className="text-xs text-muted-foreground">{note}</p> : null}
      </CardContent>
    </Card>
  );
}

function LivePage() {
  const { zone } = useZone();
  const latest = useLatest(zone);
  const history = useHistory(zone);

  const point: WaterPoint | undefined = latest.data?.points?.[latest.data.points.length - 1];
  const volumeNow = point
    ? Object.values(point.by_source).reduce((a, s) => a + (s.water_m3_per_h ?? 0), 0)
    : null;

  const sourceRows = point
    ? Object.entries(point.by_source)
        .map(([source, v]) => ({ source, ...v }))
        .sort((a, b) => b.water_m3_per_h - a.water_m3_per_h)
    : [];

  const originRows = point
    ? Object.entries(point.w3_by_origin)
        .map(([origin, v]) => ({ origin, ...v }))
        .sort((a, b) => b.water_m3_per_h - a.water_m3_per_h)
    : [];

  const topOrigin = originRows[0]?.origin;

  const series =
    history.data?.points?.map((p) => ({
      t: p.datetime,
      consumed: p.w1_consumption_L_per_kWh,
      domestic: p.w1_production_L_per_kWh,
      importedGap: Math.max(0, p.w1_consumption_L_per_kWh - p.w1_production_L_per_kWh),
      base: Math.min(p.w1_consumption_L_per_kWh, p.w1_production_L_per_kWh),
    })) ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Live signals"
        description={`W1, W2 and W3 for ${zoneLabel(zone)} (${zone}), computed from the current Electricity Maps mix and flows.`}
      />
      <ConceptBanner />

      {latest.isLoading ? (
        <CardsSkeleton />
      ) : latest.error ? (
        <ErrorCard error={latest.error} onRetry={() => latest.refetch()} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <SignalCard
            id="W1"
            title="Water consumed"
            value={fmtL(point?.w1_consumption_L_per_kWh)}
            unit="L/kWh"
            subtitle={`freshwater, flow-traced · domestic generation only: ${fmtL(point?.w1_production_L_per_kWh)} L/kWh`}
            badge="live"
            chip={<ProfilesChip />}
          />
          <SignalCard
            id="W2"
            title="Water withdrawn"
            value={fmtL(point?.w2_withdrawal_L_per_kWh)}
            unit="L/kWh"
            subtitle={`freshwater · incl. seawater: ${fmtL(point?.w2_withdrawal_total_L_per_kWh)} L/kWh`}
            badge="live"
            chip={<ProfilesChip />}
          />
          <SignalCard
            id="W3"
            title="Imported water share"
            value={fmtPct(point?.w3_imported_water_share, 0)}
            unit="%"
            subtitle={`of power: ${fmtPct(point?.w3_imported_power_share, 0)} %`}
            badge="live"
            chip={<ProfilesChip />}
          />
          <SignalCard
            id="W1"
            title="Water volume now"
            value={fmtNum(volumeNow, 0)}
            unit="m³/h"
            subtitle="sum of water behind generation in this hour"
            badge="live"
            chip={<ProfilesChip />}
          />
        </div>
      )}

      {point && point.w3_imported_water_share > 0.4 ? (
        <Card className="border-water/40 bg-water/5">
          <CardContent className="flex items-start gap-3 p-5">
            <Droplets className="mt-0.5 h-5 w-5 shrink-0 text-water" />
            <p className="text-sm text-foreground">
              {fmtPct(point.w3_imported_water_share, 0)}% of the water behind electricity consumed in{" "}
              {zoneLabel(zone)} right now is embedded in imports
              {topOrigin ? `, mostly from ${topOrigin}` : ""}. Static annual factors would miss this.
            </p>
          </CardContent>
        </Card>
      ) : null}

      <ChartCard
        title="Last 24 h — W1 consumed vs domestic generation"
        badge="live"
        note="Coral fill shows the water imported with electricity: consumption above domestic production."
      >
        {history.isLoading ? (
          <ChartSkeleton />
        ) : history.error ? (
          <ErrorCard error={history.error} onRetry={() => history.refetch()} />
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <ComposedChart data={series}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="t" tickFormatter={localHour} fontSize={11} stroke="var(--muted-foreground)" />
              <YAxis fontSize={11} stroke="var(--muted-foreground)" unit=" L" width={56} />
              <Tooltip
                labelFormatter={(v: string) => `${localHour(v)} · ${utcLabel(v)}`}
                formatter={(v: number, n: string) => [`${fmtL(v)} L/kWh`, n]}
                contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8 }}
              />
              <Area
                type="monotone"
                dataKey="base"
                stackId="gap"
                stroke="none"
                fill="transparent"
                isAnimationActive={false}
              />
              <Area
                type="monotone"
                dataKey="importedGap"
                stackId="gap"
                stroke="none"
                fill="var(--coral)"
                fillOpacity={0.25}
                name="imported water"
                isAnimationActive={false}
              />
              <Line type="monotone" dataKey="consumed" stroke="var(--water)" dot={false} strokeWidth={2} name="consumed" />
              <Line
                type="monotone"
                dataKey="domestic"
                stroke="var(--muted-foreground)"
                strokeDasharray="4 3"
                dot={false}
                name="domestic"
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </ChartCard>

      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Water by source (m³/h)" badge="live">
          {latest.isLoading ? (
            <ChartSkeleton />
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={sourceRows}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="source" fontSize={11} stroke="var(--muted-foreground)" />
                <YAxis fontSize={11} stroke="var(--muted-foreground)" width={56} />
                <Tooltip
                  contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8 }}
                  formatter={(v: number, _n, item: { payload?: { mw: number; factor_L_per_kWh: number } }) => [
                    `${fmtNum(v, 0)} m³/h · ${fmtNum(item?.payload?.mw ?? 0, 0)} MW · ${fmtL(item?.payload?.factor_L_per_kWh)} L/kWh`,
                    "water",
                  ]}
                />
                <Bar dataKey="water_m3_per_h" fill="var(--water)" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <ChartCard
          title="Imported water by origin (m³/h)"
          badge="live"
          note={
            originRows.some((r) => r.estimated)
              ? "Some neighbours are estimated (marked in the tooltip)."
              : undefined
          }
        >
          {latest.isLoading ? (
            <ChartSkeleton />
          ) : originRows.length === 0 ? (
            <p className="py-16 text-center text-sm text-muted-foreground">No imports in this hour.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={originRows}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="origin" fontSize={11} stroke="var(--muted-foreground)" />
                <YAxis fontSize={11} stroke="var(--muted-foreground)" width={56} />
                <Tooltip
                  contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8 }}
                  formatter={(v: number, _n, item: { payload?: { mw: number; estimated?: boolean } }) => [
                    `${fmtNum(v, 0)} m³/h · ${fmtNum(item?.payload?.mw ?? 0, 0)} MW${item?.payload?.estimated ? " · estimated" : ""}`,
                    "water",
                  ]}
                />
                <Bar dataKey="water_m3_per_h" fill="var(--teal)" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </div>
    </div>
  );
}
