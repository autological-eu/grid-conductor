# European hourly dispatch — selected model and error diagnosis

## Norway: source-backed water update

The updated model keeps the same resource-bid formulation and physical network,
with corrected **2025 Norwegian water inputs**. Hydro generation changes from
**107.22 to 145.54–145.73 TWh**. Against Ember,
the signed model-minus-observed difference is now **+3.95 to +4.13 TWh**;
against Elhub it is **-0.12 to +0.06 TWh**. These datasets differ in scope and
must not be treated as interchangeable targets. The update is untuned evidence,
not empirical acceptance or a certified commercial-zone model. **Norwegian price accuracy regresses in at least one observed zone. Keep this as an input diagnostic; do not promote it as an accepted baseline.**

![Norwegian hydro update and all eligible price-area errors](/research/fixed-reservoir-screening-2025/nve-water-update.png)

### What changed, and why

1. The original ERA5 Norwegian hydro profile totals **119.519 TWh** because the
   pinned PyPSA-Eur compiler substitutes the historical EIA median when its
   generation series has no 2025 entry. This is a normalization problem, not
   evidence that turbine capacity alone is inadequate.
2. Replace that normalization with [NVE's weather-driven HBV usable-inflow series](https://www.nve.no/energi/analyser-og-statistikk/hydrologiske-data-til-kraftsituasjonsrapporten/):
   **141.544 TWh** over ISO-2025 weeks, or
   **141.641 TWh** after alignment to 8,760 UTC hours.
   The separate production/stock-derived inflow column is deliberately excluded.
   Full weeks retain the original ERA5 hourly shape; partial calendar-boundary
   weeks use uniform rates over the entire source week. DST weeks have 167/169 hours.
3. Use NVE reservoir boundary stocks, linearly interpolated from adjacent weekly
   measurements: **68.550 →
   62.083 TWh** electrical-equivalent energy.
   Observed stock drawdown is explicit; no daily resets or additional water.
   Reported storage-energy capacity is **87.438 TWh**.
4. Divide electrical-equivalent reservoir inflow, capacity and stocks by original
   turbine efficiency **0.9** to obtain PyPSA's pre-dispatch stored-energy units.
   Apply that efficiency once at discharge. Run-of-river availability is electrical
   output and receives no additional efficiency conversion.
5. Retain original turbine MW and split reservoir/run-of-river water by their
   capacity shares. Country-pooled stocks and reservoir output are distributed
   over the original turbines by MW share. This is a declared allocation proxy.
6. Compute each hour's physically feasible hydro-delivery interval, holding other
   countries' schedules fixed, excluding levels that cause avoidable emergency
   production elsewhere. The envelope permits only the minimum emergency volume
   feasible that hour, with a 0.001 MW numerical allowance and an inward
   schedule margin up to 0.0001 MW. Final physics tolerances are unchanged.
   An offline linear programme penalizes spill at ten times
   the per-MWh absolute deviation from the retained seasonal pattern. Its target is scaled
   by the new water budget, not observed generation. It is **not an annual economic optimum**.
   The resulting fixed schedule then enters the same fast hourly clearing.

NVE revised its HBV history in June 2026. This is a retrospective release, not a
forecast available to operators in 2025. Gross reservoir stock and net usable
inflow are assumed to share an electrical-equivalent basis; catchment routing,
losses, cascade interactions and price-area water allocation remain unresolved.
NVE capacity is reservoir energy; original turbine MW remains unchanged. Observed
Elhub/Ember generation and ENTSO-E prices never enter the schedule or bids.

### Verification and runtime

All **8,760 clearings terminate optimal**. Separate saved-witness replay rebuilds
source coefficients and checks hourly water balance, capacity/turbine bounds,
spill, prescribed closing stocks, area/island balances, passive limits, link bounds
and objectives. Maximum water residual is **1.7e-08 MWh**;
network residual is **2.46e-06 MW**.
Native PyPSA independently checks 48 chronological water hours and three physical
market hours. Native objective differences below are formulation checks, not
price-error percentages.

| UTC hour | Objective difference EUR |
| --- | ---: |
| 2025-01-15 12:00:00 | 1.1175871e-08 |
| 2025-07-15 12:00:00 | 5.5879354e-09 |
| 2025-12-15 12:00:00 | 7.8231096e-08 |

The hourly clearing loop takes **15.51s**.
One-time source/schedule preparation takes **83.80s**,
including 65.26s for network envelopes.
The producer takes **128.15s** end to end; independent audit
and report generation are additional. Spill is **0.0000 TWh**.
Norway still has **3** modeled hours above EUR1,000/MWh.
Europe-wide emergency supply is **0.0027 MWh**
over **3 hours**, versus 0.02982 TWh over four hours
in the frozen reference. The minimum emergency volume allowed by preparation is
0.00000 TWh; clearing costs can trade off a small
shortage against costly production. Improved Norwegian energy matching does not
establish adequacy or price accuracy elsewhere.
No seconds-scale end-to-end claim is made for regenerating this schedule.

### Observed-price comparison

All 39 eligible areas with observations use the same independently replayed
ENTSO-E A44 data; four mapped areas with no price observations remain explicitly
missing in the downloadable audit.
No price fitting, held-out accuracy claim or exclusion of difficult hours. The
country-price proxy is repeated across NO1–NO5; finer geography remains necessary.

| Price area | Frozen MAE EUR/MWh | Updated MAE EUR/MWh | Updated bias EUR/MWh |
| --- | ---: | ---: | ---: |
| NO2 | 200.55 | 286.44 | -258.69 |
| NO1 | 198.03 | 281.76 | -251.65 |
| NO4 | 218.69 | 278.41 | -202.00 |
| NO5 | 196.42 | 274.77 | -240.21 |
| NO3 | 208.39 | 273.69 | -214.40 |
| DK2 | 62.03 | 55.76 | -43.13 |
| EE | 48.53 | 48.34 | 6.74 |
| SE4 | 40.80 | 45.37 | -15.72 |
| LT | 45.18 | 44.98 | 1.83 |
| LV | 45.11 | 44.94 | 1.40 |
| FI | 43.90 | 41.36 | 7.84 |
| SE2 | 42.62 | 39.67 | 28.17 |
| SE1 | 42.07 | 39.12 | 28.00 |
| SE3 | 35.79 | 38.26 | -1.53 |
| AL | 38.17 | 38.14 | -27.93 |
| BG | 33.36 | 33.30 | -16.92 |
| RO | 32.68 | 32.65 | -18.20 |
| HU | 32.30 | 32.27 | -20.15 |
| GR | 31.84 | 31.78 | -13.80 |
| MK | 31.76 | 31.72 | -17.58 |
| RS | 30.17 | 30.14 | -17.53 |
| IT-CNOR | 28.79 | 28.94 | -27.48 |
| HR | 28.94 | 28.93 | -15.30 |
| CH | 28.34 | 28.83 | -23.86 |
| IT-CSUD | 28.63 | 28.77 | -27.02 |
| IT-SUD | 28.36 | 28.49 | -25.72 |
| SI | 28.27 | 28.29 | -13.86 |
| SK | 28.31 | 28.28 | -14.62 |
| IT-North | 27.90 | 28.05 | -26.56 |
| ES | 27.17 | 26.98 | 9.89 |
| PT | 26.98 | 26.79 | 10.08 |
| PL | 26.95 | 26.78 | -15.76 |
| CZ | 25.77 | 25.83 | -8.65 |
| DK1 | 24.03 | 23.91 | -7.60 |
| AT | 23.69 | 23.86 | -15.05 |
| DE-LU | 22.70 | 22.84 | -14.46 |
| NL | 22.16 | 22.42 | -12.74 |
| BE | 21.82 | 22.03 | -12.00 |
| FR | 21.83 | 21.75 | -1.42 |

### Conclusion and reproduction

Norwegian price accuracy regresses in at least one observed zone. Keep this as an input diagnostic; do not promote it as an accepted baseline.

The historical normalization and energy-basis treatment can materially distort
Norwegian hydro. This update addresses those inputs using independent hydrology
and observed stock boundaries. Remaining energy/price discrepancies need zonal
asset mapping, metering/demand-scope reconciliation and a defensible GSK; do not
remove them by fitting generation or prices. Fixed schedules still cannot respond
to hydro investments. Paired-investment and browser-integration gates remain open.

Use the pinned interpreter for `tools/update_norway_hydro_2025.py --out <fresh-root>`,
then `tools/audit_nve_hydro_model_2025.py <fresh-root>` and
`tools/report_nve_hydro_update_2025.py <fresh-root>`. Collect the public NVE table
with `tools/collect_nve_hydrology.ts`; raw source bytes and witnesses stay ignored.

[Source hashes, numerical checks and all price metrics](/research/fixed-reservoir-screening-2025/nve-water-update.json)

## Frozen reference diagnostics

The following figures and results describe the preserved **pre-update input reference**.
They are retained for the controlled comparison above, not the updated water model.

## Summary and conclusion

We retain **one model: fixed hourly hydro injections, simple resource bids and
physical-network clearing** over all 8,760 UTC hours of 2025. The legacy and
fuel-only comparison variants have been removed from code, publication and local
checkpoints. Their small bid differences did not justify maintaining three versions.
The paused daily-storage reference remains separate; the browser still uses its
two-zone screen.

The selected model clears the year in **15.86s**
including updates and live checks, plus 6.27s common
preparation. German price MAE is **EUR22.70/MWh**.
Norway dominates the errors. Its turbine capacity is relatively close to IRENA,
but modeled hydro energy is low and the assumed grid injection pattern creates
large price sensitivity. **Changing a fixed hydro price cannot fix this model:
hydro output is injected directly, with no price-setting hydro offer.**

## Model and data

- Wind/PV offer original weather-limited volumes at EUR0/MWh. IRENA end-2024/end-2025
  linear commissioning scales fleet availability; observed commissioning is unknown.
- Gas/oil bids use hashed World Bank monthly TTF/Brent and ECB FX, efficiency,
  operational emissions and variable O&M. Coal/lignite use prepared fuel constants.
  Carbon remains an assumed EUR80/t; heating-value and delivered-oil proxies are explicit.
- Nuclear, biomass, waste, geothermal and run-of-river use prepared cost/availability
  proxies. Commitment, ramps and historical outages are unresolved; nuclear profiles
  ending in 2024 are declared proxies. Observed electricity prices do not enter bids.
- Reservoir output comes from the retained, independently replayed chronological
  water schedule. Capacity does not supply extra water. No battery/PHS dispatch is
  included. Weather availability is never replaced with realized generation.
- Forty country/AC-island areas, 256 passive branches and 74 controllable links use
  native bounds/efficiencies and PTDF/GSK constraints. These are N-0 approximations,
  not commercial zones or accepted JAO capacities. Prepared demand is still a proxy.

Identical offers merge exactly; a persistent one-thread HiGHS basis is reused for
hourly updates. There is no forecast or reservoir optimization stage. Full command,
including three native checks, component replay and witness export: 51.54s;
peak RSS 975 MiB. Historical hydro preparation, independent audit
and diagnosis/report generation are additional; loop timing is not end-to-end timing.

## Supply-curve examples

![Selected German offers and coupled prices](/research/fixed-reservoir-screening-2025/resource-bids-curves.png)

Domestic curves are illustrative: their intersection with domestic demand is not
the coupled European solution. Imports, exports and physical constraints determine
clearing. Observed DE-LU prices are comparison data, not inputs.

## Where the errors are largest

![Largest errors, Norwegian price probes and national hydro energy](/research/fixed-reservoir-screening-2025/resource-bids-errors.png)

All 39 eligible A44 observations are rehashed and independently reparsed, preserving
UTC aggregation and missingness. Four unavailable series and unresolved Italian
islands remain excluded. Norway's five observed zones share one model price, as do
other declared country proxies. Full metrics for every eligible zone are in the download.

| Observed zone | Annual MAE EUR/MWh | MAE outside modeled >1000 spikes | Absolute error from spikes |
| --- | ---: | ---: | ---: |
| NO4 | 218.69 | 59.62 | 73.3% |
| NO3 | 208.39 | 49.58 | 76.7% |
| NO2 | 200.55 | 42.85 | 79.0% |
| NO1 | 198.03 | 40.20 | 80.1% |
| NO5 | 196.42 | 38.36 | 80.8% |
| DK2 | 62.03 | 46.03 | 26.9% |
| EE | 48.53 | 48.53 | 0.0% |
| LT | 45.18 | 45.18 | 0.0% |
| LV | 45.11 | 45.11 | 0.0% |
| FI | 43.90 | 43.90 | 0.0% |
| SE2 | 42.62 | 42.62 | 0.0% |
| SE1 | 42.07 | 42.07 | 0.0% |

Removing spikes here is a **diagnostic only**; official annual errors retain them.
This is untuned descriptive evidence, not held-out empirical acceptance.

## Capacity gap or hydro energy gap?

IRENA country hydropower is compared with reservoir turbines plus run-of-river,
using parent totals once. Prepared fleet and IRENA year-end capacity have different
scopes/dates. [IRENA source capacity and provenance](/research/irena-capacity-2025/summary.json.gz)
and [Ember monthly source](https://files.ember-energy.org/public-downloads/generation/outputs/release_generation_monthly_global.csv)
are independently hashed. Ember supplies all twelve 2025 months per country. It reports national
hydro generation, including categories that are not perfectly identical to the model.

| Country | Model hydro GW | IRENA end-2025 GW | Model hydro TWh bounds | Ember hydro TWh | Model demand TWh | Ember demand TWh |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| NO | 33.18 | 34.65 | 107.22–107.25 | 141.60 | 137.04 | 134.55 |
| DK | 0.00 | 0.01 | 0.00–0.00 | 0.01 | 38.47 | 41.22 |
| EE | 0.00 | 0.01 | 0.00–0.00 | 0.01 | 7.94 | 7.84 |
| LT | 0.10 | 0.88 | 0.36–0.36 | 0.28 | 11.77 | 13.25 |
| LV | 1.54 | 1.59 | 2.82–2.82 | 2.94 | 7.20 | 7.20 |
| FI | 2.77 | 3.22 | 12.33–12.33 | 12.31 | 84.55 | 85.91 |
| SE | 14.53 | 16.30 | 60.29–60.30 | 68.42 | 129.55 | 128.38 |

Zero-cost run-of-river can merge with wind/PV. Its dispatched share is not uniquely
identified, so the table reports rigorous bounds from total merged dispatch and
individual availability; it does not invent a proportional allocation.

Norway has 33.18 GW versus
34.65 GW in IRENA—a modest capacity difference.
Fixed reservoir output is 99.78 TWh; source reservoir
inflow is 112.02 TWh of stored water-equivalent
energy, or 100.81 TWh after turbine
efficiency. Those reservoir quantities exclude run-of-river. Modeled total hydro
bounds above remain below observed generation. Extra turbine MW alone would not
close an inflow/schedule energy gap; it must be reconciled with stocks and spill.

During the 168 Norwegian price spikes, unused turbine headroom averages
22.15 GW and is never below
19.14 GW. This is power headroom, **not
proof that additional water is available**. It argues against turbine scarcity as
the sole cause. Retained model inventories are not observed NVE stocks.

## Fixed-volume and network effects

There are 168 Norwegian hours above EUR1000/MWh, 164
without emergency generation. A one-MW demand increase at these hours costs roughly
EUR10000/MWh, while the median cost saved by a one-MW demand decrease is
EUR1149.58/MWh. The asymmetric response exposes a tight volume/network boundary:
a dual price can jump despite negligible actual shortage.

The compiler's injection weights use ordinary-generator capacity and **omit reservoir
turbines**. In hydro-dominated Norway this is a material geographic approximation.
We tested the same 168 hours with Norwegian reservoir capacity included in the
injection weights, leaving turbine capacity, water, fixed output, demand, bids and
line ratings unchanged. Median Norwegian probe price is EUR121.73/MWh;
only 4 of these hours remain above EUR1000/MWh. A sampled native PyPSA
check agrees within EUR6.3329935e-08.

This isolates sensitivity to injection geometry; **it is not an accepted replacement
GSK, annual improvement claim or relaxation of physical limits**. Those weights still
aggregate a country and do not reproduce actual nodal demand, hydro injections or
commercial NO1–NO5 geography. Lower probe prices alone do not validate them.

**Would bidding-zone resolution help?** Likely, because it separates northern and
southern hydro, loads and interconnectors that a single Norwegian country price
collapses. Zone labels alone are insufficient: fixed hydro must enter at its
physical buses, demand needs a verified spatial allocation, and flexible generator
injections need defensible within-zone distribution. More zones with the same
incorrect weights can retain artificial spikes. Test audited NO1–NO5 mapping and
nodal injection placement together, then repeat native and sensitivity checks.

## Other high-error areas and next improvements

- **Eastern Denmark:** its large spikes partly accompany the Norwegian island-price
  distortion. Reconcile injection geometry and DK1/DK2 commercial boundaries first;
  national fleet totals do not establish DK2 supply.
- **Estonia/Baltics:** inspect fossil technology classification and interconnection
  assumptions. Ember records about 1.983 TWh of Estonian other-fossil generation;
  the prepared fleet has a 0.251 GW oil category priced as Brent fuel and no explicit
  oil-shale strategy. That is a classification/cost concern, not proof of missing
  capacity. Baltic topology/outages and demand need independent reconciliation.
- **Finland/Sweden:** hydro energy and country-versus-zone aggregation remain relevant;
  their fleet/energy comparisons above identify input priorities without price fitting.

Priority: correct nodal/zonal demand and hydro injection representation, then audit
Norwegian water energy against monthly Ember and observed NVE stock changes. Keep
original chronology, efficiency, stocks and spill; do not simply scale fixed output
to observed generation. If hydro offers are introduced, use explicit water-value
bids and available turbine/water volumes with carried stocks. Price tuning alone
cannot change an injection-only schedule. The daily-storage reference remains paused.

## Numerical checks and provenance

All 8760 selected hours terminate optimal. Saved-primal replay independently checks
bounds, area/island balances and passive flows outside the producer matrix. Water
residual 2.04e-06 MWh and network residual
4.7e-06 MW pass 1e-4; closure remains unchanged.
Emergency supply is 0.0298195 TWh in four hours.

| UTC hour | Native PyPSA minus fast objective EUR |
| --- | ---: |
| 2025-01-15 12:00:00 | 5.5879354e-08 |
| 2025-07-15 12:00:00 | 2.7939677e-09 |
| 2025-12-15 12:00:00 | 1.3969839e-08 |

Native parity verifies the formulation. Empirical thresholds/held-out periods,
paired investments, adaptive storage and supported browser integration remain open.

[Selected results, all-zone errors, capacity/energy sources, price probes and replay](/research/fixed-reservoir-screening-2025/resource-bids.json)

[Retained hydro source metadata](/research/fixed-reservoir-screening-2025/summary.json.gz)
· [water replay](/research/european-reservoir-clearing-2025/replay.json).

Reproduce with tools/hybrid_fixed_hydro_2025.py in a fresh output root, then --audit;
run tools/diagnose_fixed_hydro_errors_2025.py --run ROOT --out ROOT/diagnostics.json,
and tools/evaluate_fixed_hydro_bids_2025.py --run ROOT --diagnostics ROOT/diagnostics.json.
Use pinned Python and verified ignored provider/source/water caches. Raw observations
and annual witnesses stay outside Git. Only this model is maintained for this report.
