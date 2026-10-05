# 2025 generation comparison: preliminary fixed-inventory diagnostic

This comparison asks whether a feasible full-year model produces similar national
generation quantities to the reported 2025 ENTSO-E observations. It does **not**
yet establish a validated annual market model. The dispatch is candidate 001,
with fixed chronological inventories, rather than the newer best incumbent or
an annual optimum. Its input contains original renewable availability, not
observed generator dispatch substituted as availability.

## What is compared

Native Linopy generator and storage identities were reconstructed without a new
solve. Objective, bounds, equality/RHS and inequality/RHS coefficients had to
match each saved block before quantities were interpreted. All 59 blocks cover
8,760 UTC hours in order. Generator energy and unidirectional reservoir discharge
are primary generation; pumped-storage charging and discharge remain separate.
On the observation side, raw ENTSO-E A75/A16 interval energy was independently
replayed into hourly MWh. Only countries with all twelve complete reported
months enter the annual table. Missing categories are not assumed to be zero,
partial years are not annualised, and incomplete split-zone partitions are not
summed into national totals.

| Country | Model primary generation (TWh) | Reported primary generation (TWh) | Difference relative to reported |
| --- | ---: | ---: | ---: |
| AT | 39.526 | 52.160 | -24.22% |
| BG | 65.690 | 36.494 | +80.00% |
| CH | 48.575 | 48.040 | +1.11% |
| DE | 622.917 | 428.005 | +45.54% |
| FI | 82.163 | 79.375 | +3.51% |
| LT | 5.217 | 8.542 | -38.92% |
| LV | 4.047 | 5.792 | -30.12% |
| NL | 98.891 | 117.954 | -16.16% |
| PL | 162.410 | 157.942 | +2.83% |
| PT | 36.684 | 42.647 | -13.98% |

The difference is $(G_{model}-G_{reported})/G_{reported}$. It measures a discrepancy
between these two accounting quantities, not a verified whole-country error.
Germany's observed series is German national generation; it excludes Luxembourg.

## Why these are diagnostics rather than acceptance results

“Complete reported” means every hour of the returned generation categories is
present. It does not prove that every generator, autoproducer or fuel category
was reported. Net/gross accounting, mainland versus national geography, source
coverage and provisional fuel mappings remain unreconciled. The separate Ember
reference has materially different totals for some countries and may share
upstream sources; agreement between those datasets would be a consistency check,
not independent measurement.

The substantial discrepancies require investigation. Germany is roughly 46%
higher in this model accounting, and Bulgaria roughly 80% higher. A close total,
such as Poland's, can still conceal wrong fuel shares, hourly dispatch or imports.
We must not calibrate by a national ratio or treat stored energy as new primary
generation to make totals agree.

The prepared model uses 2025 source costs but zero operational carbon price and
a 2024 nuclear-availability proxy. These are plausible contributors to market
mismatches, **not demonstrated explanations**: attributing causality requires
controlled, source-consistent comparisons. Fixed-inventory conditional dual
prices also need separate interpretation from converged annual market prices.

## Reproduction and next gates

Offline evidence remains under ignored `data/pypsa-eur/`:
`annual-witness-mapping/full-001/`,
`2025-fixed-inventory-native-generation.json`,
`2025-generation-observations-audit.json` and
`2025-fixed-inventory-generation-comparison.json`.
The comparison tool checks producer/dependency hashes before writing a new
immutable diagnostic:

```sh
python tools/compare_native_generation_observations.py \
  --native data/pypsa-eur/2025-fixed-inventory-native-generation.json \
  --observed data/pypsa-eur/2025-generation-observations-audit.json \
  --output data/pypsa-eur/2025-fixed-inventory-generation-comparison-new.json
```

Next: reconcile geographic and fuel-accounting scopes; predeclare supported
bidding-zone mapping, price aggregation, coverage and held-out validation;
compare prices, monthly fuel shares and correctly scoped exchanges; investigate
mismatches before paired investment claims. The annual coordinator's bounds are
reported separately in [inventory coordination](monthly-inventory-coordination.md).
The [2025 conditional-window comparison](2025-conditional-network-benchmark.md)
and [2013 weekly comparison](network-benchmark-comparison.md) retain their own
periods and acceptance gates. No emissions or investment validity follows from
this generation table.

## Provisional hourly price comparison

The same candidate 001 witness provides conditional nodal dual prices. A separate
read-only diagnostic checks all mapping receipts, quantity hashes, package/code
versions and the exact 8,760-hour grid, then compares each provisionally mapped
node with its country's published observed price array. It performs no zonal
aggregation and no calibration. There are 88 compared nodes; split-country and
unsupported mappings remain unresolved. Native bus `DE2 16AC` has no nodal-price
row and is explicitly absent, not zero-priced.

For each node, only matched observed hours enter bias, MAE, RMSE and correlation:

$$
\mathrm{bias}=\frac{1}{n}\sum_{t\in T}(p^{model}_t-p^{observed}_t),\qquad
\mathrm{MAE}=\frac{1}{n}\sum_{t\in T}|p^{model}_t-p^{observed}_t|.
$$

Negative prices remain observations; gaps are not filled. Monthly diagnostics
retain their own matched-hour counts. The following are **ranges across individual
nodes**, not load-weighted national prices or confidence intervals.

| Provisional country comparison | Nodes | Matched hours per node | Bias range (€/MWh) | MAE range (€/MWh) |
| --- | ---: | ---: | ---: | ---: |
| FR | 19 | 8759 | -28.93 to 15.15 | 33.69 to 39.03 |
| DE | 18 | 8759 | -63.01 to -53.33 | 61.43 to 68.12 |
| PL | 6 | 8759 | -73.56 to -72.87 | 77.61 to 78.34 |
| AT | 2 | 8759 | -68.15 to -67.00 | 72.87 to 73.13 |
| BG | 1 | 8760 | -74.68 to -74.68 | 79.66 to 79.66 |

These discrepancies do not establish a single causal explanation. The zero
carbon price, fuel-cost assumptions, geographic aggregation, renewable and outage
proxies, network representation and fixed-inventory conditions require separate
controlled investigations. A node's conditional inventory dual is not automatically
the price of a zonal day-ahead auction. No acceptance threshold was selected after
seeing these errors; the predeclared held-out validation gate remains open.

Reproduce with `tools/compare_native_price_observations.py`, passing `--folder`
`data/pypsa-eur/annual-witness-mapping/full-001`, `--network` the hash-matched
`base_s_128_elec_.nc`, `--prices public/research/zone-prices-2025` and a new ignored
`--output` path. Three targeted tests preserve signed bias/missing observations,
constant-series undefined correlation, and malformed/misaligned-data rejection.
The stopped first diagnostic attempt repeatedly decompressed generation arrays;
the completed implementation instead directly replays the mapping gates. Neither
attempt changes dispatch, renewable availability or the annual coordinator.


![Conditional nodal-price bias and mean absolute error for every provisionally compared country.](../../research/network-benchmark-2025/conditional-annual-price-diagnostic.svg)

Each dot represents one native node; connecting lines show the minimum and
maximum across that country's compared nodes. They are not confidence intervals
or aggregated zonal prices. Every compared country is shown, including large
errors. Unresolved mappings and absent price rows remain listed in the
[downloadable node/month metrics and provenance](../../research/network-benchmark-2025/conditional-annual-price-diagnostic.json).
The artifact explicitly leaves empirical validation, annual optimum, held-out
acceptance and investment validation false. These are reported error diagnostics,
not acceptance thresholds or automatic calibration targets.

The publication tool checks the diagnostic producer, observed file hashes,
full-year source identity, unique model-node inventory, monthly matched-hour
accounting and finite, consistent error metrics before producing the artifact.
Three publication-gate tests reject changed sources/partial years/duplicate nodes,
promoted validation statuses, inconsistent errors and coverage.
