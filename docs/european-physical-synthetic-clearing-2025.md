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
