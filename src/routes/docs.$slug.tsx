import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { researchDocuments } from "@/lib/research-documents";
import { ResearchArticle } from "@/components/ResearchArticle";

export const Route = createFileRoute("/docs/$slug")({
  loader: ({ params }) => {
    const document = researchDocuments.find((doc) => doc.slug === params.slug);
    if (!document) throw notFound();
    return document;
  },
  head: ({ loaderData }) => ({
    meta: [{ title: `${loaderData?.title ?? "Research"} | Grid Conductor` }],
  }),
  component: Publication,
});

function Publication() {
  const document = Route.useLoaderData();
  return (
    <main className="mx-auto max-w-4xl px-5 py-8">
      <nav className="mb-8 flex flex-wrap gap-5 text-sm">
        <Link to="/docs" className="underline">
          Research library
        </Link>
        <Link to="/" className="underline">
          Workbench
        </Link>
        <Link to="/targets" className="underline">
          Target evidence
        </Link>
      </nav>
      <p className="mb-5 rounded-lg border bg-muted/40 p-3 text-sm text-muted-foreground">
        Research publication · {document.slug}.md · Preserve screening, experimental and validated
        distinctions when interpreting results.
      </p>
      <ResearchArticle content={document.content} />
    </main>
  );
}
