import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useServerFn } from "@tanstack/react-start";
import { ChevronDown, ChevronRight, Copy, Loader2, Play, Plus, RefreshCw, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { UNIT_LIBRARY, unitDef, unitDrag, type UnitType } from "@/lib/units";
import { unitIcon } from "@/lib/unitIcons";
import { COST_ASSUMPTIONS, DEFAULT_TEMPLATE_BUDGET_MEUR } from "@/lib/costAssumptions";
import {
  addUnit,
  createScenario,
  deleteScenario,
  deleteUnit,
  listScenarios,
  runScenario,
  updateUnit,
} from "@/lib/scenarios.functions";
import { copyTemplateScenario, ensureTemplateScenarios } from "@/lib/templates.functions";
import type { TargetRow } from "./EuropeMap";
import { Button } from "@/components/ui/button";
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
  const list = useServerFn(listScenarios);
  const create = useServerFn(createScenario);
  const remove = useServerFn(deleteScenario);
  const add = useServerFn(addUnit);
  const patch = useServerFn(updateUnit);
  const dropUnit = useServerFn(deleteUnit);
  const run = useServerFn(runScenario);

  const ensureTemplates = useServerFn(ensureTemplateScenarios);
  const copyTemplate = useServerFn(copyTemplateScenario);

  const [dragOver, setDragOver] = useState<string | null>(null);
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [budget, setBudget] = useState<number>(DEFAULT_TEMPLATE_BUDGET_MEUR);

  const scenarios = useQuery({
    queryKey: ["scenarios", target?.id],
    queryFn: () => list({ data: { targetId: target!.id } }),
    enabled: !!target,
  });

  // pre-compute the seven templates in the background when a target opens
  const ensureMut = useMutation({
    mutationFn: (force: boolean) =>
      ensureTemplates({ data: { targetId: target!.id, budgetMeur: budget, force } }),
    onSuccess: (r) => {
      if (r.created > 0) {
        qc.invalidateQueries({ queryKey: ["scenarios", target?.id] });
        toast.success(`${r.created} template scenarios ready`);
      }
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const targetId = target?.id;
  useEffect(() => {
    if (targetId) ensureMut.mutate(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [targetId, budget]);

  const copyMut = useMutation({
    mutationFn: (id: string) => copyTemplate({ data: { id } }),
    onSuccess: (s) => {
      qc.invalidateQueries({ queryKey: ["scenarios", target?.id] });
      onSelectScenario(s.id);
      toast.success("Template copied to your scenarios");
    },
    onError: (e: Error) => toast.error(e.message),
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
    <aside className="flex h-full w-full flex-col border-r border-border bg-card">
      <div className="border-b border-border p-4">
        <h2 className="text-sm font-semibold">
          {target.zone_a} – {target.zone_b}
        </h2>
        <p className="text-xs text-muted-foreground">
          {target.zone_a_name} to {target.zone_b_name}
        </p>
        <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
          <Stat label="Market loss" value={`${target.market_loss_meur.toFixed(1)} MEUR/y`} />
          <Stat label="Climate loss" value={`${target.climate_loss_ktco2.toFixed(1)} ktCO2/y`} />
          <Stat
            label="Congested hours"
            value={`${target.congested_hours} / ${target.total_hours}`}
          />
          <Stat
            label="Observed capacity"
            value={
              target.observed_capacity_mw
                ? `${Math.round(target.observed_capacity_mw)} MW`
                : "—"
            }
          />
        </dl>
      </div>

      <div className="border-b border-border p-4">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Unit library
        </h3>
        <p className="mb-2 text-xs text-muted-foreground">
          Drag an icon onto the map.
        </p>
        <div className="flex flex-wrap gap-2">
          {UNIT_LIBRARY.map((u) => {
            const Icon = unitIcon(u.type);
            return (
              <div
                key={u.type}
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
        <Button size="sm" variant="secondary" onClick={() => createMut.mutate()}>
          <Plus className="mr-1 size-3.5" /> New
        </Button>
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto p-4">
        {(scenarios.data ?? []).filter((s) => !s.is_template).map((s) => {
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
                  {isOpen ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
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

      <div className="border-t border-border p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Templates
          </h3>
          <div className="flex items-center gap-1">
            <label className="flex items-center gap-1 text-[11px] text-muted-foreground">
              €
              <Input
                className="h-6 w-14 px-1 text-xs"
                type="number"
                min={0.1}
                step={1}
                defaultValue={DEFAULT_TEMPLATE_BUDGET_MEUR}
                onBlur={(e) => {
                  const v = Number(e.target.value);
                  if (v > 0 && v !== budget) setBudget(v);
                }}
              />
              M
            </label>
            <Button
              size="icon"
              variant="ghost"
              className="size-6"
              disabled={ensureMut.isPending}
              onClick={() => ensureMut.mutate(true)}
              aria-label="Recompute templates"
              title="Recompute templates"
            >
              <RefreshCw className={`size-3 ${ensureMut.isPending ? "animate-spin" : ""}`} />
            </Button>
          </div>
        </div>
        <p className="mt-1 text-[11px] text-muted-foreground">
          Pre-computed scenarios, each sized to the same budget.
        </p>
        <div className="mt-2 space-y-1">
          {(scenarios.data ?? [])
            .filter((s) => s.is_template)
            .map((s) => {
              const unit = s.units[0];
              const tech = (unit?.unit_type ?? "battery") as keyof typeof COST_ASSUMPTIONS;
              const Icon = unitIcon(unit?.unit_type ?? "battery");
              const cost = COST_ASSUMPTIONS[tech];
              return (
                <div
                  key={s.id}
                  onClick={() => onSelectScenario(s.id)}
                  className={`flex cursor-pointer items-center gap-2 rounded-md border p-2 transition-colors ${
                    selectedScenarioId === s.id
                      ? "border-primary/60 bg-accent"
                      : "border-border bg-background hover:bg-accent/50"
                  }`}
                >
                  <Icon className="size-4 shrink-0 text-primary" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-medium">{s.name}</p>
                    <p className="truncate text-[11px] text-muted-foreground" title={cost?.basis}>
                      {capacityLabel(unit)}
                      {s.result
                        ? ` · ${s.result.market_opportunity_meur.toFixed(3)} MEUR/y · ${s.result.climate_opportunity_ktco2.toFixed(3)} ktCO2/y`
                        : s.status === "running" || ensureMut.isPending
                          ? " · computing…"
                          : ""}
                    </p>
                  </div>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="size-6 shrink-0"
                    disabled={copyMut.isPending}
                    onClick={(e) => {
                      e.stopPropagation();
                      copyMut.mutate(s.id);
                    }}
                    aria-label="Copy template to my scenarios"
                    title="Copy to my scenarios"
                  >
                    <Copy className="size-3" />
                  </Button>
                </div>
              );
            })}
          {(scenarios.data ?? []).filter((s) => s.is_template).length === 0 && (
            <p className="text-[11px] text-muted-foreground">
              {ensureMut.isPending ? "Computing template scenarios…" : "No templates yet."}
            </p>
          )}
        </div>
      </div>
    </aside>
  );
}

function capacityLabel(unit: { params: unknown } | undefined): string {
  const p = (unit?.params ?? {}) as Record<string, number>;
  if (p["energy_mwh"] != null) return `${p["power_mw"]} MW / ${p["energy_mwh"]} MWh`;
  if (p["capacity_mw"] != null) return `${p["capacity_mw"]} MW`;
  if (p["added_mw"] != null) return `+${p["added_mw"]} MW`;
  return "";
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-muted px-2 py-1.5">
      <dt className="text-[11px] text-muted-foreground">{label}</dt>
      <dd className="text-xs font-semibold">{value}</dd>
    </div>
  );
}
