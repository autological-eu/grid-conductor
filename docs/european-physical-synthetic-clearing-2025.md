# European hourly dispatch — selected model and error diagnosis

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
