# Hourly synthetic zonal clearing — implementation plan

Build a continuous, welfare-based European clearing model with synthetic offers,
fixed demand and verified commercial constraints. This is EUPHEMIA-inspired;
without exchange order books it cannot reproduce EUPHEMIA's actual bids or its
full nonconvex order acceptance and price-setting rules. Keep the physical
PyPSA-Eur reference, conditional numerical benchmark and this market model separate.

## 1. Freeze the experiment and its provenance

Define 2025 UTC hourly intervals, supported zones and accounting scope. Hash
source files, compiler, assumptions, package versions and outputs. Predeclare
example hours, calibration/held-out periods and numerical and empirical gates
before fitting. Initial diagnostic is uncalibrated: no parameters selected by
price-error optimisation. It supplies descriptive errors, not an acceptance claim.
Deliverable: versioned input/experiment manifest. Preserve all existing annual gates.

## 2. Establish bidding-zone geography

Verify period-specific zone membership, including Germany/Luxembourg, Italy's
zones, Nordic splits and unmatched areas. Trace original asset positions and
bus members rather than assigning everything by clustered centroids. Audit
raw geometry licenses and transformations. Flag ambiguous assets and demand
allocation; do not drop them or silently merge zones.
Deliverable: audited asset/load/zone crosswalk with coverage and unresolved cases.

## 3. Compile demand independently of prices

Use ENTSO-E hourly demand under the correct domains, UTC and interval weighting.
Reconcile national and bidding-zone scope and preserve gaps. Fixed demand is the
first demand curve; observed load does not identify willingness to pay. Add a
separately labelled shortage variable with declared penalty. Flexible demand
requires evidence and explicit energy/time constraints, not a guessed elasticity.
Deliverable: 8760-by-zone load arrays, coverage and monthly-total comparisons.

## 4. Reconcile fleet and original availability

Compare PyPSA-Eur fleet with IRENA capacities and Ember monthly/annual generation,
retaining scope differences and vintage uncertainty. IRENA year-end capacity
is not automatically capacity available all year. Version commissioning assumptions.
Use original weather-derived wind/solar availability and outages; never replace
available energy with observed or optimised dispatch. Monthly production checks
constrain plausibility, not an hourly upper-bound profile.
Deliverable: audited per-asset or cost-segment capacities and hourly availability.

## 5. Construct synthetic supply offers

Thermal offer = fuel price / efficiency + operational CO2 price × fuel emissions
factor / efficiency + variable operating cost, plus explicitly justified markup
variants. Keep fuel and carbon-price time dependence and currency units clear.
Lifecycle carbon factors belong to production accounting, not operational bids.
Represent different efficiencies as separate segments. Wind/solar negative bids
are documented assumptions, not inferred from observed negative market prices.
Treat biomass, waste, CHP and minimum-output behaviour explicitly.
Deliverable: hourly quantities/prices with provenance for every segment.

## 6. Preserve intertemporal resources

Keep reservoir inflows, turbine limits, spills, losses, water-energy capacities
and chronological inventories. Keep reservoirs separate unless pooling is justified.
Battery charging/discharge efficiencies and energy bounds are explicit. State
initial/final assumptions consistently for baseline and investment; new batteries
remain empty at both boundaries under current rules. Do not reset inventories
between days. Hydro opportunity values must arise from the defined horizon or
an independently documented terminal-value policy, not observed price fitting.
Deliverable: storage compiler and smaller monolithic chronological reference.

## 7. Implement continuous coupled clearing

Minimise total accepted offer cost plus shortage penalty, subject to zonal
energy balances, offer bounds and chronological resource constraints. For each
hour, each zone's net export equals production plus discharge minus load and
charging. Price is the balance dual under the documented sign convention.
A single uncoupled hour can use a sorted merit order; coupled/intertemporal
cases require an LP. Reuse compiled sparsity and solver bases where valid.
Report degeneracy and nonunique marginal-price intervals rather than assuming
identical prices for every optimal solution.
Deliverable: reusable sparse solver with feasibility diagnostics and prices.

## 8. Add audited commercial coupling constraints

Use JAO flow-based PTDF/RAM domains only for verified regions/hours, including
hub definitions, net-position convention, nominations and allocation restrictions.
Handle external zones and other regions with separately sourced transfer limits.
Do not infer capacity from observed flows. Do not impose overlapping internal
bilateral and flow-based constraints without an explicit coupling model.
PyPSA physical ratings may support sensitivity cases; label them physical proxies,
not day-ahead commercial capacity. Unsupported hours remain blocked.
Deliverable: constraint coverage/provenance report and small reproducible examples.

## 9. Verify numerical correctness against native PyPSA

Construct independent native zonal baseline and paired line/battery cases with
identical offers, demand, bounds and storage chronology. Compare feasibility,
objective, generation, exchanges, inventories and interpretable dual prices.
Include scarcity, curtailment, negative bids, constrained borders and cyclic storage.
Retain explicit convergence bounds where decomposition is used. Predeclare
numerical tolerances before assessment; the existing conditional physical-model
parity result does not validate this new compiler.
Deliverable: matched-case report and machine-readable verification results.

## 10. Benchmark the full chronological year

Measure cold input loading/compilation separately from warm clearing and total
scenario latency. Record peak memory and hardware limits. Solve all 8760 hours
without silently dropping intertemporal constraints. Compare decomposition
against a smaller monolithic reference before annual claims. Seconds-level
performance is a target until the complete coupled model is measured.
Deliverable: runtime/memory/accuracy benchmark with exact inputs and restart evidence.

## 11. Calibrate and evaluate on separate observations

Choose training and held-out periods before fitting. Fit only identifiable,
documented parameters with physical bounds; retain an uncalibrated baseline.
Assess price bias/MAE/RMSE/correlation, border-spread direction/duration, fuel
mix and exchanges, including seasonal/scarcity/negative-price behaviour. Preserve
missing observations and publish failures. Actual prices and load alone cannot
uniquely reconstruct bid curves. Set empirical acceptance thresholds explicitly
before calling any result validated; diagnostic metrics do not set those thresholds.
Deliverable: held-out evaluation and sensitivities, not just price matching.

## 12. Evaluate investments with matched inputs

Compare baseline and baseline-plus-intervention with the same bids, weather,
demand and boundary rules. Report system operating-cost savings, shortages,
curtailment, congestion-rent proxies and signed emissions separately. System
savings are not investor revenue. Thermal relief, new circuits and commercial
capacity changes are different interventions. Full benefits need matched native
checks; no annual extrapolation of short experiments.
Deliverable: verified paired annual scenario evidence before app integration.

## 13. Publish the full report and visualisations

Publish a readable summary, conclusion, assumptions, methods, source manifests
and downloadable data. Show German synthetic bid curves with demand and simulated
versus observed DE-LU price; then annual/hourly price charts, seasonal errors,
generation/exchange checks, constraint coverage, runtime and investment comparisons
as each stage becomes verified. Label incomplete stages and preserve nulls.
Verify CI/Pages and public URLs before saying published. Integrate only supported
verified functionality; keep recurring annual review enabled until its gates pass.

The first implemented diagnostic and figures are in the
[Germany synthetic-bid report](synthetic-bids-germany-2025.md).
