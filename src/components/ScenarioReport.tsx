import { unitDef } from "@/lib/units";
import type { TargetRow } from "./EuropeMap";
import { Button } from "@/components/ui/button";

type UnitRow = {
  id: string;
  unit_type: string;
  zone_code: string | null;
  border_zone_a: string | null;
  border_zone_b: string | null;
  params: unknown;
  capex_meur: number;
  delivery_months: number;
};

type ScenarioWithResult = {
  id: string;
  name: string;
  description: string | null;
  units: UnitRow[];
  result: {
    market_opportunity_meur: number;
    climate_opportunity_ktco2: number;
    entsoe_indicators: unknown;
    base_metrics: unknown;
    scenario_metrics: unknown;
    hourly_summary: unknown;
    created_at: string;
  } | null;
};

export function ScenarioReport({
  target,
  scenario,
  onClose,
}: {
  target: TargetRow;
  scenario: ScenarioWithResult;
  onClose: () => void;
}) {
  const r = scenario.result;
  if (!r) return null;
  const ind = (r.entsoe_indicators ?? {}) as Record<string, number | string | null>;
  const summary = (r.hourly_summary ?? {}) as Record<string, string | number>;
  const base = (r.base_metrics ?? {}) as Record<string, number>;
  const scen = (r.scenario_metrics ?? {}) as Record<string, number>;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-background/80 p-6 backdrop-blur print:static print:bg-transparent print:p-0">
      <div className="mx-auto max-w-3xl rounded-xl border border-border bg-card p-8 shadow-lg print:border-0 print:shadow-none">
        <div className="flex items-start justify-between print:hidden">
          <h2 className="text-lg font-semibold">Cost-benefit report</h2>
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" onClick={() => window.print()}>
              Print
            </Button>
            <Button size="sm" variant="ghost" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>

        <header className="mt-4 border-b border-border pb-4">
          <h1 className="text-xl font-semibold">
            {scenario.name} — border {target.zone_a} / {target.zone_b}
          </h1>
          <p className="text-sm text-muted-foreground">
            {target.zone_a_name} to {target.zone_b_name}. Assessment period{" "}
            {String(summary["period_start"] ?? "").slice(0, 10)} to{" "}
            {String(summary["period_end"] ?? "").slice(0, 10)}. Prepared{" "}
            {new Date(r.created_at).toISOString().slice(0, 10)}.
          </p>
        </header>

        <Section title="1. Project description">
          <ul className="list-disc pl-5 text-sm">
            {scenario.units.map((u) => {
              const def = unitDef(u.unit_type);
              const p = (u.params ?? {}) as Record<string, number>;
              return (
                <li key={u.id}>
                  <span className="font-medium">{def.label}</span>
                  {u.zone_code ? ` in ${u.zone_code}` : ""}
                  {u.border_zone_a ? ` on ${u.border_zone_a}–${u.border_zone_b}` : ""} —{" "}
                  {Object.entries(p)
                    .map(([k, v]) => `${k.replace(/_/g, " ")}: ${v}`)
                    .join(", ")}
                  . Cost {u.capex_meur} MEUR, delivery {u.delivery_months} months.
                </li>
              );
            })}
            {scenario.units.length === 0 && <li>No units defined.</li>}
          </ul>
        </Section>

        <Section title="2. Problem addressed">
          <p className="text-sm">
            The screening identifies price spreads above its congestion threshold for{" "}
            {target.congested_hours} of {target.total_hours} hours while prices diverged between the
            two zones. The screen estimates a market opportunity of{" "}
            {target.market_opportunity_meur.toFixed(1)} MEUR per year (the bounded deadweight loss a
            capacity project could recover) and {target.climate_loss_ktco2.toFixed(1)} ktCO2 per
            year as an unsigned average-mix climate proxy, not demonstrated avoided emissions.
          </p>
        </Section>

        <Section title="3. Methodology">
          <p className="text-sm">
            {ind["methodology"] ??
              "Experimental reduced-form screening. No dispatch-grade methodology is available for this result."}
          </p>
        </Section>

        <Section title="4. Cost-benefit indicators (ENTSO-E CBA)">
          <table className="w-full text-sm">
            <tbody>
              {Object.entries(ind)
                .filter(([k]) => k !== "methodology")
                .map(([k, v]) => (
                  <tr key={k} className="border-b border-border/60">
                    <td className="py-1 pr-4 text-muted-foreground">{k.replace(/_/g, " ")}</td>
                    <td className="py-1 text-right font-medium">{v === null ? "—" : String(v)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </Section>

        <Section title="5. Modelled results versus baseline">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted-foreground">
                <th className="py-1 font-normal">Metric</th>
                <th className="py-1 text-right font-normal">Baseline</th>
                <th className="py-1 text-right font-normal">With project</th>
              </tr>
            </thead>
            <tbody>
              {Object.keys(base).map((k) => (
                <tr key={k} className="border-b border-border/60">
                  <td className="py-1 pr-4 text-muted-foreground">{k.replace(/_/g, " ")}</td>
                  <td className="py-1 text-right">{String(base[k])}</td>
                  <td className="py-1 text-right font-medium">{String(scen[k])}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>

        <Section title="6. Interpretation">
          <p className="text-sm">
            The screening estimates {r.market_opportunity_meur.toFixed(1)} MEUR per year of
            additional welfare and {r.climate_opportunity_ktco2.toFixed(1)} ktCO2 per year as a
            signed emissions-change proxy (negative = saving, positive = increase; not verified
            avoided emissions), at a capital cost of {String(ind["c1_capex_meur"] ?? "—")} MEUR and
            a delivery time of {String(ind["c2_delivery_months"] ?? "—")} months
            {ind["simple_payback_years"] != null
              ? `, implying a simple payback of ${String(ind["simple_payback_years"])} years`
              : ""}
            .
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            Payback is a screening indicator. The 25-year figure is undiscounted; it does not
            account for changing prices, degradation, financing or project feasibility.
          </p>
        </Section>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-5">
      <h3 className="mb-2 text-sm font-semibold">{title}</h3>
      {children}
    </section>
  );
}
