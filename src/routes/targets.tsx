import { createFileRoute } from "@tanstack/react-router";
import { EuropeanTargets } from "@/components/EuropeanTargets";

export const Route = createFileRoute("/targets")({
  head: () => ({ meta: [{ title: "European target evidence | Grid Conductor" }] }),
  component: EuropeanTargetsPage,
});

function EuropeanTargetsPage() {
  return <EuropeanTargets />;
}
