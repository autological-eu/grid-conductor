# European hourly dispatch — whole-network bidding-zone model

## Summary and conclusion

The geographic/annual results below describe the retained **uncalibrated annual-v7 baseline**. The latest [hourly offer-curve experiment](#hourly-price-shape-and-resource-offer-curves--16-october-2026) changes training-fitted offers only and remains a diagnostic, with separate evaluation results.

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
**0.000000 MWh**, with emergency used in **0 of 8760 solved hours**. The model is
an untuned diagnostic, not an accepted market-price or investment estimator.

The comparison below isolates country versus bidding-zone pooling on **the same
rebuilt grid**. It is not directly attributable to the geography change alone when
compared with the earlier 128-bus report: topology and branch aggregation also changed.
All original hourly parent demand, available supply and fixed reservoir output are
conserved. These baseline results do not fit supply, demand or water to ENTSO-E prices.
The separately labelled later calibration experiments fit bids on training prices
while preserving demand, original available quantities and fixed hydro.

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

The annual-v7 baseline retains original generator cost and weather-availability
time series. Later bid-calibration diagnostics change offers only, as labelled.
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

## Hourly price-shape and resource offer curves — 16 October 2026

**Result:** July–December equal-zone MAE **32.20 → 30.03 EUR/MWh**,
mean correlation **0.407 → 0.448**, and
within-day correlation **0.361 → 0.403**.
Spain daily range is **81.61 EUR/MWh**, against observed
**98.10** and control **66.47**.
This is a verified finite retrospective experiment, not an accepted baseline replacement.

Thermal selection: **[0.0, 0.5, 0.0]**; combined selection: **[0.0, 0.5, 0.0]**.
Parameter order is [zonal-offset strength, thermal-curve strength, renewable discount EUR/MWh].
The chosen renewable discount is **0 EUR/MWh**; zero is a legitimate
result, not an omitted negative-bid implementation. France selected bias is
**+0.43 EUR/MWh**. Adverse zones and quantities remain below.

### What was implemented

- Each original gas/coal offer retains its plant fuel/efficiency/carbon/VOM anchor
  and splits available MW into **50/35/15%** blocks. Adders are [0, 35%, 100%] of
  the curve strength times EUR120/MWh gas or EUR90/MWh coal. Nuclear retains one
  running-cost block, with bounded zonal adjustment and no peaking adder.
- Jointly test offset strengths 0/0.5/1 and thermal strengths 0/0.5/1. Offsets
  come from Jan–April local-interior price residual medians, shrunk n/(n+168),
  bounded ±30/30/15 for gas/coal/nuclear. Each proposal has one shared strength;
  this is not unrestricted per-zone inverse optimization.
- A separate stage tests discounts 0/10/30 EUR/MWh on the lower **50%** of wind/
  solar offers, retaining the selected thermal curve. Negative bidding is an
  effective synthetic assumption, not a measured subsidy or inferred actual order.
  Mixed zero-cost wind/solar/run-of-river groups are separated by source membership
  first: run-of-river and other resources never inherit a renewable discount.
- Every block keeps its original network column and total original availability.
  No renewable generation is substituted for availability; no extra capacity,
  hydro flexibility, time shift, outage correction, hard minimum output, ramping,
  unit commitment or storage policy is introduced.

The daily loop contains independent hourly physical LPs; it is not intertemporal
daily market optimization. Block prices respond through cleared utilization;
there are no fitted hour-of-day electricity prices or new forecast prepasses.

### Chronological fitting and selection

January–April (2880 hours) constructs proposals and fitting scores. The best two
nonzero joint thermal states by fitting score, plus control, enter May–June
(1464 hours) selection. Thermal parameters are fixed before the renewable stage;
all three renewable states then receive fit/selection scores. Final selections
are sealed before July–December (4416 hours) evaluation. All 2025 has already been
inspected: **retrospective evaluation, not untouched validation**. Both selected
stages receive annual evaluation; identical parameters reuse their witness.

The score equally averages control-normalized overall MAE, daily-demeaned MAE,
monthly generation-allocation interval error and implied-net-export interval
error, plus declared regularization on offsets, slope and renewable discount.
Original generation/trade normalization and missingness rules remain unchanged.
Weights, blocks and bounds are experimental settings, not empirical acceptance
thresholds. The finite search does not recover actual bids or a global optimum.

| Formulation | MAE EUR/MWh | Mean r | Within-day r | Demeaned MAE EUR/MWh | Generation error | Implied-trade error |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Control | 32.20 | 0.407 | 0.361 | 22.00 | 0.41035 | 0.22541 |
| Thermal curves | 30.03 | 0.448 | 0.403 | 21.38 | 0.33264 | 0.19658 |
| Selected combined | 30.03 | 0.448 | 0.403 | 21.38 | 0.33264 | 0.19658 |

### Diagnostic findings and input limits

The separately replayed saved-data diagnosis covers all eligible zones, daily
range/ramp/tail errors, training-defined residual bands and ES/FR local profiles.
Residual demand subtracts **available** wind/solar from demand; fixed hydro is
separate. Renewable availability-versus-reported-generation lags −3…+3 hours
are descriptive checks, not time-shift prescriptions or evidence of available
supply derived from dispatch. Source missingness is retained.

Spain solar's unshifted availability/generation correlation is 0.921; comparing
available[t+1] with reported[t] gives 0.944. This flags interval/time conventions,
curtailment or fleet coverage for investigation, not a proven one-hour error.
No source correction is applied. Spanish gas availability remains 27.696 GW
and nuclear 6.460 GW every hour, without dated outage/derating timing. Independent
headroom inventory in the local summary is local availability minus dispatch,
not deliverable system reserve or a causal explanation of price errors.
Spanish control gas headroom has median **{esgas['control_headroom_median_mw']/1000:.2f} GW**
and tenth percentile **{esgas['control_headroom_p10_mw']/1000:.2f} GW**. Physical
national gas capacity is therefore often far from exhausted. Curve improvements
reflect changed economic offers and coupled dispatch, not proof of actual physical
capacity scarcity or a source-backed outage correction.

Negative offers on half of renewable supply need not create negative clearing
prices: a nonnegative resource can still be marginal. Missing negative prices
therefore cannot be fixed merely by declaring a discount. Likewise a steeper
thermal curve cannot prove that its scarcity volume is physically realistic.

### Levels, ranges, ramps, tails and timing

Ranges and tail counts show observed / modeled values. All statistics use UTC
days; local-hour plots handle DST explicitly. Peak timing is the minimum circular
distance between observed/model maximum-price hour sets; flat modeled plateaus
can make it optimistic. Tie counts and trough distances remain in the audit.

| Zone | Formulation | Bias EUR/MWh | Daily range obs/model | Ramp MAE EUR/MWh | Negative hours obs/model | >EUR150 hours obs/model | Peak set-distance hours |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ES | Control | +3.12 | 98.10 / 66.47 | 12.49 | 97 / 0 | 54 / 0 | 1.66 |
| ES | Thermal curves | +7.58 | 98.10 / 81.61 | 12.75 | 97 / 0 | 54 / 0 | 2.45 |
| ES | Selected combined | +7.58 | 98.10 / 81.61 | 12.75 | 97 / 0 | 54 / 0 | 2.45 |
| FR | Control | +0.01 | 82.51 / 46.43 | 12.56 | 150 / 0 | 22 / 0 | 3.70 |
| FR | Thermal curves | +0.43 | 82.51 / 51.32 | 12.55 | 150 / 0 | 22 / 0 | 3.60 |
| FR | Selected combined | +0.43 | 82.51 / 51.32 | 12.55 | 150 / 0 | 22 / 0 | 3.60 |
| DE-LU | Control | -17.90 | 114.33 / 56.44 | 11.96 | 142 / 0 | 232 / 0 | 3.13 |
| DE-LU | Thermal curves | -13.76 | 114.33 / 63.87 | 11.80 | 142 / 0 | 232 / 0 | 3.30 |
| DE-LU | Selected combined | -13.76 | 114.33 / 63.87 | 11.80 | 142 / 0 | 232 / 0 | 3.30 |
| NO5 | Control | -31.70 | 30.71 / 79.81 | 14.92 | 25 / 608 | 43 / 0 | 4.52 |
| NO5 | Thermal curves | -31.79 | 30.71 / 83.43 | 15.44 | 25 / 601 | 43 / 0 | 4.51 |
| NO5 | Selected combined | -31.79 | 30.71 / 83.43 | 15.44 | 25 / 601 | 43 / 0 | 4.51 |

### All eligible evaluation areas

Each cell: overall **MAE / correlation / within-day correlation**. All 41 price
areas remain; unsupported observations stay unknown, never zero-filled.

| Area | Control | Thermal curves | Selected combined |
| --- | ---: | ---: | ---: |
| AL | 38.20 / 0.355 / 0.355 | 33.05 / 0.407 / 0.427 | 33.05 / 0.407 / 0.427 |
| AT | 22.82 / 0.693 / 0.655 | 18.31 / 0.728 / 0.690 | 18.31 / 0.728 / 0.690 |
| BE | 20.92 / 0.730 / 0.637 | 20.19 / 0.741 / 0.654 | 20.19 / 0.741 / 0.654 |
| BG | 32.58 / 0.563 / 0.505 | 28.05 / 0.650 / 0.607 | 28.05 / 0.650 / 0.607 |
| CH | 27.36 / 0.611 / 0.627 | 22.47 / 0.646 / 0.649 | 22.47 / 0.646 / 0.649 |
| CZ | 25.27 / 0.454 / 0.475 | 26.10 / 0.509 / 0.553 | 26.10 / 0.509 / 0.553 |
| DE-LU | 23.35 / 0.692 / 0.611 | 21.37 / 0.717 / 0.634 | 21.37 / 0.717 / 0.634 |
| DK1 | 26.53 / 0.636 / 0.535 | 25.53 / 0.657 / 0.556 | 25.53 / 0.657 / 0.556 |
| EE | 50.04 / 0.343 / 0.272 | 51.60 / 0.373 / 0.300 | 51.60 / 0.373 / 0.300 |
| ES | 22.55 / 0.688 / 0.718 | 20.57 / 0.745 / 0.761 | 20.57 / 0.745 / 0.761 |
| FR | 20.71 / 0.685 / 0.580 | 20.46 / 0.698 / 0.599 | 20.46 / 0.698 / 0.599 |
| GR | 33.28 / 0.487 / 0.447 | 28.62 / 0.626 / 0.598 | 28.62 / 0.626 / 0.598 |
| HR | 26.86 / 0.604 / 0.549 | 22.62 / 0.678 / 0.634 | 22.62 / 0.678 / 0.634 |
| HU | 30.43 / 0.605 / 0.557 | 26.14 / 0.658 / 0.624 | 26.14 / 0.658 / 0.624 |
| IT-CNOR | 34.30 / 0.530 / 0.513 | 28.50 / 0.618 / 0.587 | 28.50 / 0.618 / 0.587 |
| IT-CSUD | 36.77 / 0.510 / 0.501 | 31.41 / 0.579 / 0.560 | 31.41 / 0.579 / 0.560 |
| IT-North | 27.08 / 0.564 / 0.530 | 21.61 / 0.679 / 0.638 | 21.61 / 0.679 / 0.638 |
| IT-SICI | 38.35 / 0.527 / 0.535 | 33.03 / 0.581 / 0.585 | 33.03 / 0.581 / 0.585 |
| IT-SUD | 35.25 / 0.538 / 0.539 | 29.89 / 0.600 / 0.591 | 29.89 / 0.600 / 0.591 |
| LT | 44.81 / 0.395 / 0.317 | 45.49 / 0.427 / 0.344 | 45.49 / 0.427 / 0.344 |
| LV | 44.87 / 0.393 / 0.313 | 45.55 / 0.424 / 0.341 | 45.55 / 0.424 / 0.341 |
| MK | 30.94 / 0.560 / 0.507 | 26.87 / 0.635 / 0.594 | 26.87 / 0.635 / 0.594 |
| NL | 21.73 / 0.705 / 0.632 | 20.55 / 0.723 / 0.657 | 20.55 / 0.723 / 0.657 |
| PL | 27.02 / 0.585 / 0.537 | 22.37 / 0.622 / 0.569 | 22.37 / 0.622 / 0.569 |
| PT | 22.73 / 0.675 / 0.709 | 21.04 / 0.736 / 0.754 | 21.04 / 0.736 / 0.754 |
| RO | 31.59 / 0.583 / 0.524 | 27.06 / 0.659 / 0.616 | 27.06 / 0.659 / 0.616 |
| RS | 29.20 / 0.576 / 0.520 | 24.32 / 0.656 / 0.616 | 24.32 / 0.656 / 0.616 |
| SI | 26.32 / 0.565 / 0.511 | 22.12 / 0.651 / 0.601 | 22.12 / 0.651 / 0.601 |
| SK | 24.95 / 0.616 / 0.575 | 22.33 / 0.662 / 0.631 | 22.33 / 0.662 / 0.631 |
| DK2 | 56.30 / 0.073 / 0.056 | 56.37 / 0.082 / 0.067 | 56.37 / 0.082 / 0.067 |
| FI | 38.15 / -0.035 / -0.030 | 38.59 / -0.038 / -0.031 | 38.59 / -0.038 / -0.031 |
| NO1 | 40.53 / -0.216 / -0.250 | 41.27 / -0.231 / -0.262 | 41.27 / -0.231 / -0.262 |
| NO2 | 39.60 / 0.039 / -0.010 | 40.15 / 0.037 / -0.010 | 40.15 / 0.037 / -0.010 |
| NO3 | 27.56 / -0.099 / -0.186 | 28.34 / -0.098 / -0.192 | 28.34 / -0.098 / -0.192 |
| NO4 | 27.08 / 0.047 / -0.142 | 27.65 / 0.048 / -0.143 | 27.65 / 0.048 / -0.143 |
| NO5 | 43.67 / -0.371 / -0.413 | 44.71 / -0.378 / -0.432 | 44.71 / -0.378 / -0.432 |
| SE1 | 27.50 / 0.037 / -0.071 | 28.00 / 0.037 / -0.070 | 28.00 / 0.037 / -0.070 |
| SE2 | 27.69 / 0.053 / -0.045 | 28.16 / 0.054 / -0.045 | 28.16 / 0.054 / -0.045 |
| SE3 | 33.76 / 0.030 / -0.008 | 34.17 / 0.035 / -0.003 | 34.17 / 0.035 / -0.003 |
| SE4 | 42.15 / 0.131 / 0.070 | 42.37 / 0.139 / 0.079 | 42.37 / 0.139 / 0.079 |
| IT-SARD | 39.61 / 0.543 / 0.552 | 34.36 / 0.584 / 0.580 | 34.36 / 0.584 / 0.580 |

### Monthly performance

Each cell: **MAE / within-day correlation**. Fitting and selection months are
in-sample development evidence, not evaluation results.

| Month | Control | Thermal curves | Selected combined |
| --- | ---: | ---: | ---: |
| 2025-01 fit | 36.62 / 0.245 | 35.25 / 0.347 | 35.25 / 0.347 |
| 2025-02 fit | 43.46 / 0.283 | 41.53 / 0.427 | 41.53 / 0.427 |
| 2025-03 fit | 35.64 / 0.478 | 34.35 / 0.519 | 34.35 / 0.519 |
| 2025-04 fit | 29.77 / 0.545 | 29.23 / 0.559 | 29.23 / 0.559 |
| 2025-05 selection | 29.64 / 0.507 | 29.50 / 0.508 | 29.50 / 0.508 |
| 2025-06 selection | 31.09 / 0.511 | 30.36 / 0.531 | 30.36 / 0.531 |
| 2025-07 evaluation | 28.17 / 0.407 | 26.23 / 0.456 | 26.23 / 0.456 |
| 2025-08 evaluation | 30.39 / 0.492 | 29.13 / 0.517 | 29.13 / 0.517 |
| 2025-09 evaluation | 32.86 / 0.402 | 31.07 / 0.455 | 31.07 / 0.455 |
| 2025-10 evaluation | 35.64 / 0.331 | 32.95 / 0.389 | 32.95 / 0.389 |
| 2025-11 evaluation | 37.26 / 0.261 | 34.50 / 0.295 | 34.50 / 0.295 |
| 2025-12 evaluation | 29.10 / 0.279 | 26.51 / 0.317 | 26.51 / 0.317 |

### Generation checks

July–December TWh, national Ember references versus conditional saved-block
allocation intervals. Separate label extremes are not jointly attainable or all
possible primal optima. Retain gross/net/CHP/taxonomy/geographic source limits.
Implied exports are generation minus prepared demand, not verified bilateral flows.

| Country | Fuel | Ember | Control interval | Thermal interval | Selected interval |
| --- | --- | ---: | ---: | ---: | ---: |
| ES | Wind | 27.56 | 20.88–21.17 | 20.88–21.17 | 20.88–21.17 |
| ES | Solar | 30.86 | 32.75–33.04 | 32.75–33.04 | 32.75–33.04 |
| ES | Nuclear | 26.93 | 24.07–24.07 | 24.24–24.24 | 24.24–24.24 |
| ES | Gas | 29.66 | 28.49–28.49 | 30.18–30.18 | 30.18–30.18 |
| ES | Coal | 0.09 | 0.00–0.00 | 0.00–0.00 | 0.00–0.00 |
| FR | Wind | 25.66 | 30.34–30.34 | 30.34–30.34 | 30.34–30.34 |
| FR | Solar | 15.16 | 18.22–18.22 | 18.22–18.22 | 18.22–18.22 |
| FR | Nuclear | 190.52 | 180.18–180.18 | 179.74–179.74 | 179.74–179.74 |
| FR | Gas | 7.27 | 4.20–4.20 | 3.93–3.93 | 3.93–3.93 |
| FR | Coal | 0.66 | 0.00–0.00 | 0.06–0.06 | 0.06–0.06 |
| DE | Wind | 71.07 | 93.47–94.60 | 93.44–94.60 | 93.44–94.60 |
| DE | Solar | 40.17 | 48.52–49.65 | 48.50–49.66 | 48.50–49.66 |
| DE | Nuclear | 0.00 | 0.00–0.00 | 0.00–0.00 | 0.00–0.00 |
| DE | Gas | 38.53 | 18.50–18.50 | 25.79–25.79 | 25.79–25.79 |
| DE | Coal | 45.32 | 15.88–15.88 | 20.30–20.30 | 20.30–20.30 |

### Complete finite search

| Index | [offset strength, thermal strength, renewable discount] | Fitting score | May–June selection score |
| --- | --- | ---: | ---: |
| 0 | [0.0, 0.0, 0.0] | 1.00000 | 1.00000 |
| 1 | [0.0, 0.5, 0.0] | 0.90150 | 0.96857 |
| 2 | [0.0, 1.0, 0.0] | 0.91404 | Not shortlisted |
| 3 | [0.5, 0.0, 0.0] | 1.02809 | Not shortlisted |
| 4 | [0.5, 0.5, 0.0] | 0.91234 | 0.97207 |
| 5 | [0.5, 1.0, 0.0] | 0.92705 | Not shortlisted |
| 6 | [1.0, 0.0, 0.0] | 1.04469 | Not shortlisted |
| 7 | [1.0, 0.5, 0.0] | 0.93043 | Not shortlisted |
| 8 | [1.0, 1.0, 0.0] | 0.93315 | Not shortlisted |
| 9 | [0.0, 0.5, 10.0] | 0.90814 | 0.98101 |
| 10 | [0.0, 0.5, 30.0] | 0.95422 | 1.03187 |

### Verification, runtime and next decision

Seven targeted tests verify mixed-source capacity partitioning, renewable-only
negative offers, a known upper-block clearing price, daily level/shape separation,
missing days, material-negative counts, temporal input boundaries and selection.
Independent replay reconstructs original source membership/capacity and physical
columns, collapses all saved block dispatch to original components, verifies
physical balances/islands/HVDC/passive ratings and LP objectives/dual certificates.
It independently reconstructs proposal medians, fitting/selection scores and
shortlists, all price/shape metrics, quantity/trade bounds, source lag diagnostics,
residual cohorts, local DST profiles, headroom, monthly metrics and timing sets.

Completed LP certificates: **16**; maximum original
physical residual **6.7e-06 MW**, maximum duality gap **EUR0.00014**.
Unchanged numerical gates: 1e-4 MW / EUR0.05. Expanded-control versus previous
control differs in **126** modeled
area-hours above EUR0.0001/MWh (mean absolute difference
**0.00925 EUR/MWh**).
Equivalent feasible sets can have nonunique dual witnesses; use the fresh common
formulation control, not a claim of exact price identity across representations.
Annual emergency supply from verified witnesses and independently replayed
source group membership: Control 0.000000 MWh / 0 hours, Thermal curves 0.000000 MWh / 0 hours, Selected combined 0.000000 MWh / 0 hours.
No failed annual hour is filled with another formulation. Source membership
provenance and shortage totals are sealed in the presentation receipt.

Source preparation **112.63s**; complete fitting/selection/
annual evaluation/export **337.97s**. Annual clearing:
Control 29.71s, Thermal curves 38.92s, Selected combined 38.92s.
Aliases reuse one solve. Independent replay **154.81s**;
peak producer RSS **2589 MiB**. No forecast optimization prepass.

Reproduce with the pinned interpreter and single-thread BLAS/OMP: run
`tools/run_hourly_offer_curves_2025.py <fresh-root>`, then
`tools/audit_hourly_offer_curves_2025.py <root>` and
`tools/report_hourly_offer_curves_2025.py <root>`. Diagnostics use
`tools/diagnose_hourly_price_shape_2025.py <fresh-diagnostic-root>`; the retained
authoritative diagnostic is hourly-shape-diagnosis-v2. Completed roots and producer
hashes are immutable. Raw arrays and PNG/SVG charts stay ignored under
`data/bidding-zone-network-2025/hourly-offer-curves-v1/presentation-v3/`.

Assess price movements, price levels and generation together. This result does
not authorize a new baseline or investment/browser integration. Audit timestamp
conventions and operational availability separately before altering inputs;
do not improve price fit by silently shifting weather or manufacturing scarcity.
No CI/Pages deployment or public-URL verification is claimed for this local update.

## Zonal resource bids and two-block supply curves — 15 October 2026

**Result:** The training-selected two-stage result improves evaluation MAE by 0.33 EUR/MWh; mean zonal correlation changes by +0.004. This is a finite bid-shape experiment, not an accepted replacement.

The experiment keeps the complete European physical network, fixed demand,
original renewable/thermal availability and precomputed hydro unchanged. These
are generator **offer** adjustments; clearing prices still result from coupled
dispatch. The original annual-v7 baseline and browser remain unchanged.

### Evaluation summary

Same July–December 4416 hours, all 41 eligible observed price areas.
MAE is the equal-area mean in EUR/MWh; correlation is the mean zonal correlation.
Generation/trade columns are normalized monthly interval-distance errors, not
percentages or observed physical border-flow errors. Lower errors are better.

| Formulation | Price MAE | Mean r | Generation-range error | Trade-range error |
| --- | ---: | ---: | ---: | ---: |
| Control | 32.21 | 0.407 | 0.40928 | 0.22507 |
| Zonal offsets | 32.21 | 0.407 | 0.40928 | 0.22507 |
| Zonal blocks | 31.87 | 0.411 | 0.40589 | 0.22032 |

**Regional interpretation:** France's correlation improves
**0.685 → 0.744**, but MAE changes
**20.71 → 20.83 EUR/MWh** and signed bias
**+0.01 → +8.37 EUR/MWh**. Better timing
does not mean better price levels. Spain MAE changes
**22.55 → 22.70 EUR/MWh**. Nordic errors
remain substantial, including adverse areas below. The modest aggregate gain
does not establish an empirically accepted replacement.

The constant-offset proposals lowered training price error but worsened quantities
and trade. Their shared strength is selected as zero. That rejects the proposed
bundle under this score, not every individual zonal offset or joint offset/spread
combination. Each stage has one common strength across its regional proposal;
there is no exhaustive or per-zone numerical optimization. Correcting the level
and slope together would require a separately declared training-only experiment,
not a post-evaluation adjustment to this result.

The full-year saved dispatch, half-year negative-price/tail records and figures are
local under `data/bidding-zone-network-2025/zonal-bid-blocks-v2/`. The reproducible
PNG/SVG chart is in `presentation-v1/zonal-bid-blocks`; no ignored figure is linked
as a public asset. Hourly errors cannot be inferred from the seven-day mean plots.

### What changed

1. **Zonal offsets:** gas (CCGT/OCGT), coal/lignite and nuclear each receive a
   constant effective adjustment in each physically present zone/resource pair.
   Bounds are ±30/±30/±15 EUR/MWh electricity respectively. Original monthly
   fuel, efficiency, operational-carbon and variable-cost anchors remain in place.
2. **Bid shape:** partition each original thermal group's hourly available MW
   into 70% lower and 30% upper blocks. Both have the original physical column;
   only the upper bid adds a nonnegative spread, bounded by 60/60/30 EUR/MWh.
   Their sum cannot exceed original capacity. Renewables, oil, other resources,
   fixed hydro and emergency offers are unchanged. Offers have an explicit zero
   floor after adjustments; this does not introduce negative generator bids.

Stage one proposes offsets from median **training** observed-minus-model errors
on local interior-offer hours, shrinking by n/(n+168). A local offer must be more
than 0.001 MW from both bounds and within 1e-5 EUR/MWh of the local clearing price.
This is model marginal evidence, not unique real price-setting identification.
Unsupported zone/resource pairs receive zero adjustment, not fabricated evidence.

Stage two retains the training-selected offsets. It proposes an upper spread
from the difference in median training price residuals between ≥70% and <70%
resource utilization, on local-interior hours. Both cohorts require 24 hours;
shrink by min(n_low,n_high)/(min(n_low,n_high)+168), clip to nonnegative bounds.
This is a proposal heuristic, not a causal estimate of a true supply curve.

Each stage tests exactly strengths 0, 0.5 and 1 inside the **coupled** network
over all 4344 training hours. Repeated parameters reuse their witness. The score
equally averages control-normalized price MAE, country/fuel/month generation
allocation-interval error and implied net-export interval error. Add 0.05 times
mean squared bound-normalized offsets, plus the same penalty for spreads, across
physically present zone/resource pairs. These settings are declared experimental
choices, not empirical acceptance thresholds. Ties prefer smaller penalties then
earlier trials. This finite search does not optimize every regional parameter.

Design/proposals/selection are sealed before opening evaluation targets. Both
training-selected stages receive annual evaluation; evaluation never chooses
between them. 2025 has already been inspected: the chronological split is
**retrospective, not untouched validation**. No observed prices enter evaluation
bid construction. No new data collection, availability fitting or source correction.

### Complete training trace

Selected trial indices: offsets **0**, blocks
**4**. A zero upper-block choice is a result,
not an omitted formulation. Parameters are effective offers, not recovered orders.

| Trial | Nonzero offsets | Nonzero spreads | Price MAE | Generation error | Trade error | Penalty | Joint score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 34.26 | 0.33772 | 0.18349 | 0.00000 | 1.00000 |
| 1 | 65 | 0 | 33.10 | 0.37693 | 0.19643 | 0.00175 | 1.05261 |
| 2 | 65 | 0 | 32.25 | 0.38867 | 0.20257 | 0.00699 | 1.07236 |
| 3 | 0 | 21 | 34.13 | 0.33896 | 0.18337 | 0.00022 | 0.99995 |
| 4 | 0 | 21 | 34.10 | 0.33812 | 0.18217 | 0.00090 | 0.99734 |

### Every eligible evaluation area

Each cell: **MAE EUR/MWh / correlation / signed bias EUR/MWh**. Adverse regions
are retained; unavailable BA/GB/IE/ME observations are not replaced by zero.

| Area | Control | Zonal offsets | Zonal blocks |
| --- | ---: | ---: | ---: |
| AL | 38.20 / 0.355 / -30.56 | 38.20 / 0.355 / -30.56 | 37.52 / 0.362 / -29.50 |
| AT | 22.82 / 0.693 / -16.35 | 22.82 / 0.693 / -16.35 | 22.25 / 0.696 / -15.57 |
| BE | 20.92 / 0.730 / -13.26 | 20.92 / 0.730 / -13.26 | 18.43 / 0.754 / -8.49 |
| BG | 32.58 / 0.563 / -17.62 | 32.58 / 0.563 / -17.62 | 32.12 / 0.571 / -16.48 |
| CH | 27.36 / 0.611 / -24.20 | 27.36 / 0.611 / -24.20 | 26.15 / 0.619 / -22.82 |
| CZ | 25.27 / 0.454 / -3.67 | 25.27 / 0.454 / -3.67 | 24.88 / 0.461 / -2.89 |
| DE-LU | 23.35 / 0.692 / -17.90 | 23.35 / 0.692 / -17.90 | 22.61 / 0.694 / -16.47 |
| DK1 | 26.53 / 0.636 / -16.58 | 26.53 / 0.636 / -16.58 | 25.23 / 0.645 / -14.32 |
| EE | 50.04 / 0.343 / +9.04 | 50.04 / 0.343 / +9.04 | 50.37 / 0.344 / +10.66 |
| ES | 22.55 / 0.688 / +3.12 | 22.55 / 0.688 / +3.12 | 22.70 / 0.691 / +4.84 |
| FR | 20.71 / 0.685 / +0.01 | 20.71 / 0.685 / +0.01 | 20.83 / 0.744 / +8.37 |
| GR | 33.28 / 0.487 / -13.37 | 33.28 / 0.487 / -13.37 | 32.42 / 0.518 / -11.69 |
| HR | 26.86 / 0.604 / -15.48 | 26.86 / 0.604 / -15.48 | 26.51 / 0.603 / -14.43 |
| HU | 30.43 / 0.605 / -20.62 | 30.43 / 0.605 / -20.62 | 29.96 / 0.609 / -19.61 |
| IT-CNOR | 34.30 / 0.530 / -33.97 | 34.30 / 0.530 / -33.97 | 33.87 / 0.536 / -33.53 |
| IT-CSUD | 36.77 / 0.510 / -36.45 | 36.77 / 0.510 / -36.45 | 36.42 / 0.516 / -36.09 |
| IT-North | 27.08 / 0.564 / -26.50 | 27.08 / 0.564 / -26.50 | 26.65 / 0.565 / -26.02 |
| IT-SICI | 38.35 / 0.527 / -37.35 | 38.35 / 0.527 / -37.35 | 38.15 / 0.527 / -37.15 |
| IT-SUD | 35.25 / 0.538 / -34.39 | 35.25 / 0.538 / -34.39 | 34.89 / 0.545 / -34.03 |
| LT | 44.81 / 0.395 / -0.25 | 44.81 / 0.395 / -0.25 | 44.95 / 0.396 / +1.37 |
| LV | 44.87 / 0.393 / -0.28 | 44.87 / 0.393 / -0.28 | 45.01 / 0.393 / +1.34 |
| MK | 30.94 / 0.560 / -17.45 | 30.94 / 0.560 / -17.45 | 30.80 / 0.561 / -16.80 |
| NL | 21.73 / 0.705 / -15.53 | 21.73 / 0.705 / -15.53 | 20.26 / 0.708 / -12.71 |
| PL | 27.02 / 0.585 / -20.86 | 27.02 / 0.585 / -20.86 | 26.10 / 0.585 / -19.61 |
| PT | 22.73 / 0.675 / +3.83 | 22.73 / 0.675 / +3.83 | 22.80 / 0.680 / +5.16 |
| RO | 31.59 / 0.583 / -18.79 | 31.59 / 0.583 / -18.79 | 31.17 / 0.588 / -17.75 |
| RS | 29.20 / 0.576 / -18.46 | 29.20 / 0.576 / -18.46 | 28.78 / 0.580 / -17.51 |
| SI | 26.32 / 0.565 / -14.12 | 26.32 / 0.565 / -14.12 | 26.02 / 0.558 / -13.01 |
| SK | 24.95 / 0.616 / -12.01 | 24.95 / 0.616 / -12.01 | 24.57 / 0.619 / -11.01 |
| DK2 | 56.30 / 0.073 / -47.24 | 56.30 / 0.073 / -47.24 | 56.03 / 0.064 / -46.62 |
| FI | 38.15 / -0.035 / -9.62 | 38.15 / -0.035 / -9.62 | 38.45 / -0.042 / -9.11 |
| NO1 | 40.53 / -0.216 / -30.98 | 40.53 / -0.216 / -30.98 | 40.28 / -0.216 / -30.25 |
| NO2 | 39.60 / 0.039 / -30.84 | 39.60 / 0.039 / -30.84 | 38.61 / 0.043 / -29.43 |
| NO3 | 27.56 / -0.099 / -1.50 | 27.56 / -0.099 / -1.50 | 27.95 / -0.098 / -1.18 |
| NO4 | 27.08 / 0.047 / +16.89 | 27.08 / 0.047 / +16.89 | 27.51 / 0.045 / +17.37 |
| NO5 | 43.67 / -0.371 / -31.70 | 43.67 / -0.371 / -31.70 | 44.34 / -0.373 / -31.79 |
| SE1 | 27.50 / 0.037 / +10.85 | 27.50 / 0.037 / +10.85 | 27.90 / 0.031 / +11.35 |
| SE2 | 27.69 / 0.053 / +11.76 | 27.69 / 0.053 / +11.76 | 28.10 / 0.047 / +12.27 |
| SE3 | 33.76 / 0.030 / -14.52 | 33.76 / 0.030 / -14.52 | 33.87 / 0.025 / -13.91 |
| SE4 | 42.15 / 0.131 / -26.04 | 42.15 / 0.131 / -26.04 | 42.01 / 0.126 / -25.41 |
| IT-SARD | 39.62 / 0.543 / -38.21 | 39.62 / 0.543 / -38.21 | 39.33 / 0.546 / -37.88 |

### Monthly price performance

Independent replay calculates these equal-zone **MAE / mean correlation** pairs
from saved annual prices. January–June is in-sample; later months are retrospective
evaluation. Monthly correlation cannot be compared directly to half-year correlation.

| Month | Control | Zonal offsets | Zonal blocks |
| --- | ---: | ---: | ---: |
| 2025-01 (training) | 36.62 / 0.352 | 36.62 / 0.352 | 36.40 / 0.358 |
| 2025-02 (training) | 43.46 / 0.380 | 43.46 / 0.380 | 43.00 / 0.430 |
| 2025-03 (training) | 35.64 / 0.510 | 35.64 / 0.510 | 35.83 / 0.511 |
| 2025-04 (training) | 29.77 / 0.528 | 29.77 / 0.528 | 29.89 / 0.532 |
| 2025-05 (training) | 29.64 / 0.560 | 29.64 / 0.560 | 29.46 / 0.565 |
| 2025-06 (training) | 31.09 / 0.530 | 31.09 / 0.530 | 30.67 / 0.539 |
| 2025-07 (evaluation) | 28.17 / 0.416 | 28.17 / 0.416 | 27.74 / 0.421 |
| 2025-08 (evaluation) | 30.39 / 0.493 | 30.39 / 0.493 | 30.01 / 0.497 |
| 2025-09 (evaluation) | 32.86 / 0.421 | 32.86 / 0.421 | 32.47 / 0.431 |
| 2025-10 (evaluation) | 35.64 / 0.412 | 35.64 / 0.412 | 35.11 / 0.410 |
| 2025-11 (evaluation) | 37.26 / 0.263 | 37.26 / 0.263 | 37.23 / 0.262 |
| 2025-12 (evaluation) | 29.10 / 0.347 | 29.10 / 0.347 | 28.88 / 0.353 |

### France and Spain: generation checks

July–December TWh, conditional bounds given saved equal-bid group/block totals.
Separate label extremes need not be jointly attainable; these are not all
alternative primal optima. National Ember/gross-net/CHP/taxonomy differences and
implied generation-minus-demand trade limitations remain unchanged. Targets
outside available energy stay soft checks; bids cannot manufacture missing supply.

| Country | Fuel | Ember | Control interval | Zonal-offset interval | Zonal-block interval |
| --- | --- | ---: | ---: | ---: | ---: |
| FR | Wind | 25.66 | 30.34–30.34 | 30.34–30.34 | 30.34–30.34 |
| FR | Solar | 15.16 | 18.22–18.22 | 18.22–18.22 | 18.22–18.22 |
| FR | Nuclear | 190.52 | 180.18–180.18 | 180.18–180.18 | 175.85–175.85 |
| FR | Gas | 7.27 | 4.21–4.21 | 4.21–4.21 | 4.16–4.16 |
| FR | Coal | 0.66 | 0.00–0.00 | 0.00–0.00 | 0.00–0.00 |
| ES | Wind | 27.56 | 20.85–21.17 | 20.85–21.17 | 20.85–21.17 |
| ES | Solar | 30.86 | 32.75–33.07 | 32.75–33.07 | 32.75–33.07 |
| ES | Nuclear | 26.93 | 24.06–24.06 | 24.06–24.06 | 24.64–24.64 |
| ES | Gas | 29.66 | 28.49–28.49 | 28.49–28.49 | 28.39–28.39 |
| ES | Coal | 0.09 | 0.00–0.00 | 0.00–0.00 | 0.00–0.00 |

### Selected parameters and evidence coverage

Offsets belong to stage one; stage two keeps them. Spread cohorts use stage-one
dispatch, not observed generation. Entries with no supporting local hours remain
zero. Nuclear being cheaper in one zone is a synthetic fit, not demonstrated
physical cost differences. Interconnected zones can change through imports even
where no local bid changes. Fixed hydro has no calibrated marginal water offer.

| Zone | Resource | Offset evidence hours | Offset EUR/MWh | Spread low/high hours | Upper spread EUR/MWh |
| --- | --- | ---: | ---: | ---: | ---: |
| AT | gas | 365 | +0.00 | 263 / 102 | 2.45 |
| BA | coal/lignite | 0 | +0.00 | 0 / 0 | 0.00 |
| BE | gas | 225 | +0.00 | 190 / 35 | 1.98 |
| BE | nuclear | 170 | +0.00 | 122 / 48 | 8.96 |
| BG | gas | 115 | +0.00 | 80 / 35 | 0.00 |
| BG | coal/lignite | 20 | +0.00 | 20 / 0 | 0.00 |
| BG | nuclear | 66 | +0.00 | 44 / 22 | 0.00 |
| CH | gas | 4 | +0.00 | 3 / 1 | 0.00 |
| CH | nuclear | 65 | +0.00 | 35 / 30 | 0.00 |
| CZ | gas | 626 | +0.00 | 427 / 199 | 2.19 |
| CZ | coal/lignite | 1130 | +0.00 | 1105 / 25 | 2.83 |
| CZ | nuclear | 184 | +0.00 | 114 / 70 | 0.69 |
| DE-LU | gas | 285 | +0.00 | 285 / 0 | 0.00 |
| DE-LU | coal/lignite | 1310 | +0.00 | 1158 / 152 | 6.86 |
| DK1 | gas | 187 | +0.00 | 127 / 60 | 2.50 |
| DK1 | coal/lignite | 41 | +0.00 | 27 / 14 | 0.00 |
| EE | gas | 55 | +0.00 | 36 / 19 | 0.00 |
| ES | gas | 1720 | +0.00 | 1703 / 17 | 0.00 |
| ES | coal/lignite | 0 | +0.00 | 0 / 0 | 0.00 |
| ES | nuclear | 574 | +0.00 | 297 / 277 | 9.69 |
| FR | gas | 260 | +0.00 | 250 / 10 | 0.00 |
| FR | coal/lignite | 53 | +0.00 | 52 / 1 | 0.00 |
| FR | nuclear | 2491 | +0.00 | 915 / 1576 | 30.00 |
| GR | gas | 1464 | +0.00 | 957 / 507 | 5.10 |
| GR | coal/lignite | 4 | +0.00 | 1 / 3 | 0.00 |
| HR | gas | 187 | +0.00 | 129 / 58 | 0.00 |
| HR | coal/lignite | 7 | +0.00 | 4 / 3 | 0.00 |
| HU | gas | 333 | +0.00 | 228 / 105 | 0.57 |
| HU | coal/lignite | 0 | +0.00 | 0 / 0 | 0.00 |
| HU | nuclear | 52 | +0.00 | 36 / 16 | 0.00 |
| IT-CALA | gas | 0 | +0.00 | 0 / 0 | 0.00 |
| IT-CNOR | gas | 310 | +0.00 | 253 / 57 | 2.50 |
| IT-CSUD | gas | 815 | +0.00 | 702 / 113 | 8.78 |
| IT-North | gas | 1981 | +0.00 | 1958 / 23 | 0.00 |
| IT-SICI | gas | 3 | +0.00 | 3 / 0 | 0.00 |
| IT-SUD | gas | 892 | +0.00 | 654 / 238 | 9.35 |
| LT | gas | 345 | +0.00 | 205 / 140 | 9.66 |
| LV | gas | 309 | +0.00 | 180 / 129 | 10.75 |
| ME | coal/lignite | 0 | +0.00 | 0 / 0 | 0.00 |
| MK | gas | 51 | +0.00 | 39 / 12 | 0.00 |
| MK | coal/lignite | 29 | +0.00 | 21 / 8 | 0.00 |
| NL | gas | 308 | +0.00 | 308 / 0 | 0.00 |
| NL | coal/lignite | 210 | +0.00 | 147 / 63 | 0.00 |
| NL | nuclear | 12 | +0.00 | 9 / 3 | 0.00 |
| PL | gas | 1053 | +0.00 | 706 / 347 | 4.66 |
| PL | coal/lignite | 516 | +0.00 | 515 / 1 | 0.00 |
| PT | gas | 845 | +0.00 | 447 / 398 | 0.00 |
| RO | gas | 566 | +0.00 | 472 / 94 | 8.18 |
| RO | coal/lignite | 8 | +0.00 | 8 / 0 | 0.00 |
| RO | nuclear | 35 | +0.00 | 22 / 13 | 0.00 |
| RS | gas | 168 | +0.00 | 118 / 50 | 0.00 |
| RS | coal/lignite | 31 | +0.00 | 31 / 0 | 0.00 |
| SI | gas | 57 | +0.00 | 38 / 19 | 0.00 |
| SI | coal/lignite | 39 | +0.00 | 27 / 12 | 0.00 |
| SI | nuclear | 50 | +0.00 | 32 / 18 | 0.00 |
| SK | gas | 153 | +0.00 | 108 / 45 | 0.00 |
| SK | coal/lignite | 2 | +0.00 | 2 / 0 | 0.00 |
| SK | nuclear | 58 | +0.00 | 39 / 19 | 0.00 |
| XK | coal/lignite | 0 | +0.00 | 0 / 0 | 0.00 |
| DK2 | gas | 5 | +0.00 | 4 / 1 | 0.00 |
| FI | gas | 298 | +0.00 | 267 / 31 | 0.00 |
| FI | coal/lignite | 86 | +0.00 | 69 / 17 | 0.00 |
| FI | nuclear | 645 | +0.00 | 367 / 278 | 0.00 |
| NO4 | gas | 42 | +0.00 | 29 / 13 | 0.00 |
| NO5 | gas | 24 | +0.00 | 18 / 6 | 0.00 |
| SE1 | gas | 3 | +0.00 | 2 / 1 | 0.00 |
| SE3 | gas | 14 | +0.00 | 10 / 4 | 0.00 |
| SE3 | nuclear | 604 | +0.00 | 420 / 184 | 0.77 |
| SE4 | gas | 47 | +0.00 | 37 / 10 | 0.00 |
| FR-COR | gas | 0 | +0.00 | 0 / 0 | 0.00 |
| GB | gas | 0 | +0.00 | 0 / 0 | 0.00 |
| GB | nuclear | 0 | +0.00 | 0 / 0 | 0.00 |
| IE-SEM | gas | 0 | +0.00 | 0 / 0 | 0.00 |
| IE-SEM | coal/lignite | 0 | +0.00 | 0 / 0 | 0.00 |
| IT-SARD | gas | 764 | +0.00 | 675 / 89 | 6.21 |
| IT-SARD | coal/lignite | 710 | +0.00 | 393 / 317 | 0.00 |

### Verification, timing and interpretation

Six targeted tests pass for physical/capacity equivalence, zonal separation,
monotone bids, training-only input boundaries, unsupported evidence, selection
signed-zero cache equivalence and an analytical upper-block clearing example.
Independent replay reconstructs the original fleet, partitions capacity afresh,
collapses saved block output and checks native component balances, islands, HVDC
and passive-network ratings. It separately checks adjusted objectives and LP dual
certificates, proposal medians/counts/shrinkage, finite-stage selection, source
targets, all-area price metrics and monthly generation/trade interval errors.
Completed LP certificates **6**; maximum native
physical residual **7.05e-06 MW**, duality gap **EUR0.00033**. Numeric gates
remain 1e-4 MW / EUR0.05; feasibility is not evidence of empirical accuracy.

Reproduction uses the pinned Python interpreter and the retained source/cache
chain: `tools/run_zonal_bid_blocks_2025.py <fresh-output-root>`, followed by
`tools/audit_zonal_bid_blocks_2025.py <output-root>` and
`tools/report_zonal_bid_blocks_2025.py <output-root>`. The producer and auditor
have 5 GiB virtual-memory / 1800-second outer guards, and each hourly solver call
retains finite retry limits. Set OPENBLAS_NUM_THREADS, OMP_NUM_THREADS and
MKL_NUM_THREADS to 1. Completed roots are immutable; do not resume them with
changed code or coefficients. Source and parameter hashes are in each summary.

Source/grid preparation **76.37s**; complete fitting,
annual stage evaluation and export **243.69s**. Annual
clearing times: Control 43.14s, Zonal offsets 43.14s, Zonal blocks 34.09s.
Aliased stage witnesses reuse the same solve. Independent replay
**110.95s**; peak producer RSS **2586 MiB**.
Fresh zero-spread split-control maximum price difference from the frozen unsplit
control **107
EUR/MWh**; report comparisons use the fresh common-formulation control.
The difference exceeds EUR0.0001/MWh in
**116 of
420480 modeled area-hours**;
mean absolute difference **0.00703
EUR/MWh**. Maximum objective difference is
**EUR0.000035**.
The feasible set is equivalent by the block-collapse/capacity proof, but optimal
dual price witnesses need not be unique. No perfect price identity or improvement
from merely splitting bids is claimed; retain these outliers and the common control.

These are independent hourly clears grouped by day, not intertemporal daily
storage optimization. Fitting can absorb incorrect availability, demand or
commercial constraint assumptions; local-marginal evidence can be absent when
imports/constraints determine prices. The small finite proposal family does not
establish that all zonal bid models succeed or fail. Consider price shape,
generation, trade and adverse zones together before a separately declared next
experiment. No automatic baseline/investment acceptance or browser integration;
no live publication or CI/Pages claim for this local report update.

## Bounded fuel-anchored bid calibration — 15 October 2026

**Result:** The declared joint training criterion selects the unchanged bids. This bounded trial does not support a calibrated replacement.
Selected global adders [gas, coal/lignite, nuclear] are **[0.0, 0.0, 0.0]
EUR/MWh electricity**. July–December equal-zone MAE changes
**EUR32.21 → EUR32.21/MWh**;
mean zonal correlation **0.407 →
0.407**. The physical annual-v7 baseline
and browser remain unchanged; no calibrated candidate is promoted.

### Training-selected nonzero diagnostics

The primary score chose unchanged bids. Nuclear −15 improved all three raw
training metrics slightly, but not enough to offset the predeclared penalty.
Gas +30 had the lowest training price MAE among the visited nonzero tuples but
worsened generation agreement. Their annual diagnostics below were separately
declared and selected from training results only, before running their evaluation.
The primary weights/decision remain intact; no diagnostic is adopted because it
looks better on evaluation. This is exploratory follow-up, not an untouched test.

Control evaluation MAE: EU 32.21, France
20.71, Spain 22.55 EUR/MWh. Generation/trade columns use the same normalized
interval-error metrics. These three global offsets do not test country/seasonal
bid shapes or establish uniquely identifiable market offers.

| Diagnostic | Adders [gas, coal, nuclear] | EU MAE | Mean r | FR MAE | ES MAE | Generation error | Trade error |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Nuclear −15 | [0.0, 0.0, -15.0] | 32.29 | 0.411 | 21.11 | 22.51 | 0.40582 | 0.22100 |
| Gas +30 | [30.0, 0.0, 0.0] | 31.60 | 0.400 | 25.18 | 31.55 | 0.33320 | 0.16584 |

**Interpretation for France and Spain:** the gas uplift modestly reduces the
European average MAE but substantially worsens both countries. Their control
mean biases are already approximately +0.01 and +3.12 EUR/MWh, respectively;
a uniform upward price adjustment misses the hourly shape/timing problem.
The nuclear reduction offers no material joint price improvement there either.
This does not rule out bid calibration: it rejects promoting these particular
global-offset diagnostics. A next bid-focused experiment should test a few
transparent zonal or scarcity-dependent offer blocks, anchored to fuel costs,
with a fresh training-only design and the same network/quantity checks. It must
not widen this search or choose parameters after inspecting these evaluation data.

FR/ES generation intervals under the nonzero diagnostics, July–December TWh;
references and control intervals appear in the main quantity table below.

| Diagnostic | Country | Fuel | Allocation interval TWh |
| --- | --- | --- | ---: |
| Nuclear −15 | FR | Nuclear | 185.96–185.96 |
| Nuclear −15 | FR | Gas | 4.22–4.22 |
| Nuclear −15 | FR | Coal | 0.00–0.00 |
| Nuclear −15 | ES | Nuclear | 24.04–24.04 |
| Nuclear −15 | ES | Gas | 28.48–28.48 |
| Nuclear −15 | ES | Coal | 0.00–0.00 |
| Gas +30 | FR | Nuclear | 180.39–180.39 |
| Gas +30 | FR | Gas | 1.89–1.89 |
| Gas +30 | FR | Coal | 2.02–2.02 |
| Gas +30 | ES | Nuclear | 23.57–23.57 |
| Gas +30 | ES | Gas | 23.59–23.59 |
| Gas +30 | ES | Coal | 0.00–0.00 |

Source preparation for the diagnostics 107.38s; total
source/two-annual-solve/export command 203.05s. Per-probe
clearing times: Nuclear −15 52.97s, Gas +30 35.57s.
The full diagnostic design, code hashes and witnesses are in
`diagnostic-evaluation-v1/`; their training selectors and all outcomes are included
in the independent replay. The local figure shows these diagnostics alongside the
control rather than presenting zero fitted adders as a new predictor.

### What was fitted, and what stayed fixed

The user explicitly authorized historical **training** prices/generation to inform
effective synthetic bids inside the coupled European dispatch model. Each offer
retains its original fuel/efficiency, operational carbon and variable cost anchor,
plus one constant resource-level adder. Gas includes CCGT/OCGT; coal includes
hard coal/lignite. Renewable, oil, other-resource and emergency bids are unchanged.
There is no fitted hourly price curve, renewable scaling, new supply block,
country-specific markup or hydro rescheduling in this first trial.

Training: January–June, 4344 UTC hours. Evaluation: July–December, 4416 hours,
without refitting or selecting parameters using evaluation outcomes. All eligible
A44 price areas enter the comparison. 2025 was already inspected, so this is
**retrospective temporal evaluation, not untouched validation**. Future bid anchors
use the same realized fuel inputs; this does not establish operational forecasting.

Demand, original generator availability, fixed reservoir output, physical PTDFs,
GSKs, electrical islands and controllable-link bounds/efficiencies remain identical.
All economic dispatch changes therefore follow from changed bids within the same
modeled constraints. Those constraints remain model-derived, not certified JAO
commercial domains; fitted costs may compensate for their inaccuracies.

### Declared search and joint objective

Finite levels: gas and coal/lignite −30/0/+30 EUR/MWh; nuclear −15/0/+15 EUR/MWh.
Exactly two coordinate sweeps in gas/coal/nuclear order, caching repeated tuples.
7 distinct training tuples were visited; the
unchanged bids remain selectable. Ties within 1e-12 prefer smaller normalized
adders, then lexicographic order. The selection manifest is sealed before creating
the evaluation-target artifact. No bounds, split or weights change after results.
This is a bounded coordinate experiment, not globally optimal inverse clearing
or unique recovery of historical market offers.

The objective averages three training errors, each divided by its control value:

1. Equal-zone price MAE across every eligible observed area.
2. Mean country/fuel/month distance from the feasible **saved-group allocation
   interval**, divided by max(reference generation, 0.25 TWh). Fit Wind, Solar,
   Nuclear, Gas and Coal, excluding hydro/waste accounting proxies from this term.
3. Mean country/month distance from the implied net-export allocation interval,
   divided by max(model monthly demand, 1 TWh). Source net exports negate Ember
   Net imports; these are not verified physical/bilateral border flows.

Add a regularization penalty of 0.05 times the mean squared bid adjustments divided
by their respective bounds. These weights, floors and bounds are experimental
settings, not empirical acceptance thresholds. Missing observations stay unknown;
known country/fuel/month rows have equal weight within the quantity term, so
coverage affects its composition. Generation intervals are marginal/conditional,
not jointly attainable extremes or a search over all primal optima.

Of 810 known generation
training targets, 190
exceed their original available-energy envelope by more than 0.001 TWh. They remain
soft diagnostic targets, not imposed equalities or silently discarded hours.
Their summed positive envelope excess is
37.92 TWh. No bid can manufacture
missing available energy; source fleet/weather/scope inconsistencies remain open.

| Period | Price MAE control → fit | Mean correlation control → fit | Generation-range error control → fit | Trade-range error control → fit |
| --- | ---: | ---: | ---: | ---: |
| training | 34.26 → 34.26 | 0.574 → 0.574 | 0.33761 → 0.33761 | 0.18363 → 0.18363 |
| evaluation | 32.21 → 32.21 | 0.407 → 0.407 | 0.40938 → 0.40938 | 0.22539 → 0.22539 |

Quantity/trade errors are the normalized monthly metrics above, not percentages
of total European energy or causal shares. Read them separately: a joint objective
does not guarantee every error component or country improves.

### France and Spain: prices and generation together

The local `bid-calibration` PNG/SVG shows the training trace, evaluation error
ratios, and FR/ES seven-day evaluation price means. The following half-year
generation ranges retain the equal-price allocation uncertainty and accounting
caveats from the preceding quantity audit. All values are TWh, July–December.

| Country | Fuel | Ember | Control allocation range | Calibrated allocation range |
| --- | --- | ---: | ---: | ---: |
| FR | Wind | 25.66 | 30.34–30.34 | 30.34–30.34 |
| FR | Solar | 15.16 | 18.22–18.22 | 18.22–18.22 |
| FR | Nuclear | 190.52 | 180.18–180.18 | 180.18–180.18 |
| FR | Gas | 7.27 | 4.23–4.23 | 4.23–4.23 |
| FR | Coal | 0.66 | 0.00–0.00 | 0.00–0.00 |
| ES | Wind | 27.56 | 20.85–21.17 | 20.85–21.17 |
| ES | Solar | 30.86 | 32.75–33.07 | 32.75–33.07 |
| ES | Nuclear | 26.93 | 24.07–24.07 | 24.07–24.07 |
| ES | Gas | 29.66 | 28.47–28.47 | 28.47–28.47 |
| ES | Coal | 0.09 | 0.00–0.00 | 0.00–0.00 |

### All eligible evaluation price areas

Control MAE is EUR/MWh; each diagnostic cell is MAE / correlation. All eligible
areas, including adverse regions, are retained. Complete bias/RMSE/tail metrics
remain in each local outcome record. These are retrospective evaluation results,
not an evaluation-driven winner selection.

| Area | Control MAE | Nuclear −15 MAE / r | Gas +30 MAE / r |
| --- | ---: | ---: | ---: |
| AL | 38.20 | 38.68 / 0.337 | 32.60 / 0.300 |
| AT | 22.82 | 22.60 / 0.691 | 20.04 / 0.686 |
| BE | 20.92 | 22.41 / 0.728 | 21.17 / 0.722 |
| BG | 32.58 | 31.96 / 0.558 | 33.72 / 0.518 |
| CH | 27.36 | 28.01 / 0.626 | 18.54 / 0.655 |
| CZ | 25.27 | 24.92 / 0.467 | 32.12 / 0.482 |
| DE-LU | 23.35 | 23.81 / 0.690 | 21.29 / 0.711 |
| DK1 | 26.53 | 27.37 / 0.629 | 25.81 / 0.656 |
| EE | 50.04 | 49.83 / 0.334 | 55.29 / 0.321 |
| ES | 22.55 | 22.51 / 0.687 | 31.55 / 0.693 |
| FR | 20.71 | 21.11 / 0.697 | 25.18 / 0.698 |
| GR | 33.28 | 32.67 / 0.489 | 35.53 / 0.492 |
| HR | 26.86 | 26.34 / 0.605 | 28.24 / 0.562 |
| HU | 30.43 | 29.99 / 0.597 | 29.27 / 0.580 |
| IT-CNOR | 34.30 | 34.77 / 0.530 | 20.84 / 0.526 |
| IT-CSUD | 36.77 | 36.95 / 0.510 | 23.41 / 0.514 |
| IT-North | 27.08 | 28.04 / 0.552 | 15.96 / 0.534 |
| IT-SICI | 38.35 | 38.47 / 0.527 | 23.92 / 0.528 |
| IT-SUD | 35.25 | 35.40 / 0.539 | 22.54 / 0.542 |
| LT | 44.81 | 44.59 / 0.387 | 48.71 / 0.378 |
| LV | 44.87 | 44.67 / 0.385 | 48.76 / 0.375 |
| MK | 30.94 | 30.53 / 0.557 | 31.75 / 0.505 |
| NL | 21.73 | 22.72 / 0.700 | 21.19 / 0.707 |
| PL | 27.02 | 27.13 / 0.575 | 22.93 / 0.574 |
| PT | 22.73 | 22.84 / 0.674 | 33.09 / 0.680 |
| RO | 31.59 | 31.02 / 0.577 | 32.37 / 0.535 |
| RS | 29.20 | 28.83 / 0.570 | 30.18 / 0.513 |
| SI | 26.32 | 25.71 / 0.577 | 28.86 / 0.521 |
| SK | 24.95 | 24.51 / 0.608 | 26.46 / 0.602 |
| DK2 | 56.30 | 60.59 / 0.073 | 56.53 / 0.079 |
| FI | 38.15 | 38.05 / -0.033 | 39.84 / -0.039 |
| NO1 | 40.53 | 42.82 / -0.185 | 42.29 / -0.213 |
| NO2 | 39.60 | 44.04 / 0.051 | 42.21 / 0.064 |
| NO3 | 27.56 | 25.29 / -0.053 | 30.56 / -0.087 |
| NO4 | 27.08 | 22.17 / 0.090 | 29.13 / 0.063 |
| NO5 | 43.67 | 43.01 / -0.355 | 47.83 / -0.376 |
| SE1 | 27.50 | 24.02 / 0.064 | 29.45 / 0.044 |
| SE2 | 27.69 | 24.19 / 0.076 | 29.60 / 0.060 |
| SE3 | 33.76 | 36.52 / 0.034 | 35.37 / 0.031 |
| SE4 | 42.15 | 45.33 / 0.129 | 43.06 / 0.136 |
| IT-SARD | 39.64 | 39.68 / 0.543 | 28.58 / 0.543 |

### Complete training trace

Adders are [gas, coal/lignite, nuclear], EUR/MWh. Generation/trade columns use the
declared relative interval-error metrics. Failed trials are ineligible, not filled
from another case. Each tuple is a controlled training probe, not a separately
accepted annual model or a restarted retired search.

| Trial | Adders | Joint score | Price MAE | Generation error | Trade error |
| --- | --- | ---: | ---: | ---: | ---: |
| 0 | [0.0, 0.0, 0.0] | 1.00000 | 34.26 | 0.33761 | 0.18363 |
| 1 | [-30.0, 0.0, 0.0] | 1.21087 | 41.53 | 0.40618 | 0.21438 |
| 2 | [30.0, 0.0, 0.0] | 1.01112 | 33.96 | 0.35136 | 0.17472 |
| 3 | [0.0, -30.0, 0.0] | 1.03008 | 35.84 | 0.35271 | 0.17436 |
| 4 | [0.0, 30.0, 0.0] | 1.12068 | 34.12 | 0.39449 | 0.21077 |
| 5 | [0.0, 0.0, -15.0] | 1.00896 | 34.06 | 0.33513 | 0.18183 |
| 6 | [0.0, 0.0, 15.0] | 1.02661 | 34.81 | 0.34028 | 0.18472 |

### Verification, runtime and interpretation

Fresh ignored root `data/bidding-zone-network-2025/bid-calibration-v1/` contains
the predeclared design, source/code hashes, training targets, every training
primal/dual witness, sealed selection, subsequent evaluation targets and the
control/selected annual witnesses. Four fixtures check resource-only changes,
chronological target separation, joint-error tradeoffs and deterministic selection.
Independent `audit_bid_calibration_2025.py` rebuilds unchanged inputs, replays
9 complete primal/dual LP certificates, objective
values, generation/trade intervals, raw training losses, every coordinate choice,
and all temporal MAE/bias/RMSE/correlation and quantity tables. Failed training
trials: 0. Numeric feasibility and dual tolerances are
unchanged; no source or acceptance gate is relaxed.

Source/target preparation 213.44s; control annual clearing
42.65s; selected annual clearing
42.65s (uses control if unchanged); complete bounded
fit/evaluation/export command 389.66s. Independent replay
173.62s. Offline fitting includes repeated training solves;
it is not the runtime of one annual scenario. Fresh-control maximum price
difference from the legacy saved baseline is
0 EUR/MWh.

Effective adders are not observed generator margins, uniquely identified bids or
proof of realistic constraint data. A parameter at its bound calls for a separately
declared future sensitivity, not widening the search after inspecting evaluation.
Do not adopt a different training tuple based on the evaluation tables. Keep the
current physical baseline; empirical thresholds, matched investment scenarios and
supported app integration remain separate gates. This report update is local;
no CI/Pages/live-publication claim follows. Full arrays and figures stay ignored.

## Dispatch generation mix, demand and trade — 15 October 2026

**This compares actual saved dispatch quantities with observations**, rather than
comparing available supply with generated energy. The retained annual-v7 baseline
is unchanged. All 34 source countries are included; 33
have twelve-month Ember total-generation references. ENTSO-E provides
211 country/technology comparisons with some known hours, of which
122 have all 8760 hours. Coverage does not certify whole-fleet scope.

The largest ranked core-fuel discrepancy that cannot be removed by changing only
the within-group allocation is **GB Gas**:
model 20.51 TWh, conditional range
[20.51, 20.51], versus
Ember 90.58 TWh. This flags a quantity mismatch, not an estimate
of missing installed capacity or a causal share of price error.

**What this changes in the diagnosis:** Germany's total generation differs by
only 2.19 TWh, but wind is
+41.04 and gas
-56.49 TWh. Matching total generation is not
matching the supply mix. Germany and the UK comparison also have demand differences
of -31.19 and -59.38 TWh: reconcile national
load boundaries before interpreting all generation errors as supply problems.
Italy's generation difference -20.29 TWh nearly
matches its demand difference -20.35 TWh, while implied net exports
differ by only +0.07 TWh.

In Poland, demand is much closer (-0.61 TWh), but model implied
net imports are 41.91 TWh versus
1.02 reported, alongside coal generation
-55.25 TWh below the reference. This motivates
separate supply-cost, commitment and network/trade tests; it does not identify
which mechanism caused the error. DE/GB wind excess and ES/PT wind deficits also
argue against a uniform European wind multiplier.

Spain's modeled wind availability integrates to 44.42
TWh, versus 55.58 TWh reported generation;
Portugal's figures are 6.51 versus
13.48 TWh. Even the available envelope is below
reported generation, so dispatch/bid changes alone cannot close those gaps with
the current inputs and boundaries. Audit fleet/capacity, weather normalization and
reporting scope first; do not substitute observed generation for availability.

### Equal-price dispatch is not a unique technology mix

The solver combines offers with identical annual bid sequences and balance columns.
Wind, solar and run-of-river can consequently share a zero-price offer. Its saved
output does not uniquely identify which of those technologies generated it.

For every retained group with output q, total available MW A and a selected
technology/country subset with available MW a, feasible subset generation lies
between max(0, q − (A − a)) and min(q, a). The illustrative point q × a/A preserves
the group's dispatch, cost and caps. Country and Ember-fuel bounds are computed
after aggregating source capacities to those labels, **not** by summing individual
technology bounds. Bounds for different labels need not be jointly attainable.
Fixed reservoir output is added exactly and remains separate from available MW.

These ranges are conditional on the retained aggregate offer outputs. They do not
explore other primal optima or rerun dispatch. Source-country placements within
shared zones, especially DE/LU and IE/GB, remain conditional under the zonal GSK
formulation. A point mix is not a uniquely predicted physical plant dispatch.

### Sources, calendar and accounting

- **Model:** annual-v7, all 8760 optimal UTC hours; source fleet, fixed hydro,
  original availability and bid profiles reconstructed; saved network physics replayed.
- **ENTSO-E:** cached A75/A16 production by PSR type, freshly replayed from raw
  intervals and integrated to hourly MWh. B19 is onshore wind; B18 offshore.
  Missing types and hours remain unknown. Country aggregates require every
  constituent zone. Germany's generation domain excludes Luxembourg and is compared
  with source-country DE; it is not treated as DE-LU or Luxembourg production.
- **Ember:** cached current-release national 2025 monthly generation, total demand
  and Net imports, with source receipt/hash. Annual references require all twelve
  months; explicit reported zeros remain zeros. Ember may share ENTSO-E upstream
  observations and is not necessarily an independent measurement.
- **Storage:** model battery/PHS dispatch is absent. Observed B10 pumped discharge
  and B25 storage discharge are kept separately, never added to primary generation.
  Ember Hydro/storage, gross/net generation, own use, charging and demand scope
  remain unreconciled. Bioenergy uses modeled biomass; all modeled waste is grouped
  with Other fossil as an explicit accounting proxy, not a verified biogenic split.
  Other renewables includes modeled geothermal but lacks some reported categories.

Incomplete national hourly geography: AL: AL; BA: BA; GB: GB, IE-SEM; IE: IE-SEM; IT: IT-CALA, IT-SICI; LU: no matching national domain; ME: ME; NO: NO5; XK: XK. Italy's missing IT-CALA/IT-SICI
and Norway's missing NO5 are not replaced by zero or partial-country annual totals.
ENTSO-E reported-primary totals cover only source-reported types; they are not
certified complete national generation. Ember country totals provide broader
comparisons where complete, with their accounting limitations retained.
For example, German gas generation is 60.55
TWh in the 8760-hour ENTSO-E PSR series but 79.33 TWh
in Ember. The model is below both, but their difference needs reporting-scope,
CHP/autoproduction and gross/net reconciliation; complete hours alone do not prove
complete fleet coverage. Reservoir versus run-of-river classification also needs
reconciliation before interpreting a PSR-subtype difference as missing water.

### Annual production, demand and implied trade

All values are TWh; differences are model minus Ember. The model generation point
uses the illustrative tie split, with its conditional allocation range in brackets.
Implied model net exports = primary generation − prepared demand. Ember exports
negate its signed Net imports. This is **not** independently validated hourly
branch flow or bilateral trade; storage/loss/demand conventions can differ.
Generation differences must be read alongside demand and trade differences.

| Country | Model generation [range] | Ember generation | Generation difference | Demand difference | Implied net-export difference |
| --- | ---: | ---: | ---: | ---: | ---: |
| AL | 5.13 [5.13, 5.13] | Unknown | Unknown | Unknown | Unknown |
| AT | 73.48 [73.48, 73.48] | 65.38 | 8.10 | -11.34 | 19.44 |
| BA | 5.16 [5.16, 5.16] | 11.41 | -6.25 | -0.74 | -5.51 |
| BE | 71.88 [71.88, 71.88] | 68.08 | 3.80 | -1.80 | 5.60 |
| BG | 31.78 [31.78, 31.78] | 36.49 | -4.71 | 2.72 | -7.43 |
| CH | 67.53 [67.53, 67.53] | 67.69 | -0.17 | -7.88 | 7.71 |
| CZ | 51.73 [51.73, 51.73] | 70.40 | -18.67 | -0.28 | -18.39 |
| DE | 480.89 [480.86, 481.05] | 478.70 | 2.19 | -31.19 | 33.37 |
| DK | 51.85 [51.85, 51.85] | 33.77 | 18.08 | -2.75 | 20.83 |
| EE | 4.16 [4.16, 4.16] | 4.82 | -0.66 | 0.10 | -0.76 |
| ES | 225.42 [225.42, 225.42] | 256.22 | -30.80 | -8.97 | -21.83 |
| FI | 79.02 [79.02, 79.02] | 80.41 | -1.39 | -1.35 | -0.03 |
| FR | 511.15 [511.15, 511.15] | 526.67 | -15.52 | 0.10 | -15.62 |
| GB | 248.42 [248.10, 248.56] | 277.12 | -28.70 | -59.38 | 30.69 |
| GR | 69.26 [69.26, 69.26] | 50.11 | 19.15 | 2.49 | 16.66 |
| HR | 13.88 [13.88, 13.88] | 12.96 | 0.91 | -0.61 | 1.52 |
| HU | 42.75 [42.75, 42.75] | 37.71 | 5.04 | -3.64 | 8.69 |
| IE | 32.92 [32.77, 33.24] | 28.92 | 4.00 | -0.07 | 4.07 |
| IT | 230.29 [230.29, 230.29] | 250.58 | -20.29 | -20.35 | 0.07 |
| LT | 13.13 [13.13, 13.13] | 8.54 | 4.58 | -1.48 | 6.06 |
| LU | 1.29 [1.13, 1.32] | 1.35 | -0.07 | 0.00 | -0.06 |
| LV | 8.08 [8.08, 8.08] | 5.79 | 2.29 | 0.01 | 2.28 |
| ME | 1.40 [1.40, 1.40] | 2.17 | -0.77 | -1.18 | 0.42 |
| MK | 3.74 [3.74, 3.74] | 6.17 | -2.42 | -1.77 | -0.65 |
| NL | 101.08 [101.08, 101.08] | 137.39 | -36.31 | -6.49 | -29.82 |
| NO | 155.50 [155.50, 155.50] | 157.00 | -1.50 | 2.50 | -4.00 |
| PL | 116.44 [116.44, 116.44] | 157.94 | -41.50 | -0.61 | -40.89 |
| PT | 45.10 [45.10, 45.10] | 45.33 | -0.23 | -1.49 | 1.26 |
| RO | 51.82 [51.82, 51.82] | 50.31 | 1.50 | -0.47 | 1.97 |
| RS | 12.99 [12.99, 12.99] | 33.41 | -20.42 | -0.91 | -19.51 |
| SE | 156.91 [156.91, 156.91] | 162.01 | -5.10 | 1.16 | -6.26 |
| SI | 12.22 [12.22, 12.22] | 13.69 | -1.47 | -0.67 | -0.80 |
| SK | 31.67 [31.67, 31.67] | 28.39 | 3.28 | -0.11 | 3.40 |
| XK | 0.25 [0.25, 0.25] | 5.86 | -5.61 | -0.68 | -4.93 |

### Annual generation differences by technology

TWh, model illustrative allocation minus Ember. Unknown means incomplete reference,
not zero. Hydro comparisons retain the pumped-storage boundary caveat. The local
`generation-mix` PNG/SVG includes a full-country heatmap and monthly FR nuclear /
ES wind examples; `generation-shares` shows DE/FR/ES/NO composition. Share errors
and absolute TWh errors are distinct: normalization can hide a wrong total.
Figures are in the fresh `presentation-v2/` subdirectory. Missing component shares
remain unknown; charts show known shares and any unallocated total separately,
rather than treating an unreported fuel as verified zero.

| Country | Wind | Solar | Hydro | Nuclear | Gas | Coal |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| AL | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown |
| AT | -4.24 | 1.90 | -3.34 | Unknown | 14.64 | 0.00 |
| BA | -0.08 | 0.37 | 0.31 | Unknown | Unknown | -6.85 |
| BE | 8.18 | 1.17 | -0.01 | 4.23 | -6.24 | -0.05 |
| BG | -0.56 | 0.82 | 0.02 | 0.21 | 1.83 | -6.88 |
| CH | -0.11 | 3.54 | -6.56 | 4.19 | Unknown | Unknown |
| CZ | -0.15 | 0.19 | 0.02 | -1.63 | 6.77 | -18.61 |
| DE | 41.04 | 18.24 | 2.40 | 0.00 | -56.49 | -19.76 |
| DK | 9.82 | 0.12 | -0.01 | Unknown | 0.91 | -0.77 |
| EE | 0.63 | -0.23 | -0.01 | Unknown | 0.69 | Unknown |
| ES | -11.47 | 3.59 | -5.87 | -5.82 | -9.34 | -1.31 |
| FI | -4.43 | 0.27 | 0.01 | -15.05 | 1.91 | 0.39 |
| FR | 7.57 | 6.76 | 6.70 | -26.60 | -8.58 | 0.36 |
| GB | 42.70 | 3.02 | -0.43 | -2.69 | -70.07 | 0.00 |
| GR | -2.36 | 2.92 | 0.81 | Unknown | 20.52 | -2.73 |
| HR | -1.97 | 0.07 | 0.50 | Unknown | 2.81 | 0.14 |
| HU | -0.17 | -1.06 | -0.05 | 0.14 | 7.05 | -1.54 |
| IE | 2.92 | 0.83 | 0.12 | Unknown | 1.26 | -0.78 |
| IT | -8.62 | 7.81 | -1.31 | Unknown | -5.20 | -1.31 |
| LT | 0.77 | 1.20 | 0.08 | Unknown | 2.70 | Unknown |
| LU | -0.03 | 0.30 | -0.07 | Unknown | -0.06 | Unknown |
| LV | 0.10 | 0.06 | -0.12 | Unknown | 2.45 | Unknown |
| ME | -0.26 | -0.04 | 0.06 | Unknown | Unknown | -0.52 |
| MK | -0.26 | -0.03 | -0.23 | 0.00 | 0.16 | -2.02 |
| NL | 12.64 | -4.00 | -0.02 | -0.83 | -40.66 | -3.44 |
| NO | -5.08 | 0.68 | 4.52 | Unknown | -0.82 | Unknown |
| PL | 1.07 | 6.41 | 0.45 | Unknown | 11.53 | -55.25 |
| PT | -7.22 | 0.20 | -3.88 | Unknown | 10.16 | 0.00 |
| RO | -2.78 | 1.05 | 2.08 | 0.34 | 6.93 | -5.95 |
| RS | -0.74 | Unknown | 0.24 | Unknown | 1.71 | -21.89 |
| SE | -4.18 | 0.85 | -8.19 | -13.61 | 0.27 | Unknown |
| SI | -0.01 | 0.44 | -0.44 | -0.04 | 0.11 | -1.39 |
| SK | -0.00 | 0.46 | 0.93 | 2.13 | 1.91 | 0.44 |
| XK | -0.33 | Unknown | -0.07 | Unknown | Unknown | -5.24 |

### Largest core-fuel gaps beyond within-group allocation

Sorted by distance of the twelve-month reference from the conditional allocation
range; hydro and waste/bioenergy proxies are excluded from this ranking. All other
countries/fuels remain in the data. “Outside range” means the mismatch cannot be
removed solely by redistributing the saved group outputs between equal-price
members. It does not distinguish fleet/weather, bid, demand, trade or reporting error.
Available energy is original available MW integrated over the year, **not dispatch**;
it ignores delivery and commitment. Where available energy exceeds reported
generation but dispatch is low, an annual capacity shortage alone is not an
explanation. Hourly timing, bids, imports, demand or other constraints may still matter.

| Country | Technology | Available TWh | Model TWh [range] | Ember TWh | Point difference | Outside range TWh |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| GB | Gas | 311.17 | 20.51 [20.51, 20.51] | 90.58 | -70.07 | 70.07 |
| DE | Gas | 323.21 | 22.84 [22.84, 22.84] | 79.33 | -56.49 | 56.49 |
| PL | Coal | 186.51 | 27.57 [27.57, 27.57] | 82.81 | -55.25 | 55.25 |
| GB | Wind | 130.41 | 128.56 [127.59, 130.05] | 85.86 | 42.70 | 41.73 |
| NL | Gas | 124.38 | 6.94 [6.94, 6.94] | 47.60 | -40.66 | 40.66 |
| DE | Wind | 174.68 | 172.20 [169.32, 174.46] | 131.17 | 41.04 | 38.15 |
| FR | Nuclear | 411.44 | 345.09 [345.09, 345.09] | 371.69 | -26.60 | 26.60 |
| RS | Coal | 42.20 | 0.01 [0.01, 0.01] | 21.90 | -21.89 | 21.89 |
| GR | Gas | 73.90 | 43.41 [43.41, 43.41] | 22.89 | 20.52 | 20.52 |
| DE | Coal | 348.73 | 75.10 [75.10, 75.10] | 94.86 | -19.76 | 19.76 |
| CZ | Coal | 83.35 | 5.11 [5.11, 5.11] | 23.72 | -18.61 | 18.61 |
| DE | Solar | 111.69 | 108.20 [105.88, 111.13] | 89.97 | 18.24 | 15.91 |

### Hourly timing and monthly quantities

The full local comparison contains monthly totals and matched-hour bias, MAE, RMSE,
correlation and allocation-range exceedances for every available country/type.
Monthly and annual ENTSO-E sums use only their known hours; a partial sum is not
annualized. The examples below show matched-hour TWh and MW MAE. Correlation may
be unknown for constant or unavailable series. Point timing metrics inherit the
declared allocation rule; interval exceedances help identify robust discrepancies.

| Country | PSR technology | Known hours | Model matched TWh | Observed matched TWh | MAE MW | Correlation |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| FR | nuclear | 8754 | 344.83 | 371.40 | 6563.75 | 0.694 |
| DE | gas | 8760 | 22.84 | 60.55 | 5144.78 | 0.542 |
| ES | onshore_wind | 8723 | 43.85 | 55.45 | 2010.72 | 0.891 |
| PT | onshore_wind | 8760 | 6.20 | 13.42 | 836.09 | 0.853 |
| SE | reservoir | 8760 | 50.18 | 68.42 | 3637.24 | 0.453 |

### Verification and next action

Four fixtures verify sharp marginal bounds and regrouping, zero availability,
emergency exclusion, missing hours and missing constituent zones, and B18/B19
identity. Independent `audit_dispatch_mix_2025.py` rebuilds source columns and
saved dispatch, checks proportional allocations and conditional bounds, rereads
PSR observations and Ember records, and replays monthly/annual quantities,
hourly metrics, shares, demand and implied trade. All 34 countries /
306 annual fuel rows pass. Maximum allocation
difference 0 MW; native-component residual
9.76e-06 MW; global generation-demand-link-loss
closure 2.81e-07 MW, below 1e-4 MW.

Fresh ignored root `data/bidding-zone-network-2025/generation-mix-v1/` contains
the declared design, raw-observation replay, source/code hashes, full monthly /
hourly metrics, quantities and figures. Producer `compare_dispatch_mix_2025.py`
plus helper `generation_mix_2025.py` takes 342.26s including
source reconstruction and raw observation replay; independent audit
106.58s. No new clearing was run; these are audit timings.

Prioritize national demand-scope reconciliation, regional wind fleet/weather inputs,
then source-backed outage timing and separate bid/network/trade controls. In
particular, cheap supply and imports displacing thermal generation warrant a joint
quantity/price check before adding generic bid steps or raising fuel prices.
A reference outside
modeled availability flags input/scope issues; sufficient availability but different
dispatch motivates bid/constraint investigation, without establishing causality.
Do not fit generation into renewable availability. Hydro remains fixed, price and
mix accuracy gates remain open, and no investment or browser integration is accepted.
This report update is local; no CI/Pages or live-publication claim follows.

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
