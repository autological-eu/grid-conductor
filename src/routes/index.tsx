import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState, type CSSProperties } from "react";
import { PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen } from "lucide-react";
import { toast } from "sonner";
import { Toaster } from "@/components/ui/sonner";
import { DataBar } from "@/components/DataBar";
import {
  EuropeMap,
  type PlacedUnit,
  type TargetRow,
  type UnitDropPlacement,
} from "@/components/EuropeMap";
import { TargetSidebar } from "@/components/TargetSidebar";
import { EvaluationPanel } from "@/components/EvaluationPanel";
import { listFastSummary } from "@/lib/fast-entsoe.functions";
import { addUnit, createScenario, listScenarios } from "@/lib/scenarios.functions";
import { unitDef, type UnitType } from "@/lib/units";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "EU Cross-Border Opportunity Workbench" },
      {
        name: "description",
        content:
          "Find congested ENTSO-E European electricity borders, simulate batteries and new lines, and evaluate them with a fast 2-node screening LP against ENTSO-E cost-benefit thinking.",
      },
      { property: "og:title", content: "EU Cross-Border Opportunity Workbench" },
      {
        property: "og:description",
        content:
          "Congested ENTSO-E borders, 2-node LP scenario simulation and cost-benefit evaluation for European grid investments.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Workbench,
});

function Workbench() {
  const summaryFn = listFastSummary;
  const [metric, setMetric] = useState<"market" | "climate">("market");
  const [target, setTarget] = useState<TargetRow | null>(null);
  const [scenarioId, setScenarioId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [evalOpen, setEvalOpen] = useState(false);
  const [leftWidth, setLeftWidth] = useState(340);
  const [rightWidth, setRightWidth] = useState(380);

  const summary = useQuery({ queryKey: ["fast-summary"], queryFn: () => summaryFn() });

  const zones = summary.data?.zones ?? [];
  const rows = (summary.data?.targets ?? []) as TargetRow[];

  const listScenariosQFn = listScenarios;
  const scenarios = useQuery({
    queryKey: ["scenarios", target?.id],
    queryFn: () => listScenariosQFn({ data: { targetId: target!.id } }),
    enabled: !!target,
  });
  const placedUnits: PlacedUnit[] = (scenarios.data ?? [])
    .filter((s) => !s.is_template)
    .flatMap((s) =>
      (s.units ?? []).map((u) => ({
        id: u.id,
        unit_type: u.unit_type,
        zone_code: u.zone_code,
        border_zone_a: u.border_zone_a,
        border_zone_b: u.border_zone_b,
        active: !scenarioId || s.id === scenarioId,
        scenario_name: s.name as string,
      })),
    );

  const selectScenario = (id: string | null) => {
    setScenarioId(id);
    if (id) setEvalOpen(true);
  };

  const step: 1 | 2 | 3 = scenarioId ? 3 : target ? 2 : 1;

  const qc = useQueryClient();
  const listScenariosFn = listScenarios;
  const createScenarioFn = createScenario;
  const addUnitFn = addUnit;

  /** a unit from the library was dropped onto the map */
  const handleDropUnit = async (unitType: UnitType, placement: UnitDropPlacement) => {
    if (unitType !== "line" && unitType !== "battery") {
      toast.error("Only lines and batteries are modelled in v1.");
      return;
    }
    if (!target) {
      toast.error("Pick a bottleneck on the map first, then drop units onto it.");
      return;
    }
    try {
      let sid = scenarioId;
      if (!sid) {
        const existing = await listScenariosFn({ data: { targetId: target.id } });
        sid = existing[0]?.id ?? null;
        if (!sid) {
          const s = await createScenarioFn({
            data: { targetId: target.id, name: `Scenario ${existing.length + 1}` },
          });
          sid = s.id;
        }
      }
      const def = unitDef(unitType);
      await addUnitFn({
        data: {
          scenarioId: sid,
          unitType,
          zoneCode: def.placement === "zone" ? (placement.zoneCode ?? null) : null,
          borderZoneA: def.placement === "border" ? (placement.zoneA ?? null) : null,
          borderZoneB: def.placement === "border" ? (placement.zoneB ?? null) : null,
        },
      });
      qc.invalidateQueries({ queryKey: ["scenarios", target.id] });
      selectScenario(sid);
      setSidebarOpen(true);
      const where =
        placement.zoneCode ?? (placement.zoneA ? `${placement.zoneA}–${placement.zoneB}` : "");
      toast.success(`${def.label} added${where ? ` in ${where}` : ""}`);
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  return (
    <main className="flex min-h-screen flex-col bg-background lg:h-screen">
      <DataBar step={step} />
      {summary.isPending && (
        <p className="px-5 py-3 text-xs" role="status">
          Loading workbench data…
        </p>
      )}
      {summary.isError && (
        <p className="px-5 py-3 text-xs" role="alert">
          {summary.error.message}{" "}
          <button className="underline" onClick={() => void summary.refetch()}>
            Retry data loading
          </button>
        </p>
      )}
      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        {sidebarOpen ? (
          <div
            className={`relative h-[640px] w-full shrink-0 rounded-l-md lg:h-full lg:w-[var(--panel-width)] ${
              step === 2 ? "bg-primary/5 ring-1 ring-primary/40" : ""
            }`}
            style={{ "--panel-width": `${leftWidth}px` } as CSSProperties}
          >
            <TargetSidebar
              target={target}
              selectedScenarioId={scenarioId}
              onSelectScenario={selectScenario}
            />
            <ResizeHandle side="left" onResize={setLeftWidth} />
            <button
              type="button"
              aria-label="Hide target panel"
              onClick={() => setSidebarOpen(false)}
              className="absolute right-3 top-4 lg:-right-3 z-10 flex h-11 w-11 items-center lg:h-6 lg:w-6 justify-center rounded-full border border-border bg-card text-muted-foreground shadow-sm hover:bg-accent hover:text-foreground"
            >
              <PanelLeftClose className="h-3.5 w-3.5" />
            </button>
          </div>
        ) : (
          <button
            type="button"
            aria-label="Show target panel"
            onClick={() => setSidebarOpen(true)}
            className="z-10 mx-auto flex h-11 w-16 shrink-0 lg:mx-0 lg:my-auto lg:h-16 lg:w-5 items-center justify-center rounded-r-md border border-l-0 border-border bg-card text-muted-foreground shadow-sm hover:w-6 hover:bg-accent hover:text-primary"
          >
            <PanelLeftOpen className="h-3.5 w-3.5" />
          </button>
        )}
        <div className="h-[460px] min-h-[460px] min-w-0 shrink-0 p-2 lg:h-auto lg:min-h-0 lg:flex-1 lg:shrink lg:p-4">
          <EuropeMap
            zones={zones}
            targets={rows}
            selectedId={target?.id ?? null}
            metric={metric}
            onMetricChange={setMetric}
            onSelect={(t) => {
              setTarget(t);
              setScenarioId(null);
              setSidebarOpen(true);
              setEvalOpen(false);
            }}
            onClear={() => {
              setTarget(null);
              setScenarioId(null);
              setSidebarOpen(false);
              setEvalOpen(false);
            }}
            onDropUnit={handleDropUnit}
            placedUnits={placedUnits}
          />
        </div>
        {evalOpen ? (
          <div
            className={`relative h-[420px] w-full shrink-0 rounded-r-md lg:h-full lg:w-[var(--panel-width)] ${
              step === 3 ? "bg-primary/5 ring-1 ring-primary/40" : ""
            }`}
            style={{ "--panel-width": `${rightWidth}px` } as CSSProperties}
          >
            <EvaluationPanel target={target} selectedScenarioId={scenarioId} />
            <ResizeHandle side="right" onResize={setRightWidth} />
            <button
              type="button"
              aria-label="Hide evaluation panel"
              onClick={() => setEvalOpen(false)}
              className="absolute right-3 top-4 lg:right-auto lg:-left-3 z-10 flex h-11 w-11 items-center lg:h-6 lg:w-6 justify-center rounded-full border border-border bg-card text-muted-foreground shadow-sm hover:bg-accent hover:text-foreground"
            >
              <PanelRightClose className="h-3.5 w-3.5" />
            </button>
          </div>
        ) : (
          <button
            type="button"
            aria-label="Show evaluation panel"
            onClick={() => setEvalOpen(true)}
            className="z-10 mx-auto flex h-11 w-16 shrink-0 lg:mx-0 lg:my-auto lg:h-16 lg:w-5 items-center justify-center rounded-l-md border border-r-0 border-border bg-card text-muted-foreground shadow-sm hover:w-6 hover:bg-accent hover:text-primary"
          >
            <PanelRightOpen className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
      <Toaster />
    </main>
  );
}

function ResizeHandle({
  side,
  onResize,
}: {
  side: "left" | "right";
  onResize: (width: number) => void;
}) {
  const start = useRef<{ x: number; width: number } | null>(null);

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={side === "left" ? "Resize target panel" : "Resize evaluation panel"}
      onPointerDown={(e) => {
        const parent = e.currentTarget.parentElement;
        if (!parent) return;
        start.current = { x: e.clientX, width: parent.getBoundingClientRect().width };
        e.currentTarget.setPointerCapture(e.pointerId);
      }}
      onPointerMove={(e) => {
        const s = start.current;
        if (!s) return;
        const dx = e.clientX - s.x;
        const next = side === "left" ? s.width + dx : s.width - dx;
        onResize(Math.min(620, Math.max(260, Math.round(next))));
      }}
      onPointerUp={(e) => {
        start.current = null;
        e.currentTarget.releasePointerCapture(e.pointerId);
      }}
      className={`absolute inset-y-0 z-10 hidden w-1.5 lg:block cursor-col-resize hover:bg-primary/30 ${
        side === "left" ? "-right-0.5" : "-left-0.5"
      }`}
    />
  );
}
