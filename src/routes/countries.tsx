import { useMemo, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { publicAsset } from "@/lib/research";
import {
  dateWindow,
  generationCsv,
  loadCountry,
  loadManifest,
  plotSeries,
  priceCsv,
  recordCsv,
  saveCsv,
  sourceGenerationCsv,
  technologyTotals,
  type CountryData,
  type ExplorerManifest,
  type PlotPoint,
  type Resolution,
} from "@/lib/country-explorer";

export const Route = createFileRoute("/countries")({
  validateSearch: (search: Record<string, unknown>) => ({
    country: typeof search["country"] === "string" ? search["country"] : "DE",
    start: typeof search["start"] === "string" ? search["start"] : "2025-01-01",
    end: typeof search["end"] === "string" ? search["end"] : "2025-01-07",
    resolution: search["resolution"] === "daily" ? ("daily" as const) : ("hourly" as const),
  }),
  head: () => ({ meta: [{ title: "Country data explorer | Grid Conductor" }] }),
  component: Countries,
});

const field = "mt-1 w-full min-w-0 rounded-lg border border-input bg-background px-3 py-2 text-sm";
const button =
  "rounded-lg border border-input bg-background px-3 py-2 text-sm font-medium hover:bg-muted disabled:opacity-50";
const panel = "min-w-0 rounded-xl border border-border bg-background p-4 sm:p-6";
const number = (value: number | null | undefined, digits = 2) =>
  value === null || value === undefined
    ? "—"
    : value.toLocaleString("en-GB", { maximumFractionDigits: digits });
const monthName = (m: number) =>
  new Date(Date.UTC(2025, m - 1)).toLocaleDateString("en-GB", { month: "short", timeZone: "UTC" });
const timeLabel = (time: number) =>
  new Date(time).toISOString().replace("T", " ").slice(0, 16) + " UTC";

function TimePlot({
  rows,
  unit,
  label,
  resolution,
  observedLabel = "ENTSO-E observed",
}: {
  rows: PlotPoint[];
  unit: string;
  label: string;
  resolution: Resolution;
  observedLabel?: string;
}) {
  return (
    <div className="mt-3 min-w-0" role="img" aria-label={label}>
      <div className="mb-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted-foreground">
        <span>
          <b className="text-blue-600">━</b> {observedLabel}
        </span>
        <span>
          <b className="text-amber-700">━</b> Model
        </span>
        {rows.some((r) => r.interval) && <span>Shading: conditional allocation range</span>}
      </div>
      <div className="h-72 min-w-0 w-full">
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <ComposedChart
            data={rows}
            margin={{ top: 8, right: 12, left: 4, bottom: 8 }}
            accessibilityLayer
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="time"
              type="number"
              domain={["dataMin", "dataMax"]}
              tickFormatter={(t) =>
                new Date(Number(t)).toLocaleDateString("en-GB", {
                  day: "numeric",
                  month: "short",
                  timeZone: "UTC",
                })
              }
              tick={{ fontSize: 11 }}
              minTickGap={55}
            />
            <YAxis width={62} tick={{ fontSize: 11 }} tickFormatter={(v) => number(Number(v), 0)} />
            <Tooltip
              labelFormatter={(v) => timeLabel(Number(v))}
              formatter={(v, name) => [
                Array.isArray(v)
                  ? `${number(Number(v[0]))}–${number(Number(v[1]))} ${unit}`
                  : `${number(Number(v))} ${unit}`,
                name === "observed"
                  ? observedLabel
                  : name === "interval"
                    ? "Conditional range"
                    : "Model",
              ]}
            />
            <Area
              dataKey="interval"
              fill="#f5d6b7"
              stroke="none"
              isAnimationActive={false}
              connectNulls={false}
            />
            <Line
              dataKey="observed"
              stroke="#2563eb"
              strokeWidth={1.5}
              dot={rows.length === 1 ? { r: 3 } : false}
              connectNulls={false}
              isAnimationActive={false}
            />
            <Line
              dataKey="model"
              stroke="#bd641b"
              strokeWidth={1.4}
              dot={rows.length === 1 ? { r: 3 } : false}
              connectNulls={false}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-muted-foreground">
        {resolution === "daily" ? "Daily mean" : "Hourly values"} · {unit} · UTC. Hover or focus the
        chart for values. Gaps mean missing source data.
      </p>
    </div>
  );
}

function Countries() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const manifest = useQuery({
    queryKey: ["country-explorer-manifest-v1"],
    queryFn: ({ signal }) => loadManifest(signal),
    staleTime: Infinity,
  });
  const entry =
    manifest.data?.countries.find((c) => c.code === search.country) ??
    manifest.data?.countries.find((c) => c.code === "DE");
  const country = useQuery({
    queryKey: ["country-explorer-v1", entry?.code, entry?.sha256],
    queryFn: ({ signal }) => loadCountry(entry!, manifest.data!.model.id, signal),
    enabled: !!entry && !!manifest.data,
    staleTime: Infinity,
    gcTime: 60_000,
  });
  const update = (next: Partial<typeof search>) =>
    void navigate({ search: (previous) => ({ ...previous, ...next }) });
  const range = dateWindow(search.start, search.end);
  return (
    <main className="mx-auto max-w-7xl px-4 py-7 sm:px-6">
      <nav className="mb-7 flex flex-wrap gap-5 text-sm">
        <Link to="/">Workbench</Link>
        <Link to="/docs">Docs</Link>
        <Link to="/docs/$slug" params={{ slug: "research-baselines-2025" }}>
          Model report
        </Link>
      </nav>
      <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Country data explorer</h1>
      <p className="mt-3 max-w-3xl leading-7 text-muted-foreground">
        Explore 2025 source generation and day-ahead prices alongside an archived European clearing
        run. This explorer has not yet been updated to the current research baseline.
      </p>
      <div className="my-6 grid grid-cols-2 gap-4 rounded-xl bg-muted/50 p-4 lg:grid-cols-5">
        <label className="col-span-2 text-sm font-medium">
          Country
          <select
            className={field}
            aria-label="Country"
            value={entry?.code ?? "DE"}
            onChange={(e) => update({ country: e.target.value })}
            disabled={!manifest.data}
          >
            {manifest.data?.countries.map((c) => (
              <option key={c.code} value={c.code}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-medium">
          From (UTC)
          <input
            aria-label="From (UTC)"
            className={field}
            type="date"
            min="2025-01-01"
            max="2025-12-31"
            value={search.start}
            onChange={(e) => update({ start: e.target.value })}
          />
        </label>
        <label className="text-sm font-medium">
          Through (UTC)
          <input
            aria-label="Through (UTC)"
            className={field}
            type="date"
            min="2025-01-01"
            max="2025-12-31"
            value={search.end}
            onChange={(e) => update({ end: e.target.value })}
          />
        </label>
        <label className="col-span-2 text-sm font-medium lg:col-span-1">
          Chart detail
          <select
            aria-label="Chart detail"
            className={field}
            value={search.resolution}
            onChange={(e) => update({ resolution: e.target.value as Resolution })}
          >
            <option value="hourly">Hourly</option>
            <option value="daily">Daily mean</option>
          </select>
        </label>
        <div className="col-span-2 flex flex-wrap gap-2 lg:col-span-5">
          <button
            className={button}
            onClick={() => update({ start: "2025-01-01", end: "2025-12-31" })}
          >
            Full year
          </button>
          <span className="self-center text-xs text-muted-foreground">
            {range ? `${number(range[1] - range[0], 0)} UTC hours selected. ` : ""}Date controls
            affect hourly charts. Annual and monthly mix tables always cover the full year.
          </span>
        </div>
      </div>
      {manifest.data && (
        <p className="mb-6 text-sm text-muted-foreground">
          <strong className="text-foreground">{manifest.data.model.label}</strong> · full-year
          Europe MAE €{number(manifest.data.model.mae_eur_mwh)}/MWh · in-sample reconstruction. The
          accepted research baseline and browser scenario engine are unchanged. Non-oil bids retain
          their earlier calibration; observed day-ahead targets have been corrected.
        </p>
      )}
      {!range && (
        <p role="alert" className="mb-6 rounded-lg border border-red-300 p-3">
          Choose valid 2025 dates, with the end on or after the start.
        </p>
      )}
      {(manifest.isPending || country.isPending) && !manifest.isError && (
        <p role="status">Loading {entry?.name ?? "country index"}…</p>
      )}
      {(manifest.isError || country.isError) && (
        <div role="alert" className={panel}>
          <p>{(manifest.error ?? country.error)?.message}</p>
          <button
            className={button + " mt-3"}
            onClick={() => {
              void manifest.refetch();
              void country.refetch();
            }}
          >
            Retry
          </button>
          {entry && (
            <a
              className="ml-4 text-sm underline"
              href={publicAsset(`research/country-explorer-2025/${entry.file}`)}
              download
            >
              Download compressed country data
            </a>
          )}
        </div>
      )}
      {country.data && manifest.data && (
        <CountryView
          key={country.data.country}
          data={country.data}
          manifest={manifest.data}
          range={range}
          resolution={search.resolution}
        />
      )}
    </main>
  );
}

function CountryView({
  data,
  manifest,
  range,
  resolution,
}: {
  data: CountryData;
  manifest: ExplorerManifest;
  range: [number, number] | null;
  resolution: Resolution;
}) {
  const [areaId, setArea] = useState("country:" + data.country);
  const [technology, setTechnology] = useState("onshore_wind");
  const [monthlyFuel, setMonthlyFuel] = useState("Wind");
  const area = data.generation.find((a) => a.id === areaId) ?? data.generation[0]!;
  const ti = manifest.technologies.findIndex((t) => t.id === technology);
  const national = data.generation.find((a) => a.id === "country:" + data.country)!;
  const oilIndex = manifest.technologies.findIndex((t) => t.id === "oil");
  const oil = technologyTotals(
    data.series[national.model[oilIndex]!]!,
    data.series[national.observed[oilIndex]!]!,
    manifest.generation_scale,
  );
  const hourly = useMemo(
    () =>
      range
        ? plotSeries(
            data,
            area.model[ti]!,
            area.observed[ti]!,
            manifest.generation_scale,
            range,
            resolution,
            [area.lower[ti]!, area.upper[ti]!],
          )
        : [],
    [data, area, ti, manifest.generation_scale, range, resolution],
  );
  const mix = manifest.ember_fuels.map((fuel) => {
    const months = data.monthly.filter((r) => r.fuel === fuel);
    const known = months.filter((r) => r.observed_twh !== null);
    return {
      fuel,
      model: months.reduce((s, r) => s + r.model_twh, 0),
      observed: known.length === 12 ? known.reduce((s, r) => s + r.observed_twh!, 0) : null,
      known: known.length,
    };
  });
  const months = data.monthly
    .filter((r) => r.fuel === monthlyFuel)
    .map((r) => ({ ...r, label: monthName(r.month) }));
  return (
    <div className="space-y-8">
      <section className={panel}>
        <h2 className="text-2xl font-semibold">1. {data.name}: generation mix</h2>
        <p className="mt-2 max-w-4xl text-sm leading-6 text-muted-foreground">
          Ember supplies monthly national generation; ENTSO-E supplies hourly generation where
          cached coverage permits. IRENA supplies capacity, shown separately below. Model fuel
          output is an illustrative allocation within equal-offer blocks, rather than uniquely
          identified plant dispatch.
        </p>
        <h3 className="mt-6 font-semibold">Annual generation by fuel</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          TWh in 2025 · observed annual totals require all 12 Ember months. Missing is never zero.
          Oil is included in the model and grouped with waste under “Other fossil” here. See the
          separate oil comparison below; Ember does not identify liquid oil on its own.
        </p>
        <div
          className="mt-4 h-96 min-w-0"
          role="img"
          aria-label="Annual observed and modeled generation mix"
        >
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <BarChart
              data={mix}
              layout="vertical"
              margin={{ top: 5, right: 20, left: 5, bottom: 5 }}
              accessibilityLayer
            >
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="fuel" width={104} tick={{ fontSize: 11 }} />
              <Tooltip
                formatter={(v, name) => [
                  `${number(Number(v), 3)} TWh`,
                  name === "observed" ? "Ember observed" : "Model illustration",
                ]}
              />
              <Legend
                formatter={(name) =>
                  name === "observed" ? "Ember observed" : "Model illustration"
                }
              />
              <Bar dataKey="observed" fill="#2563eb" isAnimationActive={false} />
              <Bar dataKey="model" fill="#bd641b" isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">Annual country generation comparison, TWh</caption>
            <thead>
              <tr className="border-b">
                <th className="p-2">Fuel</th>
                <th className="p-2">Ember TWh</th>
                <th className="p-2">Model TWh</th>
                <th className="p-2">Difference TWh</th>
                <th className="p-2">Source months</th>
              </tr>
            </thead>
            <tbody>
              {mix.map((r) => (
                <tr key={r.fuel} className="border-b border-border/50">
                  <th className="p-2 font-normal">{r.fuel}</th>
                  <td className="p-2">{number(r.observed, 3)}</td>
                  <td className="p-2">{number(r.model, 3)}</td>
                  <td className="p-2">
                    {number(r.observed === null ? null : r.model - r.observed, 3)}
                  </td>
                  <td className="p-2">{r.known}/12</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-6 rounded-lg border border-border p-4">
          <h3 className="font-semibold">Oil generation (ENTSO-E B06)</h3>
          <div className="mt-3 grid gap-4 sm:grid-cols-3">
            <p className="text-sm">
              Full-year model
              <br />
              <strong>{number(oil.annualModel, 3)} TWh</strong>
            </p>
            <p className="text-sm">
              Observed on covered hours
              <br />
              <strong>{number(oil.observed, 3)} TWh</strong>
            </p>
            <p className="text-sm">
              Model on the same hours
              <br />
              <strong>{number(oil.matchedModel, 3)} TWh</strong>
            </p>
          </div>
          <p className="mt-3 text-xs leading-5 text-muted-foreground">
            {number(oil.known, 0)} known hours; partial observations are not annualised. Oil shale,
            peat and waste are separate technologies. This checkpoint includes the audited missing
            PL/SK/SI oil capacity, daily Brent/FX and dated carbon proxies, with an optional
            heat-credit offer for 25% of source-labelled oil CHP capacity. Remaining oil output gaps
            are documented in the model report.
          </p>
          <button
            className={button + " mt-3"}
            onClick={() => {
              setArea("country:" + data.country);
              setTechnology("oil");
            }}
          >
            Inspect hourly oil
          </button>
        </div>
        <div className="mt-7 flex flex-wrap items-end gap-4">
          <label className="text-sm font-medium">
            Monthly national fuel
            <select
              className={field}
              aria-label="Monthly national fuel"
              value={monthlyFuel}
              onChange={(e) => setMonthlyFuel(e.target.value)}
            >
              {manifest.ember_fuels.map((f) => (
                <option key={f}>{f}</option>
              ))}
            </select>
          </label>
          <button
            className={button}
            onClick={() =>
              saveCsv(`${data.country}-ember-original-2025.csv`, recordCsv(data.ember_rows))
            }
          >
            Download original Ember rows
          </button>
        </div>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <caption className="mb-2 text-left text-xs text-muted-foreground">
              {monthlyFuel}: original monthly Ember generation versus modeled output (TWh)
            </caption>
            <thead>
              <tr className="border-b">
                <th className="p-2">Month</th>
                <th className="p-2">Ember</th>
                <th className="p-2">Model</th>
                <th className="p-2">Difference</th>
              </tr>
            </thead>
            <tbody>
              {months.map((r) => (
                <tr key={r.month} className="border-b border-border/50">
                  <th className="p-2 font-normal">{r.label}</th>
                  <td className="p-2">{number(r.observed_twh, 3)}</td>
                  <td className="p-2">{number(r.model_twh, 3)}</td>
                  <td className="p-2">
                    {number(r.observed_twh === null ? null : r.model_twh - r.observed_twh, 3)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <h3 className="mt-8 font-semibold">Hourly generation</h3>
        <div className="mt-3 grid gap-4 sm:grid-cols-2">
          <label className="text-sm font-medium">
            Generation area
            <select
              className={field}
              aria-label="Generation area"
              value={area.id}
              onChange={(e) => setArea(e.target.value)}
            >
              {data.generation.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm font-medium">
            Technology
            <select
              className={field}
              aria-label="Technology"
              value={technology}
              onChange={(e) => setTechnology(e.target.value)}
            >
              {manifest.technologies.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <p className="mt-3 text-sm text-muted-foreground">
          {number(area.observed_hours[ti], 0)} / 8,760 known ENTSO-E hours for{" "}
          {manifest.technologies[ti]?.label}.{" "}
          {area.missing_source_areas.length > 0 &&
            `Missing constituent areas: ${area.missing_source_areas.join(", ")}. Country totals are not filled from partial sums.`}
        </p>
        <p className="mt-2 text-xs leading-5 text-muted-foreground">
          {area.scope_note}{" "}
          {area.source_areas.length
            ? `Source area(s): ${area.source_areas.join(", ")}.`
            : "No comparable hourly source series."}{" "}
          DE national generation excludes LU; FR national generation and the FR/Corsica model scopes
          are not certified identical.
        </p>
        {range && (
          <TimePlot
            rows={hourly}
            resolution={resolution}
            unit="MW"
            label={`${data.name} ${area.label} hourly generation: ${technology}`}
          />
        )}
        <p className="mt-3 text-xs leading-5 text-muted-foreground">
          The shaded range is the conditional technology allocation within saved offer blocks;
          different technologies cannot generally attain all their bounds together. It is not a
          confidence interval. Fixed reservoir output is not adaptive storage. The hourly chart does
          not include pumped-storage output.
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <button
            className={button}
            onClick={() =>
              saveCsv(
                `${data.country}-${area.id.replace(":", "-")}-generation-2025.csv`,
                generationCsv(data, area, manifest),
              )
            }
          >
            Download full-year generation comparison
          </button>
          <button
            className={button}
            onClick={() =>
              saveCsv(
                `${data.country}-entsoe-source-generation-2025.csv`,
                sourceGenerationCsv(data, manifest.generation_scale),
              )
            }
          >
            Download hourly ENTSO-E source data
          </button>
        </div>
        <details className="mt-6 rounded-lg bg-muted/40 p-4">
          <summary className="cursor-pointer font-semibold">
            Original IRENA capacity records · MW, not generation
          </summary>
          <p className="my-3 text-sm text-muted-foreground">
            End-of-year renewable capacity cells and flags from the 2026 release. Parent totals and
            technology subcategories overlap; do not add them together. Only wind/PV use the
            inherited linear end-2024 to end-2025 commissioning assumption in this model.
          </p>
          <a
            className="text-sm underline"
            href={manifest.sources.irena.url}
            target="_blank"
            rel="noreferrer"
          >
            IRENA source PDF
          </a>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b">
                  <th className="p-2">Technology</th>
                  <th className="p-2">End 2024 MW</th>
                  <th className="p-2">End 2025 MW</th>
                  <th className="p-2">Flags 2024 / 2025</th>
                </tr>
              </thead>
              <tbody>
                {data.irena_rows.map((r) => (
                  <tr key={r.technology} className="border-b border-border/50">
                    <th className="p-2 font-normal">{r.technology}</th>
                    <td className="p-2">{number(r.capacity_2024.mw, 3)}</td>
                    <td className="p-2">{number(r.capacity_2025.mw, 3)}</td>
                    <td className="p-2">
                      {r.capacity_2024.source_flag ?? "—"} / {r.capacity_2025.source_flag ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!data.irena_rows.length && (
              <p>No parsed IRENA records for this country; missing capacity is not zero.</p>
            )}
          </div>
          <button
            className={button + " mt-4"}
            onClick={() =>
              saveCsv(
                `${data.country}-irena-capacity-source.csv`,
                recordCsv(
                  data.irena_rows.map((r) => ({
                    country: r.country,
                    provider_area: r.provider_area,
                    technology: r.technology,
                    capacity_2024_mw: r.capacity_2024.mw,
                    flag_2024: r.capacity_2024.source_flag,
                    capacity_2025_mw: r.capacity_2025.mw,
                    flag_2025: r.capacity_2025.source_flag,
                  })),
                ),
              )
            }
          >
            Download IRENA source cells
          </button>
        </details>
        <details className="mt-4 text-sm">
          <summary className="cursor-pointer font-medium">
            Hourly generation source coverage
          </summary>
          <ul className="mt-3 space-y-2 text-muted-foreground">
            {data.source_generation.map((a) => (
              <li key={a.area}>
                <strong>{a.area}</strong>: {a.scope} · {a.provenance.length}/12 replayed source
                months · reported PSR types: {Object.keys(a.psr).join(", ") || "none"}
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-muted-foreground">
            Source CSVs also retain reported pumped-storage and other PSR types, where present.
            Empty cells mean unknown. Hourly observations are published at 0.1 MWh precision; each
            one-hour MWh bin equals mean MW. Original source downloads are linked below.
          </p>
        </details>
      </section>
      <section className={panel}>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h2 className="text-2xl font-semibold">2. Day-ahead prices · all country zones</h2>
          <button
            className={button}
            onClick={() =>
              saveCsv(
                `${data.country}-prices-all-zones-2025.csv`,
                priceCsv(data, manifest.price_scale),
              )
            }
          >
            Download full-year hourly prices
          </button>
        </div>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          ENTSO-E day-ahead and modeled EUR/MWh. Each zone stays separate; shared zones are
          identified. Price metrics below cover the full year, independent of the selected chart
          window.
        </p>
        {data.prices.map((p) => (
          <div key={p.zone} className="mt-7 border-t pt-5" data-price-zone={p.zone}>
            <h3 className="text-lg font-semibold">{p.zone}</h3>
            <p className="mt-1 text-xs text-muted-foreground">{p.scope}</p>
            <p className="mt-2 text-sm">
              MAE €{number(p.mae)}/MWh · bias €{number(p.bias)}/MWh · correlation{" "}
              {number(p.correlation, 3)} · {number(p.known_hours, 0)}/8,760 observed hours
            </p>
            {p.known_hours === 0 && (
              <p className="mt-2 text-sm text-muted-foreground">
                No complete cached observed price series. The model remains visible; missing
                observations are not zero.
              </p>
            )}
            {range && (
              <TimePlot
                rows={plotSeries(
                  data,
                  p.model,
                  p.observed,
                  manifest.price_scale,
                  range,
                  resolution,
                )}
                unit="EUR/MWh"
                observedLabel="ENTSO-E day-ahead"
                resolution={resolution}
                label={`${p.zone} observed and modeled prices`}
              />
            )}
          </div>
        ))}
        {!data.prices.length && (
          <p className="mt-5">No separate modeled commercial price area for this country.</p>
        )}
      </section>
      <section className={panel}>
        <h2 className="text-xl font-semibold">Data and interpretation</h2>
        <ul className="mt-4 space-y-3 text-sm leading-6 text-muted-foreground">
          {manifest.limitations.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>
        <div className="mt-5 flex flex-wrap gap-5 text-sm underline">
          <a href={manifest.sources.ember.url}>Original Ember CSV</a>
          <a href={manifest.sources.irena.url}>IRENA capacity PDF</a>
          <a href={manifest.sources.entsoe.url}>ENTSO-E Transparency Platform</a>
          <a href={publicAsset("research/country-explorer-2025/manifest.json")}>
            Dataset provenance
          </a>
          <Link to="/docs/$slug" params={{ slug: "research-baselines-2025" }}>
            Current research baselines
          </Link>
        </div>
      </section>
    </div>
  );
}
