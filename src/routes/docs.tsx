import { createFileRoute, Link, Outlet, useMatch } from "@tanstack/react-router";
import { ResearchArticle } from "@/components/ResearchArticle";
import { researchDocuments } from "@/lib/research-documents";
import { publicAsset } from "@/lib/research";

export const Route = createFileRoute("/docs")({
  head: () => ({ meta: [{ title: "Methods, maths & evidence | Grid Conductor" }] }),
  component: ResearchRoute,
});

const artifacts = [
  ["network-benchmark/carbon-sensitivity.json", "Paired carbon-price sensitivity · experimental"],
  ["network-benchmark/results.json", "Matched real-data weekly dispatch benchmark · experimental"],
  ["entsoe-fast-targets.json", "2025 annual screening · workbench input"],
  ["model-validation.json", "FR–CH validation · experimental, failed gates"],
  ["eu-input-quality.json", "European input coverage · blocked baseline"],
  ["eu-model-validation.json", "European baseline status"],
  ["eu-month-comparison.json", "January / August comparison"],
  ["pypsa-targets.json", "PyPSA-Eur topology / experimental targets"],
  ["pypsa-input-audit.json", "PyPSA-Eur input provenance and coverage"],
  ["network-evidence-coverage.json", "JAO network evidence coverage"],
  ["jao-network-validation.json", "JAO sample validation"],
  ["market-experiment.json", "Market pilot experiment"],
  ["coverage-manifest.json", "Pilot coverage manifest"],
  ["targets.json", "Observed-spread target evidence"],
] as const;

const chapters = [
  ["1-from-source-data-to-the-map", "1. Source data"],
  ["2-what-market-opportunity-means", "2. Market opportunity"],
  ["3-rent-and-the-fixed-spread-ladder", "3. Rent and opportunity"],
  ["4-transmission-interventions", "4. Transmission"],
  ["5-storage-interventions", "5. Storage"],
  ["6-costs-and-financial-indicators", "6. Costs and finance"],
  ["7-climate-indicators-and-validation", "7. Climate and validation"],
  ["8-audit-a-number-yourself", "8. Audit a number"],
  ["research-library", "Research library & artifacts"],
] as const;

function ResearchRoute() {
  const article = useMatch({ from: "/docs/$slug", shouldThrow: false });
  return article ? <Outlet /> : <Research />;
}

function Research() {
  const overview = researchDocuments.find((doc) => doc.slug === "methods-and-maths");
  return (
    <main className="mx-auto max-w-7xl px-5 py-8">
      <nav className="mb-8 flex gap-5 text-sm">
        <Link to="/" className="underline">
          Workbench
        </Link>
        <Link to="/targets" className="underline">
          Target evidence
        </Link>
      </nav>
      <Link to="/network" className="mb-5 inline-block underline">
        Coupled network experiment
      </Link>
      <p className="text-xs uppercase tracking-widest text-muted-foreground">
        Experimental electricity-grid research
      </p>
      <h1 className="mt-3 text-4xl font-bold">Methods, maths &amp; evidence</h1>
      <p className="mt-4 max-w-3xl leading-7 text-muted-foreground">
        What the map measures, where its numbers come from, and how interventions are evaluated.
        Follow the equations from published observations to estimated system welfare.
      </p>
      <Link
        to="/docs/$slug"
        params={{ slug: "worked-example-se4-pl" }}
        className="my-6 block max-w-3xl rounded-xl border border-primary bg-muted p-5"
      >
        <span className="block font-semibold">SE4 → PL: reproduce €229.9 million/year →</span>
        <span className="mt-1 block text-sm text-muted-foreground">
          Exact source fields, arithmetic, line and battery examples, and the fallback-slope
          assumption.
        </span>
      </Link>
      <Link
        to="/docs/$slug"
        params={{ slug: "network-benchmark-comparison" }}
        className="mb-6 block max-w-3xl rounded-xl border p-5"
      >
        <span className="block font-semibold">
          Real-data benchmark: browser dispatch versus PyPSA →
        </span>
        <span className="mt-1 block text-sm text-muted-foreground">
          Matched weekly inputs, investment benefits, network-physics differences and measured
          timings.
        </span>
      </Link>
      <div className="grid gap-10 lg:grid-cols-[14rem_minmax(0,1fr)]">
        <nav aria-label="Methods chapters" className="self-start lg:sticky lg:top-5">
          <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            On this page
          </p>
          <ul className="grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-1">
            {chapters.map(([anchor, label]) => (
              <li key={anchor}>
                <a href={`#${anchor}`} className="block rounded-lg p-2 hover:bg-muted">
                  {label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
        <ResearchArticle content={overview?.content.replace(/^# .+\n/, "") ?? ""} />
      </div>
      <section id="research-library" className="mt-14 border-t pt-8">
        <h2 className="mb-2 text-2xl font-semibold">Research library &amp; published artifacts</h2>
        <p className="mb-8 max-w-3xl text-sm leading-7 text-muted-foreground">
          The overview is maintained in Markdown alongside these original publications. Read the
          detailed reports and their validation/provenance before interpreting screening results.
        </p>
        <div className="grid gap-10 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
          <section>
            <h2 className="mb-4 text-xl font-semibold">Research publications</h2>
            <Link
              to="/docs/$slug"
              params={{ slug: "fast-entsoe-screening" }}
              className="mb-4 block rounded-xl border border-primary bg-muted p-4 font-semibold"
            >
              Technical detail: Fast ENTSO-E screening ladder →
            </Link>
            <ul className="space-y-2">
              {researchDocuments.map((doc) => (
                <li key={doc.slug}>
                  <Link
                    to="/docs/$slug"
                    params={{ slug: doc.slug }}
                    className="block rounded-lg border p-4 hover:bg-muted"
                  >
                    {doc.title}
                  </Link>
                </li>
              ))}
            </ul>
          </section>
          <section>
            <h2 className="mb-4 text-xl font-semibold">Published artifacts</h2>
            <p className="mb-4 text-sm text-muted-foreground">
              Machine-readable research snapshots ship with the app. Each artifact retains its
              provenance, assumptions and validation status.
            </p>
            <ul className="space-y-2">
              {artifacts.map(([file, label]) => (
                <li key={file}>
                  <a
                    href={publicAsset(`research/${file}`)}
                    className="block rounded-lg border p-4 hover:bg-muted"
                  >
                    <span className="block text-sm font-medium">{label}</span>
                    <span className="text-xs text-muted-foreground">{file} ↗</span>
                  </a>
                </li>
              ))}
            </ul>
            <p className="mt-6 text-sm leading-6 text-muted-foreground">
              Offline Python / PyPSA-Eur tools → Markdown publication and JSON/CSV artifacts →
              research library → browser workbench. No research credentials or heavy Python models
              run in this public application.
            </p>
          </section>
        </div>
      </section>
    </main>
  );
}
