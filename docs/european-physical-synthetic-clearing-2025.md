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
