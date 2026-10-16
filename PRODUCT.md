# Grid Conductor — product requirements

## Current baseline decision — 16 October 2026

The user accepted **seasonal-calendar-v1, annual case `refit`** as the single
research baseline. `config/research-baseline.json` pins its verified source summary,
audit and full-year witness. Use `proposal-refit.json` for subsequent common-input
comparisons; the older unfitted model is a historical control, not the active baseline.
Full 2025, 8,760-hour equal-zone price MAE is **28.964 EUR/MWh** versus
33.225 previously (**12.83% lower**), across all 41 observed-price zones.
This is an all-year-calibrated reconstruction, not independent forecast accuracy.
Generation agreement and feasibility are complementary checks, not statistical
cross-validation. The three-fit out-of-fold composite remains secondary evidence
(MAE 29.177); never describe it as the single accepted annual model.
This decision supersedes older no-promotion/current-baseline wording below.
Physical inputs, fixed hydro, chronology and feasibility gates remain unchanged.
Browser integration, adaptive storage and investment validation are separate work.
Automatic hourly reviews remain disabled.

Accepted direction, updated 16 October 2026. This file defines requirements;
[TASKS.md](TASKS.md) records implementation and verification.

## Purpose and workflow

Help researchers and planners identify European electricity bottlenecks and
investigate investment opportunities with transparent data and assumptions.
The map is the landing page. Users inspect observed price/flow evidence, create
browser-local scenarios and compare a baseline with the same model plus an
investment. System benefit is not investor income or certified investment return.

## Active modelling approach and accuracy goal

The latest direction uses bounded, transparent resource bids driven by smooth
seasonal and local-time patterns, excluding residual demand as a fitted hourly
bid predictor. Source demand and weather availability still enter physical clearing.
Ember monthly generation may inform training-month national resource bid signals
and mix checks, never hourly availability or recovered observed bids. Evaluate
season-spanning disjoint whole-month cohorts and distinguish retrospective seasonal
interpolation from future-year forecasting. Any all-year-calibrated reconstruction
is in-sample and separate from out-of-fold evidence. Preserve the physical baseline,
daily-shape/ramp/tail diagnostics, all-zone MAE grid and independent acceptance gates.

Accepted clarification, 13 October 2026: develop one fast European bidding-zone
market-clearing model. Construct simple, transparent supply bids by resource
against observed, fixed zonal demand; clear under explicit dispatch/network
constraints. The target workflow clears each day with hourly quantities and
prices across the 2025 year. This is synthetic, EUPHEMIA-inspired clearing, not
recovery of actual order books or a reproduction of EUPHEMIA allocation rules.

The primary empirical target is improved correlation with observed ENTSO-E
zonal day-ahead prices. Also reduce MAE and disclose bias, RMSE, seasonal/tail
errors and negative-price behaviour, so correlation gains cannot conceal worse
price levels. Report all eligible zones and aggregate weighting/coverage; focus
error diagnosis on Norway and Sweden without excluding adverse results elsewhere.
Use declared development/held-out periods before tuning and select acceptance
thresholds explicitly; no numerical accuracy threshold has yet been agreed.
Evaluation electricity prices remain validation targets. Historical training prices
may inform the explicitly authorized bounded bid calibration described below.

Validate simulated generation quantities alongside prices: annual and monthly
country/technology TWh, generation shares and hourly timing where observations
support them. Compare demand and signed trade on matching scope before treating
a generation difference as a supply error. Preserve incomplete country-zone and
technology coverage, gross/net and storage boundaries, and differences between
ENTSO-E and Ember reporting. Agreement in total generation does not establish
agreement in the mix. Where equal-price aggregation leaves technology/country
output non-unique, disclose an illustrative allocation rule and feasible ranges
conditional on retained group totals; do not claim unique physical plant dispatch.

Native PyPSA agreement is not a product objective or empirical acceptance target.
Optional native comparisons can diagnose compiler/formulation errors; mandatory
checks are independent feasibility/physics replay, chronology, conservation,
solver status and transparent provenance. Any annual-optimum claim still requires
its separate feasibility/convergence evidence. Preserve existing reference evidence.

Develop from the current fixed-hydro/resource-bid formulation. Its precomputed
hourly reservoir injections are conditional schedules, not adaptive storage.
Daily orchestration is a target workflow, not a reason to restart the paused
daily/rolling model families. Fixed independent hours may be batched by day;
that alone adds neither intertemporal optimisation nor new hydro flexibility.
Storage changes require carried stocks, common boundaries and fresh verification.
Seconds-scale annual clearing remains the performance aim; report preparation,
clearing and complete-command times separately. The browser replacement remains
a separate integration gate.

The 13 October 2026 follow-up authorizes a fresh candidate within this framework:
replace Norwegian national water pooling with source-backed NO1–NO5 regional
inflow, reservoir capacity and opening/closing stocks, preserving turbine
locations, other countries' fixed hydro, demand, bids and network physics for a
controlled comparison. Regional pooled water and reservoir/run-of-river allocation
remain declared approximations. Evaluate all eligible observed zones and failed
hours; do not promote a candidate merely because source granularity improved.
Daily orchestration does not imply adaptive hydro or a joint daily storage auction.

Controlled input-error diagnostics are authorized: vary wind availability, gas,
oil and operational carbon cost independently while retaining the baseline's
water, demand and network. Compare observed-price errors and nonlinear interactions
before selecting source improvements. Distinguish sensitivity from verified input
correction and causal attribution; observed generation remains validation evidence.
Do not adopt perturbations simply because they offset another model error.

The subsequent wind-source correction work must distinguish fleet geography,
national capacity trajectory and site weather. A controlled geography test may
use dated turbine capacity shares while conserving national hourly availability;
this does not certify available-energy magnitude or regional weather. Current
operating registries need historical coverage checks, and shared site records
must not double-count expansions. Preserve IRENA normalization explicitly;
observed generation is comparison evidence, never available supply.

Before selecting another price-model correction, audit hourly residual demand
across the retained European bidding-zone network. Define subtraction families
explicitly and separate weather availability, nuclear/other available supply and
fixed hydro schedules from dispatch. Compare independently reported quantities
with matching geography/coverage; keep national demand checks separate from zonal
observations. Above-availability generation and demand-total differences flag
scope/fleet/profile inconsistencies, not measured causal price-error shares.
Do not fit renewable availability to generation or infer missing demand is zero.

Price-mechanism diagnostics must distinguish local interior aggregate-offer
evidence from unique real market price setters. Preserve mixed/tied offers and
dual nonuniqueness; model network shadow contributions are not causal shares of
observed-price error. Monthly fuel associations cannot by themselves explain
intraday price setting. Fixed hydro has no variable marginal water bid: adding
a price to its fixed quantity does not create bidding flexibility. Any correction
requires separately verified chronology, water and stock boundaries.

The subsequent 14 October 2026 direction prioritizes whole-fleet residual-demand
and supply-stack improvements while retaining fixed hydro. Further hydro flexibility
is not the next development step. Diagnose available supply, demand scope and
network representation separately, with common-input controls before adoption.

A separate statistical price reference may learn a simple residual-demand response
from historical prices in a predeclared training period. Report temporal evaluation
against both the dispatch model and a constant training-price reference, including
all eligible zones and extrapolation limitations. This statistical reference remains separate from dispatch; the subsequent
explicitly authorized bid-calibration trial is governed by its own training split. A statistical price
reference does not clear supply, enforce network feasibility or value investments.
Already inspected 2025 observations cannot establish untouched held-out validation;
empirical acceptance still requires the existing separately declared gates.

The latest 15 October 2026 decision authorizes a controlled bid-calibration trial
before other input corrections. Learn a small number of transparent fuel-anchored
resource bid adjustments inside the coupled European dispatch model, retaining
original demand, available supply, fixed hydro and all network/GSK constraints.
Historical prices and generation may be used only in the declared training period;
compare generation allocation ranges and trade alongside prices to discourage
price improvements achieved through less realistic dispatch. Do not force observed
generation outside the available envelope or fit renewable availability to it.
Evaluate a separate chronological period without refitting and report all eligible
European areas, with detailed France/Spain examples. Fitted bids are effective
synthetic offers, not uniquely recovered market bids; they may compensate for
incorrect constraints or other inputs. Experimental search bounds/weights are not
product acceptance thresholds. No automatic baseline or investment-model promotion.

The subsequent accepted extension permits bidding-zone-specific resource offers
and simple increasing-price blocks within each resource's original available
capacity. Preserve fuel-cost anchors and a transparent training-only calibration;
shrink weakly supported regional differences rather than assigning observed
clearing prices directly to generators. Compare constant zonal adjustments with
the added bid-shape flexibility under the same coupled constraints. Disclose
unsupported parameters and overfitting/identifiability limits. Regional bids are
effective offers, not verified regional production costs or recovered order books.

Accepted 16 October extension: target within-day price shape alongside levels.
Diagnose daily-demeaned correlation/error, price ranges, ramps and surplus/scarcity
tails for all eligible zones. Jointly evaluate regional intercepts and resource-
specific thermal curves, with a separate bounded renewable negative-offer test.
Nuclear retains low-running-cost offers rather than generic peaking blocks.
Keep installed/available supply separate; negative effective offers do not prove
subsidies or recover order books. Check timing, source scope and flat availability
before attributing missing price movements to bids; input corrections are separate
experiments. Preserve source quantities, network physics and fixed hydro. Report
DST-aware local profiles and retain the retrospective qualification for 2025.

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
   Publish adverse outcomes and all eligible areas. Keep evaluation electricity prices
   out of bid construction; the later bounded calibration permits training prices only. Bounded chronological hydro diagnostics were subsequently
   authorized: preserve each unit's source water and exact opening/closing stocks,
   cap output changes and independently verify feasibility. These tests do not authorize
   an annual adaptive policy, investment valuation or empirical baseline promotion.
   The authorized Norwegian input update uses independently sourced NVE weather-driven
   HBV inflow, dated reservoir energy capacity and observed calendar-boundary stocks.
   Keep generation-derived inflow out of input construction. Convert electrical-
   equivalent water quantities to stored-energy units before applying original
   dispatch efficiency once. Explicitly disclose gross-stock/net-inflow basis,
   country pooling, weekly/hourly allocation and retrospective release assumptions.
   Preserve the frozen pre-update input reference for controlled verification.
   Regenerate a physically feasible fixed schedule without observed-price or
   generation fitting; this does not authorize adaptive hydro or change acceptance.
   Separate fixed hydro and demand locations from generation-offer shift keys.
   Original clustered bus placement is a controlled physical diagnostic, not a
   certified commercial-zone mapping. Publish remaining adverse price outcomes
   and reconcile observed demand scope before replacing hourly demand inputs.
   Develop from this checkpoint; fixed hourly injections must not be described
   as merely fixed hydro bid prices.
   Its fixed schedule cannot respond to investments; conditional benefits are
   not guaranteed conservative estimates.
2. **Paused daily resource-bidding reference:** simple, explained strategies per
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
For bidding-zone inputs, preserve commercial boundaries during grid aggregation;
do not assign a mixed-zone cluster wholly from its centroid. Distinguish dated
fleet records, metered zonal generation/demand, weekly reservoir stocks and weather
availability. Observed generation is validation evidence, not renewable availability.
The 12 October 2026 authorization extends bidding-zone modelling to the entire
retained European network, not Norway alone. Preserve boundaries through grid
simplification as well as clustering. Combined markets need one clearing price
while retaining separate AC-island balances and explicit HVDC losses/bounds.
Isolate country-versus-zone pooling on a common backbone, with unchanged source
bids, parent-level hourly demand/availability and fixed reservoir chronology.
Label aggregate asset/weather allocation and historical-boundary gaps explicitly;
provider reporting areas are not automatically commercial market zones. Keep
failed hours and all eligible observed comparisons; no implicit baseline promotion.

Keep one workbench methodology page alongside those two reports. Remove superseded
public articles rather than maintaining a research catalogue. Supporting source
inputs, tools and minimal retained-model replay evidence may remain as dependencies;
retaining them does not make their old experiments active development priorities.
Do not restore retired annual searches. Git history provides historical context.

The European dispatch report should concisely describe the baseline, the latest
exploratory changes, and paired generation/observed-price performance over the
same evaluation period. Use a few summary figures and NO/DE/ES/FR examples;
keep historical experiment logs out of the article. Distinguish zonal generation
verification from national cross-checks, disclose missing coverage and equal-bid
allocation ambiguity, and provide compact per-area data with provenance.

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
  Native PyPSA checks are optional formulation diagnostics, not a target or
  evidence of agreement with market prices.
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
