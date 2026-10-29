# Accepted monthly fitted-bid research baseline · 2025

## Summary

Twelve monthly, local-hour, technology-by-bidding-zone monotone supply curves were fitted with 20 Adam updates at rate 1.0. The fast differentiable transport model used observed hourly demand, source fuel costs, original renewable availability, fixed hydro and independent corridor bounds. Its fitted bids were sampled onto the **original 799 offer columns** and evaluated in one 8,760-hour physical joint LP. This replaces the former solar-anchor **research baseline**; the static app is unchanged.

| Matched annual measure | New LP | Prior baseline | Change |
|---|---:|---:|---:|
| Corrected ENTSO-E zonal price MAE, EUR/MWh | 25.051 | 26.795 | -1.744 |
| Hourly country/technology generation MAE, GW | 0.552 | 0.633 | -0.082 |
| Hourly technology-share MAE | 0.0631 | 0.0777 | -0.0145 |
| Monthly generation MAE, TWh | 0.297 | 0.326 | -0.029 |

Price MAE improves in **32 of 41** complete-price bidding zones. All **8,760** LP hours are optimal, with zero emergency generation. The 24-hour seasonal pilot also used zero emergency supply. Annual clearing took **41.19 seconds**, excluding preparation, fitting and audits.

## Monthly price and generation comparison

Price MAE uses corrected hourly ENTSO-E SDAC for the same 41 complete-price zones in both LP cases. Generation MAE here is the illustrative country/technology monthly allocation in TWh; mixed renewable offers cannot be uniquely attributed to technologies.

| Month | New price MAE | Prior price MAE | New generation MAE TWh | Prior generation MAE TWh |
|---|---:|---:|---:|---:|
| 01 | 26.71 | 29.59 | 0.322 | 0.363 |
| 02 | 31.95 | 36.25 | 0.292 | 0.337 |
| 03 | 27.56 | 30.53 | 0.299 | 0.329 |
| 04 | 23.27 | 25.88 | 0.299 | 0.299 |
| 05 | 23.89 | 25.24 | 0.306 | 0.318 |
| 06 | 23.09 | 24.60 | 0.324 | 0.321 |
| 07 | 20.66 | 22.80 | 0.278 | 0.334 |
| 08 | 23.27 | 25.27 | 0.269 | 0.312 |
| 09 | 24.54 | 26.52 | 0.298 | 0.303 |
| 10 | 26.31 | 26.84 | 0.281 | 0.337 |
| 11 | 28.02 | 27.14 | 0.288 | 0.327 |
| 12 | 21.98 | 21.69 | 0.309 | 0.331 |

The largest price regressions are CZ (+9.13 EUR/MWh), IT-North (+6.22 EUR/MWh), IT-CNOR (+1.95 EUR/MWh), FR (+1.70 EUR/MWh), NO5 (+1.34 EUR/MWh). November and December price MAE also worsen despite the annual improvement.

## Training and root selection

The independently replayed fast-model same-month price MAE is **20.202 EUR/MWh** on 359,160 observed cells; fast-model hourly country/technology generation MAE is **0.502 GW**. This is a **price-conditioned training score**, not the LP result or an out-of-sample estimate. The fast fitting loop took 3,757 seconds across twelve months, plus setup and replay; it ran 21 saved states per month including initialization.

For a stalled hour, eight model-only starting price vectors were tried and only roots satisfying the original 1e-9 GW balance and generator/corridor bounds were eligible. Among the certified roots found, the one with the lowest observed-price training loss was chosen, following the user decision. This is a discrete selection, so the implicit gradient is local to the chosen root. Across all updates, 485 hard-hour fallbacks occurred and the largest valid-root price spread was 116.68 EUR/MWh. The three EE/LV/LT price cells at 2025-08-15 23:00 UTC have a structurally unidentifiable common-price direction; they were excluded from the training gradient but included in every all-cell price score.

## Physical and source audit

The independent annual replay found maximum primal violation **3.48e-07 MW**, objective discrepancy **2.61e-08 EUR**, duality gap **2.33e-06 EUR**, and complementarity **3.05e-05 EUR**. LP solar availability matches the fitting input exactly (0 TWh mismatch). Original network rows, generator availability, fixed hydro, load, link bounds, 2025 UTC order and no-emergency gate were retained.

**1061.05 TWh** of accepted LP dispatch lies in mixed-technology offers, so the generation split is illustrative rather than uniquely identified. **0.271 TWh** uses the declared zonal technology-availability fallback when original member profiles are zero. Inferred fast-model corridor flows are saved with direction and bounds; they are not observed commercial exchanges or proof of a flow-based market domain.

## Interpretation and provenance

This is a full-year **retrospective reconstruction on the same 2025 data used to fit the bids**. The independent LP protects the physical and numerical comparison from the fast model’s root choice, but it does not supply held-out forecast validation. The fixed hydro schedule also does not respond to investments. Improved observed prices and illustrative generation do not establish true order books, EUPHEMIA replication or investment value. The static app still uses its separately supported engine; no website publication is claimed here.

Source and witness identities are recorded in `config/active-research-baseline.json`, the archived prior pointer `config/research-baseline-solar-anchor-2025.json`, ignored `data/eu-market/flow-adjusted-clearing-2025/aligned-mixed-flow-observed-root-v1-u20-r1/`, and ignored `data/bidding-zone-network-2025/observed-root-fast-joint-lp-v1/`. The recorded source set includes corrected ENTSO-E SDAC prices, ENTSO-E load and commercial exchange coverage, Ember generation targets, solar/renewable availability and original LP network inputs. No large data artifacts are committed.
