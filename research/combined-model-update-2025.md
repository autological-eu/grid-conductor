# Combined 2025 fleet, connection and hydro trial

**Decision:** the 8,760-hour combined candidate passed numerical and water-balance replay, but **does not qualify as the new active research baseline**. The existing `mixed_curve_fitting` baseline remains the control. The combined source changes are retrospective and several material generation, hydro and market-validation gates remain open.

## What was run

The candidate joins three separately retained research inputs in one physical LP clear:

1. **Generation:** 39 dated A75-demonstrated zone–technology power additions add **41.16 TWh of potential hourly availability** in separate offer columns. The original renewable availability columns and zero-output weather hours remain unchanged. Extra dispatchable columns have provisional old-curve tails or same-technology bid proxies. The added columns dispatch **23.70 TWh** in this run. A75 production peaks establish a dated *power* lower bound; they do not establish all-hour availability, outages or actual offers.
2. **Connections:** all 19 previously identified A11 physical-flow gaps use the separate dated component-level candidate. Three AC branch ratings remain within original nameplate; 16 HVDC changes are effective aggregate limits, not verified individual cable ratings or a reconstructed JAO day-ahead market domain.
3. **Hydro:** 79 of 93 source reservoir units use a bounded water-value timing rule based on 31-day modeled-price mean and fullness, with hourly water, storage and turbine constraints. The combined generator/network price witness is the model-only opportunity signal. **SE2, SE3 and SE4** have dated A75 reservoir turbine-ceiling shortfalls of **693, 727 and 175 MW**. For this sensitivity each shortfall is assigned after its first observed exceedance to one source unit allocated wholly to that zone. This avoids increasing capacity in another zone but is still **not a verified plant-level mapping**. Total reservoir water and storage energy are unchanged. Original run-of-river inflow and renewable weather availability remain unchanged.

The old monthly fitted supply curves are held fixed. This isolates changed inputs but is not a refit to the revised fleet and network. Hydro is a fixed injection schedule in the hourly LP, not an endogenous market bid. The 10 Spanish and three British source reservoirs whose existing zonal allocation would shift physical-island energy stay on the original schedule; one Serbian unit has no usable storage.

## Full-year results

| 2025 hourly LP | Price MAE against corrected ENTSO-E prices | Note |
| --- | ---: | --- |
| Accepted `mixed_curve_fitting` | **25.051 €/MWh** | Original network, fleet and hydro timing |
| Dated generation additions + A11 network | **25.040 €/MWh** | Previously audited frozen-bid witness |
| Combined fleet + A11 + dated hydro turbine/timing | **24.894 €/MWh** | New candidate; 8,760 hours |

The combined schedule moves **7.248 TWh** of existing reservoir output between hours while keeping annual reservoir generation at **350.441 TWh**. The full proposed change fits the physical network with **zero emergency supply**. The annual reclear took **33.4 seconds** after input/schedule preparation. Independent all-hour replay found a maximum primal residual of **0.0000038 MW**, duality gap of **€0.0000037**, and no hourly stock, turbine or terminal-water violation above the 10⁻⁴ tolerance.

The source-covered country–technology hourly generation MAE is **0.552867 GW before and 0.552867 GW after** at the shown precision; the mix-share MAE changes from **6.316% to 6.307%**. Mixed renewable offer dispatch still requires an illustrative allocation across source members. The model's modest price gain does not solve the generation discrepancies.

| Zone | Baseline price MAE | Combined price MAE | Change |
| --- | ---: | ---: | ---: |
| NO3 | 31.48 | 29.19 €/MWh | −2.29 |
| NO5 | 33.63 | 30.47 €/MWh | −3.17 |
| SE2 | 35.63 | 34.24 €/MWh | −1.39 |
| SE3 | 28.91 | 27.90 €/MWh | −1.01 |
| IT-SARD | 22.10 | 32.60 €/MWh | **+10.50** |
| DK1 | 16.58 | 17.47 €/MWh | **+0.89** |

The large IT-SARD regression is associated with the provisional waste-power addition: the source A75 observation covers only 94 hours and does not establish year-round fuel or commercial availability. This is a material blocker to baseline promotion. Full zonal results and the 39 added offer rows are retained in `research/data/combined-model-update-v2-2025.json` and the earlier input receipts.

## Hydro generation check

Against hourly A75 B12 reservoir production, the timing and turbine trial changes the *hourly* error only slightly and leaves annual generation unchanged. Values are TWh for annual energy and GW for hourly MAE:

| Zone | A75 annual reservoir | Model annual reservoir | Hourly MAE before → after |
| --- | ---: | ---: | ---: |
| SE2 | 37.35 | 24.27 | 2.201 → 2.193 |
| SE3 | 10.40 | 5.26 | 0.746 → 0.744 |
| SE4 | 0.92 | 0.50 | 0.086 → 0.086 |
| NO1 | 5.44 | 11.03 | 0.721 → 0.716 |
| NO2 | 42.51 | 50.71 | 2.199 → 2.146 |
| NO3 | 16.49 | 19.15 | 0.902 → 0.888 |
| NO4 | 20.55 | 23.10 | 1.049 → 1.032 |

These A75 comparisons use the raw hourly `B12` entries in the retained `data/carbon-pilot/map-2025/<zone>/<month>.json` files and the same fixed source-unit zonal shares used by the LP. Swedish turbine correction cannot close an annual **water-volume or category** gap of 13.07 TWh in SE2 and 5.13 TWh in SE3. The Norwegian reservoir/run-of-river partition is also unresolved. Observed dispatch is not substituted for water availability.

## Baseline decision and next actions

Keep the combined model as a **named research candidate**. Before promotion, reconcile the sparse Italian waste/CHP capacity and offers, establish plant or zone evidence for the Swedish turbine allocations and reservoir water volume, resolve the 16 HVDC effective limits against physical equipment and outages, and refit the monthly supply curves on the revised input model. Then repeat the independent full-year price, generation, commercial A09 exchange, water, physical-network and scenario-response audits, including adverse zonal changes and independent time transfer. Current in-sample price improvement alone does not satisfy those gates.

The runner `tools/run_combined_model_update_2025.py` and independent audit `tools/audit_combined_model_update_2025.py` use the pinned scientific environment and refuse to overwrite their source-hashed annual witness. Tracked receipts: `research/data/combined-model-update-v2-2025.json` and `research/data/combined-model-update-v2-audit-2025.json`. Large hourly arrays stay ignored under `data/bidding-zone-network-2025/combined-model-update-v2/`. No public app or Pages publication is claimed.
