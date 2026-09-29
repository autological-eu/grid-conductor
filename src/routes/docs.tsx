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
                  "PyPSA-Eur nodal LMP · EUR/MWh",
                  "Matched prices define spread events. Prices are the marginal cost of energy at each country bus from the offline PyPSA-Eur solve, not a day-ahead market quotation.",
                ],
                [
                  "Generation by technology",
                  "ENTSO-E · MW, integrated to MWh",
                  "Available in the independent research pilot; feeds generation emissions and flow tracing.",
                ],
                [
                  "Actual load and physical flows",
                  "ENTSO-E demand in, PyPSA-Eur solved flows out · MW, integrated to MWh",
                  "Demand time series come from the ENTSO-E archive; flows are the solved network state. Measure demand, transfers and energy-balance consistency.",
                ],
                [
                  "Transfer capacity",
                  "PyPSA-Eur network topology · directional MW; ENTSO-E NTC as an overlay",
                  "Taken from the declared p_nom of each modelled line and link, per direction. A physical flow maximum is not a capacity rating, and capacity is never inferred from observed flow.",
                ],
                [
                  "Carbon intensity",
                  "Independent calculation from PyPSA-Eur generation and demand · gCO₂e/kWh",
                  "Domestic operational intensity: generator emissions (lifecycle factors, efficiency-corrected) divided by domestic load. Imports are not netted out; keep consumption-based accounting separate.",
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
                This page is served from the offline PyPSA-Eur solve, not from a market data feed.
                The published window is the full 2025 calendar year (8,760 hourly snapshots) across
                34 country buses and 75 modelled cross-borders, each rated from the declared
                capacity of its lines and links. Congestion rent is |Δλ| × |actual flow| summed over
                the window; the 75 borders total €10,303M for the year. The largest single exposures
                are CH–IT (€3,198M), ES–FR (€1,668M) and FR–IT (€1,535M).
              </p>
              <p className="mt-2">
                The dataset is marked experimental, not validated. Prices are the marginal cost of
                energy at each bus rather than day-ahead market quotations, so the absolute rent is
                a model quantity, not a realised cash flow. The price basis is unverified: the LMP
                recheck against nodal averages leaves a residual up to €91.1/MWh, and the KKT
                residual between the price gap and the flow duals reaches 958. Both are recorded and
                neither currently gates publication, and both are worse at full-year scale than in
                the March sample. Independent ENTSO-E quantity reconciliation, a JAO market-domain
                check, and any climate validation remain pending, and no annualised or climate
                figure is published.
              </p>
              <p className="mt-2">
                The two capacity measures cross-check each other. Rent ÷ (mean |flow| × hours) and
                marginal value ÷ hours are two estimates of the same shadow price from the same
                solve. They agree within 1.0–1.3× on the strongly binding borders — GR–IT 53.4 vs
                53.9, IT–SI 55.2 vs 57.9, ES–FR 44.7 vs 41.7 — and diverge only where the network is
                meshed, where the price gap across a border is not the dual of any single asset, and
                on slack borders. That is what the KKT residual reports.
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
            <Note title="How the workbench map is served">
              The workbench map reads the same offline baseline dataset as the evidence page. It is
              a static artefact of the PyPSA-Eur solve, bundled on the server and served directly;
              there is no longer a paid hourly feed or a database-side opportunity calculation in
              the request path. Borders are ordered by the market-loss field of that dataset. The
              legacy targets table is kept only to satisfy the scenario foreign key, so identity
              rows are created for borders the database does not yet know; the numbers displayed
              always come from the baseline dataset and are never read back from those rows. The
              capacity overlay still uses the maximum published ENTSO-E transfer capacity over a
              seven-day window where that is available.
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
            <Note title="How the baseline is actually computed">
              <p className="mb-3">
                The baseline is a genuine linear program, solved once offline and then frozen. It
                uses pinned PyPSA-Eur v2026.08.0 (commit a5408e9) and its built European network.
                The full 2025 calendar year, 8,760 hours, is clustered to 40 countries — the minimum
                the clustering supports for the selected set — of which 34 carry a bus. The dispatch
                is solved by HiGHS through pypsa.optimization.solve_model, as an operational problem
                only: no unit commitment, no investment planning, no extension carriers, no CO₂
                limit.
              </p>
              <p className="mb-3">
                Prices are the solve&apos;s own locational marginal prices, the LP duals of the bus
                balance constraints, read from buses_t.marginal_price and averaged over each
                country&apos;s buses. Border prices are therefore not a separately assumed series;
                they are an output of the optimisation. Carbon intensity is computed from the
                dispatched generation, efficiency-corrected, and is an average rather than a
                marginal quantity. Transfer limits are the declared nominal ratings of the existing
                AC lines and DC links in both directions and are never inferred from observed flow;
                reported flow is the net of the physical AC and DC exchange.
              </p>
              <p className="mb-3">
                The solve is validated before publication: the network must have no extendable
                assets, hourly snapshot weights and non-zero load, and the run is recorded in a
                manifest with the network hash, window, cluster count, upstream commit and
                assumptions. The 2025 run produced 8,760 snapshots, 40 buses, 391 generators, 71 AC
                lines and 43 DC links, 3,008 TWh of load, a mean marginal price of 38.26 EUR/MWh and
                754 Mt of operational CO₂.
              </p>
              <p>
                The published border dataset does not re-solve the network per border. It reports
                two measures from the baseline solve and one dual-assigned re-solve: congestion rent
                as the price-gap × actual-flow wedge over the window, and the marginal capacity
                value per MW from the flow-constraint duals, aggregated capacity-proportionally
                across each border&apos;s assets. Exact per-border relief experiments are a
                separate, much more expensive tool and are not published. Ranked annual or per-MW
                opportunity is deliberately not published, and no modelled opportunity figure is
                asserted.
              </p>
            </Note>
            <Note title="PyPSA-Eur: European border opportunity model">
              <p className="mb-3">
                Weather preparation processes one month at a time under a disk-space monitor.
                Verified wind and solar conversion profiles are retained; only their reproducible
                raw weather is removed. Annual regional weighting and the linked full-year dispatch
                are unchanged. The completed annual hydro runoff file is kept separately. The
                monitor stops near the 10 GiB weather budget or when free disk space becomes low;
                this is not a guarantee of total model disk usage.
              </p>
              <p className="mb-3">
                The full 2025 calendar year has been solved and validated, and is the published
                window. March 2025 remains available as a cheaper pipeline test. Full-year weather
                uses a separate file from the March sample; existing weather files do not
                automatically expand to cover new dates. The configuration enables upstream demand
                estimates and gap filling, which must be disclosed and audited before any result is
                labelled validated.
              </p>
              <p className="mb-3">
                Impedances remain fixed throughout. Any capacity experiment is relief on existing AC
                and DC connections, not the design of a new AC line, and does not re-optimise the
                network. Independent border benefits cannot be summed or annualised.
              </p>
              <p>
                ENTSO-E quantities, flows and prices and JAO congestion evidence must validate the
                baseline before it is labelled validated; publication coverage alone is
                insufficient. The price basis is separately unverified: the LMP recheck against
                nodal averages and the KKT residual between the price gap and the flow duals are
                both recorded and neither currently gating. On the targets network, grey means
                unavailable.
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
            <Note title="How a scenario is actually computed">
              <p className="mb-3">
                A scenario is not a re-solve of the European LP. It is a separate and deliberately
                lightweight zonal model around the target border: the two zones plus their direct
                neighbours, 7 to 15 countries. Each hour is cleared independently from the baseline
                nodal prices, flows and declared ATC limits.
              </p>
              <p className="mb-3">
                Each hour maximises social welfare subject to zonal balance and directional ATC
                limits. Candidate transfers are batched one per border, each pushed towards the
                direction that would equalise that border&apos;s two prices. Under the linearised
                zonal supply curves the welfare gain of a batch scaled by a is exactly quadratic,
                with g_e the price difference across border e, s_z zone z&apos;s supply-curve slope,
                and ν_z the net export zone z implies:
              </p>
              <p className="mb-3 rounded-md bg-muted px-3 py-2 font-mono text-xs">
                dW(a) = a · Σ_e x_e g_e − (a² / 2) · Σ_z s_z ν_z(a)²
              </p>
              <p className="mb-3">
                The step length is the exact maximiser of that quadratic, a = G / Q, capped by the
                remaining ATC headroom. Because the direction is already clipped to the headroom,
                the cap is at least 1, so every accepted iteration lands in the increasing region
                and welfare strictly increases: the ascent is monotone by construction. Batching is
                what makes it converge. Transferring on one border at a time with the full step that
                equalises it overshoots that pair, which moves both endpoint prices, makes a
                neighbouring border the new maximum, and re-creates the spread just closed.
              </p>
              <p className="mb-3">
                The supply-curve slope s_z is the one modelling assumption, since the price response
                of a zonal aggregate is not observed directly. It is estimated as each border&apos;s
                mean absolute nodal price difference over the hours that border is binding, divided
                by its binding capacity, and split between the two zones in proportion to load.
                Regressing price on net export was tried first and rejected: with one bus per
                country the marginal price is set by the same system-wide unit, so price is nearly
                common-mode and the fit returns noise (March values −0.0038 to +0.0059, median
                0.00002). Measuring the slope from the same nodal differences the model then
                reproduces also keeps calibration and simulation consistent with one another. It
                remains a proxy, not an identification of the supply curve.
              </p>
              <p>
                Termination is a KKT certificate, not an iteration count: any border still with ATC
                headroom in the profitable direction must have a price difference within 0.01
                EUR/MWh, while a saturated border is allowed to diverge because that divergence is
                the congestion rent. On the full 2025 baseline all 8,760 hours satisfy it with a
                dual residual of 0.00 and no adverse flows, in 22–290 ms per case.
              </p>
            </Note>
            <Note title="What the scenario model does not do">
              The zonal scenario solver is not a verified reproduction of Euphemia, is not an LP
              solve, and is not the production market-coupling algorithm. Because it works from
              country-averaged nodal prices, re-clearing moves prices by roughly 2–10 EUR/MWh
              against the PyPSA LMPs; that zonal approximation error is the dominant uncertainty in
              scenario outputs and is larger than the differences between most candidate projects.
              It models no unit commitment, no block or complex orders, no flow-based domains, no
              network reconfiguration, no losses and no intraday or balancing timeframes. Carbon
              intensities are historical averages, which do not establish marginal emissions.
              Relieving a border can raise congestion rent elsewhere in the sub-network, so the
              sub-network rent total is reported alongside rent on the target border itself.
            </Note>
            <Note title="The scenario solver undervalues heavily congested borders">
              <p className="mb-3">
                The two models measure the value of capacity very differently, and the gap is not
                random. Compared against the full-year LP duals, the value of adding 1,000 MW comes
                out at roughly €365M in both methods on ES–FR, but roughly €472M versus €44M on
                IT–ME, €507M versus €41M on IT–SI, and €587M versus €0.2M on CH–IT. The disagreement
                grows with how congested the border is.
              </p>
              <p>
                The cause is structural. The LP prices scarcity, so a persistent 55–70 EUR/MWh gap
                carries a shadow price all year and extra capacity is worth a lot. The zonal solver
                has no merit order and no scarcity pricing; it represents price response with one
                fitted linear slope, so a wide gap is closed by a modest transfer and the marginal
                value of further capacity collapses to nearly zero. It therefore behaves like a
                local perturbation model around the baseline and should be read that way.
              </p>
              <p>
                Practical consequence: the published marginal capacity values come from the LP
                duals, which price scarcity and are the better measure for investment decisions. The
                scenario solver remains useful for its intended purpose — running fast, interactive
                what-if comparisons and checking that welfare is monotone and concave — but it
                should not be used to rank borders by absolute capacity value, and its ranking
                disagrees with the LP on the most congested borders.
              </p>
            </Note>
            <Note title="How the scenario results were checked">
              <p className="mb-3">
                The value of a scenario is the welfare optimum of an LP in which capacity only
                appears on the right-hand side of flow constraints, so it must be concave and
                non-decreasing in added capacity. Sweeping added capacity from 0 to 8,000 MW and
                differencing the welfare gives a check on the economics that is independent of how
                the solver works, rather than a restatement of it. All tested borders return a
                monotonically declining marginal value of capacity, with welfare non-decreasing
                throughout, and lightly constrained borders correctly decay to zero (CH–IT, EUR 225
                per MW at the margin, falling to 0 by +4,000 MW as its rent goes to zero). This
                confirms the solver is internally consistent. It does not confirm the absolute
                level: the next note explains why the zonal model prices CH–IT near zero when the LP
                prices it as the most valuable border in the network.
              </p>
              <p>
                Congestion rent is the product of flow and shadow price, so it is genuinely
                non-monotone in capacity: relieving a border can raise the rent recorded on it. Only
                welfare is constrained to increase, and it is.
              </p>
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
                  "PyPSA-Eur: an open optimisation-based electricity grid model of Europe",
                  "https://pypsa-eur.readthedocs.io/en/latest/",
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
