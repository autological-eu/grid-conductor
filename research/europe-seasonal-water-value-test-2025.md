# Europe-wide seasonal reservoir timing test, 2025

**Status:** separate 8,760-hour research sensitivity, not a new baseline or a validated hydro bidding model. The same bounded rule used in the Norwegian test was extended to the retained European reservoir fleet. It moves existing reservoir generation between days without creating water or substituting historical dispatch for renewable availability.

## Inputs and method

The retained PyPSA-Eur-based 2025 network contains **93 reservoir units across 29 countries**. For Norway's five units, the test uses the separately source-checked NVE weekly inflow and stock reconstruction. For the other 88, it replays the archived 59-block chronological hydro witness and its original PyPSA-Eur-based hourly inflow; each block is checked against its saved SHA-256 receipt. This is a source-vintage and hydrology limitation: a successful water replay against a modeled inflow does not validate the inflow against observed catchment water.

Each unit's daily water value is `max(0, 31-day mean modeled opportunity price + 30 €/MWh × (0.5 − retained reservoir fullness))`. The schedule changes at most 5% of each day's inherited energy, keeps that day's inherited intraday shape, penalizes movement by 2 €/MWh, and constrains **every hourly stock** and turbine output. The terminal stock is unchanged; weekly stock stays within 5% of storage capacity from the retained trajectory. The price signal comes from the retrospective accepted LP model, which was fit to observed data; **observed ENTSO-E prices are not independently forecast here** and enter only the final comparison.

The fixed-injection perturbation is mapped through the retained zonal allocation and physical PTDF. Ten Spanish and three British units are held fixed because their present zonal generation-shift key would change physical-island energy when moved. One Serbian unit has no usable storage/generation. The remaining **79 units in 26 countries** participate. This is a disclosed physical mapping exclusion, not an assertion that their hydro is unimportant. The existing run-of-river profile and national Norwegian inflow split stay unchanged. The corrected Norwegian run-of-river turbine ceiling remains inactive under that water split.

## Full-year result

| Measure | Retained baseline | European timing trial |
| --- | ---: | ---: |
| All covered zonal price MAE | 25.051 €/MWh | **24.888 €/MWh** |
| Norwegian zone price MAE | 35.450 €/MWh | **34.290 €/MWh** |
| Other zone price MAE | 23.607 €/MWh | **23.582 €/MWh** |
| Annual reservoir generation | 350.441 TWh | **350.441 TWh** |
| Absolute reservoir output moved in time | — | **6.109 TWh** |
| Emergency supply | 0 MWh | **0 MWh** |
| Maximum stock/terminal mismatch | — | < 0.000001 MWh |
| Maximum physical LP primal residual | — | 0.0000005 MW |
| Annual physical reclear time | — | **31.3 s** |

The full proposed timing shift cleared with **no network scaling**. Most of it is Norway: **5.867 TWh (96.0%)**. Sweden contributes **0.149 TWh**; Switzerland **0.027**, Romania **0.017**, Greece **0.010**, and the other eligible countries smaller amounts. The rule therefore ran across Europe but did **not** produce a material Europe-wide hydro response outside Norway.

| Zone | Baseline MAE | Trial MAE | Direction |
| --- | ---: | ---: | --- |
| NO1 | 36.61 | 35.24 €/MWh | improved |
| NO2 | 40.42 | 39.24 €/MWh | improved |
| NO3 | 31.48 | 30.10 €/MWh | improved |
| NO4 | 35.11 | 34.49 €/MWh | improved |
| NO5 | 33.63 | 32.37 €/MWh | improved |
| SE2 | 35.63 | 35.09 €/MWh | improved |
| DK2 | 41.73 | 42.14 €/MWh | worsened |
| SE4 | 32.61 | 32.77 €/MWh | worsened |

Country and all-zone scores, skipped-unit reasons, water-value ranges, source hashes and the numerical witness hash are retained in `research/data/europe-seasonal-water-value-v2-2025.json`. Large hourly arrays remain ignored under `data/bidding-zone-network-2025/europe-seasonal-water-value-v2/`. The runner is `tools/test_europe_seasonal_water_value_2025.py` in the pinned PyPSA environment; it refuses to overwrite an existing witness.

## Interpretation and next work

The small outside-Norway response could reflect the inherited hydro schedules, tight stock trajectories, the 2 €/MWh movement penalty, price signal, or missing seasonal water data. It is **not** evidence that hydro timing does not matter elsewhere. Spain and Britain need a physical-island-safe zonal mapping before this fixed-injection test can include them. Norway still needs the reservoir/run-of-river inflow and generation-category reconciliation documented in `research/norway-water-availability-reconciliation-2025.md`.

This trial is exogenous reservoir scheduling; no hydro bid competes with other resources in clearing, and no line/storage investment is recleared with adaptive water value. Before baseline promotion or scenario claims: reconcile country-level inflow and observed stock, compare hourly and monthly hydro generation by reporting category, test independent time transfer, then implement endogenous reservoir bids with inventory constraints and rerun market and network audits. The active baseline is unchanged.
