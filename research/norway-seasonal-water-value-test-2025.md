# Norway seasonal water-value timing test, 2025

**Status:** full-year sensitivity, not a new baseline or validated hydro bid. This test changes when the **existing reservoir water** is released; it does not add water or alter the accepted run-of-river split.

## Rule and source control

The starting reservoir schedule and NVE inflow/stock witness are the retained `nve-updated-model-v5` inputs. For each of five inherited Norwegian reservoir units, a daily water value is the **31-day moving average of that unit's retained *model-only* zonal price**, plus `30 €/MWh × (0.5 − reservoir fullness)`, floored at zero. The daily release decision compares that value with the day's modeled opportunity price, and pays a 2 €/MWh penalty for changing the original schedule. This is a simple opportunity-cost sensitivity, not an operator bid reconstruction. The retained modeled prices themselves were produced by a retrospective fitted-bid baseline; they are not an independent forecast. Observed ENTSO-E prices enter only the final score, never this scheduling objective.

The test permits at most a 5% change in each day's original release. It retains the inherited intraday shape within each day and preserves annual water and terminal stock. Weekly reservoir stock must remain within 5% of capacity of the retained stock trajectory. Hourly stock, turbine bounds, network feasibility and zero emergency are checked after scheduling. The unchanged national NVE inflow is still split 93.72% reservoir / 6.28% run-of-river by inherited turbine capacity. The A75-supported corrected run-of-river turbine ceiling is **inactive under this water allocation**: no original hourly run-of-river water reaches the old combined 2,083 MW ceiling. Therefore, this experiment isolates reservoir timing; it does not claim to have tested a corrected run-of-river water supply.

## Full-year result

| Measure | Retained baseline | Seasonal timing trial |
| --- | ---: | ---: |
| Europe-wide observed price MAE | 25.051 €/MWh | **24.894 €/MWh** |
| Norway reservoir annual generation | 139.215 TWh | **139.215 TWh** |
| Absolute reservoir energy moved in time | — | **5.867 TWh** |
| Emergency supply | 0 MWh | **0 MWh** |
| Maximum hourly stock violation | 0 MWh | **0 MWh** |
| Terminal stock difference | — | < 0.000001 MWh |
| Physical LP maximum primal residual | — | 0.0000032 MW |
| Annual physical reclear time | — | **37.1 s** |

| Norwegian zone | Baseline price MAE | Trial price MAE |
| --- | ---: | ---: |
| NO1 | 36.61 | **35.23** €/MWh |
| NO2 | 40.42 | **39.24** €/MWh |
| NO3 | 31.48 | **30.12** €/MWh |
| NO4 | 35.11 | **34.51** €/MWh |
| NO5 | 33.63 | **32.38** €/MWh |

The rule changes monthly reservoir energy by −0.25 TWh in January, −0.24 TWh in June, +0.20 TWh in August and +0.14 TWh in November; the annual net shift is zero. These are schedule differences, **not additional generation**. The maximum aggregate hourly output change is about 1,555 MW. The network accepted the full proposed shift without clipping. The numerical receipt is `research/data/norway-seasonal-water-value-2025.json`; large hourly arrays are ignored under `data/bidding-zone-network-2025/norway-seasonal-water-value-v1/`. Reproduce with the pinned PyPSA environment: `python -m tools.test_norway_seasonal_water_value_2025` in a fresh output location after retaining the current witness.

## Interpretation and next gate

The modest all-zone price gain is useful evidence that reservoir timing matters, but it does **not** establish forward skill or scenario response. The rule receives a price signal from the retained retrospective model, the original daily intraday shape, and the original national water split. It is also an exogenous fixed-injection schedule in the physical LP, rather than hydro blocks competing with other supply bids during clearing. These restrictions can conceal the true effect of an added transmission or storage asset.

Next, reconcile regional NVE inflow and ENTSO-E hydro categories, including NO5, as set out in `research/norway-water-availability-reconciliation-2025.md`. With a source-supported reservoir/run-of-river partition, test daily **endogenous** reservoir offers against the same hourly inventory and turbine limits, then rerun full-year price, hydro generation, stock, exchange and scenario-response audits. Do not promote the timing sensitivity into the accepted baseline on price MAE alone.
