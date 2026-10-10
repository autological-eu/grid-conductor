# European hourly dispatch — fixed hydro with resource bids

## Summary and conclusion

We implemented the proposed combination: **fast hourly physical-network clearing,
precomputed fixed hydro, and simple resource-specific generator offers**. It covers
all **8,760 UTC hours of 2025** in 40 country/AC-island areas. No
price forecast, adaptive reservoir solve or observed electricity-price input is used.

The combined bids increase German MAE by EUR0.14/MWh, and improve MAE in 23 of 39 mapped observed zones. The combined annual clearing/update/live-replay loop takes
**13.78 seconds**.
This is an untuned comparative experiment, **not accepted market-price accuracy**.
Audited commercial-zone mapping and observed zonal demand remain incomplete.
The browser still uses its existing two-zone screen.

| Bid formulation | Annual loop s | DE MAE EUR/MWh | DE bias EUR/MWh | DE RMSE EUR/MWh | Equal-area mean MAE EUR/MWh |
| --- | ---: | ---: | ---: | ---: | ---: |
| Legacy fixed hydro | 15.06 | 22.56 | -9.59 | 34.23 | 38.36 |
| Gas/oil fuel update | 14.33 | 22.74 | -13.76 | 35.13 | 38.27 |
| Combined simple resource bids | 13.78 | 22.70 | -13.23 | 35.05 | 38.11 |

Both price comparisons use the **same direct ENTSO-E A44 series**, hours and
geographic proxy. The older checkpoint's published EUR23.10/MWh used a different
DE-LU observation series; it must not be substituted into this comparison.
Equal-area MAE first averages zone errors sharing one physical area, then weights
each represented physical area equally (29 areas).
It is not demand-weighted European market accuracy.

## Generator strategies and data

- **Gas/CCGT/OCGT and oil:** offer = fuel price / efficiency + carbon price ×
  operational emission factor / efficiency + variable O&M. Replace the prepared
  total cost; do not add fuel or carbon twice. Gas/oil inputs are twelve observed
  World Bank monthly TTF/Brent benchmarks, converted with ECB daily FX and repeated
  over UTC hours. Carbon is a constant **EUR80/t assumption**, not historical EUA.
  Heating-value multiplier 1 and Brent at 1.7 MWh thermal/barrel remain proxies;
  Brent is not delivered power-plant oil fuel. No daily fluctuations are invented.
- **Coal/lignite:** the same explicit formula, with prepared technology-table
  fuel constants rather than observed 2025 commodity quotes.
- **Wind/solar:** weather-limited availability and EUR0/MWh offers in the complete
  simple-bid variant. Legacy and fuel-only retain EUR−5/MWh offers. This low-price
  rule is an assumption; subsidy-specific or strategic bids are not reconstructed.
- **Nuclear, biomass, waste, geothermal and run-of-river:** labelled prepared
  operating-cost/availability proxies. Nuclear has no commitment/ramp/must-run
  representation; source availability ending in 2024 is explicitly a 2025 proxy.
- **Reservoir hydro:** the same audited precomputed hourly electrical injections
  in every variant, never renewable availability or a variable bid volume.
  Turbine/inflow/efficiency/spill/stock/closure checks preserve the retained source
  schedule and its inherited model inventory boundaries. These are not observed
  Norwegian reservoir stocks. Other 67 battery/PHS units remain excluded.

The **fuel-only** ablation changes gas/oil bids alone, keeping other legacy offers.
The **complete simple-bid** variant uses the current resource-bidding compiler's
rules, including all five thermal types and zero-price renewables. These variants
were specified before this annual run. No electricity-price fitting, parameter
selection for market acceptance or empirical pass threshold is claimed.

IRENA end-2024/end-2025 linear wind/PV commissioning, original hourly weather,
generator capacity/availability, prepared network demand, GSKs and all constraints
are identical across variants. Demand is currently the **prepared PyPSA-Eur proxy**,
not an independently audited ENTSO-E zonal-demand input. The requested observed-demand
and bidding-zone upgrade remains blocked on source/mapping verification; schematic
map centroids are not geographic asset mappings. No missing zonal data are fabricated.

## Physical clearing and speed

Each hour clears synthetic supply against inelastic residual demand, after fixed
hydro injections. Original passive-network PTDF/GSK constraints and
256 branch ratings are preserved, along with
74 native controllable links, signed bounds and efficiencies.
These are N-0 physical approximations, not audited commercial JAO capacities.
Country labels remain separate by AC island, not NO1–NO5 commercial zones.

Identical-column, identical-hourly-price offers can be merged exactly: each has the
same area and network effect. Installed-capacity GSKs do not change with merging.
Hourly vectors update a persistent one-thread HiGHS simplex model and reuse its basis.
There is no temporal reservoir/forecast optimisation. Per-hour deadlines use the
solver's cumulative clock correctly; unchanged-input cold retries are recorded.

| Variant | Actual solver s | Bid compilation/merge s | Emergency TWh | Shortage hours |
| --- | ---: | ---: | ---: | ---: |
| Legacy fixed hydro | 12.44 | 0.36 | 0.0298195 | 4 |
| Gas/oil fuel update | 11.93 | 0.41 | 0.0298195 | 4 |
| Combined simple resource bids | 11.55 | 0.42 | 0.0298195 | 4 |

Common source/hydro preparation took 6.92s.
The full command for **three annual variants, nine native checks, component replay
and witness export** took 132.89s, peak RSS
1211 MiB. These are separate from report generation and the
subsequent independent audit. The highlighted loop is not end-to-end runtime or a
browser benchmark. Offline hydro-schedule creation is excluded. The retained
legacy benchmark remains 19.17s plus 6.73s preparation; today's controlled legacy
run measures the same formulation with exact offer aggregation.

## German supply curves and clearing examples

![Domestic German supply offers and coupled clearing prices](/research/fixed-reservoir-screening-2025/resource-bids-curves.png)

Three preselected January/July/December hours show domestic offered capacity by
price. The vertical line is domestic residual demand; horizontal lines show the
network-cleared combined price and observed DE-LU price. **The domestic curve's
intersection is not the coupled clearing solution**: imports, exports and physical
constraints enter the Europe-wide solve. Examples and all bid volumes/prices are
included in the compact data download.

## Full-year observed-price evaluation

![Annual, monthly and all-zone price comparisons](/research/fixed-reservoir-screening-2025/resource-bids-errors.png)

All 39 eligible mapped observed zones are included, preserving missingness
and signed prices. Raw A44 request domains, response hashes and hourly aggregation
are rechecked. Full-year, monthly, negative-price and border-spread diagnostics are
available in the download: 67 observed border pairs. No congestion-rent
or investment benefit follows merely from price agreement.

The German combined model has 140 negative
hours versus 479 observed. Simple
renewable and nuclear rules cannot reconstruct all negative-price behaviour.
Four unavailable observed series and unresolved Italian island mappings are
excluded explicitly in the data; country prices reused for Norway, Sweden and
mainland Italy are disclosed.

| Observed Norwegian zone | Legacy MAE EUR/MWh | Fuel-only MAE EUR/MWh | Complete bids MAE EUR/MWh |
| --- | ---: | ---: | ---: |
| NO1 | 199.88 | 201.18 | 198.03 |
| NO2 | 202.49 | 203.67 | 200.55 |
| NO3 | 210.47 | 211.79 | 208.39 |
| NO4 | 220.69 | 222.22 | 218.69 |
| NO5 | 198.42 | 199.70 | 196.42 |

These five observations are compared with one Norwegian country proxy. Fixed
hydro avoids the rolling experiment's scheduling decisions, but does not validate
hydrology, resolve internal bottlenecks or recover distinct Norwegian prices.

## Numerical verification

Every variant completes 8760 optimal hours. An independent process reconstructs
sources/offers and saved primals, checks generation/link bounds and area balances,
then reconstructs nodal injections from GSKs and native link endpoints, checks
island balances and computes passive flows outside the LP constraint matrix.
All component residuals pass 1e−4 MW; water residual is
2.04e-06 MWh with unchanged annual closure. No adaptive
storage or simultaneous charge/discharge is introduced.

| Variant | UTC hour | Native PyPSA minus fast objective EUR |
| --- | --- | ---: |
| Legacy fixed hydro | 2025-01-15 12:00:00 | 5.5879354e-08 |
| Legacy fixed hydro | 2025-07-15 12:00:00 | -1.3504177e-08 |
| Legacy fixed hydro | 2025-12-15 12:00:00 | 3.9115548e-08 |
| Gas/oil fuel update | 2025-01-15 12:00:00 | -2.6077032e-08 |
| Gas/oil fuel update | 2025-07-15 12:00:00 | 5.2386895e-10 |
| Gas/oil fuel update | 2025-12-15 12:00:00 | -3.3527613e-08 |
| Combined simple resource bids | 2025-01-15 12:00:00 | 5.5879354e-08 |
| Combined simple resource bids | 2025-07-15 12:00:00 | 2.7939677e-09 |
| Combined simple resource bids | 2025-12-15 12:00:00 | 1.3969839e-08 |

Native PyPSA independently builds the same physical network and zonal GSK
constraints with fixed injections. Agreement verifies formulation, not market
prices. Controlled legacy hourly objectives reproduce the retained checkpoint
within EUR0.000916; dual prices
can differ under degeneracy (maximum difference
EUR627.500883/MWh).

## What remains before scenario acceptance

This establishes a fast, reproducible combined baseline and a fair price comparison.
It does not show that added bid complexity automatically improves prices everywhere.
Next are audited bidding-zone assets/demand, outages and commercial constraints,
explicit training/untouched validation periods and empirical thresholds, followed
by common-input native/replay investment pairs. Transmission and wind/solar cases
remain conditional on fixed hydro; adaptive battery/hydro valuation needs chronology.
No paused adaptive-hydro search or browser replacement has been resumed.

[Combined results, source/fuel provenance, all-zone/monthly/border errors and bid examples](/research/fixed-reservoir-screening-2025/resource-bids.json)

[Retained fixed-hydro checkpoint summary](/research/fixed-reservoir-screening-2025/summary.json.gz)
· [retained area summaries](/research/fixed-reservoir-screening-2025/area-summary.csv)
· [retained German hourly results](/research/fixed-reservoir-screening-2025/hourly-de.csv.gz)
· [water replay](/research/european-reservoir-clearing-2025/replay.json).

Reproduction: tools/hybrid_fixed_hydro_2025.py with a fresh --output directory,
then the same tool with --audit, then tools/evaluate_fixed_hydro_bids_2025.py --run.
Use the pinned Python environment, bounded resources and existing verified source
caches; raw inputs and full annual primals remain outside Git.
