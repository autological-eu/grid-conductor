import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useServerFn } from "@tanstack/react-start";
import { useState } from "react";
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

  const zones = useQuery({ queryKey: ["zones"], queryFn: () => zonesFn() });
  const targets = useQuery({ queryKey: ["targets"], queryFn: () => targetsFn() });

  const rows = (targets.data ?? []) as TargetRow[];

  return (
    <main className="flex h-screen flex-col bg-background">
      <DataBar metric={metric} onMetricChange={setMetric} />
      <div className="flex min-h-0 flex-1">
        <TargetSidebar
          target={target}
          selectedScenarioId={scenarioId}
          onSelectScenario={setScenarioId}
        />
        <div className="min-w-0 flex-1 p-4">
          <EuropeMap
            zones={zones.data ?? []}
            targets={rows}
            selectedId={target?.id ?? null}
            metric={metric}
            onSelect={(t) => {
              setTarget(t);
              setScenarioId(null);
            }}
          />
        </div>
        <EvaluationPanel target={target} selectedScenarioId={scenarioId} />
      </div>
      <Toaster />
    </main>
  );
}
