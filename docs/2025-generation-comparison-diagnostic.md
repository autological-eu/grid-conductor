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

## Inventory-state sensitivity: candidate 001 versus candidate 006

The candidate 006 witness has now been mapped independently across all 59 blocks
and 8,760 hours, after objective, bounds, equality/RHS and inequality/RHS identity
against the original model. Both witnesses retain the same original generation
availability, network, capacities and operating costs. Their linked inventory
states differ. These are two feasible trajectories, **not two annual optima or
two solver implementations**.

The operating cost decreases from €50,662,078,462.99544 to
€50,633,472,741.74006: **€28.606 million**, approximately 0.0565%. This is improved
dispatch at another feasible inventory state, not an investment benefit. No new
transmission or storage capacity was added.

The price comparison uses the same observed price files, provisional geography
and matched hours for both witnesses. Across 88 compared nodes, the largest
absolute change in mean price bias is only **€0.141/MWh**. The large German and
Polish underprediction persists.

| Provisional country | Nodes | Candidate 001 bias range (€/MWh) | Candidate 006 bias range (€/MWh) | Paired change in bias (€/MWh) |
| --- | ---: | ---: | ---: | ---: |
| FR | 19 | −28.93 to 15.15 | −29.07 to 15.14 | −0.141 to −0.003 |
| DE | 18 | −63.01 to −53.33 | −63.04 to −53.42 | −0.093 to −0.030 |
| PL | 6 | −73.56 to −72.87 | −73.60 to −72.92 | −0.054 to −0.033 |
| AT | 2 | −68.15 to −67.00 | −68.19 to −67.07 | −0.067 to −0.049 |
| BG | 1 | −74.68 | −74.72 | −0.047 |

Ranges describe individual nodes. The paired change is computed for each same
node before taking its range; it is not a difference between range endpoints.
Negative bias means the model's conditional price is below the observed price.

![Candidate 001 and candidate 006 conditional price biases against the same 2025 observations, with an unchanged-bias diagonal.](../../research/network-benchmark-2025/inventory-price-sensitivity.svg)

Each point represents a single provisional model node. Points near the diagonal
have similar errors in both witnesses; agreement with observed prices would
instead require small errors near zero. Colors/markers distinguish model
countries, not validated bidding zones. Overlapping points do not remove nodes
from the downloadable report.

**What this shows:** this particular feasible inventory improvement does not
resolve the price mismatch. **What it does not show:** that wider inventory
changes cannot matter, that either witness has converged, or that carbon costs
alone explain the errors. Both witnesses come from the conservative fixed-anchor
search; annual convergence and controlled cost/outage/network investigations
remain open. There is no calibration or newly selected acceptance threshold.

[Download paired node metrics, source hashes and explicit unpassed acceptance gates](../../research/network-benchmark-2025/inventory-price-sensitivity.json).
`compare_native_price_witnesses.py` rechecks both complete annual chains and
native mappings, then compares the same immutable price observations. Three tests
reject mismatched source/geography/coverage, duplicate or absent node domains and
nonfinite metrics, while preserving signed changes and undefined correlations.
`plot_native_price_witnesses.py` retains every compared node and embeds the JSON
and plotting-producer hashes in the SVG. Original candidate 001 diagnostics
remain unchanged; this sensitivity is separate from observed-data acceptance
and the 2013 weekly/2025 conditional-window benchmarks.


## German gas-generation consistency check

The newer feasible inventory witness still has a substantial generation-mix
mismatch. We retrieved Bundesnetzagentur SMARD filter **4071** (German natural-gas
feed-in), using its public hourly source rather than requiring a Clarigrid
connection. The source index and 53 weekly chunks have URL, byte-count and SHA-256
receipts. All **8,760 hours** in the exact 2025 UTC calendar are present. Reported
values are energy in **MWh per hourly interval**, summed without an additional
annual or monthly multiplier. Missing values would make the complete total
unavailable. Local-calendar monthly files are not substituted for UTC months.

| 2025 German gas quantity | Energy (TWh) | Interpretation |
| --- | ---: | --- |
| SMARD filter 4071 | 60.549009 | Reported gas feed-in |
| Audited ENTSO-E B04 | 60.548969 | German national generation proxy, Luxembourg excluded |
| Native candidate 006 CCGT + OCGT | 1.140816 | Conditional fixed-inventory model dispatch |

SMARD and ENTSO-E differ by only **40.162 MWh** across the year, approximately
**0.0000663%** of reported gas generation. This is a strong consistency check
on the reported series and interval integration. It is **not independent
measurement**: the two publications may use the same underlying TSO observations.
The small difference is consistent with rounding, but its cause is not audited.
Neither source establishes complete gross generation, behind-the-meter coverage
or a fully reconciled model-mainland/CHP taxonomy. The provider's detailed
time-label and accounting-method audit remains open.

![Monthly German gas feed-in from SMARD and ENTSO-E, compared with candidate 006 native CCGT and OCGT dispatch](../../research/network-benchmark-2025/german-gas-consistency.svg)

| UTC month | SMARD (TWh) | ENTSO-E (TWh) | Candidate 006 gas (TWh) |
| --- | ---: | ---: | ---: |
| 01 | 7.928482 | 7.928476 | 0.468921 |
| 02 | 7.703973 | 7.703972 | 0.543317 |
| 03 | 5.654577 | 5.654575 | 0.000000 |
| 04 | 3.686275 | 3.686272 | 0.000000 |
| 05 | 3.129199 | 3.129195 | 0.000000 |
| 06 | 2.402675 | 2.402671 | 0.000000 |
| 07 | 2.919264 | 2.919260 | 0.000000 |
| 08 | 3.017600 | 3.017595 | 0.000000 |
| 09 | 3.801115 | 3.801110 | 0.000000 |
| 10 | 5.259448 | 5.259443 | 0.000000 |
| 11 | 7.523793 | 7.523793 | 0.041951 |
| 12 | 7.522609 | 7.522609 | 0.086628 |

The model produces only about **1.88%** of the reported gas quantity. Together
with the persistent price and exchange mismatches, this is a reason to investigate
model assumptions before using this baseline for annual investment claims.
It does not establish that one specific assumption explains the entire error.
The prepared baseline's zero operational carbon price is a known material
limitation; fuel costs, fleet/CHP representation, outages, network aggregation
and the unresolved inventory optimum also need controlled checks. Keep the
current algorithm-study input unchanged while it runs. A policy-cost or outage
variant needs separate hashes, declared coverage and independently solved
baseline/intervention pairs. Observed generation must never replace renewable
availability. No lifecycle carbon factors or avoided-emission estimates are
inferred from this gas diagnostic.

[Download the monthly comparison, source receipts and unpassed acceptance gates](../../research/network-benchmark-2025/german-gas-consistency.json).
Reproduce with `audit_smard_2025_gas.py`, `compare_smard_2025_gas.py` and
`plot_smard_gas_comparison.py`. Five targeted tests check UTC boundaries, interval
sums, source receipts, nulls, duplicates, incomplete observations and changed
calendar/carrier identities. Annual optimisation, empirical validation and
investment acceptance remain **false**. This is separate from the 2013 weekly
and matched 2025 conditional-window benchmarks.

Source: Bundesnetzagentur / SMARD, filter 4071. Licence: [German Data Licence
Attribution 2.0](https://www.govdata.de/dl-de/by-2-0). Values are aggregated to UTC
months; the chart and comparison are our derivations.
The [Clarigrid SMARD catalog description](https://www.clarigrid.energy/datasets/smard-actual-natural-gas-4071)
helped identify this source and its interval-energy units. The public MCP endpoint
requires account sign-in and has not been used to retrieve these observations.
Catalog inclusion does not verify historical coverage or independent provenance.
