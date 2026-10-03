import { ProductionCarbonDetails } from "@/components/ProductionCarbonDetails";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, Loader2, Play, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { UNIT_LIBRARY, unitDef, unitDrag, type UnitType } from "@/lib/units";
import { unitIcon } from "@/lib/unitIcons";
import {
  addUnit,
  createScenario,
  deleteScenario,
  deleteUnit,
  listScenarios,
  runScenario,
  updateUnit,
} from "@/lib/scenarios.functions";

import type { TargetRow } from "./EuropeMap";
import { Button } from "@/components/ui/button";
import { PriceSpreadDetails } from "./PriceSpreadDetails";
import { Input } from "@/components/ui/input";

export function TargetSidebar({
  target,
  selectedScenarioId,
  onSelectScenario,
}: {
  target: TargetRow | null;
  selectedScenarioId: string | null;
  onSelectScenario: (id: string | null) => void;
}) {
  const qc = useQueryClient();
  const list = listScenarios;
  const create = createScenario;
  const remove = safely(deleteScenario);
  const add = addUnit;
  const patch = safely(updateUnit);
  const dropUnit = safely(deleteUnit);
  const run = runScenario;

  const [dragOver, setDragOver] = useState<string | null>(null);
  const [open, setOpen] = useState<Record<string, boolean>>({});

  const scenarios = useQuery({
    queryKey: ["scenarios", target?.id],
    queryFn: () => list({ data: { targetId: target!.id } }),
    enabled: !!target,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["scenarios", target?.id] });
    qc.invalidateQueries({ queryKey: ["validation"] });
  };

  const createMut = useMutation({
    mutationFn: () =>
      create({
        data: {
          targetId: target!.id,
          name: `Scenario ${(scenarios.data?.length ?? 0) + 1}`,
        },
      }),
    onSuccess: (s) => {
      invalidate();
      onSelectScenario(s.id);
      setOpen((o) => ({ ...o, [s.id]: true }));
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const runMut = useMutation({
    mutationFn: (id: string) => run({ data: { id } }),
    onSuccess: () => {
      invalidate();
      toast.success("Scenario simulated");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  async function handleDrop(scenarioId: string, unitType: UnitType) {
    if (unitType !== "line" && unitType !== "battery") {
      toast.error("Only lines and batteries are modelled in v1.");
      return;
    }
    const def = unitDef(unitType);
    try {
      await add({
        data: {
          scenarioId,
          unitType,
          zoneCode: def.placement === "zone" ? target!.zone_b : null,
          borderZoneA: def.placement === "border" ? target!.zone_a : null,
          borderZoneB: def.placement === "border" ? target!.zone_b : null,
        },
      });
      invalidate();
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  if (!target) {
    return (
      <aside className="flex h-full w-full flex-col border-r border-border bg-card p-4">
        <h2 className="text-sm font-semibold">Targets</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Pick a highlighted border on the map to open its scenarios.
        </p>
      </aside>
    );
  }

  return (
    <aside className="h-full w-full overflow-y-auto border-r border-border bg-card">
      <div className="border-b border-border p-4">
        <h2 className="text-sm font-semibold">
          {target.zone_a} – {target.zone_b}
        </h2>
        <p className="text-xs text-muted-foreground">
          {target.zone_a_name} to {target.zone_b_name}
        </p>
        <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
          <Stat
            label="Annual congestion rent (floor: 0)"
            value={
              target.congestion_rent_meur_year == null
                ? "Unavailable"
                : `${Math.max(0, target.congestion_rent_meur_year).toFixed(1)} M€`
            }
          />
          <Stat
            label="Mean absolute price spread"
            value={
              target.mean_absolute_spread_eur_mwh == null
                ? "Unavailable"
                : `${target.mean_absolute_spread_eur_mwh.toFixed(2)} €/MWh`
            }
          />
          <Stat
            label="Hours with spread > €5/MWh"
            value={`${target.congested_hours} / ${target.total_hours}`}
          />
          <Stat
            label="Observed capacity"
            value={
              target.observed_capacity_mw ? `${Math.round(target.observed_capacity_mw)} MW` : "—"
            }
          />
        </dl>
        <p className="mt-2 text-xs text-muted-foreground">
          2025 observed baseline. Mean absolute spread over covered hours; rent sums scheduled
          cross-border flow × signed price difference × interval hours in both directions. Negative
          contributions remain in the calculation; only the displayed annual total is floored at
          zero. This is a scheduled-exchange value, not verified TSO income. Source uses ENTSO-E
          scheduled flows, not metered physical flows.
        </p>
        <PriceSpreadDetails key={target.id} a={target.zone_a} b={target.zone_b} />
        <ProductionCarbonDetails a={target.zone_a} b={target.zone_b} />
        <p className="mt-2 text-xs text-muted-foreground">
          Experimental scenario welfare bound: {target.market_opportunity_meur.toFixed(1)} M€/year
          (directional model).
        </p>
      </div>

      <div className="border-b border-border p-4">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Unit library
        </h3>
        <p className="mb-2 text-xs text-muted-foreground">
          Drag onto the map, or click to add to the selected scenario.
        </p>
        <div className="flex flex-wrap gap-2">
          {UNIT_LIBRARY.filter((u) => u.type === "line" || u.type === "battery").map((u) => {
            const Icon = unitIcon(u.type);
            return (
              <div
                key={u.type}
                role="button"
                tabIndex={0}
                onClick={() => {
                  if (selectedScenarioId) void handleDrop(selectedScenarioId, u.type);
                  else toast.info("Create or select a scenario first.");
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    if (selectedScenarioId) void handleDrop(selectedScenarioId, u.type);
                    else toast.info("Create or select a scenario first.");
                  }
                }}
                draggable
                onDragStart={(e) => {
                  e.dataTransfer.setData("text/unit", u.type);
                  e.dataTransfer.effectAllowed = "copy";
                  unitDrag.current = u.type;
                }}
                onDragEnd={() => {
                  unitDrag.current = null;
                }}
                className="flex size-10 cursor-grab items-center justify-center rounded-md border border-border bg-background text-primary transition-colors hover:border-primary hover:bg-accent active:cursor-grabbing"
                title={`${u.label} — ${u.description}`}
                aria-label={u.label}
              >
                <Icon className="size-5" />
              </div>
            );
          })}
        </div>
      </div>

      <div className="flex items-center justify-between px-4 pt-4">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Scenarios
        </h3>
        <Button
          size="sm"
          className="bg-[#39FF14] text-black hover:bg-[#2fe00f]"
          onClick={() => createMut.mutate()}
        >
          <Plus className="mr-1 size-3.5" /> New
        </Button>
      </div>

      <div className="space-y-2 p-4">
        {scenarios.isError && (
          <p role="alert" className="text-xs text-destructive">
            {scenarios.error.message}
          </p>
        )}
        <p className="text-xs text-muted-foreground">
          Saved locally in this browser. Editing interventions clears previous results. Only lines
          and batteries are modelled in v1.
        </p>
        {(scenarios.data ?? [])
          .filter((s) => !s.is_template)
          .map((s) => {
            const isOpen = open[s.id] ?? true;
            return (
              <div
                key={s.id}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(s.id);
                }}
                onDragLeave={() => setDragOver(null)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragOver(null);
                  const t = e.dataTransfer.getData("text/unit") as UnitType;
                  if (t) void handleDrop(s.id, t);
                }}
                onClick={() => onSelectScenario(s.id)}
                className={`rounded-lg border p-2 transition-colors ${
                  dragOver === s.id
                    ? "border-primary bg-primary/5"
                    : selectedScenarioId === s.id
                      ? "border-primary/60 bg-accent"
                      : "border-border bg-background"
                }`}
              >
                <div className="flex items-center gap-1">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setOpen((o) => ({ ...o, [s.id]: !isOpen }));
                    }}
                    className="text-muted-foreground"
                    aria-label="Toggle scenario"
                  >
                    {isOpen ? (
                      <ChevronDown className="size-4" />
                    ) : (
                      <ChevronRight className="size-4" />
                    )}
                  </button>
                  <span className="flex-1 truncate text-sm font-medium">{s.name}</span>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="size-7"
                    disabled={runMut.isPending}
                    onClick={(e) => {
                      e.stopPropagation();
                      runMut.mutate(s.id);
                    }}
                    aria-label="Run scenario"
                  >
                    {runMut.isPending && runMut.variables === s.id ? (
                      <Loader2 className="size-3.5 animate-spin" />
                    ) : (
                      <Play className="size-3.5" />
                    )}
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="size-7"
                    onClick={async (e) => {
                      e.stopPropagation();
                      await remove({ data: { id: s.id } });
                      if (selectedScenarioId === s.id) onSelectScenario(null);
                      invalidate();
                    }}
                    aria-label="Delete scenario"
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>

                {isOpen && (
                  <div className="mt-2 space-y-2">
                    {s.units.length === 0 && (
                      <p className="rounded border border-dashed border-border px-2 py-3 text-center text-xs text-muted-foreground">
                        Drop units here
                      </p>
                    )}
                    {s.units.map((u) => {
                      const def = unitDef(u.unit_type);
                      const params = (u.params ?? {}) as Record<string, number>;
                      return (
                        <div key={u.id} className="rounded-md border border-border p-2">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-medium">{def.label}</span>
                            <button
                              className="text-muted-foreground hover:text-destructive"
                              onClick={async (e) => {
                                e.stopPropagation();
                                await dropUnit({ data: { id: u.id } });
                                invalidate();
                              }}
                              aria-label="Remove unit"
                            >
                              <Trash2 className="size-3" />
                            </button>
                          </div>
                          <div className="mt-1 grid grid-cols-2 gap-1">
                            {def.fields.map((fld) => (
                              <label key={fld.key} className="text-[11px] text-muted-foreground">
                                {fld.label} ({fld.unit})
                                <Input
                                  className="h-7 text-xs"
                                  type="number"
                                  step={fld.step}
                                  defaultValue={params[fld.key] ?? def.defaults[fld.key]}
                                  onClick={(e) => e.stopPropagation()}
                                  onBlur={async (e) => {
                                    const next = {
                                      ...params,
                                      [fld.key]: Number(e.target.value),
                                    };
                                    await patch({ data: { id: u.id, params: next } });
                                    invalidate();
                                  }}
                                />
                              </label>
                            ))}
                            <label className="text-[11px] text-muted-foreground">
                              Cost (MEUR)
                              <Input
                                className="h-7 text-xs"
                                type="number"
                                defaultValue={u.capex_meur}
                                onClick={(e) => e.stopPropagation()}
                                onBlur={async (e) => {
                                  await patch({
                                    data: { id: u.id, capexMeur: Number(e.target.value) },
                                  });
                                  invalidate();
                                }}
                              />
                            </label>
                            <label className="text-[11px] text-muted-foreground">
                              Delivery (months)
                              <Input
                                className="h-7 text-xs"
                                type="number"
                                defaultValue={u.delivery_months}
                                onClick={(e) => e.stopPropagation()}
                                onBlur={async (e) => {
                                  await patch({
                                    data: {
                                      id: u.id,
                                      deliveryMonths: Number(e.target.value),
                                    },
                                  });
                                  invalidate();
                                }}
                              />
                            </label>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
      </div>
    </aside>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-muted px-2 py-1.5">
      <dt className="text-[11px] text-muted-foreground">{label}</dt>
      <dd className="text-xs font-semibold">{value}</dd>
    </div>
  );
}

function safely<T, R>(action: (input: T) => Promise<R>) {
  return async (input: T) => {
    try {
      return await action(input);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not update browser storage");
      return undefined;
    }
  };
}
