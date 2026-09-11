import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useServerFn } from "@tanstack/react-start";
import { useState } from "react";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { Toaster } from "@/components/ui/sonner";
import { DataBar } from "@/components/DataBar";
import { EuropeMap, type TargetRow } from "@/components/EuropeMap";
import { TargetSidebar } from "@/components/TargetSidebar";
import { EvaluationPanel } from "@/components/EvaluationPanel";
import { listTargets, listZoneSummary } from "@/lib/analysis.functions";

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

  const zones = useQuery({ queryKey: ["zones"], queryFn: () => zonesFn() });
  const targets = useQuery({ queryKey: ["targets"], queryFn: () => targetsFn() });

  const rows = (targets.data ?? []) as TargetRow[];

  return (
    <main className="flex h-screen flex-col bg-background">
      <DataBar metric={metric} onMetricChange={setMetric} />
      <div className="flex min-h-0 flex-1">
        {sidebarOpen ? (
          <div className="relative h-full shrink-0">
            <TargetSidebar
              target={target}
              selectedScenarioId={scenarioId}
              onSelectScenario={setScenarioId}
            />
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
            className="z-10 my-auto -ml-0 flex h-16 w-5 shrink-0 items-center justify-center rounded-r-md border border-l-0 border-border bg-card text-muted-foreground shadow-sm hover:w-6 hover:bg-accent hover:text-primary"
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
            onSelect={(t) => {
              setTarget(t);
              setScenarioId(null);
              setSidebarOpen(true);
            }}
            onClear={() => {
              setTarget(null);
              setScenarioId(null);
              setSidebarOpen(false);
            }}
          />
        </div>
        <EvaluationPanel target={target} selectedScenarioId={scenarioId} />
      </div>
      <Toaster />
    </main>
  );
}
