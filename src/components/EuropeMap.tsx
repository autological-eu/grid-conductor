import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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

const MIN_ZOOM = 1;
const MAX_ZOOM = 12;

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
      let started = false;
      for (const pt of ring) {
        const [x, y] = project(pt[0]!, pt[1]!);
        if (x < -400 || x > W + 400 || y < -400 || y > H + 400) continue;
        d += `${started ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
        started = true;
      }
      if (started) d += "Z";
    }
  }
  return d;
}

/** Some Natural Earth features carry iso "-99"; map those by name. */
const ISO_FALLBACK: Record<string, string> = {
  Norway: "NO",
  France: "FR",
  Kosovo: "XK",
};

const countryOf = (zoneCode: string) => zoneCode.split("-")[0]!;

type View = { k: number; x: number; y: number };
const IDENTITY: View = { k: 1, x: 0, y: 0 };

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

export function EuropeMap({
  zones,
  targets,
  selectedId,
  onSelect,
  onClear,
  metric,
}: {
  zones: ZoneSummary[];
  targets: TargetRow[];
  selectedId: string | null;
  onSelect: (t: TargetRow) => void;
  onClear?: () => void;
  metric: "market" | "climate";
}) {
  const [hover, setHover] = useState<string | null>(null);
  const [view, setView] = useState<View>(IDENTITY);
  const [dragging, setDragging] = useState(false);

  const svgRef = useRef<SVGSVGElement | null>(null);
  const viewRef = useRef(view);
  viewRef.current = view;
  const dragRef = useRef<{ x: number; y: number; moved: boolean } | null>(null);
  const animRef = useRef<number | null>(null);

  const countries = useMemo(
    () =>
      (
        geo as unknown as {
          features: Array<{ properties: { name: string; iso: string }; geometry: Geom }>;
        }
      ).features.map((f) => ({
        name: f.properties.name,
        iso:
          f.properties.iso && f.properties.iso !== "-99"
            ? f.properties.iso
            : (ISO_FALLBACK[f.properties.name] ?? ""),
        d: pathFor(f.geometry),
      })),
    [],
  );

  const selected = useMemo(
    () => targets.find((t) => t.id === selectedId) ?? null,
    [targets, selectedId],
  );

  const focusIso = useMemo(() => {
    if (!selected) return null;
    return new Set([countryOf(selected.zone_a), countryOf(selected.zone_b)]);
  }, [selected]);

  /** convert a client point into untransformed viewBox coordinates */
  const toViewBox = useCallback((clientX: number, clientY: number) => {
    const el = svgRef.current;
    if (!el) return { x: 0, y: 0 };
    const r = el.getBoundingClientRect();
    return { x: ((clientX - r.left) / r.width) * W, y: ((clientY - r.top) / r.height) * H };
  }, []);

  const stopAnim = () => {
    if (animRef.current != null) {
      cancelAnimationFrame(animRef.current);
      animRef.current = null;
    }
  };

  const animateTo = useCallback((to: View, ms = 500) => {
    stopAnim();
    const from = viewRef.current;
    const start = performance.now();
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / ms);
      const e = 1 - Math.pow(1 - t, 3);
      setView({
        k: from.k + (to.k - from.k) * e,
        x: from.x + (to.x - from.x) * e,
        y: from.y + (to.y - from.y) * e,
      });
      if (t < 1) animRef.current = requestAnimationFrame(step);
      else animRef.current = null;
    };
    animRef.current = requestAnimationFrame(step);
  }, []);

  useEffect(() => () => stopAnim(), []);

  /** ease the view to fit the selected border */
  useEffect(() => {
    if (!selected) {
      animateTo(IDENTITY);
      return;
    }
    const [x1, y1] = project(selected.a_lon, selected.a_lat);
    const [x2, y2] = project(selected.b_lon, selected.b_lat);
    const pad = 140;
    const w = Math.abs(x2 - x1) + pad * 2;
    const h = Math.abs(y2 - y1) + pad * 2;
    const k = clamp(Math.min(W / w, H / h), MIN_ZOOM, 6);
    const cx = (x1 + x2) / 2;
    const cy = (y1 + y2) / 2;
    animateTo({ k, x: W / 2 - cx * k, y: H / 2 - cy * k });
  }, [selected, animateTo]);

  const zoomAt = useCallback((px: number, py: number, factor: number) => {
    const v = viewRef.current;
    const k = clamp(v.k * factor, MIN_ZOOM, MAX_ZOOM);
    const ratio = k / v.k;
    setView({ k, x: px - (px - v.x) * ratio, y: py - (py - v.y) * ratio });
  }, []);

  const wheelRef = useRef<(e: WheelEvent) => void>(() => {});
  wheelRef.current = (e: WheelEvent) => {
    const dy = e.deltaY * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? 100 : 1);
    const p = toViewBox(e.clientX, e.clientY);
    stopAnim();
    zoomAt(p.x, p.y, Math.exp(-dy * 0.0015));
  };

  useEffect(() => {
    const el = svgRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      wheelRef.current(e);
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  const onPointerDown = (e: React.PointerEvent<SVGSVGElement>) => {
    if (e.button !== 0) return;
    stopAnim();
    (e.currentTarget as SVGSVGElement).setPointerCapture(e.pointerId);
    dragRef.current = { x: e.clientX, y: e.clientY, moved: false };
    setDragging(true);
  };

  const onPointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const d = dragRef.current;
    if (!d) return;
    const el = svgRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const dx = ((e.clientX - d.x) / r.width) * W;
    const dy = ((e.clientY - d.y) / r.height) * H;
    if (Math.abs(e.clientX - d.x) + Math.abs(e.clientY - d.y) > 3) d.moved = true;
    d.x = e.clientX;
    d.y = e.clientY;
    setView((v) => ({ ...v, x: v.x + dx, y: v.y + dy }));
  };

  const endDrag = (e: React.PointerEvent<SVGSVGElement>) => {
    if (dragRef.current) {
      const el = e.currentTarget as SVGSVGElement;
      if (el.hasPointerCapture(e.pointerId)) el.releasePointerCapture(e.pointerId);
    }
    setDragging(false);
    // keep `moved` readable by the click handler for this frame
    window.setTimeout(() => {
      dragRef.current = null;
    }, 0);
  };

  const wasDrag = () => dragRef.current?.moved === true;

  const zoomButton = (factor: number) => {
    stopAnim();
    zoomAt(W / 2, H / 2, factor);
  };

  const maxLoss = Math.max(
    1,
    ...targets.map((t) => (metric === "market" ? t.market_loss_meur : t.climate_loss_ktco2)),
  );
  const maxCi = Math.max(1, ...zones.map((z) => z.avg_carbon_intensity ?? 0));
  const k = view.k;

  return (
    <div className="relative h-full w-full overflow-hidden rounded-xl border border-border bg-card">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className={`h-full w-full touch-none select-none ${dragging ? "cursor-grabbing" : "cursor-grab"}`}
        role="img"
        aria-label="Map of European bidding zones and congested borders"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
      >
        <rect
          width={W}
          height={H}
          className="fill-muted/40"
          onClick={() => {
            if (!wasDrag()) onClear?.();
          }}
        />
        <g transform={`translate(${view.x},${view.y}) scale(${k})`}>
          {countries.map((c) => {
            const focused = focusIso?.has(c.iso) ?? false;
            return (
              <path
                key={c.name}
                d={c.d}
                className={
                  focused
                    ? "fill-primary/20 stroke-primary"
                    : focusIso
                      ? "fill-secondary/60 stroke-border"
                      : "fill-secondary stroke-border"
                }
                strokeWidth={(focused ? 2 : 0.8) / k}
              />
            );
          })}

          {/* zone markers, shaded by average carbon intensity */}
          {zones.map((z) => {
            const [x, y] = project(z.lon, z.lat);
            const ci = z.avg_carbon_intensity ?? 0;
            const c = Math.min(1, ci / maxCi);
            const dim = focusIso ? !focusIso.has(countryOf(z.code)) : false;
            return (
              <g key={z.code}>
                <circle
                  cx={x}
                  cy={y}
                  r={(z.hours > 0 ? 6 : 3.5) / k}
                  fill={`oklch(${0.78 - 0.2 * c} ${0.09 + 0.13 * c} ${145 - 120 * c})`}
                  fillOpacity={dim ? 0.2 : z.hours > 0 ? 0.95 : 0.35}
                  stroke="var(--color-card)"
                  strokeWidth={1 / k}
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
            const c = Math.min(1, Math.max(0.06, v / maxLoss));
            const isSelected = selectedId === t.id;
            const active = isSelected || hover === t.id;
            const faded = selectedId != null && !isSelected;
            return (
              <g
                key={t.id}
                className="cursor-pointer"
                onClick={() => {
                  if (!wasDrag()) onSelect(t);
                }}
                onMouseEnter={() => setHover(t.id)}
                onMouseLeave={() => setHover(null)}
              >
                <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="transparent" strokeWidth={16 / k} />
                <line
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke={
                    faded
                      ? "var(--color-muted-foreground)"
                      : active
                        ? "var(--color-primary)"
                        : "var(--color-destructive)"
                  }
                  strokeOpacity={faded ? 0.25 : active ? 1 : 0.35 + 0.6 * c}
                  strokeWidth={(2 + 9 * c) / k}
                  strokeLinecap="round"
                />
                <title>
                  {t.zone_a} – {t.zone_b}: {t.market_loss_meur.toFixed(1)} MEUR/y,{" "}
                  {t.climate_loss_ktco2.toFixed(1)} ktCO2/y, {t.congested_hours} congested hours
                </title>
              </g>
            );
          })}
        </g>
      </svg>

      <div className="pointer-events-none absolute left-3 top-3 max-w-[22rem] rounded-lg border border-border bg-card/90 px-3 py-2 backdrop-blur">
        <h2 className="text-sm font-semibold text-foreground">
          European bidding zones and congested borders
        </h2>
        <p className="text-xs text-muted-foreground">
          {metric === "market"
            ? "Yearly market opportunity loss"
            : "Yearly climate opportunity loss"}
        </p>
      </div>

      <div className="absolute right-3 top-3 flex flex-col gap-1">
        <button
          type="button"
          aria-label="Zoom in"
          onClick={() => zoomButton(1.4)}
          className="h-8 w-8 rounded-md border border-border bg-card/90 text-sm text-foreground backdrop-blur hover:bg-accent"
        >
          +
        </button>
        <button
          type="button"
          aria-label="Zoom out"
          onClick={() => zoomButton(1 / 1.4)}
          className="h-8 w-8 rounded-md border border-border bg-card/90 text-sm text-foreground backdrop-blur hover:bg-accent"
        >
          −
        </button>
        <button
          type="button"
          aria-label="Reset view"
          onClick={() => animateTo(IDENTITY, 350)}
          className="h-8 w-8 rounded-md border border-border bg-card/90 text-[10px] text-foreground backdrop-blur hover:bg-accent"
        >
          Fit
        </button>
      </div>

      <div className="pointer-events-none absolute bottom-3 left-3 rounded-lg border border-border bg-card/90 px-3 py-2 text-xs text-muted-foreground backdrop-blur">
        <div className="font-medium text-foreground">
          {metric === "market" ? "Market opportunity loss" : "Climate opportunity loss"}
        </div>
        <div>Thicker border = larger yearly loss. Click a border to zoom in on it.</div>
        <div>Scroll to zoom, drag to pan.</div>
      </div>
    </div>
  );
}
