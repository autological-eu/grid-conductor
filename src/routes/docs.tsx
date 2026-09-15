import { createFileRoute, Link } from "@tanstack/react-router";
import type { ReactNode } from "react";

export const Route = createFileRoute("/docs")({
  head: () => ({
    meta: [
      { title: "Methodology | Grid Conductor" },
      {
        name: "description",
        content:
          "How Grid Conductor sources electricity data, identifies border opportunities, simulates investments and evaluates costs and climate impacts.",
      },
    ],
  }),
  component: Methodology,
});

const chapters = [
  ["data", "0", "Data"],
  ["targets", "1", "Finding targets"],
  ["scenarios", "2", "Simulating scenarios"],
  ["evaluation", "3", "Evaluating opportunities"],
] as const;

function Paragraph({ children }: { children: ReactNode }) {
  return <p className="mt-4 leading-7 text-muted-foreground">{children}</p>;
}

function Note({ title, children }: { title: string; children: ReactNode }) {
  return (
    <aside className="my-6 rounded-xl border border-border bg-muted/50 p-5">
      <p className="font-semibold text-foreground">{title}</p>
      <div className="mt-2 text-sm leading-6 text-muted-foreground">{children}</div>
    </aside>
  );
}

function Table({ headers, rows }: { headers: string[]; rows: string[][] }) {
  return (
    <div
      className="my-6 overflow-x-auto rounded-xl border border-border"
      role="region"
      aria-label={headers.join(", ")}
      tabIndex={0}
    >
      <table className="w-full min-w-[560px] text-left text-sm">
        <thead className="bg-muted">
          <tr>
            {headers.map((h) => (
              <th key={h} scope="col" className="px-4 py-3 font-semibold">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={row[0]} className={i % 2 ? "bg-muted/30" : "bg-card"}>
              {row.map((cell, j) =>
                j === 0 ? (
                  <th key={j} scope="row" className="px-4 py-4 align-top font-medium">
                    {cell}
                  </th>
                ) : (
                  <td key={j} className="px-4 py-4 align-top leading-6 text-muted-foreground">
                    {cell}
                  </td>
                ),
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Section({
  id,
  number,
  title,
  children,
}: {
  id: string;
  number: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section
      id={id}
      aria-labelledby={`${id}-title`}
      className="scroll-mt-24 border-t border-border py-10"
    >
      <div className="flex items-center gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-sm font-semibold text-primary-foreground">
          {number}
        </span>
        <h2 id={`${id}-title`} className="text-2xl font-semibold tracking-tight">
          {title}
        </h2>
      </div>
      {children}
    </section>
  );
}

function Methodology() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <a
        href="#methodology"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:bg-card focus:p-3"
      >
        Skip to methodology
      </a>
      <header className="sticky top-0 z-20 border-b border-border bg-background/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-4">
          <Link to="/" className="font-bold tracking-tight">
            Grid Conductor
          </Link>
          <Link to="/" className="rounded-md border border-border px-3 py-2 text-sm hover:bg-muted">
            Back to workbench →
          </Link>
        </div>
      </header>
      <div className="mx-auto grid max-w-6xl gap-10 px-5 py-10 lg:grid-cols-[210px_minmax(0,1fr)]">
        <nav aria-label="Methodology chapters" className="lg:sticky lg:top-28 lg:self-start">
          <p className="mb-4 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Methodology
          </p>
          <ol className="grid gap-2 sm:grid-cols-2 lg:grid-cols-1">
            {chapters.map(([id, n, label]) => (
              <li key={id}>
                <a href={`#${id}`} className="block rounded-lg px-3 py-2 text-sm hover:bg-muted">
                  <span className="mr-3 text-muted-foreground">{n}</span>
                  {label}
                </a>
              </li>
            ))}
          </ol>
          <a
            href="#references"
            className="mt-3 block px-3 py-2 text-sm text-muted-foreground hover:text-foreground"
          >
            Sources & references
          </a>
        </nav>
        <main id="methodology" className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Working methodology · v0.3 · 13 September 2026
          </p>
          <h1 className="mt-4 text-4xl font-bold tracking-tight sm:text-5xl">
            From grid data to better investment decisions.
          </h1>
          <Paragraph>
            Grid Conductor investigates where electricity-market differences suggest an opportunity,
            then compares possible interventions. A target is a connected pair of electricity zones
            with recurring evidence worth investigating. It is not yet a proven bottleneck or a
            recommended construction site.
          </Paragraph>
          <Note title="How to read this document">
            “Current app” describes the existing prototype. “Research pilot” describes calculations
            run separately from the app. “Proposed method” defines the next implementation. These
            distinctions matter: the independent carbon estimates are not yet used by the live
            target rankings.
          </Note>

          <Section id="data" number="0" title="Data">
            <Paragraph>
              Use a common time window and consistent zone boundaries. The screening snapshot uses
              the last 30 complete UTC days available in the archive, not today’s rolling window; a
              full year provides seasonal context. Store timestamps in UTC and convert to local time
              only for display.
            </Paragraph>
            <Table
              headers={["Signal", "Source and unit", "Purpose / status"]}
              rows={[
                [
                  "Day-ahead prices",
                  "ENTSO-E or Electricity Maps · EUR/MWh",
                  "Matched prices define spread events. The current app imports Electricity Maps prices; direct ENTSO-E price ingestion remains to be connected.",
                ],
                [
                  "Generation by technology",
                  "ENTSO-E · MW, integrated to MWh",
                  "Available in the independent research pilot; feeds generation emissions and flow tracing.",
                ],
                [
                  "Actual load and physical flows",
                  "ENTSO-E · MW, integrated to MWh",
                  "Available in the research pilot and app ingestion paths. Measure demand, transfers and energy-balance consistency.",
                ],
                [
                  "Transfer capacity",
                  "ENTSO-E / regional capacity platforms · directional MW or flow-based constraints",
                  "Must match the event time and market horizon. A physical flow maximum is not a capacity rating.",
                ],
                [
                  "Carbon intensity",
                  "Independent calculation; Electricity Maps benchmark · gCO₂e/kWh",
                  "Consumption-based lifecycle intensity is the proposed map indicator. Keep production intensity separately.",
                ],
                [
                  "Outages, curtailment and availability",
                  "TSOs and ENTSO-E where published · MW / MWh",
                  "Needed to explain events and test whether additional supply could actually be delivered. Coverage not yet established.",
                ],
              ]}
            />
            <h3 className="mt-8 text-lg font-semibold">Carbon accounting and flow tracing</h3>
            <Paragraph>
              Production intensity weights generation by technology-specific emission factors.
              Consumption intensity also accounts for imports. Flow tracing mixes each zone’s local
              generation with imports and solves the connected zones together, so electricity can be
              traced through transit countries and loops. It describes the observed system; it does
              not predict the response to a new investment.
            </Paragraph>
            <Paragraph>
              The research pilot uses ENTSO-E data and IPCC lifecycle factors without Electricity
              Maps as a calculation input. Its August 2026 network includes 32 borders. Great
              Britain’s unavailable generation and Norway’s incomplete storage data remain
              unresolved import sources. Unmapped fuels, external supply and stored electricity
              receive explicit uncertainty; hypothetical factors of 0 and 1,500 gCO₂e/kWh produce
              sensitivity scenarios, not confidence intervals.
            </Paragraph>
            <Note title="Geography and quality travel with every value">
              Germany and the Germany–Luxembourg bidding zone are different areas. DK1 and DK2
              remain separate. Every series needs its source, area, unit, interval, retrieval date,
              estimation flag and accounting basis. Missing values remain missing. Energy-balance
              discrepancies are reported, not automatically labeled grid losses.
            </Note>
            <Paragraph>
              The proposed data gate reports valid hours / expected hours for each signal and each
              comparison. Require complete underlying intervals when aggregating hourly data, and
              average carbon intensity using the relevant energy weights. A missing price does not
              erase an otherwise useful carbon observation, but that hour cannot support a joint
              price-and-carbon indicator.
            </Paragraph>
          </Section>

          <Section id="targets" number="1" title="Finding targets">
            <Paragraph>
              <strong className="text-foreground">Implemented screening snapshot:</strong> one
              target per configured border and selected period, with separate directional summaries.
              Store the underlying events so every highlight can be inspected. A day counts once if
              it contains at least one qualifying event interval; missing intervals and direction
              reversals break event continuity.
            </Paragraph>
            <Note title="Europe-wide results and evidence">
              <Link to="/targets" className="underline">
                Open European target evidence →
              </Link>
              <p className="mt-2">
                The first run screens 107 configured borders across 54 zones for 12 August–10
                September 2026. Eighty borders meet the price-coverage gate, of which 79 have
                qualifying events. Twenty-three have no comparable prices and four have low
                coverage. This uses archived Electricity Maps prices and consumption-based lifecycle
                carbon, not the independent ENTSO-E carbon pilot.
              </p>
              <p className="mt-2">
                Only EUR/MWh observations are compared. GBP, MDL and TRY are excluded until explicit
                exchange rates are available. Rank requires at least 80% matched price coverage and
                one event; the 80% gate is an exploratory setting, not a quality certification.
                Unranked borders remain inspectable. Configured connections are not yet
                independently verified as operational.
              </p>
            </Note>
            <Table
              headers={["Indicator", "Definition", "Interpretation"]}
              rows={[
                [
                  "Price-spread frequency",
                  "Share of matched hours with |price B − price A| ≥ τ. Snapshot τ = EUR 10/MWh; configurable when regenerating the snapshot.",
                  "Report event hours, eligible hours and affected UTC days. The threshold is a screening choice, not an ENTSO-E standard.",
                ],
                [
                  "Spread magnitude and persistence",
                  "Mean and 95th percentile absolute spread on event hours; longest consecutive event duration. Report A→B and B→A separately.",
                  "Shows recurrence and severity. Rank initially by event-hour share, then mean event spread; display coverage alongside rank.",
                ],
                [
                  "Capacity evidence",
                  "Event-time physical flows, scheduled exchanges and published directional capacity, with their distinct definitions.",
                  "A flow/capacity ratio is interpretable only for compatible measurements. Flow-based market coupling cannot be reduced to a universal bilateral spare-MW number.",
                ],
                [
                  "Directional carbon contrast",
                  "For the cheaper-to-dearer direction: receiving-zone consumption intensity − sending-zone consumption intensity, in gCO₂e/kWh.",
                  "Positive means cheaper electricity coincides with a cleaner sending-zone average. It is context, not marginal avoided emissions.",
                ],
                [
                  "Joint opportunity hours",
                  "Matched event hours with positive directional carbon contrast. The snapshot uses archived point estimates and reports its carbon denominator. Uncertainty-aware comparison remains proposed for the independent carbon model.",
                  "Highlights aligned market and climate signals without assigning a speculative euro or CO₂ benefit.",
                ],
                [
                  "Supply evidence",
                  "Coincident curtailment, negative prices, generation mix, net exports, outages and available generation where observed.",
                  "Cheap electricity does not prove excess renewable production. Installed capacity minus output does not prove available export supply.",
                ],
              ]}
            />
            <h3 className="mt-8 text-lg font-semibold">A small example</h3>
            <Paragraph>
              Suppose a border has 600 matched hours out of 720 expected. It shows a qualifying
              spread in 120 hours across 18 days: its event frequency is 20%, with 83.3% price
              coverage. If carbon data is usable for only 90 of those event hours and 60 show a
              positive contrast, report 60 / 90 eligible hours—not 60 / 120. Capacity remains
              “unknown” if no compatible event-time series exists.
            </Paragraph>
            <Paragraph>
              Event spreads use arithmetic hourly means; the 95th percentile uses linear
              interpolation between sorted observations. The downloadable evidence includes
              directional summaries, complete event intervals, estimated-carbon event counts and
              topology provenance. Capacity and supply sufficiency are not assessed by this
              snapshot. Carbon contrast is not used to invent avoided tonnes or market losses.
            </Paragraph>
            <Note title="The existing workbench still uses a separate calculation">
              The workbench map retrieves precomputed targets ordered by a market-loss field and
              calls a database calculation with a EUR 1/MWh spread threshold, a 0.98 congestion
              ratio and a 0.1 relief share. The database calculation is not defined in this
              checkout, so its full formula is not verified here. The capacity overlay uses a
              maximum from a seven-day window. The new /targets evidence page uses the event-level
              calculation above; its research identifiers are not passed into existing scenario
              records.
            </Note>
            <h3 className="mt-8 text-lg font-semibold">Bridge from the pilot to the target map</h3>
            <ol className="mt-4 list-decimal space-y-3 pl-5 leading-7 text-muted-foreground">
              <li>
                Implemented: join archived prices and carbon by exact zone and UTC interval, with
                separate coverage counts and versioned output.
              </li>
              <li>
                Implemented: export spread events and directional statistics; display the period and
                threshold in the evidence page. Next: uncertainty-aware independent carbon and map
                integration.
              </li>
              <li>
                Attach event-time capacity, flows and supply evidence. Separate “price divergence
                observed” from “constraint evidence available.”
              </li>
              <li>
                Implemented: inspectable evidence cards with source links and missing inputs. Next:
                compare multiple thresholds, add exchange rates, expand independent data coverage
                and refresh the archive.
              </li>
            </ol>
          </Section>

          <Section id="scenarios" number="2" title="Simulating scenarios">
            <Paragraph>
              <strong className="text-foreground">Proposed method:</strong> compare a baseline with
              candidate investments under identical demand, weather, fuel-price and network
              assumptions. Candidates can add transmission, solar, wind, storage or combinations. A
              EUR 10 million budget is an investment constraint; translating it into MW requires
              explicit cost, location and delivery assumptions.
            </Paragraph>
            <Table
              headers={["Model element", "Required treatment"]}
              rows={[
                [
                  "Baseline",
                  "Reproduce observed generation, flows and prices within documented tolerances before interpreting project differences. Record model geography and boundary imports.",
                ],
                [
                  "New transmission",
                  "Directional capacity, availability, losses, delivery date and network constraints. A transport model is a simplification, not a full AC power-flow or market-coupling implementation.",
                ],
                [
                  "Solar and wind",
                  "Location-specific hourly availability, installed capacity, curtailment and grid connection limits. Apply the same weather to every candidate.",
                ],
                [
                  "Storage",
                  "Power and energy capacity, charging/discharging efficiency, state of charge, initial and terminal conditions, degradation and charging-origin emissions.",
                ],
                [
                  "System response",
                  "Estimate which generators change output and how flows change. Run flow tracing on the resulting dispatch if consumption footprints are needed.",
                ],
                [
                  "Sensitivity",
                  "Repeat across weather years, fuel/carbon prices, demand, capital costs and delivery delays. Report what changes the preferred option.",
                ],
              ]}
            />
            <Note title="European ENTSO-E input pipeline">
              <p>
                The August dataset uses the ENTSO-E API: A44 prices, A75 realised generation, A65
                demand, A11 physical exchanges and A61 day-ahead estimated transfer capacity. Raw
                responses are cached with request hashes. Electricity Maps is not an input.
              </p>
              <p className="mt-2">
                Border directions and Sweden’s four bidding zones remain separate. Only complete UTC
                hours are observations. Published A03 blocks are decoded through their validity
                intervals; actual gaps are not interpolated or zero-filled. Missing capacity is
                never copied from the opposite direction or inferred from flow. Different generation
                and demand domains block acceptance until reconciled.
              </p>
              <p className="mt-2">
                The historical balance includes reported storage charging and discharge. Dispatch
                requires complete required quantities and an absolute balance residual at most 5% of
                demand in every zone. Missing prices remain unknown validation observations. This
                initial data gate is not market validation: A61 is estimated NTC, not the complete
                flow-based constraint set, and generator availability remains assumed.
              </p>
              <p className="mt-2">
                <a href="/research/eu-input-quality.json" className="underline">
                  Input coverage and balance report
                </a>
                {" · "}
                <a href="/research/eu-model-validation.json" className="underline">
                  European baseline status
                </a>
              </p>
            </Note>
            <Note title="PyPSA-Eur: European border opportunity model">
              <p className="mb-3">
                Weather preparation now processes one month at a time under a disk-space monitor.
                Verified wind and solar conversion profiles are retained; only their reproducible
                raw weather is removed. Annual regional weighting and the linked full-year dispatch
                remain unchanged. The completed annual hydro runoff file is kept separately. The
                monitor stops near the 10 GiB weather budget or when free disk space becomes low;
                this is not a guarantee of total model disk usage.
              </p>
              <p className="mb-3">
                Production now targets the full 2025 calendar year (8,760 hours), with March as a
                pipeline test. The annual baseline has not been solved or validated yet. Full-year
                weather uses a separate file from the March sample; existing weather files do not
                automatically expand to cover new dates. Current configurations enable upstream
                demand estimates and gap filling, which must be disclosed and audited before any
                result is labelled validated. The January work below remains an earlier source-data
                and method experiment.
              </p>
              <p>
                The new physical-system workflow uses pinned PyPSA-Eur v2026.08.0 and its European
                network. Each country border is tested independently with 100 MW of additional
                transfer allowance distributed across its existing AC/DC connections. January
                opportunity is the decrease in total system operating cost, in €million for the
                month. Impedances remain fixed: this is capacity relief, not the design of a new AC
                line. Independent border benefits cannot be summed or annualised.
              </p>
              <p className="mt-2">
                The network inventory is a February 2026 source snapshot and still needs January
                asset reconciliation. ENTSO-E quantities, flows and prices and JAO congestion
                evidence must validate the baseline. Publication coverage alone is insufficient. On
                the targets network, grey means unavailable. Experimental computed values require an
                explicit toggle; validated opportunity remains empty until checks pass.
              </p>
              <p className="mt-2">
                The first source inventory contains 34 countries and 74 international connections.
                The pinned ENTSO-E-derived demand archive has complete January hours for 18 of those
                countries. Demand gap filling is disabled; January weather, asset availability and
                remaining quantities must be prepared before the operational baseline can run.
              </p>
              <a href="/research/pypsa-input-audit.json" className="underline">
                Input audit
              </a>
              {" · "}
              <a href="/research/pypsa-targets.json" className="underline">
                European border dataset
              </a>
            </Note>
            <Note title="JAO network restrictions">
              <p>
                The research pipeline now collects JAO Core flow-based domains: available margins
                and the coefficients relating zonal net exports to network loading. It retains
                virtual HVDC hubs and keeps these constraints separate from bilateral NTC limits.
                ENTSO-E quantities constrain estimated supply and demand; ENTSO-E observed prices
                remain validation data.
              </p>
              <p className="mt-2">
                For 1 January 2026, 00:00–01:00 UTC, all 14,052 published Core constraints were
                checked against JAO’s four quarter-hour net positions. The largest residual was
                0.014 MW, below the declared 0.1 MW rounding tolerance. This checks the network
                data, not the estimated offers or investment benefits. January downloads use the
                published presolved filter to retain nonredundant constraints.
              </p>
              <p className="mt-2">
                January coverage is complete for Core’s 744 hourly domains and Nordic’s 2,976
                quarter-hour domains. Alongside ENTSO-E NTC, regional publication evidence now
                covers 82 of the graph’s 102 directional entries. This is evidence availability, not
                82 independent transfer limits or a validated market simulation.
              </p>
              <p className="mt-2">
                The solver supports shared flow-based restrictions, but the real-data market adapter
                still needs virtual-hub coupling, long-term-rights inclusion and allocation limits.
                Quantity and geography gates remain in force. The Nordic adapter uses its own filter
                schema and preserves quarter-hour domains; Core and Nordic data are not
                interchangeable.
              </p>
              <p className="mt-2">
                <a href="/research/jao-network-validation.json" className="underline">
                  Network validation
                </a>
                {" · "}
                <a href="/research/jao-january-coverage.json" className="underline">
                  January Core coverage
                </a>
                {" · "}
                <a href="/research/jao-nordic-january-coverage.json" className="underline">
                  January Nordic coverage
                </a>
                {" · "}
                <a href="/research/network-evidence-coverage.json" className="underline">
                  Combined network evidence
                </a>
              </p>
            </Note>
            <Note title="Planned annual market-opportunity model">
              <p>
                January and August 2026 are checked with identical input rules. Older observations
                may have more complete reporting, but moving the baseline does not fix missing
                constraint definitions or zone mismatches. Published A03 price blocks are decoded
                before measuring coverage, and intraday prices are excluded.{" "}
                <a href="/research/eu-month-comparison.json" className="underline">
                  Compare monthly data coverage
                </a>
                . A single winter month cannot establish annual benefits.
              </p>
              <a href="/research/market-model-plan.md" className="underline">
                Read or download the implementation plan →
              </a>
              <p className="mt-2">
                First construct and validate estimated supply offers under historical market
                constraints. Then hold those offers, demand, availability and initial energy
                inventories fixed and relax a precisely identified transmission constraint.
                Generation, prices and storage operation are allowed to change.
              </p>
              <p className="mt-2">
                The annual indicator is baseline modeled system cost minus counterfactual cost, in
                M€/year before investment costs. Run the full linked year, including hours without
                observed price spreads; report hourly contributions afterward. Capacity minus output
                is headroom, not automatically available economic supply.
              </p>
              <p className="mt-2">
                This requires additional generator-availability, cost and historical constraint
                data. The planned optimizer is a documented approximation to market clearing, not
                the EUPHEMIA production algorithm. Baseline validation and a complete modeled period
                are required before publishing annual opportunity rankings.
              </p>
            </Note>
            <Note title="Current simulator limitations">
              The prototype uses a local zonal price-response model and observed maximum flows as
              transfer limits. It is not a verified reproduction of Euphemia. Historical average
              carbon intensities do not establish marginal emissions. Missing carbon/load
              observations are currently held in zero-initialized arrays in parts of the model;
              quality gating must be fixed before those results support investment claims.
            </Note>
          </Section>

          <Section id="evaluation" number="3" title="Evaluating opportunities">
            <Paragraph>
              Evaluate the same system and time horizon with and without each project. Present
              economic, climate and delivery outcomes together. The framework is informed by
              ENTSO-E’s fourth cost-benefit guideline; this prototype does not claim a compliant
              TYNDP assessment or official indicator numbering.
            </Paragraph>
            <Table
              headers={["Outcome", "Proposed KPI and accounting rule"]}
              rows={[
                [
                  "Local prices",
                  "Demand-weighted mean price change per zone: Σ load × (scenario price − baseline price) / Σ load. Also show high-price hours and who gains or loses.",
                ],
                [
                  "Economic benefit",
                  "Change in system welfare or consistently defined system cost. Consumer bill savings and congestion revenues are distributional effects; do not simply add them as independent benefits.",
                ],
                [
                  "Climate benefit",
                  "Baseline system emissions − scenario system emissions, in tonnes CO₂e over the modeled period. Report operational changes and project lifecycle emissions separately. A carbon-intensity gap × extra flow is not a causal estimate.",
                ],
                [
                  "Renewable integration",
                  "Reduction in curtailed renewable energy, in MWh. Additional border transfers are not automatically additional renewable integration.",
                ],
                [
                  "Reliability",
                  "Expected energy not served and other adequacy/security measures where supported by the model. Fewer spread hours are not a security-of-supply result.",
                ],
                [
                  "Investment case",
                  "Capital, operating and replacement costs, delivery time, lifetime and residual value. Discount benefits and costs on a common price basis; disclose the discount rate.",
                ],
              ]}
            />
            <Paragraph>
              For discounted net present value, sum each year’s net benefit divided by (1 + discount
              rate) raised to that year, including investment costs at their actual timing. Discount
              the numerator and denominator of the benefit–cost ratio consistently. Keep carbon
              valuation explicit and avoid counting carbon costs twice when they already enter
              modeled operating costs.
            </Paragraph>
            <Note title="Current evaluation is illustrative">
              The app’s field labeled “25-year NPV” currently equals annual market benefit × 25
              minus capital cost, without discounting. Its renewable-integration, losses and
              security labels also include simplified proxies. The B1–B9 labels should not be
              interpreted as an audited mapping to ENTSO-E’s official indicators. A partial
              historical window is annualized in the prototype; that extrapolation is not a seasonal
              forecast.
            </Note>
            <Paragraph>
              The proposed comparison card reports the baseline, modeled dates, coverage, costs,
              price effects, emissions change, uncertainty and delivery assumptions for each
              candidate. An option becomes a recommendation only after its result is robust to those
              assumptions and its connection feasibility has been assessed.
            </Paragraph>
          </Section>

          <section
            id="references"
            className="scroll-mt-24 border-t border-border py-10"
            aria-labelledby="references-title"
          >
            <h2 id="references-title" className="text-xl font-semibold">
              Sources & references
            </h2>
            <ul className="mt-4 space-y-3 text-sm leading-6">
              {[
                [
                  "ENTSO-E: data catalogue and API documentation",
                  "https://transparencyplatform.zendesk.com/hc/en-us/articles/17260622859412-Transparency-Platform-Help-page",
                ],
                [
                  "IPCC AR5 Annex III: lifecycle emission factors",
                  "https://archive.ipcc.ch/pdf/assessment-report/ar5/wg3/ipcc_wg3_ar5_annex-iii.pdf",
                ],
                [
                  "Real-Time Carbon Accounting Method for the European Electricity Markets",
                  "https://arxiv.org/abs/1812.06679",
                ],
                [
                  "Electricity Maps: historical carbon intensity and accounting options",
                  "https://app.electricitymaps.com/docs/reference/carbon-intensity/past-range",
                ],
                [
                  "ENTSO-E: final fourth cost-benefit guideline, approved in 2024",
                  "https://www.entsoe.eu/news/2024/04/09/entso-e-publishes-the-final-guideline-for-cost-benefit-analysis-of-grid-development-projects/",
                ],
              ].map(([label, url]) => (
                <li key={url}>
                  <a
                    href={url}
                    className="underline decoration-border underline-offset-4 hover:decoration-foreground"
                  >
                    {label} ↗
                  </a>
                </li>
              ))}
            </ul>
            <Paragraph>
              This version documents the reviewed prototype and the intended measurement contract.
              Method changes should update the version, formulas and implementation status together,
              so saved results remain interpretable.
            </Paragraph>
          </section>
        </main>
      </div>
    </div>
  );
}
