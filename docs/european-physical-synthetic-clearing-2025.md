# European hourly dispatch — whole-network bidding-zone model

## Summary and conclusion

The model now uses **48 distinct clearing areas across the entire
retained European network**, including NO1–NO5, SE1–SE4, DK1/DK2 and Italy's seven
zones. DE and LU share DE-LU; Ireland/Northern Ireland share the Single Electricity
Market. Mallorca joins ES. Separate peripheral source areas such as Corsica and
Kosovo are retained and explicitly lack observed-price verification; they are not
claims of SDAC participation or certified commercial boundaries.

**13 old clusters crossed zone boundaries.** Rebuilding them
from source bus membership, rather than assigning a centroid, increases the grid
to **145 buses**. The audit also identified **3
crossings lost at the earlier stub-removal stage**; the new backbone starts before
that removal. Original uniform security factor **0.7** remains.

All 8,760 zonal hours terminate optimal. Annual zonal clearing takes **33.48s**, excluding one-time
preparation, native checks, replay, export and reporting. Emergency generation is
**0.000000 MWh** over 0 solved hours. The model is
an untuned diagnostic, not an accepted market-price or investment estimator.

The comparison below isolates country versus bidding-zone pooling on **the same
rebuilt grid**. It is not directly attributable to the geography change alone when
compared with the earlier 128-bus report: topology and branch aggregation also changed.
All original hourly parent demand, available supply and fixed reservoir output are
conserved. We have not fitted supply, demand or water to ENTSO-E prices.

Country-control failures: **2025-12-11T08:00:00 UTC: Infeasible**. A fresh solver reproduced the
reported termination. Its comparisons use common solved hours; the zonal model
still covers the full year. Country pooling restricts spatial dispatch through
its GSK and can fail where finer zonal decisions find a feasible allocation.

## Geographic and physical formulation

1. Retrieve and hash pinned [Electricity Maps geographic areas](https://github.com/electricitymaps/electricitymaps-contrib/tree/master/geo),
   [NVE's official Norwegian price-area polygons](https://gis3.nve.no/map/rest/services/Mapservices/Omradekonsesjoner/MapServer/0)
   and [entsoe-py's Italian zones](https://github.com/EnergieID/entsoe-py/tree/master/entsoe/geo/geojson), including Calabria.
   These are retrospective releases; historical 2025 boundary certification is open.
2. Map original onshore buses to polygons. Uncontained coastal points use a bounded
   nearest-polygon proxy, explicitly recorded. Offshore nodes use an electrical
   path to a same-country shore connection, not a cluster-centroid assignment.
3. Apply pinned upstream voltage-layer, converter and DC-chain routines. Do not
   remove country-only stubs. Split each old cluster by actual member zone BEFORE
   branch aggregation, preserving cross-zone branches and native HVDC bounds/losses.
4. Maintain **one clearing balance and price per modeled market area**, including
   areas spanning AC islands. Physical island balances remain separate. Capacity
   GSK fractions distribute generation; actual fixed hydro and demand enter at
   their allocated physical buses. Native PTDFs retain constraints inside zones;
   membership in a common zone does not create an unconstrained inter-island link.
5. Check source-reconstructed demand, offers, hydro and saved-primal physics.
   Compare against native PyPSA formulations and report every failed hour.

This is a synthetic zonal dispatch model with model-derived N-0 constraints,
not EUPHEMIA's full order allocation, published JAO commercial domains, outages,
contingencies or operator redispatch. Static generation shift keys remain a proxy
for intrazonal dispatch. Native parity verifies the formulation, not market realism.

## Conserved supply, demand and water inputs

Original generator cost and weather-availability time series remain unchanged.
For a mixed cluster, sourced dated plant-capacity shares allocate thermal and
reservoir assets between child areas. Missing or unsupported location detail,
including aggregate renewable profiles, uses explicit raw-member-count shares.
These are allocation assumptions, not newly measured bidding-zone capacity or
weather. Allocation methods across original generators/reservoirs: **{'pure_cluster': 1146, 'source_plant_capacity': 51, 'source_member_count_proxy': 87}**.
Commissioning/out-of-service dates filter the plant-location weights where known.

Demand uses the existing preclustered 2025 hourly series, with member-count splits
where its earlier spatial aggregation crossed a boundary. Each original parent's
hourly load remains exactly conserved. This does not turn inherited source demand
into independently audited observed zonal load. The Norwegian 137.04 versus
131.52/134.55 TWh scope discrepancy remains unresolved; no scaling forces agreement.

Fixed reservoir schedules split by the same source shares, preserving each parent's
hourly output, inflow/efficiency, inventory trajectory and terminal boundaries.
No rescheduling, new water, spill or dispatch-for-availability substitution occurs.
Newly separate areas receive the existing EUR10,000 emergency-offer rule where
needed (9 additional diagnostic offers); those MW are never
reported as real fleet capacity. Shortage energy is disclosed separately.

### Resource bids and source-backed hydro

Simple resource offers retain sourced monthly gas/oil prices (World Bank TTF/Brent
and ECB FX) and the existing carbon/efficiency assumptions. Observed electricity
prices do not enter bid construction. The pinned PyPSA-Eur v2026.08.0 backbone
uses retained 2025 weather profiles and source/replay coefficients. IRENA linear
end-2024/end-2025 wind/solar capacity interpolation is assumed commissioning,
not observed installation dates. Nuclear availability ending in 2024 is a proxy.

Norway uses [NVE's weather-driven HBV usable inflow](https://www.nve.no/energi/analyser-og-statistikk/hydrologiske-data-til-kraftsituasjonsrapporten/),
**141.641 TWh** aligned to 8,760 UTC hours. Full weeks
preserve the original ERA5 hourly shape; partial boundary weeks use uniform rates
over their source week. DST weeks retain 167/169 hours. The generation/stock-derived
inflow column is excluded. Observed generation does not set the water budget.

Electrical-equivalent opening/closing stocks are
**68.550 → 62.083 TWh**,
with **87.438 TWh** reservoir capacity.
Water, stocks and capacity are converted to stored units by dividing by original
turbine efficiency 0.9; efficiency is applied once on discharge. Original turbine
MW remains unchanged. A shortage-aware delivery envelope and seasonal-pattern
penalty prepare the fixed schedule, not an annual economic optimum. Other countries
retain their source schedules. No daily reset or additional water is introduced.

HBV history was revised in June 2026, so inputs are retrospective. Gross reservoir
stock/net usable inflow are assumed compatible electrical equivalents; catchment
routing, cascades, country-pooled reservoir/run-of-river shares and regional water
allocation remain unresolved. Fixed Norwegian reservoir output remains 139.215 TWh;
total hydro including dispatched run-of-river may change with network constraints.
Previous-model total-generation bounds are not reused for this new model.


## Full-year price comparison

![Controlled full-year errors and separate Norwegian modeled prices](/research/fixed-reservoir-screening-2025/bidding-zone-errors.png)

All 41 eligible observed areas use hashed and XML-reparsed ENTSO-E
A44 observations, UTC-aligned hourly. Country and zonal MAE below use common
available hours; downloads also contain all available zonal-hour metrics.
Missing model observations: **BA, IT-CALA, ME, XK, FR-COR, GB, IE-SEM**. Observations never enter offers.
This is descriptive full-year evidence, not a declared held-out acceptance test.

| Observed area | Common hours | Country-pool MAE | Zonal MAE | Zonal bias | Correlation |
| --- | ---: | ---: | ---: | ---: | ---: |
| DK2 | 8759 | 33.39 | 50.43 | -37.97 | 0.303 |
| EE | 8759 | 48.34 | 48.38 | +7.55 | 0.426 |
| NO5 | 8759 | 45.56 | 46.63 | -22.13 | -0.133 |
| LT | 8759 | 44.85 | 44.89 | +2.63 | 0.454 |
| LV | 8759 | 44.83 | 44.86 | +2.21 | 0.447 |
| NO1 | 8759 | 52.66 | 42.86 | -21.16 | 0.037 |
| FI | 8759 | 42.12 | 41.72 | +1.19 | 0.112 |
| NO2 | 8759 | 57.43 | 41.60 | -19.69 | 0.166 |
| SE4 | 8759 | 42.67 | 41.01 | -15.94 | 0.263 |
| IT-SARD | 8759 | 29.87 | 38.41 | -36.78 | 0.615 |
| AL | 8759 | 36.88 | 37.16 | -25.91 | 0.486 |
| SE2 | 8759 | 37.67 | 36.32 | +24.65 | 0.047 |
| NO4 | 8759 | 48.83 | 35.87 | +27.54 | 0.007 |
| SE1 | 8759 | 37.14 | 35.84 | +23.81 | 0.044 |
| IT-SICI | 8759 | 30.39 | 35.18 | -33.54 | 0.636 |
| NO3 | 8759 | 43.89 | 35.02 | +10.23 | 0.016 |
| SE3 | 8759 | 35.63 | 34.86 | -2.98 | 0.222 |
| IT-CSUD | 8759 | 29.32 | 33.70 | -32.46 | 0.644 |
| BG | 8759 | 32.47 | 32.75 | -14.79 | 0.614 |
| IT-SUD | 8759 | 28.82 | 32.72 | -31.16 | 0.659 |
| GR | 8759 | 31.75 | 32.12 | -12.39 | 0.588 |
| RO | 8759 | 31.69 | 31.95 | -15.96 | 0.630 |
| HU | 8759 | 31.05 | 31.32 | -17.15 | 0.668 |
| IT-CNOR | 8759 | 29.54 | 31.27 | -30.06 | 0.670 |
| MK | 8759 | 30.58 | 30.80 | -15.03 | 0.633 |
| RS | 8759 | 29.02 | 29.35 | -15.33 | 0.632 |
| HR | 8759 | 27.92 | 28.27 | -12.90 | 0.661 |
| SI | 8759 | 27.41 | 27.80 | -11.67 | 0.635 |
| CH | 8759 | 27.00 | 27.59 | -21.66 | 0.762 |
| SK | 8759 | 27.35 | 27.57 | -11.12 | 0.698 |
| CZ | 8759 | 27.14 | 27.30 | -0.30 | 0.570 |
| DK1 | 8759 | 31.89 | 26.57 | -14.02 | 0.690 |
| ES | 8759 | 26.51 | 26.55 | +8.78 | 0.708 |
| PT | 8759 | 26.28 | 26.32 | +9.03 | 0.695 |
| PL | 8759 | 26.13 | 26.09 | -14.91 | 0.669 |
| IT-North | 8759 | 28.65 | 25.40 | -23.37 | 0.714 |
| BE | 8759 | 24.16 | 24.31 | -15.27 | 0.784 |
| DE-LU | 8759 | 23.09 | 23.10 | -15.25 | 0.776 |
| NL | 8759 | 23.10 | 23.09 | -14.94 | 0.775 |
| FR | 8759 | 22.82 | 22.74 | -4.91 | 0.766 |
| AT | 8759 | 22.49 | 22.60 | -12.37 | 0.781 |

Errors are EUR/MWh. Separate zone prices do not guarantee better MAE: inherited
capacity, demand, intrazonal GSK and fixed hydro schedules may still be wrong.
The download includes all metrics, shortage counts and failure/retry records.
Failed zonal hours: **None**. No failed hour is filled with another model's price.

## Numerical verification and measured runtime

Independent saved replay rebuilds sources and checks parent-level supply conservation,
hourly demand/hydro conservation, generator/link bounds, zonal and physical-island
balances, native passive flows and objectives. Maximum changes after allocation:
available supply **1.82e-12 MW**,
demand **0 MW**, fixed hydro
**5.82e-11 MW**. Replay tolerance remains 0.0001.
Country optimal hours: **8759**; zonal: **8760**.

| Native formulation | Hour index | Native minus fast objective EUR |
| --- | ---: | ---: |
| country | 348 | 7.45e-09 |
| country | 4692 | 5.59e-09 |
| country | 8364 | 5.49e-08 |
| bidding_zone | 348 | 7.82e-08 |
| bidding_zone | 4692 | -7.92e-09 |
| bidding_zone | 8364 | -1.1e-07 |

Three targeted fixtures verify boundary assignment/rejection, constrained cross-zone
prices and native parity, and common-zone clearing across AC islands with HVDC
losses. The latter rejects fictitious free energy transfer. Source allocation and
physical replay are required independently of objective agreement.

One-time preparation **123.54s**; country clearing
**33.08s**; zonal clearing **33.48s**;
complete producer with both controls/native checks/export **418.11s**;
peak RSS **2584 MiB**. Independent audit and publishing are additional.
No seconds-scale end-to-end claim is made for rebuilding source inputs.

## Wind and thermal-input sensitivity — 13 October 2026

**Conclusion:** gas and carbon assumptions influence modeled price levels; oil
has no material price effect within the tested range. Uniform wind scaling does
not resolve the Nordic timing errors. Independent wind-source comparisons reveal
large regional inconsistencies, making dated fleet geography and weather profiles
a stronger next priority than an oil-price data upgrade. No perturbation is adopted.

The design was fixed before clearing: each input independently +/-10%, an unchanged
control, and one combined +10% case. Hydro schedules/water, prepared demand,
installed capacity, GSK weights, network topology/ratings and non-target inputs
remain unchanged. Wind **availability**, not installed MW, is scaled and capped
at existing capacity; solar stays unchanged. Gas/oil thermal-input components and
carbon costs are divided by original plant efficiency, with no double counting.
Carbon tests use EUR72/t and EUR88/t around the existing EUR80/t assumption.
These are **sensitivities**, not verified source corrections, causal percentages
of error, recovered operator bids or a held-out calibration exercise.

All ten cases attempt all 8760 hours. Eight solve the complete year; gas +10%
retains one unresolved Not Set hour (4028), carbon +10% another (4609), after fresh
solver retries. Cost-only changes cannot establish new physical infeasibility of
the unchanged feasible formulation. No prices are filled from another case.
All rankings below use the **same 8758 hours and 41 observed zones**.
Values are equal-zone averages, not demand-weighted; r is the arithmetic mean of
zonal correlations, not one pooled Europe correlation.

| Test | Mean absolute price response | Price MAE | Change in MAE | Mean zonal r | NO+SE MAE |
| --- | ---: | ---: | ---: | ---: | ---: |
| Control | 0.00 | 33.23 | +0.00 | 0.5017 | 38.89 |
| Wind availability -10% | 2.61 | 33.70 | +0.47 | 0.4926 | 41.20 |
| Wind availability +10% | 1.60 | 33.30 | +0.07 | 0.5018 | 38.25 |
| Gas -10% | 3.78 | 34.56 | +1.33 | 0.5063 | 37.90 |
| Gas +10% | 3.56 | 32.48 | -0.75 | 0.4974 | 39.80 |
| Oil -10% | 0.00 | 33.23 | +0.00 | 0.5017 | 38.89 |
| Oil +10% | 0.00 | 33.23 | +0.00 | 0.5017 | 38.89 |
| Carbon -10% | 2.55 | 34.02 | +0.80 | 0.4987 | 37.99 |
| Carbon +10% | 2.43 | 32.67 | -0.55 | 0.5043 | 39.75 |
| All four +10% | 6.69 | 32.23 | -0.99 | 0.5002 | 39.99 |

Price/error units are EUR/MWh. Oil has zero area-hours with a price response
above 1e-4 EUR/MWh; this does not establish irrelevance beyond +/-10% or in other
market conditions. Gas +10% improves aggregate MAE by EUR0.75/MWh but worsens
mean zonal correlation and Nordic MAE. Carbon +10% improves aggregate MAE by
EUR0.55/MWh while worsening Nordic MAE. These can offset other model errors;
observed-price fit does not prove that historical fuel/carbon quotes were too low.

For NO1–NO5 and SE1–SE4, mean zonal correlation is 0.0744 in the control and
0.0780 with wind +10%; gas +10% gives 0.0767. No tested adjustment solves the
Nordic timing problem. The combined positive case produces a mean absolute
nonadditive price response of **EUR0.751/MWh**
(maximum EUR140.25/MWh). Individual
responses therefore cannot be summed into causal shares of the observed error.

### Independent Norwegian wind comparison

The control's weather-limited availability is compared with hashed Elhub hourly
named wind generation, not substituted by it. The NVE inventory column is the
cached **current** fleet pilot; it is not certified historical 2025 capacity.
Technology, offshore/grid-connection and metering scope require reconciliation.

| Area | Model wind MW | Current NVE wind MW | Model available TWh | Elhub generated TWh | Availability/generation shape r |
| --- | ---: | ---: | ---: | ---: | ---: |
| NO1 | 343.8 | 384.7 | 0.433 | 1.172873 | 0.747 |
| NO2 | 1327.9 | 1427.0 | 2.601 | 4.060274 | 0.785 |
| NO3 | 915.8 | 2107.8 | 1.663 | 5.520565 | 0.728 |
| NO4 | 1600.9 | 1159.2 | 3.111 | 3.121915 | 0.748 |
| NO5 | 966.0 | 0.0 | 1.899 | 0.000005 | Too little observed wind |

Modeled national wind availability is **9.708 TWh**, while named metered wind
production totals **13.876 TWh**. NO3 reports generation above modeled availability
in **8172 hours** by more than 1 MWh/h. NO5 has about **966 modeled MW** but zero
farms in the current NVE inventory and negligible named metered generation.
These are strong inconsistency flags, not a proof that all differences are missing
capacity: plant coverage, curtailment, weather conversion, offshore classification
and dates matter. Generation below availability is expected under curtailment.
This experiment scales volumes; it does **not** correct geographical allocation,
GSK weights or hourly weather shape, and cannot measure their causal error shares.

### Verification, runtime and next action

Fresh control prices and objectives reproduce annual-v7 exactly. Independent
coefficient reconstruction and component-physics replay pass for every valid
case/hour; maximum network residual is 2.59e-5 MW, below the unchanged 1e-4
guard, and maximum objective replay error is 3.36e-8 EUR. All 41 price sources
are rehashed/XML-reparsed. No case uses emergency generation on its valid hours.
Six isolation/units/cap fixtures pass. Fixed water and baseline source chains
are preserved; native PyPSA objective matching is not the empirical target.

Per-case clearing loops take **26.16–53.64s** for an attempted year. Shared
preparation is **88.05s**; the ten-case producer including
compilation, hashing and saved-witness exports takes **516.75s**,
peak RSS **2584 MiB**. Independent replay/evaluation adds
**624.91s**; it is not included in clearing-loop claims.

Reproduce with pinned Python: `tools/run_input_sensitivity_2025.py <fresh-root>`,
then `tools/audit_input_sensitivity_2025.py <root>`. Current ignored evidence:
`data/bidding-zone-network-2025/input-sensitivity-v1/` (predeclared design, source
hashes, saved primals, failed-hour records and all 41-zone comparisons). No new
baseline, browser engine, public data mirror or annual optimisation claim follows.

**Next priority:** verify dated Norwegian wind-farm commissioning, capacity,
bidding-zone and grid-connection scope; correct regional allocation and rebuild
site-weighted weather profiles without using dispatch as availability. Validate
with independent generation and held-out price periods. Gas heating-value and
plant-efficiency compatibility plus sourced daily gas/EUA are secondary priorities.
Retain adverse regional outcomes; no blanket fuel uplift or wind rescaling is
justified by these sensitivities. Oil refinement has low priority within this model.

## Dated Norwegian wind-geography test — 13 October 2026

**Retain the baseline: source geography improves, but observed-price accuracy does not.**
A fresh candidate relocates Norwegian **onshore** wind using dated NVE turbine
batches. It solves all 8760 hours with zero emergency supply. Across all 41
eligible observed areas, equal-zone mean MAE changes from **EUR33.226 to
EUR33.260/MWh**; arithmetic mean zonal correlation changes from **0.50171 to
0.50106**. These are descriptive, untuned comparisons on already-inspected
2025 observations, not held-out acceptance or causal error attribution.

### What changes, and what remains conditional

The [NVE operating-farm registry](https://api.nve.no/web/WindPowerplant/GetWindPowerPlantsInOperation)
was retrieved on 10 October 2026. All 65 returned farm records have dated turbine
batches; no duplicate batch IDs, missing commissioning dates or recorded 2025
capacity events were found. Include each batch from commissioning until retirement
(exclusive), multiplying turbine count by rated kW. The resulting dated fleet is
5082.375 MW. This differs from a current installed-MW snapshot: retirement dates
matter. The current-operating endpoint can omit previously retired farms, so this
is not proof of complete historical 2025 capacity coverage.

Registry MW determine **zone shares**, not a replacement national capacity total.
Keep the existing 5016.4 MW onshore source normalization and its inherited IRENA
hourly trajectory. Preserve national hourly available MW exactly; apply the same
national wind curve to every destination zone, then distribute within each zone
using existing bus-capacity weights. Recompute physical GSKs from the relocated
nameplates. Thus this tests spatial redistribution with a common weather proxy;
it does not independently identify capacity-location, regional timing and GSK
contributions. Site-specific weather and intra-zone grid connections remain unresolved.
Non-Norwegian generators, Norwegian offshore wind, hydro schedules, demand,
fuel bids, grid topology and ratings remain unchanged.

| Zone | Dated registry MW | Source normalization before MW | After MW | Available before TWh | After TWh |
| --- | ---: | ---: | ---: | ---: | ---: |
| NO1 | 384.7 | 343.8 | 379.7 | 0.433 | 0.693 |
| NO2 | 1430.6 | 1258.9 | 1412.1 | 2.327 | 2.578 |
| NO3 | 2107.8 | 897.6 | 2080.4 | 1.590 | 3.798 |
| NO4 | 1159.3 | 1600.9 | 1144.2 | 3.111 | 2.089 |
| NO5 | 0.0 | 915.2 | 0.0 | 1.698 | 0.000 |

The table covers onshore wind only; its national available energy remains
**9.159 TWh**. The earlier 9.708 TWh wind comparison includes offshore supply.
Removing onshore wind from NO5 therefore does **not** remove its remaining
approximately 51 MW / 0.202 TWh modeled offshore allocation, whose market/grid
connection scope still needs reconciliation. Source normalization is not certified
2025 end-year nameplate capacity: the inherited IRENA trajectory is encoded in
availability and can exceed 1 relative to that older normalization. No clipping,
second IRENA scaling, observed-generation substitution or generation-target fitting
is applied. Redistribution cannot repair the national available-energy shortfall.

### Full-year observed-price comparison

All rows use the same 8760 valid hours and source-verified A44 observations.
MAE is EUR/MWh; correlation is Pearson r. Bias, RMSE, tail errors and seasonal
comparisons for every area are retained in the ignored audit witness.

| Area | Baseline MAE | Candidate MAE | Baseline r | Candidate r |
| --- | ---: | ---: | ---: | ---: |
| AL | 37.16 | 37.16 | 0.486 | 0.486 |
| AT | 22.60 | 22.60 | 0.781 | 0.781 |
| BE | 24.31 | 24.32 | 0.784 | 0.784 |
| BG | 32.74 | 32.74 | 0.614 | 0.614 |
| CH | 27.59 | 27.59 | 0.762 | 0.762 |
| CZ | 27.30 | 27.30 | 0.570 | 0.570 |
| DE-LU | 23.10 | 23.09 | 0.776 | 0.776 |
| DK1 | 26.57 | 26.59 | 0.690 | 0.690 |
| DK2 | 50.43 | 50.31 | 0.303 | 0.305 |
| EE | 48.38 | 48.38 | 0.426 | 0.426 |
| ES | 26.55 | 26.55 | 0.708 | 0.708 |
| FI | 41.72 | 41.77 | 0.112 | 0.113 |
| FR | 22.74 | 22.74 | 0.766 | 0.766 |
| GR | 32.12 | 32.12 | 0.588 | 0.588 |
| HR | 28.27 | 28.27 | 0.661 | 0.661 |
| HU | 31.32 | 31.32 | 0.668 | 0.668 |
| IT-CNOR | 31.27 | 31.27 | 0.670 | 0.670 |
| IT-CSUD | 33.70 | 33.70 | 0.644 | 0.644 |
| IT-North | 25.40 | 25.41 | 0.714 | 0.714 |
| IT-SARD | 38.41 | 38.39 | 0.615 | 0.615 |
| IT-SICI | 35.18 | 35.18 | 0.636 | 0.636 |
| IT-SUD | 32.73 | 32.73 | 0.659 | 0.659 |
| LT | 44.89 | 44.89 | 0.454 | 0.454 |
| LV | 44.86 | 44.86 | 0.447 | 0.447 |
| MK | 30.79 | 30.79 | 0.633 | 0.633 |
| NL | 23.09 | 23.09 | 0.775 | 0.775 |
| NO1 | 42.86 | 43.42 | 0.037 | 0.025 |
| NO2 | 41.60 | 42.79 | 0.166 | 0.139 |
| NO3 | 35.02 | 35.10 | 0.016 | 0.016 |
| NO4 | 35.86 | 36.22 | 0.007 | 0.007 |
| NO5 | 46.63 | 45.47 | -0.133 | -0.122 |
| PL | 26.09 | 26.09 | 0.669 | 0.669 |
| PT | 26.32 | 26.32 | 0.695 | 0.695 |
| RO | 31.95 | 31.95 | 0.630 | 0.630 |
| RS | 29.34 | 29.34 | 0.632 | 0.632 |
| SE1 | 35.84 | 35.94 | 0.044 | 0.044 |
| SE2 | 36.31 | 36.43 | 0.047 | 0.047 |
| SE3 | 34.85 | 34.97 | 0.222 | 0.221 |
| SE4 | 41.01 | 41.07 | 0.263 | 0.262 |
| SI | 27.80 | 27.80 | 0.635 | 0.635 |
| SK | 27.57 | 27.57 | 0.698 | 0.698 |

NO5 improves modestly while NO1/NO2/NO4 worsen. NO3 stays near zero correlation
although its available energy more than doubles. Winter NO3 MAE remains around
EUR58.6/MWh; seasonal timing errors are not repaired by source-backed shares alone.
Keep adverse results; do not tune a wind multiplier to offset hydro or demand errors.

Independent replay checks every dated share, unchanged non-target availability,
demand/fixed hydro/costs/grid, each hourly national volume, individual capacity
allocation, and saved native-component balances/flows/bounds. Maximum network
residual is **2.89e-06 MW**, below the unchanged 1e-4 guard;
objective replay error is **2.24e-08 EUR**. Maximum national
hourly wind change is 9.09e-13 MW. All 41 eligible observed
price areas are rehashed and XML-reparsed. Five targeted calendar/expansion/
retirement/missing-date/duplicate tests pass. These checks establish the feasibility
of this conditional diagnostic, not empirical acceptance or investment readiness.

Clearing loop: **73.93s**; source/grid preparation: **196.06s**;
complete producer/export: **272.72s**, peak RSS **2582 MiB**.
Independent replay/evaluation adds **284.75s**. Daily orchestration groups
independent hourly clears; no adaptive hydro or joint daily storage optimisation.

Reproduce with the pinned interpreter: `tools/run_norway_wind_geography_2025.py
<fresh-root>`, then `tools/audit_norway_wind_geography_2025.py <root>`.
Evidence stays in `data/bidding-zone-network-2025/norway-wind-geography-v1/`:
predeclared design, source/dependency hashes, complete saved primals and full
41-area/seasonal comparison. The retained annual-v7 baseline is unchanged.

### Site/weather correction: source inventory and remaining work

The fresh [NVE operating-site GIS service](https://kart.nve.no/enterprise/rest/services/Vindkraft2/MapServer/0)
matches 62 of 65 registry farms, representing 5054.725 MW of the current installed
snapshot, across 61 distinct site IDs. Raggovidda and Raggovidda 2 share a GIS point;
keep separate turbine batches without double counting their capacity. Lindesnes,
Nye Sandøy and Valsneset (24.05 MW current total) have no ID match and remain
explicitly unresolved. GIS site points are not individual turbine coordinates.
Raw bytes, retrieval receipts and joins stay ignored in
`data/bidding-zone-source-audit-2025/nve-wind-sites-v1/`;
`tools/collect_nve_wind_locations_2025.py <fresh-root>` reproduces collection.

A separate processed ERA5 cache, `data/pypsa-eur/monthly-weather/europe-2025-compact.nc`,
contains all 8760 hours of gridded wind conversions, with an annual hash receipt.
The runoff cutout and sparse node-weather pilot are insufficient by themselves,
but this converted cache is a possible reusable weather input. Its existing
Vestas V112 and offshore generic turbine assumptions are not certified matches to
NVE turbine models/hub heights. Presence of the file is not a completed site-profile audit.

**Next:** reconcile the three unmatched farms and historical/offshore market
coverage; verify farm-to-grid connections and the converted-cache receipt/calendar;
construct capacity-weighted site profiles with explicit turbine/height and weather
resolution limitations. Preserve the national IRENA trajectory or document a
source-backed reconciliation before changing totals. Compare availability with
Elhub generation without substituting it, then evaluate a fresh full-year candidate
with source/component replay and predeclared validation. No browser replacement,
new accepted baseline, public bulk-data mirror or recurring-review restart follows.

## Regional-water candidate evaluation — 13 October 2026

**Decision: retain the complete baseline; reject this candidate as a replacement.**
The fresh candidate uses NO1–NO5 HBV inflow, regional reservoir capacity and
observed opening/closing stocks. Turbine locations/MW, bids, demand, weather
availability outside Norwegian run-of-river, non-Norwegian reservoir schedules
and the physical grid remain unchanged. Reservoir/run-of-river inflow is split
by regional turbine MW, still a proxy. A water-only L1 adjustment preserves the
baseline seasonal output pattern as far as feasible; it is not price fitting.
Within-week inflow keeps the national weather shape. Regional pools do not
resolve catchment routing/cascades or guarantee realistic intermediate stocks.
Electrical-equivalent stocks/flows correspond to stored units divided by 0.9,
with turbine efficiency applied once. No daily inventory reset occurs.

The producer attempted all 365 UTC days / 8760 hourly clears, but only
**7496 hours** were valid. There were **1152 fresh-solver-confirmed
infeasible hours** and **112 unresolved Not Set/Unknown hours**. Failed prices
remain missing. This is not a complete feasible annual benchmark. June accounts
for 519 failures, May 245 and July 184; spring/summer delivery is a priority.
Emergency generation on solved hours totals **47.521 GWh**.
Prepared annual reservoir output is 139.881 TWh versus the baseline schedule's
139.215 TWh (about 0.48% higher); this is scheduled output, not a verified
delivered full-year generation total for a run with missing hours.

Across all 41 observed zones, equal-weight mean MAE on the **same 7496 hours**
rises from **EUR32.83 to EUR71.57/MWh**. The baseline's full-year mean MAE
is EUR33.23/MWh; it is not the matched-hour comparator. Missing hours can bias
these descriptive comparisons. No parameters were fitted; previously inspected
2025 observations do not constitute an untouched held-out test.

| Zone | Baseline MAE | Candidate MAE | Baseline correlation | Candidate correlation |
| --- | ---: | ---: | ---: | ---: |
| DE-LU | 22.14 | 22.07 | 0.800 | 0.800 |
| DK2 | 46.91 | 47.02 | 0.343 | 0.333 |
| FI | 43.81 | 43.10 | 0.093 | 0.085 |
| NO1 | 38.50 | 154.93 | 0.055 | 0.050 |
| NO2 | 37.09 | 43.05 | 0.219 | 0.088 |
| NO3 | 37.11 | 432.61 | -0.025 | 0.027 |
| NO4 | 40.36 | 764.54 | -0.031 | 0.015 |
| NO5 | 43.80 | 330.04 | -0.163 | 0.048 |
| SE1 | 39.78 | 57.45 | 0.006 | 0.009 |
| SE2 | 40.19 | 80.04 | 0.018 | -0.009 |
| SE3 | 35.64 | 36.00 | 0.224 | 0.133 |
| SE4 | 39.74 | 43.08 | 0.288 | 0.112 |

MAE units are EUR/MWh. Some sign changes in correlations occur close to zero;
they do not establish predictive skill. Large adverse Norwegian price tails
remain: NO4 reaches about -EUR180938/MWh. These are conditional marginal values
under fixed injections and GSK/physical constraints, not plausible reconstructed
market bids. Do not clip them to manufacture agreement. Regional water data
alone does not repair fixed-schedule deliverability or commercial price formation.

Clearing/retry loop: **158.848s**; grid/source/water preparation: **119.424s**;
complete producer/export: **306.342s**, peak RSS **2583 MiB**. Daily orchestration
contains independent hourly clears with precomputed hydro, not a joint daily
adaptive-storage auction. The initial driver stopped at an Optimal-labelled
solution failing the unchanged 1e-4 primal guard. A fresh driver/root retried
invalid hours and retained failures without relaxing tolerances.

Independent saved-source/water/native-component replay passes for the **7496
valid hours**, not for failed hours. Maximum electrical water-balance residual
is 3.76e-8 MWh (stored basis 4.19e-8); network residual 6.30e-5 MW stays below
the unchanged 1e-4 guard. Objective replay error is 2.98e-8 EUR; non-Norwegian
fixed output changes by exactly zero. All 41 eligible price series were rehashed
and XML-reparsed. This validates the saved feasible subset, not annual feasibility
or price realism. Six targeted water/calendar/guard tests pass. Native PyPSA
objective matching was not used as the acceptance target.

Reproduce using the pinned Python interpreter:
`tools/run_regional_water_candidate_2025.py <fresh-root>`, then
`tools/audit_regional_water_candidate_2025.py <root>`.
The current ignored witness is `data/bidding-zone-network-2025/regional-water-v2/`;
source/allocation manifests, water arrays, all 41 zone comparisons and failed-hour
records stay there. No browser integration or baseline promotion follows.

**Next:** diagnose binding constraints and physical/GSK price sensitivities on
failed/extreme hours; reconcile regional reservoir/run-of-river routing and load
scope. Then test network-aware bounded daily hydro flexibility with carried water
and fixed common boundaries, rather than reusing inflexible regional seasonal
output. Commercial Nordic constraints and source allocation remain separate
unresolved gates. Capacity increases or arbitrary negative bids are not fixes
established by this experiment.

## Reproduction and next weaknesses

Restore geographic sources with `python3 tools/collect_bidding_zone_sources_2025.py`;
pinned hashes reject changes to mutable provider releases. Restore packed metadata
with `python3 tools/pack_model_metadata.py --restore`.
Use the pinned interpreter for `tools/run_bidding_zone_network_2025.py --out <fresh-root>`,
then `tools/audit_bidding_zone_network_2025.py <fresh-root>` and
`tools/report_bidding_zone_network_2025.py <fresh-root>`. Geographic source bytes
and full witnesses stay ignored under `data/bidding-zone-network-2025/`; compact
downloads contain source/code hashes, checks and all observed metrics. Do not
overwrite a completed root or resume with changed coefficients.

**Next:** replace member-count supply/demand allocations with audited zonal fleet,
site/weather and demand data; reconcile total-load definitions. Investigate remaining
fixed-schedule failures/extremes and GSK sensitivity before changing hydro strategy.
Historical boundaries, commercial constraints, empirical thresholds/held-out periods,
paired-investment and static-app integration gates remain open. The public browser
still uses its reduced two-zone screen; publication does not replace that engine.

[Current zonal evidence and all price comparisons](/research/fixed-reservoir-screening-2025/bidding-zone-model.json)
 · [Previous source-backed water/location evidence](/research/fixed-reservoir-screening-2025/nve-hydro-diagnostics.json)
 · [Workbench methodology](/docs/workbench-methodology/)
