import { createFileRoute } from "@tanstack/react-router";
import { BorderOpportunityNetwork } from "@/components/BorderOpportunityNetwork";

export const Route = createFileRoute("/targets")({
  head: () => ({ meta: [{ title: "European target evidence | Grid Conductor" }] }),
  component: TargetsPage,
});

function TargetsPage() {
  return (
    <div className="mx-auto max-w-6xl p-6">
      <BorderOpportunityNetwork />
    </div>
  );
}
