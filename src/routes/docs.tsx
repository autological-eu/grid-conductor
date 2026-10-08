import { createFileRoute, Link, Outlet, useMatch } from "@tanstack/react-router";
import { ResearchArticle } from "@/components/ResearchArticle";
import { researchDocuments } from "@/lib/research-documents";

export const Route = createFileRoute("/docs")({
  head: () => ({ meta: [{ title: "Workbench methodology | Grid Conductor" }] }),
  component: DocsRoute,
});

function DocsRoute() {
  const article = useMatch({ from: "/docs/$slug", shouldThrow: false });
  return article ? <Outlet /> : <Docs />;
}

function Docs() {
  const methodology = researchDocuments.find((doc) => doc.slug === "workbench-methodology");
  return (
    <main className="mx-auto max-w-4xl px-5 py-8">
      <nav className="mb-8 text-sm">
        <Link to="/" className="underline">
          Workbench
        </Link>
      </nav>
      <h1 className="mb-4 text-4xl font-bold">Docs</h1>
      <p className="mb-8 leading-7 text-muted-foreground">
        How the current workbench identifies bottlenecks and estimates the effect of a line or
        battery.
      </p>
      <ResearchArticle content={methodology?.content.replace(/^# .+\n/, "") ?? ""} />
    </main>
  );
}
