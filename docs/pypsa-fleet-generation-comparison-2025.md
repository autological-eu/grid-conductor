# PyPSA-Eur fleet and 2025 generation: comparison with IRENA and Ember

## Summary

PyPSA-Eur is a useful backbone for the planned hourly zonal dispatch model, but
its prepared fleet is not yet an accepted representation of the 2025 national
fleet. IRENA exposes large solar-capacity discrepancies. A full-year native
PyPSA dispatch trial also differs materially from Ember's observed national
fuel mix. Faster numerical solution alone will not fix those differences.

This report compares three distinct quantities: installed MW, weather-derived
available MWh, and dispatched/generated MWh. Matching one does not establish
agreement in the others. The downloadable comparison covers all 34 model
countries; the figures highlight Germany, France, Spain and Poland.

## What is being compared

| Evidence | Period and scope | Interpretation |
| --- | --- | --- |
| Prepared PyPSA-Eur network | 128 buses, 1,151 generators, 160 StorageUnits; 8,760 hours in 2025 | Input fleet and original renewable availability |
| PyPSA-Eur 2025 hourly solve | Candidate 006 from the original inventory search; all 59 chronological blocks | Full-year feasible fixed-inventory trial, not current best or annual optimum |
| IRENA Renewable capacity statistics 2026 | National end-2024 and end-2025 renewable capacities | Maximum net capacity; not hourly commissioning or generation |
| Ember current monthly release | National 2025 generation by fuel, twelve months required | Observed-generation comparison; not hourly availability |

The prepared network has SHA-256
`4049c130f157305dd4988d47e432c42a89758f4ee30cafe5472b7bc883eef3ec`.
Its calendar and weather are 2025, not the separate 2013 weekly benchmark.
However, a 2025 calendar does not make every underlying fleet record a verified
2025 observation. Renewables were attached through powerplantmatching/GEM
records; the IRENASTAT reconciliation path was disabled. The configured
2025 retirement/commissioning filter retains undated assets. Nuclear availability
uses a declared 2024 proxy. Costs are 2025 assumptions with zero carbon price.

**Candidate 006 is a PyPSA-Eur-based 2025 hourly dispatch solve using native
PyPSA**, covering all 8,760 hours in 59 consecutive blocks. The candidate number
identifies a trial set of storage inventories at the block boundaries, not a
different fleet or dataset. Each block solves dispatch with those prescribed
starting/ending inventories; connected boundaries preserve storage continuity.
The table column **“PyPSA-Eur 2025 solve TWh”** sums that hourly output over the
year. It is generated electricity, not available energy. This is a decomposed
full-year solve with fixed trial inventories, not a monolithic annual optimum.

Candidate 006 is chosen because complete native hourly quantities are archived
and independently replayable. It is deliberately not presented as the latest
best inventory candidate. The latest reported 4.278% optimisation gap concerns
objective bounds in that separate search: it is neither generation error nor
ENTSO-E price error. These results do not establish price calibration.

## Capacity comparison

The capacity inventory has 238 country/category slots: solar PV, wind, renewable
hydro, pumped hydro, bioenergy, geothermal and marine. Missing or rejected IRENA
rows remain unknown. The PDF parser retains 417 records and rejects 40 ambiguous
or incomplete rows rather than filling them with zero.

| Country | Technology | Prepared fleet GW | IRENA end-2024 GW | IRENA end-2025 GW |
| --- | --- | ---: | ---: | ---: |
| Germany | Solar PV | 48.773 | 91.204 | 106.272 |
| France | Solar PV | 13.239 | 25.456 | 31.226 |
| Spain | Solar PV | 41.269 | 35.860 | 44.903 |
| Poland | Solar PV | 9.313 | 21.721 | 25.421 |
| Germany | Wind | 84.496 | 72.745 | 77.808 |
| France | Wind | 26.278 | 24.241 | 25.655 |
| Spain | Wind | 31.813 | 32.184 | 33.301 |
| Poland | Wind | 9.259 | 10.152 | 10.602 |

The solar discrepancies are too large to dismiss as annual commissioning
alone. Distributed PV coverage, source vintage and geographic scope need
reconciliation. Germany's wind fleet is larger than both IRENA endpoints;
replacing every capacity with a common multiplier would therefore be unjustified.

IRENA does not validate fossil or nuclear capacity. Hydro needs turbine MW,
catchment inflow and reservoir MWh; PHS needs separate pump power, energy and
charging. Biomass needs fuel/CHP constraints; geothermal needs availability and
outages; marine needs a represented resource model. These are not extensions
of a solar/wind scaling equation. Renewable waste and parent/child categories
must be reconciled before being added together.

## PyPSA-Eur 2025 hourly-solve generation versus Ember

![Annual generation comparison across fuels](../research/fleet-generation-2025/annual.svg)

The model quantities are sums of actual native hourly generator output, with
unidirectional reservoir discharge added to primary hydro. Pumped-storage
recycling remains separate. Coal includes coal and lignite; gas includes CCGT
and OCGT; wind includes all represented offshore technologies. Bioenergy maps
only biomass. Model oil versus Ember other fossil is only a partial comparator.
Waste and geothermal are not silently assigned to unrelated observed categories.

Of 272 country/fuel comparison rows, 224 have complete annual Ember
observations and 48 remain incomplete or missing. Each annual Ember total requires all twelve country/fuel months. Missing fuels
are unknown, not zero. Signed tiny solver residuals are retained in the audit;
no substantive negative output is concealed. Country and fuel accounting
boundaries still need reconciliation, so percentage differences are diagnostics,
not an accepted model accuracy score.

| Country | Fuel | PyPSA-Eur 2025 solve TWh | Ember TWh | Difference TWh |
| --- | --- | ---: | ---: | ---: |
| DE | solar | 55.471 | 89.965 | -34.494 |
| DE | wind | 193.309 | 131.166 | +62.143 |
| DE | gas | 1.141 | 79.325 | -78.184 |
| DE | nuclear | 0.000 | 0.000 | +0.000 |
| ES | solar | 64.432 | 58.814 | +5.618 |
| ES | wind | 43.090 | 55.578 | -12.488 |
| ES | gas | 29.613 | 52.132 | -22.519 |
| ES | nuclear | 51.386 | 51.912 | -0.526 |
| FR | solar | 17.356 | 30.273 | -12.917 |
| FR | wind | 59.148 | 48.652 | +10.496 |
| FR | gas | 2.962 | 16.358 | -13.396 |
| FR | nuclear | 355.549 | 371.692 | -16.143 |
| PL | solar | 10.204 | 19.228 | -9.024 |
| PL | wind | 20.503 | 21.894 | -1.391 |
| PL | gas | 0.003 | 20.992 | -20.989 |
| PL | nuclear | 0.000 | Unknown | Unknown |

The trial markedly underproduces gas in Germany, France and Poland while
German wind exceeds observed production. Capacity changes alone cannot explain
the entire mix: fuel costs, carbon assumptions, availability, demand, exchanges
and network constraints also shape dispatch. No isolated causal attribution is
established by this comparison. Poland nuclear remains unknown in the observed
comparison because the required twelve source records are absent.

![Monthly dispatch and observed generation](../research/fleet-generation-2025/monthly.svg)

Monthly comparisons expose seasonal and fuel-substitution differences that an
annual total can hide. Ember is monthly evidence: these plots do not verify
hour-by-hour dispatch or weather timing. Independent hourly ENTSO-E comparisons,
including outages, demand, exchanges and prices, remain necessary.

## Generation differences across all countries

![Signed annual generation differences for all 34 model countries](../research/fleet-generation-2025/differences.svg)

Each cell shows **Difference TWh = PyPSA-Eur 2025 hourly-solve generation minus
Ember generation**, summed over the year for one country and fuel. Red means
the model produces more; blue means less. A common colour scale makes the size
of differences comparable, and numeric labels retain small differences.
Grey cells are missing/incomplete observations, not zero differences.

The plot covers all 34 model countries and eight fuel groups. A country/fuel
heatmap retains the identities that a pooled histogram would hide. It also
shows why positive and negative fuel differences should not be combined into
a single country total: fuel substitution can cancel while the mix remains
wrong. Large countries naturally contribute larger absolute TWh differences;
relative differences are available in the downloadable JSON where observed
annual generation is nonzero. The oil/other-fossil column has unequal scope
and is marked as a partial comparison. These are observed-data discrepancies,
not numerical solver errors, price errors or a validated model-accuracy score.

## Availability is not generation

The earlier IRENA experiment holds the original country-weighted weather shapes
and changes only assumed capacity endpoints. Linear commissioning produces
111.69 TWh of German solar availability against 89.965 TWh Ember generation;
French solar is 37.03 versus 30.273 TWh. Spanish wind is 44.42 TWh available
against 55.578 TWh generated. The latter discrepancy remains unresolved.

Available minus generated energy is not automatically curtailment. Different
layouts, technology mixes, weather conversion, distributed-generation scope,
outages and statistical boundaries can all contribute. Monthly-fitted production
series are descriptive reconstructions; they must never become dispatch
availability. No capacity sensitivity has been solved as a new scenario here.

## Implications for the fast zonal model

Reuse PyPSA-Eur's openly sourced fleet identities, grid topology and weather
conversion machinery, with source versions and licence attribution. Aggregate
only after auditing country/bidding-zone assignment. Physical AC line ratings
are not interchangeable with commercial cross-zone market capacities or
flow-based PTDF/RAM domains.

The agreed model is an explicit 8,760-hour zonal dispatch approximation: supply
cost blocks, demand and transmission constraints, with chronology for storage
and hydro. Precompute weather conversion and sparse matrices; reuse solver
structure and warm starts. It is not a reconstruction of EUPHEMIA: authentic
auction orders, block/linked bids, nonconvex acceptance and allocation rules
are not supplied by this fleet dataset.

Before using it to value investments:

1. Reconcile national renewable capacities, distributed PV and commissioning;
   independently audit thermal/nuclear fleets and availability.
2. Reconcile monthly generation scope and weather conversion without fitting
   away held-out errors. Publish country/fuel coverage and unresolved gaps.
3. Map assets and demand to actual bidding zones and define commercial network
   constraints. Keep national proxies explicit.
4. Run matched native PyPSA and fast-solver cases with identical inputs and
   storage boundaries. Check feasibility and numerical agreement separately
   from agreement with observed prices, generation and exchanges.
5. Compare each investment against a paired baseline under the same assumptions.
   Report dispatch-cost change separately from flow–price congestion rent.

## Reproduction and evidence

[Download all country/fuel/month comparisons and capacity slots](../research/fleet-generation-2025/summary.json).
The compact artifact records the network, annual witness, current Ember and
IRENA PDF hashes. Large hourly arrays and provider files remain ignored local
caches, not Git artifacts.

From the repository root, using the pinned research interpreter:

```sh
python tools/report_fleet_generation_2025.py \
  --mapping data/pypsa-eur/annual-witness-mapping/candidate-006 \
  --replay /tmp/grid-generation-replayed.json
```

The command requires a fresh output path. It checks all 59 mapped blocks,
8,760 UTC timestamps, quantity hashes, native asset order, dependency hashes
and pinned package versions. Arrays are materialized once per block to avoid repeated NPZ decompression;
native accounting and verification equations are unchanged. The publisher requires the independently replayed
accounting to equal the retained diagnostic, checks source identity and Ember
hash, and refuses an incomplete annual observation total.

Sources: [IRENA 2026 capacity statistics](https://www.irena.org/Publications/2026/Mar/Renewable-capacity-statistics-2026),
[Ember monthly electricity data](https://ember-energy.org/data/monthly-electricity-data/),
[PyPSA-Eur](https://github.com/PyPSA/pypsa-eur).
See also the [capacity reconciliation](irena-capacity-reconciliation-2025),
[hourly availability pilot](hourly-renewable-estimates-2025), and
[hourly zonal dispatch plan](hourly-zonal-dispatch-plan).

## Conclusion

PyPSA-Eur can supply the backbone, but this comparison does not justify accepting
its prepared fleet unchanged. Renewable capacity reconciliation is necessary,
and the full-year dispatch trial reveals additional generation-mix disagreement.
The next step is a versioned, reconciled zonal input compiler and matched solver
validation, followed by held-out observed-data checks. Neither a small numerical
optimisation gap nor fast runtime establishes empirical market accuracy.
