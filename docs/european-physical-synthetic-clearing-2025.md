# European dispatch: accepted seasonal-bid baseline

## Accepted baseline: single full-year reconstruction

The seasonal/time-of-day **calendar + Ember** supply-bid model is now the accepted research baseline. Its single annual `refit` solves all **8,760 hours of 2025**, with mean zonal MAE **28.96 EUR/MWh**, **12.8% lower** than the previous unfitted control (33.23). Mean price correlation is **0.573** and within-day correlation **0.535**. Annual clearing took **36.46s**, excluding preparation, fitting and audits; all hours were optimal with zero emergency supply.

These are **2025 in-sample reconstruction scores**: 2025 prices informed bids. Generation agreement and independently replayed physics are complementary checks, not statistical cross-validation. The model changes offers before physical clearing; it never replaces cleared prices afterward. Fixed hydro and all physical constraints remain unchanged. This acceptance does not replace the browser scenario engine or validate investment effects.

## Research target and accepted-baseline diagnosis

The target is **below 10 EUR/MWh equal-zone MAE for all 8,760 hours of 2025**, across all 41 complete observed-price areas, with per-zone results retained. Seven modeled areas still lack complete observed prices. Reaching 10 from the accepted baseline requires a further **65.5% reduction**; that improvement is a research goal, not a demonstrated outcome.

| Largest price errors | Annual MAE, EUR/MWh | Signed bias, EUR/MWh |
| --- | ---: | ---: |
| DK2 | 50.15 | -38.55 |
| NO5 | 47.29 | -24.46 |
| EE | 44.56 | +9.21 |
| NO1 | 42.57 | -22.59 |
| FI | 40.88 | +0.16 |
| LV | 40.82 | +3.87 |
| LT | 40.82 | +4.29 |

Both daily levels and intraday movements matter. Mean daily-level error is **22.96 EUR/MWh**; after removing each day's mean error, within-day error remains **20.06 EUR/MWh**. These are descriptive diagnostics calculated with observed prices; their MAEs do not add and they are not usable forecast corrections. Daily fuel changes alone cannot correct all hourly shape errors.

The following national quantities come from the **accepted single annual refit**, independently re-aggregated and checked against twelve-month Ember references. Coal combines hard coal and lignite. Model points illustrate saved-group allocations; conditional bounds and national/technology scope differences remain relevant.

| Country / resource | Model TWh | Ember TWh | Difference TWh |
| --- | ---: | ---: | ---: |
| DE / Wind | 172.13 | 131.17 | +40.97 |
| DE / Solar | 108.10 | 89.97 | +18.13 |
| DE / Coal | 45.71 | 94.86 | -49.15 |
| DE / Gas | 62.06 | 79.33 | -17.26 |
| FR / Nuclear | 345.40 | 371.69 | -26.29 |
| ES / Wind | 43.95 | 55.58 | -11.63 |

**Next controlled improvements:** first reconcile country-specific wind/solar capacity and weather conversion, biomass/coal classification and reporting coverage; audit dated nuclear/thermal outages. Compare price and mix changes together. Do not scale weather availability to observed generation. Then test source-backed daily thermal costs with current bid coefficients fixed, followed by a separately labelled refit if warranted. Explore resource-specific operating bids and negative-price behaviour after those source checks; a uniform negative-bid change would not explain the excess negative prices already present in some Norwegian zones.

**Fuel precision today:** gas uses monthly World Bank TTF benchmarks; oil uses monthly Brent, both converted using monthly mean reciprocal ECB FX. Carbon is fixed at **80 EUR/t** and coal/lignite retain technology-cost assumptions. These are not daily fuel quotes. Resource bids use fuel/efficiency + carbon × emissions/efficiency + variable O&M, before the bounded seasonal correction. Gas needs gas-hub data rather than oil as a proxy.

[Ember's daily fuel-cost methodology](https://ember-energy.org/data/european-electricity-prices-and-costs/) identifies national gas hubs, API2 coal and EU/UK carbon contracts, but its embedded fuel chart explicitly restricts downloads because of licensing; no series has been adopted. [MIBGAS's 2025 archive](https://www.mibgas.es/en/file-access?path=AGNO_2025/XLS) now has **365 source-replayed delivery days** of Spanish PVB and Portuguese VTP last/average day-ahead indices. These are source-computed indices, including provider estimates in illiquid periods; they are not a Europe-wide TTF substitute. The daily trial below uses them in ES/PT; the accepted baseline remains unchanged. [EIA daily Brent](https://www.eia.gov/dnav/pet/hist_xls/RBRTEd.xls) is an oil-proxy candidate. The daily trial below documents reconciled delivery dates and nontrading-day treatment; broader gas-hub coverage, heating-value/efficiency and delivered-fuel assumptions remain open.

## Dated nuclear availability — controlled source test

The accepted model applies a flat 2024 national nuclear energy-availability factor throughout 2025. For its French source fleet this permits **46.97 GW** at every hour. [RTE's daily availability series](https://analysesetdonnees.rte-france.com/production/nucleaire), derived from REMIT reporting, provides all **365 dates of 2025**: reported available power ranges **33.45–56.23 GW**, averaging **45.72 GW**. These are available supply, not observed generation.

Three finite controls replace only French **source-country** nuclear availability: a constant RTE annual mean, daily values mapped to UTC dates, and daily values mapped to Paris dates. The mean control separates level from daily shape approximately. The source dates carry no timezone; both mappings are disclosed assumptions, not a certified correction. Paris mapping uses the adjacent **1 January 2026** boundary record and preserves 23/25-hour local days. Each daily value is repeated within its day: **a daily national proxy is not a verified hourly maximum or unit-level outage schedule**. The data are revised historical observations, not evidence of what bidders knew in advance. [EDF's annual Kd](https://opendata.edf.fr/datasets/disponibilite-du-parc-nucleaire-d-edf-sa-depuis-2002) describes technical availability with different exclusions; fleet/definition differences must be reconciled before treating these sources as interchangeable. No rescaling to Kd or observed generation is performed.

National available MW are allocated by retained source-fleet nameplate shares, within original nominal limits. Source membership, geographic placement and static GSKs stay distinct; plant outage geography is unresolved. All renewable inputs, fuel anchors, accepted seasonal/Ember bids, demand, fixed hydro and grid constraints stay unchanged. This test does **not** combine the preceding renewable changes or refit bids.

| Full-2025 case | European price MAE | FR price MAE | Within-day correlation, Europe | FR-source nuclear dispatch, TWh | Generation-interval mismatch |
| --- | ---: | ---: | ---: | ---: | ---: |
| Accepted baseline | 28.964 | 23.830 | 0.535 | 345.40 | 0.2995 |
| RTE annual mean | 28.912 | 22.818 | 0.536 | 340.21 | 0.2993 |
| RTE daily / UTC dates | 28.947 | 24.011 | 0.537 | 349.16 | 0.2994 |
| RTE daily / Paris dates | 28.949 | 24.015 | 0.537 | 349.19 | 0.2994 |

Price MAEs are EUR/MWh, equal-zone Europe includes all 41 complete observed-price areas, and all four witnesses retain **8,760 optimal hours with zero emergency supply**. National-source dispatch is a proportional allocation illustration, with conditional bounds in the receipt; national Ember/geographic reporting scope remains separate. The normalized monthly generation score is not total-fleet percentage error. [Every zone's price metrics](/research/dispatch-comparison-2025/nuclear-availability-prices-by-zone.csv) and [monthly available/dispatch quantities](/research/dispatch-comparison-2025/nuclear-availability-by-month.csv) retain the full comparison.

**Result:** daily availability raises French-source nuclear dispatch from 345.40 to about 349.2 TWh, closer to the 371.69 TWh national Ember reference but still not a scope-reconciled match. France's price correlation rises from 0.802 to about 0.817, while its MAE worsens from 23.83 to about 24.01 EUR/MWh. Europe-wide MAE only changes from 28.964 to about 28.95. The annual-mean control lowers price MAE further but worsens the nuclear generation total. Neither mapping nor mean-versus-shape controls deliver a clear joint improvement, and the <10 target remains distant. This French daily proxy does not rule out the value of better hourly/unit outage data elsewhere.

The grid below adds the three nuclear controls against the accepted baseline, separately from the wind/PV experiment's matched control. Independent replay checks source records/calendar, national MW allocation, original network physics, LP duals and annual price/mix/trade metrics. No baseline promotion or validated investment effect follows from this test.

## Wind/solar inputs and resource bids — 19 October 2026

**Wind correction:** the accepted baseline scales total national wind but retains the old fleet's onshore/offshore shares. The new case applies separate [IRENA 2026 publication](https://www.irena.org/-/media/Files/IRENA/Agency/Publication/2026/Mar/IRENA_DAT_RE_capacity_statistics_2026.pdf) end-2024/end-2025 subtype trajectories in **12 source countries**, preserving original within-subtype weather/location shares. Missing or inconsistent parent/subtype records retain original wind, with status in the [capacity audit](/research/dispatch-comparison-2025/renewable-capacity-audit.csv). Parent and child capacities are never added. For example, the old Dutch split assigned about 7.3 GW offshore at the start of 2025 versus IRENA 4.75 GW. Source-country identity and geographic/GSK allocation proxies remain distinct; original static GSKs stay fixed to isolate availability effects.

**Solar sensitivity:** the original CSi panel model already includes 10% inverter losses. [PVGIS](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/pvgis-user-manual_en) uses 14% as a generic overall system-loss default. Replacing the 10% factor with 14% multiplies available PV by **0.86/0.90**, a 4.44% reduction; applying another 14% would double-count inverter losses. This is a declared generic sensitivity, **not a verified country-specific fleet correction**. Original temperature, irradiance, south-facing 35° geometry, capacity trajectory and chronology remain; observed generation never replaces availability.

**Resource bids:** after both input changes, the lower half of available PV, wind or both is offered at **−10 EUR/MWh**, with the upper half at 0. These are simple synthetic bid controls, not measured subsidy entitlements or forced generation. Accepted gas/coal/nuclear calendar/Ember coefficients, demand, fuel, hydro and grid stay fixed; no refit. An unmodified matched control is necessary because separating formerly equal-price wind/solar columns can change duals and illustrative allocations. Its price MAE is 28.963873, versus the retained accepted baseline 28.963975.

| Full-year case | Price MAE, EUR/MWh | Within-day correlation | Generation-interval mismatch |
| --- | ---: | ---: | ---: |
| Matched control | 28.964 | 0.535 | 0.3007 |
| IRENA wind subtypes | 28.984 | 0.535 | 0.2965 |
| PV system-loss sensitivity | 28.892 | 0.535 | 0.2952 |
| Both input changes | 28.912 | 0.536 | 0.2911 |
| Both inputs + PV bids | 28.914 | 0.536 | 0.2915 |
| Both inputs + wind bids | 29.000 | 0.535 | 0.2908 |
| Both inputs + both bids | 29.004 | 0.535 | 0.2912 |

All seven cases clear **8,760 optimal hours with zero emergency supply**, retaining all 41 observed-price areas. Generation mismatch is the existing normalized monthly country/fuel interval score, not total-fleet percentage error; conditional allocation intervals do not span every possible equal-cost optimum. No case is promoted automatically. [All-zone hourly-price metrics](/research/dispatch-comparison-2025/renewable-source-prices-by-zone.csv) include every modeled area, with unknown observations blank.

![Every modeled zone and every source/bid control: price MAE changes](/research/dispatch-comparison-2025/zone-mae-grid.png)

**Conclusion:** both input changes reduce Europe-wide MAE only from 28.964 to 28.912 EUR/MWh, far from the <10 target. Germany improves from 21.57 to 20.83, while Spain worsens from 24.07 to 24.25. Wind subtype correction improves the quantity score but slightly worsens price MAE on its own; the generic PV loss sensitivity has the lowest price MAE. None of the negative renewable bid controls improves on the combined-input case. These are modest diagnostics, not evidence for adopting a universal negative bid or a measured PV derating.

Independent source-capacity, availability, component-physics, LP dual, price and monthly generation/trade replay verifies all seven cases. Wind/PV source profiles still represent generic turbines, idealized panel geometry and potential-based spatial layouts; subtype capacity corrections do not establish actual site output or resolve curtailment, outages and reporting scope.

## Previous daily-fuel check

Daily EIA Brent/ECB oil quotes and MIBGAS gas indices in ES/PT changed Europe-wide MAE from 28.964 to 28.950 EUR/MWh with coefficients frozen. Gas elsewhere remained monthly TTF; this was not a Europe-wide daily-gas test. Original heating-basis assumptions and explicit first-day fallbacks remained. The source/physics/dual replay is retained; see the [all-zone fuel comparison](/research/dispatch-comparison-2025/daily-fuel-prices-by-zone.csv). The accepted baseline was unchanged.

## Secondary development evidence

The sections and figures below retain the **previous unfitted baseline versus out-of-fold seasonal-model comparison** as secondary development evidence. Their “baseline” labels mean the previous control; their “exploratory” results combine three fits and are **not the accepted single annual refit**. Do not mix those generation/price results with the annual-refit headline.



## Summary

The exploratory model now uses **seasonal and time-of-day supply-bid patterns, without residual demand as a fitted bid predictor**. Demand and weather-dependent available supply still enter the physical clearing problem. Monthly Ember generation informs an optional resource-specific seasonal bid correction; ENTSO-E prices validate the resulting coupled clearing prices.

Across **41 observed-price zones**, full-2025 out-of-fold price MAE changes **33.23 → 29.18 EUR/MWh**, mean correlation **0.502 → 0.565**, and within-day correlation **0.407 → 0.527**. MAE improves in **38/41 zones**; Belgium, France and NO5 worsen. These are retrospective reconstruction/interpolation results, not verified actual bids or an accepted investment model.

## 1. Baseline model and data

**Clearing.** An hourly sparse linear program minimizes accepted resource-bid cost under fixed demand, original available generation and network constraints. Zonal balance duals provide prices. Hours are independent: daily processing does not add ramping, unit commitment, batteries or intertemporal reservoir optimization.

**Geography.** The retained network has **48 clearing areas and 145 physical buses**, with separate NO1–NO5, SE1–SE4, DK1/DK2 and seven Italian zones. DE-LU is combined; peripheral modeled areas are not all certified commercial bidding zones. Capacity-based generation shift keys locate zonal supply on physical buses. AC flow sensitivities, electrical-island balances, intrazonal branch limits and HVDC bounds/losses remain. A uniform **0.7 security factor** applies to branch ratings. These are model-derived N-0 constraints, not JAO commercial domains, explicit N-1 security or full EUPHEMIA allocation.

**Supply, demand and hydro.** Original resource bids use plant fuel/efficiency/carbon/operating-cost profiles; wind/solar retain zero offers. No earlier price-fitted thermal step markups are inherited in this experiment. Prepared 2025 demand is fixed, with source/member allocation proxies where historical aggregation crossed zones; it is not certified metered zonal load everywhere. Reservoir output is precomputed and fixed hourly. Norway uses NVE weather-driven HBV inflow and boundary stocks; other countries retain source schedules. Inventories, turbine limits and efficiency remain unchanged, without daily water resets. Run-of-river is an available offer. Fixed reservoir output cannot adapt to an investment or acquired bidding flexibility. Emergency offers at 10,000 EUR/MWh diagnose shortage and are excluded from real generation totals.

| Component | Source and treatment |
| --- | --- |
| Grid, plants, demand and inherited profiles | Pinned [PyPSA-Eur](https://github.com/PyPSA/pypsa-eur) v2026.08.0 backbone and retained source/replay coefficients. Location/load splits include proxies; nuclear availability ending in 2024 is a proxy, not audited 2025 outages. |
| Wind/solar availability | [IRENA](https://www.irena.org/Data) end-2024/end-2025 capacity interpolation plus retained ERA5-derived hourly profiles. Linear commissioning is assumed; observed generation never replaces availability. |
| Fuel and baseline bids | [World Bank](https://www.worldbank.org/en/research/commodity-markets) monthly TTF/Brent, [ECB](https://data.ecb.europa.eu/) FX, inherited carbon/efficiency/VOM assumptions. Delivered fuel, heating-value and EUA details remain imperfect. |
| Norwegian reservoir water | [NVE](https://www.nve.no/energi/analyser-og-statistikk/hydrologiske-data-til-kraftsituasjonsrapporten/) HBV inflow, stocks and capacity, with chronological stored/electrical-unit conversion. Retrospective revisions, national pooling and gross-stock/net-inflow compatibility remain limitations. |
| Price targets / hourly generation checks | [ENTSO-E Transparency](https://transparency.entsoe.eu/) A44 prices and A75 generation by type, source-hashed and UTC-aligned. Test-month prices do not construct bids. |
| Monthly generation signal and national check | [Ember](https://ember-energy.org/data/) national monthly fuel generation. Only fitting months inform bid corrections; each test month's generation remains excluded from its calibration and selection. |

## 2. Exploratory seasonal bids

The bids themselves change **before clearing**; predicted prices are never overwritten afterward. Physical demand, fleet capacity, hourly availability, hydro, GSKs and network rows stay identical to the baseline.

**Calendar pattern.** Each zone has a smooth annual level plus daily morning/evening harmonics. Annual sine/cosine terms also change the daily pattern through the seasons, rather than reusing one winter profile in summer. The 15 calendar coefficients comprise an intercept, two annual terms, four daily terms and eight seasonal–daily interactions. Local clock hours include DST. Ridge fitting uses only fitting-month observed-minus-baseline price errors, clipped at ±100 EUR/MWh; unsupported price zones get zero coefficients. No residual-demand, demand or observed-generation series enters this hourly feature vector.

**Ember signal.** Monthly data cannot identify hourly generation or orders. For gas, coal and nuclear, a national generation target above the baseline's conditional generation range proposes a lower bid; a target below the range proposes a higher bid. Within-range targets propose zero. The normalized correction is bounded and smoothed with an annual intercept/sine/cosine, using fitting months only. Original nameplate membership weights this national signal into mixed offers; it does not allocate observed generation to bidding zones or create capacity.

| Resource | Change relative to baseline |
| --- | --- |
| Gas and coal/lignite | Calendar correction, optionally plus Ember seasonal signal; total adjustment capped at ±30 EUR/MWh |
| Nuclear | Quarter-strength correction, capped at ±7.5 EUR/MWh; no peaking blocks |
| Wind, solar and other offers | Unchanged |
| Final bids / physical quantities | Offers floored at zero; available MW and all physical constraints unchanged |

This is a transparent effective-bid hypothesis. Price fitting may compensate for incorrect capacity, demand, constraints or outages; it does not uniquely recover actual supply orders. Generation and implied-trade checks therefore accompany price validation. Fixed-hydro areas can remain poorly priced even with better thermal bids.

## 3. Validation across seasons

The earlier Jan–April/May–June/July–December split tested extrapolation from early-year conditions. It did not represent every season in fitting. The new design rotates **whole months**, with one month from each quarter in each role:

| Fold | Fit months | Select months | Test months | Selected variant | Test price MAE: baseline → exploratory |
| --- | --- | --- | --- | --- | ---: |
| 1 | 3, 6, 9, 12 | 2, 5, 8, 11 | 1, 4, 7, 10 | Calendar + Ember | 32.57 → 28.24 |
| 2 | 1, 4, 7, 10 | 3, 6, 9, 12 | 2, 5, 8, 11 | Calendar + Ember | 34.96 → 31.28 |
| 3 | 2, 5, 8, 11 | 1, 4, 7, 10 | 3, 6, 9, 12 | Calendar + Ember | 32.18 → 28.05 |

Each fold fits its own coefficients, then selects among exactly **unchanged, calendar-only, calendar-plus-Ember** bids. The selection score gives equal weight to control-normalized hourly price MAE, daily-demeaned MAE, monthly generation-interval error and implied-trade interval error, plus a small bid-size penalty. The simplest variant wins numerical ties. First/last 48 hours of fitting and selection months are excluded from price fitting/scoring; monthly Ember checks retain whole months. No test-month price or generation target participates in its fold's fitting or selection.

**Price/mix trade-off:** adding Ember worsened selection-period price MAE relative to calendar-only bids (fold 1: 30.81 → 31.58; fold 2: 27.06 → 27.47; fold 3: 28.19 → 28.75 EUR/MWh), while improving the joint generation/trade score. That combined score selected it; this is not evidence that Ember alone improves prices. Calendar-only bids were not separately evaluated on the outer test months, so their out-of-fold price accuracy remains unmeasured.

The primary comparison stitches the three disjoint test sets into **all 8,760 hours of 2025**. It is an **out-of-fold composite of three fitted models**, not one deployed annual policy. Ramps exclude boundaries between fold fits. This tests **within-year seasonal interpolation**, using other months that may be later in calendar time. Purging reduces boundary dependence; it does not make months or coupled zones statistically independent. Previously inspected 2025 and reused model architecture prevent an untouched-validation claim. A subsequent year is needed to test genuine forecasting; capacity/weather inputs also assume perfect exogenous information. These scores are not directly comparable to earlier July–December-only headlines.

A separate final reconstruction uses **Calendar + Ember**, chosen by the mode of inner-selection winners, then refits on all 2025 fitting information. Its MAE is **28.96 EUR/MWh**, correlation **0.573**: **in-sample**, not additional validation. Its witness is retained separately; all primary figures below use out-of-fold results.

## 4. Generation and price results

![All-area generation and price errors, baseline versus out-of-fold seasonal bids](/research/dispatch-comparison-2025/overview.png)

| Full-2025 metric | Baseline | Exploratory, out of fold |
| --- | ---: | ---: |
| Equal-zone hourly price MAE, EUR/MWh | 33.23 | 29.18 |
| Mean zonal price correlation | 0.502 | 0.565 |
| Mean within-day price correlation | 0.407 | 0.527 |
| Daily-demeaned price MAE, EUR/MWh | 23.03 | 20.32 |
| Median covered-fuel generation volume error, % | 50.1 | 42.2 |

Historical out-of-fold zone metrics remain in the downloads; the all-zone grid above shows the current source/bid experiment.

Generation comparison covers **38 reporting areas**, with different fuel/hour coverage. Its error sums absolute fuel-volume differences and divides by observed generation on matched known hours; it can exceed 100% and is not a share percentage-point error or complete-fleet score. **31/38** areas improve. Saved equal-bid group dispatch is allocated proportionally to original available MW for illustration. Downloads retain conditional lower/upper allocations; they are not jointly attainable or all possible LP optima. Missing observations stay unknown; pumped-storage output remains separate from primary generation.

Within-day metrics subtract each complete UTC day's mean; the example profiles below instead group by local clock hour with DST.

## 5. Norway, Germany, Spain and France

![National annual generation shares and covered-fuel TWh against Ember](/research/dispatch-comparison-2025/national-mix.png)

This national Ember cross-check uses all twelve months, separately from hourly ENTSO-E reporting areas. Only fuels with complete monthly references enter all three bars; missing types are excluded, never filled with zero. National Norwegian totals include NO5, which has no comparable hourly zonal generation. Germany's generation excludes Luxembourg while its price is DE-LU. France uses national model membership including modeled Corsica. Geographic, gross/net and taxonomy differences remain material.

| Area | Generation volume error, %: baseline → exploratory | Price MAE, EUR/MWh: baseline → exploratory | Price correlation: baseline → exploratory |
| --- | ---: | ---: | ---: |
| NO1 | 75.4 → 75.4 | 42.86 → 42.65 | 0.037 → 0.027 |
| NO2 | 29.3 → 29.3 | 41.60 → 39.37 | 0.166 → 0.195 |
| NO3 | 41.9 → 41.8 | 35.02 → 34.66 | 0.016 → 0.009 |
| NO4 | 17.9 → 15.5 | 35.86 → 35.08 | 0.007 → 0.007 |
| NO5 | — → — | 46.63 → 47.33 | -0.133 → -0.147 |
| DE-LU | 58.9 → 48.2 | 23.10 → 21.22 | 0.776 → 0.825 |
| ES | 18.9 → 17.3 | 26.55 → 24.34 | 0.708 → 0.763 |
| FR | 15.4 → 15.1 | 22.74 → 23.63 | 0.766 → 0.797 |

DE-LU generation means Germany national; FR is national. Norway rows use available zonal series. A dash denotes unavailable generation verification.

**Norway:** modeled national hydro is **146.11 TWh** versus Ember **141.60 TWh**. NO5 price correlation is **-0.147**, MAE **47.33 EUR/MWh**. National volume agreement cannot certify regional water allocation, and new thermal bids cannot reschedule fixed reservoir injections.

**Germany:** gas is **58.25 TWh** versus Ember **79.33**, coal **48.30** versus **94.86**, wind **172.12** versus **131.17**. Price correlation **0.825** must be read alongside those quantity mismatches and demand-scope assumptions.

**Spain:** price MAE is **24.34 EUR/MWh**, bias **+0.85**, within-day correlation **0.746**. National gas is **57.11 TWh** versus **52.13** observed; wind **43.86** versus **55.58**.

**France:** nuclear is **345.37 TWh** versus **371.69**, hydro **58.33** versus **51.63**. Price MAE is **23.63 EUR/MWh**. Nuclear availability/outages and fixed hydro remain source assumptions, irrespective of fitted price accuracy.

![Winter and summer observed versus out-of-fold mean local-hour prices in NO2, DE-LU, ES and FR](/research/dispatch-comparison-2025/daily-prices.png)

Profiles separate **winter (Jan/Feb/Dec) and summer (Jun/Jul/Aug)** mean local-hour prices, with DST; solid lines are observed, dashed modeled. They are not an individual day's forecast. Spain's annual mean daily range is **80.13** versus observed **98.16 EUR/MWh**; ramp MAE **12.07**, with **0 modeled versus 556 observed negative-price hours**. Seasonal mean profiles can conceal particular-day/tail errors; downloads include them.

## Conclusion and reproducibility

Seasonal calendar bids offer a direct way to vary supply offers daily and annually without a residual-demand predictor. Ember adds a generation-consistency signal, rather than an artificial hourly supply series. The fold selections and out-of-fold results assess that hypothesis under unchanged physical constraints. **The annual refit is the accepted research baseline; retain the unfitted control and out-of-fold evidence separately.** Prices alone cannot identify true bids or validate investment effects; fleet/weather quantities, outages, Nordic water/geography and demand scope still require source work.

Independent replay checks calendar/DST features, month exclusion, price/Ember proposals, selection, original component physics, cost/LP duals, stitched test witnesses and separate refit. Maximum physical residual is **2.6e-06 MW**, duality gap **EUR 0.000033**. The out-of-fold year has **8,760 optimal hours**, emergency supply **0.000000 MWh**. Fresh test clearing totals **38.20s**; full preparation/selection/tests/refit command **282.10s**. Independent report replay additionally verifies generation geography, source observations, allocations and metrics. Research-baseline promotion is user-authorized; browser replacement, investment acceptance and deployment are separate.

- [All-zone price metrics](/research/dispatch-comparison-2025/prices-by-zone.csv), [generation coverage/errors](/research/dispatch-comparison-2025/generation-by-area.csv), [fuel volumes/hourly errors/conditional bounds](/research/dispatch-comparison-2025/generation-by-fuel.csv), [national Ember comparison](/research/dispatch-comparison-2025/national-generation.csv).
- [Compact provenance and verification receipt](/research/dispatch-comparison-2025/summary.json). Bulk hourly/source/replay evidence stays locally cached outside Git.
- [Seasonal bid formulation](tools/seasonal_calendar_bids_2025.py), [independent model replay](tools/audit_seasonal_calendar_bids_2025.py), [report derivation](tools/prepare_seasonal_dispatch_report_2025.py), [independent report replay](tools/audit_seasonal_dispatch_report_2025.py), [renderer](tools/write_concise_dispatch_report_2025.py).
