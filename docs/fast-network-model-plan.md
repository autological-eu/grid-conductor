# Fast network model: implementation plan

## Implementation status — 30 September 2026

The first experimental browser implementation is published at `/network`. The
strict schema, sparse HiGHS/WASM worker, paired dispatch, chronological storage,
energy/ramp restrictions, optional PTDF/RAM, local workspace persistence, source
audit, explicit linked-input exporter and numerical reference fixtures are in
place. Exact independent-hour decomposition addresses the first measured memory
bottleneck. Methods, measured timings and prototype limits are documented in
[fast-network-model.md](fast-network-model.md).

This is **engine progress, not completion of the research gates below**. The solved
PyPSA NetCDF and baseline manifest are absent; no reviewed European annual input,
matched baseline/counterfactual fidelity report, within-zone model or discounted
investment appraisal has been published. Native PyPSA reduction still requires
source recovery and explicit handling of unsupported physics. The current lab
retains one input/intervention workspace and recomputes results after reload; full
versioned named network scenarios remain future work. Existing map scenarios and
screening methodology continue unchanged.

Planning document, 30 September 2026. This proposes a new experimental research
model; it does not change the existing screening methodology or assert that the
new model has been implemented or validated.

## Decision and objective

Build a small, coupled electricity-dispatch model for interactive interventions.
Reuse cached hourly inputs and retain meaningful bidding-zone bottlenecks. Assess
finite investments through paired baseline/scenario optimisation, rather than
adding independent border price-spread triangles.

The operational benefit is:

```text
B = (baseline system operating cost − scenario operating cost) / 1,000,000
```

B is gross system benefit for the modelled period, not investor revenue. Project
capex, operating costs, delivery delays and discounted financial indicators are a
separate layer. Period results become annual only for an explicitly complete
calendar-year calculation. Climate benefits require signed changes in dispatch
and consistent emissions factors; missing factors produce unavailable results.

The public application remains static Bun/Vite/React/TanStack Router on GitHub
Pages, with browser-local scenarios. Weather collection and detailed PyPSA runs
remain offline. No cloud solver, paid service or research credentials enter the
browser.

## Repository findings that determine the plan

- `tools/market_model.py` already implements a sparse SciPy/HiGHS coupled LP:
  zonal balance, directional transfers, generation limits, optional ramps and
  energy budgets, chronological storage, and optional PTDF/RAM regions. Reuse
  this as a formulation reference and regression oracle where assumptions match.
- `tools/assemble_eu_market.py` fails closed on missing research quantities and
  capacity directions. It also uses fixed observed output and assumed thermal
  bands in places. Those assumptions must remain explicit; it is not a ready,
  validated annual availability dataset.
- The European input gate is currently blocked. The FR–CH pilot fails its
  published validation gates. Neither status may be upgraded by this refactor.
- `pypsa` and `codex/carbon-pilot` contain full-calendar-2025 baseline exports:
  8,760 hours, 34 countries, 40 buses. Sweden and Poland each have one bus. Their
  target artifact contains rent and marginal-capacity diagnostics, but all finite
  counterfactual benefit fields remain null.
- The audited PyPSA reference is `codex/carbon-pilot` commit
  `11660d34f760c9dae1ee1ddeffa6346a2b283cc2`; the network hash recorded there is
  `4b6f45e1d7f803aada037d965db925acc3c5a992ac3430e21e1887393382e738`.
- That solved NetCDF, its preparation manifest and weather files are not in this
  checkout. Published generation/load/price/flow CSVs cannot reconstruct all
  generation availability, operating costs or intertemporal constraints.
- `public-v1` carries an older PyPSA topology inventory. Integrate selected
  research artifacts deliberately; do not merge either older application branch
  wholesale or restore its server/SQLite architecture.
- The present browser scenario model remains exact within its stated screening
  assumptions. Keep its outputs and tests unchanged while developing the new
  engine under a separate model identifier.

## Phase 0 — recover inputs and define the comparison

### Tasks

1. Inventory research outputs on all relevant branches. Record source commits,
   hashes, periods, geography, solver versions and validation status. Distinguish
   a successfully solved LP from a validated historical market model.
2. Recover the solved PyPSA NetCDF and matching provenance manifest from the
   research machine, or obtain a compact export containing the inputs listed in
   Phase 1. Verify hashes before reuse. Do not redownload/rebuild weather merely
   to evaluate a transmission intervention.
3. Document the existing price/flow discrepancy before fitting anything: observed
   SE4–PL screening versus the single-country Swedish PyPSA node; saved-build
   prices versus dual-assigned re-solve prices; generation/cost/input assumptions.
4. Define paired experiments with identical periods and intervention semantics:
   baseline, independent +100/+500/+1,000 MW cases, a small battery case, and a
   mixed line/storage case. Directional relief and bidirectional relief are
   separate experiments. Raising transfer allowance is not building an AC
   circuit: a new circuit would also alter impedance and network flows.
5. Select one additional meshed-network case. Do not infer an internal-zone case
   from country-level exports; require actual sub-zone nodes/constraints first.

### Deliverable and gate

An input inventory and comparison protocol. Exported country-level data can
support diagnostics immediately. A SE4-labelled dispatch experiment requires
explicit SE4 inputs and geography. Missing source data blocks that experiment;
it must not be replaced with a fictional supply curve, inferred physical rating
or fabricated renewable profile.

Engine development with clearly labelled analytical test fixtures can proceed
while this data gate is open. Such fixtures are tests, not published research.

## Phase 1 — canonical input schema and offline exporter

### Proposed files

- `tools/export_fast_network.py`: PyPSA/prepared-research input export.
- `tools/audit_fast_network.py`: independent completeness/provenance audit.
- `src/lib/network-model/schema.ts`: browser schema validation and types.
- `public/research/network-model/<dataset-id>/`: approved compact publications.

### Required inputs

- Consecutive UTC timestamps, interval duration, explicit start/end-exclusive and
  complete-coverage declaration. No representative-period weighting in v1.
- Nodes with explicit bidding-zone mapping; internal nodes distinguished from
  market zones. Country prefixes do not resolve split bidding zones.
- Demand and a declared treatment of external exchanges. Internal exchanges are
  endogenous; do not also inject their historical flows into balance equations.
- Generator blocks: node, installed capacity, hourly min/max availability,
  marginal costs and their fuel/carbon components, emissions basis, and supported
  energy/ramp restrictions. Record every aggregation rule.
- Wind/solar availability profiles prepared once. Historical generation may be
  used only as a labelled proxy: observed dispatch can include curtailment and
  does not establish unconstrained resource availability.
- Hydro: distinguish run-of-river availability, reservoir inflows/inventory and
  an explicitly supported energy-budget approximation. Observed reservoir output
  is a dispatch decision, not an exogenous weather profile.
- Storage: charge/discharge power, energy capacity, efficiencies, initial and
  terminal inventories, standing losses/inflows where relevant, throughput costs
  and provenance. Unsupported physical features fail or require a declared
  reduction; they are not silently discarded.
- Transfer bounds by direction and hour with source and physical/market meaning.
  Model thermal ratings, commercial NTC/ATC and JAO RAM remain distinct concepts.
  Missing published capacity is not filled from scheduled-flow medians.
- Optional mapped flow-based regions: PTDF coefficients, RAM, market-domain
  mapping and time coverage. Prevent internal bilateral constraints from
  double-counting the same regional network representation.
- Source hashes, upstream versions, assumptions, exclusions, validation status
  and known limitations. Keep observations separate from calibration parameters.

### Gate

Round-trip export/import, timestamp/shape/unit validation, no nonfinite values,
no hidden zero filling, and supported-physics audit. Large source caches and
NetCDF files remain ignored. Publish only reviewed, compact artifacts with
appropriate source attribution; independently assess whether each artifact is
ready for an experimental calculation or remains blocked.

## Phase 2 — formulation and numerical reference

Create an explicit formulation specification and a narrow adapter around the
existing Python solver. Add required schema features in a versioned way rather
than changing the FR–CH experiment implicitly.

Baseline and scenario share fixed demand, existing capacities, availability,
weather and fuel assumptions. Scenario patches change only recorded assets or
constraints. Re-optimise all eligible dispatch and storage across the coupled
network; do not freeze baseline dispatch or sum independent project benefits.

Initial formulation:

- Zonal energy balances and bounded transfers; lossless transport as a declared
  first approximation. Loss modelling is a separate versioned extension.
- Bounded generation blocks with curtailment allowed where physically applicable.
- Chronological battery charge/discharge and state of charge. Reconcile round-trip
  efficiency with per-leg efficiencies; do not apply the loss factor twice.
- Explicit initial/terminal inventory and energy accounting. No free discharge of
  initial inventory and no unnoticed end-of-window depletion.
- Reservoir energy budgets as a declared simplification; support chronological
  reservoir inflows/inventory where recovered inputs require them.
- Existing optional ramp and flow-based constraints where data supports them.
- Load shedding as an explicit diagnostic variable with a declared penalty.
  Separate shortage reduction from ordinary dispatch savings. Any material
  shortage blocks an investment-benefit ranking in this first release.
- Detect simultaneous charging/discharging and other material cycling artefacts.
  Negative costs and prices require particular care. Any corrective operating
  restriction or regularisation must be documented and sensitivity-tested.

No unit commitment, detailed AC load flow, automatic N−1 certification or exact
Euphemia auction replay is claimed. Full-horizon storage optimisation assumes
perfect foresight and must be labelled accordingly.

### Numerical gate

Use analytical two-node and three-node tests, a constrained meshed/flow-based
case, a chronological battery case and an energy-limited hydro case. Verify
balance, capacity, inventory, energy, emissions and objective accounting. Test
that an unchanged scenario gives zero benefit and constraint relaxation cannot
increase optimal cost beyond declared numerical tolerance.

Objective agreement matters more than identical individual flows/prices where
multiple optima exist. Check finite differences of capacity relief against duals
for small perturbations, including sign and time-weight conventions.

## Phase 3 — browser solver feasibility and benchmark

### Tasks

1. Define a solver interface with immutable input, typed scenario patches,
   objective/status diagnostics and cancellation semantics.
2. Benchmark compiled HiGHS/WASM candidates against the existing JavaScript
   solver on the same formulation. Check licensing, package provenance and the
   repository's dependency release-age rule. Resolve the documented Bun ESM/WASM
   problem explicitly; do not assume browser compatibility from Node success.
3. Test Vite production builds and GitHub Pages base-aware WASM loading. Prefer a
   self-contained worker that does not require hosting headers unavailable on
   Pages or a remote CDN.
4. Cache parsed inputs and baseline results by dataset hash, formulation/solver
   version and all relevant solve options. Reuse matrix structure and warm starts
   only where supported and verified.
5. Run in a Web Worker. Keep the map responsive; report preparation, baseline and
   scenario progress separately. Terminate/recreate a worker to cancel a blocking
   solve if its solver lacks a safe interrupt API. Reject stale results.

### Benchmark protocol and gate

Measure download/decompression, parsing, matrix construction, baseline solve,
scenario solve, peak memory and worker responsiveness separately. Record cold and
warm runs, several repetitions, hardware, browser, solver/version and tolerances.
Cases span 24/168/8,760 hours, real candidate network sizes, line-only and
chronological-storage constraints. Do not benchmark only the two-node toy.

Provisional UX targets: warm small cases in about two seconds and a full-year
transmission case within ten seconds on a reference desktop. These are goals,
not promises. Select mobile memory and runtime budgets after measuring devices.
Full-year storage may need a longer explicitly reported solve.

If browser annual solves fail practical budgets, offer bounded chronological
windows for interactive experiments and exact offline annual reference results.
Do not label a short-window solve annual. Retain chronological constraints;
representative periods, rolling horizons and reservoir budget decomposition need
separate error assessments before adoption. Fixed dispatch caching does not
replace counterfactual re-optimisation.

## Phase 4 — two distinct validation exercises

### A. Numerical implementation equivalence

On identical inputs and constraints, compare browser outputs with the Python
reference. Predeclare scaled objective/residual tolerances and reject nonoptimal,
infeasible, unbounded, timed-out or numerically unreliable solves. This establishes
implementation agreement; it does not validate the economics.

### B. Historical and simplification validity

Compare baseline prices, generation, demand, exchanges, curtailment and storage
behaviour with ENTSO-E and other suitable observations. Distinguish physical flows
from scheduled exchanges and nodal dual prices from zonal auction prices.

Separate calibration and held-out periods spanning seasons and scarcity events.
Avoid using fixed observed generation both as model input and as supposed
independent validation. Report bias, MAE, congestion duration, energy errors,
coverage and uncertainty. Predeclare acceptance thresholds and benchmark against
simple baselines before fitting. Preserve existing failed gates.

For selected investments, compare fast-model cost reductions with paired detailed
PyPSA re-solves. Use the same period, intervention direction, added MW, storage,
costs and boundary conditions. Geography reduction must be explicit. Validate
both baseline behaviour and benefit sensitivity: baseline agreement alone does
not establish accurate counterfactual benefits.

Deliver a comparison table showing observed-spread screening, baseline rent,
marginal capacity value and finite intervention benefit as separate quantities.
Missing PyPSA counterfactuals stay missing. Results stay experimental until the
predeclared acceptance workflow is satisfied; no automatic confidence promotion.

## Phase 5 — experimental workbench integration

Only integrate after numerical gates pass and at least one genuine input dataset
is usable under clearly documented experimental assumptions.

- Add an explicit model choice: existing screening versus fast network experiment.
  Keep the map as the landing page and retain observed evidence alongside results.
- Select intervention nodes/constraints explicitly. A line increases the chosen
  corridor allowance; a battery has a real model node and chronology. Internal
  investments require supported sub-zone geography.
- Display system operating-cost reduction, period, baseline/scenario costs,
  shortage, key dispatch/flow changes, constraints and validation status.
  Distinguish gross welfare, project finance and investor revenue.
- Store model ID/version, dataset hash, solver/options, window, intervention
  parameters and results in IndexedDB. Version its schema with a migration that
  preserves existing screening scenarios. Prevent comparing incompatible runs.
- Replace the legacy undiscounted finance calculation only within the new model's
  explicitly specified appraisal layer. Store discount rate, lifetime, delivery,
  capex/OPEX and price assumptions; show sensitivity rather than pretend forecasts
  are known. Do not silently reinterpret old result fields.
- Report signed dispatch-based emissions only when the input factors and model
  boundary support them. Keep current unsigned screening proxies separately
  labelled; do not combine them into one confidence-ranked climate number.
- Permit input-complete experimental datasets with prominent limitations; block
  missing/unsupported inputs and material shortage. Exportable results include
  assumptions and provenance.

## Phase 6 — publication, verification and deployment

Update Markdown methods/comparison documents, README and AGENTS with actual
implementation, measured runtime, data readiness and retained limitations. Add
reproducible offline export/audit/benchmark commands and immutable publication
manifests. No real research data is replaced by test fixtures.

Verification includes frozen dependency install, lint, strict TypeScript, targeted
solver/persistence tests, existing model parity tests and production build.
Chromium checks cover real worker/WASM loading, cancellation, scenario edits,
reload persistence, desktop/mobile responsiveness, direct research routes and
production asset paths. CI then deploys to Pages and checks the public site.

Use coherent commits on `public-v1` and update the review PR. Do not merge main,
rewrite history or publish a changed default methodology without explicit review.
A successfully deployed prototype remains experimental if research gates fail.

## Milestones and completion criteria

1. **Input-ready:** audited source inventory and at least one complete compact
   dataset; explicit record of which cases remain blocked.
2. **Engine-ready:** reference/browser parity, physical invariants and production
   worker loading pass; measured performance report is available.
3. **Research-ready:** real SE4–PL or explicitly country-level preliminary case,
   meshed case and storage case have evidence/comparison reports with honest
   validation status. Missing detailed re-solves are identified, not fabricated.
4. **Public prototype:** users can create, persist and evaluate supported network
   interventions on Pages and inspect provenance/assumptions. Existing screening
   continues to work.
5. **Investment-screening acceptance:** baseline and counterfactual accuracy meet
   predeclared research gates. This is a separate milestone from shipping the
   experimental prototype.

Work can proceed through schema, reference formulation and analytical tests while
source recovery is pending. The data gate determines whether real full-year
experiments can run. Do not spend time rebuilding all European weather or an
elaborate new frontend before establishing that boundary.

## Measured progress: 30 September 2026

The experimental browser prototype now has a real prepared **weekly** European
input and a [matched PyPSA comparison](network-benchmark-comparison.md). The
37-physical-cluster archive preserves weather availability and reservoir inflow;
schema v2 adds explicit reservoir/cyclic chronology while v1 stays compatible.
Transport numerical parity passes, and source-network Kirchhoff comparisons
measure a nontrivial benefit approximation error. This closes the compact
technical-input and solver-benchmark milestones, not annual historical validation.

A separate [carbon-price study](network-carbon-sensitivity.md) shows why economic
and climate benefit require explicit policy assumptions and paired baselines.
The public lab loads the archived benchmark and persists interventions locally.
Full-year 2025 input recovery, modern calibration, seasonal robustness, named
network scenarios, security constraints and investment appraisal remain open.
The original map retains its existing screening model.
