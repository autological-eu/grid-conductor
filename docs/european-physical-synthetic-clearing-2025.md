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

## Residual-demand response and fleet-stack diagnosis — 15 October 2026

**What this adds:** compare observed and simulated prices at comparable residual
demand, then inspect the unchanged fleet's available quantities and bid structure.
Hydro remains fixed. No new clearing solve, calibrated dispatch bids, candidate,
browser change or empirical acceptance is introduced.

**Main finding: the price response is too weak, not simply too low everywhere.**
Equal-zone mean dispatch bias is EUR-1.69/MWh in the lowest residual band
and EUR-49.75/MWh in the highest. Observed high-minus-low prices average
EUR79.37/MWh, versus EUR31.32/MWh for dispatch; the dispatch
contrast is smaller in 36/41 areas. Each area uses its own bands
and hour counts. These are conditional contrasts, not causal demand derivatives.

### Comparable response bands

For each zone, January–June residual demand defines four quintile boundaries.
Evaluate all five bands on July–December only, using identical known hours for
observed A44 prices, annual-v7 dispatch and the separate statistical reference.
Residual demand is prepared demand minus **available** wind and solar, not actual
renewable generation. All 41 eligible price areas retain 4416 evaluation
hours; ties and empty bands remain explicit. Training quantiles do not guarantee
equally sized evaluation bands. Negative prices/residuals are preserved.

The local PNG/SVG `residual-response` figure shows DE-LU, FR and NO5; full area
coverage is in the table below. These are conditional means, **not inferred
physical supply curves**: seasonal fuel conditions, outages, hydro and imports
can differ between bands. Already inspected 2025 remains retrospective evidence.

Observed mean prices rise from the lowest to highest band in
41/41 areas with both bands populated.
The dispatch response moves in the opposite direction despite that observed rise
in 4 areas (NO1, NO3, NO4, NO5).
Differences in level and response shape must be investigated separately; a
zone-wide price offset alone cannot correct a wrong direction or slope.

Bias is dispatch minus observed. High-minus-low contrasts describe band means,
not derivatives or causal effects of adding capacity. All prices are EUR/MWh.

| Area | Low / high band hours | Low-band bias | High-band bias | Observed high−low | Dispatch high−low |
| --- | ---: | ---: | ---: | ---: | ---: |
| AL | 643 / 1124 | -5.39 | -57.54 | 71.38 | 19.23 |
| AT | 779 / 853 | -0.63 | -42.76 | 88.46 | 46.32 |
| BE | 793 / 552 | -1.51 | -29.49 | 85.22 | 57.24 |
| BG | 904 / 404 | 21.95 | -52.05 | 102.83 | 28.83 |
| CH | 768 / 992 | -22.29 | -32.35 | 48.97 | 38.91 |
| CZ | 1172 / 666 | 13.11 | -30.67 | 71.74 | 27.96 |
| DE-LU | 822 / 642 | -14.05 | -53.96 | 116.62 | 76.71 |
| DK1 | 917 / 747 | 5.73 | -27.87 | 76.88 | 43.28 |
| DK2 | 862 / 764 | -16.49 | -82.18 | 76.59 | 10.90 |
| EE | 588 / 750 | 39.47 | -54.43 | 127.87 | 33.97 |
| ES | 883 / 953 | 4.31 | -24.21 | 94.73 | 66.21 |
| FI | 998 / 490 | 18.30 | -44.62 | 77.02 | 14.09 |
| FR | 1203 / 353 | 10.17 | -12.01 | 76.81 | 54.62 |
| GR | 774 / 1188 | 30.76 | -52.17 | 109.16 | 26.22 |
| HR | 452 / 1090 | 8.43 | -49.41 | 89.82 | 31.99 |
| HU | 778 / 773 | 11.46 | -63.98 | 113.25 | 37.81 |
| IT-CNOR | 846 / 1016 | -50.58 | -48.16 | 47.14 | 49.56 |
| IT-CSUD | 927 / 1078 | -61.79 | -44.27 | 39.70 | 57.22 |
| IT-North | 761 / 1040 | -18.63 | -41.08 | 43.55 | 21.09 |
| IT-SARD | 886 / 1130 | -74.46 | -34.95 | 48.02 | 87.54 |
| IT-SICI | 884 / 1116 | -61.62 | -42.75 | 45.30 | 64.17 |
| IT-SUD | 790 / 1022 | -55.54 | -44.86 | 51.17 | 61.86 |
| LT | 636 / 900 | 20.24 | -60.48 | 123.80 | 43.08 |
| LV | 594 / 963 | 28.70 | -52.68 | 120.97 | 39.59 |
| MK | 853 / 576 | 21.04 | -41.85 | 92.86 | 29.97 |
| NL | 610 / 721 | -15.12 | -32.83 | 87.92 | 70.20 |
| NO1 | 1548 / 313 | -22.25 | -107.93 | 60.84 | -24.84 |
| NO2 | 1438 / 325 | -35.51 | -58.78 | 41.79 | 18.52 |
| NO3 | 1544 / 345 | 16.04 | -85.53 | 67.92 | -33.65 |
| NO4 | 1386 / 452 | 23.06 | -34.75 | 57.25 | -0.56 |
| NO5 | 1343 / 357 | -3.25 | -148.80 | 70.80 | -74.75 |
| PL | 673 / 998 | 0.01 | -57.93 | 108.93 | 50.99 |
| PT | 866 / 878 | 1.36 | -16.31 | 77.71 | 60.03 |
| RO | 837 / 804 | 18.83 | -76.16 | 127.22 | 32.23 |
| RS | 1085 / 553 | 5.91 | -38.97 | 59.43 | 14.55 |
| SE1 | 847 / 774 | 24.81 | -24.19 | 53.89 | 4.89 |
| SE2 | 726 / 950 | 26.58 | -20.45 | 52.11 | 5.08 |
| SE3 | 1100 / 330 | 9.00 | -69.80 | 93.31 | 14.52 |
| SE4 | 874 / 463 | 7.47 | -63.48 | 93.61 | 22.66 |
| SI | 736 / 865 | 12.89 | -42.42 | 85.75 | 30.44 |
| SK | 1141 / 808 | 10.03 | -40.43 | 75.72 | 25.26 |

### Supply quantities and bid dispersion

Rebuild the frozen source fleet and aggregate original generator columns by area
and carrier, retaining original p_max_pu × p_nom. Emergency supply is excluded.
Reservoir injections stay separate, never converted to flexible available supply.
The prepared p_nom anchor below is **not annual-average 2025 in-service capacity**;
renewable commissioning trajectories remain encoded in the inherited profiles.

Bid range covers the full year and positive available MW. “Profiles” is the maximum
number of distinct annual bid-price sequences within one area/carrier, not the
number of real plants or operators. Efficiency is the prepared conversion factor.
Counts compare exact stored sequences and can distinguish negligible floating-point
differences; interpret them together with actual bid/efficiency ranges.
Zero-capacity source placeholders remain explicit; their profile counts do not
represent active supply and their unavailable bid ranges are not filled with zero.

| Carrier | Prepared p_nom GW | Areas | Max profiles / area | Bid range EUR/MWh | Efficiency range |
| --- | ---: | ---: | ---: | ---: | ---: |
| CCGT | 219.94 | 40 | 19 | 65.03–198.13 | 0.344–0.733 |
| OCGT | 6.11 | 1 | 12 | 109.48–178.04 | 0.384–0.420 |
| biomass | 25.11 | 30 | 9 | 19.98–21.32 | 0.442–0.468 |
| coal | 45.17 | 13 | 15 | 80.80–109.28 | 0.330–0.453 |
| geothermal | 0.90 | 8 | 1 | 0.00–0.00 | 1.000–1.000 |
| lignite | 61.81 | 17 | 7 | 105.68–126.81 | 0.330–0.399 |
| nuclear | 112.50 | 14 | 2 | 27.32–27.32 | 0.326–0.326 |
| offwind-ac | 48.73 | 40 | 1 | 0.00–0.00 | 1.000–1.000 |
| offwind-dc | 0.00 | 32 | 1 | No available MW | 1.000–1.000 |
| offwind-float | 0.00 | 40 | 1 | No available MW | 1.000–1.000 |
| oil | 17.08 | 25 | 9 | 152.45–195.35 | 0.350–0.361 |
| onwind | 235.81 | 48 | 1 | 0.00–0.00 | 1.000–1.000 |
| ror | 47.32 | 40 | 1 | 0.00–0.00 | 0.900–0.900 |
| solar | 183.59 | 48 | 1 | 0.00–0.00 | 1.000–1.000 |
| solar-hsat | 0.00 | 48 | 1 | No available MW | 1.000–1.000 |
| waste | 8.07 | 25 | 4 | 35.93–35.93 | 0.205–0.316 |

Nuclear availability is constant through the year in 14/14
modeled nuclear areas (BE, BG, CH, CZ, ES, FR, HU, NL, RO, SI, SK, FI, SE3, GB). Its inherited
availability is a declared 2024 proxy, not an audited 2025 outage calendar.
Gas has one annual bid profile per area/technology in
23/41 nonempty area/carrier
groups. These are structural simplifications, not proof of missing physical MW.
In France, nuclear available MW stays at 46.97 GW,
against a prepared nameplate anchor of 65.69 GW, every hour.
In contrast, German CCGT already has 19 stored
profiles and efficiencies 0.459–0.583:
the present gas stack is not uniformly one bid per technology across Europe.
All 41 gas area/carrier groups nevertheless have constant available MW
through the year; dated outages/deratings are a separate missing input dimension.
All inventoried generator offers are nonnegative. Negative Norwegian dispatch
prices therefore do not come from a negative gas or renewable bid: the fixed
injections and coupled physical/GSK formulation permit such marginal prices.
The response bands alone cannot attribute the effect to one constraint or prove
that those model constraints represent actual commercial price formation.

Thermal offers inherit monthly World Bank gas/oil and ECB FX inputs, a fixed
EUR80/t carbon assumption and prepared technology costs/efficiencies. Nuclear and
other nonthermal offers retain their source costs. Low-cost renewables remain
weather-limited. Available quantities, operational bids and observed generation
are different objects; generation is not substituted for availability.

### Where to inspect first

The ten largest absolute band-mean price biases below are selected **after**
evaluation, requiring at least 100 hours. They prioritize diagnosis, not validation.
Available nuclear/thermal columns are mean local MW in those hours, not dispatch.
The final column is local generator availability bidding ≤EUR60/MWh plus fixed
reservoir output minus demand. It excludes emergency but ignores imports,
commitment, reserves and network deliverability: positive values are local supply
envelopes, not proof of feasible surplus or erroneous market prices.

| Area / band | Hours | Observed price | Dispatch price | Bias | Nuclear GW | Thermal GW | Local ≤EUR60 envelope−demand GW |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| NO5 / 5 | 357 | 96.88 | -51.92 | -148.80 | 0.00 | 0.29 | 3.65 |
| NO1 / 5 | 313 | 106.45 | -1.48 | -107.93 | 0.00 | 0.00 | -3.31 |
| NO3 / 5 | 345 | 76.05 | -9.48 | -85.53 | 0.00 | 0.00 | 0.14 |
| DK2 / 5 | 764 | 123.29 | 41.11 | -82.18 | 0.00 | 0.16 | -0.74 |
| RO / 5 | 804 | 175.01 | 98.85 | -76.16 | 1.24 | 8.17 | -3.08 |
| IT-SARD / 1 | 886 | 76.03 | 1.57 | -74.46 | 0.00 | 2.32 | 1.83 |
| SE3 / 5 | 330 | 111.00 | 41.21 | -69.80 | 5.83 | 2.25 | -1.88 |
| HU / 5 | 773 | 164.28 | 100.30 | -63.98 | 1.82 | 4.16 | -3.79 |
| SE4 / 5 | 463 | 114.26 | 50.78 | -63.48 | 0.00 | 1.55 | -2.58 |
| IT-CSUD / 1 | 927 | 93.19 | 31.41 | -61.79 | 0.00 | 7.74 | 3.62 |

The full witness includes envelopes at EUR0/30/60/100/200, all carrier availability
and per-area bid/efficiency inventory. Network coupling may make a local price
differ from a local offer; unchanged physical/GSK and transport controls remain
separate evidence, not additive causal shares of price error.

### Implications for the next model change

1. **Correct supply timing and scope before fitting bids.** Prioritize dated nuclear
   outages and existing ES/PT wind/demand flags. Constant availability and inherited
   fleet/weather proxies need source verification; do not scale to observed prices
   or replace renewable availability with generated energy.
2. **Test transparent resource-level bid dispersion.** Audit whether technology-wide
   efficiencies/cost profiles collapse genuinely different units into a few steps.
   Use sourced efficiency, variable cost and outage information, with unchanged fuel
   inputs and fixed hydro as controls. More bid steps do not automatically improve
   empirical accuracy; evaluate all areas and adverse outcomes.
   Existing German gas dispersion means a blanket “add more steps” change is not
   supported by this inventory. Prioritize source-backed availability timing first.
3. **Keep network effects explicit.** Wrong local responses can reflect neighboring
   markets or physical/GSK constraints as well as local supply. Neither this
   association nor the statistical reference authorizes replacing dispatch with a
   fitted regional price curve or double-counting imports.
   The Norwegian reversed conditional response remains a network/fixed-injection
   investigation, not evidence that hydro needs a higher bid or more installed MW.

### Provenance and verification

Fresh ignored root: `data/bidding-zone-network-2025/response-diagnostic-v1/`.
Producer `tools/diagnose_residual_response_2025.py` seals source/witness and code
hashes before reading prices. Independent `tools/audit_residual_response_2025.py`
rebuilds original columns, MW tiers, demand/fixed hydro, chronological residual
identities, efficiency/profile inventory, training quantiles, common-hour means
and diagnostic ranking. All 41 areas / 469 fleet
rows replay; maximum MW aggregation difference 2.04e-10.
Three fixtures cover training-only boundaries, tied/empty bands, training exclusion,
missing prices and negative-price retention. Preparation 233.99s;
complete source/price producer 337.15s; independent replay
321.16s. These times are diagnostics, not clearing-loop times.
Figures and arrays remain local/ignored. Report updated locally; no CI/Pages or
public-URL publication claim follows.

## Simpler supply stacks and a residual-price reference — 14 October 2026

**Decision: keep hydro fixed; investigate fleet inputs and price-response modelling.**
The user redirected work away from further hydro flexibility after earlier tests
added complexity without consistent price gains. This iteration tests a new,
simple hourly supply-stack/transport diagnostic and a separate statistical price
reference. It does not restart the paused rolling-storage model or alter the
retained physical baseline/browser engine.

**Main result:** the simpler coupled clearing runs in **10.15s**
for 8760 hours, but full-year mean zonal MAE worsens **EUR33.23 → EUR34.62/MWh**
and mean correlation **0.502 → 0.498**. Simplification alone does not fix price
agreement. A monotone residual-demand price reference fitted on January–June
performs better on July–December: **EUR24.60/MWh MAE / r 0.656**, versus the
physical baseline's **EUR32.21/MWh / r 0.407** on exactly that evaluation period.
This is a price-prediction benchmark, not improved dispatch or investment valuation.

### Supply-stack controls and transmission scope

The fresh producer uses unchanged source-generator bids and hourly availability,
demand and fixed reservoir injections. No hydro rescheduling, source-capacity
scaling, weather reconstruction, fitted bid or observed-price forecast is used
in either dispatch control. Group only identical cost profiles within an island/
zone; all original available MW are conserved. Daily orchestration batches
independent hourly clears, not a joint storage auction.

**Isolated control:** sort each island/zone's bids and dispatch the cheapest
available quantities. At a supply-stack knot, report the right-hand marginal bid.
Fixed-hydro surplus requires export: its prices and dispatch stay NaN, not zero,
and no dumping sink or reservoir spill is invented. Original EUR10,000/MWh
emergency offers expose isolated supply deficits. They are not real fleet capacity.
The control has **42096 export-required node-hours**
and **55.31 TWh** emergency supply
on valid node-hours. Its paired MAE is approximately EUR2086/MWh;
that is a diagnostic of unsupported isolation, not an annual Europe forecast.
Missing surplus hours and unequal comparison cohorts remain explicit in the audit.

**Coupled control:** 50 separate island/zone balances, 109 links. Preserve every
controllable link and its bounds/efficiency; lossy signed reverse flow is rejected
rather than silently creating energy. Cross-zone AC corridors use the **sum of
retained N-0/security-adjusted ratings**. Omit internal AC constraints, Kirchhoff
relationships and GSK allocation. These are optimistic source-model transport
envelopes, not independently validated commercial NTC/ATC or JAO domains.
Cached JAO evidence covers selected January/July/December 2025 hours, not a
complete reconciled Europe-wide annual constraint dataset. Supported commercial
coupling therefore remains an open input gate.

Separate electrical islands cannot exchange energy without a link. ES and GB
each span two modeled islands; choose the largest-annual-demand island for the
observed-area price comparison, before inspecting prices. This is an explicitly
labelled price proxy, not proof of a common commercial clearing price. All 48
market-area labels and their 50 node results remain in the witness. Native AC
feasibility is **not** certified by passing transport balances.

All 8760 coupled hours solve, zero emergency MWh; independent source and per-edge
balance/bound replay passes with maximum residual **1.24e-10 MW**,
objective replay error **2.61e-08 EUR**. Five fixtures pass:
merit ordering/kink, unresolved fixed surplus, missing capacity, transfer-limited
prices and no implicit island connection. Source preparation takes
**121.29s**; complete producer/export **134.16s**,
peak RSS **2581 MiB**. Isolated vectorized evaluation takes
**1.38s**; source/transport replay and all 41 A44 raw-source
comparisons add **174.02s**. Preparation/audit is not loop timing.

### Temporal residual-demand price reference

Train a **single univariate monotone isotonic curve per area** on January–June
(4344 UTC hours). Input is model demand minus available wind and solar, not observed
renewable generation. Duplicate feature values receive count weights; interpolate
between fitted levels and clip beyond the training feature range to its endpoint.
Keep negative training prices. Evaluate July–December (4416 hours) without refitting,
parameter/split searches or bid construction from observed electricity prices.

Only this separate statistical reference fits A44 electricity prices. The dispatch
models' bids remain unchanged and independent of those prices. All 41 eligible
areas have the same evaluation hours for each comparison. Source prices are
hashed/XML-reparsed; independent replay checks that training-only fitted values
satisfy monotonicity and isotonic optimality, then reconstructs predictions and
temporal MAE/bias/RMSE. Maximum training optimality residual is
**3.17e-09**. Five curve fixtures pass.

| July–December comparison | Equal-zone MAE EUR/MWh | Mean zonal r |
| --- | ---: | ---: |
| Physical baseline | 32.21 | 0.407 |
| Transport diagnostic | 33.41 | 0.405 |
| Training mean | 29.15 | Undefined (constant) |
| Residual reference | 24.60 | 0.656 |

The training-mean reference distinguishes learned price levels from the additional
residual-demand signal. The residual curve improves on its EUR29.15/MWh MAE;
the gain over physical dispatch is not solely a test of transmission modelling.
All 2025 aggregate results had already been inspected before this experiment:
the algorithm withholds evaluation targets from fitting, but this is **retrospective
temporal evaluation, not an untouched held-out year or empirical acceptance**.
Future feature values use the same realized-year model inputs, not a verified
operational weather/demand forecast. Out-of-training-range counts, all seasonal
dispatch metrics and reference errors/bias/RMSE remain in the local evidence.

| Area | Jul–Dec physical MAE | Coupled MAE | Residual reference MAE | Physical r | Reference r |
| --- | ---: | ---: | ---: | ---: | ---: |
| AL | 38.20 | 43.11 | 34.38 | 0.355 | 0.487 |
| AT | 22.82 | 27.09 | 20.63 | 0.693 | 0.752 |
| BE | 20.92 | 19.79 | 22.61 | 0.730 | 0.708 |
| BG | 32.58 | 35.40 | 29.21 | 0.563 | 0.648 |
| CH | 27.36 | 29.64 | 22.97 | 0.611 | 0.582 |
| CZ | 25.27 | 26.18 | 27.67 | 0.454 | 0.595 |
| DE-LU | 23.35 | 24.00 | 18.30 | 0.692 | 0.830 |
| DK1 | 26.53 | 26.05 | 26.14 | 0.636 | 0.585 |
| DK2 | 56.30 | 57.80 | 29.34 | 0.073 | 0.534 |
| EE | 50.04 | 50.47 | 42.07 | 0.343 | 0.607 |
| ES | 22.55 | 23.59 | 18.79 | 0.688 | 0.831 |
| FI | 38.15 | 39.19 | 27.73 | -0.035 | 0.496 |
| FR | 20.71 | 24.68 | 23.18 | 0.685 | 0.730 |
| GR | 33.28 | 34.09 | 36.00 | 0.487 | 0.661 |
| HR | 26.86 | 31.14 | 30.20 | 0.604 | 0.642 |
| HU | 30.43 | 34.84 | 28.22 | 0.605 | 0.680 |
| IT-CNOR | 34.30 | 32.90 | 16.82 | 0.530 | 0.774 |
| IT-CSUD | 36.77 | 38.09 | 19.58 | 0.510 | 0.688 |
| IT-North | 27.08 | 31.50 | 15.05 | 0.564 | 0.759 |
| IT-SARD | 39.64 | 39.95 | 21.21 | 0.543 | 0.645 |
| IT-SICI | 38.35 | 38.72 | 18.40 | 0.527 | 0.654 |
| IT-SUD | 35.25 | 36.56 | 17.83 | 0.538 | 0.747 |
| LT | 44.81 | 45.99 | 41.31 | 0.395 | 0.610 |
| LV | 44.87 | 46.06 | 41.62 | 0.393 | 0.588 |
| MK | 30.94 | 35.09 | 30.82 | 0.560 | 0.601 |
| NL | 21.73 | 21.52 | 24.06 | 0.705 | 0.687 |
| NO1 | 40.53 | 35.64 | 20.82 | -0.216 | 0.523 |
| NO2 | 39.60 | 43.00 | 22.15 | 0.039 | 0.454 |
| NO3 | 27.56 | 22.19 | 14.70 | -0.099 | 0.780 |
| NO4 | 27.08 | 28.20 | 8.60 | 0.047 | 0.731 |
| NO5 | 43.67 | 27.61 | 20.33 | -0.371 | 0.696 |
| PL | 27.02 | 32.53 | 20.26 | 0.585 | 0.761 |
| PT | 22.73 | 23.55 | 25.11 | 0.675 | 0.687 |
| RO | 31.59 | 35.10 | 25.17 | 0.583 | 0.768 |
| RS | 29.20 | 33.14 | 32.64 | 0.576 | 0.473 |
| SE1 | 27.50 | 28.52 | 13.55 | 0.037 | 0.680 |
| SE2 | 27.69 | 28.93 | 11.72 | 0.053 | 0.722 |
| SE3 | 33.76 | 35.02 | 23.54 | 0.030 | 0.624 |
| SE4 | 42.15 | 43.90 | 27.81 | 0.131 | 0.615 |
| SI | 26.32 | 30.24 | 27.04 | 0.565 | 0.615 |
| SK | 24.95 | 28.93 | 31.16 | 0.616 | 0.624 |

### Implication and next work

Residual demand contains usable price information. The current source-bid stack
does not reproduce that response well, and simply removing the physical/GSK layer
does not improve Europe-wide agreement. The fast transport diagnostic is a useful
iteration control, but it is not accepted as the investment simulator. The fitted
reference has no dispatch, conservation, fuel or transfer constraints; its response
to a new line/generator/storage asset is **not** a verified counterfactual benefit.

Keep fixed hydro while improving the fleet's capacity/availability and bid-response
representation: prioritize Spain/Portugal wind site conversion, demand definitions/
zonal allocation and dated nuclear outages, then inspect resource cost dispersion
and operating constraints. Test each source-backed change against the same temporal
reference rather than tuning to inspected evaluation prices. Reconcile genuine
commercial transfer constraints before supported coupled-scenario acceptance.
Any use of historical prices to calibrate dispatch bids needs a separately declared
development/validation design; this benchmark does not silently authorize it.

Reproduce with pinned Python: `tools/run_simple_supply_stack_2025.py <fresh-root>`,
`tools/audit_simple_supply_stack_2025.py <root>`,
`tools/residual_price_benchmark_2025.py <root>`,
`tools/replay_residual_price_benchmark_2025.py <root>`, then
`tools/report_simple_supply_stack_2025.py <root>`. Current ignored root:
`data/bidding-zone-network-2025/simple-stack-v1/`. Cached compiled inputs allow
later diagnostic iterations without repeating preparation, provided their exact
source/coefficient hashes are preserved; source changes require rebuilding.
Full inputs/primals/curves, all comparisons and PNG/SVG charts stay outside Git.
This report update is local; no new CI/Pages claim, browser replacement, automatic
review restart or accepted baseline follows. Only one model programme remains active.

## Hourly marginal-bid and constraint investigation — 14 October 2026

**What was investigated:** which local offers are consistent with marginality,
how model constraints enter zonal prices, and how observed electricity prices
associate with the retained monthly gas/oil inputs. This reruns the **unchanged**
annual-v7 coefficients to save primal and dual witnesses; it is not a new candidate.
All 8760 hours solve, with original demand, availability, fixed hydro, network,
GSK and fuel bids. All 264 predeclared calendar demand probes are feasible.

**Main result:** monthly gas/oil associations with observed prices are modest
(mean zonal r 0.190/0.183, versus the residual-demand audit's 0.644).
This does not make fuel bids irrelevant, but fuel prices alone do not explain
the hourly price signal. In the Nordic zones, local-interior offer evidence is
mostly absent; reservoir hydro cannot bid in this fixed-injection formulation.
Model island coupling and passive constraints therefore need investigation
alongside hydro water value, rather than an arbitrary fuel-price uplift.

### Gas, oil and the remaining supply stack

An interior aggregate offer has both positive dispatch and remaining headroom
greater than 0.001 MW, and its bid matches the local price within 1e-5 EUR/MWh.
This is local marginal-offer evidence in this LP, not identification of a unique
real market generator. Equal-cost wind/solar/run-of-river offers are merged;
mixed and tied identities remain ambiguous. A zone can have an import- or
constraint-dependent price with **no local interior offer**. These categories
partition all 41 observed-zone × 8760 hours, with equal area weighting.
The absence of a local interior offer is common in a coupled market and does not
establish a model fault: an upstream resource can influence several areas.
Carrier sets retain full-year aggregate membership, including constituents that
may be unavailable in a particular hour; this conservative classification does
not infer an hourly dispatch split. "No local interior" is witness-specific,
not evidence that the real market had no marginal generator.

| Local offer evidence | Share of observed-zone hours |
| --- | ---: |
| Gas | 9.20% |
| Nuclear | 3.08% |
| Coal/lignite | 1.81% |
| Mixed/tied | 2.40% |
| No local interior | 82.48% |
| Other local | 1.02% |

Monthly gas-input/observed-price correlation has mean zonal **r = 0.190**;
the analogous oil association is **0.183**. These use the source-verified
World Bank/ECB thermal-input series, not a new daily fuel dataset. Monthly inputs
cannot explain intraday variation by themselves, and seasonal/common drivers can
produce correlation without causal price setting. The assumed EUR80/t carbon
price is constant, so its correlation is undefined, not zero. Observed electricity
prices never enter bid construction. The earlier +/-10% gas diagnostic showed
price influence; oil perturbations did not materially affect this baseline.
Fuel-price correlation and residual-demand correlation measure different relationships.

### How network shadows enter the recorded price

Free zonal net-injection stationarity gives:

**Zonal price = island-balance contribution + passive-network contribution.**

Each contribution is the relevant row shadow prices multiplied by that area's
injection column. This is an exact algebraic identity for the saved dual witness.
Island contributions include cross-island HVDC coupling, losses and cable scarcity;
they are not a single unconstrained European energy price. Passive contributions
reflect the model's PTDF, GSK and line limits, not verified JAO commercial constraints,
physical congestion rent or an independent share of market price error. Degeneracy
can change the decomposition without changing costs; do not treat it as unique
causal attribution. Nonzero shadow prices are distinct from merely binding limits.

Passive rows have nonzero shadow prices in **8720 of 8760 hours**
somewhere in the network. The table keeps all 48 clearing areas, including areas
without an observed-price target. "Passive >1" counts a zonal contribution whose
absolute value exceeds EUR1/MWh. Shares refer to local interior offers, not all
upstream price influence. All means retain signed contributions and negative prices.

| Area | Local gas % | Local nuclear % | No local interior % | Mean island term | Mean passive term | Passive >1 hours | Negative-price hours |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AL | 0.0 | 0.0 | 100.0 | 88.23 | 4.09 | 4216 | 0 |
| AT | 7.6 | 0.0 | 92.2 | 88.23 | -1.37 | 2547 | 0 |
| BA | 0.0 | 0.0 | 99.7 | 88.23 | 4.25 | 4089 | 8 |
| BE | 8.9 | 3.8 | 86.6 | 88.23 | -20.92 | 6893 | 0 |
| BG | 2.4 | 1.2 | 95.1 | 88.23 | 3.87 | 4518 | 0 |
| CH | 0.2 | 1.2 | 98.5 | 88.23 | -8.20 | 6670 | 0 |
| CZ | 12.0 | 3.8 | 64.9 | 88.23 | 8.30 | 5588 | 2 |
| DE-LU | 15.5 | 0.0 | 50.2 | 88.23 | -13.77 | 6748 | 0 |
| DK1 | 7.7 | 0.0 | 85.9 | 88.23 | -21.14 | 6933 | 22 |
| EE | 2.5 | 0.0 | 97.4 | 88.23 | -0.27 | 5817 | 0 |
| ES | 50.2 | 10.5 | 34.9 | 87.97 | -13.90 | 6306 | 0 |
| FR | 9.4 | 51.2 | 38.1 | 88.23 | -32.06 | 7373 | 0 |
| GR | 35.9 | 0.0 | 64.0 | 88.23 | 2.98 | 4727 | 0 |
| HR | 4.3 | 0.0 | 95.2 | 88.23 | 4.22 | 4013 | 12 |
| HU | 5.3 | 0.9 | 93.7 | 88.23 | 3.13 | 4164 | 0 |
| IT-CALA | 10.7 | 0.0 | 87.9 | 88.23 | -4.69 | 5713 | 0 |
| IT-CNOR | 7.1 | 0.0 | 92.8 | 88.23 | -1.51 | 5653 | 0 |
| IT-CSUD | 24.3 | 0.0 | 72.2 | 88.23 | -4.37 | 5692 | 0 |
| IT-North | 49.3 | 0.0 | 50.5 | 88.23 | 4.26 | 6041 | 0 |
| IT-SICI | 0.5 | 0.0 | 90.5 | 88.23 | -5.70 | 5719 | 0 |
| IT-SUD | 20.5 | 0.0 | 77.6 | 88.23 | -4.37 | 5691 | 0 |
| LT | 11.8 | 0.0 | 87.7 | 88.23 | -0.27 | 5817 | 0 |
| LV | 10.7 | 0.0 | 89.2 | 88.23 | -0.27 | 5817 | 0 |
| ME | 0.0 | 0.0 | 100.0 | 88.23 | 4.23 | 4196 | 1 |
| MK | 1.4 | 0.0 | 97.9 | 88.23 | 4.72 | 4714 | 0 |
| NL | 9.9 | 0.2 | 82.7 | 88.23 | -16.35 | 6793 | 0 |
| PL | 25.3 | 0.0 | 57.2 | 88.23 | 1.16 | 5906 | 0 |
| PT | 15.6 | 0.0 | 79.2 | 88.23 | -13.02 | 6634 | 18 |
| RO | 10.8 | 0.6 | 88.4 | 88.23 | 3.97 | 4138 | 0 |
| RS | 3.3 | 0.0 | 96.4 | 88.23 | 4.30 | 4280 | 0 |
| SI | 1.2 | 0.7 | 97.0 | 88.23 | 4.74 | 4149 | 23 |
| SK | 2.8 | 1.1 | 95.8 | 88.23 | 3.34 | 4736 | 1 |
| XK | 0.0 | 0.0 | 99.9 | 88.23 | 4.44 | 4572 | 0 |
| DK2 | 0.2 | 0.0 | 92.9 | 44.53 | 0.00 | 0 | 0 |
| FI | 4.6 | 22.1 | 59.0 | 44.53 | -2.85 | 2947 | 0 |
| NO1 | 0.0 | 0.0 | 93.8 | 44.53 | -7.33 | 3536 | 1051 |
| NO2 | 0.0 | 0.0 | 85.4 | 44.53 | 1.19 | 3637 | 95 |
| NO3 | 0.0 | 0.0 | 95.4 | 44.53 | -13.19 | 3592 | 685 |
| NO4 | 0.8 | 0.0 | 92.9 | 44.53 | -8.28 | 3549 | 337 |
| NO5 | 0.4 | 0.0 | 89.9 | 44.53 | -19.73 | 3646 | 1258 |
| SE1 | 0.1 | 0.0 | 97.0 | 44.53 | -4.00 | 3090 | 87 |
| SE2 | 0.0 | 0.0 | 95.5 | 44.53 | -3.35 | 3154 | 0 |
| SE3 | 0.3 | 28.9 | 64.6 | 44.53 | -1.27 | 1290 | 0 |
| SE4 | 1.0 | 0.0 | 97.8 | 44.53 | -0.03 | 70 | 0 |
| FR-COR | 9.6 | 0.0 | 90.4 | 87.97 | 0.00 | 0 | 0 |
| GB | 25.9 | 10.1 | 46.7 | 58.57 | 0.00 | 4 | 0 |
| IE-SEM | 71.8 | 0.0 | 19.1 | 80.84 | 0.00 | 0 | 0 |
| IT-SARD | 13.6 | 0.0 | 65.3 | 75.38 | 0.00 | 0 | 0 |

Contribution units are EUR/MWh. Passive adjustments may raise or lower a zone's
price; a negative contribution is not negative congestion rent. Exact offer
carrier sets, every area's full category counts, top passive-row/link-bound
shadow diagnostics and all observed/fuel associations remain in the ignored audit.

### Hydro's structural limitation

Reservoir hydro is **fixed injection**, subtracted from load before clearing.
It has no variable offer or marginal water value in this LP. Changing the cost
of a fixed quantity adds a constant to the objective; it cannot repair prices.
A hydro-bidding correction therefore requires bounded dispatch flexibility with
explicit inflow, efficiency, turbine/stock constraints and common stock boundaries,
not simply a hydro-price multiplier. This audit does not implement or validate
that correction or identify when hydro actually set the observed market price.

### Verification and demand probes

Independent native-component replay verifies the annual saved primal. Dual replay
checks stationarity, bound/row complementary slackness, strong duality and the
price identity; it verifies that recorded prices are legitimate LP sensitivities,
not that the market model is empirically correct. Interior offer columns are
independently checked to contain only their zonal balance, and interior bid/price
agreement is tested. All 41 eligible observed prices are rehashed/XML-reparsed.

| Check | Maximum difference |
| --- | ---: |
| Baseline price reproduction EUR/MWh | 0 |
| Baseline objective reproduction EUR | 0 |
| Native-component residual MW | 9.76e-06 |
| Dual stationarity EUR/MWh | 9.77e-09 |
| Strong-duality gap EUR | 0.00033 |
| Complementarity EUR | 0.00123 |
| Price-decomposition EUR/MWh | 9.21e-09 |

Demand probes use each month's fifteenth day at noon UTC for DE-LU, FR, NO1-NO5,
SE1-SE4, with +/-1 MW along the unchanged GSK. They preserve all supply/water
inputs and physical limits. This tests the model's assumed marginal withdrawal
pattern, not independently observed demand locations. The supporting-price slope
must lie between downward/upward objective secants; kinked prices need not equal
both secants. All 264 saved feasible primals and objective differences replay.
Four targeted identity/constraint-sign/mixed-offer/boundary fixtures pass.

Annual clearing/dual capture: **73.05s**; source/grid preparation
**239.78s**; producer including probes/export
**329.50s**, peak RSS **2584 MiB**.
Independent physics/dual/probe/source replay adds **519.67s**.
These timings do not change the retained baseline's benchmark receipt.

Reproduce with pinned Python: `tools/run_price_mechanism_2025.py <fresh-root>`,
`tools/audit_price_mechanism_2025.py <root>`, then
`tools/report_price_mechanism_2025.py <root>`. Ignored root:
`data/bidding-zone-network-2025/price-mechanism-v1/`. Primal/dual/probe witnesses,
all-area evidence and PNG/SVG charts remain outside Git. The local plot shows
offer evidence and NO5's monthly decomposition. This report update is local;
no new live-publication or baseline/browser-integration claim follows.

**Next:** interpret the verified Nordic constraint contributions alongside the
residual-demand signal; reconcile commercial GSKs and test bounded hydro flexibility
with preserved water/stock boundaries. Keep wind, demand and nuclear source
corrections separate. Fuel influence is established within this model, but neither
monthly fuel correlation nor constraint shadows identify causal observed-price errors.
No price fitting, arbitrary network relaxation, annual-optimum claim or retired
search restart is authorized by these diagnostic results.

## Europe-wide residual-demand audit — 14 October 2026

**Main finding: improve supply/demand inputs, but also diagnose price formation.**
The unchanged baseline's demand-minus-wind/solar signal correlates with observed
prices at an arithmetic mean zonal **r = 0.644**, versus **0.502** for its
cleared prices. Residual-demand correlation is higher in 31 of 41 eligible areas.
This is a descriptive association, not a price estimator, improvement in MAE,
held-out validation or proof that one bidding/constraint assumption is responsible.

The audit covers **48 modeled clearing areas × 8760 UTC hours**, including all
41 eligible A44 price areas. No coefficients changed and no additional clearing
was run. The annual-v7 baseline, its zero-emergency/feasibility evidence, and the
browser's older two-zone estimator remain unchanged.

### Definitions and source coverage

Residual VRE demand = prepared model demand − available wind − available solar.
The wider envelope additionally subtracts available nuclear, run-of-river and
biomass plus the fixed reservoir schedule. It is a supply envelope, not actual
dispatch: nuclear/biomass can be curtailed, fixed hydro is conditional, and imports,
network deliverability, reserves and strategic/commitment bids are not accounted
for in this subtraction. Negative residuals are retained, not clipped. Local
thermal-envelope deficits do not establish infeasibility because imports matter.

Availability uses the retained prepared network, original hourly profiles and
the inherited IRENA capacity trajectory; generation never replaces availability.
Low-cost families are declared by technology, not an empirically fitted bid cutoff.
Emergency supply and battery/pumped-storage discharge are excluded. Generator
identity is preserved in this input audit even where clearing aggregates equal-cost
wind/solar offers, so their dispatch identities cannot be inferred from saved offers.

Fresh ENTSO-E A75/A16 raw interval replay verifies **456 area-months**.
Missing months/types/hours remain unknown. Technology comparisons sum only the
named reported categories: B18/B19 wind, B16 solar, B14 nuclear, B11 run-of-river,
B01 biomass. Unreported categories are not certified zero. Complete reported
categories do not certify whole-fleet reporting. Germany's generation excludes
Luxembourg although clearing uses DE-LU; other national/reporting-area boundaries
and source zone allocations remain proxies. A44 prices are rehashed/XML-reparsed.

Ember's [monthly national release](https://files.ember-energy.org/public-downloads/generation/outputs/release_generation_monthly_global.csv)
provides complete 2025 demand totals for 33 of 34 modeled countries.
Missing national totals are not annualised. Compare country sums, never national
totals with an individual bidding zone. Demand accounting (net/gross, losses,
embedded/self-consumed generation, industrial coverage) is still unreconciled.
Elhub's independently source-replayed Norwegian metered consumption is a separate
hourly check; it is not automatically total system load.

### Supply consistency: largest flags

The predeclared flag is reported generation exceeding available supply by more
than 1 MW. Excess TWh sums positive hourly differences on known hours; it is
**not** annual missing capacity, recoverable energy, curtailment or causal price
error. Available supply above generation can reflect curtailment; it is not an
error by itself. Different resource classifications can invalidate direct comparisons.

| Area / resource | Known hours | Available TWh | Generated TWh | Positive excess TWh | Flagged hours |
| --- | ---: | ---: | ---: | ---: | ---: |
| ES / wind | 8723 | 44.19 | 55.45 | 14.54 | 7445 |
| AT / ror | 8760 | 9.98 | 24.12 | 14.14 | 8760 |
| FR / ror | 8754 | 27.93 | 37.77 | 11.64 | 6728 |
| FR / nuclear | 8754 | 411.16 | 371.40 | 10.42 | 2309 |
| ES / ror | 8723 | 1.29 | 8.35 | 7.06 | 8723 |
| PT / wind | 8760 | 6.51 | 13.48 | 7.05 | 8582 |
| NO1 / ror | 8760 | 6.36 | 12.82 | 6.47 | 8731 |
| FI / ror | 8760 | 5.67 | 11.99 | 6.35 | 8376 |
| ES / solar | 8723 | 62.55 | 52.37 | 6.33 | 5702 |
| RS / ror | 8760 | 1.65 | 7.51 | 5.86 | 8724 |
| IT-SUD / wind | 8760 | 3.75 | 9.17 | 5.52 | 8174 |
| CH / ror | 8760 | 9.52 | 14.50 | 5.25 | 8047 |
| FI / wind | 8760 | 17.40 | 21.55 | 5.18 | 6535 |
| NO2 / ror | 8760 | 1.02 | 6.05 | 5.03 | 8760 |
| IT-North / ror | 8760 | 17.92 | 21.76 | 4.92 | 6523 |
| PT / ror | 8760 | 5.10 | 8.84 | 4.52 | 6753 |
| AT / wind | 8760 | 4.30 | 8.54 | 4.40 | 7718 |
| NO3 / ror | 8760 | 0.34 | 4.72 | 4.37 | 8760 |

Spain's wind has shape correlation 0.880 and Portugal's 0.862; their large volume
shortfalls justify auditing dated capacity and site-weighted conversion/coverage
before a bid uplift. Spain has 37 missing generation hours, which are excluded.
Its solar available energy exceeds reported generation on matched hours, yet
there are hourly above-availability flags: annual totals alone cannot validate
weather timing, geography or technology scope.

Run-of-river flags are especially sensitive to source classification: B11/B12
reservoir routing may differ from PyPSA's ROR/fixed-reservoir split. They do not
justify adding turbines or water. Reconcile combined hydro accounting and regional
routing before interpreting the Austria/Finland/Norway differences as shortages.
France's nuclear available envelope is flat through 2025, while generation varies.
Its total envelope is above reported generation but lacks outage timing. Observed
generation is not a replacement availability series; obtain capacity/outage inputs.

### National demand checks

Absolute differences above 5% flag investigation, not an acceptance threshold or
an instruction to scale loads. Totals below show complete 12-month references.

| Country | Prepared model TWh | Ember demand TWh | Difference % |
| --- | ---: | ---: | ---: |
| ME | 3.07 | 4.25 | -27.8 |
| MK | 5.32 | 7.10 | -25.0 |
| GB | 236.73 | 296.12 | -20.1 |
| AT | 59.19 | 70.53 | -16.1 |
| CH | 62.35 | 70.22 | -11.2 |
| LT | 11.77 | 13.25 | -11.1 |
| XK | 6.78 | 7.46 | -9.1 |
| BA | 8.43 | 9.18 | -8.1 |
| HU | 43.21 | 46.85 | -7.8 |
| BG | 37.89 | 35.17 | +7.7 |
| IT | 277.11 | 297.46 | -6.8 |
| DK | 38.47 | 41.22 | -6.7 |
| DE | 465.65 | 496.84 | -6.3 |
| NL | 116.90 | 123.39 | -5.3 |
| GR | 50.19 | 47.70 | +5.2 |
| SI | 12.53 | 13.20 | -5.1 |
| ES | 238.41 | 247.38 | -3.6 |
| HR | 18.23 | 18.84 | -3.2 |
| PT | 53.09 | 54.58 | -2.7 |
| RS | 34.32 | 35.23 | -2.6 |
| BE | 80.36 | 82.16 | -2.2 |
| NO | 137.04 | 134.55 | +1.9 |
| FI | 84.55 | 85.91 | -1.6 |
| EE | 7.94 | 7.84 | +1.3 |
| SE | 129.55 | 128.38 | +0.9 |
| RO | 53.56 | 54.03 | -0.9 |
| CZ | 62.61 | 62.89 | -0.4 |
| SK | 25.82 | 25.94 | -0.4 |
| PL | 158.35 | 158.97 | -0.4 |
| IE | 34.53 | 34.60 | -0.2 |
| LV | 7.20 | 7.20 | +0.1 |
| FR | 434.68 | 434.58 | +0.0 |
| LU | 4.84 | 4.84 | +0.0 |

Sixteen of 33 complete national comparisons exceed 5%. Countries with near-equal
annual totals still need hourly and zonal validation. No certified independent
whole-Europe hourly zonal demand observation was reconstructed here. Norwegian
Elhub comparisons preserve their metered-consumption scope:

| Zone | Known hours | Model TWh | Metered TWh | Hourly shape r |
| --- | ---: | ---: | ---: | ---: |
| NO1 | 8760 | 38.99 | 32.42 | 0.989 |
| NO2 | 8760 | 35.60 | 35.32 | 0.963 |
| NO3 | 8760 | 22.80 | 28.10 | 0.950 |
| NO4 | 8760 | 21.87 | 19.21 | 0.920 |
| NO5 | 8760 | 17.79 | 16.46 | 0.881 |

### All-area hourly residual and price associations

Demand/wind/solar totals below are model-input TWh over 8760 hours. VRE-negative
counts retain surplus envelope hours; they are not measured curtailment. Both r
columns compare with the same observed price series. A dash means unavailable
price comparison, not zero. Raw MW residuals are not prices, and their correlations
cannot be compared as MAE or interpreted as a calibrated substitute model.

| Area | Demand TWh | Available wind TWh | Available solar TWh | VRE-negative hours | Residual/price r | Cleared/price r |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| AL | 7.61 | 0.07 | 1.17 | 0 | 0.584 | 0.486 |
| AT | 59.19 | 4.30 | 11.72 | 374 | 0.802 | 0.781 |
| BA | 8.43 | 0.09 | 0.85 | 260 | — | — |
| BE | 80.36 | 20.72 | 11.37 | 171 | 0.745 | 0.784 |
| BG | 37.89 | 0.70 | 7.17 | 53 | 0.720 | 0.614 |
| CH | 62.35 | 0.04 | 11.71 | 21 | 0.629 | 0.762 |
| CZ | 62.61 | 0.46 | 4.91 | 0 | 0.635 | 0.570 |
| DE-LU | 470.49 | 175.11 | 112.44 | 1541 | 0.844 | 0.776 |
| DK1 | 19.61 | 22.15 | 3.72 | 5605 | 0.593 | 0.690 |
| EE | 7.94 | 1.89 | 0.87 | 237 | 0.623 | 0.426 |
| ES | 238.41 | 44.42 | 62.96 | 909 | 0.751 | 0.708 |
| FR | 433.49 | 56.21 | 37.03 | 0 | 0.832 | 0.766 |
| GR | 50.19 | 8.14 | 14.41 | 982 | 0.733 | 0.588 |
| HR | 18.23 | 1.09 | 1.43 | 0 | 0.705 | 0.661 |
| HU | 43.21 | 0.40 | 9.51 | 669 | 0.726 | 0.668 |
| IT-CALA | 3.57 | 1.68 | 3.45 | 4191 | — | — |
| IT-CNOR | 24.77 | 0.17 | 4.43 | 40 | 0.773 | 0.670 |
| IT-CSUD | 41.96 | 3.72 | 18.25 | 1879 | 0.653 | 0.644 |
| IT-North | 170.40 | 0.09 | 10.88 | 0 | 0.694 | 0.714 |
| IT-SICI | 10.02 | 1.95 | 8.17 | 3212 | 0.553 | 0.636 |
| IT-SUD | 21.91 | 3.75 | 5.15 | 696 | 0.718 | 0.659 |
| LT | 11.77 | 4.61 | 2.84 | 2040 | 0.591 | 0.454 |
| LV | 7.20 | 0.30 | 0.74 | 0 | 0.628 | 0.447 |
| ME | 3.07 | 0.04 | 0.04 | 0 | — | — |
| MK | 5.32 | 0.02 | 1.36 | 1549 | 0.701 | 0.633 |
| NL | 116.90 | 46.49 | 28.33 | 1537 | 0.743 | 0.775 |
| PL | 158.35 | 22.97 | 25.68 | 178 | 0.814 | 0.669 |
| PT | 53.09 | 6.51 | 9.65 | 132 | 0.683 | 0.695 |
| RO | 53.56 | 3.10 | 6.67 | 23 | 0.802 | 0.630 |
| RS | 34.32 | 0.61 | 0.48 | 0 | 0.548 | 0.632 |
| SI | 12.53 | 0.00 | 1.82 | 198 | 0.701 | 0.635 |
| SK | 25.82 | 0.00 | 1.03 | 0 | 0.679 | 0.698 |
| XK | 6.78 | 0.04 | 0.03 | 0 | — | — |
| DK2 | 18.86 | 9.01 | 1.29 | 521 | 0.540 | 0.303 |
| FI | 84.55 | 17.40 | 1.25 | 0 | 0.539 | 0.112 |
| NO1 | 38.99 | 0.43 | 0.20 | 0 | 0.410 | 0.037 |
| NO2 | 35.60 | 2.60 | 0.27 | 0 | 0.347 | 0.166 |
| NO3 | 22.80 | 1.66 | 0.13 | 0 | 0.582 | 0.016 |
| NO4 | 21.87 | 3.11 | 0.02 | 0 | 0.460 | 0.007 |
| NO5 | 17.79 | 1.90 | 0.19 | 0 | 0.618 | -0.133 |
| SE1 | 9.61 | 7.12 | 0.01 | 2459 | 0.437 | 0.044 |
| SE2 | 14.77 | 14.53 | 0.09 | 3315 | 0.450 | 0.047 |
| SE3 | 82.15 | 8.66 | 3.17 | 0 | 0.615 | 0.222 |
| SE4 | 23.01 | 4.56 | 2.02 | 96 | 0.631 | 0.263 |
| FR-COR | 1.19 | 0.02 | 0.00 | 0 | — | — |
| GB | 229.23 | 127.18 | 22.13 | 1642 | — | — |
| IE-SEM | 42.04 | 18.07 | 2.27 | 1005 | — | — |
| IT-SARD | 4.48 | 1.82 | 5.45 | 4121 | 0.562 | 0.615 |

NO5 residual-demand correlation is +0.618 while cleared-price correlation is
−0.133; NO3 is +0.582 versus +0.016 and SE4 +0.631 versus +0.263. Existing
demand/weather contain a meaningful market-related signal that the current
clearing output does not reproduce. This supports controlled hydro opportunity-
cost/fixed-injection and GSK/commercial-constraint diagnostics alongside input
corrections. It does not identify their causal contribution or certify a bidding rule.

### Verification, reproducibility and next action

Independent source-input replay reconstructs every zonal demand and technology
availability sum from the unchanged network, fixed hydro, reported quantities,
missingness and both residual identities. Maximum aggregation difference is
**0 MW**. National monthly demand sums and
references replay; Norwegian source responses are rehashed against their retained
raw replay. Four targeted coverage/threshold tests pass. This validates the input
audit, not a new market solution or price accuracy. Producer/replay/code/source
hashes and failed/unavailable source coverage remain local.

Producer/source replay takes **373.00s**, peak RSS
**2603 MiB**; independent reconstruction adds **155.45s**.
These are audit timings, not annual clearing-loop timings. Reproduce with pinned
Python: `tools/residual_demand_audit_2025.py <fresh-root>`, then
`tools/replay_residual_demand_audit_2025.py <root>` and
`tools/report_residual_demand_audit_2025.py <root>`. Current ignored root is
`data/residual-demand-audit-2025/v1/`. Its PNG/SVG diagnostic shows matched wind
quantities, national demand differences and French nuclear timing; full hourly
matrices, all resource coverage/flags and raw replay manifests stay outside Git.
This report update is local until CI/Pages and public URLs are verified.

**Next priorities:**

1. Reconcile Spain/Portugal wind capacity and site-weather conversion with dated
   external sources; preserve IRENA normalization and validate against generation
   without fitting availability to it. Extend the same audit to Finland/Austria
   and relevant Italian zones, retaining scope limits.
2. Resolve demand definitions for the largest discrepancies, then obtain/replay
   actual hourly zonal load. Do not silently scale demand to Ember.
3. Replace flat/proxy nuclear availability with dated fleet/outage evidence.
4. Diagnose Nordic binding constraints, fixed hydro marginal water value and GSK
   price responses on predeclared hours/common inputs. The residual signal is
   stronger than current cleared prices, so data corrections alone are insufficient
   evidence for a fix. Keep chronology/water, adverse outcomes and independent
   physics gates; do not restart retired adaptive-water searches.

Predeclare validation splits/acceptance thresholds before tuning. No blanket
fuel uplift, renewable-generation substitution, baseline promotion or browser
replacement follows from this audit. Automatic hourly reviews remain disabled.

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
