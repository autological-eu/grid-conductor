# European dispatch: baseline and exploratory supply bids

## Summary

The exploratory model makes thermal supply curves steeper while retaining the baseline's demand, fleet, weather, fixed hydro and network constraints. Across **41 price zones**, July–December mean zonal price MAE improves **32.20 → 30.03 EUR/MWh**, and mean correlation **0.407 → 0.448**. Generation agreement improves in some areas, but substantial quantity and Nordic price errors remain. This is a useful bid experiment, not an accepted investment estimator or replacement for the workbench's browser engine.

All comparisons below use **July–December 2025: 4,416 UTC hours**. Both saved runs cover all 8,760 hours; using their evaluation period here keeps generation and price results comparable. Earlier experiments are omitted from this report.

## 1. Baseline model

**Clearing.** The model minimizes accepted supply-bid cost subject to fixed demand, available generation and physical network constraints. A sparse linear program clears each hour independently; zonal balance duals provide hourly prices. Hours are orchestrated in daily batches, but there is **no intertemporal daily optimization**. No ramping, unit commitment, endogenous battery operation or reservoir rescheduling is included.

**Geography and constraints.** The retained European backbone has **48 clearing areas and 145 physical buses**, separating Norway's five zones, Sweden's four, Denmark's two and Italy's seven. DE-LU and Ireland's shared market are combined; peripheral modeled areas are not all certified commercial bidding zones. Capacity-based generation shift keys (GSKs) locate zonal dispatch on physical buses. AC flow sensitivities, separate electrical-island balances, intrazonal branch constraints and HVDC bounds/losses remain. A uniform **0.7 security factor** limits branch ratings. These are model-derived N-0 constraints, not JAO commercial capacity domains, explicit N-1 security or full EUPHEMIA order allocation.

**Supply and demand.** Each generator contributes its original hourly available MW and resource bid. Wind/solar retain low-cost offers; thermal bids use fuel cost divided by efficiency, plus carbon and variable operating costs. Other technologies retain their source cost profiles. Demand is fixed, using the prepared 2025 series; spatial splits across newly separated zones include proxies. It is not yet independently certified observed load in every bidding zone. Emergency offers at 10,000 EUR/MWh diagnose shortage and are excluded from real generation-mix totals.

**Hydro.** Reservoir output is precomputed and fixed hour by hour. Norwegian preparation uses NVE weather-driven HBV inflow and reservoir boundary stocks, preserving turbine limits, chronological inventories and efficiency once on discharge. Other countries retain their reference schedules. Run-of-river remains a dispatchable available offer. Reservoirs cannot respond to changed bids or investments during clearing; national Norwegian water pooling and location assumptions remain limitations.

### Data used

| Component | Source and treatment |
| --- | --- |
| Grid, plants, efficiencies and inherited profiles | Pinned [PyPSA-Eur](https://github.com/PyPSA/pypsa-eur) v2026.08.0 backbone; original source/replay evidence retained. Nuclear availability ending in 2024 is a proxy; gas/nuclear available MW can be flat. |
| Wind/solar capacity and weather | [IRENA](https://www.irena.org/Data) end-2024/end-2025 capacities interpolated linearly through 2025, with retained ERA5-derived hourly profiles. This assumes commissioning dates; observed generation is never substituted for availability. Mixed-cluster location shares include proxies. |
| Fuel bids | [World Bank](https://www.worldbank.org/en/research/commodity-markets) monthly TTF gas/Brent oil and [ECB](https://data.ecb.europa.eu/) FX, inherited efficiency/carbon/VOM assumptions. Delivered-fuel, heating-value and EUA assumptions need further validation. |
| Norwegian reservoir inputs | [NVE hydrological data](https://www.nve.no/energi/analyser-og-statistikk/hydrologiske-data-til-kraftsituasjonsrapporten/): weather-driven inflow, stocks and capacity; retrospective revisions and gross-stock/net-inflow compatibility remain caveats. |
| Prices and hourly generation checks | [ENTSO-E Transparency](https://transparency.entsoe.eu/) A44 day-ahead prices and A75 generation by production type, with hashed source replay and UTC alignment. |
| National generation cross-check | [Ember](https://ember-energy.org/data/) monthly generation by fuel, July–December summed separately from hourly ENTSO-E checks. |

## 2. Exploratory model: what changes

Only the **shape of gas and coal/lignite bids** changes. Original available capacity is partitioned into three progressively more expensive blocks; no capacity is added.

| Offer component | Baseline | Exploratory |
| --- | --- | --- |
| Gas available MW | Original resource bid | 50% at original bid; 35% at +21; 15% at +60 EUR/MWh |
| Coal/lignite available MW | Original resource bid | 50% at original bid; 35% at +15.75; 15% at +45 EUR/MWh |
| Nuclear | Original running-cost offer | Same; no peaking blocks |
| Regional offsets / renewable discount | Zero | Zero: tested adjustments were not selected |
| Demand, physical inputs, hydro and other bids | Retained baseline | Identical |

The block adders represent synthetic effective bids, not measured exchange orders. Jan–April fits bounded proposals; May–June selects a predeclared finite configuration using equally weighted, control-normalized price MAE, daily-demeaned price MAE, monthly generation-interval error and implied-trade error, plus regularization. July–December is evaluated afterward. Historical training prices enter this experiment; evaluation prices and generation do not enter fitting or selection. Since 2025 was previously inspected, this is **retrospective temporal evaluation**, not untouched validation.

Both runs use the same split-column representation, with zero adders for the baseline control. This avoids comparing different formulations' arbitrary dual witnesses; even equivalent LP representations can produce different prices when the optimum is non-unique. The retained annual-v7 baseline is not promoted or overwritten.

## 3. Generation and price performance

![Generation and price errors for every covered area; points below the diagonal improve](/research/dispatch-comparison-2025/overview.png)

Price coverage is **41 of 48 modeled areas**; BA, GB, IE-SEM, ME, IT-CALA, FR-COR and XK have no comparison price. Generation coverage is **38 reporting areas**, with differing fuel/hour coverage. NO1–NO4 have zonal hourly generation, but NO5 has none. Germany's generation comparison is **DE national, excluding LU**, while its price comparison is DE-LU. France's generation comparison uses national model membership including modeled Corsica. National reporting areas and modeled geography are not automatically identical commercial zones.

| Metric, July–December | Baseline | Exploratory |
| --- | ---: | ---: |
| Equal-zone hourly price MAE, EUR/MWh | 32.20 | 30.03 |
| Mean zonal price correlation | 0.407 | 0.448 |
| Mean within-day price correlation | 0.361 | 0.403 |
| Daily-demeaned price MAE, EUR/MWh | 22.00 | 21.38 |
| Median covered-fuel generation volume error, % | 54.1 | 46.8 |

Price MAE improves in **26/41 zones** and worsens in 15; generation volume error improves in **28/38 areas**. Generation error sums absolute fuel-volume differences and divides by observed generation, using only each fuel's known hours. It can exceed 100%; it is not a generation-share percentage-point error or a complete-fleet score. Coverage differs between areas, so comparisons are paired within each area. This descriptive metric differs from the monthly interval-based fitting score.

Saved dispatch is disaggregated proportionally to original available MW within equal-bid groups. These fuel allocations are **illustrative**, not uniquely identified dispatch. Downloads include conditional lower/upper allocations; those bounds are not jointly attainable and do not span all possible LP optima. Missing observations stay missing; pumped-storage production is excluded from primary generation.

## 4. Norway, Germany, Spain and France

![National fuel shares and covered generation totals for Norway, Germany, Spain and France](/research/dispatch-comparison-2025/national-mix.png)

National Ember cross-check, same six months. Shares and TWh totals cover only fuels with all six observed months: NO nuclear/coal and FR other renewables are unavailable and excluded from all three bars, not filled with zero. National Norwegian totals include NO5; they are not allocated into its missing zonal observations. Model bars use illustrative fuel allocation; the CSV includes bounds and all modeled fuel volumes.

| Area | Generation volume error, %: baseline → exploratory | Price MAE, EUR/MWh: baseline → exploratory | Price correlation: baseline → exploratory |
| --- | ---: | ---: | ---: |
| NO1 | 74.5 → 74.5 | 40.53 → 41.27 | -0.216 → -0.231 |
| NO2 | 38.5 → 38.5 | 39.60 → 40.15 | 0.039 → 0.037 |
| NO3 | 47.3 → 47.3 | 27.56 → 28.34 | -0.099 → -0.098 |
| NO4 | 19.9 → 20.0 | 27.08 → 27.65 | 0.047 → 0.048 |
| NO5 | — → — | 43.67 → 44.71 | -0.371 → -0.378 |
| DE-LU | 52.8 → 50.3 | 23.35 → 21.37 | 0.692 → 0.717 |
| ES | 16.2 → 15.6 | 22.55 → 20.57 | 0.688 → 0.745 |
| FR | 13.1 → 13.4 | 20.71 → 20.46 | 0.685 → 0.698 |

Generation in the DE-LU row means **Germany national**; FR is national; Norway rows use their available zonal series. A dash denotes unavailable generation verification.

**Norway:** the bid change does not fix the main weakness. National modeled hydro remains about **74.83 TWh**, against Ember's **68.06 TWh** for these months. Yet national agreement cannot establish correct zonal water allocation: NO1's covered-fuel error is about 74%, and price correlations remain weak or negative across the five zones. NO2 is the illustrative price profile below, not a national Norwegian price.

**Germany:** gas rises **18.50 → 25.79 TWh**, closer to Ember's **38.53 TWh**; coal rises **15.88 → 20.30 TWh**, still below **45.32 TWh**. Wind remains **94.05 TWh** versus **71.07 TWh** observed. Better prices coexist with a large generation mismatch; bids alone have not resolved fleet/weather/demand scope.

**Spain:** national mix is comparatively close: gas moves **28.49 → 30.18 TWh** versus **29.66 TWh** observed. Price correlation improves markedly, but mean bias worsens **+3.12 → +7.58 EUR/MWh**. Wind stays about **21.07 TWh** versus Ember's **27.56 TWh**; similarity in totals does not imply each fuel or hour is right.

**France:** nuclear remains **180.18 → 179.74 TWh**, below **190.52 TWh** observed; hydro is **15.92** versus **22.55 TWh**. Generation error slightly worsens despite a small price improvement. Inherited nuclear availability and fixed hydro remain source/operational assumptions to investigate.

![Observed and simulated average local-hour price profiles for NO2, DE-LU, ES and FR](/research/dispatch-comparison-2025/daily-prices.png)

Profiles average evaluation-period prices by **local clock hour, with DST applied**; they are not a selected day or an hourly forecast trace. Aggregate within-day metrics above remove each UTC day's mean. The exploratory model captures more daily variation, but still misses price extremes: Spain's mean daily range is **81.61** versus observed **98.10 EUR/MWh**, with **zero modeled versus 97 observed negative-price hours**. Hour-to-hour ramp MAE slightly worsens **12.49 → 12.75 EUR/MWh**. A better average profile is not a complete hourly fit.

## Conclusion and verification

Steeper thermal offers improve broad price movement without changing physical supply, but the gains are moderate and uneven. **Retain the baseline; keep this as an exploratory bid model.** Priorities are source timing and operational availability, wind quantities, Nordic water/geography and demand scope, followed by a fresh predeclared evaluation. Matching generation totals or passing numerical replay does not validate investment effects, adaptive storage value or commercial congestion rents.

Both annual witnesses have **8,760 optimal hours and zero emergency generation**. Independent replay covers original component feasibility, block-summed availability, LP duals and chronological selection: maximum physical residual **6.71×10⁻⁶ MW**, duality gap **EUR 0.000138**. Annual clearing took **29.71s baseline / 38.92s exploratory**, excluding preparation; the complete fitting/selection/evaluation command took **337.97s**. These are recorded run measurements, not current job-status claims. A separate source-column replay verifies this report's generation geography, allocations, observations and metrics; rewriting ran no new market solve.

### Data and reproducibility

- [All-zone price metrics](/research/dispatch-comparison-2025/prices-by-zone.csv), including bias, hourly errors, within-day metrics and missing coverage.
- [Generation coverage and errors by area](/research/dispatch-comparison-2025/generation-by-area.csv), [fuel volumes, hourly errors and conditional bounds](/research/dispatch-comparison-2025/generation-by-fuel.csv), and [national Ember comparison](/research/dispatch-comparison-2025/national-generation.csv).
- [Compact provenance and verification receipt](/research/dispatch-comparison-2025/summary.json), with hashes linking the original model, source replay and report assets. Full source/hourly witnesses stay locally cached outside Git.
- Model formulation: [hourly_offer_curves_2025.py](tools/hourly_offer_curves_2025.py); [independent model replay](tools/audit_hourly_offer_curves_2025.py). Report derivation: [prepare_concise_dispatch_report_2025.py](tools/prepare_concise_dispatch_report_2025.py), [independent report replay](tools/audit_concise_dispatch_report_2025.py), [figure/report renderer](tools/write_concise_dispatch_report_2025.py).
