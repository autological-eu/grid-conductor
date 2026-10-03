import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import geo from "@/data/europe.geo.json";
import { unitDef, unitDrag, type UnitType } from "@/lib/units";
import { unitIcon } from "@/lib/unitIcons";

export type UnitDropPlacement = { zoneCode?: string; zoneA?: string; zoneB?: string };

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
  /** Bounded deadweight-loss estimate of the directed border (MEUR/y) — the
   * cap every scenario outcome is clamped to. */
  market_opportunity_meur: number;
  price_spread_eur_mw_year?: number;
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
  { type: "Polygon"; coordinates: Ring[] } | { type: "MultiPolygon"; coordinates: Ring[][] };

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

/** grey (low) -> red (high) opportunity scale */
const lossColor = (t: number) => {
  const x = clamp(t, 0, 1);
  // interpolate light neutral grey -> vivid red
  return `oklch(${0.82 - 0.24 * x} ${0.01 + 0.22 * x} 25)`;
};

export type PlacedUnit = {
  id: string;
  unit_type: string;
  zone_code: string | null;
  border_zone_a: string | null;
  border_zone_b: string | null;
  /** false when the unit belongs to a scenario that is not currently selected */
  active?: boolean;
  scenario_name?: string;
};

export function EuropeMap({
  zones,
  targets,
  selectedId,
  onSelect,
  onClear,
  metric,
  onMetricChange,
  onDropUnit,
  placedUnits = [],
}: {
  zones: ZoneSummary[];
  targets: TargetRow[];
  selectedId: string | null;
  onSelect: (t: TargetRow) => void;
  onClear?: () => void;
  metric: "market" | "climate";
  onMetricChange?: (m: "market" | "climate") => void;
  onDropUnit?: (unitType: UnitType, placement: UnitDropPlacement) => void;
  placedUnits?: PlacedUnit[];
}) {
  const [hover, setHover] = useState<string | null>(null);
  const [view, setView] = useState<View>(IDENTITY);
  const [dragging, setDragging] = useState(false);
  const [dropTarget, setDropTarget] = useState<{ kind: "zone" | "border"; key: string } | null>(
    null,
  );
  const [dropActive, setDropActive] = useState(false);
  const [dropPlacement, setDropPlacement] = useState<"zone" | "border">("zone");

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
    const matrix = el.getScreenCTM();
    if (!matrix) return { x: 0, y: 0 };
    // Invert the SVG viewport transform, including aspect-ratio letterboxing.
    // Bounding-box ratios misplace drops on narrow or tall maps.
    const point = el.createSVGPoint();
    point.x = clientX;
    point.y = clientY;
    return point.matrixTransform(matrix.inverse());
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
    dragRef.current = { x: e.clientX, y: e.clientY, moved: false };
    setDragging(true);
  };

  const onPointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const d = dragRef.current;
    if (!d) return;
    const el = svgRef.current;
    if (!el) return;
    const previous = toViewBox(d.x, d.y);
    const current = toViewBox(e.clientX, e.clientY);
    const dx = current.x - previous.x;
    const dy = current.y - previous.y;
    if (!d.moved && Math.abs(e.clientX - d.x) + Math.abs(e.clientY - d.y) > 3) {
      // capture only once this is a real drag, so plain clicks still reach the borders
      d.moved = true;
      e.currentTarget.setPointerCapture(e.pointerId);
    }
    d.x = e.clientX;
    d.y = e.clientY;
    if (d.moved) setView((v) => ({ ...v, x: v.x + dx, y: v.y + dy }));
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

  /** distance from point to segment, in world (untransformed) coordinates */
  const distToSeg = (px: number, py: number, x1: number, y1: number, x2: number, y2: number) => {
    const dx = x2 - x1;
    const dy = y2 - y1;
    const len2 = dx * dx + dy * dy || 1;
    const t = clamp(((px - x1) * dx + (py - y1) * dy) / len2, 0, 1);
    return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy));
  };

  /** only the endpoints / lines of eligible connections can receive a unit */
  const eligibleBorders = useMemo(() => {
    const sel = targets.find((t) => t.id === selectedId);
    return sel ? [sel] : targets;
  }, [targets, selectedId]);

  const eligibleZones = useMemo(() => {
    const s = new Set<string>();
    for (const t of eligibleBorders) {
      s.add(t.zone_a);
      s.add(t.zone_b);
    }
    return s;
  }, [eligibleBorders]);

  /** icons for the units already placed in the scenarios of this target */
  const unitMarkers = useMemo(() => {
    const byCode = new Map(zones.map((z) => [z.code, z]));
    const seen = new Map<string, number>();
    const out: Array<{
      id: string;
      x: number;
      y: number;
      off: number;
      type: string;
      active: boolean;
      label: string;
    }> = [];
    for (const u of placedUnits) {
      let base: [number, number] | null = null;
      let where = "";
      if (u.zone_code) {
        const z = byCode.get(u.zone_code);
        if (z) {
          base = project(z.lon, z.lat);
          where = u.zone_code;
        }
      } else if (u.border_zone_a && u.border_zone_b) {
        const a = byCode.get(u.border_zone_a);
        const b = byCode.get(u.border_zone_b);
        if (a && b) {
          const [ax, ay] = project(a.lon, a.lat);
          const [bx, by] = project(b.lon, b.lat);
          base = [(ax + bx) / 2, (ay + by) / 2];
          where = `${u.border_zone_a}–${u.border_zone_b}`;
        }
      }
      if (!base) continue;
      const key = where;
      const n = seen.get(key) ?? 0;
      seen.set(key, n + 1);
      const def = unitDef(u.unit_type);
      out.push({
        id: u.id,
        x: base[0],
        y: base[1],
        off: n,
        type: u.unit_type,
        active: u.active !== false,
        label: `${def.label} — ${where}${u.scenario_name ? ` · ${u.scenario_name}` : ""}`,
      });
    }
    return out;
  }, [placedUnits, zones]);

  /** find the zone or border under a client point, depending on the dragged unit's placement */
  const locateDrop = useCallback(
    (clientX: number, clientY: number, placement: "zone" | "border") => {
      const p = toViewBox(clientX, clientY);
      const v = viewRef.current;
      const wx = (p.x - v.x) / v.k;
      const wy = (p.y - v.y) / v.k;
      if (placement === "zone") {
        let best: ZoneSummary | null = null;
        let bd = 70;
        for (const z of zones) {
          if (!eligibleZones.has(z.code)) continue;
          const [x, y] = project(z.lon, z.lat);
          const d = Math.hypot(x - wx, y - wy);
          if (d < bd) {
            bd = d;
            best = z;
          }
        }
        return best
          ? { kind: "zone" as const, key: best.code, placement: { zoneCode: best.code } }
          : null;
      }
      let best: TargetRow | null = null;
      let bd = 30;
      for (const t of eligibleBorders) {
        const [x1, y1] = project(t.a_lon, t.a_lat);
        const [x2, y2] = project(t.b_lon, t.b_lat);
        const d = distToSeg(wx, wy, x1, y1, x2, y2);
        if (d < bd) {
          bd = d;
          best = t;
        }
      }
      return best
        ? {
            kind: "border" as const,
            key: best.id,
            placement: { zoneA: best.zone_a, zoneB: best.zone_b },
          }
        : null;
    },
    [zones, eligibleZones, eligibleBorders, toViewBox],
  );

  const onUnitDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    const type = unitDrag.current;
    if (!type || !onDropUnit) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
    setDropActive(true);
    setDropPlacement(unitDef(type).placement);
    setDropTarget(locateDrop(e.clientX, e.clientY, unitDef(type).placement));
  };

  const onUnitDrop = (e: React.DragEvent<HTMLDivElement>) => {
    const type = (e.dataTransfer.getData("text/unit") || unitDrag.current) as UnitType | "";
    setDropActive(false);
    setDropTarget(null);
    if (!type || !onDropUnit) return;
    e.preventDefault();
    const hit = locateDrop(e.clientX, e.clientY, unitDef(type).placement);
    if (hit) onDropUnit(type, hit.placement);
  };

  const endUnitDrag = () => {
    setDropActive(false);
    setDropTarget(null);
  };

  // reset drop visuals if the drag ends anywhere outside the map
  useEffect(() => {
    window.addEventListener("dragend", endUnitDrag);
    window.addEventListener("drop", endUnitDrag);
    return () => {
      window.removeEventListener("dragend", endUnitDrag);
      window.removeEventListener("drop", endUnitDrag);
    };
  }, []);

  const zoomButton = (factor: number) => {
    stopAnim();
    zoomAt(W / 2, H / 2, factor);
  };

  const corridors = useMemo(() => {
    const grouped = new Map<string, TargetRow[]>();
    for (const target of targets) {
      const key = [target.zone_a, target.zone_b].sort().join("|");
      const members = grouped.get(key) ?? [];
      members.push(target);
      grouped.set(key, members);
    }
    return [...grouped.values()].map((members) => ({
      members,
      target:
        members.find((target) => target.id === selectedId) ??
        [...members].sort((a, b) => b.market_opportunity_meur - a.market_opportunity_meur)[0]!,
      market: Math.max(...members.map((target) => target.price_spread_eur_mw_year ?? 0)),
      climate: members.reduce((sum, target) => sum + target.climate_loss_ktco2, 0),
    }));
  }, [targets, selectedId]);

  /** market opportunity full-red point: the 90th percentile of the positive
   * values (a fixed cap burned most borders fully red; a quantile keeps the
   * scale sensitive to the bulk of candidates while the legend shows the max). */
  const maxLoss = Math.max(
    1,
    ...corridors.map((corridor) => (metric === "market" ? corridor.market : corridor.climate)),
  );
  const positive = corridors
    .map((corridor) => (metric === "market" ? corridor.market : corridor.climate))
    .filter((v) => v > 0)
    .sort((a, b) => a - b);
  const p90 =
    positive.length > 0
      ? positive[Math.min(positive.length - 1, Math.floor(0.9 * positive.length))]!
      : maxLoss;
  const lossCap = metric === "market" ? Math.max(1, Math.min(maxLoss, p90)) : maxLoss;
  const k = view.k;

  return (
    <div
      className={`relative h-full w-full overflow-hidden rounded-xl border bg-card transition-colors ${
        dropActive ? "border-primary/60" : "border-border"
      }`}
      onDragOver={onUnitDragOver}
      onDragLeave={endUnitDrag}
      onDrop={onUnitDrop}
    >
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
          className="fill-transparent"
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

          {/* zone markers */}
          {zones.map((z) => {
            const [x, y] = project(z.lon, z.lat);
            const dim = focusIso ? !focusIso.has(countryOf(z.code)) : false;
            const dropZ = dropTarget?.kind === "zone" && dropTarget.key === z.code;
            const candidate = dropActive && dropPlacement === "zone" && eligibleZones.has(z.code);
            const inactiveDrop = dropActive && !candidate;
            return (
              <g key={z.code}>
                {candidate && (
                  <circle
                    cx={x}
                    cy={y}
                    r={(dropZ ? 16 : 13) / k}
                    fill="var(--color-primary)"
                    fillOpacity={dropZ ? 0.18 : 0.08}
                    stroke="var(--color-primary)"
                    strokeWidth={(dropZ ? 2.5 : 1.5) / k}
                    strokeDasharray={`${4 / k} ${3 / k}`}
                  >
                    <animate
                      attributeName="opacity"
                      values={dropZ ? "1;0.4;1" : "0.9;0.55;0.9"}
                      dur="1s"
                      repeatCount="indefinite"
                    />
                  </circle>
                )}
                <circle
                  cx={x}
                  cy={y}
                  r={(z.hours > 0 ? 9 : 6) / k}
                  fill={candidate ? "var(--color-primary)" : "var(--color-muted-foreground)"}
                  fillOpacity={
                    inactiveDrop ? 0.15 : dim ? 0.2 : candidate ? 1 : z.hours > 0 ? 0.9 : 0.35
                  }

                  stroke="var(--color-card)"
                  strokeWidth={1.5 / k}
                >
                  <title>
                    {z.name} ({z.code})
                    {z.avg_price != null ? ` — ${z.avg_price.toFixed(1)} EUR/MWh` : ""}
                    {z.avg_carbon_intensity != null
                      ? `, ${Math.round(z.avg_carbon_intensity)} gCO2/kWh`
                      : ""}
                  </title>
                </circle>
                <text
                  x={x}
                  y={y + 16 / k}
                  textAnchor="middle"
                  dominantBaseline="hanging"
                  fontSize={9 / k}
                  fontWeight={600}
                  fill="var(--color-muted-foreground)"
                  style={{ pointerEvents: "none" }}
                >
                  {(z.country_code || countryOf(z.code)).toUpperCase()}
                </text>
              </g>
            );
          })}

          {/* target borders, coloured grey (low) to red (high) by yearly market opportunity */}
          {corridors.map((corridor) => {
            const t = corridor.target;
            const [x1, y1] = project(t.a_lon, t.a_lat);
            const [x2, y2] = project(t.b_lon, t.b_lat);
            const v = metric === "market" ? corridor.market : corridor.climate;
            const c = Math.min(1, Math.max(0, v / lossCap));
            const isSelected = selectedId === t.id;
            const dropB = dropTarget?.kind === "border" && dropTarget.key === t.id;
            const candidateB =
              dropActive &&
              dropPlacement === "border" &&
              eligibleBorders.some((b) => b.id === t.id);
            const active = isSelected || hover === t.id || dropB || candidateB;
            const faded =
              (dropActive && !candidateB) || (selectedId != null && !isSelected && !dropB);
            return (
              <g
                key={[t.zone_a, t.zone_b].sort().join("|")}
                data-corridor={[t.zone_a, t.zone_b].sort().join("|")}
                role="button"
                tabIndex={0}
                aria-label={`Select ${t.zone_a} – ${t.zone_b} corridor, ${corridor.market.toFixed(0)} €/MW-year accumulated price spread`}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelect(t);
                  }
                }}
                className="cursor-pointer"
                onClick={() => {
                  if (!wasDrag()) onSelect(t);
                }}
                onMouseEnter={() => setHover(t.id)}
                onMouseLeave={() => setHover(null)}
              >
                <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="transparent" strokeWidth={12 / k} />
                {candidateB && (
                  <line
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke="var(--color-primary)"
                    strokeOpacity={0.3}
                    strokeWidth={(dropB ? 14 : 10) / k}
                    strokeLinecap="round"
                  >
                    <animate
                      attributeName="stroke-opacity"
                      values="0.45;0.15;0.45"
                      dur="1s"
                      repeatCount="indefinite"
                    />
                  </line>
                )}
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
                        : lossColor(c)
                  }
                  strokeOpacity={faded ? 0.25 : active ? 1 : 0.9}
                  strokeWidth={(active ? 5 : 3) / k}
                  strokeLinecap="round"
                />

                <title>
                  {t.zone_a} – {t.zone_b}: {corridor.market.toFixed(0)} €/MW-year accumulated
                  absolute price spread, {corridor.climate.toFixed(1)} ktCO2/y climate proxy. Sum of
                  both directions.
                </title>
              </g>
            );
          })}

          {/* units placed in this target's scenarios */}
          {unitMarkers.map((m) => {
            const Icon = unitIcon(m.type);
            const s = 1 / k;
            return (
              <g
                key={m.id}
                transform={`translate(${m.x + (m.off * 22) / k} ${m.y - 22 / k})`}
                opacity={m.active ? 1 : 0.35}
              >
                <circle
                  r={12 * s}
                  fill="var(--color-card)"
                  stroke={m.active ? "var(--color-primary)" : "var(--color-border)"}
                  strokeWidth={1.5 * s}
                />
                <g transform={`translate(${-7 * s} ${-7 * s}) scale(${(14 * s) / 24})`}>
                  <Icon
                    width={24}
                    height={24}
                    color={m.active ? "var(--color-primary)" : "var(--color-muted-foreground)"}
                    strokeWidth={2}
                  />
                </g>
                <title>{m.label}</title>
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
            ? "Accumulated absolute price spread · 2025"
            : "Yearly climate proxy (est.)"}
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

      <div className="pointer-events-none absolute bottom-3 left-3 max-w-[calc(100%-1.5rem)] rounded-lg border border-border bg-card/90 px-3 py-2 text-xs text-muted-foreground backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="font-medium text-foreground">
            {metric === "market" ? "Price spread (€/MW-year)" : "Climate proxy (est., ktCO2/y)"}
          </span>
          <div className="pointer-events-auto flex rounded-md border border-border p-0.5 text-[10px]">
            {(["market", "climate"] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => onMetricChange?.(m)}
                className={`rounded px-1.5 py-0.5 ${
                  metric === m ? "bg-primary text-primary-foreground" : "text-muted-foreground"
                }`}
              >
                {m === "market" ? "Price spread" : "Climate"}
              </button>
            ))}
          </div>
        </div>
        <div
          className="mt-1.5 h-2 w-48 rounded-full"
          style={{
            background: `linear-gradient(to right, ${lossColor(0)}, ${lossColor(0.5)}, ${lossColor(1)})`,
          }}
        />
        <div className="mt-0.5 flex w-48 justify-between text-[10px]">
          <span>0</span>
          <span>
            {lossCap.toFixed(0)}
            {maxLoss > lossCap ? "+" : ""}
          </span>
        </div>
        <div className="mt-1">Click a border to zoom in on it. Scroll to zoom, drag to pan.</div>
      </div>

      {dropActive && (
        <div className="pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full border border-primary/50 bg-card/95 px-4 py-1.5 text-xs font-medium text-foreground shadow backdrop-blur">
          {unitDrag.current && unitDef(unitDrag.current).placement === "border"
            ? "Drop the line on a highlighted border"
            : "Drop the unit on a country"}
          {dropTarget ? " — release to place" : ""}
        </div>
      )}
    </div>
  );
}
