import { useEffect, useState } from "react";

type Border = {
  id: string;
  a: string;
  b: string;
  status: string;
  opportunity_meur: number | null;
  modelled_opportunity_meur: number | null;
  modelled_climate_opportunity_tonnes?: number | null;
  baseline_rent_meur?: number | null;
  mean_abs_spread_eur_mwh?: number | null;
  marginal_value_eur_mw?: number | null;
};
type Dataset = {
  status: string;
  start: string;
  end_exclusive: string;
  additional_mw: number | null;
  nodes: { id: string; x: number; y: number }[];
  targets: Border[];
};

export function BorderOpportunityNetwork() {
  const [data, setData] = useState<Dataset | null>(null);
  const [error, setError] = useState(false);
  const [experimental, setExperimental] = useState(false);
  const [selected, setSelected] = useState<Border | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    fetch("/research/pypsa-targets.json", { signal: controller.signal })
      .then((r) => {
        if (!r.ok) throw new Error("Dataset unavailable");
        return r.json();
      })
      .then(setData)
      .catch((e) => {
        if (e.name !== "AbortError") setError(true);
      });
    return () => controller.abort();
  }, []);
  const value = (row: Border) =>
    experimental ? (row.modelled_opportunity_meur ?? row.baseline_rent_meur) : row.opportunity_meur;
  const maximum = Math.max(0, ...(data?.targets.map((t) => value(t) ?? 0) ?? []));
  const nodes = new Map(data?.nodes.map((n) => [n.id, n]));
  const project = (id: string) => {
    const n = nodes.get(id);
    return n ? { x: 45 + ((n.x + 12) / 48) * 750, y: 540 - ((n.y - 34) / 38) * 510 } : null;
  };
  const color = (v: number | null | undefined) =>
    v == null ? "#94a3b8" : `hsl(${220 - (maximum ? v / maximum : 0) * 190} 80% 46%)`;
  return (
    <section className="my-8 rounded-xl border p-5" aria-label="Border market opportunity">
      <h2 className="text-2xl font-semibold">European border opportunities</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        {data
          ? `${data.start.slice(0, 10)} to ${data.end_exclusive.slice(0, 10)} (end exclusive)`
          : "Period pending"}{" "}
        ·{" "}
        {data?.additional_mw
          ? `System operating-cost savings from ${data.additional_mw} MW of added border allowance. Each border is tested independently; benefits cannot be added together.`
          : "Baseline congestion rent (|price gap| × actual flow) per border. Diagnostics only, not validated system benefits."}
      </p>
      {error ? (
        <p role="status" className="mt-4">
          The PyPSA-Eur dataset is not available yet.
        </p>
      ) : !data ? (
        <p role="status" className="mt-4">
          Loading European network…
        </p>
      ) : (
        <>
          <label className="mt-4 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={experimental}
              onChange={(e) => setExperimental(e.target.checked)}
            />
            Show experimental estimates (not validated)
          </label>
          <p className="mt-2 text-sm text-muted-foreground">
            {data.targets.length} connected country pairs ·{" "}
            {data.targets.filter((t) => t.opportunity_meur != null).length} validated · Grey means
            unavailable, not zero. Blue to orange indicates increasing opportunity.
          </p>
          {data.nodes.length > 0 ? (
            <svg
              viewBox="0 0 850 580"
              className="mt-4 max-h-[580px] w-full"
              role="group"
              aria-label="Select a country connection to inspect its opportunity"
            >
              {data.targets.map((t) => {
                const a = project(t.a),
                  b = project(t.b);
                if (!a || !b) return null;
                const v = value(t);
                return (
                  <g
                    key={t.id}
                    role="button"
                    tabIndex={0}
                    aria-label={`${t.id}: ${v == null ? "unavailable" : `${v.toFixed(3)} million euros`}`}
                    onClick={() => setSelected(t)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        setSelected(t);
                      }
                    }}
                    className="cursor-pointer"
                  >
                    <title>
                      {t.id}:{" "}
                      {v == null ? "Unavailable" : `€${v.toFixed(3)}m over the modelled window`}
                    </title>
                    <line
                      x1={a.x}
                      y1={a.y}
                      x2={b.x}
                      y2={b.y}
                      stroke="transparent"
                      strokeWidth={16}
                    />
                    <line
                      x1={a.x}
                      y1={a.y}
                      x2={b.x}
                      y2={b.y}
                      stroke={color(v)}
                      strokeWidth={selected?.id === t.id ? 6 : 3}
                      strokeDasharray={v == null ? "5 4" : undefined}
                    />
                  </g>
                );
              })}
              {data.nodes.map((n) => {
                const p = project(n.id)!;
                return (
                  <g key={n.id} pointerEvents="none">
                    <circle cx={p.x} cy={p.y} r={6} fill="currentColor" />
                    <text x={p.x + 9} y={p.y - 7} fontSize={13} fill="currentColor">
                      {n.id}
                    </text>
                  </g>
                );
              })}
            </svg>
          ) : (
            <p className="my-6">
              European topology is being prepared. No opportunity values have been published.
            </p>
          )}
          <p className="text-sm" aria-live="polite">
            {selected
              ? `${selected.id}: ${value(selected) == null ? "Estimate unavailable" : `€${value(selected)!.toFixed(3)} million over the modelled window`} · ${selected.status.replaceAll("_", " ")}`
              : "Select a connection to inspect its result."}
          </p>
          <details className="mt-4 text-sm">
            <summary className="cursor-pointer">All borders and exact values</summary>
            <div className="max-h-72 overflow-auto">
              <table className="mt-3 w-full text-left">
                <thead>
                  <tr>
                    <th>Border</th>
                    <th>€m / period</th>
                    <th>CO₂ avoided (tonnes)</th>
                    {experimental && <th>Spread €/MWh</th>}
                    {experimental && <th>Marginal value €/MW</th>}
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.targets.map((t) => (
                    <tr key={t.id}>
                      <td>{t.id}</td>
                      <td>{value(t)?.toFixed(3) ?? "Unavailable"}</td>
                      <td>
                        {experimental
                          ? (t.modelled_climate_opportunity_tonnes?.toFixed(0) ?? "Unavailable")
                          : "Not validated"}
                      </td>
                      {experimental && (
                        <td>{t.mean_abs_spread_eur_mwh?.toFixed(2) ?? "Unavailable"}</td>
                      )}
                      {experimental && (
                        <td>{t.marginal_value_eur_mw?.toFixed(0) ?? "Unavailable"}</td>
                      )}
                      <td>{t.status.replaceAll("_", " ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
          <p className="mt-3 text-xs text-muted-foreground">
            {data?.additional_mw
              ? `Colour range: €0m–€${maximum.toFixed(3)}m per modelled period.`
              : `Colour range: €0m–€${maximum.toFixed(3)}m baseline rent per window.`}{" "}
            Country positions are schematic. This is diagnostic evidence, not the engineering design
            or profit of a new line.
          </p>
        </>
      )}
    </section>
  );
}
