# Full-year 2025 solar-alignment comparison

Verified research comparison, 22 October 2026. Public model and accepted baseline unchanged.

## Result

Solar alignment alone changes full-year **European MAE 27.576 → 27.984 €/MWh** and **EU MAE 26.784 → 27.173 €/MWh**. Of 41 complete price zones, 5 improve and 36 worsen. These are actual 8,760-hour clearing comparisons, not extrapolated January results.

The earlier January improvement came from German thermal-stock reconciliation. Solar timing alone slightly worsened that event-week MAE. The fixed four-case design below separates the two effects across the full year. No bids were refitted or case selected by observed price.

| Case | Europe MAE | EU MAE | Mean Europe r | Emergency MWh | Annual clearing seconds |
|---|---:|---:|---:|---:|---:|
| Current model | 27.576 | 26.784 | 0.617 | 0.000000 | 0.00 |
| Solar alignment only | 27.984 | 27.173 | 0.609 | 0.000000 | 46.90 |
| German stock only | 27.552 | 26.742 | 0.617 | 0.000000 | 59.30 |
| Both corrections | 27.962 | 27.132 | 0.610 | 0.000000 | 75.47 |

MAE is €/MWh. Control reuses the independently audited current oil/CHP25 witness; zero seconds means no repeated solve. Other timings include the clearing driver and witness save, excluding source preparation and independent audit. Cases with any emergency use fail supply-model acceptance even if price errors improve.

![EU monthly and annual price errors](assets/annual-solar-alignment-eu.png)

## What changes

**All countries:** original ERA5/atlite PV coefficients label the preceding hour. Move the coefficient at t+1 to market interval [t,t+1), for both fixed and tracked solar. Keep destination-hour IRENA 2024→2025 linear commissioning, source-country/plant geography, offer tranches and original arrays. Solar and wind may share a bid group; only its reconstructed solar contribution changes. Wind timing, bids, observed demand, fixed hydro, network/GSK, links, branch ratings and offsets remain unchanged.

**German stock sensitivity only:** use the separately audited SMARD annual net stock factors: hard coal 20.352→15.951 GW, lignite 19.457→15.178 GW, gas 36.896→36.614 GW. These annual totals are not hourly available/offered fleet or proof of outages on a particular date. No other country gets an unverified capacity correction.

**Year endpoint:** the cache ends at 2025-12-31 23:00 UTC, so the shifted last hour requires a 2026-01-01 00:00 UTC coefficient. That coefficient is explicitly model-derived zero, not a retrieved ERA5 observation. Atlite solar elevation across every weather cell and minute of the full 23–24 UTC interval is at most -37.42°; an independent NOAA geometry calculation gives -37.47°. A conservative 2° margin stays below the converter's 1° irradiation cutoff. Zero irradiation produces exactly zero in the retained CSi panel model. This proves the endpoint identity without weather interpolation, circular wrapping or observed-generation substitution. Daylight missing endpoints are rejected.

## Per-zone price errors

![All-zone annual MAE comparison](assets/annual-solar-alignment-zones.png)

[All 48 zones × four cases: annual/monthly MAE, bias, RMSE, correlation, hourly-ramp MAE and top-5%-observed-price MAE](solar-alignment-2025-by-zone.csv). Unknown targets remain missing, not zero errors.

## Country overview

These are equal averages over the listed complete price zones, not demand-weighted national prices. European/EU aggregates weight each unique zone once. DE-LU is shared with Luxembourg and not duplicated; country grouping lists it under DE. Italy and France have incomplete modeled-zone coverage. Shared IE-SEM and other unavailable targets are excluded.

| Country group | Covered/model zones | Current MAE | Solar only | DE stock only | Both |
|---|---:|---:|---:|---:|---:|
| AL | 1/1 | 29.39 | 29.77 | 29.35 | 29.73 |
| AT | 1/1 | 17.77 | 18.64 | 17.65 | 18.53 |
| BE | 1/1 | 24.15 | 24.13 | 23.94 | 23.89 |
| BG | 1/1 | 23.43 | 23.52 | 23.38 | 23.46 |
| CH | 1/1 | 19.56 | 20.56 | 19.33 | 20.37 |
| CZ | 1/1 | 20.80 | 22.09 | 20.65 | 21.95 |
| DE | 1/1 | 19.71 | 19.74 | 19.38 | 19.45 |
| DK | 2/2 | 36.26 | 36.24 | 36.14 | 36.13 |
| EE | 1/1 | 45.48 | 45.83 | 45.52 | 45.85 |
| ES | 1/1 | 21.20 | 21.36 | 21.19 | 21.36 |
| FI | 1/1 | 41.37 | 41.80 | 41.49 | 41.94 |
| FR | 1/2 | 24.43 | 24.49 | 24.36 | 24.42 |
| GR | 1/1 | 22.74 | 22.70 | 22.71 | 22.65 |
| HR | 1/1 | 20.20 | 20.73 | 20.14 | 20.68 |
| HU | 1/1 | 22.60 | 22.99 | 22.50 | 22.89 |
| IT | 6/7 | 19.94 | 20.46 | 19.93 | 20.44 |
| LT | 1/1 | 41.35 | 41.85 | 41.37 | 41.86 |
| LV | 1/1 | 41.34 | 41.84 | 41.36 | 41.85 |
| MK | 1/1 | 20.95 | 20.97 | 20.89 | 20.90 |
| NL | 1/1 | 21.16 | 20.90 | 20.84 | 20.59 |
| NO | 5/5 | 36.74 | 37.23 | 36.88 | 37.38 |
| PL | 1/1 | 20.69 | 21.17 | 20.58 | 21.07 |
| PT | 1/1 | 20.73 | 20.98 | 20.71 | 20.97 |
| RO | 1/1 | 22.85 | 23.26 | 22.80 | 23.20 |
| RS | 1/1 | 19.96 | 20.39 | 19.91 | 20.33 |
| SE | 4/4 | 37.79 | 38.28 | 37.93 | 38.42 |
| SI | 1/1 | 20.77 | 21.37 | 20.71 | 21.31 |
| SK | 1/1 | 20.95 | 21.78 | 20.86 | 21.69 |

Coverage: 48 modeled zones, 41 complete price zones; EU subtotal uses 32 zones grouped under 23 country codes (AT, BE, BG, CZ, DE, DK, EE, ES, FI, FR, GR, HR, HU, IT, LT, LV, NL, PL, PT, RO, SE, SI, SK), with Luxembourg sharing DE-LU. This is the covered EU network, not complete coverage of all 27 member states. No complete targets for: BA, IT-CALA, ME, XK, FR-COR, GB, IE-SEM.

## Verification and interpretation

Independent audit replays **35,040 hourly LP witnesses**, including the reused control: original source profiles, full-year clock/capacity/geographic pooling, native component balances/AC branch limits, offer/link bounds, objectives and full primal/dual optimality. Maximum native residual 4.82e-06 MW; maximum duality gap €1.13e-05. Original feasibility and optimality gates are unchanged. Three boundary tests verify the nighttime identity, reject missing daylight coefficients and check zero-output panel behavior.

All prices are original corrected ENTSO-E main day-ahead hourly targets; published quarter-hour prices are averaged only when all four observations exist. DE-LU/AT use SDAC sequence 1. SMARD provides the German capacity sensitivity, not price targets. Original bids retain non-oil calibration to earlier incorrectly selected targets: this remains an in-sample reconstruction with inherited calibration limitations, not forecast accuracy or recovered auction bids. Timing semantics must follow the source contract even where price MAE worsens. An hourly energy-mix improvement, asset-value validation or annual model promotion cannot be inferred from price error alone.

The solar input issue affects the shared historical network-dispatch pipeline and its downstream witnesses, including the current public country explorer. This study preserves those historical files and evaluates corrected copies. It does not establish an effect on the separate observed-price/flow congestion-rent computation or automatically replace the two-node browser scenario engine.

## Conclusion

The timing correction fixes a shared input contract, but does not by itself improve annual price recovery with the inherited bids. Keep that distinction explicit: prices may have been calibrated around other input errors, while weather magnitude, available/offered fleet and network constraints retain separate uncertainties. This comparison does not identify which uncertainty explains the remaining error. Further source reconciliation and any corrected-input bid recalibration require fresh provenance; do not choose a physically incorrect clock simply because its MAE is lower.

Source/case plan: `config/annual-solar-alignment-2025.json`. Ignored authoritative evidence: `data/bidding-zone-network-2025/annual-solar-alignment-v1/inputs.json`, `summary.json`, `audit.json`, raw annual witnesses and `report-receipt.json`. Source URLs and original hashes remain chained to the January source audit, corrected-price audit and frozen oil/CHP checkpoint. Six historical explorer validation-file hashes are checked against their exact archived bytes at Git commit 5e1fe632861f402029047e3d1ca0c384a2b6212f, because the user later replaced those public exports; no old hash is waived and no obsolete public data is restored. The previous [January investigation](january-scarcity-2025.md) remains separate.
