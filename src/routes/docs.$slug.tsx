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
    meta: [{ title: `${loaderData?.title ?? "Docs"} | Grid Conductor` }],
  }),
  component: Publication,
});

function Publication() {
  const document = Route.useLoaderData();
  return (
    <main className="mx-auto max-w-4xl px-5 py-8">
      <nav className="mb-8 flex flex-wrap gap-5 text-sm">
        <Link to="/docs" className="underline">
          Docs
        </Link>
        <Link to="/" className="underline">
          Workbench
        </Link>
      </nav>
      <ResearchArticle content={document.content} />
    </main>
  );
}
