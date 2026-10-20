# European hourly clearing: diagnosing the price errors

Updated 20 October 2026. **The main problem is the shape and timing of prices, not one uniform Europe-wide offset.** The model understates high-price episodes, often overstates low-price hours, and misses a weekly pattern. Nordic errors also change sign by region and season. We traced these patterns through the saved full-year solutions and tested one bounded change to supply bids: a weekday/weekend term.

This remains a **2025 in-sample market reconstruction**, not independent forecasting, recovered actual order books or investment validation. The accepted research baseline remains the seasonal-calendar annual refit; the earlier joint supply/network fit is a separate checkpoint. Neither this test nor the joint checkpoint replaces the browser's two-zone scenario engine.

## 1. What the baseline clears

The model clears fixed observed/model-input zonal demand against synthetic resource supply offers for **48 modeled areas**, projected through a **145-bus physical backbone**. Each of the **8,760 hours** has a network-constrained linear dispatch solve. Daily grouping currently contains independent hourly solves; there is no new inter-hour commitment or adaptive reservoir optimisation.

Wind/solar offered MW come from retained weather profiles and capacity trajectories. Thermal offers use fuel, efficiency, carbon and operating-cost anchors, split into monotone supply blocks. Nuclear has its own offer. Smooth local-clock and seasonal adjustments, plus national generation consistency signals, are calibrated into the accepted supply bids. Hydro remains the retained fixed hourly injection schedule, not a freely priced reservoir bid. Passive AC constraints use the model PTDF/static generation-shift keys; controllable links retain bounds/losses. These are model-derived constraints, not certified JAO commercial domains.

The **joint checkpoint** additionally uses the frozen prior inverse gas/coal/nuclear bid fit and 15% higher effective Nordic-incident AC limits. It retains original wind availability, topology, impedances, GSKs, HVDC, demand and hydro. The headroom multiplier is a calibration assumption, not a verified grid correction. Its lower aggregate error conceals regressions in NO2/NO4 and Sweden. Full prior search outcomes, including rejected states, remain in the supporting CSVs below.

## 2. When and what kinds of errors occur

We compare model minus observed ENTSO-E day-ahead price, $e=p_{model}-p_{observed}$, preserving all **41 complete observed-price zones** and all hours. Positive bias means overpricing. The seven remaining modeled areas have no complete target and stay visibly missing. Local weekday/hour classifications include DST; shared event dates and monthly totals use UTC.

For both anchors, the three worst days are **25 November, 20 January and 15 January**. In the joint checkpoint, hours above **EUR 150/MWh account for 19.0%** of total absolute error; observed negative-price hours account for **2.4%**. The largest portion still accumulates in ordinary price bands because they contain far more hours. Fixing only rare extremes or negatives cannot close the overall gap.

![Absolute error contributions and signed bias by observed price regime](/research/dispatch-comparison-2025/overview.png)

These bands are diagnostic groupings using the observed target, never predictors passed to the solver. The model's supply stack frequently produces a narrow price range while real prices have deeper troughs and higher peaks. A calendar-only bid cannot reproduce a specific scarcity event merely because it occurred in winter. Zero renewable offers/positive thermal floors also miss negative-price mechanisms in western zones. Prior universal renewable discounts did not establish a satisfactory fleet-wide correction, so they are not silently reintroduced here.

The weekly mismatch is widespread: modeled-minus-observed bias is more positive on weekends than weekdays, even though source demand already varies hourly. A missing weekly bid effect is therefore a testable hypothesis; it is **not proof** that real suppliers use exactly this rule or that demand inputs are complete. Local interior-offer diagnostics distinguish gas/coal/nuclear support from hours without a matching local marginal offer. Network dual terms are an exact witness decomposition, not causal error shares or uniquely identified real price setters.

There are two materially different mechanisms in the saved solutions. In Germany, local gas/coal offers match the joint checkpoint price in 3,875 hours; in France, nuclear matches in 4,905 hours. These provide local bid evidence. In **NO5, 8,589/8,760 hours have no matching local interior offer**: its fixed hydro injection has no water-price decision, and its cleared price depends on the coupled network/links rather than an adjustable local water bid. That explains why this local thermal-bid correction has little leverage there; it does not establish which real constraint or hydro assumption is wrong. On 1 October at 17:00 UTC, DE-LU observed EUR 512.59/MWh versus the joint model's EUR 128.92. On 25 November at 15:00 UTC, NO5 observed EUR 266.26 versus EUR 2.86. These need different investigations, rather than one common price offset.

## 3. The targeted model change

Each zone/resource receives at most **one new coefficient** multiplying its centered local Saturday/Sunday indicator, $w=I_{weekend}-E[I_{weekend}]$. Existing 15 seasonal/time-of-day columns are included as nuisance controls in fitting; only the new weekly coefficient is applied. Thus we test the omitted weekly pattern without refitting all existing parameters or introducing residual-demand predictors.

Fit support requires the resource to be locally interior, over 0.001 MW from both bounds, and its offer to match the cleared local price within EUR 0.00001/MWh. At least 168 supported hours and 24 of each day type are required; unsupported resources receive zero correction. All 2025 observed prices inform this explicitly labelled reconstruction. A ridge of 168 and response clipping at +/-EUR 100/MWh reduce isolated-event influence. Weekly coefficient bounds are +/-EUR 30/MWh for gas/coal and +/-EUR 7.5/MWh for nuclear. In the joint case, 20 gas, 10 coal and 6 nuclear zone coefficients have nonzero support.

The same additive adjustment applies to every block of that zone/resource; final bids remain nonnegative and block ordering is preserved. The weekly term has zero annual mean before the final floor. It changes offers **before clearing**, never overwrites a cleared price. At inference it uses calendar and saved coefficients only. Wind/solar availability, fixed hydro, capacities, demand, network constraints and all other bids remain identical to the corresponding anchor.

The declared design tests exactly **two full-year corrections**, one per anchor, with no strength sweep or after-the-fact refit. Each must improve its own anchor's annual price MAE without worsening within-day, generation or trade scores by more than 2%; all 8,760 hours must be optimal with no emergency supply. These are research safeguards, not a product-acceptance or forecasting certificate.

## 4. Full-year results

Price and within-day columns are EUR/MWh. Generation and implied-trade scores are normalized monthly distances outside conditional allocation intervals, **not percentage TWh errors**; lower is better. Generation uses Wind/Solar/Nuclear/Gas/Coal national Ember observations; implied trade is generation minus demand, not verified physical border flow. Missing targets stay unknown.

| Anchor → same model with weekly bids | Price MAE | Within-day MAE | Generation score | Trade score | Declared filter |
| --- | ---: | ---: | ---: | ---: | --- |
| Accepted baseline | 28.964 → 28.663 | 20.063 → 20.054 | 0.2995 → 0.2972 | 0.1719 → 0.1727 | pass |
| Joint checkpoint | 27.752 → 27.487 | 18.983 → 18.989 | 0.2548 → 0.2532 | 0.1438 → 0.1438 | pass |

The correction reduces aggregate MAE by **1.04%** on the accepted baseline and **0.95%** on the joint checkpoint. Mean zonal correlation changes **0.573→0.582** and **0.610→0.618**, respectively. Both pass the declared filters. This is a modest improvement: the joint version slightly worsens within-day MAE and implied-trade score, though within the predeclared 2% bound. A successful fit is not a claim that every zone or metric improves.

![All modeled zones: full-year price MAE before and after the weekly supply-bid correction](/research/dispatch-comparison-2025/zone-mae-grid.png)

| Zone | Accepted baseline | Baseline + weekly | Joint checkpoint | Joint + weekly |
| --- | ---: | ---: | ---: | ---: |
| NO1 | 42.57 | 42.54 | 38.33 | 38.15 |
| NO2 | 39.25 | 39.21 | 42.39 | 42.22 |
| NO3 | 34.58 | 34.54 | 31.94 | 31.80 |
| NO4 | 35.21 | 35.16 | 39.62 | 39.50 |
| NO5 | 47.29 | 47.27 | 32.56 | 32.41 |
| SE1 | 35.05 | 34.87 | 38.39 | 38.15 |
| SE2 | 35.57 | 35.37 | 39.11 | 38.88 |
| DE-LU | 21.57 | 21.17 | 19.42 | 19.02 |
| ES | 24.07 | 23.43 | 21.62 | 21.18 |
| FR | 23.83 | 23.57 | 24.66 | 24.39 |

![Weekly error contrast and remaining seasonal regional bias](/research/dispatch-comparison-2025/national-mix.png)

The weekly comparison is descriptive: demand, weather and network conditions differ between day types. The fitted term controls the existing smooth seasonal/local-clock features but cannot establish a causal bidding effect. Nordic north/south and monthly biases remain visible rather than being averaged away.

![Hourly observed and modeled prices during a shared November error episode](/research/dispatch-comparison-2025/daily-prices.png)

The November window was chosen from both anchors' error inventory before evaluating the weekly correction. It illustrates a remaining difficult episode; headline metrics use the entire year. A successful calendar correction would still leave resource availability, scarcity premiums, operating constraints and Nordic injection/constraint geography to investigate independently. Fixed hydro has no flexible water bid to calibrate in this formulation.

## 5. Data, verification and conclusion

**Observed prices:** retained ENTSO-E A44 series, UTC-aligned to hourly 2025. Demand is the retained ENTSO-E/PyPSA-Eur-derived source input; geographic allocation/proxy limitations persist. **Supply:** PyPSA-Eur plant/network lineage, original processed weather profiles, IRENA end-2024/end-2025 wind/solar trajectories under assumed linear commissioning, retained NVE-backed fixed Norwegian hydro schedule and inherited other-country schedules. **Generation targets:** monthly national Ember; available weather supply is never replaced by reported generation or dispatch. **Fuel anchors:** inherited monthly World Bank TTF/Brent and ECB conversion, flat carbon and coal/lignite assumptions; this experiment does not adopt daily-fuel sensitivities. National capacity/quantity coverage is distinct from commercial bid-zone completeness. The model is EUPHEMIA-inspired, not a reproduction of actual block orders/allocation rules.

Independent replay reconstructs coefficients with an augmented least-squares calculation, altered offer vectors, all original source bounds and native component equations, primal/dual optimality, objectives and monthly quantities. Both tests contain 8,760 optimal hours and zero emergency supply. Maximum native residual **1.1e-06 MW**, duality gap **EUR 0.000101**. New annual clearing loops total **98.32s**; source/model preparation **97.17s**, complete driver **208.03s**, separate independent audit **134.05s**. These runtime components are kept distinct.

The useful change is to diagnose errors by event and market regime before changing more grid parameters. The weekly term is one controlled supply-bid hypothesis, not a general repair for the high-price tail or Nordic geography. The below-EUR 10/MWh target remains unmet; no automatic baseline promotion, browser integration or verified investment-return claim follows. Fitting 2025 prices and checking generation/physics does not establish future-year forecast accuracy.

- [All-zone error metrics and weekday/weekend bias](/research/dispatch-comparison-2025/hourly-error-zones.csv), [price regimes, monthly errors and worst event days](/research/dispatch-comparison-2025/hourly-error-periods.csv).
- [Prior joint calibration cases](/research/dispatch-comparison-2025/joint-search-cases.csv), [joint zonal price metrics](/research/dispatch-comparison-2025/joint-prices-by-zone.csv), [national five-fuel quantities and conditional bounds](/research/dispatch-comparison-2025/joint-generation-by-country.csv). These describe the preceding checkpoint, not the new weekly corrections.
- [Compact provenance and audit receipt](/research/dispatch-comparison-2025/summary.json). Raw inputs and full hourly witnesses remain locally cached outside Git. [Workbench methodology](/docs/workbench-methodology/).
