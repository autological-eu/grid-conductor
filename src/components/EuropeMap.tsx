import { useMemo, useState } from "react";
import geo from "@/data/europe.geo.json";

export type ZoneSummary = {
  code: string;
  name: string;
  country_code: string;
  lat: number;
  lon: number;
  avg_carbon_intensity: number | null;
  avg_price: number | null;
  hours: number;
};

export type TargetRow = {
  id: string;
  zone_a: string;
  zone_b: string;
  zone_a_name: string;
  zone_b_name: string;
  a_lat: number;
  a_lon: number;
  b_lat: number;
  b_lon: number;
  congested_hours: number;
  total_hours: number;
  market_loss_meur: number;
  climate_loss_ktco2: number;
  observed_capacity_mw: number | null;
};

const W = 900;
const H = 780;
const LON0 = -12;
const LON1 = 34;
const LAT0 = 34;
const LAT1 = 71;

const merc = (lat: number) => Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
const MY0 = merc(LAT0);
const MY1 = merc(LAT1);

function project(lon: number, lat: number): [number, number] {
  const x = ((lon - LON0) / (LON1 - LON0)) * W;
  const y = H - ((merc(lat) - MY0) / (MY1 - MY0)) * H;
  return [x, y];
}

type Ring = number[][];
type Geom =
  | { type: "Polygon"; coordinates: Ring[] }
  | { type: "MultiPolygon"; coordinates: Ring[][] };

function pathFor(geom: Geom): string {
  const polys = geom.type === "Polygon" ? [geom.coordinates] : geom.coordinates;
  let d = "";
  for (const poly of polys) {
    for (const ring of poly) {
      ring.forEach((pt, i) => {
        const [x, y] = project(pt[0]!, pt[1]!);
        if (x < -400 || x > W + 400 || y < -400 || y > H + 400) return;
        d += `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
      });
      d += "Z";
    }
  }
  return d;
}

export function EuropeMap({
  zones,
  targets,
  selectedId,
  onSelect,
  metric,
}: {
  zones: ZoneSummary[];
  targets: TargetRow[];
  selectedId: string | null;
  onSelect: (t: TargetRow) => void;
  metric: "market" | "climate";
}) {
  const [hover, setHover] = useState<string | null>(null);

  const countries = useMemo(
    () =>
      (geo as unknown as { features: Array<{ properties: { name: string }; geometry: Geom }> })
        .features.map((f) => ({ name: f.properties.name, d: pathFor(f.geometry) })),
    [],
  );

  const maxLoss = Math.max(
    1,
    ...targets.map((t) => (metric === "market" ? t.market_loss_meur : t.climate_loss_ktco2)),
  );
  const maxCi = Math.max(1, ...zones.map((z) => z.avg_carbon_intensity ?? 0));

  return (
    <div className="relative h-full w-full overflow-hidden rounded-xl border border-border bg-card">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-full w-full" role="img" aria-label="Map of European bidding zones and congested borders">
        <rect width={W} height={H} className="fill-muted/40" />
        {countries.map((c) => (
          <path
            key={c.name}
            d={c.d}
            className="fill-secondary stroke-border"
            strokeWidth={0.8}
          />
        ))}

        {/* zone markers, shaded by average carbon intensity */}
        {zones.map((z) => {
          const [x, y] = project(z.lon, z.lat);
          const ci = z.avg_carbon_intensity ?? 0;
          const k = Math.min(1, ci / maxCi);
          return (
            <g key={z.code}>
              <circle
                cx={x}
                cy={y}
                r={z.hours > 0 ? 6 : 3.5}
                fill={`oklch(${0.78 - 0.2 * k} ${0.09 + 0.13 * k} ${145 - 120 * k})`}
                fillOpacity={z.hours > 0 ? 0.95 : 0.35}
                stroke="var(--color-card)"
                strokeWidth={1}
              >
                <title>
                  {z.name} ({z.code})
                  {z.avg_price != null ? ` — ${z.avg_price.toFixed(1)} EUR/MWh` : ""}
                  {z.avg_carbon_intensity != null
                    ? `, ${Math.round(z.avg_carbon_intensity)} gCO2/kWh`
                    : ""}
                </title>
              </circle>
            </g>
          );
        })}

        {/* target borders */}
        {targets.map((t) => {
          const [x1, y1] = project(t.a_lon, t.a_lat);
          const [x2, y2] = project(t.b_lon, t.b_lat);
          const v = metric === "market" ? t.market_loss_meur : t.climate_loss_ktco2;
          const k = Math.min(1, Math.max(0.06, v / maxLoss));
          const active = selectedId === t.id || hover === t.id;
          return (
            <g
              key={t.id}
              className="cursor-pointer"
              onClick={() => onSelect(t)}
              onMouseEnter={() => setHover(t.id)}
              onMouseLeave={() => setHover(null)}
            >
              <line
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke="transparent"
                strokeWidth={16}
              />
              <line
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke={active ? "var(--color-primary)" : "var(--color-destructive)"}
                strokeOpacity={active ? 1 : 0.35 + 0.6 * k}
                strokeWidth={2 + 9 * k}
                strokeLinecap="round"
              />
              <title>
                {t.zone_a} – {t.zone_b}: {t.market_loss_meur.toFixed(1)} MEUR/y,{" "}
                {t.climate_loss_ktco2.toFixed(1)} ktCO2/y, {t.congested_hours} congested hours
              </title>
            </g>
          );
        })}
      </svg>

      <div className="pointer-events-none absolute bottom-3 left-3 rounded-lg border border-border bg-card/90 px-3 py-2 text-xs text-muted-foreground backdrop-blur">
        <div className="font-medium text-foreground">
          {metric === "market" ? "Market opportunity loss" : "Climate opportunity loss"}
        </div>
        <div>Thicker border = larger yearly loss. Click a border to open it.</div>
      </div>
    </div>
  );
}
