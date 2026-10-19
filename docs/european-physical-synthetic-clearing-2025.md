# Inverse market modelling: European 2025 bid calibration

## Summary

**The predeclared near-best ensemble contains only one member; other research-eligible fits exist but are outside that narrow score cutoff.** The accepted seasonal-bid baseline has full-year price MAE **28.964 EUR/MWh**. The score-winning eligible state, **r2-s6**, gives **28.167 EUR/MWh** (2.75% lower), with generation-interval mismatch **0.2995→0.2551** and trade mismatch **0.1719→0.1436**. The unrestricted price leader gives **27.800 EUR/MWh**; eligibility is reported below rather than hidden. The <10 EUR/MWh research target remains unmet.

This is **2025 in-sample reconstruction**, using all 2025 prices and generation to fit and select bids. Generation/trade agreement and independently checked physics are complementary evidence, **not independent forecast validation**. The primary rule retained **1** bid state(s): **r2-s6**. Their min/max price envelope contains observed prices in **0.13%** of eligible zone-hours. This is descriptive coverage of a finite tested family, not a confidence interval or a posterior probability. The accepted baseline and browser scenario engine remain unchanged; these are experimental fits.

## 1. What inverse market modelling means

Our forward problem takes supply bids, available generation, demand and network constraints, clears the system, and produces dispatch and balance-dual prices. The inverse problem asks which plausible bid parameters could explain observed outcomes while retaining that clearing mechanism.

In compact form, each hour solves $x_t(\theta)\in\arg\min_x c_t(\theta)^T x$ under the same physical constraints; $p_t(\theta)$ is its zonal balance-dual vector. Calibration compares $p_t(\theta)$ and the resulting generation/trade quantities with observations. Observed prices never overwrite the cleared prices.

**Identification is the central difficulty.** A 100 EUR/MWh price might reflect a higher gas offer, less available cheap generation, or constrained imports. The same price can arise from different mechanisms with different investment responses. A resource that never influences prices is poorly identified by price data. Equal-price aggregation and LP dual nonuniqueness add ambiguity; national generation totals do not identify actual hourly plant dispatch.

[Chan, Mahmood and Zhu's review](https://arxiv.org/abs/2109.03920) explains inverse optimisation as estimating objectives or constraints that explain decisions. [Bertsimas, Gupta and Paschalidis](https://arxiv.org/abs/1308.3397) develop data-driven estimation from equilibrium observations. These motivate an optimisation-consistent approach, but do not establish that our approximate European market is the true data-generating mechanism.

[Liang and Dvorkin](https://arxiv.org/html/2302.05498v2) study marginal offer recovery from electricity-market clearing information. Their recovery guarantees depend on their assumptions and observable marginal behaviour; non-marginal offers remain unidentified. We have zonal prices and aggregated generation rather than complete plant-level clearing observations, so **we do not inherit their uniqueness or convergence guarantees**. [Birge, Hortaçsu and Pavlin's MISO study](https://doi.org/10.1287/opre.2017.1606) investigates constraint recovery from price outcomes under specified assumptions; it does not authorize freely tuning our physical network until prices match. [Babier et al.](https://doi.org/10.1287/ijoo.2019.0045) fit inverse models from multiple decisions; their ensemble-consensus framework differs from our finite set of near-best parameter fits.

**Implemented here:** a bounded two-round inverse-calibration heuristic, with actual full-year forward solves and an explicit near-best fit selection rule. It is not an exact global bilevel inverse optimisation, proof of actual bids, exhaustive solution distribution or strategic Nash-equilibrium model.

## 2. Baseline model, sources and what stays fixed

The single accepted reference is `seasonal-calendar-v1/refit`: **48 modeled areas, 145 physical buses, 41 complete observed-price zones and all 8,760 UTC hours of 2025**. Separate Nordic and Italian zones are retained; geographic/source allocation proxies remain. Independent hourly sparse LPs minimize offered supply cost. Daily grouping does not add unit commitment, ramping, storage scheduling or complex block orders. This is EUPHEMIA-inspired synthetic clearing, not EUPHEMIA reproduction.

| Component | Source and treatment |
| --- | --- |
| Physical network and fleet | Pinned [PyPSA-Eur](https://github.com/PyPSA/pypsa-eur) v2026.08.0; PTDF/GSK, electrical islands, HVDC bounds/losses and 0.7 branch-rating factor. Model-derived N-0 limits, not certified JAO commercial domains or explicit N-1 security. |
| Wind and solar | Original 2025 [ERA5](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels)/[atlite](https://atlite.readthedocs.io/) weather profiles, [IRENA](https://www.irena.org/Data) end-2024/end-2025 capacity interpolation. Assumed commissioning, generic turbines/panels and potential-based layouts; generation never replaces availability. |
| Demand | Prepared [ENTSO-E](https://transparency.entsoe.eu/)-based 2025 hourly demand, with regional allocation/scope proxies; fixed in every fit. |
| Hydro and nuclear availability | Retained fixed hourly reservoir schedule and source water/stock evidence; Norway uses NVE HBV/stock inputs. Nuclear retains the 2024 national energy-availability-factor proxy. No adaptive hydro or RTE availability change in this trial. |
| Bid anchors | [World Bank](https://www.worldbank.org/en/research/commodity-markets) monthly TTF/Brent, [ECB](https://data.ecb.europa.eu/) FX, source efficiency/VOM and 80 EUR/t carbon assumption; accepted seasonal/local-clock and Ember bid correction. Delivered fuel and operational details remain imperfect. |
| Targets | Source-hashed ENTSO-E A44 hourly price aggregates; [Ember](https://ember-energy.org/data/) monthly national Wind/Solar/Nuclear/Gas/Coal generation and signed net exports. Unknown observations remain unknown. |

The five-fuel mix score excludes hydro, biomass and other generation; trade is **implied generation minus model demand**, not verified physical border flow. National/zone boundaries and gross/net reporting differ. Updated hourly zonal ENTSO-E A75 generation checks have not been derived for these inverse fits; prior baseline/OOF A75 evidence is separate. Passing the five-fuel national screen does not certify every zone or resource. Allocation points are proportional illustrations; conditional fuel/country bounds preserve saved group totals, are not jointly attainable bounds on all primal optima and do not identify real plant dispatch.

Recent source diagnostics remain separate: [wind/PV controls](/research/dispatch-comparison-2025/renewable-source-prices-by-zone.csv), [IRENA capacity audit](/research/dispatch-comparison-2025/renewable-capacity-audit.csv), [RTE nuclear controls](/research/dispatch-comparison-2025/nuclear-availability-prices-by-zone.csv), and [daily-fuel controls](/research/dispatch-comparison-2025/daily-fuel-prices-by-zone.csv). None was silently combined with this accepted-baseline comparison.

## 3. Implemented search and safeguards

1. Start from the accepted annual witness and its exact offer grouping. Five features—constant, annual sine/cosine and first local-clock daily sine/cosine—propose smooth **zone/resource** gas, coal and nuclear bid corrections. Fit observed-minus-parent-price residuals only when that model has a local interior offer matching its saved zonal dual. Require 168 supported hours and ridge 336; clip fitting residuals at ±100. An interior offer has neither generation bound active, so its marginal bid equals the local price in this formulation. Re-clearing is essential because the marginal offers and binding network constraints can change after a bid adjustment. This labels supporting model evidence, not unique real price setters. Unsupported groups receive zero proposals.
2. Add a national annual fuel-mix proposal only when all 12 reference months exist. Underproduction outside the conditional annual allocation interval proposes a lower offer; overproduction proposes a higher offer. Each increment is bounded at ±15 EUR/MWh and weighted into groups by original nameplate membership. It changes **bids, never availability**.
3. Accumulate the smooth/mix correction, capped at ±45 EUR/MWh for gas/coal and ±15 for nuclear. Thermal block premiums are nonnegative and monotone, capped at 60 gas/40 coal on the upper block; intermediate premium is 35% of that. Nuclear has no peaking block. Final thermal/nuclear bids have a zero floor; renewable and all other bids stay unchanged. Bounds are declared experimental assumptions, not observed market bids or subsidy evidence.
4. Make exactly two rounds of six declared step tuples, at most 12 new annual clears. Each round uses the best eligible completed state as parent. Identical bid hashes reuse their witness. There are no per-hour fitted prices, extra adaptive rounds or physical-constraint searches. The replay found supported zone/resource groups **[39, 40]** across the two rounds; each supported group estimates five coefficients, plus bounded national fuel signals.
5. Score every unique state using **55% normalized price MAE +20% normalized daily-demeaned price MAE +20% normalized generation-interval error +5% normalized trade-interval error**, plus 0.01 times availability-weighted squared bid departure. Normalization uses the accepted baseline. A research-eligible state must not increase price MAE, may increase each other score by at most 2%, and must clear all hours with zero emergency. These are predeclared trial filters, **not empirical product acceptance gates**.
6. Retain at most five distinct eligible bid states within 0.01 of the best regularized score and 1 EUR/MWh of that score winner's MAE. Keep the score winner first, then choose diverse normalized parameter vectors. Equal weights are descriptive; we do not infer a likelihood or assign posterior probabilities. The baseline can remain a member, and the set can collapse to one if alternatives fail.

The complete [predeclared design](config/inverse-bid-ensemble-2025.json) fixes every step, bound and filter before outcomes. The continuous inverse problem is nonsmooth and nonconvex through changing active constraints. Hourly LP optimality is independently checked; **there is no outer-search global-optimum or convergence certificate**.

## 4. Full-year results and model distribution

| State | Price MAE | Mean zonal r | Within-day MAE | Generation score | Trade score | Eligible? |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Accepted baseline | 28.964 | 0.573 | 20.063 | 0.2995 | 0.1719 | yes |
| Joint-score fit (r2-s6) | 28.167 | 0.593 | 19.568 | 0.2551 | 0.1436 | yes |
| Price-focused fit (r2-s2) | 27.800 | 0.594 | 19.541 | 0.2914 | 0.1678 | yes |

Price errors are EUR/MWh. Scores for generation/trade are normalized interval discrepancies, not total-fleet percentage errors. Trial IDs describe steps in the same solver: `r2-s6` means round 2, step 6, not a separate network implementation. The joint fit reaches gas/coal upper-block premiums **60/40 EUR/MWh**; the price-focused fit reaches **30/20**. Both also change bounded smooth/mix bid terms; neither changes available generation. **10/13** unique states pass the research filters. The table contains the anchor, every retained member and the overall price leader; [all search states](/research/dispatch-comparison-2025/inverse-search-cases.csv) include excluded cases and exact parent/step provenance.

![All search states: price and generation trade-offs](/research/dispatch-comparison-2025/overview.png)

The retained states are alternative explanations **within one unchanged physical network**, not randomly perturbed networks centered on observations. A narrow envelope can simply mean that the tested bid family misses the same price movements. Coverage of **0.13%** is reported rather than assuming the observed market lies inside the fit distribution. With one member, the envelope has zero width and coverage becomes an approximate numerical equality count, not useful uncertainty quantification. Envelope width excludes uncertainty from weather, capacity, demand scope, network structure and missing market mechanisms. Averaged ensemble prices are not prices from a single cleared system, and are not the primary model metric.

**Post-run cutoff diagnostic, not a change to primary selection:** applying wider score tolerances to the same completed states gives the counts below, keeping all other filters and the 1 EUR/MWh limit. No additional solve or primary-member substitution is made. This shows dependence on the analyst's tolerance; it does not establish probabilities. A second diagnostic uses **all 10 research-eligible states**, without the near-best score cutoff. That wider min/max envelope spans observed prices in **14.06%** of eligible zone-hours, with mean width **9.68 EUR/MWh**. Even this broader family is far from bracketing the observed market; the orange band below is not the primary retained ensemble or a confidence interval.

| Score tolerance above winner | Qualifying states | Maximum retained after five-member cap |
| --- | ---: | ---: |
| 0.005 | 1 | 1 |
| 0.010 | 1 | 1 |
| 0.020 | 5 | 5 |
| 0.030 | 7 | 5 |

![Per-zone price MAE for baseline, retained members and price leader](/research/dispatch-comparison-2025/zone-mae-grid.png)

All 48 areas appear; seven lack complete observed-price series and remain gray. Negative and extreme observations remain in all eligible-zone annual metrics. No zone or failed hour is removed to improve a headline.

### Norway, Germany, Spain and France

Improvements are not uniform: the score winner improves Germany and Spain, but worsens France and NO3/NO4. The all-zone table/grid retain those regressions. Better aggregate generation scores likewise do not establish improvement in every country/fuel.

| Zone | Baseline MAE | Score winner MAE | Baseline r | Score winner r |
| --- | ---: | ---: | ---: | ---: |
| NO1 | 42.57 | 42.74 | 0.032 | 0.033 |
| NO2 | 39.25 | 40.12 | 0.201 | 0.190 |
| NO3 | 34.58 | 36.65 | 0.008 | 0.024 |
| NO4 | 35.21 | 38.56 | 0.004 | 0.016 |
| NO5 | 47.29 | 46.58 | -0.147 | -0.140 |
| DE-LU | 21.57 | 19.29 | 0.829 | 0.843 |
| ES | 24.07 | 21.62 | 0.771 | 0.817 |
| FR | 23.83 | 24.69 | 0.802 | 0.794 |

**Where the inverse proposals have leverage.** The last proposal used parent **r1-s6**. Its local interior supporting-hour counts are below; fewer than 168 hours means no local price proposal for that zone/resource.

| Zone | Gas | Coal | Nuclear |
| --- | ---: | ---: | ---: |
| NO1 | 0 | 0 | 0 |
| NO2 | 0 | 0 | 0 |
| NO3 | 0 | 0 | 0 |
| NO4 | 97 | 0 | 0 |
| NO5 | 33 | 0 | 0 |
| DE-LU | 1966 | 1933 | 0 |
| ES | 5108 | 19 | 826 |
| FR | 838 | 82 | 4708 |

All Norwegian groups are below the threshold. Thermal bids there therefore have no directly fitted local price adjustment in this design; cross-border changes can still affect prices. Fixed hydro is an injection, not an adjustable water offer. Expanding a thermal bid search cannot by itself identify missing local price formation. Germany, Spain and France have much stronger supporting model evidence, without proving which actual generators set observed prices.

![Fixed example week: observed prices, baseline and retained-fit envelope](/research/dispatch-comparison-2025/daily-prices.png)

The illustration always uses **1–7 July 2025 UTC**; all headline metrics use the full year. NO5 is a price example, not an assertion of complete NO5 generation observations. The five Norwegian zones remain separate in price comparisons; national generation is checked separately below.

![National five-fuel generation comparison with Ember](/research/dispatch-comparison-2025/national-mix.png)

Whiskers show conditional saved-group allocation bounds, not probabilistic confidence. The [national generation download](/research/dispatch-comparison-2025/inverse-generation-by-country.csv) preserves every shown model/country/fuel, reporting coverage and signed TWh differences. Missing annual references stay blank; they are not summed as zero. The [per-zone price download](/research/dispatch-comparison-2025/inverse-prices-by-zone.csv) includes bias, correlation, tails, negative-hour and daily-shape diagnostics plus envelope coverage.

## 5. What this means for investment scenarios

The experiment supports a way to keep several admissible bid explanations when the observations do not uniquely identify one. It does **not** yet estimate investment benefits. For each future ensemble member, compare its own baseline with the same model plus the asset, preserving common exogenous inputs and physical chronology. Report distributions of system-cost change, emissions, congestion rent and asset revenue separately; system savings are not investor income. Calibrated offer costs include effective premiums: their objective is not verified physical production cost or economic welfare. Revalue dispatch with independently sourced resource costs/emissions when estimating economic impacts; keep cleared-price revenues and transfers separate.

A project that looks valuable across credible fits is more robust to this tested bid uncertainty. A project whose sign changes between fits needs further investigation. Neither conclusion establishes robustness to structural model error. Fixed hydro cannot change its water schedule after an investment; this can bias results in either direction. Adaptive hydro/storage would require the separate verified chronology and strategy work. The live browser remains the older two-node line/battery screen.

## 6. Conclusion, limitations and reproduction

The useful result is the **joint price/mix trade-off and the retained set**, not a claim that fitting prices recovers the real European order book. The score-winning MAE is **28.167**, versus the target below 10. Capacity/site weather, operational availability, bid constraints, reporting scope and Nordic fixed-injection/network price formation remain possible sources of error. Effective fitted bids can compensate for these errors. The nonnegative thermal floor and unchanged zero renewable offers also restrict negative-price mechanisms; keeping negative observations in the score does not make those mechanisms identifiable. Wind/solar excess cannot automatically be repaired by changing thermal bids. This finite search neither exhausts plausible bids nor rules out better model formulations.

All 2025 observations inform this reconstruction and its selection. Independent physics and generation consistency do not turn it into a forecast backtest. Any forecasting claim needs separately designed out-of-sample evaluation; investment claims need paired forward scenarios and their acceptance checks. There is no automatic baseline promotion.

Independent replay verifies **13 complete annual witnesses**, all inverse proposals, bounded costs, physical invariance, original component physics, primal/dual objectives, full price/monthly mix/trade metrics, both round-parent selections, duplicates and diversity-based ensemble membership. Maximum native-component residual is **3.69e-06 MW** and maximum duality gap **EUR 0.000054**. All unique states have 8,760 optimal hours and zero emergency supply. Fresh clearing loops total **494.91s**; preparation **110.89s**, complete search **662.29s**, peak RSS **2585 MiB**. The baseline is reused intact, not counted as a fresh clear.

To reproduce with the pinned local source caches: hydrate the four immutable model-metadata archives with `python3 tools/pack_model_metadata.py --restore`; use the pinned Python at `data/pypsa-eur/upstream/.pixi/envs/default/bin/python` to run the finite driver into a **fresh ignored output directory**, then the independent auditor on that directory. Set `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1` and `MKL_NUM_THREADS=1`. The runner enforces a 5 GiB address-space limit, 40-minute alarm and one process/lock. Existing output directories are never implicitly resumed. A fresh checkout without the authorized large source caches cannot reproduce numerical results from the small public report assets alone.

Implementation: [inverse proposals and selection](tools/inverse_bid_ensemble_2025.py), [finite driver](tools/run_inverse_bid_ensemble_2025.py), [independent replay](tools/audit_inverse_bid_ensemble_2025.py), [report renderer](tools/bid_ensemble_report_2025.py), and [compact provenance receipt](/research/dispatch-comparison-2025/summary.json). Large source inputs, hourly witnesses and proposal arrays remain ignored locally. Prior seasonal out-of-fold evidence remains in its downloads and explicitly labelled legacy receipt fields; it is not this all-year fitted ensemble.
