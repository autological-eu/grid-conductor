# Grid Conductor — product requirements

Accepted direction, 10 October 2026. This file defines requirements;
[TASKS.md](TASKS.md) records implementation and verification.

## Purpose and workflow

Help researchers and planners identify European electricity bottlenecks and
investigate investment opportunities with transparent data and assumptions.
The map is the landing page. Users inspect observed price/flow evidence, create
browser-local scenarios and compare a baseline with the same model plus an
investment. System benefit is not investor income or certified investment return.

## Maintained models and publications

The active development baseline is the fast fixed-hydro supply-curve model, as
requested on 10 October 2026. Retain two reports, with the daily resource-bidding
model and compact rolling-storage trial paused as research references:

1. **Fixed-hydro annual checkpoint:** hourly synthetic supply-curve clearing with
   audited, precomputed reservoir injections and physical network constraints.
   Retain its full-year results, methods, figures, source and replay evidence.
   The authorized combined formulation adds simple resource-specific offers,
   including sourced monthly gas/oil bids, to these same hourly physical clearings.
   Keep only the complete resource-bid model; retire the legacy/fuel-only
   comparison variants. Retain indispensable hydro source/replay evidence.
   Diagnose largest errors using independently sourced capacity, generation,
   demand and water data; isolate injection geometry from physical capacity and
   hydro water/schedule assumptions. Sensitivity probes do not establish acceptance.
   Publish adverse outcomes and all eligible areas. Keep observed electricity prices
   out of bid construction. This does not authorize adaptive-hydro experiments.
   Develop from this checkpoint; fixed hourly injections must not be described
   as merely fixed hydro bid prices.
   Its fixed schedule cannot respond to investments; conditional benefits are
   not guaranteed conservative estimates.
2. **Current resource-bidding simulator:** simple, explained strategies per
   generator type, 24 hourly UTC periods cleared daily, storage carried between
   days. Preserve this paused model for reproducibility; do not continue
   adaptive-hydro/rolling-policy experiments without a new user request.
   Retain its annual results, resource/fuel rules and observed-price diagnostics
   in one report. Target seconds-scale annual scenario estimates, measured honestly.

The paused daily simulator was tested with a compact zonal transport network and
short rolling-horizon storage optimisation, as authorized on 10 October 2026.
Treat this as a formulation experiment within the current model: retain the
physical/bidding reference and report changes in behaviour as well as speed.
Summed cross-area branch ratings are model-derived transport envelopes, not
commercial NTC or a physical-feasibility certificate. Preserve original weather,
demand, storage-unit water balances and carried/closing stocks. A declared
arithmetic seasonal-stock penalty may replace the separate hydro price forecast
in this trial; it is a heuristic, not an inferred market water value. Do not
reset reservoirs to daily budgets or adopt the trial as the browser engine.

Returning to the fast checkpoint does not validate its inherited hydrology,
country aggregation or investment values. Bidding-zone geography and observed
zonal demand/constraints remain an input priority. Battery/PHS investment support
requires chronological modelling and fresh verification; these units are excluded
from the retained fixed-hydro solve. Preserve empirical and paired-scenario gates.

Keep one workbench methodology page alongside those two reports. Remove superseded
public articles rather than maintaining a research catalogue. Supporting source
inputs, tools and minimal retained-model replay evidence may remain as dependencies;
retaining them does not make their old experiments active development priorities.
Do not restore retired annual searches. Git history provides historical context.

The live browser's two-zone line/battery screen remains in service until a
verified replacement is explicitly integrated. Neither research model becomes
the public scenario engine merely because its report is published.

## Observed bottleneck baseline and public experience

- Keep the map, one corridor per unordered zone pair, accessible selection,
  touch/keyboard controls, local scenario persistence and revision invalidation.
- Report signed annual flow × signed price difference × interval hours, summing
  both directions. Floor only the displayed annual rent at zero. Preserve missing
  intervals and signed evidence; do not extrapolate or annualise an annual sum.
  Flow classification is unverified where original request receipts are absent.
  The estimate is not verified TSO income or proof of physical congestion.
- Show mean absolute price spread and hourly price traces with gaps/provenance.
  Show mean absolute hourly lifecycle carbon spread below price spread, restricted
  to jointly observed price gaps > EUR5/MWh. The card contains label/value/units;
  coverage and mapped-subset limitations remain in methodology and source data.
- Navigation exposes Docs, not a research catalogue, European targets or network
  lab promotion. Docs explains the solver actually used, opportunity evaluation
  and exact data sources. No introductory divider, separate bottleneck picker,
  “floor: 0” labels or long duplicated sidebar explanation.
- Retain the browser screening equations, welfare caps, battery loss assumptions
  and undiscounted 25-year benefit-minus-capex interpretation until replacement.
  Economic screening is not congestion rent or investor cash flow.

## Resource bidding and physical constraints

Wind/solar offer original weather-limited availability at declared low prices.
Gas/oil use sourced fuel, efficiency, operational carbon and variable O&M without
counting fuel/carbon twice. Declare currency, heating-value basis, temporal
resolution and delivered-product approximations. Nuclear and other technologies
use labelled cost/availability proxies; unsupported commitment, outages and ramps
must be disclosed rather than invented.

In the paused daily reference, reservoir hydro uses a seasonal inventory target
and water-value bid. Battery and
pumped-hydro bids use loss/wear-adjusted forecast buy/sell thresholds. Forecasts
use common exogenous demand/weather/inflow assumptions; approximate endogenous
prices are not perfect predictions or realised ENTSO-E observations. Recompute
forecasts and strategies for each investment.

The retained physical formulation preserves original network constraints, hourly water/energy balances,
efficiencies, standing loss, inflow, spill and power/energy limits. Actual closing
stock carries forward; no daily inventory reset, water gift or substitution of
dispatch for renewable availability. IRENA end-2024/end-2025 linear wind/solar
capacity change is an assumed commissioning trajectory, not observed dates.
Hydro capacity does not establish water availability.

Declare identical horizon boundaries for paired cases. New batteries start/end
empty. A closing-window network prepass must be explicit, optimal and cycling-free,
with unchanged bid prices/physics/closing stocks and exclusive submitted directions.
It is a boundary convention, not proof of future joint feasibility or market realism.

Model-derived N-0 physical constraints and country/AC-island areas are not verified
commercial bidding zones or JAO domains. Preserve island connectivity and explicit
link efficiency/bounds. Daily UTC/hourly clearing approximates actual local market
days and quarter-hour intervals. This is EUPHEMIA-inspired synthetic bidding, not
reconstruction of actual order books or full nonconvex allocation rules.

## Verification and integration gates

- Preserve exact source/code/input hashes, resource guards, failures and independent
  saved-witness replay. Inspect actual jobs before running; stale receipts do not
  establish progress. Record preparation, solving, native checks, I/O and end-to-end
  runtime separately, plus memory and calendar/coverage.
- Require optimal termination and feasibility replay; report shortages and cycling.
  Matched native PyPSA checks verify formulation, not agreement with market prices.
  A completed daily policy year is not an annual optimum or strategic equilibrium.
  Any future annual-optimum claim needs independently checked feasibility/convergence
  bounds against a smaller monolithic reference; no acceptance gate is waived.
- Audit model-to-bidding-zone mapping, hourly UTC/interval alignment and observation
  coverage. Compare price bias/MAE/RMSE, correlation, seasonal errors, negative prices,
  border-spread direction/duration, generation by technology and exchanges. Keep
  country proxies and unavailable data explicit.
- Predeclare numerical/empirical thresholds, coverage and training/held-out periods
  before fitting or claiming empirical acceptance. Thresholds are not yet selected.
  Untuned descriptive comparisons are not held-out validation.
- Before accepting investments, verify matched baseline/intervention cases for
  transmission, battery, hydro and wind/solar, retaining common inputs/chronology.
  Heuristic strategies need sensitivity checks; adding an asset need not improve
  its dispatch under a fixed policy. Report system cost, revenue and rent separately.
- Integrate only supported, verified scenarios into the static app, then verify
  numerical consistency, browser runtime/memory, persistence and mobile behaviour.
  No silent replacement of the live screening model.

## Carbon and opportunity accounting

Keep lifecycle production intensity, operational carbon pricing and intervention
emissions separate. Historical factors need sources, units, boundaries, geography,
coverage and sensitivities, including biomass/waste/CHP and storage attribution.
Positive generation with missing factors cannot receive zero emissions. National
mixes are not individual bidding-zone data; mapped subsets are not whole-fleet totals.

Scenario emissions use scenario minus baseline: savings negative, increases positive.
The current browser average-mix energy proxy is not verified avoided emissions.
Do not introduce “carbon loss” as intensity difference × demand minus imports.
Verified savings require paired dispatch, complete factors and charging-origin
accounting. ENTSO-E transparency observations do not certify the model or establish
compliance with its transmission cost-benefit methodology.

## Engineering and recovery

Static Bun/Vite/React/TanStack Router, IndexedDB and GitHub Pages; correct project
base/deep links and reproducible builds. No credentials, login, persistent service,
paid hosting or cloud scenario database. Work on public-v1; no automatic main merge,
force-push or repository visibility change.

Keep large provider inputs locally ignored, with source requests/versions/hashes
for reconstruction. No multi-gigabyte GitHub or third-party mirror backups. Preserve
compact recovery/replay evidence and the retained PyPSA-Eur reference dependencies;
changed inputs must not silently resume saved optimisation states.

README owns setup; AGENTS owns operating instructions; TASKS owns the focused
backlog. Automatic hourly reviews remain disabled at user request.

## Minimal data retention

Cache only external inputs used by the 2025 models/baseline (including processed
ERA5 and generation inputs, IRENA, ENTSO-E, fuel/FX and relevant constraints), plus
minimal indispensable retained-model source/reference/replay witnesses. The IRENA
2026 release and end-2024 capacity endpoints are prerequisites for the 2025
commissioning trajectory, not a separate 2026 model. Toolchain installations are
not data caches. Remove unused runs, duplicate pilots, derived exports and old
search support. Do not keep bulk computed reports as public data.

Git contains the live baseline targets/prices, a compact carbon baseline with
coverage/provenance, immutable model input prerequisites and minimal assets for
the two retained reports. Prefer compact baseline metrics over shipping complete
intermediate arrays. Carbon metrics must reproduce the original hourly function
for every displayed border. Chart/download format changes must preserve values.
