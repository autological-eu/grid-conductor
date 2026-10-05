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
reported separately in [inventory coordination](../monthly-inventory-coordination/).
The [2025 conditional-window comparison](../2025-conditional-network-benchmark/)
and [2013 weekly comparison](../network-benchmark-comparison/) retain their own
periods and acceptance gates. No emissions or investment validity follows from
this generation table.
