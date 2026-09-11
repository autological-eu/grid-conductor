import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { useQueries } from "@tanstack/react-query";
import { CircleMarker, MapContainer, Popup, TileLayer, Tooltip } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { DataBadge, ProfilesChip } from "@/components/DataBadge";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { callWaterSignals, type SeriesResponse, type WaterPoint } from "@/lib/waterApi";
import { fmtL, fmtPct } from "@/lib/format";
import { ZONE_PROFILES } from "@/lib/seedData";
import { PILOT_ZONES } from "@/lib/zones";
import { useSettings } from "@/stores/settings";

type Metric = "w1" | "w2" | "w3";

const METRICS: Record<Metric, { label: string; short: string; value: (point: WaterPoint) => number }> = {
  w1: {
    label: "Water consumption intensity",
    short: "W1 · Consumption",
    value: (point) => point.w1_consumption_L_per_kWh,
  },
  w2: {
    label: "Freshwater withdrawal intensity",
    short: "W2 · Withdrawal",
    value: (point) => point.w2_withdrawal_L_per_kWh,
  },
  w3: {
    label: "Imported water share",
    short: "W3 · Imported share",
    value: (point) => point.w3_imported_water_share,
  },
};

function formatMetric(metric: Metric, value: number) {
  return metric === "w3" ? `${fmtPct(value, 0)}%` : `${fmtL(value)} L/kWh`;
}

function markerColor(value: number, min: number, max: number) {
  const share = max === min ? 0.5 : (value - min) / (max - min);
  if (share < 0.34) return "var(--teal)";
  if (share < 0.67) return "var(--amber)";
  return "var(--coral)";
}

export default function OverviewSignalMap() {
  const [metric, setMetric] = useState<Metric>("w1");
  const includeHydro = useSettings((state) => state.includeHydro);
  const mode = useSettings((state) => state.mode);
  const zoneMeta = ZONE_PROFILES.zones as Array<{ key: string; lat: number; lon: number }>;

  const queries = useQueries({
    queries: PILOT_ZONES.map((zone) => ({
      queryKey: ["water", "latest", zone.key, includeHydro, mode],
      queryFn: () =>
        callWaterSignals<SeriesResponse>({ action: "latest", zone: zone.key, includeHydro, mode }),
      staleTime: 5 * 60 * 1000,
      retry: false,
    })),
  });

  const points = PILOT_ZONES.flatMap((zone, index) => {
    const point = queries[index]?.data?.points?.at(-1);
    const location = zoneMeta.find((item) => item.key === zone.key);
    if (!point || !location) return [];
    return [{ ...zone, ...location, point, value: METRICS[metric].value(point) }];
  });
  const values = points.map((point) => point.value);
  const min = values.length ? Math.min(...values) : 0;
  const max = values.length ? Math.max(...values) : 1;
  const pending = queries.filter((query) => query.isLoading).length;
  const unavailable = queries.filter((query) => query.isError).length;

  return (
    <Card className="overflow-hidden">
      <CardContent className="space-y-4 p-5 sm:p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-foreground">The live water layer</h2>
            <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
              Electricity Maps generation mix and cross-border flows combined with literature-based water
              factors and illustrative cooling profiles across 15 pilot zones.
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            <DataBadge kind="live" />
            <ProfilesChip />
          </div>
        </div>

        <Tabs value={metric} onValueChange={(value) => setMetric(value as Metric)}>
          <TabsList className="grid h-auto w-full grid-cols-1 sm:w-auto sm:grid-cols-3">
            {(Object.entries(METRICS) as Array<[Metric, (typeof METRICS)[Metric]]>).map(([key, item]) => (
              <TabsTrigger key={key} value={key} className="whitespace-normal px-3 py-2 text-xs">
                {item.short}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        <div className="overflow-hidden rounded-lg border border-border bg-muted">
          <MapContainer
            center={[35, -20]}
            zoom={2}
            minZoom={2}
            scrollWheelZoom={false}
            style={{ height: 460, width: "100%" }}
          >
            <TileLayer
              attribution="&copy; OpenStreetMap contributors"
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {points.map((item) => {
              const color = markerColor(item.value, min, max);
              const localTime = new Intl.DateTimeFormat(undefined, {
                dateStyle: "medium",
                timeStyle: "short",
              }).format(new Date(item.point.datetime));
              const utcTime = new Date(item.point.datetime).toUTCString();
              return (
                <CircleMarker
                  key={item.key}
                  center={[item.lat, item.lon]}
                  radius={9}
                  pathOptions={{ color, fillColor: color, fillOpacity: 0.78, weight: 2 }}
                >
                  <Tooltip direction="top" offset={[0, -8]}>
                    <strong>{item.label}</strong>
                    <br />
                    {formatMetric(metric, item.value)}
                  </Tooltip>
                  <Popup minWidth={230}>
                    <div className="space-y-2 text-sm">
                      <div>
                        <strong>{item.label}</strong>
                        <div className="text-xs text-muted-foreground">{item.key}</div>
                      </div>
                      <div className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1">
                        <span>W1 consumption</span>
                        <strong>{fmtL(item.point.w1_consumption_L_per_kWh)} L/kWh</strong>
                        <span>W2 withdrawal</span>
                        <strong>{fmtL(item.point.w2_withdrawal_L_per_kWh)} L/kWh</strong>
                        <span>W3 imported share</span>
                        <strong>{fmtPct(item.point.w3_imported_water_share, 0)}%</strong>
                      </div>
                      <div className="text-xs text-muted-foreground" title={`UTC: ${utcTime}`}>
                        {localTime} local · hover for UTC
                      </div>
                      <Link
                        to="/live"
                        search={{ zone: item.key }}
                        className="inline-flex text-xs font-medium text-water underline-offset-4 hover:underline"
                      >
                        Open live signals
                      </Link>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}
          </MapContainer>
        </div>

        <div className="flex flex-col gap-2 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-3">
            <span className="font-medium text-foreground">{METRICS[metric].label}</span>
            <span className="inline-flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full bg-teal" />Lower</span>
            <span className="inline-flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full bg-amber" />Middle</span>
            <span className="inline-flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full bg-coral" />Higher</span>
          </div>
          <span>
            {points.length} zones shown{pending ? ` · ${pending} loading` : ""}{unavailable ? ` · ${unavailable} unavailable` : ""}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}