# Hourly zonal dispatch: implementation and verification plan

Planning document, 7 October 2026. This records the accepted direction, proposed
implementation and unresolved design choices. It is not a solved model or a
validation claim.

## Summary and intended result

Build a continuous, bidding-zone dispatch model for all 8,760 UTC hours of 2025.
Prepare inputs once; evaluate transmission and battery investments through
matched baseline and scenario solves. Preserve hourly renewable availability,
network restrictions and chronological storage. Aim for interactive estimates
in seconds and measure whether that target is achievable on supported devices.

The primary calculation remains an actual hourly optimisation. Precomputed
response curves and statistical surrogates are not required for this plan.
Caching an identical baseline is exact reuse, not interpolation. If runtime
misses the target, publish the measurements and review alternatives rather than
silently replacing chronology or the calculation.

Observed congestion rent identifies candidate borders; paired system operating
cost changes estimate investment opportunity. These are different quantities.
The new model approximates a zonal market with fixed demand and estimated supply
costs. It does not reproduce EUPHEMIA orders, acceptance rules or price formation.

## Scope and relationship to existing work

- Use actual bidding zones, including split countries, rather than one node per
  country. Freeze the supported zone list and treatment of external boundaries.
- Continuous generation, controllable exchange, reservoirs, pumped storage and
  new batteries; no individual plant commitment, start-up costs or complex bids
  in the first version. Declare these omissions in every result.
- Perfect foresight over the year is an initial dispatch assumption. Compare
  sensitivity to forecast/terminal assumptions before interpreting storage value
  as realised trading revenue.
- Preserve the 2013 weekly, 2025 conditional and existing annual research as
  separate evidence. Existing N1–N5 and empirical gates remain intact.
- The zonal model has its own identity, inputs and verification chain. An
  aggregated solve cannot close the unresolved 128-node annual optimum gate.
  Developing it need not wait for that gate; replacing the public annual
  estimator still needs an explicit reviewed transition and applicable annual,
  empirical and investment acceptance evidence.
- Reuse the existing sparse HiGHS engine and formulation references where
  compatible. PyPSA-Eur remains an input source and physical reference; native
  PyPSA supplies an independently constructed matched zonal reference.

## Input preparation and source contracts

Every input carries period, units, geographic identity, source/version/hash,
coverage, processing method and proxy status. Separate model inputs from observed
validation data. Never fit and validate on the same observations unnoticed.

| Input | Preparation and acceptance |
| --- | --- |
| Demand | Audit ENTSO-E load definitions and zone domains; integrate subhourly MW to hourly MWh, then hourly average MW. Resolve national versus bidding-zone scope, storage consumption and embedded generation. Missing hours block a complete historical-input claim. |
| Wind/solar | Sum asset-level available MW in each zone from original capacity and weather profiles. Preserve curtailment freedom. Observed or solved output is validation data, not available capacity. |
| Thermal/nuclear | Group assets by zone and compatible cost/availability characteristics. Retain capacity, efficiency, fuel/variable costs and documented outage/proxy assumptions. Audit 2025 operating carbon policy separately; the existing zero-carbon-price input is not a calibrated market baseline. |
| Hydro | Distinguish run-of-river availability, reservoir inflow and pumped-storage recycling. Preserve electrical-energy units, turbine/pump capacities, efficiencies, standing loss and reservoir bounds. Precompute inflows, not reservoir dispatch. |
| Storage | Group only physically compatible assets; preserve separate charge/discharge limits and initial/terminal rules. Test aggregation for fictitious access to water or energy across assets. |
| Transmission | Obtain hourly commercial capacity or complete flow-based domains with audited directions, units and restrictions. Observed flow is not capacity. Physical line ratings are only an explicitly labelled alternative approximation. |
| Prices/generation/exchanges | Retain audited observations for validation, including negative values and missing intervals. Resolve A09/A11 provenance before exchange comparisons; reported generation coverage is not whole-fleet completeness. |

Use the exact interval [2025-01-01 00:00 UTC, 2026-01-01 00:00 UTC).
Account for daylight-saving/provider timestamps explicitly. The hourly model
approximates subhourly market conditions; 2025 subhourly prices must be aggregated
with documented weights. Compute observed rent at its original aligned resolution;
product-of-hourly-averages need not equal the original rent integral.

Zone mapping must use authoritative geographic/domain evidence. A mixed-zone
128-node cluster cannot be assigned by centroid or duplicated into both zones.
Where necessary, map original asset locations before clustering and reconstruct
zone-level availability. Missing asset geography stays a blocker.

### Candidate sources identified through Clarigrid

The user identified the following candidate datasets. Treat their 2025 coverage,
versions, units, licence and geographical scope as audit questions until fetched
and checked; a catalog entry is not evidence of a complete 2025 input.

| Candidate | Intended role | Required checks and limits |
| --- | --- | --- |
| Our World in Data energy dataset | Annual country/technology generation cross-check | Verify actual 2025 rows and original upstream providers. National totals cannot allocate hourly generation or split bidding zones. Shared Ember/other upstream data are not independent validation. |
| Energy-Charts installed capacity | Fleet capacity cross-check or documented input where sufficiently resolved | Verify technology definitions, geography, effective dates, additions/retirements and net/gross scope. Year-end capacity is not capacity available throughout 2025; national totals need justified zonal allocation. |
| Ember monthly/yearly electricity | Monthly seasonality and annual generation/mix reconciliation | Verify 2025 coverage, revisions, primary generation versus pumped discharge and net/gross accounting. Existing Ember reference audits can be reused only with matching hashes/scope. No invented hourly profiles from monthly totals. |
| IRENA renewable capacity/generation | Renewable fleet and annual energy cross-check | Verify reporting year and publication vintage, technology and geographic coverage. Distinguish MW capacity from MWh generation and observed data from estimates. Annual generation is not hourly availability. |
| ERA5 atmospheric reanalysis | Weather input to hourly wind/solar and catchment/inflow modelling | Requires spatial asset layouts, wind hub height/turbine curves, solar orientation/technology and conversion models. Hydro also needs runoff/catchments/routing and energy conversion, not atmospheric variables alone. Audit hourly timestamps and annual resource weighting. |

Prefer the existing hash-pinned 2025 PyPSA-Eur weather/availability/inflow inputs
when their scope is suitable; do not download another ERA5 year merely to
evaluate scenarios. Reconstruct only missing or separately reviewed inputs.
Observed energy totals can audit or inform a disclosed training-only calibration
of weather conversion; they must not become dispatch-as-availability or conceal
curtailment, outages and accounting differences.

Clarigrid may simplify discovery and access; retain original provider provenance
and the complete transformation chain. It does not supply the missing market
bids, commercial network domains or operating costs merely by providing energy
statistics. Commercial capacity and zonal geography remain separate Z0 blockers.

Access check on 7 October 2026: no Clarigrid plugin was returned by plugin
discovery, and an unauthenticated HTTPS request to the supplied MCP endpoint
returned 401. No dataset schema, 2025 coverage or licence was verified through
that endpoint. An authenticated custom connection is needed for MCP collection;
original-provider read-only source audits can proceed independently. Keep
credentials outside Git and the public app.

### Direct-provider access verified

On 7 October 2026, public Clarigrid dataset pages linked original providers.
`tools/collect_zonal_source_candidates.py` now collects bounded source files
directly, records URL/byte count/SHA-256 and rechecks cached identity/coverage.
No Clarigrid account or browser credential is required for these three sources.
Provider caches remain ignored under `data/pypsa-eur/zonal-source-candidates/`.

- [OWID CSV](https://nyc3.digitaloceanspaces.com/owid-public/data/energy/owid-energy-data.csv):
  accessible, but the fetched version has **zero 2025 rows**. It cannot currently
  supply the proposed 2025 generation cross-check.
- [Ember monthly CSV](https://storage.googleapis.com/emb-prod-bkt-publicdata/public-downloads/monthly_full_release_long_format.csv):
  accessible, with 49,463 rows dated in 2025, 94 distinct area labels and records
  across all twelve months. This is a dataset inventory, not complete generation
  coverage for every country/fuel; category and accounting audits remain required.
- [Energy-Charts German 2025 capacity](https://api.energy-charts.info/installed_power?country=de&year=2025):
  accessible, with 18 technology entries. The response includes a deprecated
  field; API migration, units and effective-date semantics require review before
  accepting fleet inputs. No map-wide capacity coverage is inferred.
- [IRENA](https://www.irena.org/Data): the catalog points to a portal, not a
  verified machine-readable file; retrieval/schema/2025 coverage remain open.
- [ERA5](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels):
  original CDS source identified; new downloads require configured authentication
  and licence acceptance. Reuse the existing verified weather where suitable.

Three collector tests check absent years, preserved monthly scope, changed schema
and cache identity rejection. Direct collection connects candidate source access,
not the dispatch model: Z0 mapping, capacity/cost and coverage gates still apply.

### Aggregation policy

Start with multiple supply blocks per technology where efficiencies, marginal
costs or availability differ. Record each block's membership. Exact aggregation
is limited to compatible independent assets; ramps, energy budgets, reservoir
connectivity and varying merit order can invalidate a simple sum. Benchmark
progressively coarser groupings against a disaggregated zonal reference before
choosing the interactive configuration. Keep hourly cost variation where sourced.

## Mathematical formulation

Let t index hours, z zones, k supply blocks and s storage assets. Power is MW,
inventory is MWh, costs are EUR/MWh and interval duration dt is one hour.
Minimise the sum over hours of generation cost, explicitly modelled variable
storage/transfer costs and penalised unserved demand, all multiplied by dt.
With fixed served demand this is a cost-minimising market approximation; it does
not estimate consumer demand response or reproduce submitted auction bids.

For every zone and hour:

```text
sum(generation) + sum(storage discharge) - sum(storage charge)
  + net imports + unserved demand = demand
0 <= generation[k,t] <= available_MW[k,t]
```

Generation may be curtailed by not dispatching its available capacity. Add no
unbounded free-disposal sink by default. If required to match a reference,
represent disposal explicitly, give it identical bounds/cost in both models and
report it. Never hide shortage or disposal in a validated economic result.

For storage:

```text
energy[s,t] = retention[s,t] * energy[s,t-1]
              + inflow[s,t] * dt
              + eta_charge[s] * charge[s,t] * dt
              - discharge[s,t] * dt / eta_discharge[s]
              - spill[s,t] * dt
0 <= energy[s,t] <= energy_capacity[s]
0 <= charge[s,t] <= charge_capacity[s,t]
0 <= discharge[s,t] <= discharge_capacity[s,t]
```

Define inflow/spill on the inventory-energy side consistently with the source.
Preserve reference spill bounds; do not restrict spill to contemporaneous inflow
unless the chosen physics requires it. Reservoir turbines have no charging
variable; pumped storage does. No daily or monthly inventory reset is allowed.
Initial energy and terminal policy must be explicit. Compare identical boundary
conditions for existing storage; new batteries start and finish empty in the
first matched experiments. A cyclic-year sensitivity must not introduce free
initial energy or be presented as observed operation.

Continuous storage can charge and discharge simultaneously under some costs.
Detect and report cycling; test negative-price cases. Throughput costs must be
justified inputs, not an undocumented numerical fix. Material artificial cycling
blocks acceptance; a stricter formulation would require a reviewed model change.

### Commercial network representation

First implement a labelled bilateral transport approximation: one signed flow
per corridor with separate forward/reverse hourly capacities. Enforce both zone
balances and declared losses (initially lossless, with an explicit limitation).
No internal AC Kirchhoff constraints are asserted in this zonal transport model.

Where verified flow-based data are available, use PTDF times zonal net export
bounded by RAM, with the corresponding reference point and complete allocation
restrictions. Avoid overlapping bilateral and flow-based restrictions for the
same region. Virtual hubs, HVDC coupling, LTA and external exchanges need an
explicit formulation and sample replay before support. Missing domains cannot
be replaced with unconstrained trade or inferred capacity.

A bilateral added-capacity experiment means additional commercial transfer
capacity, not necessarily a physical cable. A physical investment in a flow-based
region requires a defensible update to its constraint domain; simply adding MW
to RAM is unsupported. Initially restrict scenarios to the verified intervention
semantics and label them accordingly.

## Outputs and investment comparisons

Return hourly generation, flows, storage, shortage, curtailment, prices and costs;
annual/monthly sums must reconcile to those arrays. Balance duals are model
marginal prices with documented scaling/sign, not observed auction prices.
Finite-difference demand perturbations check dual interpretation; degeneracy
means equal objectives need not give identical flows or prices.

```text
gross system benefit = baseline operating cost - scenario operating cost
```

Use the same complete input, boundary policy and objective components in both
solves. Keep capex, fixed operating costs, financing and investor revenue separate.
Report signed benefits and any shortage changes. Report model congestion-rent
proxies separately from cost savings; do not equate rent reduction with welfare.
Lifecycle production intensity and signed intervention emissions retain their
own factor/completeness gates; no automatic conversion of savings into carbon.

For numerically bounded solves, compute the benefit interval from both solves:
[baseline lower - scenario upper, baseline upper - scenario lower]. Large baseline
costs can conceal poor relative accuracy on a small investment benefit. A benefit
claim needs a sufficiently narrow interval, not just two apparently small
relative objective gaps. Time limits produce incomplete results, never optimum
or price certificates.

## Engine, caching and performance experiment

Prepare source data and sparse matrix structure offline; do not rebuild weather,
import NetCDF or reconstruct PyPSA objects for each browser scenario. Export a
versioned compact array bundle, index maps and manifest; raw caches stay ignored.
Measure compressed bytes, decode time and peak memory before public distribution.
Keep immutable arrays separate from changed scenario bounds/columns.

Use the existing worker/WASM architecture for cancellable browser solves. Cache
only fully verified baseline results keyed by input hash, model/code/solver
version and numerical/boundary settings. Cache verified bases where supported;
invalidate on any relevant change. Battery additions change matrix structure and
may not support the same warm start as a capacity edit.

Without intertemporal coupling, benchmark exact independent-hour solves against
a monolithic LP. With storage, first benchmark one sparse chronological annual
LP. Decomposition is an alternative only after monolithic smaller-reference
verification with explicit feasibility and convergence bounds. Carrying an
arbitrary sequential SOC is not an equivalent annual optimisation.

Illustrative sizing, not a measured model: 40 zones and 10 supply blocks per zone
already give about 3.5 million generation variables over 8,760 hours, before flows
and storage. Sparse memory and factorisation can dominate. Count actual variables,
nonzeros and solver memory before assuming the year is inexpensive.

Proposed engineering benchmark: warm-input, cached-baseline scenario result within
10 seconds on a declared desktop configuration. This is a provisional target,
not verified performance or a new acceptance promise. Measure cold end-to-end
load/baseline/scenario separately; include mobile results and repeated-run median
and p95. Compare 48h, 168h, one month and 8,760h; no representative-hour replacement.
If annual WASM exceeds memory/runtime budgets, report the failure and review
scope/aggregation/hosting options. Static hosting and no cloud solver remain
requirements; do not introduce a server or approximation silently.

## Verification protocol and gates

1. **Input gate:** exact UTC calendar, source hashes, complete supported quantities,
   justified zone mapping, audited availability/capacity and all declared proxies.
2. **Formulation gate:** analytical two-zone, bottleneck, battery-loss, reservoir,
   scarcity and negative-price cases. Reject invalid/unsupported inputs. Test
   flow direction, storage bounds, cyclic closure and simultaneous cycling.
3. **Matched implementation gate:** independently build native PyPSA zonal models
   with identical inputs/equations. Compare baseline and cable/battery/combined
   interventions at 48h and 168h, then month/year. Independently replay primal
   constraints and dual/objective supports in original units. Predeclare scale-
   appropriate thresholds before trials; existing 48h gates remain unchanged.
4. **Aggregation gate:** compare selected supply/storage reductions with the
   disaggregated zonal reference, including scarcity and seasonal conditions.
   Separate reduction error from solver error and physical-to-zonal differences.
5. **Empirical gate:** predeclare zone coverage, price aggregation, calibration/
   held-out split and quantitative thresholds before fitting. Compare hourly
   price bias/MAE/correlation, spread direction/duration, fuel generation and
   correctly scoped exchanges. Existing diagnostic observations already examined
   cannot be described as untouched hold-out data. Choose a genuinely unused
   evaluation subset or disclose retrospective testing. Missing observations
   stay gaps; publish failures as well as successes.
6. **Investment/runtime gate:** matched annual pairs, credible numerical benefit
   intervals, physical feasibility and measured runtime/memory. Test multiple
   investments and interactions; speed does not establish economic accuracy.
7. **Publication/app gate:** report with charts, summary/conclusion, assumptions,
   source manifests and downloadable supported results. Test browser cancellation,
   cache invalidation, desktop/mobile and deep links; verify CI/Pages and public
   URLs before publication claims. Keep the old screening model selectable and
   distinctly labelled until a reviewed replacement is justified.

No empirical thresholds are invented by this plan. A protocol must select and
record them before validation; failing a threshold cannot trigger silent relaxation.

## Implementation milestones and next action

| ID | Deliverable | Exit evidence |
| --- | --- | --- |
| Z0 | Freeze zone scope, data inventory and validation/performance protocol | Supported/missing/proxy matrix; mapping and network-domain decisions; predeclared numerical and empirical thresholds |
| Z1 | Reproducible annual input compiler | Hashed 8,760-hour bundle; monthly energy checks; no dispatch-as-availability; source and aggregation audits |
| Z2 | Small zonal LP and independent native reference | Analytical and matched 48h/168h baseline/intervention tests; primal/dual replay |
| Z3 | Full-year engine and aggregation benchmark | Chronological annual pairs, numerical bounds, reduction errors, cold/warm runtime and memory measurements |
| Z4 | Historical validation and sensitivity report | Held-out metrics, cost/outage/capacity/terminal sensitivities and explicit failures |
| Z5 | Supported static-app integration | Verified annual report/artifacts, runtime labels, browser checks and public deployment verification |

Next action: implement Z0 as a read-only input inventory from existing source
manifests and mappings. Resolve mixed bidding-zone clusters and commercial
capacity coverage before building the annual compiler. No expensive new solve
is needed for that inventory. Review live jobs and frozen fingerprints before
research edits; preserve existing failed annual diagnostics and accepted evidence.

Open design choices to resolve through Z0: exact supported zone set; external
boundary treatment; commercial domain source/coverage; supply-block resolution;
existing reservoir boundary policy; validated 2025 fuel/outage/carbon assumptions;
numerical and empirical tolerances; reproducible performance hardware/budgets.

## Follow-up: ERA5 access and capacity coverage

On 7 October 2026, the existing ignored project CDS configuration was present
and the configured client passed an authenticated read-only access check. No
weather request/download was submitted. The earlier note about authentication
being required described new-download prerequisites, not absent workspace access.
Existing prepared annual weather remains the preferred reusable input.

For durable recovery, retain credential-free setup instructions in Git and use
a managed secret binding for `CDSAPI_KEY`, with `CDSAPI_URL` set to the documented
CDS endpoint. Never put tokens in chat, Git, publications or recovery bundles.
The existing build wrapper already supports these variables and the ignored
project configuration via `CDSAPI_RC`. File-backed access works now; persistence
across environment replacement is not established. A managed secret binding and
a fresh-environment authentication check are the recovery acceptance steps,
not a reason to copy credentials into repository files. Dataset licence acceptance
remains an account prerequisite for new retrievals.

Energy-Charts installed capacity is not Germany-only. Direct yearly queries for
DE, FR, ES, SE and PL each returned a 2025 label with `deprecated=false`. This
is a five-country sample, not verified Europe-wide technology coverage. Official
API documentation specifies yearly capacity for countries and monthly capacity
only for Germany. Figures are period-end GW; battery energy is GWh, while net
installation/decommission changes are MW. Harmonise scope, units and technology
definitions before comparison. Do not exclude non-German sources by assumption
or use German-only monthly detail as the standard for all zones.

Correction to the initial collector sample: `/installed_power` does not document
a `year` parameter. The `year=2025` request returned a series rather than a
verified year-filtered dataset. Future capacity collection must use documented
`time_step=yearly` and explicitly select/check the response's 2025 label. Preserve
the initial cached response as discovery evidence, not accepted 2025 fleet input.
Source: [Energy-Charts API](https://api.energy-charts.info/); access setup:
[CDS API instructions](https://cds.climate.copernicus.eu/how-to-api).
