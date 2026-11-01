import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

type Case = {
  name: string;
  kind: "none" | "generator" | "link";
  focus_zone: string;
  model_offer_cost_reduction_meur: number;
  focus_price_mean_change_eur_mwh: number;
  focus_price_up_hours: number;
  focus_price_down_hours: number;
  generator_income_meur: number | null;
  link_signed_rent_meur: number | null;
  technology?: string;
  capacity_mw?: number;
  factor?: number;
};
type Pilot = {
  status: string;
  year: number;
  baseline: string;
  zones: number;
  hours: number;
  limitations: string;
  scenarios: Case[];
};
const base = import.meta.env.BASE_URL;

function title(row: Case) {
  if (row.kind === "generator")
    return `DE-LU ${row.technology === "solar" ? "solar" : "onshore wind"} +${row.capacity_mw?.toLocaleString()} MW`;
  if (row.kind === "link") return `NO2–GB link envelope ×${row.factor}`;
  return "Unchanged baseline";
}

export const Route = createFileRoute("/network-scenarios")({
  head: () => ({ meta: [{ title: "European network scenario pilot | Grid Conductor" }] }),
  component: NetworkScenarios,
});

function NetworkScenarios() {
  const [selected, setSelected] = useState("gen-solar-DE-LU-1000");
  const { data, isPending, error } = useQuery({
    queryKey: ["network-scenario-pilot-2025"],
    queryFn: async (): Promise<Pilot> => {
      const response = await fetch(`${base}research/network-scenario-pilot-2025.json`);
      if (!response.ok) throw new Error("Network pilot data could not be loaded.");
      const pilot = (await response.json()) as Pilot;
      if (
        pilot.status !== "saved_research_pilot_not_general_scenario_estimator" ||
        pilot.scenarios.length !== 10 ||
        pilot.hours !== 8760
      )
        throw new Error("Network pilot data did not pass its publication shape check.");
      return pilot;
    },
  });
  const row = data?.scenarios.find((item) => item.name === selected) ?? data?.scenarios[1];
  return (
    <main className="mx-auto max-w-5xl px-5 py-8">
      <nav className="mb-6 flex gap-5 text-sm">
        <Link to="/" className="underline">
          Workbench
        </Link>
        <Link to="/docs" className="underline">
          Docs
        </Link>
      </nav>
      <h1 className="text-3xl font-bold">European network scenario pilot</h1>
      <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">
        Saved full-year 2025 comparisons on the {data?.zones ?? 48}-zone joint dispatch model. Each
        declared investment was cleared for all 8,760 hours against the same fitted-bid baseline.
        Choose one of the evaluated cases to inspect its modeled response.
      </p>
      {isPending && <p className="mt-6">Loading verified pilot results…</p>}
      {error && (
        <p role="alert" className="mt-6 text-destructive">
          {error.message}
        </p>
      )}
      {data && row && (
        <>
          <div className="mt-6 rounded-xl border border-border bg-card p-5">
            <label htmlFor="network-case" className="block text-sm font-medium">
              Evaluated investment
            </label>
            <select
              id="network-case"
              value={row.name}
              onChange={(event) => setSelected(event.target.value)}
              className="mt-2 w-full rounded-md border border-border bg-background p-2 text-sm"
            >
              {data.scenarios
                .filter((item) => item.kind !== "none")
                .map((item) => (
                  <option key={item.name} value={item.name}>
                    {title(item)}
                  </option>
                ))}
            </select>
            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              <Metric
                label="Modeled offer-cost reduction"
                value={`${row.model_offer_cost_reduction_meur.toFixed(2)} M€ / year`}
              />
              <Metric
                label={`Mean ${row.focus_zone} price change`}
                value={`${row.focus_price_mean_change_eur_mwh >= 0 ? "+" : ""}${row.focus_price_mean_change_eur_mwh.toFixed(2)} €/MWh`}
              />
              <Metric
                label={
                  row.kind === "generator"
                    ? "Added generator income"
                    : "Signed link congestion rent"
                }
                value={`${(row.generator_income_meur ?? row.link_signed_rent_meur ?? 0).toFixed(2)} M€ / year`}
              />
            </div>
            <p className="mt-4 text-sm text-muted-foreground">
              {row.focus_zone} price rose in {row.focus_price_up_hours.toLocaleString()} hours and
              fell in {row.focus_price_down_hours.toLocaleString()} hours. These are modeled prices
              under this fixed scenario, not observed ENTSO-E prices.
            </p>
          </div>
          <div className="mt-7 rounded-xl border border-border bg-card p-5">
            <h2 className="text-xl font-semibold">What changes at the bid curve?</h2>
            {row.name === "gen-solar-DE-LU-1000" ? (
              <>
                <img
                  src={`${base}research/compact-solar-bid-curves-2025.png`}
                  alt="DE-LU offer stacks before and after a 1 GW solar addition, alongside one day's modeled zonal prices"
                  className="mt-4 w-full"
                />
                <p className="mt-3 text-sm text-muted-foreground">
                  At the illustrated hour, 533 MW of new zero-bid solar replaces 533 MW of existing
                  DE-LU dispatch; the coupled network price changes from €79.95 to €78.85/MWh. The
                  local offer stack alone does not set that price.
                </p>
              </>
            ) : (
              <p className="mt-3 text-sm text-muted-foreground">
                The figure below illustrates the 1 GW solar case. For this selected case, the
                full-year metrics above come from its own saved joint-LP replay; no bid-curve figure
                has yet been prepared for it.
              </p>
            )}
            {row.name !== "gen-solar-DE-LU-1000" && (
              <img
                src={`${base}research/compact-solar-bid-curves-2025.png`}
                alt="Illustration for the separate 1 GW DE-LU solar case"
                className="mt-4 w-full"
              />
            )}
          </div>
          <p className="mt-6 max-w-4xl text-sm leading-6 text-muted-foreground">
            {data.limitations} The ten cases passed the retained LP's optimality, balance and
            no-emergency checks. Results are precomputed: changing the selection reads a different
            saved case and does not solve a new investment. The existing workbench's arbitrary line
            and battery screen remains a separate two-zone calculation.
          </p>
          <p className="mt-3 text-sm">
            <a className="underline" href={`${base}research/network-scenario-pilot-2025.json`}>
              Download pilot results (JSON)
            </a>
          </p>
        </>
      )}
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-muted p-4">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 text-lg font-semibold">{value}</div>
    </div>
  );
}
