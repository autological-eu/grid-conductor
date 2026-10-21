# Grid Conductor — agent instructions

## Current audit — thermal cost basis and external bidding models, 21 October

The user requested a proper oil/thermal-bid audit and comparison with osJMM and
ASSUME. config/thermal-bid-audit-2025.json pins inspected external source files;
audit_thermal_bid_basis_2025.py replays original fuel/FX and technology units,
34 oil groups over 8760 hours and isolated ASSUME marginal-cost arithmetic.
The completed thermal-bid-audit-v2 is source/arithmetic evidence, not a new
dispatch candidate. EEX primary EUA auctions are a separate dated benchmark,
not a complete daily spot series. Generic diesel assumptions, delivered product,
electrical efficiency, carbon jurisdiction and operating roles remain unresolved.
Keep the three published articles/model/baseline unchanged. A two-volume
minimum-output/flexible-offer heuristic is a research recommendation, not an
authorized fitted correction or verified accuracy improvement. Reviews stay off.

## Current diagnostic — supply-bid review, 21 October

The user requested reviewing the actual supply curves after the oil non-dispatch
finding. review_supply_bids_2025.py derives annual bid/quantity diagnostics from
the frozen joint/weekly book and audited oil trial; audit_supply_bid_review_2025.py
checks original cost/availability signatures, saved dispatch, weighted CDFs and
source comparisons without a new solve. report_supply_bid_review_2025.py produces
a standalone PDF/plots outside Git; the website/three articles stay unchanged.
Oil/biomass/waste are absent from the five-fuel calibration targets, not absent
from the physical LP. Distinguish market-eligible supply from installed nameplate
and realised A75 output: primary operator/regulator sources identify reserve
generation outside the market. Reconcile unit/date/CHP/reserve roles before
discounting oil bids or assigning all actual output to day-ahead clearing.
This is diagnosis, not a new fitted model or baseline promotion. Reviews stay off.

## Active user direction — 21 October oil supply

Audit liquid oil explicitly through fleet capacity, availability, fuel/FX/carbon
bids, dispatch and source generation. Oil already exists in inherited inputs;
do not describe it as newly invented or confuse Ember Other fossil with oil alone.
Use config/oil-supply-2025.json for four controlled annual cases against the
latest verified joint/weekly checkpoint. ENTSO-E A68/A33 B06 fills only the
missing PL/SK/SI oil fleets; other discrepancies stay flagged. IRENA is renewable
capacity, not a fossil-oil source. Keep the original grid/GSK and all non-oil
inputs/bids/hydro frozen. Daily EIA Brent/ECB quotes retain explicit crude/heat
content, carry and retrospective-information limitations. Independently replay
modified capacity and native/KKT/quantity equations before publication. No automatic
baseline/explorer promotion or review restart. Preserve original report receipts
when appending the separately audited oil extension; keep exactly four figures.

## Active user direction — 21 October country explorer

The user requests a country selector with source/model generation mix and all
country-zone hourly prices. They explicitly selected the latest verified joint
+ weekly run (27.49 EUR/MWh) as the explorer default; no accepted-baseline
promotion follows. Add a read-only `/countries` route linked from Docs/reports;
the three existing articles/four report figures and workbench engine stay intact.
Derive data from the audited saved witness without another solve. Keep raw IRENA
capacity cells, Ember monthly rows and ENTSO-E hourly PSR observations distinct;
source coverage, nulls, shared zones and conditional mix allocation remain explicit.
Use compact lazy gzip country assets and browser-generated CSV downloads; no raw
bulk provider cache, witness or toolchain goes into Git. Independently replay
source/dispatch aggregation and rounded exports before publication. Browser checks
must cover country changes, all Norwegian/Italian zones, date windows, CSVs,
missing data, direct Pages links and mobile layout. Reviews remain disabled.

## Active user direction — 20 October hourly error follow-up

Diagnose the timing and kind of hourly price errors before expanding calibration.
The joint network trial is a committed checkpoint, not the active next publication.
Use hourly_error_events_2025.py for source-bound all-year inventories, then the
two predeclared weekly supply-bid controls in config/weekly-bids-2025.json.
Only a centered local weekend term is added to supported gas/coal/nuclear offers;
keep each anchor's physical inputs, fixed hydro and existing bid coefficients.
All2025 calibration remains explicitly in-sample. Source/native/dual/quantity
replay is required; retain adverse zones, tails and weak improvements. No automatic
promotion, browser replacement, retired search or recurring-review restart.
Update the retained report with exactly four figures; prior calibration CSVs are
supporting checkpoint evidence, not the new trial's generation results.

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

The subsequent user direction prioritizes accepted-refit price/mix diagnosis and
source-backed input improvements toward <10 EUR/MWh full-2025 equal-zone MAE.
Use the accepted single annual refit for diagnostics, not the OOF composite.
Investigate daily gas/coal/carbon and oil inputs, availability, reporting scope
and resource-specific bids in controlled cases. Gas is not an oil-price proxy.
Current gas/oil series are monthly and carbon constant; never invent daily values.
Retain original availability, source units/calendar and licensed-data boundaries.
No observed-generation scaling, new hydro search or browser replacement follows.

The 17 October daily-fuel request authorizes daily_fuel_inputs_2025.py and
run_daily_fuel_dispatch_2025.py with independent audit_daily_fuel_dispatch_2025.py.
Keep the accepted annual refit coefficients frozen and run the four declared
source/shape controls. MIBGAS applies only to ES/PT; other gas stays monthly TTF.
Preserve first-day fallbacks, quote carry flags, gas-day DST and inherited basis
assumptions; do not claim audited delivered fuel prices or Europe-wide daily gas.
All annual hours and source/native-physics/dual/quantity checks remain mandatory.
No automatic baseline promotion or browser integration follows.

The 19 October source/bid follow-up uses renewable_source_bids_2025.py,
run_renewable_source_bids_2025.py and independent audit_renewable_source_bids_2025.py.
IRENA wind parents and on/offshore children remain separate; use complete,
reconciled endpoints only, preserving missing profiles/values and original
source-country/geographic distinctions. PVGIS 14% overall-loss replacement is a
generic sensitivity, not measured country availability; atlite already includes
10% inverter loss, so never multiply an additional 14% onto it. Retain source
weather, static original GSK and fixed hydro. Separate wind/PV pricing columns
require a matched control; preserve conditional-generation-allocation caveats.
Seven predeclared annual cases keep accepted seasonal coefficients frozen;
negative renewable offers are synthetic controls, not observed subsidies.
Retain exactly four report figures; latest all-zone source/bid grid replaces the
historical OOF grid, with old comparison metrics still separately downloadable.

The subsequent source-availability follow-up uses nuclear_availability_2025.py,
run_nuclear_availability_2025.py and independent audit_nuclear_availability_2025.py.
RTE national daily French nuclear availability is separate from generation. Keep
annual-mean, UTC-date and Paris-date controls separate; source date timezone and
subdaily aggregation are not certified. Use the adjacent boundary date explicitly,
never fill missing data. Allocate national available MW by retained source-country
nameplate shares within existing nominal limits, keeping geographic/GSK proxies.
This is not a per-unit outage reconstruction or day-ahead-known information set.
Renewables and accepted bids/hydro/grid remain frozen; no automatic promotion.
Use the existing report/four figures, compact per-zone and monthly CSVs only.

The subsequent user explicitly authorizes bounded inverse market calibration and
an ensemble report. config/inverse-bid-ensemble-2025.json predeclares two rounds,
six step tuples per round (at most12 new full-year clears) with accepted physics
fixed. All2025 prices/generation may inform this new reconstruction only; older
training-only experiments remain frozen. Fit smooth resource-specific proposals,
apply bounded bids before clearing, retain multiple eligible near-best states.
No hour-specific price overwrite, arbitrary capacity fitting, hydro restart or
claim of recovered bids/posterior confidence. Replay every unique witness and
search/ensemble selection independently. No automatic baseline/browser promotion.
Update the existing report, retaining four figures and compact comparison CSVs;
source/witness/proposal arrays stay ignored. Explain inverse modelling literature,
identifiability, adverse cases and paired-investment limitations explicitly.

The 20 October user continuation authorizes a fresh joint supply/network inverse
trial, superseding the previous physics-fixed restriction for this experiment
only. config/joint-network-calibration-2025.json declares exactly16 states,
14 new parameter states plus two verified existing anchors. Every selectable
case needs a complete annual witness; failed physical states need independent
numerical Farkas replay and no annual metrics. Reuse the completed wind control
from the interrupted first driver with exact provenance. Fit effective AC
ratings and a wind-profile derating jointly with two frozen bid anchors; no
free topology/impedance/GSK, hourly limit or target-generation replacement.
The numerical +/-15% AC and -10% wind bounds are diagnostic assumptions, not
verified JAO or weather corrections. Replay modified source availability AND
native branch limits independently; unchanged-source replay alone is insufficient.
Retain adverse cases, all zones and original no-emergency/quantity gates. No
baseline promotion, investment certification, browser replacement or review restart.
Numerical retries keep identical state parameters and tolerance, bind source/retry
provenance, and need matched full-year backend controls. Not Set is unresolved,
never evidence of infeasibility; only independently replayed rays reject a physical
state. Preserve the two-stage retry source; do not edit frozen calculation helpers.

Read PRODUCT.md and TASKS.md first. PRODUCT owns requirements, TASKS owns current
priorities/evidence, README owns setup. Develop on public-v1. Main promotions
require explicit user authorization; the alpha promotion was authorized on
2026-10-10. Never force-push, rewrite published history, change visibility or
expose credentials.

## Focus and publication policy

The 13 October 2026 user clarification governs current priorities: develop one
fast, whole-network bidding-zone synthetic supply-bid model against observed
fixed zonal demand, under dispatch/network constraints, with daily clearing and
hourly prices. Improve observed ENTSO-E price correlations, alongside MAE/bias
and seasonal/tail diagnostics; diagnose Norway/Sweden without dropping other
eligible zones. Native PyPSA matching is not a target or required empirical gate;
use it only when useful as a numerical diagnostic. Independent physics/feasibility,
chronology, source provenance and held-out validation requirements remain.
Keep evaluation prices out of bid construction and predeclare splits/thresholds
before tuning. Historical training prices may enter only the explicitly authorized
15 October bounded calibration described below. Maintain one active model; do not restart paused model families.
The current annual-v7 witness clears independent hours with fixed hydro; daily
orchestration is the agreed workflow to implement, not an already verified feature.
Preserve frozen producers/references and give any changed implementation fresh
provenance. TASKS owns the concise model inventory and current priorities.

Input-sensitivity diagnostics are authorized on 13 October 2026. Use
input_sensitivity_2025.py, run_input_sensitivity_2025.py and independent
audit_input_sensitivity_2025.py. Predeclared +/-10% wind availability, gas, oil
and carbon cases keep annual-v7 hydro, demand, capacity/GSK and grid fixed.
These are measured sensitivities, not source corrections, causal error shares or
new accepted baseline candidates. Elhub generation is comparison evidence only;
never use it as renewable availability. Preserve failures and all eligible zones.

The subsequent wind-source follow-up uses norway_wind_geography_2025.py and
separate run/audit_norway_wind_geography_2025.py producers. Dated NVE turbine
batches supply onshore zone shares only: preserve national hourly available MW,
the inherited IRENA trajectory and all non-target inputs; recompute capacity GSKs
explicitly. Common national weather and within-zone bus shares are diagnostic
proxies, not verified site profiles. Preserve this fresh witness/dependency chain.
Current-operating registries do not prove complete historical fleets. The public
NVE GIS collector inventories site points only; extensions may share a point and
must not duplicate turbine capacity. No generation-target scaling, baseline
promotion, browser replacement or recurring-review restart is implied.

A fresh regional-water candidate is authorized on 13 October 2026. Use
regional_water_candidate_2025.py, run_regional_water_candidate_2025.py and
independent audit_regional_water_candidate_2025.py with a new ignored output root.
Protect annual-v7 and all frozen dependency files. Regional HBV/EL1–EL5 stock
inputs replace national pooling only for Norway; keep provenance, electrical/stored
unit conversion, chronology, turbine bounds and adverse observed-price results.
365 daily groups still contain independent hourly clears with fixed hydro schedules.
The candidate is not accepted or integrated merely by completing a run.

Active work returns to the fixed-hydro supply-curve checkpoint by user request
(10 October 2026). Maintain two reports; daily bidding and compact rolling storage
are paused references. Do not restart them or publish the parked Norwegian hydro
trial without a new user request. Fixed output is not fixed-price bidding.

The user subsequently authorized the fixed-hydro/resource-bid combination. Its
fresh producer is tools/hybrid_fixed_hydro_2025.py; independent --audit reconstructs
annual physics, and tools/evaluate_fixed_hydro_bids_2025.py publishes controlled
same-observation comparisons in the existing fixed-hydro report. Preserve the
frozen checkpoint producer and sources. By subsequent user decision, keep only the complete resource-bid formulation.
Legacy/fuel-only variants, their checkpoints and comparison exports are retired.
tools/diagnose_fixed_hydro_errors_2025.py audits capacity/energy and high-price
sensitivity in the same report. Its demand/GSK probes are diagnostics, not new
baseline candidates, calibration or accepted physical scenarios. No forecast, adaptive
hydro or browser replacement is implied. Audited zonal inputs remain outstanding.
The Norwegian source-input pilot uses prepare_norway_zonal_inputs_2025.py and
independent audit_norway_zonal_inputs_2025.py. Raw Elhub/NVE observations and
receipts stay in ignored data/bidding-zone-source-audit-2025/. Preserve UTC/DST,
group missingness and separate wildcard production; full-hour coverage does not
certify total-load scope, metering completeness or historical fleet capacity.

The user-authorized Norwegian water-input update uses collect_nve_hydrology.ts,
nve_hydro_inputs_2025.py and update_norway_hydro_2025.py. Only Norway substitutes
source-backed NVE HBV inflow and observed reservoir boundary stocks/capacity;
other countries retain original inflows and fixed schedules. Electrical-equivalent
inputs are converted to stored units, preserving original turbine efficiency.
Keep the production/stock-derived NVE inflow column excluded. Independent saved
water/network/objective replay and all eligible observed-price comparisons use
audit_nve_hydro_model_2025.py. report_nve_hydro_update_2025.py updates the existing
fixed-hydro report only. Preserve the frozen source/witness chain. Country pooling,
net-inflow/gross-stock basis and fixed-schedule limitations remain explicit.
Improved annual energy agreement alone does not authorize baseline promotion;
retain adverse price outcomes and reconcile injection geography before acceptance.

Subsequent authorization permits targeted price/geography diagnostics and bounded
48-hour hydro rescheduling. nve_hydro_diagnostics.py reconstructs verified sources;
diagnose_nve_hydro_prices_2025.py checks price derivatives and bus placement;
run_nve_bus_geography_2025.py tests unchanged Norwegian hydro AND demand at their
original buses. run_nve_hydro_windows_2025.py / nve_hydro_flexibility.py retain each
unit's inflow, efficiency, zero spill, capacity and exact opening/closing stocks,
with ±20% hourly output bounds capped by turbine MW. No annual adaptive policy.
audit_nve_hydro_diagnostics_2025.py independently replays saved component physics;
report_nve_hydro_diagnostics_2025.py rewrites the existing fixed-hydro report only.
Keep these completed producers frozen. Relocated run-of-river dispatch may change:
use independently replayed current hydro bounds, not the annual producer's inherited
fixed_no_hydro_twh field. Material-negative counts use price < -1e-6 EUR/MWh;
strict <0 legacy metrics include numerical zeros and must stay distinguishable.

Whole-network bidding-zone work is authorized (12 October 2026).
bidding_zone_network_2025.py protects boundaries before stub removal, uses pinned
geographic sources/plant records and conserves original parent hourly volumes.
global_bidding_zone_2025.py projects physical rows to one balance per market area,
retaining separate island RHS corrections and HVDC losses. Do not silently use
provider reporting-area labels as certified commercial zones. Mixed aggregate
renewable/unsupported-fuel location shares remain explicitly marked proxies.
run_bidding_zone_network_2025.py uses a common country/zonal backbone with native
checks; audit_bidding_zone_network_2025.py independently replays source allocation
and component physics. report_bidding_zone_network_2025.py updates the existing
fixed-hydro article only. Require fresh roots and finite guards; distinguish
unresolved solver status from proven infeasibility. No browser engine replacement.

Maintain these reproducible models:

- Fixed-hydro annual checkpoint: tools/fixed_reservoir_screening_2025.py and
  tools/report_fixed_reservoir_screening_2025.py; report
  docs/european-physical-synthetic-clearing-2025.md.
- Paused daily resource-bidding reference: tools/fast_daily_market.py is the experimental performance
  adapter; tools/terminal_daily_market.py is the retained producer,
  tools/terminal_settlement_bids.py, simple_resource_bids.py and shared daily/
  physical compiler modules; independent replay tools/audit_terminal_daily_market.py;
  report tools/compare_daily_dispatch_prices.py → docs/daily-fuel-dispatch-2025.md.
  The adapter records its source hash in fresh manifests and leaves archived
  producer/dependency files intact. Forecasts and bids remain model-generated.
  Rules config/simple-bidding/defaults.json; thermal inputs thermal_bid_rules.py
  and prepare_fuel_prices.py; direct validation prices collect_dispatch_validation_prices.py.

Paused compact daily-formulation trial: tools/compact_zonal_market.py and
run_compact_zonal_2025.py; report_compact_zonal_2025.py appends evidence to the
current daily report. Keep its transport/rolling-policy assumptions separate from
the frozen physical/bidding reference. No daily reservoir resets, dispatch-based
renewable availability or silent commercial-capacity claims. Retain one current
annual trial/witness and small numerical fixtures; do not create a third report.

Only these two reports and docs/workbench-methodology.md are active publications.
The current report uses prepare_seasonal_dispatch_report_2025.py,
independent audit_seasonal_dispatch_report_2025.py and
write_concise_dispatch_report_2025.py. Its derived root is
seasonal-report-v1/verification-v1; intraday-report-v1 is the previous reference.
Maintain the concise baseline/exploratory structure and four tracked figures,
including the all-zone MAE grid; do not rerun historical append-style report
producers over it. Physical producers and original witnesses remain frozen.
Primary comparisons now use full-2025 seasonal out-of-fold predictions; never mix
them with older Jul–Dec headlines or the in-sample all-year refit. National Ember
checks remain separate from zonal A75 coverage. NO5 generation is missing,
DE excludes LU, FR is national.
Do not recreate removed reports or restart retired model/search programmes.
Only used source tools and minimal retained-model evidence may remain
as supporting dependencies; their presence is not an instruction to develop them.
Keep methods/provenance/limitations in retained reports, not a proliferating catalogue.
Preserve the single retained PyPSA-Eur 2025 reference (archival candidate-006), source
hashes, annual witness replay and coefficients needed for fixed-hydro preparation.
No obsolete candidate restoration. Automatic hourly reviews are disabled.

## Research operating rules

The subsequent price-mechanism investigation captures a fresh unchanged-baseline
primal/dual witness with run_price_mechanism_2025.py and independent
audit_price_mechanism_2025.py; price_mechanism_2025.py defines offer grouping and
dual checks. Preserve full-year mixed/tied membership, local-interior ambiguity
and dual degeneracy; local marginal evidence is not a unique real price setter.
Island-balance terms include HVDC coupling/losses; passive PTDF/GSK contributions
are witness identities, not causal error shares or certified commercial congestion.
Predeclared calendar +/-1 MW probes change demand along the GSK and retain source
water, bids and ratings; independently replay saved primals and supporting slopes.
Monthly fuel-price association is distinct from hourly residual demand and causal
fuel sensitivity. No adaptive-hydro/search restart or baseline promotion follows.

The 14 October 2026 follow-up authorizes a Europe-wide residual-demand source
audit before selecting another input correction. Use residual_demand_audit_2025.py
and independent replay_residual_demand_audit_2025.py with a fresh ignored root.
Protect retained model producers; this audit does not change coefficients or run
another market solve. Distinguish available wind/solar from reported generation,
full low-cost availability envelopes from dispatched supply, fixed hydro from
adaptive water, and national/reference demand from certified zonal demand.
One-MW supply and five-percent national-demand flags are investigation thresholds,
not empirical acceptance gates or calibrated causal error shares. Preserve missing
types/hours, source scope and all 48 modeled / all eligible observed areas.

The subsequent 14 October user direction keeps hydro fixed and prioritizes
whole-fleet residual-demand/supply-stack improvements over further flexible-hydro
experiments. The simple_supply_stack_2025.py diagnostic has separate run/audit
producers; preserve electrical islands, original offers/availability and fixed
injections. Summed physical corridor ratings are model-derived transport envelopes,
not verified JAO commercial limits. Passing transport balances does not establish
native AC/PTDF feasibility or authorize baseline promotion.

A separate residual_price_benchmark_2025.py reference may fit historical prices
in its declared training period only, with independent training-optimality and
prediction replay. That reference remains separate from dispatch and investment valuation; the
later authorized bid-calibration experiment has its own training-only exception. Declare temporal cohorts before fitting;
2025 has already been inspected, so call its split retrospective temporal evaluation,
not untouched held-out validation. Keep all eligible areas, negative prices and
source missingness. Reference accuracy cannot certify dispatch or scenario effects.

The 15 October follow-up uses diagnose_residual_response_2025.py and separate
source/response replay audit_residual_response_2025.py. Training-only residual
quintiles define July–December descriptive cohorts, not causal supply curves or
untouched validation. Inventory original available MW, bid profiles and efficiencies;
exclude emergency from real supply and distinguish local price-tier envelopes from
network-deliverable dispatch. Exact profile counts may include negligible floating
point differences. Preserve fixed hydro and frozen baseline; the report producer
updates the existing article only, with full arrays/plots locally ignored.

Generation-mix validation uses generation_mix_2025.py and compare_dispatch_mix_2025.py
with a fresh ignored root. Independent audit_dispatch_mix_2025.py writes a fresh
verification subdirectory; report_dispatch_mix_2025.py updates the retained article.
Compare saved dispatch, not available supply. Equal-bid disaggregation is conditional:
report proportional illustrations plus label-specific bounds, regrouping capacities
before computing country/combined-fuel bounds. Those bounds are not jointly
attainable or a search over all primal optima. Country source placements under GSKs
and implied generation-minus-demand exports are not verified physical border flows.
Require all constituent zones and explicit type coverage; storage B10/B25 stays
separate from primary generation. Preserve source taxonomy/gross-net differences,
no generation-derived availability fitting, no new solve or baseline promotion.

The latest 15 October user request explicitly authorizes bounded fuel-anchored
bid calibration inside the unchanged coupled European model, before further input
corrections. This supersedes earlier blanket bans on price-fitted dispatch bids
only for the declared training period/experiment. Evaluation prices and generation
must not enter fitting/selection. Keep availability, demand, fixed hydro, GSKs and
network constraints fixed; learn few transparent gas/coal/nuclear adjustments.
Use generation allocation intervals and declared monthly trade comparisons as
soft training checks, never impose infeasible generation or treat implied exports
as verified border flows. Predeclare bounds, objective weights and finite search;
2025 temporal evaluation remains retrospective. Baseline promotion, investment
acceptance and empirical thresholds are separate gates. Preserve frozen producers.
The completed trial uses bid_calibration_2025.py, run_bid_calibration_2025.py,
evaluate_bid_calibration_probes_2025.py and independent audit_bid_calibration_2025.py.
The declared score selected unchanged bids. Preserve primary selection separately
from the two training-selected nonzero annual diagnostics; no baseline promotion.
report_bid_calibration_2025.py updates the existing article, with figures local.

The subsequent user authorization extends this experiment to bidding-zone/resource
offsets and monotone two-block thermal offers. Use fresh zonal_bid_blocks_2025.py
and run/audit_zonal_bid_blocks_2025.py; freeze completed global-offset producers.
Declare training-only proposal estimators, finite strengths, shrinkage and search
before solving. Partition original thermal availability; never create new capacity.
Keep physical rows/GSKs/hydro/demand fixed and independently replay original
component physics after collapsing block dispatch. Evaluate both training-selected
stages with all eligible zones and quantity/trade checks; no automatic promotion.
The completed authoritative root is zonal-bid-blocks-v2 with verification-v1;
stage-one offsets select zero, stage-two selects 21 upper spreads. Six targeted
tests and independent block-collapse/native-component/dual/selection replay pass.
Retain common-formulation control: equal-cost column splitting can change optimal
dual price witnesses despite equivalent capacity/feasible sets. No price identity
or empirical acceptance claim. Initial interrupted v1 has no retained NPZs and
must not be resumed. report_zonal_bid_blocks_2025.py updates the same article;
plots and all bulk witnesses stay ignored locally. Preserve completed producers.

The 16 October implementation authorizes joint resource curves and hourly-shape
validation. hourly_offer_curves_2025.py preserves capacity and physical columns,
splitting mixed zero-cost groups by renewable versus other source membership
before applying negative offers. Nuclear has no peaking blocks. Freeze the
Jan–April fit / May–June selection / Jul–Dec retrospective evaluation design;
use all eligible zones, generation/trade checks and independent original-component
and selection replay. No input time-shift or outage correction merely from a lag
correlation; no unit commitment, hydro/storage restart, browser or baseline promotion.
The completed authoritative hourly-offer-curves-v1/verification-v1 replay covers
11 fit states and 16 LP certificates, selecting [0,.5,0]. Preserve this producer,
hourly_offer_curves_2025.py and diagnosis-v2. The selected renewable discount is
zero; negative-offer tests were implemented and rejected by declared selection.
Current presentation-v2 updates the existing report. Seven tests and independent
capacity/physics/duals/chronological-selection/hourly-metric/diagnostic replay pass.
The next step is source timing/operational availability, not post-evaluation tuning
of the frozen design. Thermal/combined aliases share one selected annual witness.

The subsequent user request authorizes a fresh intraday-bid experiment. Preserve
the preceding experiment; use intraday_offer_bids_2025.py and separate run/audit
producers with a fresh root. Jan–Apr training-only residual/time-of-day features,
May–Jun finite selection and Jul–Dec retrospective evaluation remain distinct.
Hourly synthetic fuel-anchored bid corrections do not establish measured bidding
behaviour, new available MW, outages, commitment or adaptive hydro. Keep original
physics, all eligible price zones and generation/trade checks. Update the concise
report, including an all-zone MAE grid; no baseline/browser promotion is implied.
The completed intraday-offers-v1/verification-v1 independently replays ten LP
certificates and selects [1,1]. Freeze its helper/runner and source inputs.
Generation/report derivation has separate fresh provenance; prior hourly-curve
and annual-v7 witnesses remain reference evidence, not competing active searches.

The subsequent user direction replaces residual-demand bid predictors with
seasonal/time-of-day bids. Fresh seasonal_calendar_bids_2025.py and separate
run/audit producers use calendar-only seasonal/daily interactions and an optional
training-month Ember national fuel signal. Demand/weather remain physical inputs,
not fitted hourly bid predictors; generation never becomes availability. Use
three whole-month seasonal rotations, each with disjoint fit/selection/test
months and 48-hour price-boundary purges. Report all-year out-of-fold interpolation
separately from any all-year-fitted reconstruction; neither is future-year or
untouched validation. This explicitly supersedes Jul–Dec-only reporting for the
new experiment, without changing earlier frozen evidence or acceptance gates.
Completed seasonal-calendar-v1/verification-v1 independently replays eleven LP
certificates. All folds select calendar+Ember on the joint score; Ember worsens
selection-price MAE versus calendar-only while improving quantity/trade checks.
Report that trade-off; calendar-only outer-test accuracy has not been measured.
Keep the three-fold OOF witness distinct from the all-year in-sample refit.

- Inspect actual supervisor/worker processes and locks before computations.
  Receipts do not establish liveness or progress. If the managed environment is
  inaccessible, say verification is unavailable; do not rely on stale status.
- Freeze producer/dependency source and package versions during live jobs. Do not
  edit under a live producer/auditor. Changes require fresh manifests/output roots,
  never implicit resumption across changed code, data or coefficients.
- Use pinned Python: data/pypsa-eur/upstream/.pixi/envs/default/bin/python.
  Inspect actual cgroup memory/CPU limits; keep finite memory, solver and worker guards.
- Never substitute dispatch for original renewable availability. Preserve demand,
  original inflows, efficiency, standing losses, power/energy bounds, spill and
  hourly chronology. Actual inventories carry across days; no daily resets/water gifts.
- Fixed reservoir injections are conditional schedules, not adaptive availability.
  Native/fast parity verifies a formulation, not market realism, forecasts or returns.
  Optimal termination, saved-primal replay, closure and cycling/shortage disclosure
  are mandatory. Daily policies are not annual-optimum certificates.
- Terminal mode-selection prepasses must keep original bids/physics/common closing
  stocks, terminate optimal and cycling-free, then submit exclusive directions.
  Disclose the exception and timing. It does not guarantee future network feasibility.
- Source country/AC-island areas/GSKs/N-0 ratings are not verified commercial zones
  or JAO domains. Keep island accounting and controllable link bounds/efficiencies.
  Do not combine passive constraints and regional PTDFs without defined coupling.
- Any annual optimisation claim still requires explicit independently checked
  feasibility/convergence bounds validated against a smaller monolithic reference.
  Do not silently weaken empirical, annual, paired-investment or integration gates.
- For observations preserve source requests/hashes, UTC alignment, interval weights,
  geography and missingness. Do not fit and validate on the same observations.
  Predeclare thresholds/splits before empirical acceptance; report all eligible areas.
- Paired investments use common exogenous inputs/boundaries. Recompute strategies/
  forecasts for each investment. Publish adverse outcomes as well as improvements.
  Gross system cost savings are not investor income or congestion rent.
- Raw provider inputs and large witnesses stay in ignored data/. No Git bulk backups,
  secrets or third-party input mirrors. Compact public outputs need provenance.
- Keep only compact failed diagnostics needed to explain retained results and
  the immediate preceding state. Delete obsolete runs; protect current source/replay
  dependencies and never infer a deleted result has passed verification.

## Source/toolchain notes

Pinned PyPSA-Eur v2026.08.0 source is data/pypsa-eur/upstream (a5408e9), pixi in
 data/pypsa-eur/bin/pixi. ERA5 and monthly-weather outputs must be checked by actual
calendar/hash; source nuclear availability ending in 2024 is a declared 2025 proxy.
IRENA linear end-2024/end-2025 wind/solar capacity change is assumed commissioning,
not observed dates. Capacity alone establishes neither reservoir water nor energy.
Monthly fuel compiler uses World Bank TTF/Brent and ECB FX. Heating-value compatibility,
delivered oil and observed EUA remain unresolved; never invent historical quotes.
Credential-backed uncached collection stays offline in Python, outside src/.

For numerical tests use the pinned interpreter with targeted tools/test_*.py
modules. Existing native/storage/physical fixtures are verification dependencies.
Do not regenerate them blindly or treat a structural fixture as annual evidence.

## Browser architecture and checks

- Bun 1.4.2, bun.lock and bun install --frozen-lockfile; retain the 24-hour package
  release age. Vite/React 19/TanStack Router/Tailwind v4; static Pages, no persistent
  server, SSR, account or database. Keep strict TypeScript settings.
- Map at /, Docs at /docs, Markdown at /docs/$slug. Only three active articles.
  tools/prepare-pages.ts generates direct HTML routes. publicAsset() from
  src/lib/research.ts handles every static fetch/link under /grid-conductor/.
- Live src/lib/fast-entsoe-lp.ts remains the reduced-form two-zone screen, with
  exact cable trapezoid, javascript-lp-solver batteries, finite-difference shadow
  checks, quarter-hour annual sums and welfare caps. Do not replace it implicitly.
- IndexedDB persistence in workbench.ts: stable UUIDs, ordered units, revision
  checks and edit invalidation. No cloud synchronization; only line/battery UI.
- Preserve schema-v3 observed screening, zone-prices-2025 and carbon-spreads-2025
  baseline data. Publish carbon metrics with tools/publish_carbon_spreads.ts after
  offline publish_map_carbon_2025.py; hourly generation-derived inputs stay ignored. Signed annual rent combines directed flows; floor display only.
  Scheduled/physical classification remains unverified without original receipts.
- Left carbon card: mean absolute hourly lifecycle spread during observed >EUR5/MWh
  price gaps, label/value/units only. Coverage/proxy limits remain in Docs/evidence.
  Right scenario proxy: savings negative, increases positive; not avoided emissions.
  Lifecycle factors, operational pricing and dispatch emissions are separate.
  Missing factors remain unknown; no intensity × demand-minus-imports “carbon loss”.
- Navigation stays Workbench/Docs. Legacy /network and /targets routes, browser
  network-lab code and their derived exports are retired; do not restore them.
- Run appropriate checks: bun run lint, typecheck, test, build; production Chromium
  workbench/math smoke checks. Verify mobile overflow, images, downloads
  and project-base deep links. Never claim unperformed checks.
- Publication claims require successful CI/Pages and unauthenticated public URL
  verification; a build or push is insufficient. Name material failures explicitly.

## Data allowlist

Only 2025 external inputs used by models/baseline belong in local caches, with
necessary adjacent-year endpoints/release provenance labelled. Keep the fixed
hydro reference, native coefficients, current annual witness and water schedule
because the retained models require them. Keep installed pinned toolchains.
No unused experiment exports, duplicate model runs or alternative search state.
Public research assets are allowlisted in tools/check_public_assets.py and
.gitignore; run the asset check before builds. Do not commit ignored intermediates
or republish old charts just because a frozen historical producer can write them.

Before offline model/report work in a fresh checkout, run
`python3 tools/pack_model_metadata.py --restore`. This restores exact immutable
JSON bytes from Git's gzip archives without modifying calculation source hashes.
After successful report generation, run the packer without --restore and the
asset check. Hydrated JSON remains ignored/local and is excluded from dist.
