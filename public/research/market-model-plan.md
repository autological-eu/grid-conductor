# Annual market opportunity: implementation plan

Status: proposed implementation, 13 September 2026. No counterfactual annual
market-opportunity model is implemented by this document.

## 1. Outcome and measurement contract

For each candidate connection, estimate the annual reduction in modeled system
cost when a precisely identified transmission constraint is relaxed. Report
M€/year before investment costs, alongside hourly contributions, emissions
changes, data coverage and sensitivity to assumptions.

Run the same model twice:

1. Baseline with reconstructed historical constraints.
2. Counterfactual with only the selected constraint changed.

Freeze estimated supply offers, generator availability, demand, weather, fuel
and carbon prices, boundary assumptions, starting energy inventories and model
version. Generation, prices, exchanges and storage operation are outputs and
may differ between the runs. Do not recalibrate offers in the counterfactual.

For fixed demand, annual market opportunity is:

`(baseline total system cost − counterfactual total system cost) / 1,000,000`

Include variable generation, startup/no-load costs where represented, storage
operating costs and any unserved-energy penalty consistently. Separate cost
categories in the report. Reliability benefits that depend on an assumed
unserved-energy value must be visible, not hidden in trading savings.

Use a complete, explicitly dated year. Our existing archive covers
11 September 2025–10 September 2026; it is not automatically the latest trailing
year. Offer that reproducible historical window first, then refresh to a new
complete-year snapshot. Do not multiply a partial-period result by 8,760/hours
and label it an observed annual opportunity. Missing windows produce a partial
result with coverage, or explicitly modeled imputations with sensitivity.

## 2. Existing assets and missing inputs

| Asset                           | Available now                                      | Work required                                                                      |
| ------------------------------- | -------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Annual zone prices and carbon   | Electricity Maps archive                           | Currency normalization, native-resolution history and geography checks             |
| European screening              | 107 configured borders, 54 zones; versioned events | Operational topology audit and annual screening run                                |
| Generation/load/physical flows  | ENTSO-E research pilot for a subset and month      | Full-year ingestion, resolution checks and neighboring-zone coverage               |
| Constraints                     | App capacity reader and physical flows             | Historical market constraints for every modeled interval; flows are not capacity   |
| Generator capacity/availability | Not assembled for this model                       | Join assets, installed capacities and outage histories; assess reporting gaps      |
| Supply costs                    | No calibrated supply stacks                        | Fuel/carbon prices, efficiencies, costs and operational assumptions                |
| Storage/hydro                   | Partial pilot observations                         | Energy inventories, budgets, efficiency, operating limits and initial conditions   |
| Existing simulator              | Zonal price-response prototype                     | Keep separately labeled; do not repurpose its results as validated market clearing |

## 3. Phase A — data audit and pilot selection

Build a coverage manifest before choosing the pilot border. Prefer a small
connected region with published directional transfer limits and reliable load
and generation records. Use Core/Nordic flow-based regions only with a suitable
constraint adapter. Select the geography on evidence, not on an assumed easy
country pair.

For every dataset record source, licensing/access terms, domain/EIC, technology
or asset identifier, units, interval, publication time, retrieval time, revision
and observed/estimated/missing status. Pin raw-response hashes and mappings.

Separate two experiments:

- Historical operational reconstruction: realized demand and renewable resource
  estimates, with the result labeled an ex-post cost experiment.
- Day-ahead market reconstruction: forecasts and capacity versions actually
  available before clearing, validated against prices and scheduled exchanges.

Use the second for claims about historical day-ahead opportunity. Actual physical
flows and generation provide additional diagnostics; they can differ because of
intraday trading, balancing and outages. Do not silently mix realized data with
day-ahead inputs and call that an auction replay.

Fetch native market intervals, including the transition to 15-minute SDAC
delivery intervals on 1 October 2025. Retain interval duration; aggregate to
hourly reports after solving. Hourly-only data can support an explicitly
simplified prototype, not a faithful reconstruction of subhourly constraints.

Deliverable: coverage report and a documented pilot boundary. Gate: all essential
inputs exist or have an explicit, reviewable fallback; no hidden zero filling.

## 4. Phase B — estimated supply stacks

Construct generator or technology-cohort supply blocks by zone and interval.
Use unit-level records where coverage permits, otherwise clearly labeled cohorts.
Avoid double counting unit-level and aggregated capacity, including assets that
were commissioned or retired during the year.

For thermal blocks:

`cost €/MWh = fuel €/MWh_thermal / efficiency + direct tCO2/MWh × allowance €/tCO2 + variable operating cost`

Version efficiency bands, startup costs, minimum stable output, ramp rates,
minimum up/down times and reserve restrictions. Incorporate these physically
where modeled, or disclose their omission. Physical constraints belong in a
dispatch model; a synthetic auction model must represent relevant restrictions
through supported order structures. Do not claim these are identical approaches.

Compute nominal headroom as installed MW minus observed MW, and available
headroom as estimated available MW minus observed MW. Keep these as diagnostics.
Neither is an extra supply offer: availability, ramping, energy budgets and costs
determine economic dispatch. Observed output is not frozen in the counterfactual.

Wind/solar availability should use resource or forecast potential, not just
actual output, which can embed curtailment. Hydro needs turbine limits and water
budgets; storage needs power, energy, efficiency and state of charge. Model
opportunity costs across time rather than treating their entire capacity as free
supply. Distinguish direct operating emissions from lifecycle accounting.

Deliverable: versioned supply blocks with observed versus assumed fields, plus
low/central/high flexibility parameter sets. These are cost-based synthetic
offers, not recovered historical order books.

## 5. Phase C — baseline optimization

Implement a new Python optimization service/module, separate from the existing
TypeScript price-response simulator. Start with a linear dispatch model and a
maintained LP solver such as HiGHS, subject to dependency and deployment checks.
Add mixed-integer commitment only where justified by validation and runtime.

Minimize total modeled operating cost subject to:

- Zone energy balances and fixed demand; explicit unserved-energy slack.
- Available generation and supported operating restrictions.
- Directional transmission limits or flow-based net-position constraints.
- Storage charge/discharge efficiency, inventories and terminal conditions.
- Hydro budgets, boundary exchanges and consistent losses.

Solve linked multi-period windows, not isolated hours. Use rolling horizons with
look-ahead and identical rules for both runs. Carry each run's own state forward
after their identical initial state. Prevent window-end storage depletion and
water-budget artifacts. Record terminal energy values so the counterfactual
cannot appear cheaper merely by leaving less stored energy at year end.

Expose energy-balance duals as model prices for the convex prototype. If commitment
is introduced, document the separate pricing procedure: mixed-integer solutions
do not automatically provide market-clearing prices. Do not equate marginal cost,
accounting cost and observed auction prices without checking conventions.

Deliverable: reproducible baseline dispatch, costs, prices, residuals and solver
status per interval/window. Gate: feasibility and conservation tests pass; failed
or unconverged solves do not produce opportunity KPIs.

## 6. Phase D — calibration and independent validation

Split the year into calibration and held-out blocks spanning seasons, demand
levels and renewable conditions. Avoid tuning a separate curve to each observed
hour, which can fit the price without identifying the response to extra trade.

Assess price errors and negative-price/high-price behavior, generation by fuel,
scheduled exchanges, constraint activity, energy balances, storage operation and
renewable curtailment where independently observed. Compare against simple
benchmarks, not only a complex model's own fitted output.

Set numerical acceptance thresholds before evaluating held-out periods, based on
the intended decision and available reporting precision. Report tradeoffs rather
than inventing universal validation thresholds now. Price fit alone is not proof
of the correct supply curve. Repeat the analysis across plausible supply stacks.

Deliverable: baseline validation report with approved modeling scope. Gate: pass
predeclared criteria or label the model experimental and withhold headline ranks.

## 7. Phase E — paired constraint experiments

For directional-capacity borders, test specified increments (for example +100,
+500 and +1,000 MW), then a sufficiently loose limit as a sensitivity experiment.
Identify whether one or both directions change and retain outages unless the
experiment explicitly removes them. Other constraints remain unchanged.

For flow-based regions, record the exact network-element/contingency constraints
and margin changes. A bilateral border is not generally one removable constraint.
Changing margins while holding network sensitivities fixed is a margin-relaxation
experiment, not a physical new-line model. A new line requires updated topology
and sensitivity calculations in a later scenario phase.

Run the full linked historical period for each experiment, including hours without
an observed price gap: storage and dispatch can shift effects into other hours.
Observed constrained hours explain target selection and provide a decomposition;
they must not truncate total annual system benefits. Preserve negative hourly
contributions and sum the paired costs before rounding.

Hourly report fields: baseline/scenario costs, cost difference, zone prices,
generation changes by fuel, exchanges, emissions, constraint activity, boundary
effects and quality flags. Attribute startup and terminal costs consistently and
reconcile hourly totals to the optimization objective.

Annual report fields: M€ opportunity before project costs, operational tonnes CO2
change, modeled period, coverage, sensitivity range, solve status and binding
constraints that remain. Report CO2e only when the emission factors support it.
Add lifecycle effects separately; use flow tracing afterward for consumption
footprints, not for computing total system generation emissions.

Sanity gates: zero relaxation reproduces the baseline; with the same feasible
set otherwise, relaxing a constraint cannot increase an exactly optimized total
cost beyond solver tolerance. Rolling-horizon artifacts or approximate solver
gaps must be flagged rather than hidden. Individual hourly benefits may be negative.

## 8. Phase F — Europe-wide execution and app integration

Scale from the validated pilot to a shared European baseline. Reuse that baseline
for individual constraint experiments, parallelize bounded jobs, cache immutable
inputs and resume failed windows. Keep external Europe-neighbor supply explicit.
Individual border opportunities are not additive: two relaxations can compete
for the same benefit. Evaluate combined projects in a joint run.

Proposed persistence:

- `model_input_snapshots`: data hashes, mappings, coverage and revisions.
- `model_assumptions`: cost/availability/operating parameters and provenance.
- `market_model_runs`: baseline or experiment, parent baseline, constraint patch,
  solver configuration, validation status and runtime.
- `market_model_hourly`: costs, dispatch, flows, emissions and flags.
- `market_opportunities`: annual totals, modeled period and sensitivity range.

Add a separate “Modeled annual opportunity” column and detail view to `/targets`.
Keep observed spread metrics alongside it. Never place synthetic cost benefits
in legacy market-loss fields without a deliberate schema and UI migration.
An experiment must be inspectable: changed constraints, fixed assumptions,
coverage, baseline fit and interval-level results. Display unavailable or
experimental results as such, not as zero-valued opportunities.

Update `/docs` with each delivered phase, model version and validation report.
Only then connect this target estimate to concrete project costs and Step 2
investment scenarios. No production database migration or deployment is implied
by this planning document.

## 9. EUPHEMIA boundary and references

We currently have a public algorithm description, not an authorized executable or
the complete historical auction inputs. This plan implements an explicitly
documented subset of market-clearing principles, not EUPHEMIA itself. Block and
complex orders, pricing rules, tie-breaking and multi-period behavior prevent
claims of exact replication. Exact replay would be a separate access and data
workstream; synthetic offers would still limit historical fidelity.

- [ENTSO-E SDAC and market-resolution timeline](https://www.entsoe.eu/network_codes/cacm/implementation/sdac/)
- [EUPHEMIA public description](https://www.nemo-committee.eu/assets/files/euphemia-public-description.pdf)
- [Core capacity calculation and flow-based constraints](https://www.entsoe.eu/bites/ccr-core/day-ahead/)
- [ENTSO-E data catalogue](https://transparencyplatform.zendesk.com/hc/en-us/articles/17260622859412-Transparency-Platform-Help-page)
- [ENTSO-E fourth cost-benefit guideline](https://www.entsoe.eu/news/2024/04/09/entso-e-publishes-the-final-guideline-for-cost-benefit-analysis-of-grid-development-projects/)

## First delivery

Start with the coverage manifest, pilot selection and a small set of historical
linked windows. Deliver a synthetic supply stack, a baseline that can be inspected,
and one paired constraint-relaxation experiment. Expand to the complete year only
after validating that end-to-end calculation. The milestone is a reproducible
cost difference with explicit assumptions, not a prematurely precise European rank.
