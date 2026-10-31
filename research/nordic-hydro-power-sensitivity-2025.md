# Nordic hydro turbine-power test, 2025

**Status:** full-year frozen-bid sensitivity, not a new baseline or source-verified hydro reconstruction. Raising a reservoir turbine ceiling while keeping the current hourly fixed reservoir schedule unchanged has **exactly zero effect** on this LP: that ceiling is not an active control over the fixed injection. The separately tested Norwegian run-of-river case adds a parallel turbine with the *original model's hourly per-unit profile* in NO1–NO4. Its added turbine ceiling follows the **running A75 observed peak**, so a later 2025 peak is never applied to earlier hours. This preserves the original offers and their zero-output hours, but assumes extra run-of-river water follows the same shape. The A75 observed peak proves power existed at a dated hour; it does **not** validate that added water profile for other hours. An initial look-ahead version that applied the final annual peak too early is retained only as a rejected diagnostic.

## Power and energy evidence

The [A75 zone–technology inventory](data/zone-tech-power-envelope-2025.csv) has 8,760 matched hours for each of the four Norwegian run-of-river zones. The trial starts its parallel profile at the first observed hour exceeding model source nameplate, and scales the existing profile by `(running observed peak at hour / source nameplate − 1)`. The original renewable availability remains a separate unchanged LP column.

| Zone | Source turbine ceiling MW | A75 peak MW | Added ceiling MW | Original model available TWh | Added profile available TWh | A75 observed generation TWh |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| NO1 | 1,489 | 2,027 | 538 | 6.36 | 1.38 | 12.82 |
| NO2 | 240 | 1,147 | 907 | 1.02 | 3.69 | 6.05 |
| NO3 | 80 | 1,044 | 964 | 0.34 | 3.82 | 4.72 |
| NO4 | 214 | 408 | 194 | 0.91 | 0.75 | 1.97 |

The added **9.64 TWh** is a sum of potential hourly MW, not observed generation, independently measured inflow or a feasible reservoir water budget. Even after the profile scaling, model potential in NO1 and NO2 remains below their A75 reported annual energy. This is evidence against treating turbine power as the whole discrepancy. A75 category scope and missing run-of-river fleet/inflow still require reconciliation. The rejected look-ahead version had 10.88 TWh of added potential; its [receipt](data/nordic-ror-power-sensitivity-2025.json) is retained to expose that difference.

## Full-year dispatch result

| LP and hydro case | Added run-of-river offer dispatch | Price MAE vs ENTSO-E | Emergency |
| --- | ---: | ---: | ---: |
| Accepted original network, original hydro | — | €25.051/MWh | 0 MWh |
| Original network + dated parallel run-of-river profile | 7.03 TWh | €25.062/MWh | 0 MWh |
| A11 network only, original hydro | — | €24.831/MWh | 0 MWh |
| A11 network + dated parallel run-of-river profile | 7.08 TWh | €24.819/MWh | 0 MWh |

Both new cases clear all 8,760 UTC hours with zero emergency; the independent [primal/dual replay](data/nordic-ror-power-sensitivity-audit-2025.json) passes with maximum primal residual below 10⁻⁶ MW and duality gap below €0.000007. The [dated annual receipt](data/nordic-ror-power-sensitivity-v2-2025.json) retains source hashes, added-offer dispatch and per-zone prices. The original-network trial improves NO3 price MAE from 31.48 to **28.87 €/MWh** and NO4 from 35.11 to **31.24**, but worsens NO1 from 36.61 to **40.35** and NO2 from 40.42 to **44.98**. The Europe-wide price difference is negligible.

| Zone | A75 generation TWh | Baseline model RoR dispatch TWh | Trial original + parallel RoR dispatch TWh |
| --- | ---: | ---: | ---: |
| NO1 | 12.82 | 4.42 | 4.93 |
| NO2 | 6.05 | 0.79 | 3.25 |
| NO3 | 4.72 | 0.28 | 3.28 |
| NO4 | 1.97 | 0.77 | 1.35 |

This trial reduces part of the run-of-river generation gap but does not close it. It also cannot validate *why* the original model is short: source fleet vintage, plant allocation, reporting taxonomy and independent inflow are unresolved. The added 0 €/MWh offers and frozen fitted bids are provisional. Observed A75 dispatch was used only to set a dated power ceiling, never copied into hourly availability.

## Reservoir result and next action

For Swedish reservoirs, observed turbine peaks exceed source ceilings by 693 MW in SE2, 727 MW in SE3 and 175 MW in SE4. With the existing **fixed hourly reservoir output**, changing those ceilings alone changes neither energy nor prices. The source-covered annual reservoir production also exceeds the fixed schedule: SE2 37.35 versus 24.27 TWh, SE3 10.40 versus 5.26 TWh, SE4 0.92 versus 0.50 TWh. Higher turbine capacity cannot explain that energy difference. A meaningful reservoir test requires a source-reconciled water/inflow and stock model, then a water-conserving schedule with the higher turbine limits and original network gates. An unverified extra-water schedule should not replace the accepted baseline.

Reproduce with the pinned scientific environment: `python -m tools.run_nordic_hydro_power_sensitivity_2025` and `python -m tools.audit_nordic_hydro_power_sensitivity_2025`. The runner refuses to overwrite existing witnesses; select a new output location for a new hypothesis. Large annual arrays remain ignored under `data/`.
