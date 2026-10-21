# European hourly clearing: current oil/CHP model

Updated 22 October 2026. **The current displayed model includes daily oil costs and a simple CHP heat credit. Germany's hourly oil-generation error falls by 42.5%, but European price accuracy remains far from the below-€10/MWh goal.** The full-year comparison now uses audited ENTSO-E main day-ahead prices, averaged to UTC hours.

[Explore any country, its generation sources and hourly prices](/countries/) · [Denmark, 1–20 January (hourly)](/countries?country=DK&start=2025-01-01&end=2025-01-20&resolution=hourly)

## 1. What the model clears

Fixed hourly demand meets synthetic generator offers in **48 modeled market areas**, through a **145-bus PyPSA-Eur-derived physical backbone**. All **8,760 hours of 2025** are cleared under model transmission constraints. Daily grouping runs independent hourly LPs: it does not add commitment, battery arbitrage or adaptive reservoir optimisation.

- **Demand and geography:** retained ENTSO-E/PyPSA-Eur input and geographical allocation; source-country labels and bidding zones are distinct. Coverage and allocation proxies remain.
- **Wind and solar:** original processed weather profiles and IRENA end-2024/end-2025 capacity trajectories, with assumed linear commissioning. Availability is never replaced by observed generation or dispatch.
- **Hydro:** the retained, water-audited fixed hourly reservoir schedule, including NVE-backed Norwegian reconciliation; run-of-river remains a supply resource. Reservoir output cannot adapt to a new investment.
- **Thermal and nuclear bids:** fuel, efficiency, carbon and variable-cost anchors plus saved monotone gas/coal blocks and calibrated seasonal/local-clock/weekly adjustments. The retained joint checkpoint also includes an inverse gas/coal/nuclear bid correction. Those non-oil coefficients are frozen. Non-oil fuel anchors remain inherited monthly World Bank/ECB inputs and coal/lignite/carbon assumptions; daily gas prices were not adopted.
- **Network:** model PTDFs, static generation-shift keys and bounded/lossy controllable links. The retained joint fit uses 15% higher effective Nordic-incident AC ratings. This is a calibration assumption, not measured extra capacity or a certified JAO commercial domain.

This is a transparent zonal-dispatch approximation inspired by market clearing, **not EUPHEMIA or a reconstruction of actual order books**. The workbench's two-zone scenario engine and formally accepted research baseline are unchanged; this report and the country explorer show the newer verified oil/CHP checkpoint.

## 2. What changed in oil supply

The audited annual ENTSO-E A68/A33 B06 inventory fills only three missing oil fleets: **PL 392.535 MW, SK 259 MW and SI 58 MW**. Existing fleets remain. Installed nameplate is treated as available supply, not proof of hourly operational readiness. IRENA covers renewable capacity and does not supply these fossil-oil figures.

Oil's merchant offer is `(fuel + carbon × emissions factor) / electrical efficiency + variable O&M`. Fuel uses daily **EIA Brent and ECB exchange rates**; Brent is a crude-price proxy, not the delivered plant fuel product. The inherited efficiency (typically 35%), thermal emissions factor (0.2571 t/MWh) and operating cost (€8.0148/MWh electrical) remain assumptions.

EU/EEA oil carbon uses dated **EEX T3PA primary-auction prices**, carried forward: the first 144 hours use €80/t, and the longest carry is 16 days. Outside that jurisdiction the retained €80/t remains unresolved. Primary auctions are not a complete daily spot series.

For **25% of source-labelled, geographically matched oil CHP capacity**, an optional cheaper tranche subtracts an avoided-heat credit: `(0.5 / electrical efficiency) × (monthly gas + carbon × 0.198) / 0.9`. Useful-heat efficiency 0.5 and alternative-boiler efficiency 0.9 are explicit proxies. The remaining capacity keeps the merchant bid. Total hourly MW is conserved; there is no forced heat generation, measured heat-demand schedule or new energy. This tranche is not fitted to electricity prices or oil generation. All non-oil bids, weather, fixed hydro, demand and physical constraints stay frozen.

## 3. Full-year results

**European price MAE is €27.58/MWh**, the equal-weight mean of 41 complete zonal MAEs over all 8,760 hours; mean zonal correlation is **0.617**. The same frozen model with merchant oil bids, missing-capacity additions and daily oil costs scores **€27.56/MWh** against these same corrected observations. Oil CHP improves generation, not aggregate price accuracy.

![European price error and German oil-generation improvement](/research/dispatch-comparison-2025/overview.png)

| Zone | Price MAE €/MWh | Bias €/MWh | Correlation |
| --- | ---: | ---: | ---: |
| AT | 17.77 | -5.46 | 0.834 |
| DE-LU | 19.71 | -11.15 | 0.831 |
| DK1 | 23.42 | -11.61 | 0.774 |
| ES | 21.20 | 2.13 | 0.825 |
| FR | 24.43 | -12.10 | 0.799 |
| DK2 | 49.11 | -35.92 | 0.310 |
| NO1 | 38.08 | -15.72 | 0.199 |
| NO2 | 42.15 | -22.02 | 0.138 |
| NO3 | 31.71 | 21.78 | 0.237 |
| NO4 | 39.41 | 35.45 | 0.101 |
| NO5 | 32.34 | -5.12 | 0.279 |

The hourly error is $e_t = p_t^{model} - p_t^{ENTSO-E}$; zonal $MAE = (1/8760) \sum_t |e_t|$. Positive bias means model overpricing. All zones and adverse results are in the CSV and explorer. Seven modeled areas lack complete observed targets; none is assigned a zero error.

![Full-year price MAE for every modeled zone](/research/dispatch-comparison-2025/zone-mae-grid.png)

Germany produces **1.406 TWh oil** against **2.818 TWh observed**; hourly oil MAE falls from **321.64 to 185.05 MW**. Its hourly oil correlation is only **0.127**. This is partial recovery, not a solved timing model. The other four comparable countries still dispatch no oil, despite observed output. Physical B06 output is not necessarily day-ahead market-accepted generation.

| Country | Matched hours | Observed oil TWh | Model oil TWh | Hourly MAE MW |
| --- | ---: | ---: | ---: | ---: |
| DE | 8,760 | 2.8175 | 1.4058 | 185.05 |
| BE | 8,760 | 0.5523 | 0.0000 | 63.04 |
| PL | 8,760 | 1.4880 | 0.0000 | 169.86 |
| SK | 8,758 | 0.4110 | 0.0000 | 46.93 |
| SI | 8,758 | 0.0005 | 0.0000 | 0.06 |

![National generation by fuel compared with original monthly Ember observations](/research/dispatch-comparison-2025/national-mix.png)

Generation totals are **availability-proportional allocations within aggregated equal-offer groups**, not independently identified plant dispatch. The country explorer supplies conditional lower/upper allocation bounds and original source rows. Ember is monthly and national; IRENA is capacity, not hourly generation. Hourly ENTSO-E generation is shown only where original PSR/geographical coverage exists. Missing NO5 prevents a complete Norwegian national hourly source total; its available zonal observations remain visible. Ember's “Other fossil” is broader than oil.

![Hourly prices in Germany, France, Spain and Norway during 15–21 January](/research/dispatch-comparison-2025/daily-prices.png)

The January plot answers the spike question with the corrected auction. On 20 January at 16:00 UTC (17:00 CET), DE-LU's actual day-ahead price is **€583.40/MWh**; on 15 January at the same hour it is **€377.99/MWh**. Missing scarcity premiums, operational constraints, hydro response and imperfect supply/network inputs remain possible contributors. These plots do not establish causal error shares. All headline metrics use the entire year, including negative and extreme prices.

## 4. Observed prices, provenance and verification

**Every observed comparison price comes from ENTSO-E A44**, in EUR/MWh, for the requested zone. Main day-ahead contract A01 is required; A07 intraday is excluded. Germany and Austria explicitly use **auction sequence 1 (SDAC)**, with no fallback to sequence 2. Other cached markets use their sole unclassified A01 series; non-coupled markets are not labelled SDAC. Four published quarter-hour samples are required for each UTC-hour mean; published block curves are expanded, while missing points remain missing.

The earlier research importer incorrectly preferred the highest auction sequence in DE-LU and Austria. This publication rebuilds the targets from original XML and independently replays all hourly cells. A separate Energy-Charts/SMARD check agrees **exactly for all 8,760 hours in DE-LU, AT, DK1 and DK2**; that reference never substitutes for ENTSO-E observations. Denmark's targets do not change. The map's archived prices also agree wherever covered; its existing coverage is preserved.

**No model was refitted or re-solved for this source correction.** We re-evaluate the saved verified annual oil/CHP solution. Its non-oil calibration used the earlier auction targets, so the updated MAE is a corrected-target evaluation of that frozen model—not evidence of a new correctly targeted fit, forecasting validation or recovered real bids. Earlier research MAEs are historical retained-target scores and should not be compared directly with the corrected scores here.

The displayed witness has 8,760 optimal hours and zero emergency supply. Its independent native-equation residual is **2.01e-07 MW**, maximum duality gap **€2.14e-06**, and objective replay error **€3.35e-08**, within the original gates. The original annual clearing loop took **29.55s**; input preparation and independent audit are separate costs. Numerical feasibility does not certify empirical accuracy.

The new export independently replays all countries' saved dispatch allocations, source generation, prices, original IRENA cells and Ember rows before publication. Hourly downloads round generation to 0.1 MW and prices to €0.001/MWh; summary scores use unrounded arrays. Country source coverage, shared DE-LU/IE-SEM areas and conditional bounds remain explicit.

## Conclusion

The heat-credit oil bid recovers meaningful German oil generation without forcing output or relaxing the network. It leaves large price and generation gaps. **Correct auction identity is now verified for the published comparisons; the next modeling step is to re-establish calibration against these corrected targets before interpreting further price improvements.** This checkpoint does not validate investment returns, adaptive storage or future-year forecasts.

- [All-zone full-year price metrics](/research/dispatch-comparison-2025/prices-by-zone.csv)
- [Matched-hour oil generation](/research/dispatch-comparison-2025/oil-generation.csv) · [Monthly country/fuel generation](/research/dispatch-comparison-2025/national-generation.csv)
- [Compact source and verification receipt](/research/dispatch-comparison-2025/summary.json) · [Country data and downloads](/countries/) · [Workbench methodology](/docs/workbench-methodology/)

Original bulk sources, calibration receipts and hourly solver witnesses remain outside Git. Data providers: [ENTSO-E](https://transparency.entsoe.eu/), [IRENA](https://www.irena.org/Publications), [Ember](https://ember-energy.org/data/), [NVE](https://www.nve.no/), [EIA](https://www.eia.gov/), [ECB](https://www.ecb.europa.eu/), [EEX](https://www.eex.com/), and the retained [PyPSA-Eur](https://github.com/PyPSA/pypsa-eur) source lineage. Independent price check: [Energy-Charts API](https://api.energy-charts.info/), CC BY 4.0 Bundesnetzagentur/SMARD.
