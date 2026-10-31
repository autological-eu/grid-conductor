# Norway hydro water availability: 2025 source reconciliation

**Status:** source and accounting diagnostic. No new water availability, LP result, or baseline change is claimed.

## Current model

The Norwegian hydro input uses the source-hashed NVE weekly **HBV usable inflow** series. The source collector explicitly selects this weather-driven column rather than NVE's post-2015 series, which is derived from production and reservoir statistics and therefore is not an independent generation-validation input. The 2025 UTC calendar, including portions of adjacent ISO weeks, receives **141.64 TWh** of HBV inflow. The PyPSA hydro profile shapes full weekly volumes hourly; partial boundary weeks are uniform. These are electrical-equivalent water units, an explicit approximation.

The model pools Norway's reservoir water and observed NVE stock nationally. It splits inflow between reservoirs and run-of-river by inherited PyPSA turbine nameplate: **93.72% reservoir, 6.28% run-of-river**. The national reservoir starts at **68.55 TWh** and ends at **62.08 TWh**. A fixed hourly reservoir dispatch is scheduled against inflow, stock, turbine and network bounds; the run-of-river share is an hourly availability ceiling, so its actual dispatch can be lower. No observed hourly generation is copied into availability.

Source implementation: `tools/nve_hydro_inputs_2025.py`, `tools/update_norway_hydro_2025.py`; retained source workbook `data/hydro-observations-2025/nve-hydrology-release/table.xlsx`, stock `data/bidding-zone-source-audit-2025/nve-reservoir-history.json`; retained output `data/hydro-observations-2025/nve-updated-model-v5/`. The workbook and stock are checked against acquisition hashes by the compiler. The regional source reader in `tools/regional_water_candidate_2025.py` was used for the diagnostic below; it does not define the accepted baseline.

## Regional cross-check

The same NVE workbook reports HBV inflow for NO1–NO5, and NVE stock history reports regional reservoir inventory. Regional **inflow + starting stock − closing stock** is a rough electrical-equivalent annual water budget; it does not model transfers, cascades, pumping, or category boundaries. A75 values are exact-zone generation where covered, not water input. Values below are TWh, rounded; calendar inflow includes partial adjacent ISO weeks.

| Zone | NVE regional water budget | A75 reservoir generation | A75 run-of-river generation | A75 hydro minus budget | Current fixed reservoir output | Current run-of-river availability |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| NO1 | 14.78 | 5.44 | 12.82 | +3.48 | 11.03 | 6.36 |
| NO2 | 45.16 | 42.51 | 6.05 | +3.40 | 50.71 | 1.02 |
| NO3 | 26.08 | 16.49 | 4.72 | −4.88 | 19.15 | 0.34 |
| NO4 | 27.86 | 20.55 | 1.97 | −5.34 | 23.10 | 0.91 |
| NO5 | 34.17 | unavailable | unavailable | unavailable | 35.23 | 0.26 |

The A75 run-of-river total for NO1–NO4 is **25.56 TWh**, versus only **8.64 TWh** of their modeled availability (8.89 TWh nationally). NO1/NO2 observed *total* hydro exceeds the regional HBV-plus-stock budget by **6.88 TWh combined**. This prevents interpreting the run-of-river gap as merely a turbine ceiling. Regional water routing, source taxonomy, and the electrical-equivalent conversion need checking. NO5 has no matched A75 hydro category in the retained exact-zone inventory, so the four-zone comparison is incomplete.

For reference, NVE's 52 ISO weeks of national 2025 post-2015 usable inflow sum to **137.39 TWh**, against **141.54 TWh** for HBV. It is complete but production/stock-derived and lower in aggregate. Substituting it would neither independently validate nor close the observed run-of-river gap.

## Reconciliation path

1. Verify NVE's definitions and geography for HBV usable inflow, production/stock-derived inflow, regional reservoir inventory and run-of-river plants. Check whether the regional inflow series includes unregulated plants and how upstream cascades or cross-zone water transfer are counted.
2. Reconcile the A75 B12 Norwegian hydro category and zone mapping against plant-level generation or official Norwegian statistics, including NO5. The 2025 zone–technology A75 inventory is `research/data/adequacy-2025/zone-technology.csv`.
3. Obtain an independently measured or weather-derived run-of-river inflow/availability split, with explicit catchment and turbine mapping. Then test a water-conserving regional schedule and the original full-year price, generation, exchange, storage and no-emergency gates. Do not set availability equal to A75 dispatch or add water merely to close a price error.

This accounting check is reproducible by reading the hashed NVE sources with `regional_water_candidate_2025.source_inputs()` in the pinned PyPSA environment and joining the exact-zone rows of the adequacy CSV. The current national split is reproducible from `nve-updated-model-v5/summary.json`.
