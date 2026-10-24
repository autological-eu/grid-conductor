# Grid Conductor — product requirements

## Hourly fits with next-month validation

Evaluate a separate historical reconstruction with individual spline midpoint
and five positive supply-node increments for each hour/technology/bidding zone.
Initialize all twelve monthly models from the same neutral source-cost curve;
penalize hourly departures and abrupt
changes in those departures. Preserve zero renewable bids, available MW, original
network constraints and fixed reservoir injections. Every batch must include all
hours of its training month and actual summed monthly generation, not a scaled
sample. Compute gradients through constrained smooth clearing, then report actual
original-LP prices and generation separately.

Fit every month, covering all8760 chronological2025 hours. Retain individual
calendar-hour coefficients; for the following month average the learned economic
bid functions by technology/bidding zone/local hour of week. Average functions,
not nonlinear raw parameters or available MW. Use only available training hours;
unsupported clock slots use that resource's training-month mean and wholly absent
resources use the neutral prior. Keep actual target-hour source/fuel costs,
demand, renewable availability, network bounds and fixed hydro exogenous.

Evaluate all eleven adjacent pairs January→February through November→December,
covering8016 forward hours. December's fit has no forward score without2026
inputs; never wrap backwards to January2025. After every common epoch select
the twelve-model checkpoint with lowest aggregate next-month original-LP price
MAE, stopping after three consecutive nonimproving epochs (1e-6 EUR/MWh).
Generation errors participate in monthly training and are reported separately.
Compare forward predictions with independent hourly fits and averaged-curve
within-month fits, including matched February–December coverage. Report monthly
generation against actual known country/technology targets, not invented hourly
generation observations.

Because next-month scores choose the epoch/stopping, label them model-selection
validation rather than an untouched test. Disclose retrospective perfect-input
and fixed-hydro limitations, historical2025 model exploration, actual runtime
and failures. Keep best coefficients and auditable provenance; no unique actual
order-book, baseline-promotion or public-explorer claim follows. Earlier
January-only reconstruction and six odd/even studies are distinct experiments;
their stopping/selection rules do not govern this twelve-month study.

## Differentiable supply-curve fitting

Evaluate six explicit marginal-price nodes at0/20/40/60/80/100% of hourly
available output per technology and bidding zone. Positive independently learned
node increments permit changing curvature while keeping bids nondecreasing.
Compile fitted smooth curves into divisible offer tranches for the original LP,
then measure actual LP price MAE and source-matched generation errors. Preserve
the distinction between smooth-clearing training gradients and discontinuous LP
inference, and quantify offer discretisation. If source groups are pooled, retain
all physical MW/location constraints, disclose cost aggregation and country output
allocation, and compare against a control with identical pooling assumptions.
When identical zero-priced offers permit multiple optimal generation mixes,
disclose the allocation convention and quantify sensitivity. A valid optimal LP
allocation does not establish a unique hourly technology-generation prediction.

Evaluate flexible monotone cubic spline bids using gradients through constrained
market clearing, jointly fitting cleared ENTSO-E prices and source-matched
generation. Distinguish this from inverse least squares or heuristic coefficient
updates. Shared technology/country parameters may produce different hourly curves
through observed availability, source costs and local clock features. Keep the
physical feasible set and fixed reservoir schedule explicit. Test wind, solar and
run-of-river at zero economic bid as a declared assumption, with numerical
regularisation measured separately. Smooth bids alone do not guarantee smooth
solutions at active-constraint changes: verify price and dispatch gradients,
feasibility, stationarity and complementarity before empirical claims.

Preserve independent odd-month fits and next-even-month all-hour evaluation.
Disclose sampled training objectives, fitting budgets and convergence limits;
monthly generation must remain a monthly target. Report exact evaluation
coverage and ordinary errors, without substituting training loss for validation.
No automatic baseline promotion, public explorer update or storage-fleet adoption.

## Learned supply curves and month-ahead validation

Evaluate monotone parameterised technology supply curves inside the constrained
European clearing model. Hourly curves use shared learned parameters and changing
source costs/availability, rather than independent parameters for every hour.
Fit January and test February, March→April, May→June, July→August,
September→October and November→December. Each fit uses only its odd month's
price/generation targets; test months must not determine parameters or selection.
Remove inherited full-year target-fitted bid and solar coefficients from the
candidate's training inputs. Retain physical constraints, transparent source
assumptions and fixed observed demand; disclose historical model selection and
perfect-input limitations. Compare cleared ENTSO-E price errors and source-matched
generation errors at their actual hourly/monthly resolution. Label the six even-
month composite separately from a full-year score and from the accepted in-sample
baseline. No automatic baseline or public-model promotion follows.
Do not infer bidding-zone generation targets from national totals. Disclose any
shared national/resource parameters, source technology distinctions, curve
discretisation and weakly identified or unconverged fitting proposals.

## Chronological storage extension

Evaluate a separate storage-enabled candidate with explicit charging demand,
discharging supply, pump/turbine power, MWh capacity, efficiencies, losses and
hourly energy balance. Carry actual cleared stock across days; disclose initial
and terminal assumptions and preserve fixed reservoir injections separately.
Support batteries and pumped storage through the same explicit asset interface.
Distinguish retained source-model fleet assumptions from verified 2025 inventories
and hypothetical investment/test assets. Never infer missing batteries or initial
inventories from generation. Use own-model reference prices for look-ahead bids,
not observed auction prices as a forecast shortcut. Test numerical chronology,
runtime, generation and observed-price fit before considering adoption. This
sequential hourly screen does not establish intertemporal day-ahead auction,
market forecasting, carbon savings or investment-profit validity.

## European linked-order performance evaluation — 23 October 2026

Evaluate the linked-bid extension on the full retained European network, with
explicit spatial/time coverage and measured runtime. Distinguish independent
hourly supply, the MW actually offered through linked packages, hypothetical
storage and actual source capacity. Preserve physical/energy chronology and
price-acceptance checks; report computational limits and remaining offer-cost
bounds separately from observed-price error. Cached topology must not freeze
daily changing bids, demand, renewable availability or network-flow constraints.
This runtime evaluation does not itself adopt new bidding assumptions, change
the research baseline or establish full market/investment validity.

Before adopting a linked-bid extension, compare its saved hourly cleared prices
and generation with the accepted baseline on identical observed source coverage.
Use corrected hourly ENTSO-E SDAC targets, original Ember monthly generation and
available hourly ENTSO-E generation; distinguish IRENA capacity from generation.
Retain missingness, country/zone boundaries, pooled-allocation uncertainty and
separate storage discharge from primary generation. Runtime and numerical
feasibility alone do not establish improved empirical model performance.

## Block and linked-bid research direction — 23 October 2026

Explore intertemporal block and parent/child bid relationships for gas and storage
as an extension to the accepted hourly offer model. Distinguish supply-curve
tranches, market-order acceptance and physical operating constraints. Storage
linkage must retain explicit energy balance, efficiencies, stock chronology and
power limits. Price validation must account for the economic conditions of
accepted families, not assume that dispatch optimality alone supplies valid
market prices. Preserve the adopted research baseline while evaluating this
extension; a prototype or partial EUPHEMIA feature set does not establish full
market replication, observed-price improvement or investment validity.

## Accepted research baseline — 23 October 2026

Use **solar-anchor-bids-v1, annual case resource_full**, as the active research
baseline for new comparisons. The user explicitly accepts its better observed-
price fit together with the documented deterioration in thermal generation mix.
config/active-research-baseline.json is the authoritative current pointer;
config/research-baseline.json remains a historical replay manifest. This decision
supersedes older baseline/control-retention requirements below without changing
the completed experiment's failed generation guard or its original evidence.

Retain country solar factors and resource-specific seasonal/local-hour thermal
bid corrections, corrected ENTSO-E SDAC targets, source provenance, and all
feasibility/zero-emergency requirements. Continue reporting generation mix and
price performance separately. Acceptance is for calibrated2025 reconstruction,
not independent forecasting or validated investment estimation. Public explorer
and browser scenario integration are separate work; automatic reviews stay off.

## Retained solar inputs and bidding direction — 22 October 2026

The user accepts the country solar factors from solar-country-fit-v1 as the
research starting point, retaining country eligibility/exclusions and empirical
yield/source-boundary limitations. This supersedes the older research starting
point below; config/research-baseline.json remains an immutable historical replay
manifest. Fresh comparisons use config/solar-anchor-bids-2025.json and its pinned
solar witness. Improve resource-specific supply bids against
corrected hourly ENTSO-E main day-ahead prices while preserving this generation
improvement. Keep daily fuel/carbon assumptions explicit; seasonal and local-hour
effective bid corrections must enter constrained clearing, never replace cleared
prices with a statistical prediction. Report full-year all-zone errors alongside
generation mix and numerical feasibility. Same-year fitting is reconstruction,
not independent forecast validation. This decision does not replace the public
report/explorer checkpoint or browser scenario engine; automatic reviews stay off.

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

The recorded performance above uses retained price targets. The verified
22 October German auction-selection finding requires re-evaluation before those
historical numbers can be represented as SDAC benchmark accuracy. The current
report/explorer use corrected target snapshots and explicitly retain the earlier
non-oil calibration limitation; an accepted-baseline refit is separate work.
Validate auction identity
as well as units, calendar and reproducibility; a higher classification sequence
is not automatically a newer revision of the same auction. Corrected source
snapshots and refits require fresh provenance, with historical results preserved.

Accepted direction, updated 16 October 2026. This file defines requirements;
[TASKS.md](TASKS.md) records implementation and verification.

## Purpose and workflow

Help researchers and planners identify European electricity bottlenecks and
investigate investment opportunities with transparent data and assumptions.
The map is the landing page. Users inspect observed price/flow evidence, create
browser-local scenarios and compare a baseline with the same model plus an
investment. System benefit is not investor income or certified investment return.

The 21 October country-data request adds a read-only explorer at `/countries`,
linked from Docs and the research report. A country selector precedes generation
and price comparisons. The 22 October user update supersedes the earlier joint +
weekly default: display the verified oil/CHP 25% checkpoint with corrected ENTSO-E
main day-ahead hourly targets. This is a frozen-witness re-evaluation, not a refit;
its existing non-oil calibration used earlier auction targets. This is not
promotion of the accepted baseline or integration into the scenario engine. Show all price zones
within the selected country, retaining shared-zone and missing-observation labels.
Support UTC date windows, hourly data, explicit daily aggregation and full-year
CSV downloads. Keep source generation (ENTSO-E hourly where available, Ember
monthly), IRENA capacity cells and modeled dispatch separate. Never invent hourly
generation from monthly totals, zero-fill missing types/constituent zones, or
represent partial zone sums as national totals. Show original provider records,
units, coverage and provenance. Illustrative generation allocation and conditional
bounds must remain visible; they are not uniquely recovered plant dispatch or
confidence intervals. Publish compact per-country files loaded only on demand.

## Daily thermal bidding and deliverability

The user requests testing whether thermal flexibility can explain scarcity-price
events. Daily market outputs should account for delivery across adjacent hours:
keep running-unit ramping distinct from offline startup delays, minimum stable
output and minimum up/down times. Carry state across days and state the forecast
lookahead and initialization assumptions. Test original network and supply bounds
before attributing an observed spike to physical scarcity or strategic markups.
Any aggregate continuous commitment approximation must identify its relaxation
and price interpretation. Source-informed technology parameters remain distinct
from verified plant-level operating data. Event stresses must not replace original
renewable availability with observed dispatch, weaken feasibility gates or silently
promote a calibrated correction. Full-year validation and investment acceptance
remain separate requirements.

High day-ahead prices alone do not establish unserved demand or emergency
generation. Keep finite market offers, out-of-market reserves and numerical
emergency slack distinct. The existing zero-emergency acceptance gate must not
be bypassed by repricing slack to match an observed spike. Diagnose available
cheap offers and coherent network constraints before attributing a price error
to absent peaking supply; inferred offer parameters are not recovered actual bids.

Market eligibility must use dated, identified unit records before offer pooling.
Reserve redispatch capacity stays outside ordinary market supply. Distinguish a
whole plant from a block at a multi-unit site, nameplate from reserve dispatch,
and administrative decision date from its effective period. Preserve unresolved
matches explicitly. National installed-stock adjustments and unit-role exclusions
must reconcile their overlap; they are not automatically additive reductions.

## Hourly source contracts and forecast evidence

Every hourly input must distinguish interval-start, interval-end and instantaneous
samples, with energy converted to average power using the interval duration.
Align ERA5 solar radiation/PV intervals to market hour starts from the source
contract, not a lag chosen for price fit. Keep wind timing, destination-hour
capacity commissioning and original arrays intact; certify calendar endpoints
before claiming an annual corrected profile. Do not wrap or silently fill a
missing weather endpoint.

An otherwise missing nighttime PV endpoint may instead be established as an
exact converter identity: independently verify solar geometry across every
weather cell and the complete interval, with a conservative margin below the
converter cutoff, and verify zero irradiation yields zero retained-panel output.
Label this endpoint model-derived, not a retrieved weather sample. This does not
authorize interpolation or filling missing daylight coefficients. Evaluate source
corrections across the full year and all covered zones, separating EU coverage
from the larger European network and keeping country summaries explicit about
shared or missing bidding zones.

Keep reported annual net installed capacity, hourly available capacity and
actually offered capacity distinct. Proportional reconciliation to an annual
stock is a source sensitivity, not proof of outages or plant market eligibility.
Forecast archives must identify revision/vintage limits: a current day-ahead
archive is not automatically information available before the historical auction.
Observed generation remains validation evidence, never a substitute for original
renewable availability. Prices remain original ENTSO-E SDAC hourly targets.

Solar validation must separate available power from market dispatch and retain
conditional allocation bounds in mixed-resource offers. Check national/monthly
energy, hourly shape and peak/twilight behavior against generation sources with
explicit geographical coverage. Distinguish IRENA net generating capacity from
PV conversion peak-power normalization; do not invent a fleet AC/DC ratio.
System losses, orientation, tracking shares and actual spatial deployment require
separate source support. A generic loss benchmark is a sensitivity, not measured
fleet correction. Preserve the distinction between historical reanalysis and an
operational forecast, and recompute changed conversions before market clearing.
Hourly completeness alone must not imply national fleet coverage. Reconcile
grid-feed-in versus total production and the matching demand boundary before
splitting behind-the-meter solar into self-consumption and market offers; never
deduct it twice. Where the observed Solar category includes solar thermal, keep
that output/storage separate from the modeled PV technology and its validation.

The user authorizes empirical country PV yield calibration: a transparent constant
factor fitted to monthly generation may adjust the retained weather-derived curve
without changing installed capacity or copying observed hourly dispatch. Source
and technology eligibility, rejected coefficients and factor bounds must be
explicit. Keep generation calibration separate from price evaluation and preserve
curtailment/network effects by rerunning clearing. Such a factor can absorb source,
reporting, curtailment and fleet-model errors; it is not a measured loss, outage or
uniquely identified physical correction. A fit to2025 generation and evaluation
against2025 prices remains retrospective, even if no prices enter the regression.

## Active modelling approach and accuracy goal

Liquid-oil generators require explicit source-backed generating capacity and
transparent oil/FX/efficiency/carbon/VOM offers, separate from gas, oil shale,
peat and waste. IRENA renewable capacity cannot fill fossil capacity gaps.
Distinguish annual installed capacity from hourly availability, and crude oil
quotes from delivered generating-fuel costs. Retain source geography, reporting
year and CHP/fuel-switching limitations. The explorer must expose oil separately
against ENTSO-E B06 even when the national Ember chart groups it as Other fossil;
compare covered hours consistently and leave unknown observations missing.
Separate market-eligible capacity from installed nameplate and realised physical
generation from day-ahead cleared quantities. Actual generation can include
out-of-market reserve/redispatch or heat-led operations; these observations do not
by themselves identify supply bids. Retain dated operating-role evidence and
explain the validation scope before fitting a market model to total generation.

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
thresholds explicitly. The accepted 16 October research target is below **10 EUR/MWh**
equal-zone mean absolute error across every currently eligible observed-price zone
and all **8,760 hours of 2025**. Report each zone separately; this aggregate target
does not mean every zone is below 10. Preserve all negative/extreme hours, coverage
and weighting. The current 41 observed-price areas are not all 48 modeled areas;
additional areas enter when complete source-backed observations are available.
Price-calibrated annual results are reconstruction accuracy, not independent
forecast accuracy. Improving source-backed generation mix and transparent
resource bids is the current priority; do not obtain this target by overwriting
cleared prices, substituting generation for availability or relaxing physics.
Evaluation electricity prices remain validation targets. Historical training prices
may inform the explicitly authorized bounded bid calibration described below.

The 20 October follow-up prioritizes event-led error diagnosis before further
calibration: identify when/where prices are over- or understated, daily/weekly/
seasonal patterns, tail episodes and matching supply/network witness conditions.
Test an interpretable change within the clearing model, with a matched full-year
control and generation/physics checks. Diagnostic associations are not causal
attribution; correcting a calendar pattern does not certify scarcity behaviour,
Nordic geography or future-year forecasting. The accepted baseline remains pinned.

The accepted inverse-modelling direction permits a bounded, interpretable family
of resource-bid calibrations inside the unchanged physical market model. Retain
several distinct plausible fits when supported, rather than declaring a uniquely
identified order book. Entire2025 observations may calibrate this explicitly
labelled historical reconstruction; generation/trade/physics checks complement
price fitting but do not establish independent forecasting. Every retained fit
must have full-year forward clearing and independent replay. Ensemble spread is
descriptive within the tested model family, not a posterior or a calibrated
confidence interval. Any future investment distribution must pair baseline and
investment under the same member's exogenous assumptions; system benefits,
price fit and verified investor value remain separate. Calibrated offered-cost objectives may include premiums and must not be represented as verified physical resource cost or social welfare; economic impacts need separate resource-cost and emissions accounting. Source-backed physical
uncertainty is a later step, not unrestricted capacity/network fitting.

Renewable-source reconciliation must distinguish total wind from onshore/offshore
subtypes, installed capacity from weather conversion, and available supply from
dispatched generation. Preserve original within-subtype weather/geography unless
new independent site/profile evidence supports a change. Do not infer zero
capacity from missing subtype tables. Generic solar system-loss assumptions
must account for losses already included in the panel model; label sensitivities
separately from verified country-fleet corrections. Resource-specific renewable
offers may be investigated with matched-formulation controls and full-year price
and generation evidence; synthetic negative bids do not establish actual subsidies.

Operational availability inputs must remain distinct from actual generation and
annual energy factors. National daily availability mapped to hourly plant offers
is a labelled proxy: disclose units, source dates, timezone/aggregation uncertainty,
within-country allocation and nominal-capacity limits. Revised historical outage
information does not establish what was known before day-ahead bidding.

Daily fuel inputs must identify quote/delivery dates, hub coverage, currency and
thermal heating-value basis. Apply them to source fuel costs before the retained
resource bid adjustments and clearing. Keep unavailable hubs explicit; regional
indices cannot silently stand in for European TTF. Declare nontrading-day carries
and boundary fallbacks. Distinguish direct source-level changes from controls
that preserve monthly fuel means, and retain generation checks alongside prices.

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

Cost arithmetic and empirical bid validity are separate checks. Trace fuel,
emissions factors and electrical efficiency to their technology and vintage;
a generic diesel entry does not certify every oil plant. Declare the carbon
pricing jurisdiction and distinguish primary-auction observations from daily
secondary-market prices. Any heat credit must represent a documented useful-heat
benefit without deleting combustion emissions or applying total CHP efficiency
as electrical efficiency. Market-ineligible reserve capacity cannot be made
eligible by changing its bid price.

For simple heat-led bid experiments, conserve each parent offer's hourly available
MW when splitting a low-price tranche from flexible merchant supply. Distinguish
an optional cheap offer from a forced minimum or observed heat schedule. Declare
heat-conversion and alternative-boiler assumptions, keep thermodynamic bounds,
and report hourly/monthly generation errors and negative-price behaviour alongside
annual energy. Annual-total agreement alone cannot establish dispatch or bid validity.

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

## Joint supply and network inverse modelling

The user authorized joint calibration against generation mix and observed zonal
prices, allowing physically consistent changes to supply availability and network
constraints. Use a small, predeclared parameterization with independent source
bounds where available; explicitly label experimental bounds when independent
evidence cannot certify them. Preserve topology, electrical equations, island/link
physics, original weather chronology and water conservation unless a separately
specified experiment changes them faithfully. Fit effective limits separately
from impedance or physical expansion. Observations constrain the forward model;
never overwrite cleared prices or replace weather availability with dispatch.
Report multiple explanations and adverse regional outcomes where applicable.
A fitted grid is not a verified physical network or an investment counterfactual.
