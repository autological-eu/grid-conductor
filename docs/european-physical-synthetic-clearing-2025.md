# European hourly dispatch — the final fast screening model

## Summary

The model clears all **8,760 UTC hours of 2025** across **40 country/island
areas**, spanning **34 country labels**. It combines synthetic generator bids,
prepared hourly demand, physical network limits and **93 reservoirs’ precomputed
hourly output**. The annual solve-and-replay loop takes **19.17 seconds**;
preparation and water checks add **6.73 seconds**.

This is a verified numerical baseline for **fixed-hydro screening**. Reservoir
output is fixed rather than re-optimised during clearing. Market calibration,
adaptive hydro and investment-scenario acceptance remain open.

| Result | Current model |
| --- | ---: |
| Year / hourly solves | 2025 / 8760 |
| Prepared demand TWh | 3008.32 |
| Precomputed reservoir generation TWh | 311.00 |
| Norway reservoir generation TWh | 99.78 |
| Emergency supply TWh | 0.0298195 |
| Hours with emergency supply | 4 |
| Solve and network replay seconds | 19.17 |
| Preparation and water checks seconds | 6.73 |

All remaining emergency supply is in Norway. Emergency bids at €10,000/MWh
make shortages visible; these are diagnostic penalties, not observed market bids.
Runtime excludes Python imports, offline reservoir-schedule generation, separate
native verification and report production. No browser or end-to-end runtime is
claimed.

## How the model works

**Supply and demand.** The prepared PyPSA-Eur network supplies 1,151 generators
and hourly demand. Generator availability retains the original weather profiles;
wind/PV capacity follows the IRENA end-2024/end-2025 linear trajectory. This applies
61 country/technology trajectories, with missing capacity/profile coverage recorded
in the source audit. Linear commissioning is an assumption, not observed dates.
Synthetic thermal bids add €80/t operational CO2 to source marginal costs;
wind/solar bids are −€5/MWh. Demand is a prepared-network proxy, not independently
audited ENTSO-E hourly demand. Actual EUPHEMIA orders, block bids and commitment
rules are not reconstructed.

**Network.** The model retains 256 passive branches and 74 controllable links.
Countries stay separate within each original AC island. Installed-capacity
generation shift keys allocate net local injections to original buses; merging
repeated country labels would invent connectivity. Links retain original endpoints,
signed bounds and efficiencies. Passive limits use source ratings in both directions.
These are static N-0 physical limits, without observed outages, contingencies or
commercial JAO capacity domains.

**Reservoir supply.** Each reservoir’s saved electric output is an explicit fixed
hourly injection. It is not generator availability. Before clearing, the complete
schedule is checked against original inflows, discharge efficiency, spill limits,
turbine capacity, reservoir energy bounds and annual closure. It comes from an
offline chronological solve with 60 fixed inventory boundaries inherited from
the retained PyPSA-Eur reference; those inventories are model assumptions, not
observed water levels or an annual-optimum certificate.

Original demand stays intact. Where hydro exceeds local demand, residual demand
in the LP becomes negative, representing a fixed injection to be exported.
With hydro fixed, the network problems separate by hour and can reuse a solver
basis. The other **67 battery and pumped-storage units remain excluded**.

## Reservoir supply across Europe

![Current-model reservoir generation by country](../../research/fixed-reservoir-screening-2025/model-hydro.svg)

The chart aggregates the fixed schedule by country for display; clearing retains
all 40 country/island areas. Zero bars mean no reservoir output in this model,
not proof of no real-world hydro capacity. Source turbine capacities, hydrology
and geographic coverage still need observed-data validation.

## German price validation

![Current model and observed German prices](../../research/fixed-reservoir-screening-2025/model-prices.svg)

Mainland-DE prices are compared with the observed Energy-Charts/SMARD **DE-LU**
series for **8,759 jointly observed hours**. Missing observations are not
filled. The line chart shows seven-day means; the error histogram uses individual
hours. Germany and DE-LU have different geographic scope, so this is a descriptive
proxy comparison, without fitting or held-out market acceptance.

| Metric | Current model versus observed DE-LU |
| --- | ---: |
| MAE €/MWh | 23.10 |
| Bias €/MWh | -9.22 |
| RMSE €/MWh | 36.01 |

## Numerical verification

Three preselected hours are independently solved by native PyPSA with the same
fixed hydro injections, GSKs, passive network and controllable-link constraints.
They verify this model’s numerical formulation, not agreement with market prices
or an unrestricted nodal optimum.

| UTC hour | Native PyPSA objective € | Fast objective € | Absolute difference € |
| --- | ---: | ---: | ---: |
| 2025-01-15 12:00:00 | 18,482,618.03 | 18,482,618.03 | 0.000002116 |
| 2025-07-15 12:00:00 | 477,444.46 | 477,444.46 | 0.000000008 |
| 2025-12-15 12:00:00 | 8,418,111.10 | 8,418,111.10 | 0.000000041 |

All 8,760 fast solves terminated optimal after any retry. Independent network
and bound replay has maximum residual **8.38e-06 MW**;
water replay has maximum residual **2.04e-06 MWh** and checks
annual closure. Both are below the declared `1e−4` diagnostic threshold.
4 nonoptimal warm-basis solves recovered through unchanged-input cold retries;
no bounds were relaxed. Two targeted tests cover double-spent water, broken
closure and country/island injection accounting, including local hydro surplus.

The underlying chronological water schedule has separate saved-primal replay
evidence. Numerical cost agreement does not validate marginal prices or
congestion-rent valuations.

## Conclusion and limitations

The current model provides a seconds-scale, full-year physical dispatch baseline
with audited fixed reservoir supply and explicit shortage reporting. Its main
limitation is **fixed hydro**: output cannot respond to new transmission, batteries,
demand or bid costs. That restriction can materially affect marginal prices,
especially in Nordic areas. Price-based investment estimates remain unvalidated.

Future interventions would be conditional on the same schedule and need paired
verification. Adaptive hydro requires enforceable water budgets and water-value
bids, or a new chronological solve. Bidding-zone mapping, observed fleet/demand/
hydrology, commercial constraints and empirical validation remain open. This
research model has not replaced the browser scenario estimator or closed the
annual/investment acceptance gates.

## Data and reproduction

Run `tools/fixed_reservoir_screening_2025.py` in the pinned Python environment;
render this report with `tools/report_fixed_reservoir_screening_2025.py`.
The calculation uses HiGHS 1.15.1 and native PyPSA 1.2.4. Source requests, hashes,
water witnesses and retry evidence are recorded for reproducibility.

[Current-model summary, native checks and provenance](../../research/fixed-reservoir-screening-2025/summary.json),
[all 40 area summaries](../../research/fixed-reservoir-screening-2025/area-summary.csv),
[hourly German results](../../research/fixed-reservoir-screening-2025/hourly-de.csv),
and [water-schedule replay evidence](../../research/european-reservoir-clearing-2025/replay.json).
The existing machine-readable files retain supporting sensitivity-audit fields;
the report presents only the final model. Large witnesses stay in the ignored
cloud cache.
