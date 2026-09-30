import { createFileRoute, Link } from "@tanstack/react-router";
import { researchDocuments } from "@/lib/research-documents";
import { publicAsset } from "@/lib/research";

export const Route = createFileRoute("/docs")({
  head: () => ({ meta: [{ title: "Grid Conductor Research" }] }),
  component: Research,
});

const artifacts = [
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

function Research() {
  return (
    <main className="mx-auto max-w-6xl px-5 py-8">
      <nav className="mb-8 flex gap-5 text-sm">
        <Link to="/" className="underline">
          Workbench
        </Link>
        <Link to="/targets" className="underline">
          Target evidence
        </Link>
      </nav>
      <p className="text-xs uppercase tracking-widest text-muted-foreground">
        Experimental electricity-grid research
      </p>
      <h1 className="mt-3 text-4xl font-bold">Grid Conductor Research</h1>
      <p className="mt-4 max-w-3xl leading-7 text-muted-foreground">
        From source data to published evidence to interactive scenarios. Read the assumptions,
        coverage and validation before interpreting an estimated investment opportunity.
      </p>
      <aside className="my-6 rounded-xl border bg-muted/40 p-5 text-sm leading-7">
        <strong>Current workbench: 2025 reduced-form screening.</strong> Cable welfare uses an exact
        trapezoid response; batteries use a daily-cycle LP. These are screening estimates, not
        dispatch-grade valuations. Climate figures are unsigned average-mix proxies, not
        demonstrated avoided emissions. The separate FR–CH pilot has failed validation gates; the
        European dispatch baseline remains blocked by input quality. PyPSA-Eur and JAO publication
        coverage do not establish validated investment benefits.
      </aside>
      <div className="grid gap-10 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <section>
          <h2 className="mb-4 text-xl font-semibold">Research publications</h2>
          <Link
            to="/docs/$slug"
            params={{ slug: "fast-entsoe-screening" }}
            className="mb-4 block rounded-xl border border-primary bg-muted p-4 font-semibold"
          >
            Start here: Fast ENTSO-E screening ladder →
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
            research library → browser workbench. No research credentials or heavy Python models run
            in this public application.
          </p>
        </section>
      </div>
    </main>
  );
}
