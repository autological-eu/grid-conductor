import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";

export const Route = createFileRoute("/targets")({
  head: () => ({ meta: [{ title: "European target evidence | Grid Conductor" }] }),
  component: Targets,
});

type Event = {
  start: string;
  end_exclusive: string;
  direction: string;
  hours: number;
  mean_spread_eur_mwh: number;
  carbon_hours: number;
  joint_hours: number;
};
type Target = {
  id: string;
  a: string;
  b: string;
  name_a: string;
  name_b: string;
  rank: number | null;
  status: string;
  eligible_hours: number;
  expected_hours: number;
  coverage: number;
  event_hours: number;
  event_share: number | null;
  mean_event_spread: number | null;
  p95_event_spread: number | null;
  affected_days: number;
  longest_event_hours: number;
  carbon_event_hours: number;
  joint_hours: number;
  excluded_price_units: string[];
  events: Event[];
  topology_source: string;
};
type Report = {
  version: string;
  start: string;
  end_exclusive: string;
  computed_at: string;
  threshold_eur_mwh: number;
  min_price_coverage: number;
  zone_count: number;
  data_source: string;
  targets: Target[];
  limitations: string[];
};
const pct = (n: number | null) => (n == null ? "Unknown" : `${(n * 100).toFixed(1)}%`);
const number = (n: number | null) => (n == null ? "—" : n.toFixed(1));

function Targets() {
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState("");
  const [all, setAll] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch("/research/targets.json", { signal: controller.signal })
      .then((r) => {
        if (!r.ok) throw new Error("Snapshot unavailable");
        return r.json();
      })
      .then(setReport)
      .catch((e) => {
        if (e.name !== "AbortError") setError(true);
      });
    return () => controller.abort();
  }, []);
  const rows =
    report?.targets.filter(
      (t) =>
        (all || t.rank != null) &&
        `${t.a} ${t.b} ${t.name_a} ${t.name_b}`.toLowerCase().includes(search.toLowerCase()),
    ) ?? [];
  return (
    <main className="mx-auto min-h-screen max-w-6xl px-5 py-8">
      <nav className="mb-10 flex flex-wrap gap-5 text-sm">
        <Link to="/" className="underline">
          Workbench
        </Link>
        <Link to="/docs" className="underline">
          Methodology
        </Link>
      </nav>
      <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
        European screening · research snapshot
      </p>
      <h1 className="mt-3 text-4xl font-bold tracking-tight">Where do price gaps persist?</h1>
      <p className="mt-4 max-w-3xl leading-7 text-muted-foreground">
        Inspect recurring price differences and coincident carbon contrasts. These are candidates
        for investigation, not proven grid constraints or quantified investment benefits.
      </p>
      {error && (
        <p role="alert" className="my-8 rounded-lg border p-5">
          The screening snapshot could not be loaded. Reload this page to try again.
        </p>
      )}
      {!report && !error && (
        <p role="status" className="my-8">
          Loading European target evidence…
        </p>
      )}
      {report && (
        <>
          <section
            aria-label="Snapshot coverage"
            className="my-8 rounded-xl border bg-muted/40 p-5 text-sm leading-7"
          >
            <p>
              <strong>
                {report.targets.length} borders · {report.zone_count} zones ·{" "}
                {report.targets.filter((t) => t.rank != null).length} ranked candidates
              </strong>
            </p>
            <p>
              {report.start.slice(0, 10)} to {report.end_exclusive.slice(0, 10)} (exclusive), UTC.
              Historical archive window, not a live feed.
            </p>
            <p>
              Spread threshold: €{report.threshold_eur_mwh}/MWh. Ranking requires{" "}
              {pct(report.min_price_coverage)} matched price coverage.
            </p>
            <p>{report.data_source}</p>
            <p>
              Capacity: not assessed. Connection operation: unverified. Carbon contrast is an
              average-mix indicator, not avoided emissions.
            </p>
            <a className="underline" href="/research/targets.json" download>
              Download full evidence, directions and events (JSON)
            </a>
          </section>
          <div className="mb-6 flex flex-wrap items-center gap-5">
            <label className="flex flex-col gap-2 text-sm">
              Find a zone or country
              <input
                className="rounded-md border bg-background px-3 py-2"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="e.g. France or DK"
              />
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={all} onChange={(e) => setAll(e.target.checked)} />
              Include unranked and missing-data borders
            </label>
            <p aria-live="polite" className="text-sm text-muted-foreground">
              {rows.length} borders shown
            </p>
          </div>
          <p className="mb-5 text-sm text-muted-foreground">
            Sorted by event frequency, then mean event spread. A carbon opportunity hour has a
            cleaner average mix on the cheaper side.
          </p>
          <div className="space-y-4">
            {rows.map((t) => (
              <details key={t.id} className="rounded-xl border bg-card p-5">
                <summary className="cursor-pointer text-lg font-semibold">
                  {t.rank == null ? "Unranked" : `#${t.rank}`} · {t.a} ↔ {t.b}
                  <span className="ml-3 text-sm font-normal text-muted-foreground">
                    {t.name_a} / {t.name_b}
                  </span>
                </summary>
                <dl className="my-5 grid gap-4 text-sm sm:grid-cols-3">
                  {[
                    [
                      "Price coverage",
                      `${t.eligible_hours} / ${t.expected_hours} hours (${pct(t.coverage)})`,
                    ],
                    ["Event frequency", `${t.event_hours} hours · ${pct(t.event_share)}`],
                    [
                      "Event days / longest run",
                      `${t.affected_days} days / ${t.longest_event_hours} hours`,
                    ],
                    [
                      "Mean / p95 event spread",
                      `€${number(t.mean_event_spread)} / €${number(t.p95_event_spread)} per MWh`,
                    ],
                    [
                      "Aligned carbon hours",
                      `${t.joint_hours} / ${t.carbon_event_hours} eligible event hours`,
                    ],
                    ["Data status", t.status.replaceAll("_", " ")],
                  ].map(([label, value]) => (
                    <div key={label}>
                      <dt className="text-muted-foreground">{label}</dt>
                      <dd className="mt-1 font-medium">{value}</dd>
                    </div>
                  ))}
                </dl>
                {t.excluded_price_units.length > 0 && (
                  <p className="mb-4 text-sm">
                    Excluded currencies: {t.excluded_price_units.join(", ")}. No currency conversion
                    applied.
                  </p>
                )}
                <a href={t.topology_source} className="text-sm underline">
                  Connection configuration source ↗
                </a>
                <h2 className="mb-3 mt-5 font-semibold">Spread events (UTC)</h2>
                {!t.events.length ? (
                  <p className="text-sm text-muted-foreground">
                    No qualifying events in comparable data. Check coverage before interpreting this
                    as no opportunity.
                  </p>
                ) : (
                  <div
                    className="overflow-x-auto"
                    tabIndex={0}
                    role="region"
                    aria-label={`${t.a} to ${t.b} events`}
                  >
                    <table className="w-full min-w-[560px] text-left text-sm">
                      <thead>
                        <tr>
                          {[
                            "Start",
                            "Direction",
                            "Hours",
                            "Mean spread",
                            "Aligned / carbon hours",
                          ].map((h) => (
                            <th key={h} scope="col" className="py-3 pr-4">
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {t.events.slice(0, 25).map((e) => (
                          <tr key={e.start} className="border-t">
                            <td className="py-3 pr-4">{e.start.replace("T", " ")}</td>
                            <td>{e.direction}</td>
                            <td>{e.hours}</td>
                            <td>€{number(e.mean_spread_eur_mwh)}</td>
                            <td>
                              {e.joint_hours} / {e.carbon_hours}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {t.events.length > 25 && (
                      <p className="mt-3 text-muted-foreground">
                        First 25 of {t.events.length} events. The download contains every event.
                      </p>
                    )}
                  </div>
                )}
              </details>
            ))}
          </div>
          {!rows.length && <p className="py-10">No borders match these filters.</p>}
          <aside className="mt-10 border-t pt-6 text-sm text-muted-foreground">
            <h2 className="mb-3 font-semibold text-foreground">Coverage and interpretation</h2>
            <ul className="list-disc space-y-2 pl-5">
              {report.limitations.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
            <p className="mt-4">
              Method {report.version} · Computed {report.computed_at.slice(0, 10)}
            </p>
          </aside>
        </>
      )}
    </main>
  );
}
