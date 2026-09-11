import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useServerFn } from "@tanstack/react-start";
import { useRef, useState } from "react";
import { PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen } from "lucide-react";
import { toast } from "sonner";
import { Toaster } from "@/components/ui/sonner";
import { DataBar } from "@/components/DataBar";
import { EuropeMap, type TargetRow, type UnitDropPlacement } from "@/components/EuropeMap";
import { TargetSidebar } from "@/components/TargetSidebar";
import { EvaluationPanel } from "@/components/EvaluationPanel";
import { listTargets, listZoneSummary } from "@/lib/analysis.functions";
import { addUnit, createScenario, listScenarios } from "@/lib/scenarios.functions";
import { unitDef, type UnitType } from "@/lib/units";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "EU Cross-Border Opportunity Workbench" },
      {
        name: "description",
        content:
          "Find congested European electricity borders, simulate batteries, renewables and new lines hour by hour, and evaluate them against ENTSO-E cost-benefit guidelines.",
      },
      { property: "og:title", content: "EU Cross-Border Opportunity Workbench" },
      {
        property: "og:description",
        content:
          "Congested borders, hourly market-coupling simulation and ENTSO-E cost-benefit evaluation for European grid investments.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Workbench,
});

function Workbench() {
  const zonesFn = useServerFn(listZoneSummary);
  const targetsFn = useServerFn(listTargets);
  const [metric, setMetric] = useState<"market" | "climate">("market");
  const [target, setTarget] = useState<TargetRow | null>(null);
  const [scenarioId, setScenarioId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [evalOpen, setEvalOpen] = useState(false);
  const [leftWidth, setLeftWidth] = useState(340);
  const [rightWidth, setRightWidth] = useState(380);

  const zones = useQuery({ queryKey: ["zones"], queryFn: () => zonesFn() });
  const targets = useQuery({ queryKey: ["targets"], queryFn: () => targetsFn() });

  const rows = (targets.data ?? []) as TargetRow[];

  const selectScenario = (id: string | null) => {
    setScenarioId(id);
    if (id) setEvalOpen(true);
  };

  const step: 1 | 2 | 3 = scenarioId ? 3 : target ? 2 : 1;

  const qc = useQueryClient();
  const listScenariosFn = useServerFn(listScenarios);
  const createScenarioFn = useServerFn(createScenario);
  const addUnitFn = useServerFn(addUnit);

  /** a unit from the library was dropped onto the map */
  const handleDropUnit = async (unitType: UnitType, placement: UnitDropPlacement) => {
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
      const where = placement.zoneCode ?? (placement.zoneA ? `${placement.zoneA}–${placement.zoneB}` : "");
      toast.success(`${def.label} added${where ? ` in ${where}` : ""}`);
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  return (
    <main className="flex h-screen flex-col bg-background">
      <DataBar step={step} />
      <div className="flex min-h-0 flex-1">
        {sidebarOpen ? (
          <div
            className={`relative h-full shrink-0 rounded-l-md ${
              step === 2 ? "bg-primary/5 ring-1 ring-primary/40" : ""
            }`}
            style={{ width: leftWidth }}
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
              className="absolute -right-3 top-4 z-10 flex h-6 w-6 items-center justify-center rounded-full border border-border bg-card text-muted-foreground shadow-sm hover:bg-accent hover:text-foreground"
            >
              <PanelLeftClose className="h-3.5 w-3.5" />
            </button>
          </div>
        ) : (
          <button
            type="button"
            aria-label="Show target panel"
            onClick={() => setSidebarOpen(true)}
            className="z-10 my-auto flex h-16 w-5 shrink-0 items-center justify-center rounded-r-md border border-l-0 border-border bg-card text-muted-foreground shadow-sm hover:w-6 hover:bg-accent hover:text-primary"
          >
            <PanelLeftOpen className="h-3.5 w-3.5" />
          </button>
        )}
        <div className="min-w-0 flex-1 p-4">
          <EuropeMap
            zones={zones.data ?? []}
            targets={rows}
            selectedId={target?.id ?? null}
            metric={metric}
            onMetricChange={setMetric}
            onSelect={(t) => {
              setTarget(t);
              setScenarioId(null);
              setSidebarOpen(true);
            }}
            onClear={() => {
              setTarget(null);
              setScenarioId(null);
              setSidebarOpen(false);
              setEvalOpen(false);
            }}
            onDropUnit={handleDropUnit}
          />
        </div>
        {evalOpen ? (
          <div
            className={`relative h-full shrink-0 rounded-r-md ${
              step === 3 ? "bg-primary/5 ring-1 ring-primary/40" : ""
            }`}
            style={{ width: rightWidth }}
          >
            <EvaluationPanel target={target} selectedScenarioId={scenarioId} />
            <ResizeHandle side="right" onResize={setRightWidth} />
            <button
              type="button"
              aria-label="Hide evaluation panel"
              onClick={() => setEvalOpen(false)}
              className="absolute -left-3 top-4 z-10 flex h-6 w-6 items-center justify-center rounded-full border border-border bg-card text-muted-foreground shadow-sm hover:bg-accent hover:text-foreground"
            >
              <PanelRightClose className="h-3.5 w-3.5" />
            </button>
          </div>
        ) : (
          <button
            type="button"
            aria-label="Show evaluation panel"
            onClick={() => setEvalOpen(true)}
            className="z-10 my-auto flex h-16 w-5 shrink-0 items-center justify-center rounded-l-md border border-r-0 border-border bg-card text-muted-foreground shadow-sm hover:w-6 hover:bg-accent hover:text-primary"
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
      className={`absolute inset-y-0 z-10 w-1.5 cursor-col-resize hover:bg-primary/30 ${
        side === "left" ? "-right-0.5" : "-left-0.5"
      }`}
    />
  );
}
