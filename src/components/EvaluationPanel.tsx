import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { listScenarios, getValidation } from "@/lib/scenarios.functions";
import type { TargetRow } from "./EuropeMap";
import { Button } from "@/components/ui/button";
import { ScenarioReport } from "./ScenarioReport";

const LABELS: Record<string, string> = {
  b1_socio_economic_welfare_meur_y: "B1 Socio-economic welfare (MEUR/y)",
  b2_co2_variation_ktco2_y: "B2 Climate proxy (est., ktCO2/y)",
  b3_res_integration_gwh_y: "B3 RES integration (GWh/y)",
  b4_losses_variation_gwh_y: "B4 Grid losses variation (GWh/y)",
  b5_security_of_supply_congested_hours_avoided: "B5 Security of supply (congested hours avoided)",
  b6_flexibility_avg_spread_reduction_eur_mwh: "B6 Flexibility (avg spread reduction, EUR/MWh)",
  b7_transfer_capability_mwh_y: "B7 Transfer capability (MWh/y)",
  b8_congestion_rent_variation_meur_y: "B8 Congestion rent variation (MEUR/y)",
  b9_price_convergence_hours_gained: "B9 Price convergence hours gained",
  c1_capex_meur: "C1 Capital cost (MEUR)",
  c2_delivery_months: "C2 Delivery time (months)",
  npv_25y_meur: "25-year undiscounted benefit minus capex (MEUR)",
  benefit_cost_ratio: "Benefit / cost ratio",
  simple_payback_years: "Simple payback (years)",
};

export function EvaluationPanel({
  target,
  selectedScenarioId,
}: {
  target: TargetRow | null;
  selectedScenarioId: string | null;
}) {
  const list = listScenarios;
  const validationFn = getValidation;
  const [expanded, setExpanded] = useState<string | null>(null);
  const [reportId, setReportId] = useState<string | null>(null);

  const scenarios = useQuery({
    queryKey: ["scenarios", target?.id],
    queryFn: () => list({ data: { targetId: target!.id } }),
    enabled: !!target,
  });
  const validation = useQuery({ queryKey: ["validation"], queryFn: () => validationFn() });

  const rows = (scenarios.data ?? []).filter((s) => s.result && !s.is_template);
  const reportScenario = rows.find((s) => s.id === reportId) ?? null;

  return (
    <section className="flex h-full w-full flex-col border-l border-border bg-card">
      <div className="border-b border-border p-4">
        <h2 className="text-sm font-semibold">Evaluation</h2>
        <p className="text-xs text-muted-foreground">
          Screening estimates with CBA-inspired indicators. Climate is an unsigned average-mix
          proxy, not avoided emissions.
        </p>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {!target && (
          <p className="text-sm text-muted-foreground">Select a target to see evaluations.</p>
        )}
        {target && rows.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No simulated scenarios yet. Build one on the left and press play.
          </p>
        )}

        {rows.map((s) => {
          const r = s.result!;
          const ind = (r.entsoe_indicators ?? {}) as Record<string, number | string | null>;
          const isOpen = expanded === s.id;
          return (
            <article
              key={s.id}
              className={`rounded-lg border p-3 ${
                selectedScenarioId === s.id ? "border-primary/60" : "border-border"
              }`}
            >
              <header className="flex items-center justify-between">
                <h3 className="text-sm font-medium">{s.name}</h3>
                <Button size="sm" variant="ghost" onClick={() => setReportId(s.id)}>
                  Report
                </Button>
              </header>
              <div className="mt-2 grid grid-cols-2 gap-2">
                <Kpi
                  label="Market opportunity"
                  value={`${r.market_opportunity_meur.toFixed(1)}`}
                  unit="MEUR / year"
                  positive={r.market_opportunity_meur > 0}
                />
                <Kpi
                  label="Climate proxy (est.)"
                  value={`${r.climate_opportunity_ktco2.toFixed(1)}`}
                  unit="ktCO2 / year"
                  positive={r.climate_opportunity_ktco2 > 0}
                />
              </div>
              <button
                className="mt-2 text-xs font-medium text-primary underline-offset-2 hover:underline"
                onClick={() => setExpanded(isOpen ? null : s.id)}
              >
                {isOpen ? "Hide" : "Show"} ENTSO-E evaluation
              </button>
              {isOpen && (
                <dl className="mt-2 space-y-1">
                  {Object.entries(LABELS).map(([key, label]) =>
                    ind[key] === undefined ? null : (
                      <div key={key} className="flex justify-between gap-2 text-xs">
                        <dt className="text-muted-foreground">{label}</dt>
                        <dd className="font-medium">
                          {ind[key] === null ? "—" : String(ind[key])}
                        </dd>
                      </div>
                    ),
                  )}
                  <p className="pt-2 text-[11px] text-muted-foreground">{ind["methodology"]}</p>
                </dl>
              )}
            </article>
          );
        })}
      </div>

      {validation.data && (
        <div className="border-t border-border p-4 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-semibold">Screening data availability</span>
            <span className={validation.data.passed ? "text-emerald-600" : "text-destructive"}>
              {validation.data.passed ? "Available" : "Check"}
            </span>
          </div>
          <p className="mt-1 text-muted-foreground">
            This check is not model validation. See Research for the separate pilot gates.
          </p>
          <ul className="mt-1 space-y-0.5 text-muted-foreground">
            {Object.entries(validation.data.metrics as Record<string, number>).map(([k, v]) => (
              <li key={k} className="flex justify-between gap-3">
                <span>{k.replace(/_/g, " ")}</span>
                <span className="max-w-[65%] break-words text-right font-medium text-foreground">
                  {String(v)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {reportScenario && target && (
        <ScenarioReport
          target={target}
          scenario={reportScenario}
          onClose={() => setReportId(null)}
        />
      )}
    </section>
  );
}

function Kpi({
  label,
  value,
  unit,
  positive,
}: {
  label: string;
  value: string;
  unit: string;
  positive: boolean;
}) {
  return (
    <div className="rounded-md bg-muted p-2">
      <div className="text-[11px] text-muted-foreground">{label}</div>
      <div className={`text-lg font-semibold ${positive ? "text-emerald-600" : "text-foreground"}`}>
        {value}
      </div>
      <div className="text-[11px] text-muted-foreground">{unit}</div>
    </div>
  );
}
