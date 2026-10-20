# Inverse market modelling: fitting supply and network constraints

## Summary

We now allow **network limits and generation availability to change alongside supply bids**, rather than fitting bids against a fixed grid. A finite 2025 experiment tests **16 combinations**, using two existing bid anchors and **14 new parameter states**. **10 cases have complete annual witnesses; 6 are rejected by independently replayed infeasibility certificates**. The best joint-score case is **`inverse_joint-nordic_higher-w100`**: price MAE **27.752 EUR/MWh**, versus **28.964** for the accepted baseline and **28.167** for the previous bid-only winner. Generation mismatch is **0.2548**, versus **0.2995** baseline; implied-trade mismatch **0.1438**, versus **0.1719**. The joint winner changes physical inputs.

The winner uses **the previous fitted bids**, **15% more headroom on Nordic-incident AC branches**, and **wind availability ×1.0**. These are fitted effective assumptions, **not a recovered real grid**. The lowest price MAE across all tested cases is **27.740 EUR/MWh**; price-only leadership and joint eligibility are distinct. The target below 10 EUR/MWh remains unmet. All targets also inform selection: this is **in-sample reconstruction, not independent forecasting**. Neither the accepted baseline nor the browser scenario engine is replaced.

![Every joint supply/network state, price and generation performance](/research/dispatch-comparison-2025/overview.png)

## 1. What is being estimated?

Each forward hourly LP chooses dispatch $x_t$ to minimize submitted offer cost $c_t(\theta)^T x_t$, subject to generation bounds and the physical network equations. Its zonal balance duals give cleared prices $p_t(\theta)$. In this experiment, $\theta$ selects a bid anchor, a wind-availability factor and an AC rating factor; **prices are always produced by clearing, never replaced by observations**.

Inverse modelling selects parameters whose forward prices and generation resemble observations. Price alone cannot distinguish expensive bids from unavailable cheap supply or limited imports. Generation and exchanges add information, but do not make the parameters uniquely identified. Fixed GSKs, aggregated offers and nonunique LP duals add ambiguity. The experiment is a small finite search, not an exact globally solved bilevel problem, exhaustive model distribution or proof of actual market offers.

The method follows the inverse-optimisation framing in [Chan, Mahmood and Zhu](https://arxiv.org/abs/2109.03920). [Liang and Dvorkin](https://arxiv.org/html/2302.05498v2) study electricity offer recovery; their identification assumptions do not automatically hold for our aggregated synthetic market. [Birge, Hortaçsu and Pavlin](https://doi.org/10.1287/opre.2017.1606) study constraint recovery from prices. Those results motivate constraint calibration; they do not validate arbitrary European capacity changes or guarantee our fitted parameters are true.

## 2. Baseline model and source data

The accepted `seasonal-calendar-v1/refit` has **48 modeled areas, 145 physical buses, 41 complete observed-price zones and all 8,760 UTC hours of 2025**. Country-to-zone/source allocation proxies remain. Each hour is an independent sparse LP; daily grouping adds no commitment, ramps or storage optimization. This is EUPHEMIA-inspired synthetic clearing, not reconstruction of actual order books or nonconvex allocation rules.

| Component | Data and treatment |
| --- | --- |
| Grid and fleet | Pinned [PyPSA-Eur](https://github.com/PyPSA/pypsa-eur) v2026.08.0; existing PTDF/GSK, AC islands, original HVDC bounds and losses. Static AC headroom starts at 0.7 of source nominal ratings; N-0 model limits, not certified commercial JAO domains. |
| Wind/solar | Original 2025 [ERA5](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels)/[atlite](https://atlite.readthedocs.io/) weather profiles and [IRENA](https://www.irena.org/Data) end-2024/end-2025 linear capacity trajectory. Commissioning dates, fleet siting and generic resource conversion are proxies. |
| Demand | Prepared 2025 [ENTSO-E](https://transparency.entsoe.eu/) demand, fixed in every case; regional allocation and gross/net scope limitations remain. |
| Hydro/nuclear | Fixed hourly water schedules, with retained Norwegian NVE inflow/stock evidence; unchanged nuclear availability proxy. Capacity does not create water. No hydro or storage search restarted. |
| Offers | Monthly World Bank TTF/Brent and ECB FX anchors, plant efficiency/VOM, 80 EUR/t carbon assumption, accepted smooth seasonal/hourly bids. The second anchor is the independently verified prior inverse joint winner `r2-s6`; no new bid coefficients are fitted here. |
| Targets | Source-hashed ENTSO-E A44 hourly prices; [Ember](https://ember-energy.org/data/) monthly national Wind/Solar/Nuclear/Gas/Coal generation and signed net exports. Missing values stay unknown. |

Generation scores measure distance outside **conditional saved-group allocation bounds**, divided by max(reference,0.25 TWh), averaged over known country/fuel/month observations. Proportional point allocations are illustrative; bounds are not jointly attainable ranges over all optimal dispatches or statistical confidence intervals. Hydro, biomass and other generation are outside the five-fuel score. New-fit hourly zonal A75 generation validation remains outstanding.

The trade score compares implied generation minus demand with national net exports, normalized by max(model demand,1 TWh). It is **not observed physical border flow**. JAO domains and original-request-classified ENTSO-E flows are not fitted here. Generation/price consistency cannot by itself certify every border constraint.

## 3. Exact adjustable parameters and search

**AC constraints:** preserve $|Hq_t+o_t|\leq r(\theta)$, with unchanged PTDF $H$, injection variables $q_t$, offsets $o_t$, topology, impedance, GSK, islands and HVDC physics. Multiply existing symmetric MW limits by **0.85, 1 or 1.15**. The inherited nominal-rating factor becomes 0.595/0.7/0.805. Nothing exceeds source nominal ratings. This changes permitted headroom, not impedance or physical construction, and includes internal AC constraints rather than treating every branch as a commercial border.

Global controls adjust all **255** passive branches. Nordic controls adjust the **37** branches with either endpoint in NO/SE/FI/DK, including incident cross-region AC lines. HVDC links remain unchanged. These static bounds are **experimental calibration assumptions**, not values verified from JAO, outage records or N-1 studies. Their narrow range is deliberately interpretable; it does not encompass every plausible constraint error.

**Wind availability:** multiply original source wind available MW by **1 or 0.9**, before aggregation. Preserve chronological weather shape, source country, capacity/nameplate and all solar/other availability. Recompute the available MW used in both clearing and conditional generation allocation. The 0.9 hypothesis can represent a coarse conversion/derating bias; it is not a measured correction or capacity estimate, and no observed hourly dispatch becomes available supply. A spatially uniform annual factor cannot repair wrong site geography or within-year timing.

**Bids:** compare two frozen anchors: accepted seasonal bids and prior inverse joint bids. The latter contains bounded smooth gas/coal/nuclear adjustments, Ember mix signals and monotone thermal premiums. Those coefficients are not refitted when the physical parameters change. Therefore this tests joint combinations and interactions, not unrestricted simultaneous continuous estimation.

The main factorial has 2 bid anchors × 3 global AC choices × 2 wind choices = 12 cases; four extra Nordic lower/higher controls use original wind. Exactly 16 states are retained, including adverse and infeasible outcomes. There is no adaptive widening after seeing results. The all-year objective is 0.55 normalized price MAE + 0.20 within-day demeaned MAE + 0.20 generation mismatch + 0.05 trade mismatch, plus 0.01 times bid/physical departure regularization. Physical regularization averages squared normalized departures in wind, Nordic-incident AC and other AC limits. Bid regularization uses the previous source-availability-weighted offer deviation.

Eligibility requires price MAE no higher than accepted baseline; demeaned-price, generation and trade scores no more than 2% worse; all 8,760 optimal hours and emergency supply at most 1e-6 MWh. These are declared research filters, **not product acceptance gates**. Selection minimizes the regularized score among eligible states, then penalty and ordinal. No automatic baseline promotion follows.

| # | Case | Price MAE | Generation score | Trade score | Joint score | Eligible |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `accepted-unchanged-w100` | 28.964 | 0.2995 | 0.1719 | 1.0000 | yes |
| 2 | `accepted-unchanged-w90` | 29.183 | 0.2979 | 0.1717 | 1.0066 | no |
| 3 | `accepted-all_lower-w100` | — | — | — | — | no |
| 4 | `accepted-all_lower-w90` | — | — | — | — | no |
| 5 | `accepted-all_higher-w100` | 28.597 | 0.3016 | 0.1759 | 0.9954 | no |
| 6 | `accepted-all_higher-w90` | 28.810 | 0.3007 | 0.1755 | 1.0018 | no |
| 7 | `accepted-nordic_lower-w100` | — | — | — | — | no |
| 8 | `accepted-nordic_higher-w100` | 28.647 | 0.2996 | 0.1720 | 0.9920 | yes |
| 9 | `inverse_joint-unchanged-w100` | 28.167 | 0.2551 | 0.1436 | 0.9429 | yes |
| 10 | `inverse_joint-unchanged-w90` | 28.502 | 0.2504 | 0.1424 | 0.9493 | yes |
| 11 | `inverse_joint-all_lower-w100` | — | — | — | — | no |
| 12 | `inverse_joint-all_lower-w90` | — | — | — | — | no |
| 13 | `inverse_joint-all_higher-w100` | 27.740 | 0.2556 | 0.1475 | 0.9359 | yes |
| 14 | `inverse_joint-all_higher-w90` | 28.049 | 0.2510 | 0.1460 | 0.9411 | yes |
| 15 | `inverse_joint-nordic_lower-w100` | — | — | — | — | no |
| 16 | `inverse_joint-nordic_higher-w100` | 27.752 | 0.2548 | 0.1438 | 0.9324 | yes |

**Rejected physical combinations.** The first tightened case was initially allowed to continue after HiGHS reported infeasible hours. That diagnostic run was stopped; its completed wind-control witness is reused with original code provenance. Before the remaining search, the failure policy was amended to reject a year at its first numerically certified infeasible hour. Parameter bounds, objective and acceptance filters were unchanged. No partial-year price/mix metric is reported or eligible.

| Rejected case | First rejected UTC hour index | Numerical Farkas separation (MW) |
| --- | ---: | ---: |
| `accepted-all_lower-w100` | 0 | 12.324599 |
| `accepted-all_lower-w90` | 0 | 12.324599 |
| `accepted-nordic_lower-w100` | 0 | 12.324599 |
| `inverse_joint-all_lower-w100` | 0 | 12.324599 |
| `inverse_joint-all_lower-w90` | 0 | 12.324599 |
| `inverse_joint-nordic_lower-w100` | 0 | 11.963541 |

The first rejected case's independently replayed certificate uses **5 AC branch rows** with endpoint countries **NO, SE**. These are participating constraints in one proof, not a unique causal attribution to individual real lines. The certificate therefore localizes a model-consistency issue; it does not establish a real-world shortage.

Hour index 0 means 1 January 2025 at 00:00 UTC. A Farkas row ray combines the model's row bounds into a requirement larger than any value allowed by its generation/link bounds, with zero free-injection coefficients to numerical tolerance. The positive separation certifies that hour's constraint set is empty within numerical tolerance. Rays are normalized by their largest absolute row coefficient; the separation magnitude depends on that normalization and is not a physical shortage volume or measured line-capacity deficit. This may expose restricted fixed injection/GSK assumptions, not a real European electricity shortage. Later hours need not be solved to reject a full-year-feasible claim. Changing bid prices cannot repair an empty physical feasible set; reducing only an upper availability bound cannot restore feasibility either. A source-backed constraint or injection/GSK correction would be a different model change, requiring fresh verification.

`accepted` and `inverse_joint` identify bid anchors; `w100`/`w90` identify original/90% wind availability. All-zone, monthly quantity and tail evidence remain separate from aggregate ranking. See [every case](/research/dispatch-comparison-2025/joint-search-cases.csv), [shown-model zonal metrics](/research/dispatch-comparison-2025/joint-prices-by-zone.csv), and [national fuel volumes/differences](/research/dispatch-comparison-2025/joint-generation-by-country.csv).

## 4. Does changing the network help?

The following comparisons hold both bids and original wind availability fixed. Deltas are relative to the unchanged-network case with the **same** bid anchor; negative values improve the error. This isolates effective network-limit changes from bid-fitting gains.

| Bid anchor | Network change | Price MAE delta | Generation-score delta | Eligible |
| --- | --- | ---: | ---: | --- |
| accepted | all_lower | rejected: infeasible hour | — | no |
| accepted | all_higher | -0.367 | +0.0022 | no |
| accepted | nordic_lower | rejected: infeasible hour | — | no |
| accepted | nordic_higher | -0.317 | +0.0001 | yes |
| inverse_joint | all_lower | rejected: infeasible hour | — | no |
| inverse_joint | all_higher | -0.427 | +0.0004 | yes |
| inverse_joint | nordic_lower | rejected: infeasible hour | — | no |
| inverse_joint | nordic_higher | -0.415 | -0.0004 | yes |

![Full-year price MAE for every modeled zone](/research/dispatch-comparison-2025/zone-mae-grid.png)

The grid shows every modeled area, retaining unknown-price cells and regional regressions. NO5 improves from **47.29 to 32.56 EUR/MWh**, with correlation **-0.147→0.272**. But NO2/NO4 and all four Swedish zones have higher MAE than the accepted baseline; France also worsens under the joint winner. The globally relaxed price leader offers a different country trade-off; its near-identical aggregate MAE does not identify which grid is true. National generation agreement is not evidence of correctly located zonal injections. Norway's fixed hydro remains an important structural restriction: AC-limit changes can reroute its fixed production, but cannot create a water-value offer or reschedule water.

| Zone | Accepted MAE | Bid-only MAE | Joint winner MAE | Winner r |
| --- | ---: | ---: | ---: | ---: |
| NO1 | 42.57 | 42.74 | 38.33 | 0.189 |
| NO2 | 39.25 | 40.12 | 42.39 | 0.128 |
| NO3 | 34.58 | 36.65 | 31.94 | 0.227 |
| NO4 | 35.21 | 38.56 | 39.62 | 0.092 |
| NO5 | 47.29 | 46.58 | 32.56 | 0.272 |
| DE-LU | 21.57 | 19.29 | 19.42 | 0.843 |
| ES | 24.07 | 21.62 | 21.62 | 0.817 |
| FR | 23.83 | 24.69 | 24.66 | 0.794 |

![Observed and simulated hourly prices in a fixed July week](/research/dispatch-comparison-2025/daily-prices.png)

Examples always use 1–7 July 2025 UTC. All headline scores use the full year, not that week. NO5 is a price illustration; it does not establish complete NO5 generation validation. The five Norwegian price zones remain separate.

![National generation for Norway, Germany, Spain and France](/research/dispatch-comparison-2025/national-mix.png)

The mix comparison shows five fuels for NO/DE/ES/FR. Hydro, biomass and other resources are excluded, so this is not a complete national energy-mix validation. Winner whiskers represent conditional allocation bounds; they are not probabilistic uncertainty. Downloads retain missing reference months and signed model-minus-observed TWh. Lower generation mismatch can accompany worse prices in an individual zone, so neither outcome is hidden by the joint score.

## 5. Interpretation, limitations and next steps

**Joint calibration is implementable at this scale.** This trial changes real forward-model bounds, rather than applying a statistical price correction after solving. It exposes whether coarse source/grid assumptions have more leverage than bids alone. The selected Nordic headroom is at the upper tested bound; that is neither a measured transfer capacity nor justification to widen it without new evidence. Its result is a comparison within a deliberately small parameter family; it cannot rule out better seasonal/regional availability, commercial-domain or operating models.

A fitted network can compensate for incorrect bids, demand scope, fixed hydro or GSKs. A lower in-sample error therefore supports a hypothesis, not a verified source correction. The next useful refinement should depend on the observed frontier: independently check the constraints/availability that need adjustment, add verified commercial flow/net-position evidence where available, and expand regional/seasonal parameters only with explicit bounds and identifiability checks. The current model still lacks commitment/ramping, adaptive water offers and a fully represented negative-bid mechanism. Do not assign all residual error to transmission.

For investment analysis, compare each credible fitted model with itself plus the asset, preserving common inputs. Freeze its calibrated parameters within each pair; refitting an intervention to historical baseline prices would suppress the investment effect being estimated. Capacity addition and effective-limit calibration are different interventions; new AC impedance or GSK effects require a faithful network recompile. Effective calibrated bid costs are not verified physical production costs or welfare. Revalue dispatch with independent resource-cost/emission inputs, separating system impacts from revenues/rent. **No investment scenario or posterior distribution is verified by this trial.** Fixed hydro may bias investment effects in either direction. The live browser remains the older two-node line/battery screen.

## 6. Verification and reproduction

Independent replay checks **10 full-year witnesses and 6 rejected-state certificates**, source hashes, exactly declared states, altered source wind MW and group allocation, native component flows against **altered branch limits**, unchanged source physics elsewhere, primal bounds, objective/dual/complementarity, all price/mix/trade metrics, regularization, eligibility and winner selection. Maximum component residual **1.7e-05 MW**; maximum duality gap **EUR 0.000060**.

Three complete witnesses are reused intact: two prior anchors and the wind control from the interrupted driver. Fresh verified-driver clearing/rejection/retry loops total **801.73s**; source preparation **299.74s**, retry preparation **386.73s**, sum of verified source/retry driver commands **1641.71s**, peak RSS **2603 MiB**. Independent replay is additional time. An initial restart also stopped at a source-versus-normalized-JSON provenance check before any new clears; that check was corrected and moved before model building. That preparation and the earlier interrupted diagnostic are additional, excluded from this current-driver total; the reused wind-control clearing took 141.11s. This is not a claim of combined end-to-end wall-clock experiment runtime.

Two global-relaxation states initially returned Not Set, not Infeasible. Their unchanged-network solutions are checked as feasible controls, and the same state parameters are retried with a reset HiGHS scheduler and presolve off, preserving the 1e-8 primal tolerance. Every successful retry receives the same independent primal/dual and native-physics audit; unresolved numerical cases are never treated as evidence of infeasibility. The auditor also re-clears **2 complete unchanged-network years** with the retry backend as matched numerical controls, not new fitted states. Their largest observed-hour mean absolute price departure from the saved controls is **2.78088e-12 EUR/MWh**; LP dual nonuniqueness remains an identification caveat.

With existing verified source caches, restore immutable metadata with `python3 tools/pack_model_metadata.py --restore`. Use pinned Python `data/pypsa-eur/upstream/.pixi/envs/default/bin/python` with `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`; run `tools/run_joint_network_calibration_2025.py` into a **fresh ignored output directory**, then audit the final directory with `tools/audit_joint_network_calibration_2025.py`. When the declared driver records unresolved numerical states, use `tools/repair_joint_network_calibration_2025.py SOURCE FRESH_RETRY_DIRECTORY` before that audit; it retries only the identical failed states and binds both stages. The retained interrupted wind-control/code/config caches are also prerequisites for current replay. The runner enforces 5 GiB address space, a 50-minute alarm and a per-output process lock. Existing directories are never implicitly resumed. Public compact assets alone cannot reproduce numerical runs without the omitted large provider/source caches.

Sources/method: [joint parameterization](tools/joint_network_calibration_2025.py), [driver](tools/run_joint_network_calibration_2025.py), [independent replay](tools/audit_joint_network_calibration_2025.py), and [provenance receipt](/research/dispatch-comparison-2025/summary.json). Prior [bid-only cases](/research/dispatch-comparison-2025/inverse-search-cases.csv), [zonal metrics](/research/dispatch-comparison-2025/inverse-prices-by-zone.csv) and [mix comparison](/research/dispatch-comparison-2025/inverse-generation-by-country.csv) remain supporting evidence, not a new accepted baseline. Raw observations, hourly arrays and witnesses stay locally ignored. This report does not claim deployment, market certification or independent forecasting.
