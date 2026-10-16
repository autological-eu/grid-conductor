# European dispatch: baseline and exploratory supply bids

## Summary

The exploratory model combines stepped thermal supply curves with **hourly bid adjustments** driven by residual demand and a training-fitted local-time pattern. Demand, fleet, weather, fixed hydro and network constraints retain the baseline values. Across **41 price zones**, July–December mean zonal price MAE changes **32.20 → 28.29 EUR/MWh**, and mean correlation **0.407 → 0.524**. Generation and Nordic price errors remain material. This is an exploratory bid model, not an accepted investment estimator or replacement for the browser engine.

All comparisons below use **July–December 2025: 4,416 UTC hours**. Both saved runs cover all 8,760 hours; using their evaluation period here keeps generation and price results comparable. Earlier experiments are omitted from this report.

The hourly update improves on the previous constant-markup exploration: price MAE **30.03 → 28.29 EUR/MWh**, within-day correlation **0.403 → 0.529**, and daily-demeaned MAE **21.38 → 18.55 EUR/MWh**. The main figures compare the unchanged physical baseline with the updated exploration.

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

Both **quantity-dependent bid steps and hour-dependent offer prices** change. The earlier constant-markup experiment responded hourly through dispatch, but did not explicitly vary markups within the day. The new rule addresses the previously weak daily price response; it neither adds capacity nor imposes observed prices on the solver.

| Offer component | Baseline | Exploratory |
| --- | --- | --- |
| Gas available MW | Original resource bid | 50% at original bid; 35% at +21; 15% at +60 EUR/MWh |
| Coal/lignite available MW | Original resource bid | 50% at original bid; 35% at +15.75; 15% at +45 EUR/MWh |
| Nuclear | Original running-cost offer | No peaking blocks; small hourly bid adjustment |
| Regional offsets / renewable discount | Zero | Zero: tested adjustments were not selected |
| Hourly gas/coal adjustment | None | Residual-demand and local-time terms, capped at ±30 EUR/MWh |
| Hourly nuclear adjustment | None | One quarter of the gas/coal hourly adjustment, capped at ±7.5 EUR/MWh |
| Demand, physical inputs, hydro and other bids | Retained baseline | Identical |

**Hourly rule.** Residual demand is prepared demand minus fixed reservoir output minus available wind/solar. Its deviation from each UTC day's mean is scaled by Jan–April variability. Local-clock sine/cosine terms capture broad morning/evening patterns with DST. Each zone fits five ridge-regularized coefficients to the Jan–April observed-minus-previous-model price error after daily demeaning; extreme training errors are clipped at ±100 EUR/MWh. These terms alter gas/coal bids, and nuclear at quarter strength, before coupled clearing. The ±30 cap and zero offer floor preserve monotone thermal blocks, but can introduce daily mean shifts. Renewables and fixed hydro do not acquire new flexibility.

**Selection and limits.** Five predeclared residual/calendar strength pairs include the unchanged previous model. May–June selects **[1.0, 1.0]**, without refitting, using equally weighted prior-normalized price MAE, daily-demeaned MAE, monthly generation-interval error and implied-trade error, plus a small squared-shift penalty. July–December is evaluated afterward. Evaluation prices/generation never enter fitting or selection; runtime features require only calendar and model inputs, assuming perfect exogenous daily forecasts. Zones without training prices receive zero fitted corrections. These are synthetic effective bids, not measured orders or causal flexibility costs, and may compensate for incorrect inputs or constraints. Development months have been reused across experiments; previously inspected 2025 gives **retrospective temporal evaluation**, not untouched validation.

Baseline and exploration use the same split-column representation; equivalent LPs can have different non-unique price witnesses. Original annual-v7 and the preceding experiment remain immutable evidence. Daily features add no ramping, commitment or intertemporal storage optimization.

## 3. Generation and price performance

![Generation and price errors for every covered area; points below the diagonal improve](/research/dispatch-comparison-2025/overview.png)

Price coverage is **41 of 48 modeled areas**; BA, GB, IE-SEM, ME, IT-CALA, FR-COR and XK have no comparison price. Generation coverage is **38 reporting areas**, with differing fuel/hour coverage. NO1–NO4 have zonal hourly generation, but NO5 has none. Germany's generation comparison is **DE national, excluding LU**, while its price comparison is DE-LU. France's generation comparison uses national model membership including modeled Corsica. National reporting areas and modeled geography are not automatically identical commercial zones.

| Metric, July–December | Baseline | Exploratory |
| --- | ---: | ---: |
| Equal-zone hourly price MAE, EUR/MWh | 32.20 | 28.29 |
| Mean zonal price correlation | 0.407 | 0.524 |
| Mean within-day price correlation | 0.361 | 0.529 |
| Daily-demeaned price MAE, EUR/MWh | 22.00 | 18.55 |
| Median covered-fuel generation volume error, % | 54.1 | 45.2 |

Price MAE improves in **38/41 zones** and worsens in 3; generation volume error improves in **28/38 areas**. Generation error sums absolute fuel-volume differences and divides by observed generation, using only each fuel's known hours. It can exceed 100%; it is not a generation-share percentage-point error or a complete-fleet score. Coverage differs between areas, so comparisons are paired within each area. This descriptive metric differs from the monthly interval-based fitting score.

![Per-zone hourly price MAE grid comparing baseline and updated exploratory model](/research/dispatch-comparison-2025/zone-mae-grid.png)

Every tile gives **baseline → exploratory MAE**, then the signed change. Blue means lower error, red higher error; gray denotes unavailable observed prices. All 48 modeled areas remain visible. [Open the full-size grid](/research/dispatch-comparison-2025/zone-mae-grid.png).

Saved dispatch is disaggregated proportionally to original available MW within equal-bid groups. These fuel allocations are **illustrative**, not uniquely identified dispatch. Downloads include conditional lower/upper allocations; those bounds are not jointly attainable and do not span all possible LP optima. Missing observations stay missing; pumped-storage production is excluded from primary generation.

## 4. Norway, Germany, Spain and France

![National fuel shares and covered generation totals for Norway, Germany, Spain and France](/research/dispatch-comparison-2025/national-mix.png)

National Ember cross-check, same six months. Shares and TWh totals cover only fuels with all six observed months: NO nuclear/coal and FR other renewables are unavailable and excluded from all three bars, not filled with zero. National Norwegian totals include NO5; they are not allocated into its missing zonal observations. Model bars use illustrative fuel allocation; the CSV includes bounds and all modeled fuel volumes.

| Area | Generation volume error, %: baseline → exploratory | Price MAE, EUR/MWh: baseline → exploratory | Price correlation: baseline → exploratory |
| --- | ---: | ---: | ---: |
| NO1 | 74.5 → 74.4 | 40.53 → 41.16 | -0.216 → -0.232 |
| NO2 | 38.5 → 38.5 | 39.60 → 38.70 | 0.039 → 0.081 |
| NO3 | 47.3 → 47.3 | 27.56 → 27.95 | -0.099 → -0.106 |
| NO4 | 19.9 → 19.8 | 27.08 → 27.02 | 0.047 → 0.049 |
| NO5 | — → — | 43.67 → 45.60 | -0.371 → -0.383 |
| DE-LU | 52.8 → 50.1 | 23.35 → 19.75 | 0.692 → 0.783 |
| ES | 16.2 → 16.3 | 22.55 → 19.26 | 0.688 → 0.785 |
| FR | 13.1 → 13.2 | 20.71 → 19.33 | 0.685 → 0.731 |

Generation in the DE-LU row means **Germany national**; FR is national; Norway rows use their available zonal series. A dash denotes unavailable generation verification.

**Norway:** national modeled hydro is **74.83 TWh**, against Ember's **68.06 TWh**. National totals cannot establish correct zonal water allocation: NO1's covered-fuel error is **74.4%**, with price MAE **41.16 EUR/MWh**. The table retains all five zones and adverse results. NO2 illustrates a local price profile below, not a national Norwegian price; adjusting bids cannot reschedule fixed reservoir water.

**Germany:** gas changes **18.50 → 26.51 TWh**, against Ember's **38.53 TWh**; coal **15.88 → 20.64 TWh**, against **45.32 TWh**. Wind is **94.05 TWh** versus **71.07 TWh** observed. Price correlation is **0.783**, but bids alone have not resolved the large fleet/weather/demand-scope discrepancies.

**Spain:** national gas changes **28.49 → 30.55 TWh** versus **29.66 TWh** observed. Price correlation changes **0.688 → 0.785**, mean bias **+3.12 → +6.46 EUR/MWh**. Wind is **21.07 TWh** versus **27.56 TWh**; similarity in total generation does not establish accurate fuel quantities or hourly timing.

**France:** nuclear changes **180.18 → 180.85 TWh**, against **190.52 TWh** observed; hydro is **15.92** versus **22.55 TWh**. Generation error changes **13.1 → 13.2%**. Inherited nuclear availability and fixed hydro remain assumptions to investigate, irrespective of price improvement.

![Observed and simulated average local-hour price profiles for NO2, DE-LU, ES and FR](/research/dispatch-comparison-2025/daily-prices.png)

Profiles average evaluation-period prices by **local clock hour, with DST applied**; they are not a selected day or an hourly forecast trace. Aggregate within-day metrics remove each UTC day's mean. Spain's mean daily range changes **66.47 → 97.37**, versus observed **98.10 EUR/MWh**; within-day correlation **0.718 → 0.809**. Hour-to-hour ramp MAE changes **12.49 → 12.36 EUR/MWh**, with **0 modeled versus 97 observed negative-price hours**. A better average profile is not a complete hourly fit.

## Conclusion and verification

Hourly bid rules explicitly represent intraday variation while physical supply remains unchanged. Evaluate the improvement using both the all-zone grid and daily-shape metrics, rather than a single average profile. **Retain the baseline; keep this as an exploratory bid model.** Source timing/operational availability, wind quantities, Nordic water/geography and demand scope remain priorities. Matching totals or passing numerical replay does not validate investment effects, adaptive storage value or commercial congestion rents.

Both annual witnesses have **8,760 optimal hours**; exploratory emergency generation is **0.000000 MWh**. Independent replay covers source inputs, original component feasibility, capacity conservation, hourly feature construction, training-only fitting, LP duals and chronological selection: maximum physical residual **1.3e-05 MW**, duality gap **EUR 0.000023**. Annual clearing took **29.71s baseline / 47.75s exploratory**, excluding preparation; the new fitting/selection/evaluation command took **281.34s**. Report derivation separately replays generation geography, allocations, observations and metrics. Full source/hourly witnesses remain local; no deployment or investment acceptance is implied.

### Data and reproducibility

- [All-zone price metrics](/research/dispatch-comparison-2025/prices-by-zone.csv), including bias, hourly errors, within-day metrics and missing coverage.
- [Generation coverage and errors by area](/research/dispatch-comparison-2025/generation-by-area.csv), [fuel volumes, hourly errors and conditional bounds](/research/dispatch-comparison-2025/generation-by-fuel.csv), and [national Ember comparison](/research/dispatch-comparison-2025/national-generation.csv).
- [Compact provenance and verification receipt](/research/dispatch-comparison-2025/summary.json), with hashes linking the original model, source replay and report assets. Full source/hourly witnesses stay locally cached outside Git.
- Model formulation: [intraday_offer_bids_2025.py](tools/intraday_offer_bids_2025.py); [independent model replay](tools/audit_intraday_offer_bids_2025.py). Report derivation: [prepare_intraday_dispatch_report_2025.py](tools/prepare_intraday_dispatch_report_2025.py), [independent report replay](tools/audit_intraday_dispatch_report_2025.py), [figure/report renderer](tools/write_concise_dispatch_report_2025.py).
